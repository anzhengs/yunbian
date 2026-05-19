import time


def carry(arm,tackList, putList):
    # print("提高Z轴")
    arm.p2p_interpolation(tackList[0], tackList[1], 230)

    # print("到达取料块坐标点")
    arm.p2p_interpolation(tackList[0], tackList[1], tackList[2])

    # print("气泵开启-吸气")
    time.sleep(1)
    arm.pump_suction()


    # print("提高Z轴")
    arm.p2p_interpolation(tackList[0], tackList[1], 230)

    # print("提高Z轴")
    arm.p2p_interpolation(putList[0], putList[1], 230)

    # print("到达放料块坐标点1")
    arm.p2p_interpolation(putList[0], putList[1], putList[2])

    # print("气泵关闭")
    time.sleep(1)
    arm.pump_off()
    time.sleep(1)

    # print("提高Z轴")
    arm.p2p_interpolation(putList[0], putList[1], 230)

    # print("回到零点")
    arm.p2p_interpolation(200, 0, 230)
    time.sleep(2)

def test(arm,tackList, putList):
    # print("提高Z轴")
    arm.p2p_interpolation(tackList[0], tackList[1], 230)

    # print("到达取料块坐标点")
    arm.p2p_interpolation(tackList[0], tackList[1], tackList[2])

    # print("提高Z轴")
    arm.p2p_interpolation(tackList[0], tackList[1], 230)

    # print("提高Z轴")
    arm.p2p_interpolation(putList[0], putList[1], 230)

    # print("到达放料块坐标点1")
    arm.p2p_interpolation(putList[0], putList[1], putList[2])

    # print("提高Z轴")
    arm.p2p_interpolation(putList[0], putList[1], 230)

    # print("回到零点")
    time.sleep(2)




