# VERL Integration Guide - Ascend NPU

## Overview

VERL (Volcengine Reinforcement Learning) is a production-ready RL training library for large language models. It supports diverse RL algorithms including PPO, GRPO, and DPO, with seamless integration with vLLM-Ascend for inference on Ascend NPU.

## ⚠️ NPU Environment Setup

```python
import os
# Set NPU devices BEFORE importing torch
os.environ["ASCEND_RT_VISIBLE_DEVICES"] = "0,1,2,3,4,5,6,7"

import torch
import torch_npu  # Registers NPU backend
```

## Key Differences: GPU → NPU

| GPU | NPU | Notes |
|-----|-----|-------|
| `n_gpus_per_node` | `n_npus_per_node` | Trainer config |
| `gpu_memory_utilization` | `npu_memory_utilization` | Memory config |
| `CUDA_VISIBLE_DEVICES` | `ASCEND_RT_VISIBLE_DEVICES` | Device selection |

## Key Components

### 1. RayPPOTrainer

Main training class for PPO-style algorithms.

```python
from verl.trainer.ppo.ray_trainer import RayPPOTrainer
```

**Initialization Parameters:**
- `config`: OmegaConf - Training configuration
- `tokenizer`: PreTrainedTokenizerBase - Tokenizer
- `role_worker_mapping`: dict - Worker role assignments
- `resource_pool_manager`: ResourcePoolManager - NPU resource allocation
- `ray_worker_group_cls`: RayWorkerGroup - Worker group class

### 2. Configuration Management

VERL uses OmegaConf for configuration:

```python
from omegaconf import OmegaConf

# Load from file
config = OmegaConf.load("config.yaml")

# Create from dict
config = OmegaConf.create({
    "trainer": {"n_npus_per_node": 8},
    "actor_rollout_ref": {...}
})
```

## Configuration Structure (NPU)

### Trainer Configuration

```yaml
trainer:
  n_npus_per_node: 8          # NPUs per node
  nnodes: 1                   # Number of nodes
  total_epochs: 10            # Training epochs
  save_freq: 100              # Checkpoint frequency
  project_name: agent_training
  experiment_name: grpo_train
```

### Actor-Rollout-Ref Configuration

```yaml
actor_rollout_ref:
  model:
    path: meta-llama/Llama-3-8B  # Model path
  
  actor:
    strategy: fsdp2             # Distribution strategy (NPU optimized)
    optim:
      lr: 1e-6                 # Learning rate
    ppo_mini_batch_size: 256
    use_dynamic_bsz: True
  
  rollout:
    name: vllm                 # vLLM-Ascend inference engine
    n: 4                       # Samples per prompt
    tensor_model_parallel_size: 2
  
  ref:
    strategy: fsdp2
    log_prob_use_dynamic_bsz: True
```

### Algorithm Configuration

```yaml
algorithm:
  adv_estimator: grpo         # Advantage estimator: grpo, ppo
  gamma: 1.0                  # Discount factor
  lam: 0.95                   # GAE lambda
  norm_adv_by_std_in_grpo: True
  kl_ctrl:
    kl_coef: 0.001            # KL penalty coefficient
```

## Training Workflow (NPU)

### Step 1: Initialize Ray for NPU

```python
import os
os.environ["ASCEND_RT_VISIBLE_DEVICES"] = "0,1,2,3,4,5,6,7"

import ray

ray.init(
    num_cpus=64,
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

### Step 2: Load Configuration

```python
from omegaconf import OmegaConf

config = OmegaConf.load("verl_config.yaml")
# or
config = OmegaConf.create(YOUR_CONFIG_DICT)
```

### Step 3: Define Worker Mapping

```python
from verl.trainer.ppo.ray_trainer import RayWorkerGroup

role_worker_mapping = {
    "actor": actor_worker_group,
    "rollout": rollout_worker_group,
    "critic": critic_worker_group,
    "ref": ref_worker_group
}
```

### Step 4: Initialize Resource Pool Manager

```python
from verl.trainer.ppo.ray_trainer import ResourcePoolManager

