#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""对口令加密保护"""
import os
import re

from ..constants import Constant, ErrorCode
from ..utils import parameter_validation_path, log, data_enc, clean_bytearray, parameter_validation_str


def passwd_enc(ks_path: str, passwd: str, ciphertext_path: str) -> (int, str):
    """对口令加密保护
    通过kmc，对口令进行加密，生成加密后的密文文件
    ks_path:工具路径  passwd:待加密口令  ciphertext_path:加密口令路径
    """
    if not parameter_validation_path(ks_path):
        log.error("The ks_path validation failed.")
        return ErrorCode.INVALID_PARAM.value
    is_str = passwd is not None and isinstance(passwd, str)
    if not is_str or len(passwd) > Constant.PASSES_MAX_LEN or len(passwd) < Constant.PASSES_MIN_LEN:
        log.error("The password validation failed.")
        return ErrorCode.INVALID_PARAM.value
    patterns = [r'[A-Z]', r'[a-z]', r'[0-9]', r'[^a-zA-Z0-9]']
    conditions_count = sum(bool(re.search(pattern, passwd)) for pattern in patterns)
    if conditions_count < Constant.PASSES_VALID_COUNT:
        log.error("The password validation failed.")
        return ErrorCode.INVALID_PARAM.value
    if not parameter_validation_str(ciphertext_path):
        log.error("The ciphertext_path validation failed.")
        return ErrorCode.INVALID_PARAM.value
    b_passwd = bytearray(passwd, 'utf-8')
    ret = data_enc(os.path.realpath(ks_path), b_passwd, os.path.realpath(ciphertext_path))
    clean_bytearray(b_passwd)
    if ret != 0:
        log.error(f"Encryption passwd failed, the result is {ret}")
        return ErrorCode.ENCRYPT_FAILED.value
    return ErrorCode.SUCCESS.value
