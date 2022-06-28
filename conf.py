#!/usr/bin/python
# -*- coding:utf-8 -*-

import pymysql,os

#============================ DB Config ==============================

config = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'passwd': '123456',
    'charset': 'utf8',
    'cursorclass': pymysql.cursors.DictCursor
}