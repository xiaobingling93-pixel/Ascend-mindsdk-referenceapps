# Configuration Schemas Reference

## MindSpeed-RL (MSRL) Configuration

### RLConfig

```yaml
rl_config:
  n_samples_per_prompt: int          # Samples per prompt (default: 4)
  max_prompt_length: int             # Max prompt tokens (default: 4096)
  max_response_length: int          # Max response tokens (default: 2048)
  actor_rollout_dispatch_size: int  # Rollout batch size
  kl_ctrl:
    kl_coef: float                  # KL penalty coefficient
    kl_ctrl_method: str             # adaptive/fixed
```

### MegatronConfig

```yaml
actor_config:
  tensor_parallel_size: int         # TP degree
  pipeline_parallel_size: int       # PP degree
  tokenizer_name_or_path: str       # Model path
  global_batch_size: int            # Batch size
  train_iters: int                  # Training iterations
  save_interval: int                # Checkpoint interval
  save: str                         # Save path
  micro_batch_size: int             # Micro batch size
  gradient_clip_norm: float         # Gradient clipping
```

### GenerateConfig

```yaml
generate_config:
  tokenizer_name_or_path: str
  trust_remote_code: bool
  dtype: str                        # bfloat16/float16/float32
  infer_tensor_parallel_size: int
  infer_pipeline_parallel_size: int
  infer_expert_parallel_size: int
  max_num_seqs: int
  max_num_batched_tokens: int
  max_model_len: int
  gpu_memory_utilization: float
  offload_train_optimizer: bool
  offload_train_grad: bool
  offload_train_param: bool
  enable_prefix_caching: bool
  num_scheduler_steps: int
  enforce_eager: bool
  torchair_graph: bool
  enable_expert_parallel: bool
  ascend_scheduler_config_enabled: bool
  limit_mm_image_per_prompt: int
  limit_mm_video_per_prompt: int
  sampling_config:
    logprobs: int
    max_tokens: int
    top_p: float
    top_k: int
    min_p: float
    temperature: float
    detokenize: bool
    seed: int
```

## VERL Configuration

### Trainer Config

```yaml
trainer:
  n_gpus_per_node: int              # GPUs per node
  nnodes: int                       # Number of nodes
  total_epochs: int                  # Training epochs
  save_freq: int                    # Save frequency
  project_name: str                 # Project name
  experiment_name: str              # Experiment name
  default_local_dir: str            # Checkpoint directory
  val_before_train: bool             # Validate before training
  critic_warmup: int                # Critic warmup steps
  logger: str                       # Logger type
```

### Actor-Rollout-Ref Config

```yaml
actor_rollout_ref:
  model:
    path: str                       # Model path
    use_remove_padding: bool        # Remove padding optimization
  
  actor:
    strategy: str                   # fsdp/fsdp2/megatron
    optim:
      lr: float                     # Learning rate
      beta1: float
      beta2: float
      weight_decay: float
    ppo_mini_batch_size: int
    use_dynamic_bsz: bool
    ppo_max_token_len_per_gpu: int
    use_kl_loss: bool
    kl_loss_coef: float
    kl_loss_type: str               # low_var_kl/kl
    loss_agg_mode: str              # mean/sum
    enable_gradient_checkpointing: bool
    fsdp_config:
      param_offload: bool
      optimizer_offload: bool
  
  rollout:
    name: str                       # vllm/sglang
    n: int                          # Samples per prompt
    mode: str                       # sync/async
    tensor_model_parallel_size: int
    gpu_memory_utilization: float
    calculate_log_probs: bool
    log_prob_use_dynamic_bsz: bool
    enable_prefix_caching: bool
  
  ref:
    strategy: str
    log_prob_use_dynamic_bsz: bool
    fsdp_config:
      param_offload: bool
```

### Algorithm Config

