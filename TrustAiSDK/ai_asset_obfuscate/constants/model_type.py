#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""模型类型枚举定义类"""

from enum import Enum


class ModelType(Enum):
    DEEPSEEK_QWEN_1_5B = "DeepSeek-R1-Distill-Qwen-1.5B"
    DEEPSEEK_QWEN_7B = "DeepSeek-R1-Distill-Qwen-7B"
    DEEPSEEK_QWEN_14B = "DeepSeek-R1-Distill-Qwen-14B"
    DEEPSEEK_QWEN_32B = "DeepSeek-R1-Distill-Qwen-32B"
    DEEPSEEK_R1_671B_W8A8 = "DeepSeek-671B-w8a8"
    DEEPSEEK_V3_671B_W8A8 = "DeepSeek-671B-w8a8"
    QWEN3 = "Qwen3"
    QWEN3_VL = "Qwen3-VL"
