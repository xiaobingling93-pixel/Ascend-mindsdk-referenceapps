#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""公共方法工具类"""

import shutil
from pathlib import Path

from .. import log
from ...constants import Constant, ErrorCode
from ...exception import ObfException


def check_device_space(input_path: str, target_path: str) -> bool:
    input_size = sum(f.stat().st_size for f in Path(input_path).rglob('*') if f.is_file())
    _, _, free = shutil.disk_usage(Path(target_path).parent)
    return input_size + Constant.RESERVED_SPACE < free


def check_white_list(token_white_list, vocab_size):
    """对白名单入参进行校验
    1 list不为空时进入校验
    2 list内元素必须为int类型，且大于等于0，小于vocab_size
    """
    if token_white_list is not None:
        if any(not isinstance(item, int) or item < 0 or item >= vocab_size for item in token_white_list):
            log.error("The element of token white list must be greater than or equal to zero and small " +
                      "than vocab size.")
            raise ObfException(ErrorCode.WHITE_LIST_CHECK_FAILED.value)

