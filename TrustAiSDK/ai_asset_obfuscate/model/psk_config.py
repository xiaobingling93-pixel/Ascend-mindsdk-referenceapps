#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""PSK配置类"""
import os

from ..constants import Constant
from ..utils import clean_bytearray, date_dec, log, parameter_validation_file


class PskConfig(object):
    """Psk配置
    psk_path：psk密文路径
    ks_path：工具路径
    ciphertext_path：加密口令路径
    """
    def __init__(self, psk_path, ks_path, ciphertext_path):
        self.psk_path = os.path.realpath(psk_path)
        self.ks_path = os.path.realpath(ks_path)
        self.ciphertext_path = os.path.realpath(ciphertext_path)
        self.passwd = None

    def __del__(self):
        if self.passwd is not None:
            clean_bytearray(self.passwd)

    def check_passwd(self):
        self.passwd = date_dec(self.ks_path, self.ciphertext_path)
        if self.passwd is None:
            log.error("Psk config param validation failed due to failed to decrypt passwd.")
            return False
        if len(self.passwd) < Constant.PASSES_MIN_LEN or len(self.passwd) > Constant.PASSES_MAX_LEN:
            log.error("Psk config param validation failed due to the len of passwd is illegal.")
            return False
        return True

    def decrypt_validate(self):
        if not self.check_passwd():
            log.error("The password validation failed.")
            return False
        if not parameter_validation_file((self.ks_path, self.ciphertext_path)):
            log.error("Psk config param validation failed due to ciphertext password file path error.")
            return False
        return True
