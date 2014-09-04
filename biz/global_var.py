#coding:utf-8
import os,sys
import threading
import copy

sys.path.append(os.path.join( os.path.dirname( \
    os.path.dirname(os.path.abspath(__file__))),'lib'))
import CQueue

#全局消息队列
g_cqueue_msg_list = []

#全局队列锁
g_cqueue_mutex_list = []

#feedback黑名单
g_feedback_black_list = {}

#全局变量配置
g_vars = {}

def set_up(confs):
    global g_cqueue_msg_list
    for i in range(confs['max_worker_num']):
    	g_cqueue_msg_list.append(CQueue.CQueue(confs['max_queue_size']))

    global g_cqueue_mutex_list
    for i in range(confs['max_worker_num']):
    	g_cqueue_mutex_list.append(threading.RLock())
    
    global g_vars
    g_vars = copy.copy(confs) 
    
