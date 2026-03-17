# Websearcher Agent 参考文档

## 1 WebSearcher Agent 简介

WebSearcher Agent 是一个专门用于执行网络搜索的智能代理组件，能够根据用户查询自动调用搜索引擎（本文以本地检索服务为例），抓取并解析网页内容，提取关键信息。该 Agent 支持多轮搜索与结果相关性排序，并能结合自然语言处理技术对原始网页进行摘要和结构化处理，为问答系统、数据分析、知识库构建等上层应用提供准确、实时的网络数据支持。

## 2 下载数据

- 嵌入模型：[e5-base-v2](https://huggingface.co/intfloat/e5-base-v2)
- 本地 RAG 数据：[Wiki 语料库文件](https://huggingface.co/datasets/inclusionAI/ASearcher-Local-Knowledge/tree/main)
- 训练数据集：[AsearcherBase35k](https://huggingface.co/datasets/inclusionAI/ASearcher-train-data)

## 3 预处理数据集

### 3.1 数据集字段转换
```bash
cd /path/to/your/AgentSDK/websearcher/utils

python process_data.py input.jsonl output.jsonl
# Note: 
# 1. 第一个参数为原始数据集路径；
# 2. 第二个参数为待保存路径。
```

### 3.2 分割数据集
```bash
cd /path/to/your/AgentSDK/websearcher/utils

python split_dataset.py input.jsonl train.jsonl test.jsonl 0.8
# Note: 
# 1. 第一个参数为原始数据集经处理后的路径；
# 2. 第二个参数为分割后的训练集待保存路径；
# 3. 第三个参数为分割后的测试集待保存路径；
# 4. 第四个参数为分割比例。
```

## 4 启动本地 RAG 服务

```bash 
pip install faiss-cpu==1.7.4

# 切换至工作目录
cd /path/to/your/AgentSDK

# 构建本地 wiki RAG 索引
bash examples/agents/websearcher/scripts/build_index.sh

# 启动本地 RAG 服务 (以端口号 11101 为例)
bash examples/agents/websearcher/scripts/launch_local.server.sh 11101
```

## 5 训练 Websearcher Agent
使用AgentSDK训练智能体
```bash
agentic_rl --config-path="/your_config_dir/your_config_file_name.yaml"

# Note:
# 1. 请确保已启动本地 RAG 服务 (websearcher agent默认访问端口号 11101，如果本指南中第三步更改启动端口，需在修改agents_configuration.py中search_url为 http://127.0.0.1:{your_prot}/)。
# 2. 请根据实际情况修改yaml配置文件中的各个参数。
# 3. 请修改agents_configuration.py中tokenizer的路径。
# 4. 如果需要启动context压缩中的MemorySummary功能，需修改agents_configuration.py中client为可访问的服务。
```

## 6 tensorboard 可视化
```bash
tensorboard --logdir=/path/to/your/tensorboard_logs
```
