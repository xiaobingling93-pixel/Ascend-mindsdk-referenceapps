#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""随机数工具类
生成随机映射表，随机浮点数，随机字节
"""

import ctypes
from ctypes import Structure, POINTER, c_uint8, c_uint32
import numpy as np

from .c_lib import lib_obf_tool
from .log_util import log
from ...constants import Constant, ErrorCode
from ...exception import ObfException


class CryptData(Structure):
    _fields_ = [
        ('data', POINTER(c_uint8)),  # 数据指针
        ('len', c_uint32)  # 数据长度
    ]


# 定义CryptOutput类，用于存储加密输出数据
class ObfData(Structure):
    _fields_ = [
        ('data', POINTER(c_uint8)),  # 输出数据指针
        ('len', c_uint32)  # 输出数据长度
    ]


# 定义函数参数类型和返回值类型
lib_obf_tool.GenerateRandomBytes.argtypes = [
    ctypes.c_size_t,  # input_length
    ctypes.POINTER(ctypes.c_uint8)  # output_data
]
lib_obf_tool.GenerateRandomBytes.restype = ctypes.c_int

# 设置库函数的参数类型和返回类型
lib_obf_tool.GenerateObfAndDeObfDict.argtypes = [
    ctypes.POINTER(CryptData),
    ctypes.POINTER(ObfData),
    ctypes.POINTER(ctypes.c_uint32),  # whiteList
    ctypes.c_size_t,  # whiteListLength
    ctypes.c_size_t  # random_list_len
]
lib_obf_tool.GenerateObfAndDeObfDict.restype = ctypes.c_int  # 返回指针

# 设置库函数的参数类型和返回类型
lib_obf_tool.GetObfDictValueByKey.argtypes = [
    ctypes.c_int  # key
]
lib_obf_tool.GenerateObfAndDeObfDict.restype = ctypes.c_int  # 返回指针

# 设置库函数的参数类型和返回类型
lib_obf_tool.GeneratePatchAndChannelPermute.argtypes = [
    ctypes.POINTER(CryptData),
    ctypes.POINTER(ObfData),
    ctypes.c_size_t  # random_list_len
]
lib_obf_tool.GeneratePatchAndChannelPermute.restype = ctypes.c_int  # 返回指针

# 设置库函数的参数类型和返回类型
lib_obf_tool.ApplyPatchAndChannelPermute.argtypes = [
    ctypes.POINTER(ctypes.c_uint8),  # data
    ctypes.c_int,  # channel
    ctypes.c_int,  # grid_h
    ctypes.c_int,  # grid_w
    ctypes.c_int  # patch_size_squared
]
lib_obf_tool.ApplyPatchAndChannelPermute.restype = ctypes.c_int


def apply_patch_and_channel_permute(
        input_data: np.ndarray,
) -> np.ndarray:
    """
    调用C++函数应用通道和patch混淆

    Args:
        input_data: 输入数据 (patches_flat), 形状为 (channel, grid_h, grid_w, patch_size_squared)

    Returns:
        output_data: 输出数据 (permuted_flat), 形状与输入相同

    Raises:
        ObfException: C函数调用失败时抛出
    """

    # 确保输入是连续的uint8数组，并创建副本以避免修改原始数据
    patches_flat_copy = np.ascontiguousarray(input_data.astype(np.uint8))
    channels, grid_h, grid_w, patch_pixels = patches_flat_copy.shape
    # 调用C++函数
    result = lib_obf_tool.ApplyPatchAndChannelPermute(
        patches_flat_copy.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
        ctypes.c_int(channels),
        ctypes.c_int(grid_h),
        ctypes.c_int(grid_w),
        ctypes.c_int(patch_pixels)
    )
    if result != 0:
        log.error(f"ApplyPatchAndChannelPermute failed, the result is {result}")
    return patches_flat_copy.copy()


def generate_patch_and_channel_permute(input_seed: bytearray, random_list_len: int, adin: bytes = None) -> None:
    # 创建输入数据
    input_length = len(input_seed)
    input_data = (ctypes.c_uint8 * input_length)(*input_seed)
    crypt_data = CryptData(ctypes.cast(input_data, ctypes.POINTER(ctypes.c_uint8)), ctypes.c_uint32(input_length))

    # 创建附件数据
    if adin is None:
        adin_length = 0
        adin_data = ObfData(None, ctypes.c_uint32(adin_length))
    else:
        adin_length = len(adin)
        adin_tmp = (ctypes.c_uint8 * adin_length)(*adin)
        adin_data = ObfData(ctypes.cast(adin_tmp, ctypes.POINTER(ctypes.c_uint8)), ctypes.c_uint32(adin_length))

    result = lib_obf_tool.GeneratePatchAndChannelPermute(ctypes.byref(crypt_data), ctypes.byref(adin_data),
                                                         ctypes.c_size_t(random_list_len))
    if result != 0:
        log.error(f"Failed to generate patch and channel permute, the result is {result}")
        raise ObfException(ErrorCode.GENERATED_RANDOM_FAILED.value)


def get_obf_dict_value_by_key(key: int) -> int:
    value = lib_obf_tool.GetObfDictValueByKey(ctypes.c_int(key))
    return value


def get_de_obf_dict_value_by_key(key: int) -> int:
    value = lib_obf_tool.GetDeObfDictValueByKey(ctypes.c_int(key))
    return value


def generate_obf_and_de_obf_dict(white_set: list, input_seed: bytearray, random_list_len: int,
                                 adin: bytes = None) -> None:
    # 创建输入数据
    input_length = len(input_seed)
    input_data = (ctypes.c_uint8 * input_length)(*input_seed)
    crypt_data = CryptData(ctypes.cast(input_data, ctypes.POINTER(ctypes.c_uint8)), ctypes.c_uint32(input_length))

    # 创建附件数据
    if adin is None:
        adin_length = 0
        adin_data = ObfData(None, ctypes.c_uint32(adin_length))
    else:
        adin_length = len(adin)
        adin_tmp = (ctypes.c_uint8 * adin_length)(*adin)
        adin_data = ObfData(ctypes.cast(adin_tmp, ctypes.POINTER(ctypes.c_uint8)), ctypes.c_uint32(adin_length))

    whitelist_length = len(white_set)
    c_whitelist = (ctypes.c_uint32 * whitelist_length)(*white_set)
    result = lib_obf_tool.GenerateObfAndDeObfDict(ctypes.byref(crypt_data), ctypes.byref(adin_data),
                                                  c_whitelist, whitelist_length, ctypes.c_size_t(random_list_len))
    if result != 0:
        log.error(f"Failed to generate obf and deobf dict, the result is {result}")
        raise ObfException(ErrorCode.GENERATED_RANDOM_FAILED.value)


def generate_random_bytes(random_len):
    output = (ctypes.c_uint8 * random_len)(*[i for i in range(random_len)])
    result = lib_obf_tool.GenerateRandomBytes(random_len, output)
    if result != 0:
        log.error(f"Failed to generate random bytes, the result is {result}")
        raise ObfException("Failed to generate a secure random number.")
    seed_content_bytearray = bytearray(output)
    for i in range(random_len):
        output[i] = 0
    del output
    return seed_content_bytearray
