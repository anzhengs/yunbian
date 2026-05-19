import time
from plc_connect import plc_db
from wlkata_mirobot import WlkataMirobot
import moveSelf
import moveOther
import maduoXYZ
from getShapeVideo import ShapeAnalysis
from realsense_depth import *
import cv2 as cv




# # 创建机械臂
# arm = WlkataMirobot(portname='/dev/ttyUSB0')
# # 机械臂初始化（必须）
# arm.home()


def moveTest(arm):
    AList = [-65.4, -199.6, 132.0]
    one1 = [219.0, 35.0, 149.0]
    moveSelf.test(arm, AList, one1)

    # AList = [-65.4, -199.6, 132.0]
    # BList = [-16.5, -150.0, 130.0]
    # CList = [73.6, -132.6, 135.0]
    # DList = [-140.0, 65.2, 134.0]
    # twoList = [40.6, 225.0, 150.0]

    # one1 = [219.0, 35.0, 149.0]
    # oneTop = [220.0, 35.0, 170.0]
    # oneLift1 = [248.0, 10.0, 150.0]
    # oneRight1 = [190.0, 60.0, 148.0]

    # oneLift2 =  [273.0, 35.0, 150.0]
    # one2 =      [244.0, 60.0, 149.0]
    # oneRight2 = [215.0, 85.0, 148.0]

    # x-29, y-25, z-20

def maduo():
    xyzList = maduoXYZ.z_row(248.0, -5.0, 143.0, 2, 2, 2)
    print(xyzList)
    xyzList = xyzList[::-1]
    print(xyzList)
    # AList = [-65.4, -199.6, 132.0]
    # AList = [-68.3, -198.9, 132.7]
    # for xyz in xyzList:
    #     print(xyz)
    #     # moveSelf.carry(arm, AList, xyz)
    #     time.sleep(1)
# maduo()

def visualRecognition():
    while True:
        dc = DepthCamera()
        ld = ShapeAnalysis()
        ret, depth_frame, color_frame = dc.get_frame()

        color_frame_belt = color_frame[160:330, 10:600]
        shapes, color_str, shape_type = ld.analysis(color_frame_belt)
        cv.imshow("color_frame_belt:", color_frame_belt)
        # cv.waitKey(100000)
        # cv2.imshow('img', img)
        key = cv.waitKey(0) & 0xff
        if key == ord(' '):
            return color_frame_belt, color_str, shape_type
            break

# color_frame_belt, color_str, shape_type = visualRecognition()
# print(color_str,shape_type)


