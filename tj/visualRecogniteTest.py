import cv2
from realsense_depth import *
from getShapeVideo import *


def d435i_camera():
    # 实例化一个深度相机对象
    dc = DepthCamera()
    while True:
        # 获取深度图像和彩色图像数据,color_frame[640,480]
        ret, depth_frame, color_frame = dc.get_frame()
        if ret:
            # 显示深度图像
            # cv2.imshow("Depth frame:", depth_frame)

            # 像素点坐标
            point = [300, 200]
            # 在彩色图像上画一个半径是4像素，颜色是红色的圆圈，代表点point
            cv2.circle(color_frame, point, 4, (0, 0, 255))
            # 像素是[400，300]这个点的深度数据
            distance = depth_frame[300, 200]
            cv2.putText(color_frame, "{}mm".format(distance), (point[0], point[1] - 20), cv2.FONT_HERSHEY_PLAIN, 2,
                        (0, 0, 0), 2)
            # # 皮带在color_frame中四个点的像素坐标
            # ptRightTop:(640,160)
            # ptLeftBottom:(0,330)
            ptLeftTop = (0, 160)
            ptRightBottom = (640, 330)
            redColor = (0, 0, 255)
            thickness = 1
            lineType = 4
            # 将皮带区域用红色线标记出来
            cv2.rectangle(color_frame, ptLeftTop, ptRightBottom, redColor, thickness, lineType)
            # 显示彩色图像
            # cv2.imshow("Color frame:", color_frame)

            # 将皮带裁减出来
            color_frame_belt = color_frame[160:330, 10:600]
            # 显示皮带的彩色图像
            cv2.imshow("Color frame belt:", color_frame_belt)

            # 对皮带像素内的数据进行识别
            # 对黑色皮带部分图像做滤波操作，去除噪音
            Denoising_frame = cv2.blur(color_frame_belt, (5, 5))
            cv2.imshow("Denoising_frame:", Denoising_frame)

            key = cv2.waitKey(1)
            if key == 27:
                break


if __name__ == '__main__':
    d435i_camera()
