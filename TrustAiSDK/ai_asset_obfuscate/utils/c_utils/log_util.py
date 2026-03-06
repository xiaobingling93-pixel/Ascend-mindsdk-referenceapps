#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""obf_sdk日志配置类
该类配置了公共的日志方法，包括info，debug，error，warning，critical级别
"""

import ctypes
import os

from .c_lib import lib_obf_tool
from ...exception import ObfException

AI_ASSET_OBF_TYPE = 3

LOG_LEVEL_CRITICAL = 0
LOG_LEVEL_ERROR = 1
LOG_LEVEL_WARN = 2
LOG_LEVEL_INFO = 3
LOG_LEVEL_DEBUG = 4


class ObfLog:
    """自定义日志公共配置"""
    def __init__(self):
        path = os.getenv('OBF_LOG_PATH', os.path.sep + 'tmp')
        # 设置参数类型和返回值类型 C方法：int InitLog(int logType, int logLevel, const char *confPath);
        lib_obf_tool.InitLog.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p]
        lib_obf_tool.InitLog.restype = ctypes.c_int
        result = lib_obf_tool.InitLog(AI_ASSET_OBF_TYPE, LOG_LEVEL_INFO, path.encode("utf-8"))
        if result != 0:
            log.error(f"InitLog failed, the result is {result}")
            raise ObfException("InitLog failed.")

    @staticmethod
    def record_log(level, msg):
        # 设置参数类型和返回值类型 C方法: void RecordLogString(int level, const char *logString);
        lib_obf_tool.RecordLogString.argtypes = [ctypes.c_int, ctypes.c_char_p]
        lib_obf_tool.RecordLogString.restype = None
        lib_obf_tool.RecordLogString(level, msg.encode("utf-8"))

    def debug(self, msg):
        self.record_log(LOG_LEVEL_DEBUG, msg)

    def info(self, msg):
        self.record_log(LOG_LEVEL_INFO, msg)

    def warning(self, msg):
        self.record_log(LOG_LEVEL_WARN, msg)

    def error(self, msg):
        self.record_log(LOG_LEVEL_ERROR, msg)

    def critical(self, msg):
        self.record_log(LOG_LEVEL_CRITICAL, msg)


log = ObfLog()
