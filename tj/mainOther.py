import time
from plc_connect import plc_db
from wlkata_mirobot import WlkataMirobot
import moveOther
import maduoXYZ
from getShapeVideo import ShapeAnalysis
from realsense_depth import *
import cv2 as cv
import visualSignal

# 实例化arm对象
arm = WlkataMirobot()
# 机械臂初始化（必须）
arm.home()
# 实例化PLC对象
PLC = plc_db()

# 连接plc
while True:
    message_plc = 'connect plc ok' if PLC.connect() else 'connect plc fail'
    if message_plc == 'connect plc ok':
        break


# 视觉识别
def visualRecognition():
    dc = DepthCamera()
    ld = ShapeAnalysis()
    ret, depth_frame, color_frame = dc.get_frame()
    if ret:
        color_frame_belt = color_frame[198:310, 200:500]
        Denoising_frame = cv.blur(color_frame_belt, (3, 3))
        shapes, color_str, shape_type = ld.analysis(Denoising_frame)
        cv.imshow("color_frame_belt:", color_frame_belt)
        cv.waitKey(10)
        return color_frame_belt, color_str, shape_type


# 取料坐标点
AList = [-65.5, -197.9, 133.6]
BList = [-17.5, -148.9, 128.6]
CList = [69.3, -138.1, 130.0]
DList = [-140.0, 65.2, 131.0]

# 放料中心坐标
one1 = [219.0, 35.0, 142.0]
two2 = [40.6, 225.0, 138.0]


def move(PLC, arm, startPoint, endPoint):
    # 移动到取物体点
    moveOther.tackUp(arm, startPoint)
    # 读24序号的值
    pumpOn = PLC.read('bool', 24, 0)
    print('pumpOn1', pumpOn)
    time.sleep(1)
    if pumpOn == False:
        print('pumpOn2', pumpOn)
        # 控制吸泵开，将24数据改成True
        PLC.write(24, bytearray(b'\x01'))
        time.sleep(1)
        pumpOn = PLC.read('bool', 24)
        time.sleep(1)
        if pumpOn == True:
            print('pumpOn3', pumpOn)
            # 拿取物体后，移动到放物体点
            moveOther.putDown(arm, startPoint, endPoint)
            time.sleep(1)

            # 控制吸泵关，将24数据改成False
            PLC.write(24, bytearray(b'\x00'))
            time.sleep(1)
            pumpOn = PLC.read('bool', 24)
            time.sleep(1)
            if pumpOn == False:
                print('pumpOn4', pumpOn)
                # 回到初始点
                moveOther.goToZero(arm, endPoint)
                # 写入完成信号
                end = PLC.read('int', 2)
                while end == 0:
                    PLC.write(2, bytearray(b'\x00\n'))
                    end = PLC.read('int', 2)
                    if end == 10:
                        break
                time.sleep(1)
                PLC.write(2, bytearray(b'\x00\x00'))
    time.sleep(1)


# 主程序循环读取plc信号
while True:
    start = PLC.read('int', 0)
    carryStatu = PLC.read('int', 18)
    visual = PLC.read('bool', 44, 0)
    maduoStart = PLC.read('int', 26)

    # 分拣-搬运
    if start == 30 and maduoStart == 0 and visual == False:
        print('搬运信号', start)
        # 分拣A
        if carryStatu == 10:
            startPoint = AList
            endPoint = one1
        # 分拣B
        elif carryStatu == 20:
            startPoint = BList
            endPoint = two2
        # 分拣C
        elif carryStatu == 30:
            startPoint = CList
            endPoint = DList

        # 执行搬运程序
        move(PLC, arm, startPoint, endPoint)

    # 视觉处理
    elif start == 0 and visual is True:
        print('视觉识别信号', visual)
        color_frame_belt, color_str, shape_type = visualRecognition()
        if shape_type == '三角形':
            print(shape_type)
            visualSignal.visual(PLC)
            visualSignal.triangle(PLC)

        elif shape_type == '圆形':
            print(shape_type)
            visualSignal.visual(PLC)
            visualSignal.circular(PLC)

        elif shape_type == '矩形':
            print(shape_type)
            visualSignal.visual(PLC)
            visualSignal.rectangle(PLC)

    # 分拣堆垛（调用stackingXYZ获取堆垛坐标点）
    elif start == 30 and maduoStart == 50 and visual is False:
        print('分拣堆垛信号', maduoStart)
        # xNumOne, yNumOne, zNumOne 需要读取plc获得，分别代表行数，列数，层数
        xNumOne = PLC.read('int', 28)
        yNumOne = PLC.read('int', 30)
        zNumOne = PLC.read('int', 32)
        # xNumTwo, yNumTwo, zNumTwo 需要读取plc获得，分别代表行数，列数，层数
        xNumTwo = PLC.read('int', 34)
        yNumTwo = PLC.read('int', 36)
        zNumTwo = PLC.read('int', 38)

        num1 = xNumOne * yNumOne * zNumOne
        num2 = xNumTwo * yNumTwo * zNumTwo

        # ranks: 1是行优先，2是列优先, order：1是Z次序，2是S次序
        ranks = PLC.read('int', 46)
        order = PLC.read('int', 48)

        # 分拣
        while (num1 > 0 or num2 > 0) and maduoStart == 50:
            maduoStart = PLC.read('int', 26)
            if maduoStart == 0:
                print('Stop 分拣堆垛信号', maduoStart)
                break

            carryStatu = PLC.read('int', 18)
            if carryStatu == 10:
                # 确定放物坐标点
                XYZ = [244.0, -6.8, 140.0]
                coordsList = maduoXYZ.getXYZList(ranks, order, XYZ[0], XYZ[1], XYZ[2], xNumOne, yNumOne, zNumOne)
                xyzListA = coordsList[::-1]
                xyz = xyzListA[num1 - 1]
                start = PLC.read('int', 0)
                if start == 30:
                    print('one', xyz)
                    move(PLC, arm, AList, xyz)
                    num1 = num1 - 1
                    print('num1', num1)

            # 分拣B
            elif carryStatu == 20:
                # 确定放物坐标点
                XYZ = [54.8, 177.3, 138.0]
                coordsList = maduoXYZ.getXYZList(ranks, order, XYZ[0], XYZ[1], XYZ[2], xNumTwo, yNumTwo, zNumTwo)
                xyzListB = coordsList[::-1]
                xyz = xyzListB[num2 - 1]
                start = PLC.read('int', 0)
                if start == 30:
                    print('two', xyz)
                    move(PLC, arm, BList, xyz)
                    num2 = num2 - 1
                    print('num2', num2)
