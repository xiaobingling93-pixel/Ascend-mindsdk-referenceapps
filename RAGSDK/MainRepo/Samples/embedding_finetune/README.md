# Embedding微调样例代码说明

## 脚本执行

样例pyhthon脚本执行命令：

```
python3 finetune.py \
--document_path /home/embedding_finetune/rag_optimized/train_document \
--generate_dataset_path /home/embedding_finetune/rag_optimized/dataset \
--llm_url  http://51.38.68.109:1025/v1/chat/completions \
--llm_model_name Llama \
--use_http True \
--embedding_model_path /home/embedding_finetune/bge-large-zh-v1.5 \
--reranker_model_path /home/embedding_finetune/bge-reranker-v2-m3 \
--finetune_output_path /home/embedding_finetune/rag_optimized/finetune_model \
--featured_percentage 0.8 \
--llm_threshold_score 0.8 \
--train_question_number 2 \
--query_rewrite_number 1 \
--eval_data_path /home/embedding_finetune/rag_optimized/eval/evaluate_data.jsonl \
--max_iter 3 \
--log_path /home/embedding_finetune/app.log \
--increase_rate 15
```

参数说明：

document_path：用于训练的原始文档路径，支持txt、md、doc格式

generate_dataset_path：数据集路径，生成的训练数据存放路径

llm_url：大模型推理接口地址

llm_model_name：接口地址对应的大模型名称

use_http：是否是http接口，默认False

embedding_model_path：embedding模型路径

reranker_model_path：reranker模型路径

finetune_output_path：微调模型的输出路径

featured_percentage：精选比例，bm25打分和reranker排序后保留的列表大小

llm_threshold_score：大模型打分优选分数阈值，只保留分数在阈值之上的QD对

train_question_number：针对切分的doc片段，每个doc片段产生的问题数

query_rewrite_number：query重写的次数

eval_data_path：评估数据路径，需要符合{"anchor": "query?", "positive": "answer."}这种格式，也可自定义key值，注意和代码对应

或者借助sdk辅助生成，生成后注意数据质量，需要手动过滤低质量数据

max_iter：最大迭代次数，对于切分后的doc数据来说，设定最大迭代次数，则每次取1/max_iter的数据（顺序取）参与训练数据生成

log_path：log文件保存路径

increase_rate：提升比例，当微调模型的召回率-原始模型的召回率超过了提升比例，则终止训练

## 微调实践之模型合并

如果微调后的模型在其他数据集上表现下降，可以采用模型合并的技术

https://github.com/FlagOpen/FlagEmbedding/blob/master/research/LM_Cocktail/README.md

# [LM-Cocktail: Resilient Tuning of Language Models via Model Merging](https://arxiv.org/abs/2311.13534)

**Make fine-tuning of language models akin to crafting a nuanced cocktail.**

