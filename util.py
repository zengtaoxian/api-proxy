#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging
import os
import json
from cloghandler import ConcurrentRotatingFileHandler as FileHandler


def init_log(dir_name, file_name, level):
    """
    初始化日志
    :param dir_name: 文件夹名称
    :param file_name: 文件名称
    :param level: 级别
    """

    _levelNames = {
        'CRITICAL': logging.CRITICAL,
        'ERROR': logging.ERROR,
        'WARN': logging.WARNING,
        'WARNING': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG,
        'NOTSET': logging.NOTSET,
    }

    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

    log = logging.getLogger()

    fmt = "[%(asctime)s] %(process)d %(levelname)s %(filename)s %(lineno)d %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, date_fmt)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    log.addHandler(console_handler)

    # log_path = os.path.join(dir_name, file_name)
    # log_file = os.path.abspath(log_path)
    # file_handler = FileHandler(filename=log_file,
    #                            maxBytes=1024 * 1024 * 10,
    #                            backupCount=5)
    # file_handler.setFormatter(formatter)
    # log.addHandler(file_handler)

    log.setLevel(_levelNames.get(str(level), logging.INFO))


def load_cfg(file_path):
    """
    加载配置
    :param file_path: 文件路径
    :return:配置对象
    """
    cfg = None

    with open(file_path, 'r') as f:
        try:
            cfg = json.load(f)
        except Exception, e:
            logging.error("e:{0}".format(e))

    return cfg
