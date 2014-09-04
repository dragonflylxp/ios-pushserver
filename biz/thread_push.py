#!/usr/bin/python2.6
#coding=utf-8
#author lixp@500wan.com 
#edit 2014-08-30 07:30:35

import os
import sys
import time
import select
from threading import Thread

APP_PATH=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(APP_PATH,'lib'))
from CQueue import MSG, CQueue 
from logger import Log
from apns_conn import ApnsGateway
import global_var

logger = Log().getLog()

class PushThread(Thread):
    def __init__(self, params):
        Thread.__init__(self)
        self.tid          = params['tid']                              #work线程id
        self.apns_gateway = ApnsGateway(certfile=params['certfile'],   #apns连接
                                            host=params['host'],
                                            port=params['port'],
                                           retry=params['retry'])   

    def run(self):
        while 1:
            #创建一个apns连接
            ssl_sock = self.apns_gateway.connection()

            #阻塞等待IO事件
            if ssl_sock:
                r, w, e = select.select([ssl_sock],[ssl_sock],[])
                if len(r) > 0:
                    self.read_handler()
   
                if len(w) > 0:#必要时，可设置发送缓冲区低水位标记  
                    self.write_handler()


    def read_handler(self):
        resp = self.apns_gateway.recv_resp()
        if len(resp) > 0: 
            cmd, status, identifier = MSG.error_response_unpack(resp)
            logger.debug('RCVD message from APNS![ CMD=%d STATUS=%d IDENTIFIER=%d]' % (cmd, status, identifier))

            #加锁与回溯，阻塞锁仅与redis线程竞争
            global_var.g_cqueue_mutex_list[self.tid].acquire()
            global_var.g_cqueue_msg_list[self.tid].resend_from_fail(identifier)
            global_var.g_cqueue_mutex_list[self.tid].release()

            #重建连接
            self.apns_gateway._reconnect()
        else:  # apns断开TCP连接或其他异常
            logger.info('The connection pipe broken by apns, reconnect!')
            global_var.g_cqueue_mutex_list[self.tid].acquire()
            global_var.g_cqueue_msg_list[self.tid].resend_from_n(global_var.g_vars['apns_resend_default'])
            global_var.g_cqueue_mutex_list[self.tid].release()
            self.apns_gateway._reconnect()

    def write_handler(self):
        global_var.g_cqueue_mutex_list[self.tid].acquire()
        msg = global_var.g_cqueue_msg_list[self.tid].dequeue() 
        if msg:
            pack = msg.apns_pack()
            if pack:
                logger.debug('Worker send a msg![ QID=%d MID=%d ]' % (self.tid, msg['id']))
                self.apns_gateway.send_msg(pack)
        else:
            status = global_var.g_cqueue_msg_list[self.tid].get_queue_status()
            logger.info('No msg to send![ QID=%d STATUS:%s ]' % (self.tid, status))

            # 队列为空,可能被待确定的msg占满
            istrap = global_var.g_cqueue_msg_list[self.tid].is_trap()      
            if istrap:
                #阻塞等待error_resp,若没有就手动清除队列
                ssl_sock = self.apns_gateway.connection()
                r, w, e  = select.select([ssl_sock],[],[],global_var.g_vars['apns_slp_time'])
                if len(r) > 0:
                    self.read_handler()
                else:
                    global_var.g_cqueue_msg_list[self.tid].remove_succ()
            else:
                #速度控制sleep
                time.sleep(global_var.g_vars['apns_ctl_time']) 
        global_var.g_cqueue_mutex_list[self.tid].release()
            
def test():
    print 'push-thread test'

if __name__ == '__main__':
    test()
