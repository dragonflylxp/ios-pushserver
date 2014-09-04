#!/usr/bin/python2.6
#coding=utf-8
#author lixp@500wan.com 
#edit 2014-08-28 19:13:51

import os
import sys
import time
import getopt
import signal
from multiprocessing import Pool

APP_PATH=os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
sys.path.append(os.path.join(APP_PATH,'biz'))
sys.path.append(os.path.join(APP_PATH,'lib'))
import global_var
import configer
import jobs
from logger import Log
from  thread_redis import RedisThread      #redis拉取线程
from  thread_push  import PushThread       #push发送线程
from  thread_feedback import FeedbackBiz   #feedback定时任务

"""初始化application: conf/log/global_var
"""
def init_app(cfgfile):
    confs = configer.JsonConfiger.get_instance()
    try:
        confs.load_file(cfgfile)
    except:
        print "Open config file error! [cfgfile : %s]" % cfgfile  
        sys.exit(0)

    #Log初始化
    Log.set_up(os.path.join(APP_PATH,confs.get("log/logfile")),\
               confs.get("log/logger"))
    global logger
    logger = Log().getLog()

    #全局变量初始化
    global_var.set_up(confs.get("variables"))
    return confs.get()


def usage():
    print u'''使用参数启动:
    usage: [-c]
    -c <file> ******加载配置文件
    ''' 
    sys.exit(0)


"""子进程main入口
"""
def p_main(channel):
    confs = configer.JsonConfiger.get_instance()
    svrs = confs.get("servers")
    try:
        #启动消息拉取线程
        svrs['redis'].update({'key': channel['key']})
        t_redis = RedisThread(svrs['redis']) 
        t_redis.start()

        #启动消息发送线程
        t_push = []
        for i in range(global_var.g_vars['max_worker_num']):
            svrs['apns_push'].update({'tid' : i, 'certfile' : os.path.join(APP_PATH,channel['cert'])})
            t = PushThread(svrs['apns_push'])
            t.start() 
            t_push.append(t)
        
        #启动定时任务线程
        svrs['apns_feedback'].update({'certfile' : os.path.join(APP_PATH,channel['cert'])})
        t_feedback = FeedbackBiz(svrs['apns_feedback'])
        jobs.sched.add_cron_job(t_feedback.cron_feedback_job, \
                    day_of_week='mon-sun', hour='1', minute='*',second='*') #凌晨1点
        jobs.sched.start()
    except Exception, e:
        logger.error("%s : %s" % (Exception, e))
        sys.exit(0)
    else:
        #等待子线程结束
        t_redis.join()
        for i in range(global_var.g_vars['max_worker_num']):
            t_push[i].join()
        #jobs.sched.join()

"""信号处理:SIGCHLD/SIGTERM/SIGINT
"""
g_chld_pid = []
g_chld_num = 0
def sig_chld(signo, frame):
    while 1:
        try:
            pid = os.waitpid(-1, os.WNOHANG)[0] 
            if pid <= 0: break
            global g_chld_num
            g_chld_num -= 1
            logger.info('Child process : %d terminated!' % pid)
        except OSError:
            break;
    return

def sig_quit(signo, frame):
    for i in range(len(g_chld_pid)):
        os.kill(g_chld_pid[i], signal.SIGKILL)


"""总入口
"""
def main():
    #初始化
    cfgfile  = None
    try:
        opts, argvs = getopt.getopt(sys.argv[1:], "c:h") 
        for op, value in opts:
            if   op == '-c':
                cfgfile = value
            elif op == '-h':
                usage()
    except getopt.GetoptError:
        usage()
    confs = init_app(cfgfile)
            
    #创建子进程
    signal.signal(signal.SIGCHLD, sig_chld)
    signal.signal(signal.SIGTERM, sig_quit)
    signal.signal(signal.SIGINT,  sig_quit)
    global g_chld_pid
    global g_chld_num
    channels =  confs.get('channels')
    for k,chl in channels.iteritems():
        try:
            pid = os.fork()
            if pid == 0:
                p_main(chl)
                sys.exit(0)
            else:
                g_chld_pid.append(pid)
                g_chld_num += 1
        except OSError:
            logger.error("Fork child process failed!") 

    #确保子进程都结束再退出
    while g_chld_num > 0:
        time.sleep(5)
    logger.info("Parent process terminated!") 
    sys.exit(0)
    
if __name__ == '__main__':
    main()
