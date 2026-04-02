#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""图片数据混淆接口"""

import base64
import json
import math
import os
from io import BytesIO
from typing import Tuple

import torch
from PIL import Image
from torchvision.transforms.v2 import functional as F

from ..api.asset_obfuscation import AssetObfuscation
from ..constants import Constant, ErrorCode
from ..exception import ObfException
from ..utils import log, clean_bytearray, data_dec_mul, \
    generate_patch_and_channel_permute, apply_patch_and_channel_permute


def _check_local_save_path(is_local_save, seed_ciphertext_dir) -> bool:
    return is_local_save and isinstance(seed_ciphertext_dir, str) and not os.path.islink(seed_ciphertext_dir) \
        and os.path.exists(seed_ciphertext_dir)


class ImageDataAssetObfuscation(AssetObfuscation):
    """图片推理数据混淆对外接口
    创建ImageDataAssetObfuscation类实例
    """

    def __init__(self, patch_size: int = 16, merge_size: int = 2, longest_edge: int = 16777216, 
                 shortest_edge: int = 65536, temporal_patch_size: int = 2):
        args = [patch_size, merge_size, longest_edge, shortest_edge, temporal_patch_size]
        if not all(isinstance(arg, int) for arg in args):
            log.error("The parameters for visual data preprocessing must be of int type.")
            raise ObfException(ErrorCode.INVALID_PARAM.value)
        self.patch_size = patch_size
        self.merge_size = merge_size
        self.longest_edge = longest_edge
        self.shortest_edge = shortest_edge
        self.temporal_patch_size = temporal_patch_size
        self.factor = self.patch_size * self.merge_size
        if self.factor == 0 or self.longest_edge == 0:
            log.error("The 'factor' or 'longest_edge' cannot be zero.")
            raise ObfException(ErrorCode.INVALID_PARAM.value)
 
        self.is_seed_content = False

    @staticmethod
    def _to_rgb(pil_image: Image.Image) -> Image.Image:
        """
        将图片颜色格式转为RGB

        :param pil_image: 图片对象
        :return: RGB格式的图片对象
        """
        if pil_image.mode == 'RGBA':
            white_background = Image.new("RGB", pil_image.size, (255, 255, 255))
            white_background.paste(pil_image, mask=pil_image.split()[3])  # Use alpha channel as mask
            return white_background
        else:
            return pil_image.convert("RGB")

    @staticmethod
    def _smart_resize(height: int, width: int, factor: int, min_pixels: int, max_pixels: int) -> Tuple[int, int]:
        """
        缩放图片，以满足以下条件：
        1. 高度和宽度都能被“factor”整除
        2. 像素总数在'min_pixels'和'max_pixels'范围内
        3. 尽可能保持图像的宽高比

        :param height: 高度
        :param width: 宽度
        :param factor: 高度和宽度必须能被整除的因子
        :param min_pixels: 允许的最小像素总数
        :param max_pixels: 允许的最大像素总数
        :return: 包含新高度和宽度的元组
        """
        if max(height, width) / min(height, width) > Constant.IMAGE_MAX_RATIO:
            log.error(f"Absolute aspect ratio must be smaller than {Constant.IMAGE_MAX_RATIO}")
            raise ObfException(ErrorCode.INVALID_IMAGE_ASPECT_RATO.value)
        h_bar = round(height / factor) * factor
        w_bar = round(width / factor) * factor
        if h_bar * w_bar > max_pixels:
            beta = math.sqrt((height * width) / max_pixels)
            h_bar = max(factor, math.floor(height / beta / factor) * factor)
            w_bar = max(factor, math.floor(width / beta / factor) * factor)
        elif h_bar * w_bar < min_pixels:
            beta = math.sqrt(min_pixels / (height * width))
            h_bar = math.ceil(height * beta / factor) * factor
            w_bar = math.ceil(width * beta / factor) * factor
        return h_bar, w_bar

    @staticmethod
    def _tensor_to_pil(tensor) -> Image.Image:
        """
        张量数据转PIL图片对象

        :param tensor: 输入的张量
        :return: PIL.Image对象
        """
        if tensor.dtype == torch.float32:
            tensor = (tensor * 255).clamp(0, 255)
        tensor = tensor.byte()
        return F.to_pil_image(tensor)

    @staticmethod
    def _validate_base64_image(image: str) -> Tuple[str, Image.Image]:
        """
        验证并解码base64编码的图像字符串

        :param image: base64编码格式的图片数据
        :return: base64前缀字符串和PIL.Image对象
        """
        if not isinstance(image, str) or len(image) > Constant.MAX_BASE64_IMAGE_LENGTH * 1024 * 1024:
            log.error("The image data type or length validation failed.")
            raise ObfException(ErrorCode.INVALID_PARAM.value)

        base64_field = "base64,"
        base64_prefix = ""
        if base64_field in image:
            base64_prefix, image = image.split(base64_field, 1)
            base64_prefix += base64_field

        try:
            decoded_bytes = base64.b64decode(image, validate=True)
        except Exception as e:
            log.error("Failed to decode base64 string.")
            raise ObfException(ErrorCode.INVALID_BASE64_STRING.value) from e

        image_stream = None
        pil_img = None
        try:
            image_stream = BytesIO(decoded_bytes)
            pil_img = Image.open(image_stream)
            return base64_prefix, pil_img
        except Exception as e:
            # 如果出错，确保关闭已打开的资源
            if pil_img:
                pil_img.close()
            log.error("Failed to open image.")
            raise ObfException(ErrorCode.INVALID_IMAGE.value) from e
    
    @classmethod
    def create_by_config(cls, config_path: str):
        """
        通过配置文件构造实例

        :param config_path: 模型图片预处理配置文件路径
        :return: ImageDataAssetObfuscation对象
        """
        if not isinstance(config_path, str) or not os.path.isfile(config_path):
            log.error(f"Invalid preprocess config json file path")
            raise ObfException(ErrorCode.INVALID_PATH.value)

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            log.error(f"Failed to load the preprocess config json file")
            raise ObfException(ErrorCode.INVALID_JSON_FILE.value) from e

        patch_size = data.get("patch_size")
        merge_size = data.get("merge_size")
        size = data.get("size")
        longest_edge = size.get("longest_edge") if isinstance(size, dict) else None
        shortest_edge = size.get("shortest_edge") if isinstance(size, dict) else None
        temporal_patch_size = data.get("temporal_patch_size")

        return cls(patch_size, merge_size, longest_edge, shortest_edge, temporal_patch_size)
    
    def set_seed_content(self, seed_content: str = None, is_local_save: bool = False,
                         seed_ciphertext_dir: str = None) -> (int, str):
        """
        1.输入混淆因子内容，用于数据混淆
        2.通过本地软保护设置混淆因子

        :param seed_content: 混淆因子类型
        :param is_local_save: 是否从本地获取
        :param seed_ciphertext_dir: 密文保存路径，is_local_save为True时需要此参数需要被校验
        :return: errorCode(int, str)
        """
        if not isinstance(seed_content, str) and not _check_local_save_path(is_local_save, seed_ciphertext_dir):
            log.error("The obfuscate seed content data type validation failed.")
            return ErrorCode.INVALID_SEED_CONTENT.value
        if seed_content is not None and (len(seed_content) > Constant.SEED_CONTENT_MAX_LEN
                                            or len(seed_content) < Constant.SEED_CONTENT_MIN_LEN):
            log.error("The obfuscate seed content len validation failed.")
            return ErrorCode.INVALID_SEED_CONTENT.value
        if seed_content is not None:
            seed_content_bytes = bytearray(seed_content, "utf-8")
        else:
            seed_content_bytes = data_dec_mul(seed_ciphertext_dir, Constant.DATA_CIPHERTEXT_FILE_NAME)
        set_seed_result = self._set_seed_core(seed_content_bytes, Constant.DATA_SEED_TYPE)
        clean_bytearray(seed_content_bytes)
        return set_seed_result

    def image_base64_obf(self, image: str) -> str:
        """
        混淆base64编码格式的图片数据

        :param image: base64编码格式的图片数据
        :return: 混淆后图片的base64编码
        """
        if not self.is_seed_content:
            log.error("The seed content is not set.")
            raise ObfException(ErrorCode.SEED_CONTENT_NOT_SET.value)
        base64_prefix, pil_img = self._validate_base64_image(image)

        try:
            obf_pil_image = self._image_obf(pil_img)
        except Exception as e:
            log.error(f"Failed to obfuscate image: {e}")
            raise ObfException(ErrorCode.FAILED.value) from e

        obf_image_bytes = BytesIO()
        obf_pil_image.save(obf_image_bytes, "JPEG")
        obf_base64_data = obf_image_bytes.getvalue()
        obf_base64_data = base64.b64encode(obf_base64_data).decode('utf-8')
        return base64_prefix + obf_base64_data

    def image_bytearray_obf(self, image: bytearray) -> bytearray:
        """
        混淆bytearray格式图片流

        :param image: bytearray格式图片流
        :return: 混淆后的bytearray格式图片流
        """
        if not self.is_seed_content:
            log.error("The seed content is not set.")
            raise ObfException(ErrorCode.SEED_CONTENT_NOT_SET.value)

        if not isinstance(image, bytearray) or len(image) > Constant.MAX_BYTES_IMAGE_LENGTH * 1024 * 1024:
            log.error("The image data type or length validation failed.")
            raise ObfException(ErrorCode.INVALID_PARAM.value)

        pil_img = None
        try:
            # 创建BytesIO对象并确保在使用后关闭
            image_stream = BytesIO(image)
            pil_img = Image.open(image_stream)
            
            try:
                obf_pil_image = self._image_obf(pil_img)
            except Exception as e:
                log.error(f"Failed to obfuscate image: {e}")
                raise ObfException(ErrorCode.FAILED.value) from e

            obf_image_bytes = BytesIO()
            obf_pil_image.save(obf_image_bytes, "JPEG")
            return bytearray(obf_image_bytes.getvalue())
        except Exception as e:
            log.error("Failed to open image.")
            raise ObfException(ErrorCode.INVALID_IMAGE.value) from e
        finally:
            # 关闭PIL Image对象
            if pil_img:
                pil_img.close()

    def _image_obf(self, image: Image.Image) -> Image.Image:
        """
        混淆PIL.Image对象

        :param image: PIL.Image对象
        :return: 混淆后的PIL.Image对象
        """
        image = self._to_rgb(image)
        width, height = image.size

        resized_height, resized_width = self._smart_resize(
            height,
            width,
            factor=self.factor,
            min_pixels=self.shortest_edge,
            max_pixels=self.longest_edge,
        )
        image = image.resize((resized_width, resized_height))

        image = F.pil_to_tensor(image)
        grid_h, grid_w = resized_height // self.patch_size, resized_width // self.patch_size
        channel = image.shape[0]
        patches = image.reshape(channel, grid_h, self.patch_size, grid_w, self.patch_size)

        patches = patches.permute(0, 1, 3, 2, 4)
        patches_flat = patches.reshape(channel, grid_h, grid_w, self.patch_size * self.patch_size)

        numpy_array = patches_flat.numpy()
        numpy_array = apply_patch_and_channel_permute(numpy_array)
        permuted_flat = torch.tensor(numpy_array)

        permuted_patches = permuted_flat.reshape(channel, grid_h, grid_w, self.patch_size, self.patch_size)
        permuted_patches = permuted_patches.permute(0, 1, 3, 2, 4)
        restored_image = permuted_patches.reshape(channel, grid_h * self.patch_size, grid_w * self.patch_size)
        permuted_image = self._tensor_to_pil(restored_image)
        return permuted_image

    def _set_seed_core(self, seed_content_bytes, seed_type):
        """
        通过混淆因子生成混淆列表

        :param seed_content_bytes: 混淆因子
        :return: errorCode(int, str)
        """
        log.info("Start to set seed core.")
        try:
            generate_patch_and_channel_permute(seed_content_bytes, self.patch_size * self.patch_size,
                                               Constant.SEED_ADD_IN.encode("utf-8"))
        except ObfException as e:
            return e.code, e.message
        log.info("Set seed core successful.")
        self.is_seed_content = True
        return ErrorCode.SUCCESS.value
