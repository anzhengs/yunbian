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
import ast  # 鏂板锛氳В鏋愬瓧鍏稿瓧绗︿覆蹇呴渶
import os   # 鏂板锛氬垱寤虹洰褰?璺緞鎷兼帴蹇呴渶锛堝師浠ｇ爜鐢ㄤ簡os浣嗘湭瀵煎叆锛?
# 瀹炰緥鍖?arm 瀵硅薄
arm = WlkataMirobot()
# 鏈烘鑷傚垵濮嬪寲锛堝繀椤伙級
arm.home()
# 瀹炰緥鍖?PLC 瀵硅薄
PLC = plc_db()

# 杩炴帴 plc锛岀洿鍒拌繛鎺ユ垚鍔?while True:
    message_plc = 'connect plc ok' if PLC.connect() else 'connect plc fail'
    if message_plc == 'connect plc ok':
        break

# 浜戝钩鍙癆PI鍦板潃锛堟牴鎹疄闄呮帴鍙ｈ皟鏁达級
CLOUD_API_URL = "http://192.168.40.49:5401"
UPLOAD_ENDPOINT = f"{CLOUD_API_URL}/upload"  # 浜戝钩鍙版帴鏀跺浘鐗囩殑鎺ュ彛
RESULT_ENDPOINT = f"{CLOUD_API_URL}/result"  # 浜戝钩鍙拌繑鍥炵粨鏋滅殑鎺ュ彛

# 缁撴灉淇濆瓨鏍圭洰褰曪紙纭繚鐪熷疄杩愯鏃剁洰褰曞瓨鍦級
SAVE_ROOT = "./recognition_results"
os.makedirs(SAVE_ROOT, exist_ok=True)  # 鏂板锛氳嚜鍔ㄥ垱寤虹洰褰曪紝閬垮厤淇濆瓨澶辫触

# 琛ュ叏鐪熷疄杩愯鎵€闇€鐨勬椂闂存埑鍑芥暟锛堝鏋滀富绋嬪簭宸叉湁鍙拷鐣ワ級
def get_timestamped_filename(prefix, ext):
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{ext}"

