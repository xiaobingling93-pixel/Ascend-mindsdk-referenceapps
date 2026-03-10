#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""资产混淆基类"""

from abc import ABC, abstractmethod
from typing import List

from ..constants import Constant, ErrorCode
from ..model import TLSConfig, PskConfig
from ..utils import log, clean_bytearray, call_obf_query_seed


class AssetObfuscation(ABC):
    @abstractmethod
    def _set_seed_core(self, seed_content_bytes, seed_type):
        pass  # abstract method

    def export_set_obf_seed(self, tls_conf: TLSConfig = None, psk_conf: PskConfig = None,
                            device_id: List[int] = None) -> (int, str):
        """
        导出并设置数据混淆因子

        参数:
        tls_conf: tls通信相关参数
        psk_conf: psk解密相关参数
        device_id: 导出的设备id
        返回值:
        （error_code， msg）
        异常描述:
        无
        """
        if tls_conf is None or psk_conf is None:
            log.error("The tls config or psk config is None.")
            return ErrorCode.INVALID_PARAM.value
        if device_id:
            if not all(0 <= value <= Constant.MAX_DEVICE_ID for value in device_id):
                log.error("All values in device_id must be in the range 0-15.")
                return ErrorCode.INVALID_PARAM.value
            if len(device_id) != len(set(device_id)):
                log.error("All values in device_id must be unique.")
                return ErrorCode.INVALID_PARAM.value
        try:
            if not tls_conf.decrypt_validate() or not psk_conf.decrypt_validate():
                log.error("Tls or psk validation failed.")
                return ErrorCode.INVALID_PARAM.value
            seed_content_bytes = call_obf_query_seed(tls_conf, psk_conf, device_id)
            if seed_content_bytes is None:
                log.error("The seed content bytes is none.")
                return ErrorCode.QUERY_SEED_FAILED.value
            set_seed_result = self._set_seed_core(seed_content_bytes, Constant.DATA_SEED_TYPE)
            clean_bytearray(seed_content_bytes)
            return set_seed_result
        finally:
            del tls_conf
            del psk_conf
