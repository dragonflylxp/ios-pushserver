#!/usr/bin/python2.6
#coding=utf-8
#author lixp@500wan.com 
#edit 2014-08-31 09:54:47

import os,sys
import ssl
import socket
import datetime
from CQueue import MSG
from logger import Log

logger = Log().getLog()

class ApnsConn(object):
    def __init__(self, certfile, host, port, retry=3):
        self.certfile   = certfile
        self.host       = host
        self.port       = port
        self.retry      = retry
        self.ssl_sock   = None

    def connection(self):
        if not self.ssl_sock:
            self._connect()
        return self.ssl_sock

    def _connect(self):
        for i in range(self.retry):
            try:
                sockfd = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
                self.ssl_sock = ssl.wrap_socket(sockfd, certfile=self.certfile, \
                                ssl_version=ssl.PROTOCOL_SSLv3)
                self.ssl_sock.connect((self.host, self.port))
                break
            except (NameError, TypeError, ssl.SSLError),e:
                self.ssl_sock = None

        if not self.ssl_sock:
            logger.error('Connect to server failed! [ HOST=%s RETRY=%d ]' % (self.host, self.retry))


    def _disconnect(self):
        if self.ssl_sock:
            self.ssl_sock.close()

    def _reconnect(self):
        self._disconnect()
        self._connect()        

class ApnsGateway(ApnsConn):
    def __init__(self, **kwargs):
        super(ApnsGateway, self).__init__(**kwargs)

    def send_msg(self, msg):
        try:
            self.connection().sendall(msg)
        except socket.error as e:
            logger.warning('Send msg failed![ ETYPE=%s ECTX=%s]' % (str(type(e)), str(e)))

    def recv_resp(self):
        try:
            resp = self.connection().recv(256)
            return resp
        except socket.error as e:
            logger.warning('Recv resp failed![ ETYPE=%s ECTX=%s]' % (str(type(e)), str(e)))
            return "" 

class ApnsFeedback(ApnsConn):
    def __init__(self, **kwargs):
        super(ApnsFeedback, self).__init__(**kwargs)

    def _chunks(self):
        """generator:每次都若干字节并返回数据"""
        while 1:
            data = self.connection().recv(4096)
            yield data
            if not data:
                break;

    def items(self):
        """generator:用_chunks读到的数据拼装一个包"""
        buff = ''
        for chunk in self._chunks():
            buff += chunk
            if not buff:
                break;

            if len(buff) < 6:
                break;

            while len(buff) > 6:
                token_length  = MSG.ushort_big_endian_unpack(buff[4:6])
                bytes_to_read = 6 + token_length
                if len(buff) >= bytes_to_read:
                    fail_time_unix = MSG.uint_big_endian_unpack(buff[0:4])
                    fail_time_date = datetime.datetime.utcfromtimestamp(fail_time_unix)
                    fail_time_fmt  = fail_time_date.strftime('%Y-%m-%d %H:%M:%S.%f')
                    token          = MSG.token_unpack(buff[6:bytes_to_read])
                    yield(token, fail_time_fmt)
                    buff = buff[bytes_to_read:]
                else:
                    break;
    
def test():
    pass
      
if __name__ == '__main__':
    test()
