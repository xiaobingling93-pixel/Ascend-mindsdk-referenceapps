# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024. All rights reserved.

import argparse
import os
from paddle.base import libpaddle
import torch
import torch_npu
from datasets import load_dataset
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger
from mx_rag.document import LoaderMng
from mx_rag.document.loader import DocxLoader
from mx_rag.llm import Text2TextLLM
from mx_rag.reranker.local import LocalReranker
from mx_rag.tools.finetune.generator import TrainDataGenerator, DataProcessConfig
from mx_rag.utils import ClientParam
from mx_rag.utils.file_check import FileCheck
from sentence_transformers import SentenceTransformer
from sentence_transformers import SentenceTransformerTrainer
from sentence_transformers import SentenceTransformerTrainingArguments
from sentence_transformers.evaluation import InformationRetrievalEvaluator
from sentence_transformers.losses import MultipleNegativesRankingLoss
from sentence_transformers.training_args import BatchSamplers

DEFAULT_LLM_TIMEOUT = 10 * 60
key_id = 'id'

class Finetune:
    def __init__(self,
                 document_path: str,
                 generate_dataset_path: str,
                 llm: Text2TextLLM,
                 embed_model_path: str,
                 reranker: LocalReranker,
                 finetune_output_path: str,
                 featured_percentage: float,
                 llm_threshold_score: float,
                 train_question_number: int,
                 query_rewrite_number: int,
                 eval_data_path: str,
                 log_path: str,
                 max_iter: int,
                 increase_rate: float):
        self.document_path = document_path
        self.generate_dataset_path = generate_dataset_path
        self.llm = llm
        self.embed_model_path = embed_model_path
        self.reranker = reranker
        self.finetune_output_path = finetune_output_path

        self.featured_percentage = featured_percentage
        self.llm_threshold_score = llm_threshold_score
        self.train_question_number = train_question_number
        self.query_rewrite_number = query_rewrite_number

        self.eval_data_path = eval_data_path

        self.log_path = log_path
        self.max_iter = max_iter
        self.increase_rate = increase_rate

    def start(self):
        # 配置日志文件
        logger.add(self.log_path, rotation="1 MB", retention="10 days", level="INFO",
                   format="{time} {level} {message}")
        train_data_generator = TrainDataGenerator(self.llm, self.generate_dataset_path, self.reranker)
        logger.info("--------------------Processing origin document--------------------")

        loader_mng = LoaderMng()
        loader_mng.register_loader(loader_class=TextLoader, file_types=[".txt", ".md"])
        loader_mng.register_loader(loader_class=DocxLoader, file_types=[".docx"])
        # 加载文档切分器，使用langchain的
        loader_mng.register_splitter(splitter_class=RecursiveCharacterTextSplitter,
                                     file_types=[".docx", ".txt", ".md"],
                                     splitter_params={"chunk_size": 750,
                                                      "chunk_overlap": 150,
                                                      "keep_separator": False
                                                      }
                                     )

        split_doc_list = train_data_generator.generate_origin_document(self.document_path, loader_mng=loader_mng)
        logger.info("--------------------Calculate origin embedding model recall--------------------")
        origin_recall_top5 = self.evaluate("origin_model", self.embed_model_path)
        logger.info(f"origin_recall@5: {origin_recall_top5}")
        config = DataProcessConfig(question_number=self.train_question_number,
                                   featured_percentage=self.featured_percentage,
                                   llm_threshold_score=self.llm_threshold_score,
                                   query_rewrite_number=self.query_rewrite_number)
        iter_num = 1
        while iter_num <= self.max_iter:
            logger.info(f'the {iter_num} iteration beginning')
            per_data_len = round(len(split_doc_list) // self.max_iter)
            end_index = len(split_doc_list) if iter_num == self.max_iter else iter_num * per_data_len
            train_doc_list = split_doc_list[:end_index]
            logger.info("--------------------Generating training data--------------------")
            train_data_generator.generate_train_data(train_doc_list, config)

            logger.info("--------------------Fine-tuning embedding--------------------")
            train_data_path = os.path.join(self.generate_dataset_path, "train_data.jsonl")
            output_embed_model_path = os.path.join(self.finetune_output_path, 'embedding', str(iter_num))
            if not os.path.exists(output_embed_model_path):
                os.makedirs(output_embed_model_path)
                FileCheck.dir_check(output_embed_model_path)
            self.train_embedding(train_data_path, output_embed_model_path)
            logger.info("--------------------Calculate origin embedding model recall--------------------")
            finetune_recall_top5 = self.evaluate("finetune_model", output_embed_model_path)
            logger.info(f"finetune_recall@5: {finetune_recall_top5}")
            recall_increase = (finetune_recall_top5 - origin_recall_top5) / origin_recall_top5 * 100
            logger.info(f'The recall rate of the {iter_num} iteration increases by {recall_increase}%.')
            iter_num += 1
            if recall_increase > self.increase_rate or finetune_recall_top5 >= 0.95:
                break
            if iter_num < self.max_iter:
                self.delete_dataset_file()

    def train_embedding(self, train_data_path, output_path):
        torch.npu.set_device(torch.device("npu:0"))
        model = SentenceTransformer(self.embed_model_path, device="npu" if torch.npu.is_available() else "cpu")
        train_loss = MultipleNegativesRankingLoss(model)
        train_dataset = load_dataset("json", data_files=train_data_path, split="train")
        args = SentenceTransformerTrainingArguments(
            output_dir=output_path,  # output directory and hugging face model ID
            num_train_epochs=4,  # number of epochs
            per_device_train_batch_size=4,  # train batch size
            gradient_accumulation_steps=16,  # for a global batch size of 512
            warmup_ratio=0.1,  # warmup ratio
            learning_rate=2e-5,  # learning rate, 2e-5 is a good value
            lr_scheduler_type="cosine",  # use constant learning rate scheduler
            optim="adamw_torch_fused",  # use fused adamw optimizer
            batch_sampler=BatchSamplers.NO_DUPLICATES,
            # MultipleNegativesRankingLoss benefits from no duplicate samples in a batch
            logging_steps=10,  # log every 10 steps
        )
        trainer = SentenceTransformerTrainer(
            model=model,
            args=args,
            train_dataset=train_dataset.select_columns(["query", "corpus"]),
            loss=train_loss,
        )
        trainer.train()
        trainer.save_model()
        torch.npu.empty_cache()

    def evaluate(self, model_name, model_path):
        torch.npu.set_device(torch.device("npu:0"))
        model = SentenceTransformer(model_path, device="npu" if torch.npu.is_available() else "cpu")
        eval_data = load_dataset("json", data_files=self.eval_data_path, split="train")
        eval_data = eval_data.add_column(key_id, range(len(eval_data)))
        corpus = dict(
            zip(eval_data[key_id], eval_data["corpus"])
        )
        queries = dict(
            zip(eval_data[key_id], eval_data["query"])
        )
        relevant_docs = {}
        for q_id in queries:
            relevant_docs[q_id] = [q_id]
        evaluator = InformationRetrievalEvaluator(queries=queries,
                                                  corpus=corpus,
                                                  relevant_docs=relevant_docs,
                                                  name=model_name)
        result = evaluator(model)
        return result[model_name + "_cosine_recall@5"]

    def delete_dataset_file(self):
        # 删除dataset下所有文件
        for filename in os.listdir(self.generate_dataset_path):
            file_path = os.path.join(self.generate_dataset_path, filename)
            # 检查是否是文件
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"delete file success: {file_path}")
                except Exception as e:
                    logger.info(f"delete file occur error:", {file_path} - {e})


