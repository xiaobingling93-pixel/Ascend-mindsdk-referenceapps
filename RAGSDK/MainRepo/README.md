# RAG SDK

RAG SDK是昇腾面向大语言模型的知识增强开发套件，为解决大模型知识更新缓慢以及垂直领域知识问答弱的问题，面向大模型知识库提供垂域调优、生成增强、知识管理等特性，帮助用户搭建专属的高性能、准确度高的大模型问答系统。

## 版本配套说明

本版本配套RAG SDK 7.3.0版本使用,依赖的其他配套软件版本为：

| 软件包简称                 | 配套版本    |
|-----------------------|---------|
| CANN软件包               | 8.5.0   |
| 二进制算子包         | 8.5.0   |
| npu-drive驱动包          | 25.5.0  |
| npu-firmware固件包       | 25.5.0  |
| Index SDK检索软件包        | 7.3.0   |
| MindIE推理引擎软件包         | 2.3.0   |
| Ascend Docker Runtime | 7.0.RC1 |

## 支持的硬件和运行环境

| 产品系列              | 产品型号                |
|-------------------|---------------------|
| Atlas 推理系列产品      | Atlas 300I Duo 推理卡  |
| Atlas 800I A2推理产品 | Atlas 800I A2 推理服务器 |

支持的软件运行环境为:Ubuntu 22.04，Python3.11

## 目录结构与说明

| 目录         | 说明                                                           |
|------------|--------------------------------------------------------------|
| Dockerfile | 部署RAG SDK容器,用户若自行准备镜像文件的参考样例，对应[《RAG SDK 用户指南》](https://www.hiascend.com/document/detail/zh/mindsdk/730/rag/ragug/mxragug_0001.html)"安装部署/安装RAG SDK"章节。            |
| Samples    | RAG SDK完整开发流程的开发参考样例,包含"创建知识库"、"在线问答"、"MxRAGCache缓存和自动生成QA"。 |
| langgraph  | Agentic RAG样例。                                               |
| sd_samples | 安装并运行stable_diffusion模型参考样例。                                 |

