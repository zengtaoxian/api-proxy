#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import time
import hashlib


def request_timestamp(timestamp):
    time_array = time.localtime(timestamp)
    time_str = time.strftime("%Y%m%d%H%M%S", time_array)
    return time_str


def request_sigkey(app_id, app_token, timestamp):
    time_str = request_timestamp(timestamp)

    m = hashlib.md5()
    m.update(app_id)
    m.update(app_token)
    m.update(time_str)
    return m.hexdigest().upper()


def hangup_answered_time(time_str):
    return int(time.mktime(time.strptime(time_str, "%Y-%m-%d %H:%M:%S")))


def hangup_disconnected_time(time_str):
    return int(time.mktime(time.strptime(time_str, "%Y-%m-%d %H:%M:%S")))


def hangup_status(status):
    res = 2
    if status == 2:
        res = 0
    return res
