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
log = '/home/yunbian/online-vision/model/LeNet/log/'

def load_image(image_path):
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"无法找到图片: {image_path}，请检查路径是否正确。")

    # 1. 灰度
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 2. 去噪 + 对比度增强
    gray_blur = cv2.GaussianBlur(gray_image, (3, 3), 0)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
    gray_enhanced = clahe.apply(gray_blur)

    # 3. 自适应二值化：黑字变白字，背景变黑底
    min_side = min(gray_enhanced.shape[:2])
    block_size = max(11, min(31, (min_side // 4) * 2 + 1))

    binary_image = cv2.adaptiveThreshold(
        gray_enhanced,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        block_size,
        8
    )

    # 4. 去小噪声，轻微加粗笔画
    kernel = np.ones((2, 2), np.uint8)
    binary_image = cv2.morphologyEx(binary_image, cv2.MORPH_OPEN, kernel, iterations=1)
    binary_image = cv2.dilate(binary_image, kernel, iterations=1)

    # 5. 清掉最外圈，防止图像边缘进入识别
    H, W = binary_image.shape
    border = 4
    binary_image[:border, :] = 0
    binary_image[-border:, :] = 0
    binary_image[:, :border] = 0
    binary_image[:, -border:] = 0

    # 6. 用连通域代替 findContours 直接按面积排序
    # 核心：优先选择靠近图像中心、面积合理、不是边框线的区域
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        binary_image,
        connectivity=8
    )

    candidates = []
    img_area = H * W

    for i in range(1, num_labels):
        x0 = stats[i, cv2.CC_STAT_LEFT]
        y0 = stats[i, cv2.CC_STAT_TOP]
        w0 = stats[i, cv2.CC_STAT_WIDTH]
        h0 = stats[i, cv2.CC_STAT_HEIGHT]
        area = stats[i, cv2.CC_STAT_AREA]

        box_area = w0 * h0
        if area < 20:
            continue

        # 过滤过大的纸张边框、阴影块
        if box_area > 0.45 * img_area:
            continue

        # 过滤横向边框线
        if w0 > 0.35 * W and h0 < 0.10 * H:
            continue

        # 过滤纵向边框线
        if h0 > 0.35 * H and w0 < 0.025 * W:
            continue

        # 过滤贴边的大块干扰
        if (x0 <= 3 or y0 <= 3 or x0 + w0 >= W - 3 or y0 + h0 >= H - 3) and area > 0.08 * img_area:
            continue

        cx, cy = centroids[i]
        center_dist = ((cx - W / 2.0) / W) ** 2 + ((cy - H / 2.0) / H) ** 2

        # 面积越大、越靠近中心，分数越高
        # 这样可以避免把纸张底部横线当成数字
        score = area * np.exp(-6.0 * center_dist)

        candidates.append((score, i, x0, y0, w0, h0, area))

    if candidates:
        candidates = sorted(candidates, key=lambda t: t[0], reverse=True)

        # 只取分数最高的连通域作为数字主体
        # 这是为了避免把纸张边框、小横线一起裁进去
        _, best_i, x0, y0, w0, h0, area = candidates[0]

        mask = np.zeros_like(binary_image)
        mask[labels == best_i] = 255

        # 对主体区域裁剪
        ys, xs = np.where(mask > 0)
        x, y, w, h = cv2.boundingRect(np.column_stack((xs, ys)).astype(np.int32))

        margin = max(4, int(0.20 * max(w, h)))
        x = max(0, x - margin)
        y = max(0, y - margin)
        w = min(W - x, w + 2 * margin)
        h = min(H - y, h + 2 * margin)

        digit = mask[y:y + h, x:x + w]
    else:
        digit = np.zeros((20, 20), dtype=np.uint8)

    # 7. 等比缩放到 20x20，再 pad 到 28x28
    h, w = digit.shape
    if h == 0 or w == 0:
        resized = np.zeros((20, 20), dtype=np.uint8)
    else:
        scale = 20.0 / max(h, w)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        resized = cv2.resize(digit, (new_w, new_h), interpolation=cv2.INTER_AREA)

    canvas = np.zeros((28, 28), dtype=np.uint8)
    pad_x = (28 - resized.shape[1]) // 2
    pad_y = (28 - resized.shape[0]) // 2
    canvas[pad_y:pad_y + resized.shape[0], pad_x:pad_x + resized.shape[1]] = resized

    # 8. 按重心居中
    m = cv2.moments(canvas)
    if m["m00"] != 0:
        cx = m["m10"] / m["m00"]
        cy = m["m01"] / m["m00"]
        shift_x = 14 - cx
        shift_y = 14 - cy
        M = np.float32([[1, 0, shift_x], [0, 1, shift_y]])
        canvas = cv2.warpAffine(canvas, M, (28, 28), flags=cv2.INTER_LINEAR, borderValue=0)

    normalized_image = canvas.astype(np.float32) / 255.0
    flattened_image = np.reshape(normalized_image, (1, 784))

    return image, gray_image, binary_image, normalized_image, flattened_image

def correct_by_shape(image28, prediction_num, confidence):
    """
    对低置信度结果做轻量几何修正。
    不替代模型，只在模型明显不确定时修正 1 和 0。
    """

    img = (image28 * 255).astype(np.uint8)

    _, bin_img = cv2.threshold(img, 30, 255, cv2.THRESH_BINARY)

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        bin_img,
        connectivity=8
    )

    if num_labels <= 1:
        return prediction_num, confidence, False

    # 找最大连通域
    areas = stats[1:, cv2.CC_STAT_AREA]
    best_i = 1 + int(np.argmax(areas))

    x = stats[best_i, cv2.CC_STAT_LEFT]
    y = stats[best_i, cv2.CC_STAT_TOP]
    w = stats[best_i, cv2.CC_STAT_WIDTH]
    h = stats[best_i, cv2.CC_STAT_HEIGHT]
    area = stats[best_i, cv2.CC_STAT_AREA]

    aspect = w / (h + 1e-6)
    fill_ratio = area / (w * h + 1e-6)

    corrected = False

    # 规则1：细长竖线，低置信度时优先判为 1
    # 解决 1 被误识别成 2、7、9 的情况
    if confidence < 0.85:
        if h >= 14 and aspect < 0.45 and fill_ratio < 0.55:
            prediction_num = 1
            corrected = True

    # 规则2：近似圆形，且模型低置信度时，优先判为 0
    # 解决现场圆形/0 被识别成 8 的情况
    if confidence < 0.75:
        contours, _ = cv2.findContours(bin_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            c = max(contours, key=cv2.contourArea)
            contour_area = cv2.contourArea(c)
            perimeter = cv2.arcLength(c, True)

            if perimeter > 0:
                circularity = 4.0 * np.pi * contour_area / (perimeter * perimeter + 1e-6)
            else:
                circularity = 0

            if 0.65 <= aspect <= 1.35 and circularity > 0.55 and w >= 12 and h >= 12:
                prediction_num = 0
                corrected = True

    return prediction_num, confidence, corrected

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
        _, _, _, image28, image3 = load_image(args.input)
    except Exception as e:
        print(e)
        exit(1)

    # 运行预测
    logits = sess.run(h_fc3, feed_dict={x: image3})[0]

    # 如果 h_fc3 已经是 softmax，直接用；否则做一次 softmax
    if np.all(logits >= 0) and abs(np.sum(logits) - 1.0) < 1e-3:
        probs = logits
    else:
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / np.sum(exp_logits)

    prediction_num = int(np.argmax(probs))
    confidence = float(probs[prediction_num])
    
    prediction_num, confidence, corrected = correct_by_shape(
        image28,
        prediction_num,
        confidence
    )

    print(f"Raw Output: {logits}")
    print(f"Prob: {probs}")
    print(f"识别结果: {prediction_num}")
    print(f"置信度: {confidence:.4f}")

    if corrected:
        print(f"已进行低置信度几何修正，最终结果: {prediction_num}")

    # 5. 奇偶分类逻辑
    if prediction_num == 0:
        parity_result = "零"
    elif prediction_num % 2 == 0:
        parity_result = "偶数"
    else:
        parity_result = "奇数"

    print(f"分类结果: {parity_result}")

    # 6. 保存结果到 TXT
    content = (
        f"识别的结果：{prediction_num}\n"
        f"置信度为：{confidence:.4f}\n"
        f"分类结果：{parity_result}"
    )

    try:
        output_path = os.path.abspath(args.output)
        output_dir = os.path.dirname(output_path)

        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        if os.path.exists(output_path):
            print(f"结果已保存至: {output_path}")
        else:
            raise RuntimeError(f"结果文件写入后仍不存在: {output_path}")

    except Exception as e:
        print(f"保存文件失败: {e}")
        sess.close()
        exit(1)

    sess.close()