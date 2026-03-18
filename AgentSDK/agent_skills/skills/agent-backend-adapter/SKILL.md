---
name: agent-backend-adapter
description: |
 自动化适配Agent后端，集成MSRL(MindSpeed-RL)、VERL、VLLM等训练推理框架。When users need to integrate training frameworks (MindSpeed-RL/VERL) with inference engines (vLLM), configure agent backend pipelines, generate training scripts, create adapter wrappers, or build complete training-inference pipelines for LLM agents, use this skill. Supports GRPO/PPO training algorithms, multi-NPU distributed inference on Ascend NPUs, and standalone code generation independent of OpenCode. This skill is optimized for Ascend NPU (昇腾) hardware.
---

# Agent Backend Adapter Skill

This skill automates the integration of Agent training and inference backends, supporting MSRL (MindSpeed-RL), VERL, and vLLM frameworks on Ascend NPU. It generates standalone code that can run independently without OpenCode.

## ⚠️ IMPORTANT: Ascend NPU Optimization

This skill is specifically designed for **Ascend NPU (昇腾AI处理器)**. Key differences from GPU/CUDA:

| CUDA/GPU | Ascend NPU | Notes |
|----------|------------|-------|
| `torch.cuda` | `torch_npu.npu` | Device module |
| `.cuda()` | `.npu()` | Device placement |
| `CUDA_VISIBLE_DEVICES` | `ASCEND_RT_VISIBLE_DEVICES` | Device selection |
| GPU memory | NPU memory | Memory management |
| `nccl` | `hccl` | Collective comm |

**Environment Variables for NPU:**
```bash
# Device selection (use specific NPU devices)
export ASCEND_RT_VISIBLE_DEVICES=0,1,2,3,4,5,6,7

# CANN version (if needed)
export CANN_VERSION=8.5.1

# PyTorch NPU backend
export PYTHONPATH=/usr/local/Ascend/pyACL:$PYTHONPATH
```

## Core Capabilities

### 1. Training Framework Integration

**MindSpeed-RL (MSRL)**
- Uses `RayGRPOTrainer` from `mindspeed_rl`
- Supports GRPO algorithm with Actor-Critic architecture
- Requires: RLConfig, MegatronConfig, GenerateConfig
- Key classes: `AgentGRPOTrainer`, `RolloutWorker`

**VERL**
- Uses `RayPPOTrainer` from `verl.trainer.ppo`
- Supports PPO/GRPO/DPO algorithms
- Uses OmegaConf for configuration
- Key classes: `AgentGRPOTrainer`, `RolloutWorker`

### 2. Inference Engine Integration

**vLLM (Ascend NPU Optimized)**
- Offline inference via `LLM` class
- Distributed inference via Tensor/Pipeline Parallelism on NPU
- OpenAI-compatible API server
- Key parameters: tensor_parallel_size, pipeline_parallel_size, npu_memory_utilization (use gpu_memory_utilization for compatibility)
- Supports vllm-ascend backend

## Usage Scenarios

### Scenario 1: Generate Training Script

When user wants to create a training script:

```
User: "帮我生成一个使用VERL训练Agent的脚本"
```

**Generated Output Structure:**
```python
# standalone_train_agent.py
# This file is fully independent - can run without OpenCode

import os
import torch
import ray
from verl.trainer.ppo.ray_trainer import RayPPOTrainer
from omegaconf import OmegaConf

# Configuration
CONFIG = {
    "model": {"path": "meta-llama/Llama-3-8B"},
    "trainer": {"n_npus_per_node": 8, "nnodes": 1},
    "actor_rollout_ref": {
        "actor": {"strategy": "fsdp2", "optim": {"lr": 1e-6}},
        "rollout": {"name": "vllm", "n": 4}
    }
}

def main():
    # Initialize Ray
    ray.init(num_cpus=64)
    
    # Load config
    config = OmegaConf.create(CONFIG)
    
    # Build trainer
    trainer = RayPPOTrainer(config)
    
    # Train
    trainer.fit()

if __name__ == "__main__":
    main()
```

### Scenario 2: Create Adapter Wrapper