class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter):
    def _get_default_metavar_for_optional(self, action):
        return action.type.__name__

    def _get_default_metavar_for_positional(self, action):
        return action.type.__name__


if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=CustomFormatter)
    parser.add_argument("--document_path", type=str, default="", help="语料文档路径,支持doc、txt、md格式")
    parser.add_argument("--generate_dataset_path", type=str, default="", help="生成数据保存路径")
    parser.add_argument("--llm_url", type=str, default="http://127.0.0.1/v1/chat/completions", help="大模型推理服务地址")
    parser.add_argument("--llm_model_name", type=str, default="", help="大模型推理服务对应的模型名称")
    parser.add_argument("--use_http", type=bool, default=False, help="是否是http")
    parser.add_argument("--embedding_model_path", type=str, default="", help="embedding模型路径")
    parser.add_argument("--reranker_model_path", type=str, default="", help="reranker模型路径")
    parser.add_argument("--finetune_output_path", type=str, default="", help="微调模型的输出路径")

    parser.add_argument("--featured_percentage", type=float, default=0.8, help="数据精选比例")
    parser.add_argument("--llm_threshold_score", type=float, default=0.8, help="大模型打分阈值")
    parser.add_argument("--train_question_number", type=int, default=2, help="单个文档切片生成的问题数")
    parser.add_argument("--query_rewrite_number", type=int, default=1, help="问题重写次数")

    parser.add_argument("--eval_data_path", type=str, default="", help="评估数据路径")

    parser.add_argument("--log_path", type=str, default='./app.log', help="日志路径")
    parser.add_argument("--max_iter", type=int, default=5, help="最大迭代次数")
    parser.add_argument("--increase_rate", type=float, default=20, help="召回率提升比例")

    args = parser.parse_args()

    logger.info("Fine-tuning beginning")
    client_param = ClientParam(timeout=DEFAULT_LLM_TIMEOUT, use_http=args.use_http)
    text_llm = Text2TextLLM(base_url=args.llm_url, model_name=args.llm_model_name, client_param=client_param)
    local_reranker = LocalReranker(args.reranker_model_path, dev_id=1)

    finetune = Finetune(args.document_path,
                        args.generate_dataset_path,
                        text_llm,
                        args.embedding_model_path,
                        local_reranker,
                        args.finetune_output_path,
                        args.featured_percentage,
                        args.llm_threshold_score,
                        args.train_question_number,
                        args.query_rewrite_number,
                        args.eval_data_path,
                        args.log_path,
                        args.max_iter,
                        args.increase_rate)
    finetune.start()
    logger.info("Fine-tuning ending")
