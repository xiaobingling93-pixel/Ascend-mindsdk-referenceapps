# MindSpeed-RL (MSRL) Integration Guide - Ascend NPU

## Overview

MindSpeed-RL is Huawei's reinforcement learning framework for training large language models on Ascend NPU. It provides distributed training capabilities using Ray and supports GRPO (Group Relative Policy Optimization) algorithm.

## ⚠️ NPU vs GPU

MindSpeed-RL is specifically designed for **Ascend NPU**. Key differences:

| GPU/CUDA | Ascend NPU | Notes |
|----------|------------|-------|
| `num_gpus` | `num_npus` | Ray initialization |
| `.cuda()` | `.npu()` | Device placement |
| `gpu_memory_utilization` | `npu_memory_utilization` | Memory config |
| `CUDA_VISIBLE_DEVICES` | `ASCEND_RT_VISIBLE_DEVICES` | Device selection |

## Environment Setup

```python
import os

# Set NPU visible devices BEFORE importing torch
os.environ["ASCEND_RT_VISIBLE_DEVICES"] = "0,1,2,3,4,5,6,7"

import torch
import torch_npu  # Registers NPU backend
```

## Key Components

### 1. RayGRPOTrainer

Main training class that orchestrates the entire training process.

```python
from mindspeed_rl import RayGRPOTrainer, RLConfig, MegatronConfig, GenerateConfig
```

**Initialization Parameters:**
- `rl_config`: RLConfig - Reinforcement learning hyperparameters
- `actor_config`: MegatronConfig - Model configuration
- `generate_config`: GenerateConfig - Inference configuration
- `agentic_rl_config`: AgenticRLConfig (optional) - Agent-specific configuration

### 2. Configuration Classes

#### RLConfig

```python
from mindspeed_rl import RLConfig

rl_config = RLConfig(
    n_samples_per_prompt=4,        # Number of samples per prompt
    max_prompt_length=4096,        # Maximum prompt length
    max_response_length=2048,      # Maximum response length
    actor_rollout_dispatch_size=4, # Rollout batch size
    kl_ctrl=dict(kl_coef=0.001)    # KL control coefficient
)
```

#### MegatronConfig

```python
from mindspeed_rl import MegatronConfig

actor_config = MegatronConfig(
    tensor_parallel_size=8,         # Tensor parallelism
    pipeline_parallel_size=1,      # Pipeline parallelism
    tokenizer_name_or_path="meta-llama/Llama-3-8B",
    global_batch_size=64,
    train_iters=1000,
    save_interval=100,
    save="./checkpoints"
)
```

#### GenerateConfig (NPU Optimized)

```python
from mindspeed_rl import GenerateConfig

generate_config = GenerateConfig(
    infer_tensor_parallel_size=8,
    infer_pipeline_parallel_size=1,
    max_num_seqs=256,
    max_model_len=4096,
    dtype="bfloat16",
    npu_memory_utilization=0.8,  # Use npu_memory_utilization for NPU
    enforce_eager=False
)
```

## Training Workflow (NPU)

### Step 1: Initialize Ray for NPU

```python
import os
os.environ["ASCEND_RT_VISIBLE_DEVICES"] = "0,1,2,3,4,5,6,7"

import ray

ray.init(
    num_cpus=64,
    num_gpus=0,  # NPU doesn't use GPU count
    runtime_env={
        "env_vars": {
            "TOKENIZERS_PARALLELISM": "false",
            "NCCL_DEBUG": "WARN",
            "ASCEND_RT_VISIBLE_DEVICES": "0,1,2,3,4,5,6,7",
            "HCCL_WHITELIST_DISABLE": "1"
        }
    }
)
```

### Step 2: Create Worker Groups (NPU)

```python
from mindspeed_rl import RayActorGroup

# Actor workers (training) - use num_npus_per_worker for NPU
actor_worker = RayActorGroup(
    role="actor",
    num_workers=8,
    num_npus_per_worker=1  # Use NPUs instead of GPUs
)

# Reference workers (for KL)
reference_worker = RayActorGroup(
    role="reference", 
    num_workers=8,
    num_npus_per_worker=1
)
```

