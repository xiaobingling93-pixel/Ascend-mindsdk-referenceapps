#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""工具类
时间格式处理，定义数据结构，加载动态库，随机数生成等
"""

import ctypes
import os.path
from ctypes import Structure, POINTER, byref

from .c_lib import lib_obf_tool
from .log_util import log

UTF_8 = "utf-8"


class Bytes(Structure):
    _fields_ = [
        ('ptr', ctypes.c_char_p),
        ('size', ctypes.c_size_t),
    ]


class TlsMaterial(Structure):
    _fields_ = [
        ("cert_file", ctypes.c_char_p),
        ("pri_keyfile", ctypes.c_char_p),
        ("ca_file", ctypes.c_char_p),
        ("crl_file", ctypes.c_char_p),
        ("npu_ca_file", ctypes.c_char_p),
        ("version", ctypes.c_char_p),
        ("cipher_suite", ctypes.c_char_p),
        ("password", Bytes),
        ("ip", ctypes.c_char_p),
        ("port", ctypes.c_int16),
    ]


class PskMaterial(Structure):
    _fields_ = [
        ('psk_path', ctypes.c_char_p),
        ('password', Bytes),
    ]


class SeedInfo(Structure):
    _fields_ = [
        ('domain_id', ctypes.c_int),
        ('seed_name', ctypes.c_char_p),
        ('seed', POINTER(ctypes.c_ubyte)),
        ('seed_len', ctypes.c_int),
        ('device_id', POINTER(ctypes.c_uint32)),
        ('device_count', ctypes.c_int),
        ('seed_type', ctypes.c_int),
    ]


# 定义SeedFlag结构体
class SeedFlag(Structure):
    _fields_ = [
        ("domain_id", ctypes.c_int),
        ("seed_name", ctypes.c_char_p),
        ('device_id', POINTER(ctypes.c_uint32)),
        ("device_count", ctypes.c_int),
        ("seed_type", ctypes.c_int)
    ]


class DeviceInfo(Structure):
    _fields_ = [
        ("device_id", POINTER(ctypes.c_uint32)),
        ("device_count", ctypes.c_uint32)
    ]

# 设置函数参数类型和返回类型
lib_obf_tool.ObfRegSeed.argtypes = [
    POINTER(TlsMaterial),
    POINTER(SeedInfo),
    POINTER(PskMaterial)
]
lib_obf_tool.ObfRegSeed.restype = ctypes.c_int

lib_obf_tool.ObfDelSeed.argtypes = [
    POINTER(TlsMaterial),
    POINTER(SeedFlag)
]
lib_obf_tool.ObfDelSeed.restype = ctypes.c_int

lib_obf_tool.ObfQuerySeed.argtypes = [
    POINTER(TlsMaterial),
    POINTER(PskMaterial),
    POINTER(Bytes)
]
lib_obf_tool.ObfQuerySeed.restype = ctypes.c_int


def generate_tls(tls_info):
    buf = (ctypes.c_char * len(tls_info.passwd)).from_buffer(tls_info.passwd)
    passwd_byte = Bytes(
        # 入参为bytes，不会产生新内存，无需手动清理
        ptr=ctypes.cast(buf, ctypes.c_char_p),
        size=len(tls_info.passwd)
    )
    return TlsMaterial(
        ca_file=tls_info.ca_file.encode(UTF_8),
        cert_file=tls_info.cert_file.encode(UTF_8),
        npu_ca_file=tls_info.npu_ca_file.encode(UTF_8),
        version=tls_info.version.encode(UTF_8),
        cipher_suite=tls_info.cipher_suite.encode(UTF_8),
        pri_keyfile=tls_info.pri_keyfile.encode(UTF_8),
        password=passwd_byte,
        ip=tls_info.ip.encode(UTF_8),
        port=tls_info.port,
    )


def generate_psk(psk_info):
    buf = (ctypes.c_char * len(psk_info.passwd)).from_buffer(psk_info.passwd)
    psk_passwd_bytes = Bytes(
        # 入参为bytes，不会产生新内存，无需手动清理
        ptr=ctypes.cast(buf, ctypes.c_char_p),
        size=len(psk_info.passwd),
    )
    # 创建PSK材料结构体
    return PskMaterial(
        psk_path=psk_info.psk_path.encode(UTF_8),
        password=psk_passwd_bytes,
    )


def generate_seed_flag(device_id, seed_type):
    if device_id:
        device_id_array = (ctypes.c_uint32 * len(device_id))(*device_id)
        p_device_id = ctypes.cast(device_id_array, ctypes.POINTER(ctypes.c_uint32))
        device_count = len(device_id)
    else:
        p_device_id = None
        device_count = 0
    seed_name = 'obf_model_seed' if seed_type == 1 else 'obf_data_seed'
    # 初始化SeedFlag实例
    return SeedFlag(
        domain_id=15,
        seed_name=seed_name.encode(UTF_8),
        device_id=p_device_id,
        device_count=device_count,
        seed_type=seed_type,
    )


def generate_seed_info(device_id, seed_type, seed_content):
    if device_id:
        device_id_array = (ctypes.c_uint32 * len(device_id))(*device_id)
        p_device_id = ctypes.cast(device_id_array, ctypes.POINTER(ctypes.c_uint32))
        device_count = len(device_id)
    else:
        p_device_id = None
        device_count = 0

    # 创建种子信息结构体
    seed_name = 'obf_model_seed' if seed_type == 1 else 'obf_data_seed'
    return SeedInfo(
        domain_id=15,
        seed_name=seed_name.encode(UTF_8),
        # 入参为bytearray，不会产生新内存，无需手动清理
        seed=(ctypes.c_ubyte * len(seed_content)).from_buffer(seed_content),
        seed_len=len(seed_content),
        device_id=p_device_id,
        device_count=device_count,
        seed_type=seed_type
    )


def parameter_validation_file(parameter):
    if isinstance(parameter, str):
        if not os.path.exists(parameter) or len(parameter) > 4096:
            return False
        return True
    for file in parameter:
        if not os.path.exists(file) or len(file) > 4096:
            return False
    return True


def call_obf_reg_seed(seed_type, seed_content_bytearray, device_id, psk_conf, tls_conf):
    # 初始化 TlsMaterial
    tls_info_c = generate_tls(tls_conf)
    seed_info_c = generate_seed_info(device_id, seed_type, seed_content_bytearray)
    # 创建PSK材料结构体
    psk_info_c = generate_psk(psk_conf)
    # 调用注册函数
    return lib_obf_tool.ObfRegSeed(byref(tls_info_c), byref(seed_info_c), byref(psk_info_c))


def call_obf_del_seed(tls_info, device_id, seed_type):
    # 初始化 TlsMaterial
    tls_info_c = generate_tls(tls_info)
    seed_flag = generate_seed_flag(device_id, seed_type)
    # 调用删除函数
    return lib_obf_tool.ObfDelSeed(byref(tls_info_c), byref(seed_flag))


def generate_device_info(device_id):
    if device_id:
        device_id_array = (ctypes.c_uint32 * len(device_id))(*device_id)
        p_device_id = ctypes.cast(device_id_array, ctypes.POINTER(ctypes.c_uint32))
        device_count = len(device_id)
    else:
        p_device_id = None
        device_count = 0
    return DeviceInfo(p_device_id, device_count)



def call_obf_query_seed(tls_info, psk_info, device_id):
    # 初始化 TlsMaterial
    tls_info_c = generate_tls(tls_info)
    psk_info_c = generate_psk(psk_info)
    device_info = generate_device_info(device_id)
    # 创建数据密钥结构体
    dec_data_key = Bytes()
    # 调用查询函数
    result = lib_obf_tool.ObfQuerySeed(
        byref(tls_info_c),
        byref(psk_info_c),
        byref(dec_data_key),
        byref(device_info)
    )
    if result != 0:
        log.error(f"Failed to query seed, the result is {result}")
        return None
    seed_content = bytearray(dec_data_key.ptr)
    lib_obf_tool.SecureFreeBytes(byref(dec_data_key))
    return seed_content


def data_enc(ks_path, passwd, cipher_file_path):
    lib_obf_tool.EncryptData.argtypes = (
        ctypes.c_char_p, ctypes.POINTER(ctypes.c_ubyte), ctypes.c_uint, ctypes.c_char_p)
    lib_obf_tool.EncryptData.restype = ctypes.c_int  # 返回值类型
    data_len = len(passwd)
    data = (ctypes.c_ubyte * data_len).from_buffer(passwd)  # 创建一个字节数组
    res = lib_obf_tool.EncryptData(ks_path.encode(UTF_8), data, data_len, cipher_file_path.encode(UTF_8))
    for i in range(data_len):
        data[i] = 0
    del data
    return res


def date_dec(ks_path, cipher_file_path):
    lib_obf_tool.DecryptData.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_ubyte),
                                         ctypes.POINTER(ctypes.c_uint))
    lib_obf_tool.DecryptData.restype = ctypes.c_int  # 返回值类型
    data = (ctypes.c_ubyte * 128)()
    data_len = ctypes.c_uint(128)
    ret = lib_obf_tool.DecryptData(ks_path.encode(UTF_8), cipher_file_path.encode(UTF_8), data,
                                   ctypes.byref(data_len))
    if ret != 0:
        log.error(f"Failed to decrypt seed, the result is {ret}")
        decrypted_data = None
    else:
        decrypted_data = bytearray(data[:data_len.value])
    for i in range(data_len.value):
        data[i] = 0
    del data
    return decrypted_data


def data_enc_mul(ks_path, sensitive_data, enc_file_name):
    lib_obf_tool.EncryptData.argtypes = (
        ctypes.c_char_p, ctypes.POINTER(ctypes.c_ubyte), ctypes.c_uint, ctypes.c_char_p)
    lib_obf_tool.EncryptDataMul.restype = ctypes.c_int  # 返回值类型
    data_len = len(sensitive_data)
    data = (ctypes.c_ubyte * data_len).from_buffer(sensitive_data)  # 创建一个字节数组
    res = lib_obf_tool.EncryptDataMul(ks_path.encode(UTF_8), data, data_len, enc_file_name.encode(UTF_8))
    for i in range(data_len):
        data[i] = 0
    del data
    return res


def data_dec_mul(ks_path, enc_file_name):
    lib_obf_tool.DecryptData.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_ubyte),
                                         ctypes.POINTER(ctypes.c_uint))
    lib_obf_tool.DecryptDataMul.restype = ctypes.c_int  # 返回值类型
    data = (ctypes.c_ubyte * 128)()
    data_len = ctypes.c_uint(128)
    ret = lib_obf_tool.DecryptDataMul(ks_path.encode(UTF_8), enc_file_name.encode(UTF_8), data,
                                   ctypes.byref(data_len))
    if ret != 0:
        log.error(f"Failed to decrypt data mul, the result is {ret}")
        decrypted_data = None
    else:
        decrypted_data = bytearray(data[:data_len.value])
    for i in range(data_len.value):
        data[i] = 0
    del data
    return decrypted_data
