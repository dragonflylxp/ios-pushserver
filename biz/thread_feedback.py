#!/usr/bin/python2.6
#coding=utf-8
#author lixp@500wan.com 
#edit 2014-08-31 22:57:42

import os
import sys
import time
import redis

APP_PATH=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(APP_PATH,'lib'))
import global_var
from CQueue import MSG, CQueue 
from logger import Log
from apns_conn import ApnsFeedback
from jobs import sched

logger = Log().getLog()

class FeedbackBiz(object):
    def __init__(self, params):
        self.apns_feedback = ApnsFeedback(certfile=params['certfile'],   #apns连接
                                              host=params['host'],
                                              port=params['port'],
                                             retry=params['retry'])   

    def cron_feedback_job(self):
        """feedback定时任务(天级别)
        """
        #清除昨天的黑名单
        global_var.g_feedback_black_list.clear() 
        #获取最新的黑名单
        for token, fail_time in self.apns_feedback.items():
            global_var.g_feedback_black_list.update({token:fail_time})
        logger.info('Token unreachable blacklist! [ TOTAL=%d MEM=%d ]' % \
             (len(global_var.g_feedback_black_list), sys.getsizeof(global_var.g_feedback_black_list)))
            
def test():
    print 'feedback-thread test'

if __name__ == '__main__':
    test()