```yaml
algorithm:
  adv_estimator: str               # grpo/ppo
  gamma: float                     # Discount factor
  lam: float                       # GAE lambda
  norm_adv_by_std_in_grpo: bool
  kl_ctrl:
    kl_coef: float
    kl_ctrl_method: str
```

### Data Config

```yaml
data:
  train_files: str                  # Training data path
  val_files: str                   # Validation data path
  train_batch_size: int
  val_batch_size: int
  max_prompt_length: int
  max_response_length: int
  return_raw_chat: bool
  gen_batch_size: int
```

## vLLM Configuration

### LLM Initialization

```python
LLM(
    model: str,                    # Model path or HuggingFace ID
    tensor_parallel_size: int = 1,
    pipeline_parallel_size: int = 1,
    gpu_memory_utilization: float = 0.9,
    max_num_seqs: int = 256,
    max_model_len: int = 16384,
    dtype: str = "float16",
    quantization: str = None,       # awq/gptq/squeezellm
    trust_remote_code: bool = False,
    enforce_eager: bool = False,
    enable_prefix_caching: bool = False,
    limit_mm_per_prompt: dict = None,
    chat_template_func: callable = None,
    tokenizer: str = None,
    distributed_executor_backend: str = "ray",
    worker_use_ray: bool = False,
    # ... more options
)
```

### SamplingParams

```python
SamplingParams(
    temperature: float = 1.0,
    top_p: float = 1.0,
    top_k: int = -1,
    min_p: float = 0.0,
    max_tokens: int = 16,
    seed: int = None,
    stop: Union[str, List[str]] = None,
    stop_token_ids: List[int] = None,
    include_stop_str_in_output: bool = False,
    logprobs: int = None,
    prompt_logprobs: int = None,
    detokenize: bool = True,
    # ... more options
)
```

## Example Configurations

### MSRL Full Config

```yaml
# msrl_full.yaml
rl_config:
  n_samples_per_prompt: 4
  max_prompt_length: 4096
  max_response_length: 2048
  actor_rollout_dispatch_size: 4
  kl_ctrl:
    kl_coef: 0.001

actor_config:
  tensor_parallel_size: 8
  pipeline_parallel_size: 1
  tokenizer_name_or_path: meta-llama/Llama-3-8B
  global_batch_size: 64
  train_iters: 1000
  save_interval: 100
  save: ./checkpoints

generate_config:
  tokenizer_name_or_path: meta-llama/Llama-3-8B
  trust_remote_code: false
  dtype: bfloat16
  infer_tensor_parallel_size: 8
  infer_pipeline_parallel_size: 1
  max_num_seqs: 256
  max_model_len: 4096
  gpu_memory_utilization: 0.8
  enforce_eager: false
  sampling_config:
    temperature: 0.2
    top_p: 0.95
    max_tokens: 2048
```

### VERL Full Config

```yaml
# verl_full.yaml
trainer:
  n_gpus_per_node: 8
  nnodes: 1
  total_epochs: 15
  save_freq: 100
  project_name: agent_training
  experiment_name: grpo_llama3_8b
  default_local_dir: ./checkpoints

actor_rollout_ref:
  model:
    path: meta-llama/Llama-3-8B
    use_remove_padding: true
  
  actor:
    strategy: fsdp2
    optim:
      lr: 1.0e-6
    ppo_mini_batch_size: 256
    use_dynamic_bsz: true
    ppo_max_token_len_per_gpu: 24000
    use_kl_loss: true
    kl_loss_coef: 0.001
    fsdp_config:
      param_offload: false
      optimizer_offload: false
  
  rollout:
    name: vllm
    n: 4
    tensor_model_parallel_size: 2
    gpu_memory_utilization: 0.8
  
  ref:
    strategy: fsdp2

algorithm:
  adv_estimator: grpo
  gamma: 1.0
  lam: 0.95
  norm_adv_by_std_in_grpo: true
  kl_ctrl:
    kl_coef: 0.001
```
