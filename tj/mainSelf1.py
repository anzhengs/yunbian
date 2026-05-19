import time
from plc_connect import plc_db
from wlkata_mirobot import WlkataMirobot
import moveSelf
import maduoXYZ
from getShapeVideo1 import ShapeAnalysis
from realsense_depth import *
import cv2 as cv
import visualSignal

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


def visualRecognition():
    time.sleep(2)
    dc = DepthCamera()
    ld = ShapeAnalysis()
    ret, depth_frame, color_frame = dc.get_frame()
    if ret:
        color_frame_belt = color_frame[178:310, 258:400]
        # Denoising_frame = cv.blur(color_frame_belt, (3, 3))
        shape_type = ld.analysis(color_frame_belt)
        cv.imshow("color_frame_belt:", color_frame_belt)
        cv.waitKey(100)
        return shape_type


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
        color_frame_belt, shape_type = visualRecognition()
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

    # 分拣堆垛（调用 stackingXYZ 获取堆垛坐标点）
    elif start == 30 and maduoStart == 50 and visual == False:
        print('分拣堆垛信号', maduoStart)
        # xNumOne, yNumOne, zNumOne 需要读取 plc 获得，分别代表行数，列数，层数
        xNumOne = PLC.read('int', 28)
        yNumOne = PLC.read('int', 30)
        zNumOne = PLC.read('int', 32)
        # xNumTwo, yNumTwo, zNumTwo 需要读取 plc 获得，分别代表行数，列数，层数
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