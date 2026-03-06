#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""OBF_SDK自定义异常"""


class ObfException(Exception):
    """obf自定义异常"""

    def __init__(self, input_obf):
        if isinstance(input_obf, tuple) and len(input_obf) == 2:
            self.code = input_obf[0]
            self.message = input_obf[1]
        else:
            self.message = input_obf
        super().__init__(self.message)