When user wants to create a custom engine wrapper:

```
User: "创建一个基于vLLM的Agent推理适配器"
```

**Generated Output Structure:**
```python
# vllm_agent_adapter.py
# Standalone adapter - no OpenCode dependencies

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from vllm import LLM, SamplingParams

class BaseAgentAdapter(ABC):
    @abstractmethod
    def generate(self, prompts: List[str]) -> List[str]:
        pass

class VLLMAdapter(BaseAgentAdapter):
    def __init__(self, model_path: str, tensor_parallel_size: int = 1):
        self.llm = LLM(model=model_path, tensor_parallel_size=tensor_parallel_size)
        self.sampling_params = SamplingParams(temperature=0.7, max_tokens=2048)
    
    def generate(self, prompts: List[str]) -> List[str]:
        outputs = self.llm.generate(prompts, self.sampling_params)
        return [o.outputs[0].text for o in outputs]
```

### Scenario 3: Build Complete Pipeline

When user wants a complete training-inference pipeline:

```
User: "构建一个完整的Agent训练Pipeline，需要支持MSRL训练和vLLM推理"
```

**Generated Output Structure:**
```python
# agent_training_pipeline.py
# Complete standalone pipeline

import os
import ray
from mindspeed_rl import RayGRPOTrainer, RLConfig
from vllm import LLM

class AgentPipeline:
    def __init__(self, config: dict):
        self.config = config
        self.inference_engine = None
        self.trainer = None
    
    def setup_inference(self):
        """Initialize vLLM inference engine"""
        self.inference_engine = LLM(
            model=self.config["model"]["path"],
            tensor_parallel_size=self.config["inference"]["tensor_parallel_size"],
            gpu_memory_utilization=self.config["inference"]["gpu_memory_utilization"]
        )
    
    def setup_training(self):
        """Initialize training framework"""
        rl_config = RLConfig(...)
        self.trainer = RayGRPOTrainer(rl_config, ...)
    
    def run(self):
        """Execute complete training pipeline"""
        self.setup_inference()
        self.setup_training()
        self.trainer.fit()
```

## Code Generation Guidelines

### Decoupling Requirements (MUST FOLLOW)

1. **No OpenCode Dependencies**: Generated code must NOT import from `agentic_rl`, `opencode`, or any project-specific modules
2. **Standalone Imports Only**: Use public APIs from frameworks:
   - `mindspeed_rl` (if available)
   - `verl` 
   - `vllm`
   - `transformers`
   - `torch`
   - `ray`
3. **Self-Contained**: Include all necessary configuration, helper functions, and setup code
4. **No Relative Imports**: Use absolute imports only

### Template System

Use Jinja2-like templates in `references/` directory:
- `msrl_train_template.py` - MindSpeed-RL training template
- `verl_train_template.py` - VERL training template
- `vllm_infer_template.py` - vLLM inference template
- `pipeline_template.py` - Complete pipeline template

### Configuration Generation

Generate YAML/JSON config files that match framework requirements:

**VERL Config (NPU):**
```yaml
trainer:
  n_npus_per_node: 8
  nnodes: 1
  total_epochs: 10
actor_rollout_ref:
  model:
    path: meta-llama/Llama-3-8B
  actor:
    strategy: fsdp2
    optim:
      lr: 1e-6
  rollout:
    name: vllm
    n: 4
algorithm:
  adv_estimator: grpo
```

**MSRL Config (NPU):**
```yaml
rl_config:
  n_samples_per_prompt: 4
  max_prompt_length: 4096
actor_config:
  tensor_parallel_size: 8
  pipeline_parallel_size: 1
generate_config:
  infer_tensor_parallel_size: 8
  npu_memory_utilization: 0.8
```

## Framework-Specific Details

### MindSpeed-RL (MSRL) - Ascend NPU Optimized

**Key Components:**
- `RayGRPOTrainer`: Main training class (NPU optimized)
- `RLConfig`: RL hyperparameters
- `MegatronConfig`: Model configuration
- `GenerateConfig`: Inference configuration (NPU)
- `RayActorGroup`: Distributed worker group

