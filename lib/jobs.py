#!/usr/bin/python2.6
#coding=utf-8
#author lixp@500wan.com 
#edit 2014-09-01 10:56:27

import apscheduler
from apscheduler.scheduler import Scheduler
from logger import Log

logger = Log().getLog()

sched = Scheduler()
sched.daemonic = False  #非daemon线程


def job_events_listener(jobEvent):
    '''监听任务事件
    '''
    if jobEvent.code == apscheduler.events.EVENT_JOB_EXECUTED:
        pass
        # 正常执行任务
        logger.info("scheduled|%s|trigger=%s|scheduled_time=%s" % (jobEvent.job.name, jobEvent.job.trigger, jobEvent.scheduled_run_time))

    else:
        # 异常或丢失
        logger.exception((jobEvent.code, jobEvent.exception, jobEvent.job, jobEvent.scheduled_run_time))
        except_msg = "miss execute" if not jobEvent.exception else str(jobEvent.exception.args)
        alert_msg = "%s,%s,%s,%s" % (
            jobEvent.code, jobEvent.job.name, except_msg, jobEvent.scheduled_run_time.strftime("%H:%M:%S"))
        # 告警
        #monitor.add_alert_msg(jobEvent.job.name, alert_msg)
        logger.info("send alert over, key=%s|msg=%s" % alert_msg)


#监听执行情况
sched.add_listener(job_events_listener,
                apscheduler.events.EVENT_JOB_ERROR | apscheduler.events.EVENT_JOB_MISSED | apscheduler.events.EVENT_JOB_EXECUTED)
