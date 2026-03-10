#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""混淆结构体构造和相关校验"""
import ctypes
import errno
import glob
import json
import math
import os
import shutil
import stat
from collections import defaultdict
from concurrent.futures import wait, FIRST_EXCEPTION, CancelledError
from ctypes import c_uint32
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import numpy as np
import torch
from safetensors import safe_open
from safetensors.torch import load_file, save_file

from .asset_obfuscation import AssetObfuscation
from ..constants import Constant, ErrorCode, ModelType, OpType
from ..exception import ObfException
from ..utils import (log, parameter_validation_file, check_device_space, clean_bytearray, thread_pools,
                     check_white_list, data_dec_mul)
from ..utils.c_utils.obf_api import (create_weight_obfuscator, destroy_weight_obfuscator, apply_weight_obfuscation,
                                     ObfConfig, ObfOperation, TORCH_TO_NP_DTYPE)


def parse_model_weight(model_path):
    files = glob.glob(os.path.join(model_path, "*.index.json"))
    if len(files) == 0:
        log.warning("The file suffix is [index.json] is not exist, use the empty map.")
        return None
    elif len(files) > 1:
        log.error("Found multiple files that suffix is [index.json].")
        raise ObfException(ErrorCode.FOUND_INDEX_JSON_ERROR.value)
    else:
        index_path = files[0]
    index_json = load_json(index_path)
    return index_json.get('weight_map', None)


def load_json(input_path: str) -> json:
    if not parameter_validation_file(input_path):
        log.error(f"The path validation failed, path: {input_path}")
        raise ObfException(ErrorCode.INVALID_CONFIG_PATH.value)
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        file_name = Path(input_path)
        log.error(f"The file: {file_name} is incorrect json format, {e}.")
        raise ObfException(f"{ErrorCode.INVALID_JSON_FILE.value}") from e


def parse_tp_num(common_config_json: json, tp_num: int) -> int:
    if tp_num is not None:
        final_tp_num = tp_num
    elif common_config_json is not None:
        final_tp_num = common_config_json.get("tp_num", None)
    else:
        final_tp_num = 1
    if (final_tp_num is not None and isinstance(final_tp_num, int)
            and final_tp_num in range(Constant.TP_NUM_MIN, Constant.TP_NUM_MAX + 1)):
        return final_tp_num
    else:
        log.error("The config param tp number validation failed.")
        raise ObfException(ErrorCode.INVALID_TP_NUM.value)


def is_obf_coefficient_valid(value, min_val, max_val, tolerance=1e-5):
    return math.isclose(value, 0.0) or min_val + tolerance <= value <= max_val + tolerance


def parse_obf_coefficient(common_config_json: json, obf_coefficient: float) -> float:
    if obf_coefficient is not None:
        final_obf_coefficient = obf_coefficient
    elif common_config_json is not None:
        final_obf_coefficient = common_config_json.get("obf_coefficient", None)
    else:
        final_obf_coefficient = Constant.OBF_COEFFICIENT_MAX
    if final_obf_coefficient is not None and isinstance(final_obf_coefficient, float) and \
            is_obf_coefficient_valid(final_obf_coefficient, Constant.OBF_COEFFICIENT_MIN, Constant.OBF_COEFFICIENT_MAX):
        return final_obf_coefficient
    else:
        log.error("The config param obf coefficient validation failed.")
        raise ObfException(ErrorCode.INVALID_OBF_COEFFICIENT.value)


def ignore_model_file(_dir, files):
    return [f for f in files if f.endswith('.safetensors') or f.endswith('.pth')]


def save_by_suffix(model, model_name, model_save, original_metadata):
    if model_name.endswith(".safetensors"):
        save_file(model, model_save, metadata=original_metadata)
    else:
        torch.save(model, model_save)


def load_by_suffix(model_name, model_load, model_weight_obf, specifies_device_id):
    device_name = model_weight_obf.get_current_device_type(specifies_device_id)
    original_metadata = None
    if model_name.endswith(".safetensors"):
        model = load_file(model_load, device=device_name)
        with safe_open(model_load, framework="pt", device=device_name) as f:
            original_metadata = f.metadata()
    else:
        model = torch.load(model_load, map_location=torch.device(device_name))
    return model, original_metadata


def get_reversed(obf_ops_list, is_reversed):
    return obf_ops_list if is_reversed else obf_ops_list[::-1]


def process_and_add_to_set(value, model_name_set):
    if not isinstance(value, list):
        value = [value]
    for ckpt in value:
        model_name_set.add(ckpt.split(":")[0] if ":" in ckpt else ckpt)
    return model_name_set


def is_assemble_cfg(obf_json):
    return "config" in obf_json


def select_mapping(obf_config_name):
    mapping = {}
    pos, data = "pos", "data"
    if obf_config_name == "model_protection_config.json":
        mapping = {
            "default_mode": {
                "self_attn.q_proj.weight": {pos: 1, data: [[7, 1]]},
                "self_attn.k_proj.weight": {pos: 1, data: [[7, 1]]},
                "self_attn.v_proj.weight": {pos: 1, data: [[7, 1]]},
            },
            "moe_mode": {
                "input_layernorm.weight": {pos: 1, data: [[7, 0]]},
                "self_attn.q_proj.weight": {pos: 1, data: [[7, 1]]},
                "self_attn.k_proj.weight": {pos: 1, data: [[7, 1]]},
                "self_attn.v_proj.weight": {pos: 1, data: [[7, 1]]},
                "self_attn.o_proj.weight": {pos: 1, data: [[7, 0]]},
                "post_attention_layernorm.weight": {pos: 1, data: [[7, 0]]},
                "mlp.gate.weight": {pos: 1, data: [[7, 1]]},
                "mlp.experts.gate_up_proj": {pos: 1, data: [[7, 1]]},
                "mlp.experts.down_proj": {pos: 2, data: [[7, 2]]},
                "linear_fc2.bias": {pos: 1, data: [[7, 0]]},
                "linear_fc2.weight": {pos: 1, data: [[7, 0]]},
                "model.language_model.norm.weight": {pos: 1, data: [[7, 0]]},
                "lm_head.weight": {pos: 1, data: [[7, 1]]}
            }
        }
    return mapping


