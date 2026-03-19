# SDK Knowledge Base - Ascend NPU

Comprehensive documentation for error analysis in Ascend NPU hardware scenarios.

## Overview

This skill supports error analysis for multiple Ascend-related SDKs and frameworks:

| SDK/Framework | Description | Error Prefix |
|--------------|-------------|--------------|
| MultimodalSDK | Multimodal LLM preprocessing on NPU | `mm.` |
| Vision SDK | Image/video processing on Ascend | `mxv`, `mxstream` |
| MindSpeed-RL | Reinforcement learning on Ascend NPU | `mindspeed` |
| MindSpeed-LLM | LLM training on Ascend NPU | `mindspeed` |
| CANN | Ascend Neural Network Toolkit | `acl`, `cann` |

## Key Components

### MultimodalSDK

| Component | Description |
|-----------|-------------|
| mm.Image | Image data handling |
| mm.Tensor | General tensor data |
| mm.video_decode | Video decoding |
| Adapter | Model preprocessor acceleration |
| patcher | vLLM integration patches |

### Vision SDK

| Component | Description |
|-----------|-------------|
| MxStreamManager | Stream processing manager |
| MxImage | Image data handling |
| MxVideo | Video data handling |

### CANN (Compute Architecture for Neural Networks)

| Component | Description |
|-----------|-------------|
| ACL (Ascend CL) | Application C library |
| Runtime | NPU execution runtime |
| Driver | NPU driver |
| GE (Graph Engine) | Graph execution engine |

## Version Requirements

### CANN Versions

| CANN Version | Python Version | Typical SDK Support |
|-------------|---------------|-------------------|
| 8.0.0 | 3.7-3.9 | Vision SDK 2.x, MultimodalSDK 1.x |
| 8.5.0 | 3.9-3.11 | Vision SDK 3.x, MultimodalSDK 2.x |
| 8.5.1 | 3.9-3.11 | Vision SDK 3.x, MultimodalSDK 2.x |
| 25.5.0 | 3.9+ | Latest SDKs |

### Python Dependencies

```
transformer>=4.51.3
pillow>=11.2.1
numpy>=1.26.4
torch>=2.5.1
```

## Error Codes

### AccData Error Codes (MultimodalSDK)

| Code | Name | Description |
|------|------|-------------|
| 0 | H_OK | Success |
| 1 | H_COMMON_ERROR | Common error |
| 2 | H_COMMON_UNKNOWN_ERROR | Unknown error |
| 3 | H_COMMON_LOGGER_ERROR | Logger error |
| 4 | H_COMMON_INVALID_PARAM | Invalid parameter |
| 5 | H_COMMON_OPERATOR_ERROR | Operator error |
| 6 | H_COMMON_NULLPTR | Null pointer |
| 7 | H_SINGLEOP_ERROR | Single operator error |
| 8 | H_FUSIONOP_ERROR | Fusion operator error |
| 9 | H_USEROP_ERROR | User operator error |
| 10 | H_PIPELINE_ERROR | Pipeline error |
| 11 | H_PIPELINE_BUILD_ERROR | Pipeline build error |
| 12 | H_PIPELINE_STATE_ERROR | Pipeline state error |
| 13 | H_TENSOR_ERROR | Tensor error |
| 14 | H_THREADPOOL_ERROR | Thread pool error |

### ACL Error Codes

| Code | Name | Description |
|------|------|-------------|
| 0 | ACL_ERROR_NONE | Success |
| 1 | ACL_ERROR_INVALID_PARAM | Invalid parameter |
| 2 | ACL_ERROR_NO_MEMORY | Out of memory |
| 3 | ACL_ERROR_NO_PERMISSION | Permission denied |
| 4 | ACL_ERROR_NOT_SUPPORTED | Not supported |
| 5 | ACL_ERROR_NULL_POINTER | Null pointer |
| 6 | ACL_ERROR_INVALID_FILE | Invalid file |
| 7 | ACL_ERROR_NOT_COMPLETE | Not complete |

## Common Error Patterns

### Import Errors

**Symptom**: `ModuleNotFoundError` or `ImportError` involving Ascend/NPU

**Common Causes**:
1. CANN environment variables not set
   - Solution: `source /usr/local/Ascend/ascend-toolkit/set_env.sh`
2. Python version mismatch
   - Solution: Use Python 3.9+
3. Missing pip dependencies
   - Solution: Install required packages