resource_pool_manager = ResourcePoolManager(
    num_nodes=1,
    num_gpus_per_node=8,
    resource_pool_config={
        "actor": {"gpu": 4},
        "critic": {"gpu": 2},
        "rollout": {"gpu": 2}
    }
)
```

### Step 5: Initialize Trainer

```python
trainer = RayPPOTrainer(
    config=config,
    tokenizer=tokenizer,
    role_worker_mapping=role_worker_mapping,
    resource_pool_manager=resource_pool_manager,
    ray_worker_group_cls=RayWorkerGroup,
    reward_fn=your_reward_function
)
```

### Step 6: Run Training

```python
trainer.init_workers()
trainer.fit()
```

## GRPO Algorithm Example

```python
#!/usr/bin/env python3
"""Standalone VERL GRPO training script"""

import ray
from omegaconf import OmegaConf
from verl.trainer.ppo.ray_trainer import RayPPOTrainer, ResourcePoolManager

# Configuration
CONFIG = {
    "trainer": {
        "n_gpus_per_node": 8,
        "nnodes": 1,
        "total_epochs": 10
    },
    "actor_rollout_ref": {
        "model": {"path": "meta-llama/Llama-3-8B"},
        "actor": {
            "strategy": "fsdp2",
            "optim": {"lr": 1e-6},
            "ppo_mini_batch_size": 256
        },
        "rollout": {
            "name": "vllm",
            "n": 4,
            "tensor_model_parallel_size": 2
        },
        "ref": {"strategy": "fsdp2"}
    },
    "algorithm": {
        "adv_estimator": "grpo",
        "gamma": 1.0,
        "lam": 0.95
    }
}

def main():
    ray.init(num_cpus=64)
    
    config = OmegaConf.create(CONFIG)
    
    # Setup workers and resource manager
    # ... (worker setup code)
    
    trainer = RayPPOTrainer(
        config=config,
        tokenizer=tokenizer,
        role_worker_mapping=role_worker_mapping,
        resource_pool_manager=resource_pool_manager,
        ray_worker_group_cls=RayWorkerGroup,
        reward_fn=reward_fn
    )
    
    trainer.init_workers()
    trainer.fit()

if __name__ == "__main__":
    main()
```

## Async Training Mode

VERL supports fully asynchronous training:

```bash
# Launch async training
python -m recipe.fully_async_policy.fully_async_main \
    rollout_mode=async \
    rollout_name=vllm \
    actor_rollout_ref.actor.strategy=fsdp2 \
    trainer.nnodes=2 \
    trainer.n_gpus_per_node=8
```

Key parameters:
- `rollout_mode`: async/sync
- `rollout_name`: vllm/sglang
- `staleness_threshold`: Max staleness for async updates

## Integration with vLLM

VERL uses vLLM for inference by default:

```yaml
actor_rollout_ref:
  rollout:
    name: vllm
    n: 4
    tensor_model_parallel_size: 2
    gpu_memory_utilization: 0.8
    calculate_log_probs: True
```

## Data Format

VERL uses DataProto for data handling:

```python
from verl import DataProto

# Prepare batch data
batch_data = {
    "input_ids": torch.tensor([...]),
    "attention_mask": torch.tensor([...])
}

batch = DataProto.from_single_dict(batch_data)
```

## Metrics and Logging

```python
# TensorBoard support
trainer = RayPPOTrainer(
    config=config,
    # ... other params
    use_tensorboard=True,
    tensorboard_log_dir="./logs",
    project_name="my_project"
)
```

## Complete Configuration Example

```yaml
# verl_grpo_config.yaml
trainer:
  n_gpus_per_node: 8
  nnodes: 1
  total_epochs: 15
  save_freq: 100
  project_name: agent_grpo
  experiment_name: llama3_8b

actor_rollout_ref:
  model:
    path: meta-llama/Llama-3-8B
    use_remove_padding: True
  
  actor:
    strategy: fsdp2
    optim:
      lr: 1e-6
    ppo_mini_batch_size: 256
    use_dynamic_bsz: True
    ppo_max_token_len_per_gpu: 24000
    use_kl_loss: True
    kl_loss_coef: 0.001
  
  rollout:
    name: vllm
    n: 5
    tensor_model_parallel_size: 2
    gpu_memory_utilization: 0.8
  
  ref:
    strategy: fsdp2
    param_offload: False

algorithm:
  adv_estimator: grpo
  gamma: 1.0
  lam: 0.95
  norm_adv_by_std_in_grpo: True
  kl_ctrl:
    kl_coef: 0.001
```
