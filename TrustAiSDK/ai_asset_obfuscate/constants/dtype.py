#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""数据类型枚举定义类"""

from enum import Enum


class DType(Enum):
    BFLOAT16 = 0  # Brain Floating Point 16-bit (2 bytes)
    FLOAT16 = 1   # Half Precision Floating Point (2 bytes)
    FLOAT32 = 2   # Single Precision Floating Point (4 bytes)
    INT8 = 3      # 1 byte
    INT32 = 4     # 4 bytes
