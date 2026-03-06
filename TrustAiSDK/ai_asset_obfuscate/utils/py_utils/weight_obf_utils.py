#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""模型混淆工具类
根据操作类型不同，对数据做不同处理，包括混淆，解混淆，embedding混淆，lm_head解混淆，加乘法掩码，解加乘法掩码
"""

import torch

from .. import log
from ...exception import ObfException
from ...constants import OpType, ErrorCode, Constant


class WeightObfParam:
    def __init__(self, obf_param, model_obf_param, obf_op):
        self.obf_op = obf_op
        self.obf_param = obf_param
        self.op_type = obf_op[Constant.OP_TYPE_INDEX]
        self.dim = obf_op[Constant.OP_DIM_INDEX]
        self.weight_name = model_obf_param.weight_name
        self.model_weight = model_obf_param.get_model_weight()
        self.device_type = obf_param.get_current_device_type(model_obf_param.current_device_id)

    def base_obf_function(self, obf_tensor, layer_obf_function, *args):
        return layer_obf_function(self.model_weight, self.weight_name, obf_tensor.to(self.device_type), self.dim, *args)


def layer_part_clo_obf(model_layer, weight_name, obf_tensor, dim, start=0):
    """模型层进行部分混淆，如果本层的长度和perm一致时，会全部混淆
    Args：
        model_layer: torch.Tensor
        perm: 根据混淆因子生成的混淆list
        dim: int 0/1
    Return:
        混淆后的模型层
    Raise:
        ObfException: 当前层不支持该类型的混淆算法
    """
    total_len = model_layer.shape[dim]
    obf_tensor_len = len(obf_tensor)
    if total_len < start + obf_tensor_len:
        log.error(f"The model layer is too short, please check obf config file, weight_name: {weight_name}.")
        raise ObfException(ErrorCode.UNSUPPORTED_OP_TYPE.value)
    part1, part2, part3 = torch.split(model_layer, [start, obf_tensor_len, total_len - obf_tensor_len - start], dim=dim)
    return torch.cat([part1, torch.index_select(part2, dim, obf_tensor), part3], dim)


def layer_split_col_obf(model_layer, weight_name, obf_tensor, dim):
    """主要用户DS满血版的MTP模式，模型层进行平均分割混淆，要求该层长度是perm的两倍
    Args：
        model_layer: torch.Tensor
        perm: 根据混淆因子生成的混淆list
        dim: int 0/1
    Return:
        混淆后的模型层
    Raise:
        ObfException: 当前层不支持该类型的混淆算法
    """
    obf_tensor_len = len(obf_tensor)
    total_len = model_layer.shape[dim]
    if total_len != obf_tensor_len + obf_tensor_len:
        log.error(f"The model layer length is not twice the hidden size, please check obf config file, "
                  f"weight_name: {weight_name}.")
        raise ObfException(ErrorCode.UNSUPPORTED_OP_TYPE.value)
    part1, part2 = torch.split(model_layer, [obf_tensor_len, obf_tensor_len], dim=dim)
    return torch.cat([torch.index_select(part1, dim, obf_tensor), torch.index_select(part2, dim, obf_tensor)], dim)


def layer_segment_switch_obf(model_layer, weight_name, obf_tensor, dim, is_obfuscation):
    obf_tensor_len = len(obf_tensor)
    total_len = model_layer.shape[dim]
    part_size = 2 * obf_tensor_len
    if total_len % part_size != 0:
        log.error(f"The model layer length cannot be divided by twice as obf_tensor_len, please check obf config file,"
                  f" weight_name: {weight_name}.")
        raise ObfException(ErrorCode.UNSUPPORTED_OP_TYPE.value)
    part_array = torch.split(model_layer, part_size, dim=dim)

    # 预处理perm，生成所有需要交换的索引对
    swap_indices = []
    for i in range(0, obf_tensor_len):
        if obf_tensor[i] == 1:
            swap_indices.append((i, obf_tensor_len + i))

    # 如果没有需要交换的索引对，直接返回
    if not swap_indices:
        return model_layer

    # 处理每个块
    processed_parts = []
    for part in part_array:
        # 复制原始部分作为基础
        new_part = part.clone()

        # 处理需要交换的部分
        for i, j in swap_indices:
            if i >= part_size or j >= part_size:
                continue
            # 交换第i和第j个元素 创建选择这两个索引的张量
            indices = torch.tensor([i, j], dtype=torch.long, device=part.device)
            # 获取这两个位置的值 并交换它们
            values = torch.index_select(part, dim, indices)
            swapped_values = values.flip(0)
            swapped_values[0] = -swapped_values[0]
            if not is_obfuscation:
                swapped_values *= -1
            # 将交换后的值放回到new_part中
            new_part.index_copy_(dim, indices, swapped_values)
        processed_parts.append(new_part)
    # 拼接所有块
    return torch.cat(processed_parts, dim=dim)


def layer_segment_neg_obf(model_layer, weight_name, obf_tensor, dim):
    obf_tensor_len = len(obf_tensor)
    total_len = model_layer.shape[dim]
    if total_len % (2 * obf_tensor_len) != 0:
        log.error(f"The model layer length cannot be divided by twice as obf_tensor_len, please check obf config file,"
                  f" weight_name: {weight_name}.")
        raise ObfException(ErrorCode.UNSUPPORTED_OP_TYPE.value)
    obf_segment_list = torch.where(obf_tensor == 1)[0].tolist()
    neg_indices = [
        i * obf_tensor_len + local
        for i in range(total_len // obf_tensor_len)
        for local in obf_segment_list
    ]
    tmp_layer = model_layer.clone()
    idx = [slice(None)] * tmp_layer.ndim
    idx[dim] = neg_indices
    tmp_layer[tuple(idx)] *= -1
    return tmp_layer


def layer_segment_col_obf(model_layer, weight_name, obf_tensor, dim):
    total_len = model_layer.shape[dim]
    obf_tensor_len = len(obf_tensor)
    # 检查model_layer的长度是否是perm_len的倍数
    if total_len % obf_tensor_len != 0:
        log.error(f"The model layer length cannot be divided by obf_tensor_len, please check obf config file,"
                  f" weight_name: {weight_name}.")
        raise ObfException(ErrorCode.UNSUPPORTED_OP_TYPE.value)
    # 分割model_layer为多个块，每个块的长度为perm_len
    parts = torch.split(model_layer, obf_tensor_len, dim=dim)
    # 处理每个块
    processed_parts = []
    for part in parts:
        # 调用layer_part_clo_obf函数进行混淆处理
        obfuscated_block = layer_part_clo_obf(part, weight_name, obf_tensor, dim)
        processed_parts.append(obfuscated_block)
    # 拼接所有块
    return torch.cat(processed_parts, dim=dim)


def obf_weight_by_op_type(obf_param, model_obf_param, obf_op, obf_resources, is_obfuscation=True):
    params = WeightObfParam(obf_param, model_obf_param, obf_op)
    # 定义处理函数映射
    handlers = {
        OpType.ROW_SHUFFLE.value: handle_shuffle,
        OpType.COL_SHUFFLE.value: handle_shuffle,
        OpType.CUSTOM_COL_SHUFFLE.value: handle_shuffle,
        OpType.COL_SHUFFLE_ADDIN.value: handle_shuffle,
        OpType.MTP_COL_SHUFFLE.value: handle_mtp_col_shuffle,
        OpType.MUL_MASK.value: handle_mul_mask,
        OpType.COL_SHUFFLE_COEFFICIENT.value: handle_shuffle,
        OpType.MTP_COL_SHUFFLE_COEFFICIENT.value: handle_mtp_col_shuffle_coefficient,
        OpType.SEGMENT_SWITCH.value: handle_segment_switch,
        OpType.SEGMENT_COL_SHUFFLE.value: handle_segment_col_shuffle,
        OpType.SEGMENT_NEGATIVE.value: handle_segment_neg,
        OpType.MOE_COL_SHUFFLE.value: handle_shuffle,
        OpType.RESHAPE_SHUFFLE.value: handle_reshape_shuffle,
        OpType.VL_COL_SHUFFLE.value: handle_shuffle
    }
    # 获取处理函数并执行
    handler = handlers.get(params.op_type)
    if handler:
        if params.op_type == OpType.SEGMENT_SWITCH.value or params.op_type == OpType.MTP_COL_SHUFFLE_COEFFICIENT.value:
            obf_model_weight = handler(params, obf_resources, is_obfuscation)
        else:
            obf_model_weight = handler(params, obf_resources)
        model_obf_param.set_obf_model_weight(obf_model_weight)
    else:
        log.warning('Unsupported op_type: ' + str(params.op_type))


def check_model_layer(model_weight, weight_name, obf_tensor, dim):
    if obf_tensor is None or len(obf_tensor) == 0:
        log.error(f"The input obf_tensor is empty, please check config.json in model folder, "
                  f"weight_name: {weight_name}.")
        raise ObfException(ErrorCode.UNSUPPORTED_OP_TYPE.value)
    if model_weight is None:
        log.error(f"The model weight is None, please check backbone or weight_name: {weight_name}.")
        raise ObfException(ErrorCode.UNSUPPORTED_OP_TYPE.value)
    if dim >= len(model_weight.shape):
        log.error(f"The model layer shape {dim} is not exist, the max shape is {len(model_weight.shape)}, "
                  f"please check obf config file, weight_name: {weight_name}.")
        raise ObfException(ErrorCode.UNSUPPORTED_OP_TYPE.value)


def handle_shuffle(params, obf_resources):
    if len(params.obf_op) == Constant.OP_CUSTOM_LEN_INDEX + 1:
        custom_start = params.obf_op[Constant.OP_CUSTOM_START_INDEX]
        custom_len = params.obf_op[Constant.OP_CUSTOM_LEN_INDEX]
        obf_tensor = obf_resources.obf_custom_dict.get(OpType(params.op_type)).get(custom_len)
    else:
        custom_start = 0
        obf_tensor = obf_resources.obf_dict[OpType(params.op_type)]
    check_model_layer(params.model_weight, params.weight_name, obf_tensor, params.dim)
    total_len = params.model_weight.shape[params.dim]
    obf_tensor_len = len(obf_tensor)
    obf_model_weight = {}
    if total_len == obf_tensor_len:
        obf_model_weight = params.base_obf_function(obf_tensor, layer_part_clo_obf, custom_start)
    elif total_len % obf_tensor_len == 0:
        obf_model_weight = params.base_obf_function(obf_tensor, layer_segment_col_obf)
    else:
        log.error("obf_tensor_len cannot be exactly divided by total_len.")
        raise ObfException(ErrorCode.UNSUPPORTED_OP_TYPE.value)
    return obf_model_weight


def handle_mtp_col_shuffle(params, obf_resources):
    obf_tensor = obf_resources.obf_dict[OpType.COL_SHUFFLE]
    check_model_layer(params.model_weight, params.weight_name, obf_tensor, params.dim)
    return params.base_obf_function(obf_tensor, layer_split_col_obf)


def handle_mul_mask(params, obf_resources):
    check_model_layer(params.model_weight, params.weight_name,
                      obf_resources.obf_dict[OpType.MUL_MASK][params.obf_param.precision_mode], params.dim)
    mul_mask_matrix = torch.diag(1 / obf_resources.obf_dict[OpType.MUL_MASK][params.obf_param.precision_mode]).to(
        dtype=params.model_weight.dtype).to(params.device_type)
    return torch.matmul(params.model_weight, mul_mask_matrix.T)


def handle_mtp_col_shuffle_coefficient(params, obf_resources, is_obfuscation):
    obf_tensor_addin = obf_resources.obf_dict[OpType.COL_SHUFFLE_ADDIN]
    obf_tensor_same_ta = obf_resources.obf_dict[OpType.COL_SHUFFLE_COEFFICIENT]
    check_model_layer(params.model_weight, params.weight_name, obf_tensor_addin, params.dim)
    check_model_layer(params.model_weight, params.weight_name, obf_tensor_same_ta, params.dim)
    if not is_obfuscation:
        params.model_weight = params.base_obf_function(obf_tensor_same_ta, layer_part_clo_obf, len(obf_tensor_same_ta))
        return params.base_obf_function(obf_tensor_addin, layer_split_col_obf)
    params.model_weight = params.base_obf_function(obf_tensor_addin, layer_split_col_obf)
    return params.base_obf_function(obf_tensor_same_ta, layer_part_clo_obf, len(obf_tensor_same_ta))


def handle_segment_switch(params, obf_resources, is_obfuscation):
    obf_tensor = obf_resources.obf_dict[OpType(params.op_type)]
    check_model_layer(params.model_weight, params.weight_name, obf_tensor, params.dim)
    return params.base_obf_function(obf_tensor, layer_segment_switch_obf, is_obfuscation)


def handle_segment_neg(params, obf_resources):
    obf_tensor = obf_resources.obf_dict[OpType(params.op_type)]
    check_model_layer(params.model_weight, params.weight_name, obf_tensor, params.dim)
    return params.base_obf_function(obf_tensor, layer_segment_neg_obf)


def handle_segment_col_shuffle(params, obf_resources):
    obf_tensor = obf_resources.obf_dict[OpType(params.op_type)]
    check_model_layer(params.model_weight, params.weight_name, obf_tensor, params.dim)
    return params.base_obf_function(obf_tensor, layer_segment_col_obf)


def handle_reshape_shuffle(params, obf_resources):
    custom_start = params.obf_op[Constant.OP_CUSTOM_START_INDEX]
    custom_len = params.obf_op[Constant.OP_CUSTOM_LEN_INDEX]
    dim = params.obf_op[Constant.OP_DIM_INDEX]
    model_weight = params.model_weight

    out_ch, in_ch, time_dim, k_h, k_w = model_weight.shape
    if k_h * k_w != Constant.VISION_DATA_LEN:
        log.error("Incorrect model_weight shape.")
        raise ObfException(ErrorCode.UNSUPPORTED_OP_TYPE.value)
    reshape_weight = model_weight.reshape(out_ch, in_ch, time_dim, k_h * k_w)
    obf_tensor = obf_resources.obf_custom_dict.get(OpType(params.obf_op[0])).get(custom_len)
    check_model_layer(reshape_weight, params.weight_name, obf_tensor, dim)
    obf_reshape_weight = layer_part_clo_obf(
        reshape_weight, params.weight_name, obf_tensor.to(params.device_type), dim, custom_start)
    return obf_reshape_weight.reshape(out_ch, in_ch, time_dim, k_h, k_w)