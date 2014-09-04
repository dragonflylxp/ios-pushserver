#!/usr/bin/python2.6
#coding=utf-8
#author lixp@500wan.com 
#edit 2014-08-26 20:21:10

import binascii
import json 
import datetime
import time
import struct
import copy
import global_var
from logger import Log

logger = Log().getLog()

class MSG(dict):
    """redis消息"""

    def set_msg_id(self, id):
        self.update({'id' : id})

    def is_msg_expired(self):
        expiry = int(self.get('expiry','0')) 
        return time.time() > expiry > 0

    def is_device_unreachable(self):
        token_text = self.get('token').replace(' ','')
        token_hex  = token_text.encode('utf-8')
        if not token_hex in global_var.g_feedback_black_list:
            return False
        return True

    def apns_pack(self):
        """
        打包，符合APNS要求
        msg_id: int
        expiry: int
        token_text:   unicode
        payload_text: unicode
        """
        msg_id = self.get('id', 0)
        expiry = self.get('expiry')
        if expiry is None:
            future = datetime.datetime.now() + datetime.timedelta(hours=1)
            expiry = int(time.mktime(future.timetuple()))
        
        token_text   = self.get('token').replace(' ','')
        token_hex    = token_text.encode('utf-8')
        token_bin    = binascii.a2b_hex(token_hex)

        payload_dict = self.get('payload')
        payload_text = json.dumps(payload_dict, ensure_ascii=False, separators=(',',':'))
        payload_hex  = payload_text.encode('utf-8')
        payload_len  = len(payload_hex) 
        if payload_len > 256:
            looger.debug('Msg is too big![ LEN=%d ]' % payload_len)
            return None 
        
        fmt  = '!B2IH%dsH%ds' % (len(token_bin), payload_len)
        pack = struct.pack(fmt, 1, msg_id, expiry, len(token_bin), \
                            token_bin, payload_len, payload_hex)
        return pack

    @staticmethod
    def error_response_unpack(error_resp):
        cmd, status, msg_id = struct.unpack('!BBI', error_resp)
        return cmd, status, msg_id

    @staticmethod
    def ushort_big_endian_unpack(bytes):
        return struct.unpack('>H', bytes)[0]

    @staticmethod
    def uint_big_endian_unpack(bytes):
        return struct.unpack('>I', bytes)[0]

    @staticmethod
    def token_unpack(bytes):
        return binascii.b2a_hex(bytes)
    

class CQueue(object):

    """ 循环队列
    --------|-------|--------|---|---------|------
    ...ready|       |   succ | F | resend  | ready...
    --------|-------|--------|---|---------|------
            |       |          |           |
          rear    frontl      fail       frontr
    """
    
    frontl = 0   #取msg发送点
    frontr = 0
    rear   = 0   #新msg插入点
    fail   = 0   #标记失败msg

    size  = 0   #队列最大容量
    data  = []

    def __init__(self, n=1):
        self.size      = n 
        self.clear()

    def clear(self):
        self.frontl    = 0
        self.frontr    = 0
        self.rear      = 0 
        self.fail      = -1 
        self.data      = [None]*self.size 

    def is_empty(self):
        """用frontr判断队列是否为空"""
        return self.rear == self.frontr
    
    def is_full(self):
        """用frontl判断队列是已满"""
        return (self.rear + 1) % self.size == self.frontl
    
    def enqueue(self, msg):
        if self.is_full():
            return -1 
        self.data[self.rear] = copy.copy(msg)
        self.data[self.rear].set_msg_id(self.rear)
        self.rear = (self.rear + 1) % self.size
        return 1

    def dequeue(self):
        if self.is_empty():
            return None
        msg = copy.copy(self.data[self.frontr])
        self.frontr = (self.frontr + 1) % self.size 
        return msg

    def find_fail(self, fail_msg_id):
        t = self.frontl
        while t != self.frontr:
            if self.data[t].get('id') == fail_msg_id:
                self.fail = t
                return 1
            t = (t + 1) % self.size
        return -1 

    def resend_from_fail(self, fail_msg_id):
        """回溯到F点的下一个(丢弃F点)，清除fail标记"""
        if self.find_fail(fail_msg_id) == 1:
            self.frontr = (self.fail + 1) % self.size
            self.remove_succ()
            return 1

        #找不到错误msg时，认为全部发送成功
        self.remove_succ()
        return -1 

    def resend_from_n(self, n=10):
        """回溯n步，清除fail标记"""
        if self.frontl == self.frontr:
            self.remove_succ()
            return -1

        t = self.frontr
        while n>0:
            if t == self.rear:
                t = (t + 1) % self.size
                break;
            t = (t - 1 + self.size) % self.size 
            n -= 1
        self.frontr = t
        self.remove_succ()
        return 1

    def remove_succ(self):
        """清除成功发送的msg"""
        self.frontl = self.frontr
        self.fail   = -1

    def is_trap(self):
        return self.is_empty and self.is_full()

    def get_queue_status(self):
        return 'REAR=%d FRONTL=%d FAIL=%d FRONTR=%d SIZE=%d' \
                % (self.rear, self.frontl, self.fail, self.frontr, self.size)


def test():
    cq  = CQueue(100)
    print cq.is_empty(), cq.is_full()
    msg = MSG(expiry=1, token='abcd', payload='def')     
    for i in range(99):
        msg.set_msg_id(i)
        cq.enqueue(msg)

    print cq.is_empty(), cq.is_full()
    print cq.rear, cq.frontl, cq.fail, cq.frontr

    cq.frontr = 60
    print cq.find_fail(100)
    print cq.find_fail(50)
    
    cq.fail = 30
    print cq.rear, cq.frontl, cq.fail, cq.frontr
    print cq.resend_from_fail(cq.fail)
    print cq.rear, cq.frontl, cq.fail, cq.frontr

    msg = cq.dequeue()
    print msg
    print msg.is_msg_expired()
    print msg.apns_pack()
    
if __name__ == '__main__':
    test()
