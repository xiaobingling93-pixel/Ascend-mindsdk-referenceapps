# !/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""加载C语言库文件
加载动态链接库文件，实现在python中使用C语言实现的算法
"""

from ctypes import CDLL, c_int, c_void_p, c_size_t
import os

from ...constants import ErrorCode
from ...exception import ObfException
from ...libs import lib_path

try:
    lib_secure_c = CDLL(os.path.join(lib_path, "libsecurec.so"))
    lib_secure_c.memcpy_s.argtypes = [c_void_p, c_size_t, c_void_p, c_size_t]
    lib_secure_c.memcpy_s.restype = c_int

    CDLL(os.path.join(lib_path, "libkmc.so"))
    CDLL(os.path.join(lib_path, "libsdp.so"))
    lib_obf_tool = CDLL(os.path.join(lib_path, "libobfuscate.so"))
except OSError as e:
    raise ObfException(ErrorCode.FAILED_TO_LOAD_LIBRARY.value) from e
