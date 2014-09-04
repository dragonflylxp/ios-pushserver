#!/usr/bin/python2.6
#coding=utf-8
#author lixp@500wan.com 
#edit 2014-08-29 10:47:23

import os
import sys
import time
import json
import redis
from threading import Thread

APP_PATH=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(APP_PATH,'lib'))
from CQueue import MSG, CQueue 
from logger import Log
import global_var

logger = Log().getLog()

class RedisThread(Thread):
    def __init__(self, params):
        Thread.__init__(self)
        self.r_key     = params['key']
        self.r_timeout = params['timeout'] 
        self.r_client  = redis.StrictRedis(params['host'], params['port'], params['db'])
    
    def run(self):
        message = None
        while 1:
            #轮询所有消息队列
            changed = False
            for i in range(global_var.g_vars['max_worker_num']):

                #获取一个消息
                if not message:
                    message = self.get_msg_from_redis()

                if message:
                    #加锁,非阻塞锁避免队列间互相等待
                    if global_var.g_cqueue_mutex_list[i].acquire(blocking=False):    
                        if global_var.g_cqueue_msg_list[i].enqueue(message) == 1:
                            changed = True
                            message = None
                            logger.debug('Insert a msg into queue![ QID=%d ]' % i)
                        global_var.g_cqueue_mutex_list[i].release()

            #所有消息队列均无插入操作,sleep
            if not changed:
                logger.info('Sleep for no changes![ SEC=%f ]' % global_var.g_vars['redis_slp_time'])
                time.sleep(global_var.g_vars['redis_slp_time'])

            #速度控制sleep
            time.sleep(global_var.g_vars['redis_ctl_time']) 

    def get_msg_from_redis(self):
        t = self.r_client.blpop(self.r_key, timeout=self.r_timeout)
        if t:
            try:     
                key, msg_byte = t
                msg_text = msg_byte.decode('utf-8')
                msg_dict = MSG(json.loads(msg_text))

                if msg_dict.is_device_unreachable():
                    logger.debug('Device unreachable![ TOKEN=%s ]' % msg_dict.get('token',''))
                    return None

                if msg_dict.is_msg_expired():
                    logger.debug('Msg expired![ NOWTIME=%s EXPIRY=%s ]' % (time.time(),msg_dict.get('expiry',0)))
                    return None

                return msg_dict
            except:
                logger.debug('Unpack msg error![ MSG=%s ]' % json.dumps(msg_type))
                return None 
        else:
            logger.info('No msg in redis!')
            return None


def test():
    print 'redis-thread test'

if __name__ == '__main__':
    test()