def get_rule_for_key(template_key, mapping):
    # moe模型model.visual.merger.linear_fc2.bias、model.visual.merger.linear_fc2.weight不加[7,0]
    if template_key in {"model.visual.merger.linear_fc2.bias", "model.visual.merger.linear_fc2.weight"}:
        return None
    for keyword, rule in mapping.items():
        if keyword in template_key:
            return rule
    return None


class ObfParam:
    def __init__(self, precision_mode, model_save_path, device_type, device_id):
        self.precision_mode = precision_mode
        self.model_save_path = model_save_path
        self.device_type = device_type
        self.device_id = device_id

    def get_current_device_type(self, current_device_id):
        return (self.device_type + ':' + str(current_device_id)) if (self.device_type == 'npu') else self.device_type


class ModelObfParam:
    def __init__(self, model, model_name, current_device_id):
        self.model = model
        self.model_backbone = None
        self.model_name = model_name
        self.current_device_id = current_device_id
        self.current_model_weight = None
        self.weight_name = None

    def set_weight_name(self, weight_name):
        self.weight_name = weight_name

    def set_model_backbone(self, target_model):
        if target_model.find(":") != -1:
            self.model_backbone = target_model.split(":")[1]

    def get_model_weight(self):
        if self.model_backbone is None:
            return self.model.get(self.weight_name, None)
        else:
            backbone_weight = self.model.get(self.model_backbone, None)
            if backbone_weight is None:
                return None
            return backbone_weight.get(self.weight_name, None)

    def set_obf_model_weight(self, obf_model_tensor):
        if self.model_backbone is None:
            self.model[self.weight_name] = obf_model_tensor
        else:
            self.model[self.model_backbone][self.weight_name] = obf_model_tensor


def _check_save_path(model_save_path) -> bool:
    target = Path(model_save_path)
    parent = Path(os.path.dirname(model_save_path))
    if not parent.exists() or not parent.is_dir() or not os.access(parent, os.W_OK):
        log.error("The [model_save_path] is not exist or can not be write.")
        return False
    if target.exists():
        if target.is_file() or (target.is_dir() and os.listdir(target)):
            log.error("The [model_save_path] is a file or is a non-empty dir.")
            return False
    return True


def _check_obf_config(obf_config):
    """obf_config校验
    1 weight_value是一个二维数组，其中每一个元素是一个长度为2的list
    2 元素的第一个值op_type必须在opType的范围内
    3 元素的第二个值dim只能为0或者1
    """
    if not obf_config:
        log.error("obf_config is empty..")
        raise ObfException(ErrorCode.CONFIGURATION_FILE_FORMAT_ERROR.value)
    for _, weight_value in obf_config.items():
        for value in weight_value:
            if not isinstance(value, list) or (
                    len(value) != Constant.OP_DIM_INDEX + 1 and len(value) != Constant.OP_CUSTOM_LEN_INDEX + 1):
                log.error("The format or length of the value is incorrect.")
                raise ObfException(ErrorCode.CONFIGURATION_FILE_FORMAT_ERROR.value)
            if not value[0] in range((len(OpType))):
                log.error("The optype is not within the range of OpType. ")
                raise ObfException(ErrorCode.CONFIGURATION_FILE_FORMAT_ERROR.value)
            if not isinstance(value[1], int):
                log.error("The dim is not a int value.")
                raise ObfException(ErrorCode.CONFIGURATION_FILE_FORMAT_ERROR.value)
            if len(value) == Constant.OP_CUSTOM_LEN_INDEX + 1:
                _check_obf_custom_config(value)


def _check_obf_custom_config(value):
    if (len(value) != Constant.OP_CUSTOM_LEN_INDEX + 1 or
            not isinstance(value[Constant.OP_CUSTOM_START_INDEX], int) or
            not isinstance(value[Constant.OP_CUSTOM_LEN_INDEX], int)):
        log.error("The custom config is validation failed.")
        raise ObfException(ErrorCode.CONFIGURATION_FILE_FORMAT_ERROR.value)


def _check_device(device_type, device_id):
    if device_type not in ['cpu', 'npu']:
        log.error("The device type is out of range.")
        raise ObfException(ErrorCode.INVALID_DEVICE_TYPE.value)
    if device_type == 'npu':
        if not bool(device_id) or any(not isinstance(item, int) or item < 0 or item > 7 for item in device_id):
            log.error("The device id verification failed.")
            raise ObfException(ErrorCode.INVALID_DEVICE_ID.value)


def _check_local_save_path(is_local_save, seed_ciphertext_dir) -> bool:
    return is_local_save and isinstance(seed_ciphertext_dir, str) and not os.path.islink(seed_ciphertext_dir) \
        and os.path.exists(seed_ciphertext_dir)


@dataclass
class CreateParams:
    model_path: str
    obf_config_path: str
    tp_num: Optional[int] = None
    token_white_list: Optional[List] = None
    obf_coefficient: Optional[float] = None
    is_obfuscation: bool = True


def check_params(params):
    if params is None:
        log.error("The input params cannot be None.")
        raise ObfException(ErrorCode.INVALID_PARAM.value)
    if not isinstance(params, CreateParams):
        log.error("The input params must be an instance of CreateParams.")
        raise ObfException(ErrorCode.INVALID_PARAM.value)
    if not hasattr(params, 'model_path') or not hasattr(params, 'obf_config_path'):
        log.error("The input params must have both model_path and obf_config_path attributes.")
        raise ObfException(ErrorCode.INVALID_PARAM.value)


