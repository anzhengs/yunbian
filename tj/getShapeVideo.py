import cv2 as cv
import numpy as np
from realsense_depth import *


class ShapeAnalysis:
    def __init__(self):
        self.shapes = {'triangle': 0, 'rectangle': 0, 'polygons': 0, 'circles': 0}

    def analysis(self, frame):
        # 获取图像高度和宽度以及通道数量
        height = frame.shape[0]
        weight = frame.shape[1]
        channels = frame.shape[2]
        result = np.zeros((height, weight, channels), dtype=np.uint8)

        print("start to detect lines...\n")
        # 函数cvCvtColor实现色彩空间转换,获取灰度图
        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        # 背景为黑色
        # threshold图像的二值化，就是将图像上的像素点的灰度值设置为0或255
        ret, binary = cv.threshold(gray, 170, 255, cv.THRESH_BINARY | cv.THRESH_OTSU)
        binary = cv.medianBlur(binary, 7)


        # findContours()获取图像轮廓
        contours, hierarchy = cv.findContours(binary, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        for cnt in range(len(contours)):
            # 提取与绘制轮廓
            cv.drawContours(result, contours, cnt, (0, 255, 0), 2)

            # 轮廓逼近
            # arcLength计算图像轮廓的周长
            epsilon = 0.028 * cv.arcLength(contours[cnt], True)
            # 多边形拟合曲线
            approx = cv.approxPolyDP(contours[cnt], epsilon, True)

            # 分析几何形状
            corners = len(approx)
            shape_type = ""
            if corners == 3:
                count = self.shapes['triangle']
                count = count + 1
                self.shapes['triangle'] = count
                shape_type = "三角形"
                print("三角形")
            elif corners == 4:
                # print('approx', approx)
                count = self.shapes['rectangle']
                count = count + 1
                self.shapes['rectangle'] = count
                shape_type = "矩形"
                print("矩形")
            elif corners == 6:
                shape_type = "六边形"
                print("六边形")
            elif corners == 10:
                shape_type = "五角星"
                print("五角星")

            elif corners == 8:
                count = self.shapes['circles']
                shape_type = "圆形"
                print("圆形")
            else:
                print(corners)



            # 求解中心位置
            mm = cv.moments(contours[cnt])
            if mm['m00'] != 0:
                cx = int(mm['m10'] / mm['m00'])
                cy = int(mm['m01'] / mm['m00'])
                cv.circle(result, (cx, cy), 3, (0, 0, 255), -1)

                # 颜色分析
                color = frame[cy][cx]
                color_str = "(" + str(color[0]) + ", " + str(color[1]) + ", " + str(color[2]) + ")"

                # 计算面积与周长
                p = cv.arcLength(contours[cnt], True)
                area = cv.contourArea(contours[cnt])
                #print("颜色: %s 形状: %s " % (color_str, shape_type))

        cv.imshow("Analysis Result", self.draw_text_info(result))
        return self.shapes, color_str, shape_type

    def draw_text_info(self, image):
        c1 = self.shapes['triangle']
        c2 = self.shapes['rectangle']
        c3 = self.shapes['polygons']
        c4 = self.shapes['circles']
        cv.putText(image, "triangle: " + str(c1), (10, 20), cv.FONT_HERSHEY_PLAIN, 1.2, (255, 0, 0), 1)
        cv.putText(image, "rectangle: " + str(c2), (10, 40), cv.FONT_HERSHEY_PLAIN, 1.2, (255, 0, 0), 1)
        cv.putText(image, "polygons: " + str(c3), (10, 60), cv.FONT_HERSHEY_PLAIN, 1.2, (255, 0, 0), 1)
        cv.putText(image, "circles: " + str(c4), (10, 80), cv.FONT_HERSHEY_PLAIN, 1.2, (255, 0, 0), 1)
        return image


if __name__ == "__main__":
    # 视频
    dc = DepthCamera()
    ld = ShapeAnalysis()
    while True:
        ret, depth_frame, color_frame = dc.get_frame()
        if ret:
            color_frame_belt = color_frame[178:310, 250:400]
            Denoising_frame = cv.blur(color_frame_belt, (3, 3))
            ld.analysis(Denoising_frame)
            cv.imshow("Denoising_frame:", Denoising_frame)
        key = cv.waitKey(1)
        if key == 27:
            break

    # 图片
    # src = cv.imread("gem_test.png")
    # ld = ShapeAnalysis()
    # ld.analysis(src)
    # cv.imshow('图形', src)
    # cv.waitKey(1000000)