**NPU Initialization:**
```python
import os
os.environ["ASCEND_RT_VISIBLE_DEVICES"] = "0,1,2,3,4,5,6,7"

import torch
import torch_npu  # Auto-registers NPU backend

# Device placement uses .npu() instead of .cuda()
model = model.npu()
tensor = tensor.npu()
```

**Integration Pattern (NPU):**
```python
from mindspeed_rl import RayGRPOTrainer, RLConfig, MegatronConfig, GenerateConfig

rl_config = RLConfig(
    n_samples_per_prompt=4,
    max_prompt_length=4096,
    actor_rollout_dispatch_size=4
)

actor_config = MegatronConfig(
    tensor_parallel_size=8,
    pipeline_parallel_size=1,
    tokenizer_name_or_path=model_path
)

generate_config = GenerateConfig(
    infer_tensor_parallel_size=8,
    npu_memory_utilization=0.8  # or gpu_memory_utilization for compatibility
)
```

### VERL - Ascend NPU Support

**Key Components:**
- `RayPPOTrainer`: Main training class
- `OmegaConf`: Configuration management
- `ResourcePoolManager`: NPU resource allocation
- `DataProto`: Data format

**NPU Ray Configuration:**
```python
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

**Integration Pattern:**
```python
from verl.trainer.ppo.ray_trainer import RayPPOTrainer
from omegaconf import OmegaConf

config = OmegaConf.load("config.yaml")
trainer = RayPPOTrainer(config)
trainer.init_workers()
trainer.fit()
```

### vLLM-Ascend

**Key Components:**
- `LLM`: Main inference engine class (vllm-ascend)
- `SamplingParams`: Generation parameters
- Async server for online inference

**NPU-specific Integration:**
```python
from vllm import LLM, SamplingParams

llm = LLM(
    model="meta-llama/Llama-3-8B-Instruct",
    tensor_parallel_size=4,
    npu_memory_utilization=0.9,  # Use npu_memory_utilization if available
    # For compatibility, vllm-ascend accepts gpu_memory_utilization
    trust_remote_code=True,
    device="npu"  # Specify NPU device
)

sampling_params = SamplingParams(
    temperature=0.7,
    max_tokens=2048,
    top_p=0.95
)

outputs = llm.generate(prompts, sampling_params)
```

## Workflow

### Step 1: Analyze User Request

1. Identify the target framework(s): MSRL, VERL, vLLM
2. Determine the use case: training, inference, pipeline
3. Extract configuration requirements

### Step 2: Select Template

- Training only → `*_train_template.py`
- Inference only → `vllm_infer_template.py`
- Complete pipeline → `pipeline_template.py`

### Step 3: Generate Code

1. Load appropriate template
2. Fill in user-specified parameters
3. Add necessary imports
4. Ensure standalone execution capability

### Step 4: Validate Output

1. Check for no OpenCode/project dependencies
2. Verify all imports are standard framework APIs
3. Ensure configuration matches framework schema

## Reference Files

- `references/msrl_integration.md` - MindSpeed-RL integration guide
- `references/verl_integration.md` - VERL integration guide
- `references/vllm_integration.md` - vLLM integration guide
- `references/config_schemas.md` - Configuration schema references

## Examples

### Example 1: VERL GRPO Training

```
User: "生成一个VERL的GRPO训练脚本，使用LLaMA-8B模型"
```

**Action:** Use `verl_train_template.py`, customize:
- model path: meta-llama/Llama-3-8B
- algorithm: grpo
- n_samples_per_prompt: 4

### Example 2: vLLM Inference Adapter

```
User: "创建一个vLLM推理适配器，支持Tensor Parallelism"
```

**Action:** Use `vllm_infer_template.py`, customize:
- tensor_parallel_size: 4
- Add adapter class wrapper

### Example 3: Complete Pipeline

```
User: "构建完整的训练推理Pipeline，需要支持多节点训练"
```

**Action:** Use `pipeline_template.py`, customize:
- Multi-node configuration
- Trainer + Inference engine coordination
- Checkpoint management