### NPU Initialization Errors

**Symptom**: NPU device errors, initialization failures

**Common Causes**:
1. Driver not installed
   - Solution: Install Ascend NPU driver
2. CANN not properly installed
   - Solution: Reinstall CANN development kit
3. Device busy or unavailable
   - Solution: Check `npu-smi` output

### Memory Errors on NPU

**Symptom**: OOM, memory allocation failures on NPU

**Common Causes**:
1. Insufficient NPU memory
   - Solution: Free NPU memory, reduce batch size
2. Memory leak
   - Solution: Check for proper cleanup in code
3. Large image/video
   - Solution: Process in smaller chunks

### Image Processing Errors

**Symptom**: Image decoding or processing failures

**Common Causes**:
1. Unsupported format
   - Solution: Check supported formats (JPEG, PNG, etc.)
2. Corrupted image file
   - Solution: Verify image file integrity
3. Memory issues
   - Solution: Check NPU memory availability

### Video Processing Errors

**Symptom**: Video decode failures

**Common Causes**:
1. FFmpeg not installed
   - Solution: Install FFmpeg
2. Unsupported codec
   - Solution: Use supported codecs (H.264, H.265, etc.)
3. Corrupted video file
   - Solution: Verify video file integrity

### API Usage Errors

**Symptom**: TypeError, ValueError from API calls

**Common Causes**:
1. Wrong parameter types
   - Solution: Check API signatures in documentation
2. Invalid parameter values
   - Solution: Verify parameter ranges
3. Device mode not supported
   - Solution: Use valid DeviceMode (CPU/NPU)

## API Reference

### MultimodalSDK Image API

```python
from mm import Image, DeviceMode, Interpolation

img = Image.open("/path/to/image.jpg", "cpu")
img_resize = img.resize((width, height), Interpolation.BICUBIC, DeviceMode.CPU)
img_crop = img.crop(x, y, width, height, DeviceMode.CPU)
```

### MultimodalSDK Tensor API

```python
from mm import Tensor
tensor = Tensor(data, device_mode)
```

### MultimodalSDK Video API

```python
from mm import video_decode
images = video_decode("/path/to/video.mp4")
```

### MultimodalSDK Adapter API

```python
from mm.adapter import Qwen2VLPreprocessor, InternVL2Preprocessor
processor = Qwen2VLPreprocessor()
```

### Vision SDK API

```python
from mxstream import MxStreamManager

manager = MxStreamManager(config_path)
result = manager.process(image_data)
```

## Troubleshooting Checklist

### Environment
- [ ] Python version >= 3.9
- [ ] CANN installed correctly
- [ ] Environment variables set: `source /usr/local/Ascend/ascend-toolkit/set_env.sh`
- [ ] NPU driver loaded: `npu-smi info`

### Dependencies
- [ ] All pip packages installed
- [ ] FFmpeg available (for video)
- [ ] Correct versions used

### SDK
- [ ] MultimodalSDK/Vision SDK installed correctly
- [ ] Version compatible with CANN
- [ ] Imports work without errors

### Runtime
- [ ] NPU device available: `npu-smi list`
- [ ] Sufficient memory: `npu-smi info -q -d memory`
- [ ] Proper permissions

### NPU Diagnostic Commands

```bash
# Check NPU status
npu-smi info

# Check NPU memory usage
npu-smi info -q -d memory

# List available NPU devices
npu-smi list

# Monitor NPU utilization
npu-smi dmon -c 1

# Clear NPU memory cache
npu-smi -r

# Check CANN version
cat /usr/local/Ascend/ascend-toolkit/version.info

# Check driver version
npu-smi -v
```

## Environment Setup

### Standard CANN Environment Variables

```bash
# Add to ~/.bashrc or /etc/profile
export ASCEND_HOME=/usr/local/Ascend/ascend-toolkit
export PATH=$ASCEND_HOME/bin:$PATH
export LD_LIBRARY_PATH=$ASCEND_HOME/lib64:$LD_LIBRARY_PATH
export PYTHONPATH=$ASCEND_HOME/python/site-packages:$PYTHONPATH
export CANN_HOME=$ASCEND_HOME
```

### Docker Environment

```bash
# For CANN container
docker run -it --device /dev/davinci0 --device /dev/davinci_manager \
  -v /usr/local/Ascend:/usr/local/Ascend \
  ascend-cann-runtime:8.5.1
```