def visualRecognition():
    time.sleep(2)
    dc = DepthCamera()
    ret, depth_frame, color_frame = dc.get_frame()

    print(f"鐩告満鑾峰彇甯э細ret={ret}")
    if not ret:
        print("璀﹀憡锛氭湭鑾峰彇鍒扮浉鏈哄抚锛岃烦杩囦繚瀛?)
        return None, None, None

    # 1. 瑁佸壀鎰熷叴瓒ｅ尯鍩燂紙淇濇寔鍘熸湁閫昏緫锛?    color_frame_belt = color_frame[178:310, 258:400]

    # 2. 涓存椂淇濆瓨鍥惧儚锛堢敤浜庝笂浼狅級
    temp_image_path = os.path.join(SAVE_ROOT, "temp_upload.jpg")
    try:
        cv.imwrite(temp_image_path, color_frame_belt)
        print(f"涓存椂鍥惧儚宸蹭繚瀛樿嚦锛歿temp_image_path}")
    except Exception as e:
        print(f"鉂?涓存椂鍥惧儚淇濆瓨澶辫触锛歿e}")
        return None, None, None

    # 3. 涓婁紶鍥惧儚鍒颁簯骞冲彴
    uploaded_filename = None
    try:
        with open(temp_image_path, "rb") as f:
            files = {"file": ("temp_upload.jpg", f, "image/jpeg")}  # 鍖归厤app.py鐨勬枃浠跺弬鏁板悕
            response = requests.post(UPLOAD_ENDPOINT, files=files, timeout=30)
            response.raise_for_status()  # 妫€鏌ヨ姹傛槸鍚︽垚鍔?            upload_result = response.json()

            # 瀹归敊锛氬垽鏂笂浼犳垚鍔熺殑瀛楁锛堝尮閰嶄簯骞冲彴杩斿洖锛?            if not upload_result.get("success", False):
                err_msg = upload_result.get("message", "鏈煡閿欒")
                print(f"鉂?浜戝钩鍙颁笂浼犲け璐ワ細{err_msg}")
                return None, None, None

            uploaded_filename = upload_result.get("filename")
            if not uploaded_filename:
                print(f"鉂?浜戝钩鍙版湭杩斿洖鏂囦欢鍚嶏紝涓婁紶澶辫触")
                return None, None, None

            print(f"鉁?鍥惧儚涓婁紶鎴愬姛锛屾枃浠跺悕锛歿uploaded_filename}")
    except requests.exceptions.Timeout:
        print(f"鉂?涓婁紶璇锋眰瓒呮椂锛?0绉掞級锛岃妫€鏌ヤ簯骞冲彴缃戠粶")
        return None, None, None
    except requests.exceptions.ConnectionError:
        print(f"鉂?浜戝钩鍙拌繛鎺ュけ璐ワ紝璇锋鏌UPLOAD_ENDPOINT}鏄惁鍙揪")
        return None, None, None
    except Exception as e:
        print(f"鉂?涓婁紶璇锋眰澶辫触锛歿str(e)}")
        return None, None, None

    # 4. 杞浜戝钩鍙拌幏鍙栬В鏋愮粨鏋滐紙鏈€澶氱瓑寰?0绉掞紝姣?绉掓煡涓€娆★級
    max_retries = 15
    retry_count = 0
    result_data = None
    while retry_count < max_retries:
        try:
            params = {"filename": uploaded_filename}  # 鍖归厤浜戝钩鍙扮殑鍙傛暟鍚?            response = requests.get(RESULT_ENDPOINT, params=params, timeout=10)
            response.raise_for_status()
            result_data = response.json()

            # 妫€鏌ョ粨鏋滄槸鍚﹀氨缁?            if result_data.get("ready", False):
                print("鉁?浜戝钩鍙拌繑鍥炶В鏋愮粨鏋?)
                break

            print(f"鈴?绛夊緟瑙ｆ瀽缁撴灉锛坽retry_count + 1}/{max_retries}锛?)
            retry_count += 1
            time.sleep(2)
        except requests.exceptions.Timeout:
            print(f"鉂?缁撴灉鏌ヨ瓒呮椂锛?0绉掞級")
            retry_count += 1
            time.sleep(2)
        except requests.exceptions.ConnectionError:
            print(f"鉂?浜戝钩鍙拌繛鎺ュけ璐ワ紝璇锋鏌RESULT_ENDPOINT}鏄惁鍙揪")
            retry_count += 1
            time.sleep(2)
        except Exception as e:
            print(f"鉂?缁撴灉鏌ヨ澶辫触锛歿str(e)}")
            retry_count += 1
            time.sleep(2)

    if not result_data or not result_data.get("ready"):
        print("鉂?瓒呮椂鏈幏鍙栧埌瑙ｆ瀽缁撴灉锛?0绉掞級")
        return None, None, None

    raw_content = result_data.get("content", "").strip()  # 鑾峰彇浜戝钩鍙拌繑鍥炵殑3琛屾枃鏈?    print(f"馃摑 浜戝钩鍙拌繑鍥炲師濮嬬粨鏋滐細\n{raw_content}")
    # 鍒濆鍖栧彉閲忥紙榛樿鍊硷級
    out = None  # 璇嗗埆鐨勬暟瀛楋紙濡?锛?    conf = None  # 缃俊搴︼紙濡?.98锛?    shape_type = None  # 鍒嗙被缁撴灉锛堝"濂?锛?    # 鍏煎鍘熶唬鐮佺殑shapes瀛楀吀锛堣嫢鍚庣画涓嶉渶瑕佸彲鍒犻櫎锛岃繖閲屼繚鐣欓伩鍏嶆姤閿欙級
    shapes = {"triangle": 0, "rectangle": 0, "polygons": 0, "circles": 0}

    # 鎸夎鍒嗗壊瑙ｆ瀽锛堜弗鏍煎尮閰嶄綘鐨?琛屾牸寮忥級
    lines = [line.strip() for line in raw_content.split("\n") if line.strip()]
    for line in lines:
        # 瑙ｆ瀽銆岃瘑鍒殑鏁板瓧銆嶏紙鏍煎紡锛氳瘑鍒殑鏁板瓧:7锛?        print("寮€濮嬭В鏋?)
        if line.startswith("璇嗗埆鐨勬暟瀛?"):
            num_str = line.split(":", 1)[1].strip()
            if num_str.isdigit():
                out = int(num_str)
            else:
                print(f"鈿狅笍 璇嗗埆鏁板瓧鏍煎紡閿欒锛歿num_str}锛堝簲涓烘暣鏁帮級")

        # 瑙ｆ瀽銆岀疆淇″害銆嶏紙鏍煎紡锛氱疆淇″害涓?0.98锛?        elif line.startswith("缃俊搴︿负:"):
            conf_str = line.split(":", 1)[1].strip()
            try:
                conf = float(conf_str)
            except ValueError:
                print(f"鈿狅笍 缃俊搴︽牸寮忛敊璇細{conf_str}锛堝簲涓哄皬鏁帮級")

        # 瑙ｆ瀽銆屽垎绫荤粨鏋溿€嶏紙鏍煎紡锛氬垎绫荤粨鏋滐細濂囷級
        elif line.startswith("鍒嗙被缁撴灉锛?):  # 娉ㄦ剰鏄腑鏂囧啋鍙枫€岋細銆嶏紝鍜屽墠涓や釜鑻辨枃鍐掑彿鍖哄垎
            shape_type = line.split("锛?, 1)[1].strip()  # 鐢ㄤ腑鏂囧啋鍙峰垎鍓?            # 缁熶竴鍒嗙被缁撴灉鏍煎紡锛堝彲閫夛細閬垮厤澶у皬鍐?绌烘牸闂锛?            shape_type = shape_type.replace(" ", "").lower()

    # 鏍￠獙瑙ｆ瀽缁撴灉
    if out is None or conf is None or shape_type is None:
        print(f"鉂?瑙ｆ瀽澶辫触锛佸師濮嬪唴瀹癸細\n{raw_content}")
        print(f"褰撳墠瑙ｆ瀽缁撴灉锛氭暟瀛?{out}锛岀疆淇″害={conf}锛屽垎绫?{shape_type}")
        return None, None, None, None

    # 5. 淇濆瓨缁撴灉鍒皌xt鏂囦欢锛堟寜浣犵殑鏍煎紡淇濆瓨锛屽寘鍚疆淇″害锛?    txt_filename = get_timestamped_filename("recognition_result", "txt")
    txt_save_path = os.path.join(SAVE_ROOT, txt_filename)
    try:
        # 淇濇寔鍜屼簯骞冲彴涓€鑷寸殑鏍煎紡淇濆瓨
        result_content = (
            f"璇嗗埆鐨勬暟瀛?{out}\n"
            f"缃俊搴︿负:{conf:.2f}\n"
            f"鍒嗙被缁撴灉锛歿shape_type}"
        )
        with open(txt_save_path, 'w', encoding='utf-8') as f:
            f.write(result_content)
        print(f"鉁?璇嗗埆缁撴灉宸蹭繚瀛樿嚦锛歿txt_save_path}")
    except Exception as e:
        print(f"鉂?鍐欏叆缁撴灉鏂囦欢鏃跺嚭閿欙細{str(e)}")

    # 6. 杩斿洖缁撴灉锛歴hapes锛堝吋瀹瑰師浠ｇ爜锛夈€乻hape_type锛堝垎绫荤粨鏋滐級銆乷ut锛堟暟瀛楋級銆乧onf锛堢疆淇″害锛?    print(f"鉁?瑙嗚璇嗗埆瀹屾垚锛氭暟瀛?{out}锛岀疆淇″害={conf:.2f}锛屽垎绫荤粨鏋?{shape_type}")
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


# 鍙栨枡鍧愭爣鐐?AList = [-65.5, -197.9, 133.6]
BList = [-17.5, -148.9, 128.6]
CList = [69.3, -138.1, 130.0]
DList = [-140.0, 65.2, 131.0]

# 鏀炬枡涓績鍧愭爣
one1 = [219.0, 35.0, 142.0]
two2 = [40.6, 225.0, 138.0]

# 寰幆璇诲彇 plc 淇℃伅
while True:
    start = PLC.read('int', 0)
    carryStatu = PLC.read('int', 18)
    visual = PLC.read('bool', 44, 0)
    maduoStart = PLC.read('int', 26)

    # 鍒嗘嫞鎼繍
    if start == 30 and maduoStart == 0 and visual == False:
        print('鎼繍淇″彿', start)
        # 鍒嗘嫞 A
        if carryStatu == 10:
            startPoint = AList
            endPoint = one1
        # 鍒嗘嫞 B
        elif carryStatu == 20:
            startPoint = BList
            endPoint = two2
        # 鍒嗘嫞 C
        elif carryStatu == 30:
            startPoint = CList
            endPoint = DList

        # 鎵ц鎼繍绋嬪簭
        moveSelf.carry(arm, startPoint, endPoint)
        # 瀹屾垚鎼繍绋嬪簭,缁?plc 瀹屾垚淇″彿
        moveEndSignal(PLC)

    elif start == 0 and visual == True:
        time.sleep(1)
        print('瑙嗚璇嗗埆淇″彿', visual)
        shapes, shape_type, out = visualRecognition()
        if shape_type == '濂囨暟':  # 001
            print(shape_type)
            visualSignal.visual(PLC)
            visualSignal.circular(PLC)

        elif shape_type == '鍋舵暟':
            print(shape_type)
            visualSignal.visual(PLC)
            visualSignal.rectangle(PLC)

        elif shape_type == '闆?:
            print(shape_type)
            visualSignal.visual(PLC)
            visualSignal.triangle(PLC)

    # 鍒嗘嫞鍫嗗灈锛堣皟鐢?stackingXYZ 鑾峰彇鍫嗗灈鍧愭爣鐐癸級
    elif start == 30 and maduoStart == 50 and visual == False:
        print('鍒嗘嫞鍫嗗灈淇″彿', maduoStart)
        # xNumOne, yNumOne, zNumOne 闇€瑕佽鍙?plc 鑾峰緱锛屽垎鍒唬琛ㄨ鏁帮紝鍒楁暟锛屽眰鏁?        xNumOne = PLC.read('int', 28)
        yNumOne = PLC.read('int', 30)
        zNumOne = PLC.read('int', 32)
        # xNumTwo, yNumTwo, zNumTwo 闇€瑕佽鍙?plc 鑾峰緱锛屽垎鍒唬琛ㄨ鏁帮紝鍒楁暟锛屽眰鏁?        xNumTwo = PLC.read('int', 34)
        yNumTwo = PLC.read('int', 36)
        zNumTwo = PLC.read('int', 38)

        num1 = xNumOne * yNumOne * zNumOne
        num2 = xNumTwo * yNumTwo * zNumTwo

        # ranks: 1 鏄浼樺厛锛? 鏄垪浼樺厛, order锛? 鏄?Z 娆″簭锛? 鏄?S 娆″簭
        ranks = PLC.read('int', 46)
        order = PLC.read('int', 48)

        # 鍒嗘嫞
        while (num1 >= 0 and maduoStart == 50) or (num2 >= 0 and maduoStart == 50):
            maduoStart = PLC.read('int', 26)
            if maduoStart == 0:
                print('Stop 鍒嗘嫞鍫嗗灈淇″彿', maduoStart)
                break

            carryStatu = PLC.read('int', 18)
            if carryStatu == 10:
                # 纭畾鏀剧墿鍧愭爣鐐?                XYZ = [244.0, -6.8, 141.0]
                xyzList = maduoXYZ.getXYZList(ranks, order, XYZ[0], XYZ[1], XYZ[2], xNumOne, yNumOne, zNumOne)
                xyzList = xyzList[::-1]
                xyz = xyzList[num1 - 1]
                start = PLC.read('int', 0)
                print('AList', AList)
                print('xyz', xyz)

                if start == 30:
                    moveSelf.carry(arm, AList, xyz)
                    # 瀹屾垚鎼繍绋嬪簭,缁?plc 瀹屾垚淇″彿
                    moveEndSignal(PLC)
                    num1 = num1 - 1
                    print('num1', num1)

            # 鍒嗘嫞 B
            elif carryStatu == 20:
                # 纭畾鏀剧墿鍧愭爣鐐?                XYZ = [54.8, 177.3, 139.0]
                xNumOne, yNumOne, zNumOne = 2, 2, 2
                xyzList = maduoXYZ.getXYZList(ranks, order, XYZ[0], XYZ[1], XYZ[2], xNumTwo, yNumTwo, zNumTwo)
                xyzList = xyzList[::-1]
                xyz = xyzList[num2 - 1]
                start = PLC.read('int', 0)
                if start == 30:
                    moveSelf.carry(arm, BList, xyz)
                    # 瀹屾垚鎼繍绋嬪簭,缁?plc 瀹屾垚淇″彿
                    moveEndSignal(PLC)
                    num2 = num2 - 1
                    print('num2', num2)