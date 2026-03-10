#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""c语言库文件提供的工具类"""

__all__ = [
    "lib_secure_c",
    "lib_obf_tool",
    "log",
    "data_enc",
    "date_dec",
    "data_enc_mul",
    "data_dec_mul",
    "call_obf_del_seed",
    "call_obf_reg_seed",
    "call_obf_query_seed",
    "generate_obf_and_de_obf_dict",
    "get_obf_dict_value_by_key",
    "get_de_obf_dict_value_by_key",
    "generate_patch_and_channel_permute",
    "generate_random_bytes",
    "apply_patch_and_channel_permute",
    "create_weight_obfuscator",
    "destroy_weight_obfuscator",
    "apply_weight_obfuscation"
]

from .c_lib import lib_secure_c, lib_obf_tool
from .log_util import log
from .obf_api import create_weight_obfuscator, destroy_weight_obfuscator, apply_weight_obfuscation
from .obf_tool_util import (data_enc, date_dec, data_enc_mul, data_dec_mul, call_obf_del_seed, call_obf_reg_seed, \
                            call_obf_query_seed)
from .random_api import generate_random_bytes, generate_obf_and_de_obf_dict, get_obf_dict_value_by_key, \
    get_de_obf_dict_value_by_key, \
    generate_patch_and_channel_permute, apply_patch_and_channel_permute
