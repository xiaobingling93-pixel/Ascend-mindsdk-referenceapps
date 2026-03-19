# Error Analysis Examples

This document provides examples of error analysis workflows in Ascend NPU scenarios.

## Example 1: NPU Out of Memory

### Input
```
## Error
RuntimeError: NPU out of memory. Tried to allocate 2.0 GB on device 0.

## Environment
- OS: Ubuntu 22.04
- Python: 3.9
- CANN: 8.5.0
- MultimodalSDK: 2.0

## Context
Running MultimodalSDK preprocessing with batch_size=16
```

### Analysis
1. **Error Type**: RuntimeError - NPU OOM
2. **Pattern Match**: NPU memory exhaustion
3. **Root Cause**: Batch size too large for available NPU memory

### Response
```
## Issue Analysis

**Root Cause**: The NPU device has insufficient memory to process the requested batch size.

**Solution**:
1. Reduce batch size:
   ```python
   batch_size = 8  # Try smaller values
   ```
2. Enable memory optimization:
   ```python
   # Use gradient checkpointing
   model.gradient_checkpointing_enable()
   ```
3. Clear NPU cache:
   ```bash
   npu-smi -r
   ```
4. Monitor memory usage:
   ```bash
   npu-smi info -q -d memory
   ```

**Prevention**: Monitor NPU memory during development and implement automatic batch size tuning.
```

---

## Example 2: CANN Import Error

### Input
```
## Error
ImportError: cannot import name 'acl' from 'ascend'

## Environment
- OS: CentOS 7.9
- Python: 3.9
- CANN: 8.0.0

## Context
Initializing Ascend NPU for inference
```

### Analysis
1. **Error Type**: ImportError
2. **Pattern Match**: CANN not properly installed or environment not set
3. **Root Cause**: CANN environment variables not sourced

### Response
```
## Issue Analysis

**Root Cause**: The CANN environment variables are not set, so Python cannot find the ASCEND modules.

**Solution**:
1. Source the CANN environment:
   ```bash
   source /usr/local/Ascend/ascend-toolkit/set_env.sh
   ```

2. Verify installation:
   ```bash
   npu-smi info
   ```

3. If not installed, download and install CANN from:
   https://www.hiascend.com/software/CANN

**Prevention**: Add CANN environment setup to your shell profile:
```bash
echo "source /usr/local/Ascend/ascend-toolkit/set_env.sh" >> ~/.bashrc
```

---

## Example 3: MultimodalSDK Adapter Error

### Input
```
## Error
AdapterError: Input tensor shape mismatch. Expected (B, C, H, W), got (B, H, W, C)

## Environment
- OS: Ubuntu 22.04
- Python: 3.9
- CANN: 8.5.0
- MultimodalSDK: 2.0

## Context
Using Qwen2VLPreprocessor for image input
```

### Analysis
1. **Error Type**: AdapterError - Tensor shape mismatch
2. **Pattern Match**: MultimodalSDK input format error
3. **Root Cause**: Input tensor dimension order incorrect (CHW vs HWC)

### Response
```
## Issue Analysis

**Root Cause**: The input tensor has incorrect dimension order. MultimodalSDK expects CHW format (Channel, Height, Width) but received HWC format (Height, Width, Channel).

**Solution**:
1. Convert tensor from HWC to CHW:
   ```python
   import torch
   
   # If input is (B, H, W, C)
   input_tensor = input_tensor.permute(0, 3, 1, 2)  # Now (B, C, H, W)
   ```

2. Or use SDK's built-in conversion:
   ```python
   from mm import Tensor, DeviceMode
   tensor = Tensor(data, DeviceMode.NPU, layout='CHW')
   ```

**Prevention**: Always verify input tensor layout before passing to MultimodalSDK.
```

---

## Example 4: Vision SDK Configuration Error

### Input
```
## Error
KeyError: 'device_id'

## Environment
- OS: Ubuntu 22.04
- Python: 3.9
- Vision SDK: 3.0
- CANN: 8.5.0

## Context
Loading Vision SDK pipeline configuration
```

### Analysis
1. **Error Type**: KeyError
2. **Pattern Match**: Configuration key missing
3. **Root Cause**: Missing required configuration parameter in pipeline config

### Response
```
## Issue Analysis

**Root Cause**: The pipeline configuration file is missing the required 'device_id' parameter.

**Solution**:
1. Add device_id to your config file:
   ```yaml
   pipeline:
     device_id: 0
     device_type: NPU
   ```

2. Verify available devices:
   ```bash
   npu-smi list
   ```

3. Example complete config:
   ```yaml
   pipeline:
     device_id: 0
     device_type: NPU
     batch_size: 1
     model_path: /path/to/model
   ```

**Prevention**: Always validate config against SDK documentation before loading.
```

---

## Example 5: Network/Distributed Error

### Input
```
## Error
socket.gaierror: [Errno -3] Temporary failure in name resolution

## Environment
- OS: Ubuntu 22.04
- Python: 3.9
- MindSpeed-RL: 1.0

## Context
Starting distributed training on multi-node cluster
```

### Analysis
1. **Error Type**: socket.gaierror - DNS resolution failure
2. **Pattern Match**: Network/DNS error in distributed training
3. **Root Cause**: Hostname not resolvable in /etc/hosts

### Response
```
## Issue Analysis

**Root Cause**: The hostname cannot be resolved, causing distributed training initialization to fail.

**Solution**:
1. Add hostname to /etc/hosts:
   ```bash
   echo "127.0.0.1 $(hostname)" | sudo tee -a /etc/hosts
   ```

2. Verify resolution:
   ```bash
   ping $(hostname)
   ```

3. For multi-node training, ensure all nodes can resolve each other:
   ```bash
   # On each node, add all node IPs to /etc/hosts
   echo "192.168.1.1 node0" | sudo tee -a /etc/hosts
   echo "192.168.1.2 node1" | sudo tee -a /etc/hosts
   ```

**Prevention**: Document hostname configuration in deployment guide and automate in startup scripts.
```
