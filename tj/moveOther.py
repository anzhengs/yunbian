import time


def tackUp(arm,tackList):
    # print("提高Z轴")
    arm.p2p_interpolation(tackList[0], tackList[1], 230)

    # print("到达取料块坐标点")
    arm.p2p_interpolation(tackList[0], tackList[1], tackList[2])
    time.sleep(1)


def putDown(arm,tackList, putList):
    # print("提高Z轴")
    arm.p2p_interpolation(tackList[0], tackList[1], 230)

    # print("提高Z轴")
    arm.p2p_interpolation(putList[0], putList[1], 230)

    # print("到达放料块坐标点1")
    arm.p2p_interpolation(putList[0], putList[1], putList[2])
    time.sleep(1)


def goToZero(arm,putList):
    # print("提高Z轴")
    arm.p2p_interpolation(putList[0], putList[1], 230)

    # print("回到零点")
    arm.p2p_interpolation(200, 0, 230, 0, 0, 0)






