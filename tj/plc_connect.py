# 导入链接plc模块
import snap7
from snap7.util import *


class plc_db():
    # 定义初始参数 key parameter for init ----------------
    def __init__(self, plc_address='192.168.40.106', db_number=14, db_read_start=0, db_read_size=50, db_read_number=0):
        self.plc_address = plc_address
        self.db_number = db_number
        self.db_read_start = db_read_start
        self.db_read_size = db_read_size
        self.db_read_number = db_read_number
        
        
    # 创建连接 create connection-----------------------   
    def connect(self): 
        self.plc = snap7.client.Client()
        try:
            self.plc.connect('192.168.40.106', 0, 1)
        except:
            return False
        else:
            return True
        
        
    # 取消连接 disconnect        
    def disconnect(self):
        if hasattr(self, 'plc'):
            self.plc.disconnect()
        
    # 读取plc的db数据块 read
    def read(self, dataType, orderNumber, boolIndex=0):
        self.readData = self.plc.db_read(self.db_number, self.db_read_start, self.db_read_size)
        if dataType == 'int':
            return snap7.util.get_int(self.readData, orderNumber)
        if dataType == 'real':
            return snap7.util.get_real(self.readData, orderNumber)
        if dataType == 'bool':
#             print(boolNum[0])
            return snap7.util.get_bool(self.readData, orderNumber, boolIndex)
        

    # 写入plc数据 write
    def write(self, orderNumber, db_write_bytearray):
        self.plc.db_write(self.db_number, orderNumber, db_write_bytearray)
        
#         # \x00\x14  is 20
#         # \x00\x00  is 0
#         # \x00\n    is 10
#         plc.db_write(14,2,bytearray(b'\x00\n'))
