import torch
import torchvision.transforms as transforms
from PIL import Image
from model import MyLeNet
import cv2 as cv
import numpy as np
from realsense_depth import DepthCamera


class ShapeAnalysis:
    def __init__(self):
        self.shapes = {'triangle': 0, 'rectangle': 0, 'polygons': 0, 'circles': 0}

    def analysis(self, frame):
        print("start to detect lines...\n")
        transform = transforms.Compose(
            [transforms.Resize((32, 32)),
            transforms.ToTensor(),
            transforms.Normalize((0.1307), (0.3081))])
        classes = ('0', '1', '2', '3',
                   '4', '5', '6', '7', '8', '9')
        net = MyLeNet()
        net.load_state_dict(torch.load('./MNistLeNet.pth'))
        gray = cv.cvtColor(frame,cv.COLOR_BGR2GRAY)  #灰度化
        ret,binary = cv.threshold(gray, 170, 255, cv.THRESH_BINARY | cv.THRESH_OTSU)  #反二值化
        binary = 255 - binary
        kernel = np.ones((2,2),np.uint8)
        erosion = cv.erode(binary,kernel)  #腐蚀
        kernel = np.ones((10,10),np.uint8)
        frame = cv.dilate(erosion,kernel)  #膨胀
        cv.imwrite('1.jpg',frame)
        frame = Image.open('1.jpg')
        frame = transform(frame)  # [C, H, W]
        frame = torch.unsqueeze(frame, dim=0)  # [N, C, H, W]
        with torch.no_grad():
            outputs = net(frame)
            predict = torch.max(outputs, dim=1)[1].numpy()
            out = classes[int(predict)]
            out = int(out)
            print(out)

            shape_type = ""
            if out == 0:
                count = self.shapes['triangle']
                count = count + 1
                self.shapes['triangle'] = count
                shape_type = "零"
                print("零")
            elif (out % 2) != 0:
                # print('approx', approx)
                count = self.shapes['rectangle']
                count = count + 1
                self.shapes['rectangle'] = count
                shape_type = "奇数"
                print("奇数")
            else:
                count = self.shapes['circles']
                count = count + 1
                self.shapes['circles'] = count
                shape_type = "偶数"
                print("偶数")

        return self.shapes,shape_type



if __name__ == "__main__":
    # 视频
    dc = DepthCamera()
    ld = ShapeAnalysis()
    while True:
        ret, depth_frame, color_frame = dc.get_frame()
        if ret:
            color_frame_belt = color_frame[178:310, 258:400]
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