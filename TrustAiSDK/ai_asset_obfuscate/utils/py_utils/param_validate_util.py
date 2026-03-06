#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""参数校验工具类"""

import os

from ...constants import Constant


def parameter_validation_file(parameter):
    if isinstance(parameter, str):
        if os.path.exists(parameter) and len(parameter) <= Constant.FILE_MAX_LEN:
            return True
    if isinstance(parameter, tuple):
        for file in parameter:
            result = parameter_validation_file(file)
            if not result:
                return False
        return True
    return False


def parameter_validation_path(parameter):
    if parameter_validation_str(parameter) and os.path.exists(os.path.normpath(parameter)) and len(
            parameter) <= Constant.FILE_MAX_LEN:
        return True
    return False


def parameter_validation_str(parameter):
    if parameter is not None and isinstance(parameter, str):
        return True
    return False

