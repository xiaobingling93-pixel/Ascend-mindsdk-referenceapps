#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""清除数组内元素"""


def clean_bytearray(sen_bytearray):
    for i, _ in enumerate(sen_bytearray):
        sen_bytearray[i] = 0x00
    del sen_bytearray
