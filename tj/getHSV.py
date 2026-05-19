import cv2
import numpy as np
from realsense_depth import *
from matplotlib import pyplot as plt
dc = DepthCamera()
ret, depth_frame, image = dc.get_frame()  # 读取深度相机彩色图和深度图
# image = cv2.imread('hsv.png')
HSV = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)


def getpos(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:  # 定义一个鼠标左键按下去的事件
        print(HSV[y, x])


cv2.imshow("imageHSV", HSV)
cv2.imshow('image', image)
cv2.setMouseCallback("imageHSV", getpos)
cv2.waitKey(0)
