#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import ctypes
from ctypes import Structure, POINTER, c_uint8, c_uint32, c_int32, c_double, c_void_p, c_int

import numpy as np
import torch

from .c_lib import lib_obf_tool
from .log_util import log
from ...constants import Constant, ErrorCode, DType
from ...exception import ObfException


# 映射torch dtype到numpy dtype
TORCH_TO_NP_DTYPE = {
    torch.bfloat16: np.float32,
    torch.float32: np.float32,
    torch.float16: np.float16,
    torch.int8: np.int8,
    torch.int32: np.int32
}

# 定义torch dtype到DType枚举的映射
TORCH_TO_DTYPE_ENUM = {
    torch.bfloat16: DType.BFLOAT16.value,
    torch.float16: DType.FLOAT16.value,
    torch.float32: DType.FLOAT32.value,
    torch.int8: DType.INT8.value,
    torch.int32: DType.INT32.value
}


# 定义ObfConfig结构体，与C++端保持一致
class ObfConfig(Structure):
    _fields_ = [
        ('hidden_size', c_uint32),
        ('vocab_size', c_uint32),
        ('intermediate_size', c_uint32),
        ('moe_intermediate_size', c_uint32),
        ('head_dim', c_uint32),
        ('num_attention_heads', c_uint32),
        ('vision_hidden_size', c_uint32),
        ('tp_num', c_uint32),
        ('obf_coefficient', c_double),
        ('is_obfuscation', c_uint32),
        ('white_list', POINTER(c_uint32)),
        ('white_list_length', c_uint32)
    ]


# 定义ObfOperation结构体，与C++端保持一致
class ObfOperation(Structure):
    _fields_ = [
        ('op_type', c_int32),
        ('dim', c_int32),
        ('custom_start', c_int32),
        ('custom_len', c_int32),
        ('weight_rank', c_int32),
        ('shape', c_int32 * 8),
        ('dtype', c_int32)
    ]

    def __init__(self, obf_op, original_dtype, original_shape):
        super().__init__()
        self.op_type = obf_op[Constant.OP_TYPE_INDEX]
        self.dim = obf_op[Constant.OP_DIM_INDEX]
        if len(obf_op) == Constant.OP_CUSTOM_LEN_INDEX + 1:
            self.custom_start = obf_op[Constant.OP_CUSTOM_START_INDEX]
            self.custom_len = obf_op[Constant.OP_CUSTOM_LEN_INDEX]
        else:
            self.custom_start = 0
            self.custom_len = 0
        self.weight_rank = len(original_shape)
        # 填充shape信息
        self.shape = (c_int32 * 8)(*([0] * 8))
        for i, dim_size in enumerate(original_shape):
            if i < 8:
                self.shape[i] = dim_size
        self.dtype = TORCH_TO_DTYPE_ENUM.get(original_dtype, DType.FLOAT32.value)


# 设置CreateWeightObfuscator函数的参数类型和返回值类型
lib_obf_tool.CreateWeightObfuscator.argtypes = [
    POINTER(c_uint8),  # seed_data
    c_uint32,  # seed_len
    POINTER(ObfConfig)  # config
]
lib_obf_tool.CreateWeightObfuscator.restype = c_void_p

# 设置DestroyWeightObfuscator函数的参数类型和返回值类型
lib_obf_tool.DestroyWeightObfuscator.argtypes = [c_void_p]  # obfuscator
lib_obf_tool.DestroyWeightObfuscator.restype = None

# 设置ApplyWeightObfuscation函数的参数类型和返回值类型
lib_obf_tool.ApplyWeightObfuscation.argtypes = [
    c_void_p,  # obfuscator
    POINTER(c_uint8),  # weight_bytes
    c_uint32,  # weight_len
    POINTER(ObfOperation),  # operation
    POINTER(c_uint8)  # output_data
]
lib_obf_tool.ApplyWeightObfuscation.restype = c_int


def create_weight_obfuscator(seed_data, config):
    """
    创建权重混淆器对象
    
    Args:
        seed_data: 混淆因子字节数据 (bytes或bytearray)
        config: ObfConfig结构体，包含配置参数
    
    Returns:
        混淆器对象指针(c_void_p)
    
    Raises:
        ObfException: 创建失败时抛出异常
    """
    # 将seed_data转换为ctypes数组
    if isinstance(seed_data, bytes):
        seed_data = bytearray(seed_data)
    seed_len = len(seed_data)
    seed_array = (c_uint8 * seed_len)(*seed_data)

    # 调用C++接口创建混淆器对象
    obfuscator_ptr = lib_obf_tool.CreateWeightObfuscator(
        ctypes.cast(seed_array, POINTER(c_uint8)),
        c_uint32(seed_len),
        ctypes.byref(config)
    )

    if obfuscator_ptr is None:
        log.error("Failed to create weight obfuscator.")
        raise ObfException(ErrorCode.CREATE_OBFUSCATOR_FAILED.value)

    return obfuscator_ptr


def destroy_weight_obfuscator(obfuscator_ptr):
    """
    销毁权重混淆器对象
    
    Args:
        obfuscator_ptr: 混淆器对象指针(c_void_p)
    """
    if obfuscator_ptr is not None:
        lib_obf_tool.DestroyWeightObfuscator(obfuscator_ptr)


def apply_weight_obfuscation(obfuscator_ptr, weight_bytes, operation):
    """
    应用权重混淆

    Args:
        obfuscator_ptr: 混淆器对象指针(c_void_p)
        weight_bytes: 权重数据字节流 (bytes或bytearray)
        operation: ObfOperation结构体，包含混淆操作参数

    Returns:
        bytes: 混淆后的权重数据字节流

    Raises:
        ObfException: 混淆失败时抛出异常
    """
    # 准备输入数据 - 优化：直接转换bytes为ctypes数组，避免中间bytearray副本
    weight_len = len(weight_bytes)
    if isinstance(weight_bytes, bytes):
        # 使用from_buffer_copy创建ctypes数组，避免额外的bytearray副本
        # 对于大规模数据（如1.2GB），这可以避免复制bytearray的额外开销
        # 与原始实现保持一致的行为模式，但性能更高
        weight_array = (c_uint8 * weight_len).from_buffer_copy(weight_bytes)
    else:
        # 已经是bytearray，转换为ctypes数组
        weight_array = (c_uint8 * weight_len)(*weight_bytes)

    # 创建输出缓冲区（保持在函数作用域内）
    output_buffer = (c_uint8 * weight_len)()

    # 使用 try-except 捕获 ctypes 调用错误
    try:
        result = lib_obf_tool.ApplyWeightObfuscation(
            c_void_p(obfuscator_ptr),
            ctypes.cast(weight_array, POINTER(c_uint8)),
            c_uint32(weight_len),
            ctypes.byref(operation),
            ctypes.cast(output_buffer, POINTER(c_uint8))
        )
    except Exception as ctypes_error:
        raise ObfException(ErrorCode.APPLY_OBFUSCATION_FAILED.value) from ctypes_error

    if result != 0:
        log.error(f"Failed to apply weight obfuscation, error code: {result}")
        raise ObfException(ErrorCode.APPLY_OBFUSCATION_FAILED.value)

    # 转换为 bytes 对象（避免返回 ctypes 数组引用）
    output_bytes = bytes(output_buffer)
    return output_bytes
