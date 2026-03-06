#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""TLS配置类"""
import os

from ..constants import Constant
from ..utils import clean_bytearray, date_dec, log, parameter_validation_file


class TLSConfig(object):
    """TLS配置
    ca_file：ca证书路径
    cert_file：证书路径
    pri_keyfile：证书key路径
    crl_file：吊销证书
    npu_ca_file：与npu通信的对端ca证书
    ks_path：ks工具路径
    ciphertext_path：加密口令路径
    port：kms agent端口号
    ip：kms agent ip
    cipher_suite：通信加密算法
    version：tls版本
    """
    def __init__(self, ca_file, cert_file, pri_keyfile, ks_path, ciphertext_path):
        self.ca_file = os.path.realpath(ca_file)
        self.cert_file = os.path.realpath(cert_file)
        self.pri_keyfile = os.path.realpath(pri_keyfile)
        self.crl_file = None
        self.npu_ca_file = ca_file
        self.ks_path = os.path.realpath(ks_path)
        self.ciphertext_path = os.path.realpath(ciphertext_path)
        self.port = Constant.IP_DEFAULT_PORT
        self.ip = Constant.IP_ADDRESS
        self.cipher_suite = "TLS_AES_128_GCM_SHA256"
        self.version = 'TLSv1.3'
        self.passwd = None

    def __del__(self):
        if self.passwd is not None:
            clean_bytearray(self.passwd)

    def set_port(self, port):
        self.port = port

    def set_npu_ca_file(self, npu_ca_file):
        self.npu_ca_file = npu_ca_file

    def check_passwd(self):
        self.passwd = date_dec(self.ks_path, self.ciphertext_path)
        if self.passwd is None:
            log.error("TLS config param validation failed due to failed to decrypt passwd.")
            return False
        if len(self.passwd) < Constant.PASSES_MIN_LEN or len(self.passwd) > Constant.PASSES_MAX_LEN:
            log.error("TLS config param validation failed due to the len of passwd is illegal.")
            return False
        return True

    def decrypt_validate(self):
        if not self.check_passwd():
            return False
        if not parameter_validation_file((self.ca_file, self.cert_file, self.pri_keyfile)):
            log.error("TLS config param validation failed due to cert file path error.")
            return False
        if not parameter_validation_file((self.ks_path, self.ciphertext_path)):
            log.error("TLS config param validation failed due to ciphertext password file path error.")
            return False
        if not isinstance(self.port, int) or self.port < 0 or self.port > Constant.IP_MAX_PORT:
            log.error("TLS config param validation failed due to port is illegal.")
            return False
        return True