Model merging can be used to improve the performance of single model.
We find this method is also useful for large language models and dense embedding model,
and design the LM-Cocktail strategy which automatically merges fine-tuned models and base model using a simple function
to compute merging weights.
LM-Cocktail can be used to improve the performance on target domain without decrease
the general capabilities beyond target domain.
It also can be used to generate a model for new tasks without fine-tuning.
For more details please refer to our report: [LM-Cocktail](https://arxiv.org/abs/2311.13534).

## Application

The following are some application scenarios (Note that the models used to merge need to have the same architecture and
the same initialization parameter):

### 1. Mitigate the problem of Catastrophic Forgetting

Fine-tuning the base language model could lead to severe degeneration of model’s general capabilities beyond the
targeted domain.
By mixing the fine-tuned model and the base model (use function `mix_models`), LM-Cocktail can significantly enhance
performance in downstream task
while maintaining performance in other unrelated tasks.

If there are some available models fine-tuned on other tasks, you can further use them to enhance your fine-tuned model.
Firstly, you need to collect five example data from your task, then employ function `mix_models_with_data` to compute
weights and merge available models.
In this way, it can assign lower weights to low-quality models, avoiding degrading the performance on your task.
Finally, use `mix_models` to merge produced model and your fine-tuned model.

### 2. Improve the performance of new task without fine-tuning

LM-Cocktail can improve the accuracy of the new task without a requisition to fine-tune a model.
Give a few examples data (e.g., five examples),
and some available models (from open-source community or pre-existing for other tasks),
function `mix_models_wit_data` can automatically assign different merging weights for different model
based their loss in example data, and then merge these available models to generate a task-specific new model.

### 3. Approximate multitask learning

If you have some models who are fine-tune on different tasks, you can merge them into one model to approximate multitask
learning.
The merged model can be used to perform multiple tasks.

## Usage

Install the latest version from source (Recommended):

```bash
git clone https://github.com/FlagOpen/FlagEmbedding.git
cd FlagEmbedding/research/LM_Cocktail
pip install -e .
```

Install by pip:

```bash
pip install -U LM_Cocktail
```

There are two key functions in LM-Cocktail:

### 1. Mix models

`mix_models` can merge models based on the given merging weights.
An example is merging the fine-tuned model and
the base model to mitigate Catastrophic Forgetting after fine-tuning:

```python
from LM_Cocktail import mix_models, mix_models_with_data

# mix LLMs and save it to output_path: ./mixed_model_1
model = mix_models(
    model_names_or_paths=["meta-llama/Llama-2-7b-chat-hf", "Shitao/llama2-ag-news"], 
    model_type='decoder', 
    weights=[0.7, 0.3], 
    output_path='./mixed_llm')
# you can select a weight for your models to get a trade-off between generality and expertise.

# Mix Embedding Models
model = mix_models(
    model_names_or_paths=["BAAI/bge-base-en-v1.5", "Shitao/bge-hotpotqa"], 
    model_type='encoder', 
    weights=[0.5, 0.5],
    output_path='./mixed_embedder')

# Mix reranker Models
model = mix_models(
    model_names_or_paths=["BAAI/bge-reranker-base", "BAAI/bge-reranker-base"], 
    model_type='reranker', 
    weights=[0.5, 0.5],
    output_path="./mixed_reranker")
```

Note that the sum of weights should be equal to 1.

You also can merge multiple models:

```python
from LM_Cocktail import mix_models, mix_models_with_data

model = mix_models(
    model_names_or_paths=["BAAI/bge-base-en-v1.5", "Shitao/bge-hotpotqa", "Shitao/bge-quora", "Shitao/bge-msmarco"], 
    model_type='encoder', 
    weights=[0.3, 0.2, 0.2, 0.3],
    output_path='./mixed_embedder_2')
# The sum of weights should be equal to 1.
```

### 2. Mix models with weights computed based on a few examples

`mix_models_with_data` can compute merging weights based on given data and merge models.
It can be used to produce a model for a new task without training,
or boost the performance for the downstream task by leveraging the knowledge in others models.

- For LLMs

The format of `example_data` for LLMs is a list, where each item is a dict like:

```
{"input": str, "output": str}
```

LM-cocktial will compute the loss of the output.

You can use the example data to merge models as following:

```python
from LM_Cocktail import mix_models, mix_models_with_data

example_data = [
    {"input": "Question: when was the last time anyone was on the moon? Answer:\n", "output": "14 December 1972 UTC"},
    {"input": "Review: \"it 's a charming and often affecting journey . \" Is this movie review sentence negative or positive?\n", "output": "Positive"}
]

model = mix_models_with_data(
    model_names_or_paths=["meta-llama/Llama-2-7b-chat-hf", "Shitao/llama2-ag-news", "Shitao/llama2-nq"], 
    model_type='decoder', 
    example_data=example_data, 
    temperature=5.0)
# you can set the temperature argument to adjust the distribution of mixing weights
```

- For Embedder

The format of `example_data` for LLMs is a list, where each item is a dict like:

```
{"query": str, "pos": List[str], 'neg': List[str]}
```

where pos is a list of positive text and neg is a list of negative text. LM-Cocktail will compute the contrastive loss.

You can use the example data to merge models as following:

```python
from LM_Cocktail import mix_models, mix_models_with_data

example_data = [
    {"query": "How does one become an actor in the Telugu Film Industry?", "pos": [" How do I become an actor in Telugu film industry?"], "neg": [" What is the story of Moses and Ramesses?", " Does caste system affect economic growth of India?"]}, 
    {"query": "Why do some computer programmers develop amazing software or new concepts, while some are stuck with basic programming work?", "pos": [" Why do some computer programmers develops amazing softwares or new concepts, while some are stuck with basics programming works?"], "neg": [" When visiting a friend, do you ever think about what would happen if you did something wildly inappropriate like punch them or destroy their furniture?", " What is the difference between a compliment and flirting?"]}
]

model = mix_models_with_data(
    model_names_or_paths=["BAAI/bge-base-en-v1.5", "Shitao/bge-hotpotqa", "Shitao/bge-quora"], 
    model_type='encoder', 
    example_data=example_data,
    temperature=5.0,
    max_input_length=512,
    neg_number=2)
```

### 3. Mix models layer by layer for reducing memory cost

The function `mix_models_by_layers` creates temporary directories to store weights of individual models and then merges
them layer by layer.

This approach helps in reducing the memory consumption.

Once the merging process is completed, the temporary directories and files will be automatically removed.

```python
from LM_Cocktail import mix_models_by_layers

# Mix Large Language Models (LLMs) and save the combined model to the path: ./mixed_llm
model = mix_models_by_layers(
    model_names_or_paths=["meta-llama/Llama-2-7b-chat-hf", "Shitao/llama2-ag-news"], 
    model_type='decoder', 
    weights=[0.7, 0.3], 
    output_path='./mixed_llm')
```

## Performance

Detailed results please refer to our report: [LM-Cocktail](https://arxiv.org/abs/2311.13534)

- LM-Cocktail for Catastrophic Forgetting

| Model                      | Target Task | Others(29 tasks) |
|:---------------------------|:-----------:|:----------------:|
| Llama                      |    40.8     |       46.8       |
| Fine-tuned                 |    94.4     |       38.6       |
| LM-Cocktail(2 models) [1]  |    94.5     |       47.7       |
| LM-Cocktail(10 models) [2] |    94.4     |       48.3       |

[1]: merge 2 models: fine-tuned model and the base model

[2]: merge 10 models based on five examples: fine-tuned model, the base model, and 8 models fine-tuned on other tasks

| Model                  | Target Task | Other Tasks(14 tasks) |
|:-----------------------|:-----------:|:---------------------:|
| BGE                    |    71.8     |         49.8          |
| Fine-tuned             |    76.0     |         48.5          |
| LM-Cocktail(2 models)  |    74.8     |         50.0          |
| LM-Cocktail(10 models) |    74.7     |         50.6          |

- LM-Cocktail for new tasks without fine-tuning

Merge 10 models fine-tuned on other tasks based on five examples for new tasks:

| Model                  | MMLU(57 tasks) |
|:-----------------------|:--------------:|
| Llama                  |      45.9      |
| Llama-5shot            |      46.7      |
| LM-Cocktail(10 models) |      48.0      |

| Model                  | Retrieval(12 tasks) |
|:-----------------------|:-------------------:|
| BGE                    |        47.3         |
| LM-Cocktail(10 models) |        48.8         |





