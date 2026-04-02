#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""OBF_SDK错误码枚举定义类"""

from enum import Enum


class ErrorCode(Enum):
    SUCCESS = (0, "Success.")
    FAILED = (1, "Failed.")
    FAILED_TO_LOAD_LIBRARY = (2, "Failed To Load Library.")
    INVALID_PARAM = (1001, "Parameter validation failed.")
    INVALID_PATH = (1002, "Path validation failed.")
    INVALID_SEED_CONTENT = (1003, "Obfuscate seed content validation failed.")
    INVALID_TP_NUM = (1004, "The config param tp number validation failed.")
    INVALID_CONFIG_PATH = (1005, "The obfuscate config path validation failed.")
    INVALID_JSON_FILE = (1006, "The obfuscate config file is incorrect json format.")
    INVALID_MODEL_TYPE = (1007, "The model type validation failed, please use support model type.")
    MODEL_CONFIG_INVALID_TORCH_TYPE = (1008, "The model config torch type validation failed.")
    MODEL_CONFIG_INVALID_HIDDEN_SIZE = \
        (1009, "The model config hidden size validation failed, please check hidden size and tp number.")
    MODEL_CONFIG_INVALID_VOCAB_SIZE = (1010, "The model config vocab size validation failed.")
    GET_MODEL_LIST_FAILED = (1011, "Get model list failed, please check the model config and the model folder.")
    INVALID_SEED_TYPE = (1012, "The input param seed type validation failed.")
    INVALID_OBF_TYPE = (1013, "The input param obfuscate type validation failed.")
    UNMATCHED_OBF_TYPE = \
        (1014, "The input param obfuscate type is unmatched with the obfuscate seed that have already been set.")
    INSUFFICIENT_DISK_SPACE = (1015, "There is insufficient disk space.")
    IO_ERROR = (1016, "Unknown I/O error.")
    CONFIGURATION_FILE_FORMAT_ERROR = (1017, "The format of the Value section in the configuration file is incorrect.")
    INVALID_DEVICE_TYPE = (1018, "The device type is out of range.")
    INVALID_DEVICE_ID = (1019, "The device id verification failed.")
    CONFIGURATION_FILE_ERROR = (1020, "The configuration file is selected incorrectly.")
    INVALID_OBF_COEFFICIENT = (1021, "The config param obf coefficient validation failed.")
    MODEL_CONFIG_INVALID_NUM_ATTENTION_HEADS = (1022, "The model config num attention heads validation failed.")
    MODEL_CONFIG_INVALID_NUM_HIDDEN_LAYERS = (1023, "The model config num_hidden_layers validation failed.")
    MODEL_CONFIG_INVALID_MOE_INTERMEDIATE_SIZE = (1024, "The model config moe_intermediate_size validation failed.")
    MODEL_CONFIG_INVALID_NUM_EXPERTS = (1025, "The model config num_experts validation failed.")
    MODEL_CONFIG_INVALID_INTERMEDIATE_SIZE = (1026, "The model config intermediate_size validation failed.")
    MODEL_CONFIG_INVALID_HEAD_DIM = (1027, "The model config head_dim validation failed.") 
    MODEL_CONFIG_INVALID_TEXT_CONFIG = (1028, "The model config text_config validation failed.")
    MODEL_CONFIG_INVALID_VISION_CONFIG = (1029, "The model config vision_config type validation failed.")
    MODEL_CONFIG_INVALID_DEPTH = (1030, "The model config vision_config type validation failed.")
    MODEL_CONFIG_INVALID = (1031, "The model config validation failed.")
    ENCRYPT_FAILED = (2001, "Encryption passwd failed.")
    DECRYPT_FAILED = (2002, "Decryption passwd failed.")
    CREATE_SEED_FAILED = (2003, "Create obfuscate seed failed.")
    QUERY_SEED_FAILED = (2004, "Query obfuscate seed failed.")
    GENERATED_RANDOM_FAILED = (3001, "Generated random list failed.")
    VOCAB_SIZE_FAILED = (3002, "The size of vocab must be greater than zero.")
    ITEM_VALIDATE_FAILED = (3003, "Item type must be int and item must less than vocab_size.")
    MODEL_PATH_FAILED = (3004, "Please use create_model_obfuscation() or create_custom_model_obfuscation() instead.")
    WHITE_LIST_CHECK_FAILED = (3005, "Failed to verify the white list.")
    FOUND_INDEX_JSON_ERROR = (3006, "Found multiple .index.json files.")
    FOUND_MODEL_WEIGHT_ERROR = (3007, "Failed to find model weight.")
    UNSUPPORTED_OP_TYPE = (4001, "The op_type is not supported on the model shape.")
    INVALID_FLAG = (5001, "The flag validation failed.")
    MODEL_ALREADY_OBFUSCATED = \
        (5002, "Model weight obfuscation for model protection has already been completed.")
    DATA_ALREADY_OBFUSCATED = \
        (5003, "Model weight obfuscation for data protection has already been completed.")
    OBFUSCATION_ALREADY_COMPLETED = \
        (5004, "Model and data protection via weight obfuscation has already been completed.")
    READ_CONFIG_ERROR = (5005, "Failed to read configuration file.")
    UPDATE_CONFIG_ERROR = (5006, "Failed to update configuration file.")
    INVALID_DE_OBFUSCATION = (5007, "Model weights do not support current de-obfuscation operation.")
    INVALID_BASE64_STRING = (5008, "Failed to decode base64 string.")
    INVALID_IMAGE = (5009, "Failed to open image.")
    INVALID_VIDEO = (5010, "Failed to open video.")
    SEED_CONTENT_NOT_SET = (5011, "The seed content is not set.")
    INVALID_IMAGE_ASPECT_RATO = (5012, "The image aspect ratio is invalid.")
    INVALID_VIDEO_FRAME_SIZE = (5013, "The video frame size is invalid.")
    INVALID_VIDEO_FRAME_ASPECT_RATO = (5014, "The video frame aspect ratio is invalid.")
    INVALID_IMAGE_SIZE = (5015, "The image size is invalid.")
    CREATE_OBFUSCATOR_FAILED = (5016, "Failed to create weight obfuscator.")
    APPLY_OBFUSCATION_FAILED = (5017, "Failed to apply weight obfuscation.")
    OBFUSCATOR_NOT_INITIALIZED = (5018, "Obfuscator is not initialized.")
    INVALID_ELEMENT_SIZE = (5019, "Invalid element size for data type.")
    UNSUPPORTED_DTYPE = (5020, "The dtype is not supported.")
    INVALID_VIDEO_METADATAS = (5021, "Failed to parse video metadata.")


    @property
    def code(self):
        return self.value[0]

    @property
    def message(self):
        return self.value[1]
