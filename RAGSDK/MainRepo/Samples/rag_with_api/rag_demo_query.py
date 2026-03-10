# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024. All rights reserved.

import argparse
import threading
import traceback
from loguru import logger
from paddle.base import libpaddle
from mx_rag.chain import SingleText2TextChain
from mx_rag.embedding.local import TextEmbedding
from mx_rag.embedding.service import TEIEmbedding
from mx_rag.llm import Text2TextLLM
from mx_rag.reranker.local import LocalReranker
from mx_rag.reranker.service import TEIReranker
from mx_rag.retrievers import Retriever
from mx_rag.storage.document_store import SQLiteDocstore
from mx_rag.storage.vectorstore import MindFAISS
from mx_rag.utils import ClientParam



class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter):
    def _get_default_metavar_for_optional(self, action):
        return action.type.__name__

    def _get_default_metavar_for_positional(self, action):
        return action.type.__name__


class ThreadWithResult(threading.Thread):
    def __init__(self, group=None, target=None, name=None, args=None, kwargs=None, *, daemon=None):
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        def function():
            self.result = target(*args, **kwargs)

        super().__init__(group=group, target=function, name=name, daemon=daemon)


def rag_demo_query():
    parse = argparse.ArgumentParser(formatter_class=CustomFormatter)
    parse.add_argument("--embedding_path", type=str, default="/home/data/acge_text_embedding",
                       help="embedding模型本地路径")
    parse.add_argument("--tei_emb", type=bool, default=False, help="是否使用TEI服务化的embedding模型")
    parse.add_argument("--embedding_url", type=str, default="http://127.0.0.1:8080/embed",
                       help="使用TEI服务化的embedding模型url地址")
    parse.add_argument("--embedding_dim", type=int, default=1024, help="embedding模型向量维度")
    parse.add_argument("--llm_url", type=str, default="http://127.0.0.1:1025/v1/chat/completions", help="大模型url地址")
    parse.add_argument("--model_name", type=str, default="Llama3-8B-Chinese-Chat", help="大模型名称")
    parse.add_argument("--score_threshold", type=float, default=0.5,
                       help="相似性得分的阈值，大于阈值认为检索的信息与问题越相关,取值范围[0,1]")
    parse.add_argument("--tei_reranker", type=bool, default=False, help="是否使用TEI服务化的reranker模型")
    parse.add_argument("--reranker_path", type=str, default=None, help="reranker模型本地路径")
    parse.add_argument("--reranker_url", type=str, default=None, help="使用TEI服务化的embedding模型url地址")
    parse.add_argument("--query", type=str, action='append', help="用户问题")
    parse.add_argument("--num_threads", type=int, default=2, help="可以根据实际情况调整线程数量")

    args = parse.parse_args().__dict__
    embedding_path: str = args.pop('embedding_path')
    embedding_url: str = args.pop('embedding_url')
    tei_emb: bool = args.pop('tei_emb')
    embedding_dim: int = args.pop('embedding_dim')
    llm_url: str = args.pop('llm_url')
    model_name: str = args.pop('model_name')
    score_threshold: int = args.pop('score_threshold')
    query: list[str] = args.pop('query')
    num_threads: int = args.pop('num_threads')

    try:
        # 设置向量检索使用的npu卡，具体可以用的卡可执行npu-smi info查询获取
        dev = 0
        # 加载embedding模型，请根据模型具体路径适配
        if tei_emb:
            emb = TEIEmbedding(url=embedding_url, client_param=ClientParam(use_http=True))
        else:
            emb = TextEmbedding(model_path=embedding_path, dev_id=dev)

        # 初始化向量数据库
        vector_store = MindFAISS(x_dim=embedding_dim,
                                 devs=[dev],
                                 load_local_index="./faiss.index",
                                 auto_save=True
                                 )
        # 初始化文档chunk关系数据库
        chunk_store = SQLiteDocstore(db_path="./sql.db")

        # Step2在线问题答复,初始化检索器
        text_retriever = Retriever(vector_store=vector_store,
                                   document_store=chunk_store,
                                   embed_func=emb.embed_documents,
                                   k=1,
                                   score_threshold=score_threshold
                                   )
        # 配置reranker，请根据模型具体路径适配
        reranker_path = args.get("reranker_path")
        reranker_url = args.get("reranker_url")
        tei_reranker = args.get("tei_reranker")
        if tei_reranker:
            reranker = TEIReranker(url=reranker_url, client_param=ClientParam(use_http=True))
        elif reranker_path is not None:
            reranker = LocalReranker(model_path=reranker_path, dev_id=dev)
        else:
            reranker = None
        # 配置text生成text大模型chain，具体ip端口请根据实际情况适配修改
        llm = Text2TextLLM(base_url=llm_url, model_name=model_name, client_param=ClientParam(use_http=True, timeout=60))

        def process_query(input_string: str) -> str:
            text2text_chain = SingleText2TextChain(retriever=text_retriever, llm=llm, reranker=reranker)
            # 知识问答
            res = text2text_chain.query(input_string)
            # 打印结果
            logger.info(res)
            return f"{res}"

        results = []
        batch_size = len(query) // num_threads
        if len(query) % num_threads != 0:
            batch_size += 1
        batchs = [query[i:i + batch_size] for i in range(0, len(query), batch_size)]

        threads = []
        for batch in batchs:
            def process_batch(batch):
                batch_results = []
                for s in batch:
                    batch_results.append(process_query(s))
                return batch_results

            thread = ThreadWithResult(target=process_batch, args=(batch,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()
            results.extend(thread.result)

        return results

    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(stack_trace)
        raise e


if __name__ == '__main__':
    rag_demo_query()
