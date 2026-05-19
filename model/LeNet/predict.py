#coding=utf-8
from lenet5 import *
import numpy as np
import os
import cv2
from PIL import Image
import matplotlib.pyplot as plt
import argparse  # 引入参数解析库

# 指定使用 GPU 0（原代码注释有误，已修正格式）
# os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
# 请确认这里的 log 路径是你存放 checkpoint (模型权重) 的真实路径
# 如果之前是在 log2 训练的，请改为 log2
log = '/home/sazuser/401_tensorflow/online-vision/model/LeNet/log/'

def load_image(image_path):
    # 读取图片
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"无法找到图片: {image_path}，请检查路径是否正确。")
        
    # 1. 调整尺寸为 28x28
    image = cv2.resize(image, (28, 28), interpolation=cv2.INTER_AREA)
    # 2. 转为灰度图
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 3. 核心处理：转为严格的白底黑字
    # 3.1 计算图像整体亮度，判断背景是亮还是暗
    # 计算平均像素值（0=黑，255=白）
    mean_brightness = np.mean(gray_image)
    # 3.2 二值化（将图像转为纯黑纯白）
    # 使用Otsu自动阈值，适合大多数场景
    _, binary_image = cv2.threshold(
        gray_image, 
        0, 
        255, 
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    
    # 3.3 确保背景为白色，文字为黑色
    # 如果平均亮度 < 128，说明原始背景偏暗（黑底），需要反转颜色
    if mean_brightness < 128:
        binary_image = cv2.bitwise_not(binary_image)
    
    # 3.4 膨胀处理，让笔画更清晰
    kernel = np.ones((2, 2), np.uint8)  # 修正为uint8（OpenCV要求）
    dilated_image = cv2.dilate(binary_image, kernel)
    
    # 3.5 归一化到 0-1 范围（模型输入要求）
    normalized_image = dilated_image / 255.0
    
    # 3.6 展平为 (1, 784)
    flattened_image = np.reshape(normalized_image, (1, 784))
    
    return image, gray_image, binary_image, normalized_image, flattened_image

if __name__ == "__main__":
    # 1. 设置参数解析
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="输入图片路径")
    parser.add_argument("--output", required=True, help="结果输出路径")
    args = parser.parse_args()

    # 2. 准备模型结构
    # 注意：这里调用 lenet5(0) 会构建图结构，确保 lenet5.py 里的下载数据代码已经移入 if __name__ 块中
    train_step, x, y_true, h_fc3, accuracy, loss, learning_rate = lenet5(0)

    # 3. 启动 Session 并加载权重
    sess = tf.Session()
    saver = tf.train.Saver()
    
    # 检查模型是否存在
    ckpt = tf.train.get_checkpoint_state(log)
    if ckpt and ckpt.model_checkpoint_path:
        saver.restore(sess, ckpt.model_checkpoint_path)
        print("模型加载成功！")
    else:
        print(f"错误：在路径 {log} 未找到模型权重文件！")
        exit(1)

    # 4. 加载图片并预测
    try:
        _, _, _, _, image3 = load_image(args.input)
    except Exception as e:
        print(e)
        exit(1)

    # 运行预测
    raw_output = sess.run([h_fc3], feed_dict={x: image3})
    
    # 获取最终数字结果
    prediction_num = np.argmax(raw_output) 
    print(f"Raw Output: {raw_output}")
    print(f"识别结果: {prediction_num}")

    # 5. 奇偶分类逻辑
    if prediction_num % 2 == 0:
        parity_result = "偶数"
    elif prediction_num == 0:
        parity_result = "零"
    else:
        parity_result = "奇数"
    

    print(f"分类结果: {parity_result}")

    # 6. 保存结果到 TXT
    content = f"识别的结果：{prediction_num}\n分类结果：{parity_result}"
    
    try:
        # 使用 utf-8 编码防止中文乱码
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"结果已保存至: {args.output}")
    except Exception as e:
        print(f"保存文件失败: {e}")

    sess.close()