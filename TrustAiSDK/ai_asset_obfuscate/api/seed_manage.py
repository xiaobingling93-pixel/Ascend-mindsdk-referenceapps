#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""创建混淆因子对外接口"""

import os
from typing import List

from ..constants import Constant, ErrorCode
from ..model import TLSConfig, PskConfig
from ..utils import (call_obf_reg_seed, log, call_obf_del_seed, generate_random_bytes,
                     clean_bytearray, data_enc_mul)


def __create_seed_core(seed_type, seed_content_bytearray, device_id, psk_conf, tls_conf):
    result = call_obf_reg_seed(seed_type, seed_content_bytearray, device_id, psk_conf, tls_conf)
    if result == 1:
        call_obf_del_seed(tls_conf, device_id, seed_type)
        result = call_obf_reg_seed(seed_type, seed_content_bytearray, device_id, psk_conf, tls_conf)
    if result == 0:
        return ErrorCode.SUCCESS.value
    else:
        log.error(f"Create obfuscate seed failed, the result is {result}")
        return ErrorCode.CREATE_SEED_FAILED.value


def __check_local_save_param(seed_type, seed_ciphertext_dir) -> bool:
    return seed_type in [Constant.MODEL_SEED_TYPE, Constant.DATA_SEED_TYPE] \
        and isinstance(seed_ciphertext_dir, str) and not os.path.islink(seed_ciphertext_dir)


def distribute_obf_seed(seed_type: int, tls_conf: TLSConfig, psk_conf: PskConfig, seed_content: str,
                        device_id: List[int] = None) -> (int, str):
    """
    下发混淆因子到npu

    :param seed_type: 混淆因子类型
    :param tls_conf: tls通信配置
    :param psk_conf: psk私钥配置
    :param seed_content: 混淆因子明文
    :param device_id: 需要下发的设备id，非必填
    :return: errorCode(int, str)
    """
    try:
        if not check_param(tls_conf, psk_conf, seed_type, device_id):
            return ErrorCode.INVALID_PARAM.value
        if seed_content is not None and isinstance(seed_content, str) and (
                Constant.SEED_CONTENT_MIN_LEN <= len(seed_content) <= Constant.SEED_CONTENT_MAX_LEN):
            seed_content_bytearray = bytearray(seed_content, "utf-8")
        else:
            log.error("The params of create seed validation failed.")
            return ErrorCode.INVALID_PARAM.value
        # 校验完毕，传入参数
        error_code, msg = __create_seed_core(seed_type, seed_content_bytearray, device_id, psk_conf, tls_conf)
        clean_bytearray(seed_content_bytearray)
        return error_code, msg
    finally:
        del tls_conf
        del psk_conf


def check_param(tls_conf, psk_conf, seed_type, device_id):
    if not tls_conf or not psk_conf:
        log.error("The tls_conf or psk_conf is null.")
        return False
    if not tls_conf.decrypt_validate() or not psk_conf.decrypt_validate():
        log.error("Psk or tls validation failed.")
        return False
    if seed_type not in [1, 2]:
        log.error("The seed type is out of range.")
        return False
    if device_id:
        if not all(0 <= value <= Constant.MAX_DEVICE_ID for value in device_id):
            log.error("All values in device_id must be in the range 0-15.")
            return False
        if len(device_id) != len(set(device_id)):
            log.error("All values in device_id must be unique.")
            return False
    return True


def local_save_obf_seed(seed_type: int, seed_ciphertext_dir: str, seed_content: str = None) -> (int, str):
    """
    本地保存混淆因子

    :param seed_type: 混淆因子类型
    :param seed_ciphertext_dir: 密文保存路径
    :param seed_content: 混淆因子明文
    :return: errorCode(int, str)
    """
    # 检查seed_type和seed_ciphertext_dir的有效性
    if not __check_local_save_param(seed_type, seed_ciphertext_dir):
        log.error("Invalid seed type or empty storage directory.")
        return ErrorCode.INVALID_PARAM.value

    # 处理seed_content
    if seed_content is None:
        seed_content_bytearray = generate_random_bytes(Constant.SEED_CONTENT_MIN_LEN)
    elif Constant.SEED_CONTENT_MIN_LEN <= len(seed_content) <= Constant.SEED_CONTENT_MAX_LEN:
        seed_content_bytearray = bytearray(seed_content, "utf-8")
    else:
        log.error("The ciphertext storage path and the confusion factor content cannot both be empty.")
        return ErrorCode.INVALID_PARAM.value
    enc_file_name = Constant.MODEL_CIPHERTEXT_FILE_NAME if seed_type == Constant.MODEL_SEED_TYPE \
        else Constant.DATA_CIPHERTEXT_FILE_NAME
    ret = data_enc_mul(os.path.realpath(seed_ciphertext_dir), seed_content_bytearray, enc_file_name)
    clean_bytearray(seed_content_bytearray)
    if ret != 0:
        log.error(f"Encryption failed, the result is {ret}")
        return ErrorCode.ENCRYPT_FAILED.value
    return ErrorCode.SUCCESS.value