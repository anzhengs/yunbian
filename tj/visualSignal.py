from plc_connect import plc_db
import time

PLC = plc_db()

# 连接plc
while True:
    message_plc = 'connect plc ok' if PLC.connect() else 'connect plc fail'
    if message_plc == 'connect plc ok':
        break


def visual(PLC):
    visual = PLC.read('bool', 44, 0)
    print('visual1', visual)
    while visual:
        PLC.write(44, bytearray(b'\x00'))
        visual = PLC.read('bool', 44, 0)
        if visual == False:
            print('visual2', visual)
            break


def rectangle(PLC):
    visualStatuA = PLC.read('bool', 20, 0)
    print('visualStatuA', visualStatuA)
    while visualStatuA == False:
        PLC.write(20, bytearray(b'\x01'))
        visualStatuA = PLC.read('bool', 20, 0)
        if visualStatuA:
            print('visualStatuA', visualStatuA)
            break


def circular(PLC):
    visualStatuB = PLC.read('bool', 20, 1)
    print('visualStatuA', visualStatuB)
    while visualStatuB == False:
        PLC.write(20, bytearray(b'\x02'))
        visualStatuB = PLC.read('bool', 20, 1)
        if visualStatuB:
            print('visualStatuB', visualStatuB)
            break


def triangle(PLC):
    visualStatuC = PLC.read('bool', 20, 2)
    print('visualStatuC', visualStatuC)
    while visualStatuC == False:
        PLC.write(20, bytearray(b'\x04'))
        visualStatuC = PLC.read('bool', 20, 2)
        if visualStatuC:
            print('visualStatuC', visualStatuC)
            break


def visualSetZero0(PLC):
    time.sleep(1)
    visualStatu = PLC.read('bool', 20, 0)
    while visualStatu:
        PLC.write(20, bytearray(b'\x00'))
        zero = PLC.read('bool', 20, 0)
        if zero == False:
            print('visual over single', zero)
            break


def visualSetZero1(PLC):
    time.sleep(1)
    visualStatu = PLC.read('bool', 20, 1)
    while visualStatu:
        PLC.write(20, bytearray(b'\x00'))
        zero = PLC.read('bool', 20, 1)
        if zero == False:
            print('visual over single', zero)
            break


def visualSetZero2(PLC):
    time.sleep(1)
    visualStatu = PLC.read('bool', 20, 2)
    while visualStatu:
        PLC.write(20, bytearray(b'\x00'))
        zero = PLC.read('bool', 20, 2)
        if zero == False:
            print('visual over single', zero)
            break


def test(PLC):
    visual = PLC.read('bool', 44, 0)
    print('visual1', visual)
    while visual:
        PLC.write(44, bytearray(b'\x00'))
        visual = PLC.read('bool', 44, 0)
        if visual == False:
            print('visual2', visual)
            break

    visualStatuC = PLC.read('bool', 20, 2)
    print('visualStatuC', visualStatuC)
    while visualStatuC == False:
        PLC.write(20, bytearray(b'\x04'))
        visualStatuC = PLC.read('bool', 20, 2)
        if visualStatuC:
            print('visualStatuC', visualStatuC)
            break

    time.sleep(1)
    while visualStatuC:
        PLC.write(20, bytearray(b'\x00'))
        C = PLC.read('bool', 20, 2)
        if C == False:
            print('visual over')
            break
