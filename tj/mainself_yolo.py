# tj/mainself_yolo.py
import requests
import time
from plc_connect import plc_db
from wlkata_mirobot import WlkataMirobot
import moveSelf
import maduoXYZ
from realsense_depth import *
import cv2 as cv
import visualSignal
import ast  # 新增：解析字典字符串必需
import os   # 新增：创建目录/路径拼接必需（原代码用了os但未导入）
import datetime
# 实例化 arm 对象
arm = WlkataMirobot()
# 机械臂初始化（必须）
arm.home()
# 实例化 PLC 对象
PLC = plc_db()

# 连接 plc，直到连接成功
while True:
    message_plc = 'connect plc ok' if PLC.connect() else 'connect plc fail'
    if message_plc == 'connect plc ok':
        break

CLOUD_API_URL = "http://192.168.40.59:5401"
UPLOAD_ENDPOINT = f"{CLOUD_API_URL}/upload"
RESULT_ENDPOINT = f"{CLOUD_API_URL}/result"

session = requests.Session()

SAVE_ROOT = "./recognition_results"
os.makedirs(SAVE_ROOT, exist_ok=True)


def get_timestamped_filename(prefix, ext):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{ext}"

def visualRecognition():
    time.sleep(2)
    dc = DepthCamera()
    ret, depth_frame, color_frame = dc.get_frame()

    if not ret:
        print("警告：未获取到相机帧")
        return None, None, None

    color_frame_belt = color_frame[178:310, 258:400]

    temp_image_path = os.path.join(SAVE_ROOT, "temp_upload.jpg")
    try:
        cv.imwrite(temp_image_path, color_frame_belt)
    except Exception as e:
        print(f"临时图像保存失败: {e}")
        return None, None, None

    # 1. 上传图片，获取 task_id
    task_id = None
    uploaded_filename = None
    try:
        with open(temp_image_path, "rb") as f:
            files = {"file": ("temp_upload.jpg", f, "image/jpeg")}
            response = session.post(UPLOAD_ENDPOINT, files=files, timeout=30)
            response.raise_for_status()
            upload_result = response.json()

            if not upload_result.get("success", False):
                print(f"云平台上传失败: {upload_result.get('message', '未知错误')}")
                return None, None, None

            task_id = upload_result.get("task_id")        # ✅ 新增：获取任务ID
            uploaded_filename = upload_result.get("filename")
            print(f"图像上传成功，task_id={task_id}，filename={uploaded_filename}")
    except requests.exceptions.Timeout:
        print("上传请求超时(30秒)")
        return None, None, None
    except requests.exceptions.ConnectionError:
        print(f"云平台连接失败，请检查 {UPLOAD_ENDPOINT}")
        return None, None, None
    except Exception as e:
        print(f"上传请求失败: {e}")
        return None, None, None

    # 2. 用 task_id 轮询结果（最多等待30秒，每2秒查询一次）
    max_retries = 15
    retry_count = 0
    result_data = None
    while retry_count < max_retries:
        try:
            # 优先用 task_id 查询（更快），兼容 filename 回退
            params = {"task_id": task_id} if task_id else {"filename": uploaded_filename}
            response = session.get(RESULT_ENDPOINT, params=params, timeout=10)
            response.raise_for_status()
            result_data = response.json()

            if result_data.get("ready", False):
                print("✅ 云平台返回解析结果")
                break

            retry_count += 1
            time.sleep(2)
        except requests.exceptions.Timeout:
            retry_count += 1
            time.sleep(2)
        except Exception as e:
            print(f"结果查询失败: {e}")
            retry_count += 1
            time.sleep(2)

    if not result_data or not result_data.get("ready"):
        print("超时未获取到解析结果(30秒)")
        return None, None, None
        
    if not result_data.get("success", False):
        error_msg = result_data.get("message", "未知算法错误")
        print(f"❌ 云端算法执行失败: {error_msg}")
        return None, None, None

    # 3. 解析结果（增强鲁棒性，兼容中英文冒号及不同描述）
    raw_content = result_data.get("content", "").strip()
    out, conf, shape_type = None, None, None
    shapes = {"triangle": 0, "rectangle": 0, "polygons": 0, "circles": 0}

    lines = [line.strip() for line in raw_content.split("\n") if line.strip()]
    for line in lines:
        # 统一将中文冒号替换为英文冒号，方便处理
        line = line.replace("：", ":")
        
        if line.startswith("识别的数字:") or line.startswith("识别的结果:"):
            parts = line.split(":", 1)
            if len(parts) > 1:
                num_str = parts[1].strip()
                # 提取字符串中的数字部分，防止有乱码或空格
                num_str = ''.join(filter(str.isdigit, num_str))
                if num_str.isdigit():
                    out = int(num_str)
                    
        elif line.startswith("置信度为:") or line.startswith("置信度:"):
            parts = line.split(":", 1)
            if len(parts) > 1:
                try:
                    conf = float(parts[1].strip())
                except ValueError:
                    pass
                    
        elif line.startswith("分类结果:"):
            parts = line.split(":", 1)
            if len(parts) > 1:
                shape_type = parts[1].strip().replace(" ", "").lower()

    # 只要拿到了【数字】和【分类结果】，就算成功（置信度 conf 视为可选项）
    if out is None or shape_type is None:
        print(f"解析失败！原始内容:\n{raw_content}")
        return None, None, None

    # ✅ 修复：提前安全地处理 conf_str，防止 None 无法格式化
    conf_str = f"{conf:.2f}" if conf is not None else "N/A"

    # 4. 保存结果到本地
    txt_filename = get_timestamped_filename("recognition_result", "txt")
    txt_save_path = os.path.join(SAVE_ROOT, txt_filename)
    try:
        result_content = (
            f"识别的数字:{out}\n"
            f"置信度为:{conf_str}\n"
            f"分类结果：{shape_type}"
        )
        with open(txt_save_path, 'w', encoding='utf-8') as f:
            f.write(result_content)
    except Exception as e:
        print(f"写入结果文件时出错: {e}")

    print(f"视觉识别完成: 数字={out}, 置信度={conf_str}, 分类={shape_type}")
    return shapes, shape_type, out



