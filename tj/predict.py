#预测
import torch
import torchvision.transforms as transforms
from PIL import Image
from model import  MyLeNet
import matplotlib.pyplot as plt
import cv2
import numpy as np

def main():
    transform = transforms.Compose(
        [transforms.Resize((32, 32)),
         transforms.ToTensor(),
         transforms.Normalize((0.1307), (0.3081))])
    classes = ('0', '1', '2', '3',
               '4', '5', '6', '7', '8', '9')
    net = MyLeNet()
    net.load_state_dict(torch.load('MNistLeNet.pth'))
    im = cv2.imread('9.jpg')
    im_gray = cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)  #灰度化
    ret,binary = cv2.threshold(im_gray,125,255,cv2.THRESH_BINARY_INV)  #反二值化
    kernel = np.ones((10,10),np.uint8)
    erosion = cv2.erode(binary,kernel)  #腐蚀
    kernel = np.ones((100,100),np.uint8)
    im = cv2.dilate(erosion,kernel)  #膨胀
    cv2.imwrite('im.jpg',im)
    plt.imshow(im)
    plt.show()
    im = Image.open('im.jpg')     
    im = transform(im)  # [C, H, W]
    im = torch.unsqueeze(im, dim=0)  # [N, C, H, W]
    with torch.no_grad():
        outputs = net(im)
        predict = torch.max(outputs, dim=1)[1].numpy()
        out = classes[int(predict)]
        out = int(out)
        print(out)
        if out == 0:
            print("零")
        elif (out%2) == 0:
            print("偶数")
        else:
            print("奇数")
            
if __name__ == '__main__':
    main()