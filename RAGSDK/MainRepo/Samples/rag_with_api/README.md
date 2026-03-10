
# Demo运行说明

## 前提条件

执行Demo前请先阅读[《RAG SDK 用户指南》](https://www.hiascend.com/document/detail/zh/mindsdk/730/rag/ragug/mxragug_0001.html)，并按照其中"安装部署"章节的要求完成必要软、硬件安装。
本章节为"应用开发"章节提供开发样例代码,便于开发者快速开发。

## 样例说明

详细的样例介绍请参考[《RAG SDK 用户指南》](https://www.hiascend.com/document/detail/zh/mindsdk/730/rag/ragug/mxragug_0001.html)"应用开发"章节说明。 其中：

注意：
1.创建知识库过程和在线问答过程使用的embedding模型、关系数据库路径、向量数据库路径需对应保持一致。其中关系数据库和向量数据库路径在样例代码中已经默认设置成一致，embedding模型需用户手动设置成一致。

## 运行及参数说明

1.调用示例

```commandline
# 上传知识库，支持多线程上传
python3 rag_demo_knowledge.py  --file_path "/home/data/MindIE.docx" --file_path "/home/data/gaokao.docx"  

# 在线问答，支持多线程问答
python3 rag_demo_query.py --query "请描述2024年高考作为题目" --query "请问2025年一共有多少天法定节假日"   
```

说明:
调用示例前请先根据用户实际情况完成参数配置,确保embedding模型路径正确，大模型能正常访问，文件路径正确等，参数可以通过修改样例代码，也可通过命令行的方式传入。

2.参数说明

```commandline
#以"创建知识库"为例,用户可以通过以下命令查看参数情况;如需开发其他样例,请详细参考《RAG SDK用户指南》"接口参考"章节。
python3 rag_demo_knowledge.py  --help
```