#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""视频数据混淆接口"""

import base64
import json
import math
import os
import tempfile
from fractions import Fraction
from io import BytesIO
from typing import Tuple

import av
import cv2
import numpy as np
import torch
from torchvision.transforms.v2 import functional as F
from transformers.image_utils import PILImageResampling

from ..api.asset_obfuscation import AssetObfuscation
from ..constants import Constant, ErrorCode
from ..exception import ObfException
from ..utils import log, clean_bytearray, data_dec_mul, \
    generate_patch_and_channel_permute, apply_patch_and_channel_permute


def _check_local_save_path(is_local_save, seed_ciphertext_dir) -> bool:
    return is_local_save and isinstance(seed_ciphertext_dir, str) and not os.path.islink(seed_ciphertext_dir) \
        and os.path.exists(seed_ciphertext_dir)


class VideoDataAssetObfuscation(AssetObfuscation):
    """视频推理数据混淆对外接口
    创建VideoDataAssetObfuscation类实例
    """

    def __init__(self, patch_size: int = 16, merge_size: int = 2, longest_edge: int = 25165824, 
                 shortest_edge: int = 4096, temporal_patch_size: int = 2, num_frames: int = 32):
        args = [patch_size, merge_size, longest_edge, shortest_edge, temporal_patch_size, num_frames]
        if not all(isinstance(arg, int) for arg in args):
            log.error("The parameters for visual data preprocessing must be of int type.")
            raise ObfException(ErrorCode.INVALID_PARAM.value)
        self.patch_size = patch_size
        self.merge_size = merge_size
        self.longest_edge = longest_edge
        self.shortest_edge = shortest_edge
        self.temporal_patch_size = temporal_patch_size
        self.factor = self.patch_size * self.merge_size
        if self.factor == 0 or self.longest_edge == 0 or self.temporal_patch_size == 0:
            log.error("The 'factor' or 'longest_edge' or 'temporal_patch_size' cannot be zero.")
            raise ObfException(ErrorCode.INVALID_PARAM.value)
 
        self.num_frames = num_frames
        self.fps = -1
        self.is_seed_content = False

    @staticmethod
    def _smart_resize(
        num_frames: int,
        height: int,
        width: int,
        temporal_factor: int,
        factor: int,
        min_pixels: int,
        max_pixels: int,
    ) -> Tuple[int, int]:
        if height == 0 or width == 0:
            log.error("Failed to parse video metadata.")
            raise ObfException(ErrorCode.INVALID_VIDEO_METADATAS.value)
        if height < factor or width < factor:
            log.error(f"Video frame height:{height} or width:{width} must be larger than factor:{factor}")
            raise ObfException(ErrorCode.INVALID_VIDEO_FRAME_SIZE.value)
        elif max(height, width) / min(height, width) > Constant.IMAGE_MAX_RATIO:
            log.error(f"Video frame absolute aspect ratio must be smaller than {Constant.IMAGE_MAX_RATIO}")
            raise ObfException(ErrorCode.INVALID_VIDEO_FRAME_ASPECT_RATO.value)
        h_bar = round(height / factor) * factor
        w_bar = round(width / factor) * factor
        t_bar = math.ceil(num_frames / temporal_factor) * temporal_factor

        if t_bar * h_bar * w_bar > max_pixels:
            beta = math.sqrt((num_frames * height * width) / max_pixels)
            h_bar = max(factor, math.floor(height / beta / factor) * factor)
            w_bar = max(factor, math.floor(width / beta / factor) * factor)
        elif t_bar * h_bar * w_bar < min_pixels:
            beta = math.sqrt(min_pixels / (num_frames * height * width))
            h_bar = math.ceil(height * beta / factor) * factor
            w_bar = math.ceil(width * beta / factor) * factor

        return h_bar, w_bar

    @staticmethod
    def _validate_base64_video(video: str):
        """
        验证并解码base64编码的视频字符串

        :param video: base64编码格式的视频数据
        :return: base64前缀字符串、视频数据
        """
        if not isinstance(video, str) or len(video) > Constant.MAX_BASE64_VIDEO_LENGTH * 1024 * 1024:
            log.error("The video data type or length validation failed.")
            raise ObfException(ErrorCode.INVALID_PARAM.value)
        base64_field = "base64,"
        base64_prefix = ""
        if base64_field in video:
            base64_prefix, video = video.split(base64_field, 1)
            base64_prefix += base64_field

        try:
            decoded_bytes = base64.b64decode(video, validate=True)
        except Exception as e:
            log.error("Failed to decode base64 string.")
            raise ObfException(ErrorCode.INVALID_BASE64_STRING.value) from e

        try:
            cap = VideoDataAssetObfuscation._read_video(decoded_bytes)
        except Exception as e:
            log.error("Failed to open video.")
            raise ObfException(ErrorCode.INVALID_VIDEO.value) from e

        return base64_prefix, cap

    @staticmethod
    def _read_video(vide: bytes):
        tmp_file = tempfile.NamedTemporaryFile(delete=True, suffix=".mkv")
        temp_path = tmp_file.name

        try:
            tmp_file.write(vide)
            tmp_file.flush()

            cap = cv2.VideoCapture(temp_path)

            if not cap.isOpened():
                cap.release()
                log.error("Failed to open video.")
                raise ObfException(ErrorCode.INVALID_VIDEO)

            return cap
        except Exception as e:
            log.error("read video failed")
            raise ObfException(ErrorCode.FAILED) from e
        finally:
            tmp_file.close()
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @classmethod
    def create_by_config(cls, config_path: str, num_frames: int = 32):
        """
        通过配置文件构造实例

        :param config_path: 模型视频预处理配置文件路径
        :return: VideoDataAssetObfuscation对象
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

        return cls(patch_size, merge_size, longest_edge, shortest_edge, temporal_patch_size, num_frames)

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

    def video_base64_obf(self, video: str, fps: int = 2) -> str:
        """
        混淆base64编码格式的视频数据

        :param video: base64编码格式的视频数据
        :return: 混淆后视频的base64编码
        """
        if not self.is_seed_content:
            log.error("The seed content is not set.")
            raise ObfException(ErrorCode.SEED_CONTENT_NOT_SET.value)
        if not isinstance(fps, int):
            log.error("The parameters for visual data preprocessing must be of int type.")
            raise ObfException(ErrorCode.INVALID_PARAM.value)
        self.fps = fps
        base64_prefix, cap = self._validate_base64_video(video)

        try:
            obf_video_bytes = self._video_obf(cap)
        except Exception as e:
            log.error(f"Failed to obfuscate video: {e}")
            raise ObfException(ErrorCode.FAILED.value) from e
        finally:
            if cap is not None:
                cap.release() # 释放视频资源

        obf_base64_data = obf_video_bytes.getvalue()
        obf_base64_data = base64.b64encode(obf_base64_data).decode('utf-8')

        return base64_prefix + obf_base64_data

    def video_bytearray_obf(self, video: bytearray, fps: int = 2) -> bytearray:
        """
        混淆bytearray格式视频流

        :param video: bytearray格式视频流
        :return: 混淆后的bytearray格式视频流
        """
        if not self.is_seed_content:
            log.error("The seed content is not set.")
            raise ObfException(ErrorCode.SEED_CONTENT_NOT_SET.value)
        if not isinstance(fps, int):
            log.error("The parameters for visual data preprocessing must be of int type.")
            raise ObfException(ErrorCode.INVALID_PARAM.value)
        self.fps = fps

        if not isinstance(video, bytearray) or len(video) > Constant.MAX_BYTES_VIDEO_LENGTH * 1024 * 1024:
            log.error("The video data type or length validation failed.")
            raise ObfException(ErrorCode.INVALID_PARAM.value)

        try:
            cap = self._read_video(video)
        except Exception as e:
            log.error("Failed to open video.")
            raise ObfException(ErrorCode.INVALID_VIDEO) from e

        try:
            obf_video_bytes = self._video_obf(cap)
        except Exception as e:
            log.error(f"Failed to obfuscate video: {e}")
            raise ObfException(ErrorCode.FAILED.value) from e
        finally:
            if cap is not None:
                cap.release() # 释放视频资源

        return bytearray(obf_video_bytes.getvalue())

    def _video_obf(self, cap) -> torch.Tensor:
        """
        混淆视频

        :param cap: 视频对象
        :return: 混淆后视频帧
        """
        obf_video_bytes = BytesIO()
        output_container = av.open(obf_video_bytes, mode='w', format='mp4')

        interpolation = PILImageResampling.BICUBIC

        num_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

        frame_idx, resized_frame_num = self._sample_frames(num_frames, fps)
        resized_h, resized_w = self._smart_resize(num_frames=resized_frame_num, height=height, width=width,
                                                  temporal_factor=self.temporal_patch_size,
                                                  factor=self.patch_size * self.merge_size,
                                                  min_pixels=self.shortest_edge,
                                                  max_pixels=self.longest_edge)

        output_video = output_container.add_stream("libx264", 
                        rate=Fraction(len(frame_idx) / num_frames * fps).limit_denominator(1000))
        output_video.width = resized_w
        output_video.height = resized_h
        output_video.pix_fmt = "yuv420p"

        for idx in range(num_frames):
            ok = cap.grab()
            if not ok:
                break
            if idx not in frame_idx:
                continue
            ret, frame = cap.retrieve()
            if ret:
                frames = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_tensor = torch.from_numpy(frames.transpose(2, 0, 1).copy())

                patches = F.resize(frame_tensor, (resized_h, resized_w), interpolation=interpolation, antialias=True)

                grid_h, grid_w = resized_h // self.patch_size, resized_w // self.patch_size
                patches = patches.reshape(3, grid_h, self.patch_size, grid_w, self.patch_size)
                patches = patches.permute(0, 1, 3, 2, 4)
                patches = patches.reshape(3, grid_h, grid_w, self.patch_size * self.patch_size)

                numpy_array = patches.numpy()
                numpy_array = apply_patch_and_channel_permute(numpy_array)
                permuted_patches = torch.tensor(numpy_array)

                permuted_patches = permuted_patches.reshape(3, grid_h, grid_w, self.patch_size, self.patch_size)
                permuted_patches = permuted_patches.permute(1, 3, 2, 4, 0)
                obf_patches = permuted_patches.reshape(grid_h * self.patch_size, grid_w * self.patch_size, 3)

                video_array = torch.as_tensor(obf_patches, dtype=torch.uint8).numpy(force=True)
                frame = av.VideoFrame.from_ndarray(video_array, format="rgb24")
                frame.pict_type = av.video.frame.PictureType.NONE

                for packet in output_video.encode(frame):
                    output_container.mux(packet)

        for packet in output_video.encode():
            output_container.mux(packet)

        output_container.close()
        return obf_video_bytes

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
    
    def _sample_frames(self, total_frames: int, fps) -> list:
        if total_frames == 0 or fps == 0:
            log.error("Failed to parse video metadata.")
            raise ObfException(ErrorCode.INVALID_VIDEO_METADATAS.value)
        target_frames = total_frames
        if self.num_frames > 0:
            target_frames = min(self.num_frames, total_frames)
        resized_frame = target_frames
        if target_frames == total_frames or (target_frames - 1) * 2 + 1 >= total_frames:
            frame_idx = list(range(0, total_frames))
        else:
            target_frames = (target_frames - 1) * 2 + 1
            uniform_sampled_frames = np.linspace(0, total_frames - 1, target_frames, dtype=int)
            frame_idx = uniform_sampled_frames.tolist()
        if total_frames <= 0 and self.fps > 0:
            if self.fps < fps:
                target_frames = int(total_frames / fps * self.fps)
                resized_frame = target_frames
                uniform_sampled_frames = np.linspace(0, total_frames - 1, target_frames, dtype=int)
                frame_idx = uniform_sampled_frames.tolist()
        return frame_idx, resized_frame
