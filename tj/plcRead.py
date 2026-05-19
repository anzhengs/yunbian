from plc_connect import plc_db
import time
PLC = plc_db()

# 连接plc
while True:
    message_plc = 'connect plc ok' if PLC.connect() else 'connect plc fail'
    if message_plc == 'connect plc ok':
        break

def whileRead(PLC):

    start = PLC.read('int', 0)
    carryStatu = PLC.read('int', 18)
    visual = PLC.read('bool', 44, 0)
    print(visual)

    xNumOne = PLC.read('int', 28)
    yNumOne = PLC.read('int', 30)
    zNumOne = PLC.read('int', 32)
    print('xNumOne', xNumOne)
    print('yNumOne', yNumOne)
    print('zNumOne', zNumOne)

    xNumTwo = PLC.read('int', 34)
    yNumTwo = PLC.read('int', 36)
    zNumTwo = PLC.read('int', 38)
    print('xNumTwo', xNumTwo)
    print('yNumTwo', yNumTwo)
    print('zNumTwo', zNumTwo)
whileRead(PLC)
# 视觉处理判断完成信号是否成功写入plc
def isWriteSorting(PLC):
    for i in range(0, 3):
        boolNum = PLC.read('bool', 20, i)
        print(boolNum)
    # 001
    PLC.write(20, bytearray(b'\x01'))
    time.sleep(4)
    PLC.write(20, bytearray(b'\x00'))

    # 010
    PLC.write(20, bytearray(b'\x02'))
    time.sleep(4)
    PLC.write(20, bytearray(b'\x00'))

    # 100
    PLC.write(20, bytearray(b'\x04'))
    time.sleep(4)
    PLC.write(20, bytearray(b'\x00'))

def pumn(PLC):
    # open
    PLC.write(24, bytearray(b'\x01'))
    # time.sleep(10)

    # close
    PLC.write(24, bytearray(b'\x00'))

pumn(PLC)