def moveEndSignal(PLC):
    end = PLC.read('int', 2)
    while end == 0:
        PLC.write(2, bytearray(b'\x00\n'))
        end = PLC.read('int', 2)
        if end == 10:
            break
    time.sleep(2)
    PLC.write(2, bytearray(b'\x00\x00'))


# 取料坐标点
AList = [-65.5, -197.9, 133.6]
BList = [-17.5, -148.9, 128.6]
CList = [69.3, -138.1, 130.0]
DList = [-140.0, 65.2, 131.0]

# 放料中心坐标
one1 = [219.0, 35.0, 142.0]
two2 = [40.6, 225.0, 138.0]

# 循环读取 plc 信息
while True:
    start = PLC.read('int', 0)
    carryStatu = PLC.read('int', 18)
    visual = PLC.read('bool', 44, 0)
    maduoStart = PLC.read('int', 26)

    # 分拣搬运
    if start == 30 and maduoStart == 0 and visual == False:
        print('搬运信号', start)
        # 分拣 A
        if carryStatu == 10:
            startPoint = AList
            endPoint = one1
        # 分拣 B
        elif carryStatu == 20:
            startPoint = BList
            endPoint = two2
        # 分拣 C
        elif carryStatu == 30:
            startPoint = CList
            endPoint = DList

        # 执行搬运程序
        moveSelf.carry(arm, startPoint, endPoint)
        # 完成搬运程序,给 plc 完成信号
        moveEndSignal(PLC)

    elif start == 0 and visual == True:
        time.sleep(1)
        print('视觉识别信号', visual)
        shapes, shape_type, out = visualRecognition()
        
        # 增加判空保护，防止网络异常导致程序崩溃
        if shape_type is None:
            print("⚠️ 视觉识别失败或超时，跳过本次信号")
            continue  # 跳过本次循环，重新读取 PLC 信号
            
        if shape_type == '奇数':  # 001
            print(shape_type)
            visualSignal.visual(PLC)
            visualSignal.circular(PLC)

        elif shape_type == '偶数':
            print(shape_type)
            visualSignal.visual(PLC)
            visualSignal.rectangle(PLC)

        elif shape_type == '零':
            print(shape_type)
            visualSignal.visual(PLC)
            visualSignal.triangle(PLC)

    # 分拣堆垛
    elif start == 30 and maduoStart == 50 and visual == False:
        print('分拣堆垛信号', maduoStart)
        # xNumOne, yNumOne, zNumOne 需要寻址 plc 获得，分别代表行数，列数，层数
        xNumOne = PLC.read('int', 28)
        yNumOne = PLC.read('int', 30)
        zNumOne = PLC.read('int', 32)
        # xNumTwo, yNumTwo, zNumTwo 需要寻址 plc 获得，分别代表行数，列数，层数
        xNumTwo = PLC.read('int', 34)
        yNumTwo = PLC.read('int', 36)
        zNumTwo = PLC.read('int', 38)

        num1 = xNumOne * yNumOne * zNumOne
        num2 = xNumTwo * yNumTwo * zNumTwo

        # ranks: 1 是行优先，2 是列优先, order：1 是 Z 次序，2 是 S 次序
        ranks = PLC.read('int', 46)
        order = PLC.read('int', 48)

        # 分拣
        while (num1 >= 0 and maduoStart == 50) or (num2 >= 0 and maduoStart == 50):
            maduoStart = PLC.read('int', 26)
            if maduoStart == 0:
                print('Stop 分拣堆垛信号', maduoStart)
                break

            carryStatu = PLC.read('int', 18)
            if carryStatu == 10:
                # 确定放物坐标点
                XYZ = [244.0, -6.8, 141.0]
                xyzList = maduoXYZ.getXYZList(ranks, order, XYZ[0], XYZ[1], XYZ[2], xNumOne, yNumOne, zNumOne)
                xyzList = xyzList[::-1]
                xyz = xyzList[num1 - 1]
                start = PLC.read('int', 0)
                print('AList', AList)
                print('xyz', xyz)

                if start == 30:
                    moveSelf.carry(arm, AList, xyz)
                    # 完成搬运程序,给 plc 完成信号
                    moveEndSignal(PLC)
                    num1 = num1 - 1
                    print('num1', num1)

            # 分拣 B
            elif carryStatu == 20:
                # 确定放物坐标点
                XYZ = [54.8, 177.3, 139.0]
                xNumOne, yNumOne, zNumOne = 2, 2, 2
                xyzList = maduoXYZ.getXYZList(ranks, order, XYZ[0], XYZ[1], XYZ[2], xNumTwo, yNumTwo, zNumTwo)
                xyzList = xyzList[::-1]
                xyz = xyzList[num2 - 1]
                start = PLC.read('int', 0)
                if start == 30:
                    moveSelf.carry(arm, BList, xyz)
                    # 完成搬运程序,给 plc 完成信号
                    moveEndSignal(PLC)
                    num2 = num2 - 1
                    print('num2', num2)