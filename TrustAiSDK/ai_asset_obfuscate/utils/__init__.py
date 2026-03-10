#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""定义外部可访问的子包和模块（module）清单"""

__all__ = [
    "check_device_space",
    "check_white_list",
    "parameter_validation_file",
    "parameter_validation_path",
    "parameter_validation_str",
    "clean_bytearray",
    "lib_secure_c",
    "lib_obf_tool",
    "log",
    "data_enc",
    "data_enc_mul",
    "date_dec",
    "data_dec_mul",
    "call_obf_del_seed",
    "call_obf_reg_seed",
    "call_obf_query_seed",
    "generate_random_bytes",
    "thread_pools",
    "generate_obf_and_de_obf_dict",
    "get_obf_dict_value_by_key",
    "generate_patch_and_channel_permute",
    "get_de_obf_dict_value_by_key",
    "apply_patch_and_channel_permute"
]

from .c_utils import (data_enc, data_enc_mul, date_dec, data_dec_mul, call_obf_del_seed, call_obf_reg_seed, \
                      call_obf_query_seed, generate_random_bytes, generate_obf_and_de_obf_dict,
                      get_obf_dict_value_by_key, \
                      get_de_obf_dict_value_by_key, apply_patch_and_channel_permute, \
                      lib_secure_c, lib_obf_tool, log, generate_patch_and_channel_permute)
from .py_utils import check_device_space, check_white_list, clean_bytearray, \
    parameter_validation_file, parameter_validation_path, parameter_validation_str, thread_pools
