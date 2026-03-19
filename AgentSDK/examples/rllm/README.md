# Agent SDK快速入门——BaseEngineWrapper抽象类基本使用教程

## 1 介绍

### 1.1 简介
BaseEngineWrapper 类提供统一的抽象接口，允许不同的 AgentEngine 自行适配，从而实现 AgentSDK AgenticRL 训推调 API 与多种类型 AgentEngine 的功能对接。本教程以 rLLM agent 引擎为例，提供 BaseEngineWrapper 的实现类 RllmEngineWrapper，并提供 math agent 的特定场景，实现 rLLM 与 AgentSDK AgenticRL 训推调 API 的功能对接。

### 1.2 支持的产品
本教程支持昇腾 Atlas A2 训练系列产品，如 Atlas 800T A2。

### 1.3 支持的版本
| Agent SDK 版本 | CANN 版本 | Driver / Firmware 版本 |
|----|----|----|  
| 7.3.0 | 8.3.RC1   | 25.3.RC1   |

## 2 安装 Agent 软件包
### 2.1 获取软件包
联系华为工程师获取`Ascend-mindsdk-agentsdk_7.3.0_linux-aarch64.run`或者参考[AgentSDK开源仓库](https://gitcode.com/Ascend/AgentSDK)进行操作。

### 2.2 安装软件包
**步骤1：** 将 Agent SDK 软件包下载到安装环境的任意路径下，并进入软件包所在路径。

**步骤2：** 执行安装命令。
```sh
chmod u+x Ascend-mindsdk-agentsdk_7.3.0_linux-aarch64.run
./Ascend-mindsdk-agentsdk_7.3.0_linux-aarch64.run --install
```

**步骤3：** 设置环境变量。
```sh
export PATH=$PATH:~/.local/bin
```

## 3 安装开源软件及设置环境变量
通过 AgentSDK 使用 MindSpeed-RL 进行训练时，需安装以下指定版本开源软件至指定位置，并设置相应环境变量。

```sh
mkdir -p /home/third-party # 可自定义目录
cd /home/third-party

git clone https://github.com/NVIDIA/Megatron-LM.git
cd Megatron-LM
git checkout core_r0.8.0
cd ..

git clone https://github.com/Ascend/MindSpeed.git
cd MindSpeed
git checkout 2.1.0_core_r0.8.0
cd ..

git clone https://github.com/Ascend/MindSpeed-LLM.git
cd MindSpeed-LLM
git checkout 2.1.0
cd ..

git clone https://github.com/Ascend/MindSpeed-RL.git
cd MindSpeed-RL
git checkout 2.2.0
cd ..

git clone https://github.com/rllm-org/rllm.git
cd rllm
git checkout v0.1
cd .. 

git clone https://github.com/vllm-project/vllm.git
cd vllm
git checkout v0.9.1
VLLM_TARGET_DEVICE=empty pip3 install -e .
cd ..

pip3 install --ignore-installed --upgrade blinker=1.9.0
git clone https://github.com/vllm-project/vllm-ascend.git
cd vllm-ascend
git checkout v0.9.1-dev
pip3 install -e .
cd ..

pip3 install -r MindSpeed/requirements.txt
pip3 install -r MindSpeed-LLM/requirements.txt
pip3 install -r MindSpeed-RL/requirements.txt

# 使能环境变量，根据实际安装的情况调整目录
source /usr/local/Ascend/driver/bin/setenv.sh
source /usr/local/Ascend/ascend-toolkit/set_env.sh
source /usr/local/Ascend/nnal/atb/set_env.sh
export PYTHONPATH=$PYTHONPATH:/home/third-party/Megatron-LM/:/home/third-party/MindSpeed/:/home/third-party/MindSpeed-LLM/:/home/third-party/MindSpeed-RL:/home/third-party/rllm/
```

## 4 运行

### 4.1 Token模式运行
**步骤1：** 下载示例代码 `AgentSDK/examples/rllm` 至工作文件夹。


**步骤2：** 新建 yaml 配置文件，编辑配置参数。
```sh
vim /your_config_dir/your_config_file_name.yaml

# 编辑配置参数（示例）
tokenizer_name_or_path: /path/to/tokenizer
agent_name: websearcher
agent_engine_wrapper_path: /your_workdir/AgentSDK/examples/rllm/rllm_engine_wrapper.py
use_stepwise_advantage: false
train_backend: mindspeed_rl
model_name: qwen2.5-7b
num_gpus_per_node: 8
max_model_len: 16384
max_num_seqs: 32
max_num_batched_tokens: 16384
rollout_n: 16
infer_tensor_parallel_size: 4
gpu_memory_utilization: 0.4
kl_penalty: low_var_kl
use_tensorboard: true
test_before_train: false
test_only: false
dataset_additional_keys: ["problem", "ground_truth"] # 必须匹配预处理后数据中的字段名，此处以websearcher场景为例
top_k: 50
top_p: 0.9
min_p: 0.01
temperature: 0.8
entropy_coeff: 0.001
kl_coef: 0.001
kl_horizon: 1000
lam: 0.95
kl_target: 100.0
weight_decay: 0.01
max_prompt_length: 8192
actor_rollout_dispatch_size: 16

mindspeed_rl:
  data_path: /path/to/data
  load_params_path: /path/to/model_weights
  save_params_path: /path/to/model_weights_save
  epochs: 1
  train_iters: 100
  save_interval: 100
  global_batch_size: 16
  mini_batch_size: 16
  seq_length: 16384
  tensor_model_parallel_size: 4
  # 根据需要选择是否添加下面三个参数以开启开启重计算功能
  recompute_granularity: full
  recompute_method: block
  recompute_num_layers: 24
```

**步骤3：** 进入`AgentSDK`目录，启动训练任务。
```sh
cd /your_workdir/AgentSDK
agentic_rl --config-path="/your_config_dir/your_config_file_name.yaml"
```

**步骤4：** 查看结果；运行后会在 `save_params_path` 目录下保存模型权重文件。

### 4.2 Step模式运行
**步骤1：** 下载示例代码 `AgentSDK/examples/rllm` 至工作文件夹。


**步骤2：** 新建 yaml 配置文件，编辑配置参数。
```sh
vim /your_config_dir/your_config_file_name.yaml

# 编辑配置参数（示例）
tokenizer_name_or_path: /path/to/tokenizer
agent_name: websearcher
agent_engine_wrapper_path: /your_workdir/AgentSDK/examples/rllm/rllm_engine_wrapper.py
use_stepwise_advantage: True # 将use_stepwise_advantage设置为True开启step模式
train_backend: mindspeed_rl
model_name: qwen2.5-7b
num_gpus_per_node: 8
max_model_len: 16384
max_num_seqs: 32
max_num_batched_tokens: 16384
rollout_n: 16
infer_tensor_parallel_size: 4
gpu_memory_utilization: 0.4
kl_penalty: low_var_kl
use_tensorboard: true
test_before_train: false
test_only: false
dataset_additional_keys: ["problem", "ground_truth"] # 必须匹配预处理后数据中的字段名，此处以websearcher场景为例
top_k: 50
top_p: 0.9
min_p: 0.01
temperature: 0.8
entropy_coeff: 0.001
kl_coef: 0.001
kl_horizon: 1000
lam: 0.95
kl_target: 100.0
weight_decay: 0.01
max_prompt_length: 8192
actor_rollout_dispatch_size: 16

mindspeed_rl:
  data_path: /path/to/data
  load_params_path: /path/to/model_weights
  save_params_path: /path/to/model_weights_save
  epochs: 1
  train_iters: 100
  save_interval: 100
  global_batch_size: 16
  mini_batch_size: 16
  seq_length: 16384
  tensor_model_parallel_size: 4
  # 根据需要选择是否添加下面三个参数以开启开启重计算功能
  recompute_granularity: full
  recompute_method: block
  recompute_num_layers: 24
```

**步骤3：** 修改`AgentSDK/examples/rllm/rllm_engine_wrapper.py`文件，将mode修改为Step模式。
```
class RllmEngineWrapper(BaseEngineWrapper):
    ...
    def __init__(
        self,
        agent_name: str,
        tokenizer: Any,
        sampling_params: Optional[Dict[str, Any]] = None,
        max_prompt_length: int = DEFAULT_MAX_PROMPT_LENGTH,
        max_response_length: int = DEFAULT_MAX_RESPONSE_LENGTH,
        n_parallel_agents: int = DEFAULT_N_PARALLEL_AGENTS,
        max_steps: int = DEFAULT_MAX_STEPS,
        mode: str = "Step",  # ← 修改此处：从 "Token" 改为 "Step"
    ) -> None:
    ...
```

**步骤4：** 进入`AgentSDK`目录，启动训练任务。
```sh
cd /your_workdir/AgentSDK
agentic_rl --config-path="/your_config_dir/your_config_file_name.yaml"
```

**步骤5：** 查看结果；运行后会在 `save_params_path` 目录下保存模型权重文件。

**注意：** Step 模式需同时满足两个条件，两个参数需正确对应配置：
- YAML 配置中设置 `use_stepwise_advantage: True`：该参数用于指定训练过程中是否采用 step 模式进行训练
- `RllmEngineWrapper` 初始化时设置 `mode="Step"`：该参数用于指定轨迹数据的内容格式为 step 模式

参数对应关系说明：
- 当 YAML 配置中 `use_stepwise_advantage: false`（默认值）时，`RllmEngineWrapper` 初始化时需设置 `mode="Token"`
- 当 YAML 配置中 `use_stepwise_advantage: True` 时，`RllmEngineWrapper` 初始化时需设置 `mode="Step"`

请确保两个参数的配置保持一致，否则可能导致训练失败或结果不符合预期。