class ModelAssetObfuscation(AssetObfuscation):
    """创建ModelObfuscation类实例"""
    model_path = None
    obf_config_path = None
    torch_dtype = None
    hidden_size = None
    vocab_size = None
    white_set = None
    quantize = None
    tp_num = None
    num_attention_heads = None
    obf_config_map = {}
    weight_map = None
    obf_resources_map = {}
    data_seed_obf_resources = None  # GeneratedObfResources()
    model_seed_obf_resources = None  # GeneratedObfResources()
    obf_coefficient = None
    flag = None
    flag_config_path = None
    is_obfuscation = True
    num_hidden_layers = None
    head_dim = None
    model_type = None
    intermediate_size = None
    moe_intermediate_size = None
    num_experts = None
    depth = None
    vision_hidden_size = None
    c_obfuscator = None  # C++混淆器对象引用

    def __init__(self):
        if self.model_path is None:  # 防止直接调用init方法
            log.error("The model path is none.")
            raise ObfException(ErrorCode.MODEL_PATH_FAILED.value)

    @classmethod
    def create_model_obfuscation(cls, model_path: str, model_type: ModelType, tp_num: int = None,
                                 token_white_list: list = None, obf_coefficient: float = None,
                                 is_obfuscation: bool = True):
        if not isinstance(model_type, ModelType):
            log.error("The model type verification failed.")
            raise ObfException(ErrorCode.INVALID_MODEL_TYPE.value)
        real_config_path = os.path.join(Path(__file__).resolve().parent.parent, 'conf', model_type.value)
        params = CreateParams(
            model_path=os.path.realpath(model_path),
            obf_config_path=real_config_path,
            tp_num=tp_num,
            token_white_list=token_white_list,
            obf_coefficient=obf_coefficient,
            is_obfuscation=is_obfuscation)
        return cls.__create(params)

    @classmethod
    def create_custom_model_obfuscation(cls, model_path: str, custom_obf_config_path: str, tp_num: int = None,
                                        token_white_list: list = None, obf_coefficient: float = None,
                                        is_obfuscation: bool = True):
        params = CreateParams(
            model_path=os.path.realpath(model_path),
            obf_config_path=os.path.realpath(custom_obf_config_path),
            tp_num=tp_num,
            token_white_list=token_white_list,
            obf_coefficient=obf_coefficient,
            is_obfuscation=is_obfuscation)
        return cls.__create(params)

    @classmethod
    def __create(cls, params):

        """
        初始化函数，用于加载模型配置文件并设置相关参数

        :param model_path: 模型文件路径（包含配置文件和权重文件的存储目录）
        :return: 模型混淆实例
        :except: ObfException 参数校验错误或json格式错误

        类属性说明：
        - self.model_path: 模型根目录路径，用于后续模型文件的加载
        - self.torch_dtype: 模型参数的数据类型（如"float32"或"float16"，影响内存和计算精度）
        - self.hidden_size: 模型隐藏层的节点数量（神经网络的核心参数，决定模型复杂度）
        - self.vocab_size: 模型词汇表的大小（词嵌入层的维度，对应训练数据的词汇量）
        - self.quantize: 模型是否量化（用于模型压缩技术）
        - self.obf_embedding_map: 词汇表混淆映射表（None表示初始化，用于嵌入层混淆）
        - self.deobf_embedding_map: 词汇表解混淆映射表（初始值全为-1，长度与词汇表大小一致）
        - self.obf_weight_list: 权重混淆映射表（None表示初始化，用于权重矩阵混淆）
        - self.deobf_weight_map: 权重解混淆映射表（初始值全为-1，长度与隐藏层大小一致）
        - self.obf_coefficient: 权重解混淆系数（初始值为1, 范围为(0,1] ）
        - self.num_hidden_layers: 模型层数
        - self.head_dim: 注意力头维度
        - self.model_type: 模型类型
        - self.moe_intermediate_size: moe模型中间层大小
        - self.intermediate_size: 模型中间层大小
        - self.num_experts: 专家总数
        """
        # 检查 params 是否为 CreateParams 的实例
        check_params(params)
        if not parameter_validation_file((params.model_path, params.obf_config_path)):
            log.error("The model path or obf config path validation failed.")
            raise ObfException(ErrorCode.INVALID_PATH.value)
        if not isinstance(params.is_obfuscation, bool):
            log.error("The is_obfuscation verification failed.")
            raise ObfException(ErrorCode.INVALID_PARAM.value)
        self = cls.__new__(cls)
        self.model_path = params.model_path
        self.obf_config_path = params.obf_config_path
        common_conf_path = os.path.join(self.obf_config_path, 'common_config.json')
        common_config_json = None if not parameter_validation_file(common_conf_path) else load_json(common_conf_path)
        self.tp_num = parse_tp_num(common_config_json, params.tp_num)
        self.obf_coefficient = parse_obf_coefficient(common_config_json, params.obf_coefficient)
        self.is_obfuscation = params.is_obfuscation
        # 将模型路径和模型权重文件名拼接，得到模型权重文件的完整路径，并读取模型权重配置文件，用于接下来的模型权重修改,允许为空
        self.weight_map = parse_model_weight(self.model_path)
        model_config_path = os.path.join(self.model_path, 'config.json')
        flag_config_path = os.path.join(self.model_path, 'obf_config.json')
        # 加载配置文件各项属性并校验
        if parameter_validation_file(model_config_path):
            self._parse_model_config(model_config_path)
            self._validate()
            check_white_list(params.token_white_list, self.vocab_size)
            self.white_set = [] if params.token_white_list is None else set(params.token_white_list)
        if parameter_validation_file(flag_config_path):
            self.flag_config_path = flag_config_path
            self.flag = self._read_current_flag(self.flag_config_path)
        else:
            self.flag = Constant.UNCONFUSED
        self.c_obfuscator = None  # 初始化C++混淆器对象引用
        return self

    def set_seed_content(self, seed_type: int = Constant.MODEL_SEED_TYPE, seed_content: str = None,
                         is_local_save: bool = False, seed_ciphertext_dir: str = None):
        """输入混淆因子内容，用于模型混淆"""
        if seed_content is None:
            return self.set_from_local(is_local_save, seed_ciphertext_dir, seed_type)
        if seed_type not in [Constant.MODEL_SEED_TYPE, Constant.DATA_SEED_TYPE]:
            log.error("The seed type is not legal.")
            return ErrorCode.INVALID_SEED_TYPE.value
        if not isinstance(seed_content, str) or len(seed_content) > Constant.SEED_CONTENT_MAX_LEN or len(
                seed_content) < Constant.SEED_CONTENT_MIN_LEN:
            log.error("The obfuscate seed content len validation failed.")
            return ErrorCode.INVALID_SEED_CONTENT.value
        seed_content_bytes = bytearray(seed_content, "utf-8")
        set_seed_result = self._set_seed_core(seed_content_bytes, seed_type)
        clean_bytearray(seed_content_bytes)
        return set_seed_result

    def set_from_local(self, is_local_save, seed_ciphertext_dir, seed_type):
        if not _check_local_save_path(is_local_save, seed_ciphertext_dir):
            log.error("The parameter of local save validation failed.")
            return ErrorCode.INVALID_SEED_CONTENT.value
        if seed_type not in [Constant.MODEL_SEED_TYPE, Constant.DATA_SEED_TYPE]:
            log.error("The seed type is not legal.")
            return ErrorCode.INVALID_SEED_TYPE.value
        enc_file_name = Constant.MODEL_CIPHERTEXT_FILE_NAME if \
            seed_type == Constant.MODEL_SEED_TYPE else Constant.DATA_CIPHERTEXT_FILE_NAME
        seed_content_bytes = data_dec_mul(seed_ciphertext_dir, enc_file_name)
        # 解析为UTF-8字符串
        seed_content_str = seed_content_bytes.decode('utf-8')
        clean_bytearray(seed_content_bytes)
        # 使用重构后的set_seed_content接口（内部调用C++）
        return self.set_seed_content(seed_type, seed_content_str, is_local_save=False)

    def model_weight_obf(self, obf_type: int, precision_mode: int = None, model_save_path: str = None,
                         device_type: str = 'cpu', device_id: List[int] = None) -> (int, str):
        """
        对模型进行权重混淆

        参数:
        obf_type: 混淆类型，0表示同时进行两种模型权重混淆处理，1用于模型保护的模型权重混淆处理，2用于数据保护的模型权重混淆处理
        precision_model: 精度选择(可选0,1)  0为浮点计算模式  1为量化计算模式
        model_save_path: 混淆后模型存储路径
        device_type: 使用npu\cpu加速
        device_id: npu设备id, 当device_type是cpu时，可不传；当device_type是npu，device_id为空时，默认使用0号卡
        返回值:
        （errorcode， msg）

        异常描述:
        无
        """
        try:
            self._check_obf_type(obf_type)
            self._check_flag(obf_type)
            if device_id is None:
                device_id = [0]
            _check_device(device_type, device_id)
            # 根据精度模式选择掩码向量
            final_precision_mode = self._precision_mode_choose(precision_mode)
            final_model_save_path = self._preprocessing_save_path(model_save_path)
            obf_param = ObfParam(final_precision_mode, final_model_save_path, device_type, device_id)
            obf_result = self._obf_core(obf_type, obf_param)
            if obf_result == ErrorCode.SUCCESS.value:
                self._update_flag(obf_type, obf_param)
            return obf_result
        except ObfException as e:
            log.error("Failed to obfuscation the model weight.")
            return e.code, e.message
        finally:
            if self.c_obfuscator is not None:
                destroy_weight_obfuscator(self.c_obfuscator)
                self.c_obfuscator = None

    def _obf_core(self, obf_type, obf_param) -> (int, str):
        # 找到所有需要加载的模型文件
        all_model_name = self._get_models()
        if obf_param.device_type == 'npu':
            futures = []
            # 遍历 all_model_name，为每个元素启动一个线程池执行任务.
            for idx, model_name in enumerate(all_model_name):
                future = (thread_pools[idx % len(obf_param.device_id)]
                          .submit(self._obf_each_model, obf_type, model_name, obf_param,
                                  obf_param.device_id[idx % len(obf_param.device_id)]))
                futures.append(future)
            # 等待所有任务完成或超时
            done, not_done = wait(futures, return_when=FIRST_EXCEPTION)
            for future in not_done:
                future.cancel()
            for future in futures:
                try:
                    future.result()
                except ObfException as e:
                    log.error("The task in the thread pool has failed due to confusion.")
                    return e.code, e.message
                except CancelledError as e:
                    log.error(f"Some threads failed to execute and were canceled: {e}")
                    return ErrorCode.FAILED.value
            return ErrorCode.SUCCESS.value
        else:
            try:
                for model_name in all_model_name:
                    self._obf_each_model(obf_type, model_name, obf_param, obf_param.device_id)
                return ErrorCode.SUCCESS.value
            except ObfException as e:
                return e.code, e.message

    def _obf_each_model(self, obf_type, model_name, obf_param, current_device_id):
        # 拼接模型加载路径
        model_load = Path(self.model_path, model_name)
        if not os.path.exists(model_load):
            log.warning(f"The model weight file [{model_name}] is not exist.")
            return
        # 加载模型
        model, original_metadata = load_by_suffix(model_name, model_load, obf_param, current_device_id)
        model_obf_param = ModelObfParam(model, model_name, current_device_id)
        self._execute_by_obf_type(obf_type, obf_param, model_obf_param)
        try:
            model_save = Path(obf_param.model_save_path, model_name)
            if model_load == model_save:
                model_bak = Path(obf_param.model_save_path, model_name + ".bak")
                os.replace(model_save, model_bak)
                save_by_suffix(model, model_name, model_save, original_metadata)
                os.remove(model_bak)
            else:
                save_by_suffix(model, model_name, model_save, original_metadata)
        except OSError as e:
            if e.errno == errno.ENOSPC:
                log.error("There is insufficient disk space to store the model.")
                raise ObfException(ErrorCode.INSUFFICIENT_DISK_SPACE.value) from e
            log.error(f"An unknown I/O error has occurred: {e}.")
            raise ObfException(ErrorCode.IO_ERROR.value) from e
        log.info(f"The {model_name} confusing successful.")

    def _execute_by_obf_type(self, obf_type, obf_param, model_obf_param):
        if obf_type == Constant.OBF_BY_ALL_SEED:
            if self.is_obfuscation:
                self._obf_model_by_obf_config(obf_param, model_obf_param, self.obf_config_map[Constant.MODEL_SEED_TYPE])
                self._obf_model_by_obf_config(obf_param, model_obf_param, self.obf_config_map[Constant.DATA_SEED_TYPE])
            else:
                self._obf_model_by_obf_config(obf_param, model_obf_param, self.obf_config_map[Constant.DATA_SEED_TYPE])
                self._obf_model_by_obf_config(obf_param, model_obf_param, self.obf_config_map[Constant.MODEL_SEED_TYPE])
        elif obf_type == Constant.OBF_BY_MODEL_SEED:
            self._obf_model_by_obf_config(obf_param, model_obf_param, self.obf_config_map[Constant.MODEL_SEED_TYPE])
        else:
            self._obf_model_by_obf_config(obf_param, model_obf_param, self.obf_config_map[Constant.DATA_SEED_TYPE])

    def _obf_model_by_obf_config(self, obf_param, model_obf_param, obf_config):
        if self.c_obfuscator is None:
            log.error("C++ obfuscator not initialized. Call set_seed_content() first.")
            raise ObfException(ErrorCode.OBFUSCATOR_NOT_INITIALIZED.value)

        # 反转操作顺序用于解混淆
        reverse_ops = self.is_obfuscation

        if self.weight_map is None:
            for weight_name, obf_ops in obf_config.items():
                model_obf_param.set_weight_name(weight_name)
                obf_ops = get_reversed(obf_ops, reverse_ops)
                self._apply_weight_obf(model_obf_param, obf_ops, obf_param)
            return
        for weight_name, obf_ops in obf_config.items():
            if weight_name not in self.weight_map:
                log.warning("The weight name is not in safetensors weight map.")
                continue
            model_obf_param.set_weight_name(weight_name)
            model_weight_value = self.weight_map[weight_name]
            obf_ops = get_reversed(obf_ops, reverse_ops)
            if not isinstance(model_weight_value, List):
                self._obf_model_match_target(obf_param, model_obf_param, obf_ops, model_weight_value)
            else:
                for target_model in model_weight_value:
                    self._obf_model_match_target(obf_param, model_obf_param, obf_ops, target_model)

    def _obf_model_match_target(self, obf_param, model_obf_param, obf_ops, model_weight_value):
        if model_weight_value.find(model_obf_param.model_name) == -1:
            return
        model_obf_param.set_model_backbone(model_weight_value)
        self._apply_weight_obf(model_obf_param, obf_ops, obf_param)

    def _apply_weight_obf(self, model_obf_param, obf_ops, obf_param):
        """使用C++混淆接口对模型权重进行混淆"""
        model_weight = model_obf_param.get_model_weight()
        if model_weight is None:
            log.warning(f"Model weight {model_obf_param.weight_name} not found, skip obfuscation.")
            return

        original_shape = model_weight.shape
        original_dtype = model_weight.dtype
        weight_tensor = model_weight.cpu().float() if original_dtype == torch.bfloat16 else model_weight.cpu()
        conversion_dtype = TORCH_TO_NP_DTYPE.get(original_dtype)
        if conversion_dtype is None:
            log.warning(f"Unsupported dtype {original_dtype}, using float32 as fallback")
            weight_tensor = weight_tensor.float()
            conversion_dtype = np.float32
        weight_bytes = weight_tensor.numpy().tobytes()
        # 创建输出缓冲区
        output_buffer = bytearray(len(weight_bytes))

        # 对每个操作应用混淆
        for obf_op in obf_ops:
            # 检查操作格式
            self._check_obf_op(obf_op)
            # 准备ObfOperation结构
            operation = ObfOperation(obf_op, original_dtype, original_shape)
            # 调用C++混淆接口
            input_data = weight_bytes if obf_op == obf_ops[0] else output_buffer
            output_buffer = apply_weight_obfuscation(self.c_obfuscator, input_data, operation)

        # 使用conversion_dtype来解析bytes（因为可能发生了dtype转换）
        try:
            obf_array = np.frombuffer(output_buffer, dtype=conversion_dtype).copy()
        except Exception as np_error:
            raise ObfException(ErrorCode.APPLY_OBFUSCATION_FAILED.value) from np_error
        obf_tensor = torch.from_numpy(obf_array).reshape(original_shape).to(original_dtype)
        # 写回模型权重
        model_obf_param.set_obf_model_weight(obf_tensor)

    def _check_obf_op(self, obf_op):
        if not isinstance(obf_op, list) or (
                len(obf_op) != Constant.OP_DIM_INDEX + 1 and len(obf_op) != Constant.OP_CUSTOM_LEN_INDEX + 1):
            log.error("The format or length of the value is incorrect.")
            raise ObfException(ErrorCode.CONFIGURATION_FILE_FORMAT_ERROR.value)

    def _check_obf_type(self, obf_type):
        if obf_type not in [Constant.OBF_BY_ALL_SEED, Constant.OBF_BY_MODEL_SEED, Constant.OBF_BY_DATA_SEED]:
            log.error("The [obf_type] is invalid.")
            raise ObfException(ErrorCode.INVALID_OBF_TYPE.value)

    def _check_flag_obf(self, obf_type):
        if self.flag == Constant.MODEL_CONFUSED and obf_type != Constant.OBF_BY_DATA_SEED:
            log.error("Model weight obfuscation for model protection has already been completed.")
            raise ObfException(ErrorCode.MODEL_ALREADY_OBFUSCATED.value)
        if self.flag == Constant.DATA_CONFUSED and obf_type != Constant.OBF_BY_MODEL_SEED:
            log.error("Model weight obfuscation for data protection has already been completed.")
            raise ObfException(ErrorCode.DATA_ALREADY_OBFUSCATED.value)
        if self.flag == Constant.BOTH_CONFUSED:
            log.error("Model and data protection via weight obfuscation has already been completed.")
            raise ObfException(ErrorCode.OBFUSCATION_ALREADY_COMPLETED.value)

    def _check_flag_deobf(self, obf_type):
        # 解混淆：当前仅支持基于数据混淆因子保护的模型
        if self.flag != Constant.DATA_CONFUSED:
            log.error("De-obfuscation is only supported for models protected by data seed.")
            raise ObfException(ErrorCode.INVALID_DE_OBFUSCATION.value)
        if self.flag == Constant.DATA_CONFUSED and obf_type != Constant.OBF_BY_DATA_SEED:
            log.error("Model weights are data-seed obfuscated, and can only be de-obfuscation with data seed.")
            raise ObfException(ErrorCode.INVALID_DE_OBFUSCATION.value)

    def _check_flag(self, obf_type):
        if self.flag is None or self.flag not in \
                [Constant.UNCONFUSED, Constant.MODEL_CONFUSED, Constant.DATA_CONFUSED, Constant.BOTH_CONFUSED]:
            log.error("The flag is invalid.")
            raise ObfException(ErrorCode.INVALID_FLAG.value)
        if self.is_obfuscation:
            self._check_flag_obf(obf_type)
        elif self.flag_config_path is not None:
            self._check_flag_deobf(obf_type)
        else:
            log.warning("Missing obf_config.json, unable to guarantee the correctness of de-obfuscation.")

    def _read_current_flag(self, flag_config_path) -> str:
        try:
            with open(flag_config_path, 'r', encoding='utf-8') as f:
                flag_config = json.load(f)
            self.flag = flag_config.get("flag", Constant.UNCONFUSED)
            log.info(f"Current flag state read: {self.flag}")
            return self.flag
        except Exception as e:
            log.error("Failed to read flag config")
            raise ObfException(ErrorCode.READ_CONFIG_ERROR.value) from e

    def _update_flag(self, obf_type, obf_param):
        if not self.is_obfuscation and self.flag_config_path is None:
            return
        if self.is_obfuscation:
            if self.flag == Constant.UNCONFUSED:
                new_state = {Constant.OBF_BY_MODEL_SEED: Constant.MODEL_CONFUSED,
                             Constant.OBF_BY_DATA_SEED: Constant.DATA_CONFUSED}.get(obf_type, Constant.BOTH_CONFUSED)
            else:
                new_state = Constant.BOTH_CONFUSED
        else:
            new_state = Constant.UNCONFUSED
        obf_flag_config = {"flag": new_state}
        self.flag_config_path = os.path.join(obf_param.model_save_path, 'obf_config.json')
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        modes = stat.S_IRUSR | stat.S_IWUSR
        try:
            with os.fdopen(os.open(self.flag_config_path, flags, modes), mode='w', encoding='utf-8') as f:
                json.dump(obf_flag_config, f, indent=4, ensure_ascii=False)
            log.info("Update obf_config.json successful.")
        except Exception as e:
            log.error("Failed to update obf_config.json.")
            raise ObfException(ErrorCode.UPDATE_CONFIG_ERROR.value) from e

    def _validate(self):
        if self.torch_dtype is None or self.torch_dtype not in ['int8', 'float32', 'float16', 'bfloat16']:
            log.error("The model config does not have the [torch_dtype] property.")
            raise ObfException(ErrorCode.MODEL_CONFIG_INVALID_TORCH_TYPE.value)
        if self.hidden_size is None or not isinstance(self.hidden_size, int):
            log.error("The model config does not have the [hidden_size] property or property invalid.")
            raise ObfException(ErrorCode.MODEL_CONFIG_INVALID_HIDDEN_SIZE.value)
        if self.hidden_size % self.tp_num != 0:
            log.error("The model config [hidden_size] property can not be divided by [tp_num].")
            raise ObfException(ErrorCode.MODEL_CONFIG_INVALID_HIDDEN_SIZE.value)
        if self.vocab_size is None or not isinstance(self.vocab_size, int):
            log.error("The model config does not have the [vocab_size] property or property invalid.")
            raise ObfException(ErrorCode.MODEL_CONFIG_INVALID_VOCAB_SIZE.value)
        if self.num_hidden_layers is None or not isinstance(self.num_hidden_layers, int):
            log.error("The model config does not have the [num_hidden_layers] property or property invalid.")
            raise ObfException(ErrorCode.MODEL_CONFIG_INVALID_NUM_HIDDEN_LAYERS.value)
        self._validate_moe_parameters()
        self._validate_vision_parameters()
        self._validate_num_attention_heads()

    def _validate_num_attention_heads(self):
        if (self.num_attention_heads is None or not isinstance(self.num_attention_heads, int)
                or self.num_attention_heads == 0):
            log.error("The model config does not have the [num_attention_heads] property or property invalid.")
            raise ObfException(ErrorCode.MODEL_CONFIG_INVALID_NUM_ATTENTION_HEADS.value)
        # 检查hidden_size是否能被num_attention_heads整除
        if self.hidden_size % self.num_attention_heads != 0:
            log.error("The model config [hidden_size] property can not be divided by [num_attention_heads].")
            raise ObfException(ErrorCode.MODEL_CONFIG_INVALID_HIDDEN_SIZE.value)
        # 检查head_dim，如果head_dim为None,那hidden_size除以num_attention_heads的结果要为偶数
        if self.head_dim is None and (self.hidden_size // self.num_attention_heads) % 2 != 0:
            log.error("The [head_dim] is none and hidden_size//num_attention_heads is not an even number.")
            raise ObfException(ErrorCode.MODEL_CONFIG_INVALID_HEAD_DIM.value)
        # 检查head_dim，如果head_dim不为None,那head_dim必须为偶数
        if self.head_dim is not None and not isinstance(self.head_dim, int) and self.head_dim % 2 != 0:
            log.error("The [head_dim] is invalid.")
            raise ObfException(ErrorCode.MODEL_CONFIG_INVALID_HEAD_DIM.value)

    def _get_models(self):
        model_name_set = set()
        if self.weight_map:
            for _, value in self.weight_map.items():
                model_name_set = process_and_add_to_set(value, model_name_set)
        else:
            expect_model_name = 'quant_model_description_w8a8.safetensors' if self.quantize else 'model.safetensors'
            expect_model_path = Path(os.path.join(self.model_path, expect_model_name))
            if expect_model_path.exists() and expect_model_path.is_file():
                model_name_set.add(expect_model_name)
            else:
                log.error(f"The weight_map is empty and can not find [{expect_model_name}]")
        if not model_name_set:
            log.error("Can find any model file.")
            raise ObfException(ErrorCode.GET_MODEL_LIST_FAILED.value)
        return model_name_set

    def _precision_mode_choose(self, precision_mode):
        # 如果precision_model为None，根据quantize的值设定precision_model
        if precision_mode is None:
            return 1 if self.quantize else 0
        if precision_mode in [0, 1]:
            return precision_mode
        log.error("The [precision_mode] is not None but is invalid.")
        raise ObfException(ErrorCode.INVALID_PARAM.value)

    def _preprocessing_save_path(self, model_save_path):
        if model_save_path is None:
            return self.model_path
        if os.path.islink(model_save_path):
            log.error("The [model_save_path] is a soft link.")
            raise ObfException(ErrorCode.INVALID_PATH.value)
        if not isinstance(model_save_path, str):
            log.error("The [model_save_path] is not None but is invalid path.")
            raise ObfException(ErrorCode.INVALID_PATH.value)
        real_save_path = os.path.normpath(model_save_path)
        if not _check_save_path(real_save_path):
            raise ObfException(ErrorCode.INVALID_PATH.value)
        if not check_device_space(self.model_path, real_save_path):
            log.error("There is insufficient disk space to store the model.")
            raise ObfException(ErrorCode.INSUFFICIENT_DISK_SPACE.value)
        self._copy_config_to_save_path(real_save_path)
        return real_save_path

    def _copy_config_to_save_path(self, model_save_path):
        shutil.copytree(self.model_path, model_save_path, ignore=ignore_model_file, dirs_exist_ok=True)
        log.info("Success to copy model config files to model save path.")

    def _set_seed_core(self, seed_content_bytes, seed_type):
        # 解析配置文件
        result = self._parse_obf_conf(seed_type)
        if result != ErrorCode.SUCCESS.value:
            log.error("Failed to parse obfuscate config.")
            return result

        obf_c_config = self._generate_c_config()
        # 设置白名单
        self._add_white_list_for_config(obf_c_config)

        try:
            self.c_obfuscator = create_weight_obfuscator(seed_content_bytes, obf_c_config)
            return ErrorCode.SUCCESS.value
        except Exception as e:
            log.error(f"Failed to create C obfuscator.: {e}")
            if self.c_obfuscator is not None:
                destroy_weight_obfuscator(self.c_obfuscator)
                self.c_obfuscator = None
            return ErrorCode.CREATE_OBFUSCATOR_FAILED.value
        finally:
            clean_bytearray(seed_content_bytes)

    def _add_white_list_for_config(self, obf_c_config):
        white_list_list = list(self.white_set) if self.white_set else []
        white_list_length = len(white_list_list)
        if white_list_length > 0:
            c_white_list = (c_uint32 * white_list_length)(*white_list_list)
            obf_c_config.white_list = ctypes.cast(c_white_list, ctypes.POINTER(c_uint32))
            obf_c_config.white_list_length = white_list_length
        else:
            obf_c_config.white_list = None
            obf_c_config.white_list_length = 0

    def _choose_obf_conf(self, seed_type):
        if seed_type == Constant.MODEL_SEED_TYPE:
            return "model_protection_config.json"
        if self.obf_config_map.get(Constant.MODEL_SEED_TYPE, None):
            return "data_protection_config_model_confused.json"
        if self.is_obfuscation and self.flag == Constant.MODEL_CONFUSED:
            return "data_protection_config_model_confused.json"
        return "data_protection_config.json"

    def _parse_obf_conf(self, seed_type: int):
        obf_config_name = self._choose_obf_conf(seed_type)
        config_path = os.path.join(self.obf_config_path, obf_config_name)
        try:
            self.obf_config_map[seed_type] = self._assemble_completion_cfg(
                load_json(config_path),
                obf_config_name
            )
            _check_obf_config(self.obf_config_map[seed_type])
            return ErrorCode.SUCCESS.value
        except ObfException as e:
            return e.code, e.message

    def _assemble_completion_cfg(self, obf_json, obf_config_name):
        if not is_assemble_cfg(obf_json):
            return obf_json
        expanded_dict = {}
        weight_map = obf_json.get("weight_map", {})
        for key, value in weight_map.items():
            if "{index}" in key:
                self._process_index_key(key, value, expanded_dict, obf_config_name)
            elif "{vision_index}" in key:
                self._process_vision_key(key, value, expanded_dict)
            else:
                moe_mapping = select_mapping(obf_config_name).get("moe_mode", {})
                current_value = list(value)
                if self._is_moe_model() and self._is_vision_model() and moe_mapping:
                    self._add_rule_for_key(key, moe_mapping, current_value)
                expanded_dict[key] = current_value

        return expanded_dict

    def _add_rule_for_key(self, key, mapping, current_value):
        rule = get_rule_for_key(key, mapping)
        if rule:
            pos, data = rule["pos"], rule["data"]
            current_value[pos:pos] = data

    def _process_index_key(self, key, value, expanded_dict, obf_config_name):
        """处理包含 {index} 的键"""
        for i in range(self.num_hidden_layers):
            tmp_key = key.replace("{index}", str(i))
            # 处理 MoE 模型的 experts
            if self._is_moe_model() and "{experts_index}" in key:
                self._process_expert_keys(tmp_key, value, expanded_dict, obf_config_name, i)
            else:
                self._process_regular_index_key(tmp_key, value, expanded_dict, obf_config_name, i)

    def _has_any_qkv_weight(self, s: str) -> bool:
        keys = [
            "self_attn.q_proj.weight",
            "self_attn.k_proj.weight",
            "self_attn.v_proj.weight"
        ]
        return any(key in s for key in keys)

    def _process_moe_index(self, new_key, current_value, i):
        """去除moe模型第0层,q,k,v的第1层[7,0]或[7,1]"""
        if not self._is_moe_model():
            return current_value
        if i == 0 or (i == 1 and self._has_any_qkv_weight(new_key)):
            current_value = [x for x in current_value if x not in [[7, 1], [7, 0]]]
        return current_value

    def _process_expert_keys(self, tmp_key, value, expanded_dict, obf_config_name, i):
        """处理 expert 相关的键"""
        default_mapping = select_mapping(obf_config_name).get("default_mode", {})
        for j in range(self.num_experts):
            new_key = tmp_key.replace("{experts_index}", f".experts.{j}")
            current_value = list(value)
            if i == 0 and default_mapping:
                self._add_rule_for_key(tmp_key, default_mapping, current_value)
            expanded_dict[new_key] = self._process_moe_index(new_key, current_value, i)

    def _process_regular_index_key(self, tmp_key, value, expanded_dict, obf_config_name, i):
        """处理普通的 index 键"""
        new_key = tmp_key.replace("{experts_index}", "")
        current_value = list(value)
        default_mapping = select_mapping(obf_config_name).get("default_mode", {})
        moe_mapping = select_mapping(obf_config_name).get("moe_mode", {})
        if self._is_moe_model() and self._is_vision_model() and moe_mapping:
            self._process_vlmoe_regular_index_key(tmp_key, moe_mapping, default_mapping, current_value, i)
        else:
            if i == 0 and default_mapping:
                self._add_rule_for_key(tmp_key, default_mapping, current_value)
        expanded_dict[new_key] = self._process_moe_index(new_key, current_value, i)

    def _process_vlmoe_regular_index_key(self, tmp_key, moe_mapping, default_mapping, current_value, i):
        if i > 0 and moe_mapping:
            self._add_rule_for_key(tmp_key, moe_mapping, current_value)
        if i == 1 and default_mapping:
            rule = get_rule_for_key(tmp_key, default_mapping)
            if rule:
                pos, data = rule["pos"], rule["data"]
                delete_length = len(data)
                current_value = current_value[:pos] + current_value[pos + delete_length:]

    def _process_vision_key(self, key, value, expanded_dict):
        """处理包含 {vision_index} 的键"""
        for j in range(self.depth):
            new_key = key.format(vision_index=j)
            expanded_dict[new_key] = list(value)

    def _is_moe_model(self):
        return "moe" in self.model_type.lower()

    def _is_vision_model(self):
        return "qwen3_vl" in self.model_type.lower()

    def _parse_model_config(self, model_config_path):
        model_config = load_json(model_config_path)
        self.model_type = model_config.get("model_type")
        if self._is_vision_model():
            self._parse_vision_model_config(model_config)
        else:
            self.torch_dtype = model_config.get("torch_dtype")
            self.hidden_size = model_config.get("hidden_size")
            self.vocab_size = model_config.get("vocab_size")
            self.quantize = model_config.get("quantize")
            self.num_attention_heads = model_config.get("num_attention_heads")
            self.num_hidden_layers = model_config.get("num_hidden_layers")
            self.head_dim = model_config.get("head_dim")
            self.moe_intermediate_size = model_config.get("moe_intermediate_size")
            self.intermediate_size = model_config.get("intermediate_size")
            self.num_experts = model_config.get("num_experts")

    def _validate_moe_parameters(self):
        if self._is_moe_model():
            if self.moe_intermediate_size is None or not isinstance(self.moe_intermediate_size, int):
                log.error("The model config does not have the [moe_intermediate_size] property or property invalid.")
                raise ObfException(ErrorCode.MODEL_CONFIG_INVALID_MOE_INTERMEDIATE_SIZE.value)
            if self.num_experts is None or not isinstance(self.num_experts, int):
                log.error("The model config does not have the [num_experts] property or property invalid.")
                raise ObfException(ErrorCode.MODEL_CONFIG_INVALID_NUM_EXPERTS.value)
        else:
            if self.intermediate_size is None or not isinstance(self.intermediate_size, int):
                log.error("The model config does not have the [intermediate_size] property or property invalid.")
                raise ObfException(ErrorCode.MODEL_CONFIG_INVALID_INTERMEDIATE_SIZE.value)

    def _validate_vision_parameters(self):
        if self._is_vision_model() and (self.depth is None or not isinstance(self.depth, int)):
            log.error("The model config does not have the [depth] property or property invalid.")
            raise ObfException(ErrorCode.MODEL_CONFIG_INVALID_DEPTH.value)

    def _parse_vision_model_config(self, model_config):
        text_config = model_config.get("text_config", "")
        if not text_config:
            log.error("The model config does not have the [text_config] property or property invalid.")
            raise ObfException(ErrorCode.MODEL_CONFIG_INVALID_TEXT_CONFIG.value)
        self.torch_dtype = text_config.get('dtype')
        self.hidden_size = text_config.get('hidden_size')
        self.vocab_size = text_config.get('vocab_size')
        self.quantize = text_config.get('quantize')
        self.num_attention_heads = text_config.get('num_attention_heads')
        self.num_hidden_layers = text_config.get('num_hidden_layers')
        self.head_dim = text_config.get("head_dim")
        self.moe_intermediate_size = text_config.get("moe_intermediate_size")
        self.intermediate_size = text_config.get("intermediate_size")
        self.num_experts = text_config.get("num_experts")

        vision_config = model_config.get("vision_config", "")
        if not vision_config:
            log.error("The model config does not have the [vision_config] property or property invalid.")
            raise ObfException(ErrorCode.MODEL_CONFIG_INVALID_VISION_CONFIG.value)
        self.depth = vision_config.get('depth')
        self.vision_hidden_size = vision_config.get('hidden_size')
    
    def _generate_c_config(self):
        obf_config = ObfConfig()
        obf_config.hidden_size = self.hidden_size or 0
        obf_config.vocab_size = self.vocab_size or 0
        obf_config.intermediate_size = self.intermediate_size or 0
        obf_config.moe_intermediate_size = self.moe_intermediate_size or 0
        obf_config.head_dim = self.head_dim or 0
        obf_config.num_attention_heads = self.num_attention_heads or 0
        obf_config.vision_hidden_size = self.vision_hidden_size or 0
        obf_config.tp_num = self.tp_num
        obf_config.obf_coefficient = self.obf_coefficient
        obf_config.is_obfuscation = self.is_obfuscation
        return obf_config
