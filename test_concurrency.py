# test_concurrency.py
import requests
import time
import threading
import os
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============ 配置区 ============
CLOUD_API_URL = "http://192.168.40.59:5401"  # 修改为你的后端地址
UPLOAD_ENDPOINT = f"{CLOUD_API_URL}/upload"
RESULT_ENDPOINT = f"{CLOUD_API_URL}/result"

NUM_CLIENTS = 5          # 模拟并发客户端数量（建议设为 3~5 测试，避免瞬间打满 GPU OOM）
POLL_TIMEOUT = 60        # 单个任务轮询超时时间（秒）
POLL_INTERVAL = 1        # 轮询间隔（秒）

# 生成测试图片的保存目录
TEST_IMG_DIR = "./test_images"
os.makedirs(TEST_IMG_DIR, exist_ok=True)

# ============ 辅助函数 ============
def generate_test_image(device_id: int) -> str:
    """为每个设备生成一张带有编号的测试图片，方便区分"""
    img = Image.new('RGB', (100, 100), color=(73, 109, 137))
    draw = ImageDraw.Draw(img)
    
    # 尝试加载字体，失败则用默认字体
    try:
        # Linux 常见字体路径，如果没有会用默认
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    except IOError:
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except IOError:
            font = ImageFont.load_default()
        
    draw.text((30, 30), str(device_id), fill=(255, 255, 0), font=font)
    
    img_path = os.path.join(TEST_IMG_DIR, f"device_{device_id}.jpg")
    img.save(img_path)
    return img_path

# ============ 核心模拟逻辑 ============
def simulate_edge_device(device_id: int) -> dict:
    """
    模拟单个边缘端设备的完整工作流：
    上传图片 -> 获取 task_id -> 轮询结果 -> 验证结果
    """
    start_time = time.time()
    img_path = generate_test_image(device_id)
    
    print(f"[Device {device_id}] [INFO] 开始上传图片: {img_path}")
    
    # 1. 上传图片
    task_id = None
    uploaded_filename = None
    try:
        with open(img_path, "rb") as f:
            files = {"file": (f"device_{device_id}.jpg", f, "image/jpeg")}
            response = requests.post(UPLOAD_ENDPOINT, files=files, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if not result.get("success"):
                return {"device_id": device_id, "status": "上传失败", "detail": result.get("message")}
                
            task_id = result.get("task_id")
            uploaded_filename = result.get("filename")
            print(f"[Device {device_id}] [OK] 上传成功，获得 task_id: {task_id[:8]}... filename: {uploaded_filename}")
            
    except Exception as e:
        return {"device_id": device_id, "status": "上传异常", "detail": str(e)}

    # 2. 轮询结果
    poll_start = time.time()
    while time.time() - poll_start < POLL_TIMEOUT:
        try:
            # 严格使用 task_id 查询，这是防串流的关键
            params = {"task_id": task_id}
            res = requests.get(RESULT_ENDPOINT, params=params, timeout=5)
            res.raise_for_status()
            data = res.json()
            
            #  只要 ready 为 True，无论成功失败都停止轮询
            if data.get("ready"):
                cost_time = time.time() - start_time
                
                # 检查是否是业务失败（如算法崩溃、找不到文件等）
                if not data.get("success"):
                    error_msg = data.get("message", "未知错误")
                    print(f"[Device {device_id}] [FAIL] 任务处理失败！耗时: {cost_time:.2f}s, 原因: {error_msg}")
                    return {"device_id": device_id, "status": "处理失败", "detail": error_msg}
                
                # 成功的逻辑
                content = data.get("content", "")
                print(f"[Device {device_id}] [OK] 获取结果成功！耗时: {cost_time:.2f}s")
                
                if data.get("filename") != uploaded_filename:
                    return {"device_id": device_id, "status": "串流错误", "detail": f"期望 {uploaded_filename}, 实际 {data.get('filename')}"}
                
                return {
                    "device_id": device_id, 
                    "status": "成功", 
                    "cost_time": f"{cost_time:.2f}s",
                    "task_id": task_id[:8],
                    "result_preview": content[:50] + "..." if len(content) > 50 else content
                }
                
            time.sleep(POLL_INTERVAL)
            
        except requests.exceptions.HTTPError as e:
            # 如果后端依然返回 4xx/5xx，在这里捕获并提示
            print(f"[Device {device_id}] [ERROR] 服务器返回错误: {e.response.status_code}")
            try:
                err_detail = e.response.json().get("message", e.response.text)
                return {"device_id": device_id, "status": "接口异常", "detail": err_detail}
            except ValueError:
                return {"device_id": device_id, "status": "接口异常", "detail": str(e)}
        except Exception as e:
            print(f"[Device {device_id}] [WARN] 轮询异常: {e}")
            time.sleep(2)
            
    return {"device_id": device_id, "status": "轮询超时", "detail": f"超过 {POLL_TIMEOUT} 秒未获取结果"}

# ============ 主测试流程 ============
def run_concurrency_test():
    print("=" * 60)
    print(f"[START] 开始并发测试：模拟 {NUM_CLIENTS} 个边缘端同时工作")
    print(f"[TARGET] 目标服务器: {CLOUD_API_URL}")
    print("=" * 60)
    
    results = []
    
    # 使用线程池模拟并发
    with ThreadPoolExecutor(max_workers=NUM_CLIENTS) as executor:
        futures = {executor.submit(simulate_edge_device, i): i for i in range(NUM_CLIENTS)}
        
        for future in as_completed(futures):
            results.append(future.result())
            
    # 打印测试报告
    print("\n" + "=" * 60)
    print("[REPORT] 并发测试报告")
    print("=" * 60)
    
    success_count = 0
    total_time = 0.0
    
    # 按 device_id 排序输出
    results.sort(key=lambda x: x["device_id"])
    
    for res in results:
        dev_id = res["device_id"]
        status = res["status"]
        
        if status == "成功":
            success_count += 1
            cost = res.get("cost_time", "0")
            total_time += float(cost.replace('s', ''))
            print(f"Device {dev_id} | [OK] {status} | 耗时: {cost} | Task: {res.get('task_id')} | 结果: {res.get('result_preview')}")
        else:
            print(f"Device {dev_id} | [FAIL] {status} | 详情: {res.get('detail')}")
            
    print("-" * 60)
    print(f"[RESULT] 成功率: {success_count}/{NUM_CLIENTS}")
    
    # 性能评估
    if success_count == NUM_CLIENTS:
        avg_time = total_time / NUM_CLIENTS
        max_serial_time = NUM_CLIENTS * 5  # 假设单次处理至少 5 秒
        if avg_time < max_serial_time * 0.5:  # 如果平均时间远小于串行总时间，说明并发生效
            print("[PERF] 并发性能: 优秀 (后端成功并发处理，未出现排队)")
        else:
            print("[WARN] 并发性能: 一般 (可能仍存在排队等待，请检查 max_workers 或 GPU 占用)")
    else:
        print("[FAIL] 测试未全部通过，请检查后端日志排查错误。")

if __name__ == '__main__':
    # 检查 PIL 是否安装
    try:
        from PIL import Image
    except ImportError:
        print("[ERROR] 缺少 Pillow 库，请运行: pip install Pillow")
        exit(1)
        
    run_concurrency_test()