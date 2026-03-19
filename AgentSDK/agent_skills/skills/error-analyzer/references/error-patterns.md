# Error Patterns Reference

Comprehensive error patterns for Ascend NPU hardware scenarios, including general errors and NPU-specific errors.

## Category: NPU/Ascend Specific Errors

| Error Pattern | Typical Root Cause | Resolution |
|--------------|-------------------|------------|
| `NPU out of memory` | NPU device memory exhausted | Reduce batch size, enable memory optimization |
| `ACL error` | Ascend ACL initialization failure | Check CANN installation, verify NPU device |
| `CANN not found` | CANN environment not set | Source CANN set_env.sh |
| `NPU device not found` | NPU hardware not detected | Check npu-smi output, verify driver |
| `ascend initialize failed` | NPU initialization error | Check device permissions, reinstall driver |
| `hiai error` | Huawei AI framework error | Check CANN version compatibility |
| `Atlas.*error` | Atlas board specific error | Check hardware connection |

## Category: MultimodalSDK Errors

| Error Pattern | Typical Root Cause | Resolution |
|--------------|-------------------|------------|
| `mm.*import.*error` | MultimodalSDK not installed | pip install multimodalsdk |
| `AdapterError` | Preprocessor adapter failure | Check input data format |
| `TensorError` | Tensor shape/type mismatch | Verify tensor dimensions |
| `DeviceMode.*error` | Invalid device mode | Use CPU/NPU correctly |
| `Image.*decode.*error` | Image decode failure | Verify image format, check corrupted file |

## Category: Vision SDK Errors

| Error Pattern | Typical Root Cause | Resolution |
|--------------|-------------------|------------|
| `mxvision.*error` | Vision SDK initialization | Check Vision SDK installation |
| `mxstream.*error` | Stream processing error | Verify pipeline configuration |
| `Image.*decode.*error` | Image decode failure | Check image format (JPEG, PNG) |
| `Video.*decode.*error` | Video decode failure | Install FFmpeg, check codec |
| `Permission denied` | Missing read permissions | Check file/directory permissions |
| `Device or resource busy` | Device locked by another process | Identify and terminate locking process |

## Category: Memory/Resource Errors

| Error Pattern | Typical Root Cause | Resolution |
|--------------|-------------------|------------|
| `Out of memory` / `OOM` | Insufficient RAM or memory leak | Increase memory, check for leaks |
| `Memory allocation failed` | System memory exhausted | Free up memory, increase swap |
| `Cannot allocate memory` | Process memory limit reached | Check ulimits, increase limits |
| `CUDA out of memory` | GPU memory exhausted | Reduce batch size, clear cache |
| `NPU out of memory` | NPU memory exhausted | Reduce batch size, enable optimization |

## Category: Network/Distributed Errors

| Error Pattern | Typical Root Cause | Resolution |
|--------------|-------------------|------------|
| `socket.gaierror` | DNS resolution failure | Check /etc/hosts, network config |
| `Connection refused` | Service not running | Start the service |
| `Connection timeout` | Network/firewall issue | Check network, firewall rules |
| `NCCL.*error` | NCCL distributed error | Check GPU/NPU visibility, network |
| `RayTaskError` | Ray distributed task failure | Check Ray cluster status |
| `ProcessGroup.*error` | PyTorch distributed error | Verify distributed config |

## Category: Permission/Device Errors

| Error Pattern | Typical Root Cause | Resolution |
|--------------|-------------------|------------|
| `Permission denied` | Missing read/write permissions | Check file/directory permissions |
| `No such device` | Device not available or driver issue | Check hardware connection, driver status |
| `Device not found` | Specified device doesn't exist | Verify device ID |
| `Invalid device` | Device ID out of range | Check available devices with npu-smi |

## Category: Path/File Errors

| Error Pattern | Typical Root Cause | Resolution |
|--------------|-------------------|------------|
| `No such file or directory` | File missing or path incorrect | Verify path, check working directory |
| `File exists` | Duplicate file name | Use different name or force overwrite |
| `Is a directory` / `Not a directory` | Type mismatch | Use correct file/directory operation |

## Category: Library/Dependency Errors

| Error Pattern | Typical Root Cause | Resolution |
|--------------|-------------------|------------|
| `cannot find library` / `libxxx.so` | Missing shared library | Install dependency, set LD_LIBRARY_PATH |
| `undefined symbol` | Library version mismatch | Ensure compatible library versions |
| `ImportError` / `ModuleNotFoundError` | Python module missing | Install required package |
| `No module named 'xxx'` | Python path issue | Check PYTHONPATH, virtualenv |

## Category: Configuration Errors

| Error Pattern | Typical Root Cause | Resolution |
|--------------|-------------------|------------|
| `KeyError` | Missing config key | Add required key to config |
| `ValueError` | Invalid config value | Verify value range/format |
| `yaml.*error` | YAML parsing error | Check YAML syntax |
| `Configuration.*error` | Config loading failure | Verify config file path |

## Category: API/SDK Errors

| Error Pattern | Typical Root Cause | Resolution |
|--------------|-------------------|------------|
| `API key invalid` | Authentication failure | Verify API key/credentials |
| `Rate limit exceeded` | Too many requests | Implement retry with backoff |
| `Invalid parameter` | Wrong input to API | Check API documentation |
| `Service unavailable` | Service down or overloaded | Wait and retry |

## Category: Compilation/Build Errors

| Error Pattern | Typical Root Cause | Resolution |
|--------------|-------------------|------------|
| `undefined reference to` | Missing linking library | Add library to linker flags |
| `No rule to make target` | Missing build dependency | Install required build tools |
| `command not found` | Missing system command | Install required tool |

## Analysis Approach

When encountering an error:

1. **Extract the key error message** - Focus on the primary error, not surrounding context
2. **Identify the category** - Match to one of the patterns above
3. **Check NPU-specific first** - For Ascend errors, check CANN/NPU patterns first
4. **Check the obvious** - Verify versions, paths, permissions first
5. **Look for version info** - Error often includes version numbers
6. **Search with exact message** - Use quotes for precise matching

## Quick Reference: NPU Diagnostic Commands

```bash
# Check NPU status
npu-smi info

# Check NPU memory
npu-smi info -q -d memory

# List available devices
npu-smi list

# Check CANN version
npu-smi -v

# Monitor NPU usage
npu-smi dmon -c 1

# Clear NPU cache
npu-smi -r
```

## Quick Reference: Common Root Causes by Error Type

| Error Type | Common Root Causes |
|------------|-------------------|
| NPU startup failures | Driver not loaded, CANN not installed, device busy |
| NPU runtime errors | Memory exhaustion, CANN version mismatch, device error |
| MultimodalSDK errors | Input format not supported, CANN not initialized |
| Vision SDK errors | Pipeline misconfiguration, missing dependencies |
| Startup failures | Missing deps, wrong permissions, config errors |
| Runtime crashes | Memory issues, null pointers, race conditions |
| Performance issues | Resource exhaustion, inefficient algorithms |
| Intermittent issues | Timing, race conditions, external dependencies |