### Step 3: Initialize Trainer

```python
from mindspeed_rl import RuleReward

# Define reward function
reward_fn = RuleReward(...)

trainer = RayGRPOTrainer(
    rl_config=rl_config,
    actor_config=actor_config,
    generate_config=generate_config,
    agentic_rl_config=agentic_rl_config,
    actor_worker=actor_worker,
    reference_worker=reference_worker,
    reward_list=[reward_fn],
    tokenizer=tokenizer
)
```

### Step 4: Run Training

```python
trainer.fit(train_data_iters, test_data_iters)
```

## Configuration File (YAML - NPU)

```yaml
# msrl_config.yaml
rl_config:
  n_samples_per_prompt: 4
  max_prompt_length: 4096
  max_response_length: 2048
  kl_ctrl:
    kl_coef: 0.001

actor_config:
  tensor_parallel_size: 8
  pipeline_parallel_size: 1
  tokenizer_name_or_path: meta-llama/Llama-3-8B
  global_batch_size: 64
  train_iters: 1000

generate_config:
  infer_tensor_parallel_size: 8
  max_num_seqs: 256
  max_model_len: 4096
  dtype: bfloat16
  npu_memory_utilization: 0.8
```

## Integration with vLLM-Ascend

MindSpeed-RL uses vLLM-Ascend for inference on NPU:

```python
# The GenerateConfig automatically configures vLLM-Ascend
generate_config = GenerateConfig(
    infer_tensor_parallel_size=8,
    npu_memory_utilization=0.8,
    enforce_eager=False,
    enable_prefix_caching=True
)
```

## Complete Example (NPU Optimized)

```python
#!/usr/bin/env python3
"""Standalone MSRL training script for Ascend NPU - no OpenCode dependencies"""

import os
os.environ["ASCEND_RT_VISIBLE_DEVICES"] = "0,1,2,3,4,5,6,7"

import ray
from mindspeed_rl import (
    RayGRPOTrainer, 
    RLConfig, 
    MegatronConfig, 
    GenerateConfig,
    RayActorGroup,
    RuleReward
)


def main():
    # Initialize Ray for NPU
    ray.init(
        num_cpus=64,
        num_gpus=0,
        runtime_env={
            "env_vars": {
                "TOKENIZERS_PARALLELISM": "false",
                "NCCL_DEBUG": "WARN",
                "ASCEND_RT_VISIBLE_DEVICES": "0,1,2,3,4,5,6,7",
                "HCCL_WHITELIST_DISABLE": "1"
            }
        }
    )
    
    # Configuration
    model_path = "meta-llama/Llama-3-8B"
    
    rl_config = RLConfig(
        n_samples_per_prompt=4,
        max_prompt_length=4096,
        max_response_length=2048
    )
    
    actor_config = MegatronConfig(
        tensor_parallel_size=8,
        tokenizer_name_or_path=model_path,
        global_batch_size=64,
        train_iters=1000
    )
    
    generate_config = GenerateConfig(
        infer_tensor_parallel_size=8,
        npu_memory_utilization=0.8
    )
    
    print(f"Initializing training on Ascend NPU...")
    print(f"Model: {model_path}")
    print(f"Tensor Parallel Size: 8")
    
    # Create workers for NPU
    actor_worker = RayActorGroup("actor", num_workers=8)
    reference_worker = RayActorGroup("reference", num_workers=8)
    
    # Example trainer initialization:
    # trainer = RayGRPOTrainer(
    #     rl_config=rl_config,
    #     actor_config=actor_config,
    #     generate_config=generate_config,
    #     actor_worker=actor_worker,
    #     reference_worker=reference_worker,
    #     reward_list=[],
    #     tokenizer=None
    # )
    # trainer.fit(None, None)
    
    print("Training configuration generated successfully!")


if __name__ == "__main__":
    main()
```
