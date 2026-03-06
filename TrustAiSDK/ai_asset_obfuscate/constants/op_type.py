#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""混淆类型枚举定义类"""

from enum import Enum


class OpType(Enum):
    ROW_SHUFFLE = 0
    COL_SHUFFLE = 1
    CUSTOM_COL_SHUFFLE = 2
    COL_SHUFFLE_ADDIN = 3
    MTP_COL_SHUFFLE = 4
    MUL_MASK = 5
    DE_MUL_MASK = 6
    COL_SHUFFLE_COEFFICIENT = 7
    MTP_COL_SHUFFLE_COEFFICIENT = 8
    SEGMENT_SWITCH = 9
    SEGMENT_COL_SHUFFLE = 10
    SEGMENT_NEGATIVE = 11
    MOE_COL_SHUFFLE = 12
    RESHAPE_SHUFFLE = 13
    VL_COL_SHUFFLE = 14
