# vLLM-Ascend Integration

## Overview
vLLM inference engine for Ascend NPUs (vllm-ascend package).

## Quick Start

```python
from vllm import LLM, SamplingParams

os.environ["ASCEND_RT_VISIBLE_DEVICES"] = "0,1,2,3"

llm = LLM(model="meta-llama/Llama-3-8B-Instruct", device="npu", trust_remote_code=True)
params = SamplingParams(temperature=0.7, max_tokens=512)
outputs = llm.generate(["Explain quantum computing"], params)
print(outputs[0].outputs[0].text)
```

## Key Configurations

| Parameter | CUDA | NPU |
|-----------|------|-----|
| memory | `gpu_memory_utilization` | `npu_memory_utilization` |
| device | `cuda` | `npu` |
| env | `CUDA_VISIBLE_DEVICES` | `ASCEND_RT_VISIBLE_DEVICES` |

## Common Options

```python
LLM(
    model=model_path,
    npu_memory_utilization=0.4,
    max_num_seqs=256,
    max_model_len=4096,
    dtype="bfloat16",
    enforce_eager=False,
    enable_prefix_caching=True,
    device="npu"
)
```

## Training Integration

### VERL
```yaml
actor_rollout_ref:
  rollout:
    name: vllm
    n: 4
    tensor_model_parallel_size: 2
```

### MindSpeed-RL
```python
GenerateConfig(infer_tensor_parallel_size=8, npu_memory_utilization=0.8)
```

## API Server

```bash
vllm serve meta-llama/Llama-3-8B-Instruct --tensor-parallel-size 4
```

```python
from openai import OpenAI
client = OpenAI(api_key="EMPTY", base_url="http://localhost:8000/v1")
print(client.chat.completions.create(model="model", messages=[{"role": "user", "content": "Hi"}]).choices[0].message.content)
```
