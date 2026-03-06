#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""混淆和解混淆数据接口"""

import os
from typing import List
import numpy as np
import json

from .asset_obfuscation import AssetObfuscation
from ..constants import Constant, ErrorCode
from ..exception import ObfException
from ..model import TLSConfig, PskConfig
from ..utils import log, generate_random_obf_list, get_obf_dict_value_by_key, rand_by_seed, clean_bytearray, \
    get_de_obf_dict_value_by_key, lib_secure_c, \
    check_white_list, restore_white_set, data_dec_mul, generate_obf_and_de_obf_dict


def _check_local_save_path(is_local_save, seed_ciphertext_dir) -> bool:
    return is_local_save and isinstance(seed_ciphertext_dir, str) and not os.path.islink(seed_ciphertext_dir) \
        and os.path.exists(seed_ciphertext_dir)


class DataAssetObfuscation(AssetObfuscation):
    """推理数据混淆对外接口
    创建DataAssetObfuscation类实例
    """

    def __init__(self, vocab_size: int, token_white_list: list = None):
        """参数：vocab_size:模型词汇表实际长度
        token_white_list:词表tokenId白名单,该token不做混淆
        """
        if not isinstance(vocab_size, int) or vocab_size <= 0:
            log.error("The size of vocab must be greater than zero.")
            raise ObfException(ErrorCode.VOCAB_SIZE_FAILED.value)
        check_white_list(token_white_list, vocab_size)
        self.vocab_size = vocab_size
        self.white_set = [] if token_white_list is None else set(token_white_list)

    def set_seed_safer(self, tls_info: tuple, psk_info: tuple) -> (int, str):
        """设置混淆因子，用于推理数据混淆
        ca_file：ca证书路径  cert_file：证书路径  pri_keyfile：证书key路径  port：端口号  ks_path：ks工具路径
        ciphertext_path：加密口令路径
        psk_path：psk密文路径  ks_path_psk：工具路径  ciphertext_path_psk：加密口令路径
        """
        if tls_info is None or len(tls_info) != Constant.TSL_INFO_PARAM_SIZE:
            log.error("Tls info param size validation failed.")
            return ErrorCode.INVALID_PARAM.value
        if psk_info is None or len(psk_info) != Constant.PSK_INFO_PARAM_SIZE:
            log.error("Psk info param size validation failed.")
            return ErrorCode.INVALID_PARAM.value
        ca_file, cert_file, pri_keyfile, port, ks_path, ciphertext_path = tls_info
        psk_path, ks_path_psk, ciphertext_path_psk = psk_info
        tls = TLSConfig(ca_file, cert_file, pri_keyfile, ks_path, ciphertext_path)
        tls.set_port(port)
        psk = PskConfig(psk_path, ks_path_psk, ciphertext_path_psk)
        return self.export_set_obf_seed(tls, psk)

    def set_seed_content(self, seed_content: str = None, is_local_save: bool = False,
                         seed_ciphertext_dir: str = None) -> (int, str):
        """
        1.输入混淆因子内容，用于数据混淆
        2.通过本地软保护设置混淆因子

        :param seed_content: 混淆因子类型
        :param is_local_save: 是否从本地获取
        :param seed_ciphertext_dir: 密文保存路径，is_local_save为True时需要此参数需要被校验
        :return: errorCode(int, str)
        """
        if not isinstance(seed_content, str) and not _check_local_save_path(is_local_save, seed_ciphertext_dir):
            log.error("The obfuscate seed content data type validation failed.")
            return ErrorCode.INVALID_SEED_CONTENT.value
        if seed_content is not None and (len(seed_content) > Constant.SEED_CONTENT_MAX_LEN
                                            or len(seed_content) < Constant.SEED_CONTENT_MIN_LEN):
            log.error("The obfuscate seed content len validation failed.")
            return ErrorCode.INVALID_SEED_CONTENT.value
        if seed_content is not None:
            seed_content_bytes = bytearray(seed_content, "utf-8")
        else:
            seed_content_bytes = data_dec_mul(seed_ciphertext_dir, Constant.DATA_CIPHERTEXT_FILE_NAME)
        set_seed_result = self._set_seed_core(seed_content_bytes, Constant.DATA_SEED_TYPE)
        clean_bytearray(seed_content_bytes)
        return set_seed_result

    def data_2d_obf(self, tokens: List[List[int]]) -> List[List[int]]:
        """混淆二维数据
        参数：tokens:待加混淆的tokens 注意：最内层列表内需为int数
        返回值：obf_tokens:加混淆后的tokens
        """
        obf_tokens = []
        for token_row in tokens:
            obf_row = []
            for token in token_row:
                self.__check_input_item(token)
                token = get_obf_dict_value_by_key(token)
                obf_row.append(token)
            obf_tokens.append(obf_row)
        return obf_tokens

    def data_1d_obf(self, tokens: List[int]) -> List[int]:
        """混淆一维数据
        参数：tokens:待加混淆的tokens 注意：列表内需为int数
        返回值：obf_tokens:加混淆后的tokens
        """
        obf_tokens = []
        for token in tokens:
            self.__check_input_item(token)
            token = get_obf_dict_value_by_key(token)
            obf_tokens.append(token)
        return obf_tokens

    def data_2d_deobf(self, tokens: List[List[int]]) -> List[List[int]]:
        """解混淆二维数据
        参数：tokens:待解混淆的tokens 注意：最内层列表内需为int数
        返回值：obf_tokens:解混淆后的tokens
        """
        deobf_tokens = []
        for row in tokens:
            deobf_row = []
            for token in row:
                self.__check_input_item(token)
                token = get_de_obf_dict_value_by_key(token)
                deobf_row.append(token)
            deobf_tokens.append(deobf_row)
        return deobf_tokens

    def data_1d_deobf(self, tokens: List[int]) -> List[int]:
        """解混淆一维数据
        参数：tokens:待解混淆的tokens 注意：列表内需为int数
        返回值：obf_tokens:解混淆后的tokens
        """
        deobf_tokens = []
        for token in tokens:
            self.__check_input_item(token)
            token = get_de_obf_dict_value_by_key(token)
            deobf_tokens.append(token)
        return deobf_tokens

    def token_obf(self, token: int) -> int:
        """混淆int数据
        参数：token:待加混淆的token
        返回值；token:加混淆后的token
        """
        if token >= self.vocab_size:
            log.warning("The input token is out of range, return the original value.")
            return token
        return get_obf_dict_value_by_key(token)

    def token_deobf(self, token: int) -> int:
        """解混淆int数据"""
        return get_de_obf_dict_value_by_key(token)

    def __check_input_item(self, item: int):
        if not isinstance(item, int) or item >= self.vocab_size:
            log.error("Item type must be int and item must less than vocab_size.")
            raise ObfException(ErrorCode.ITEM_VALIDATE_FAILED.value)

    def _set_seed_core(self, seed_content, _):
        log.info("Start to set seed core.")
        # 使用种子生成随机数，需要将8位数合并成32位数，需要32位数的长度为self.vocab_size，因此需要生成4倍长度的8位数的数组
        try:
            generate_obf_and_de_obf_dict(self.white_set, seed_content, self.vocab_size)
        except ObfException as e:
            return e.code, e.message
        log.info("Set seed core successful.")
        return ErrorCode.SUCCESS.value
