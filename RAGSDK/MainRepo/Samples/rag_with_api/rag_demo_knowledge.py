# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024. All rights reserved.

import argparse
import threading
import traceback
from loguru import logger
from paddle.base import libpaddle
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from mx_rag.embedding.local import TextEmbedding
from mx_rag.embedding.service import TEIEmbedding
from mx_rag.document import LoaderMng
from mx_rag.document.loader import DocxLoader, PdfLoader
from mx_rag.knowledge import KnowledgeDB
from mx_rag.knowledge.handler import upload_files
from mx_rag.knowledge.knowledge import KnowledgeStore
from mx_rag.storage.document_store import SQLiteDocstore
from mx_rag.storage.vectorstore import MindFAISS
from mx_rag.utils import ClientParam


class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter):
    def _get_default_metavar_for_optional(self, action):
        return action.type.__name__

    def _get_default_metavar_for_positional(self, action):
        return action.type.__name__


def rag_demo_upload():
    parse = argparse.ArgumentParser(formatter_class=CustomFormatter)
    parse.add_argument("--embedding_path", type=str, default="/home/data/acge_text_embedding",
                       help="embedding模型本地路径")
    parse.add_argument("--tei_emb", type=bool, default=False, help="是否使用TEI服务化的embedding模型")
    parse.add_argument("--embedding_url", type=str, default="http://127.0.0.1:8080/embed",
                       help="使用TEI服务化的embedding模型url地址")
    parse.add_argument("--embedding_dim", type=int, default=1024, help="embedding模型向量维度")
    parse.add_argument("--white_path", type=str, nargs='+', default=["/home"], help="文件白名单路径")
    parse.add_argument("--file_path", type=str, action='append', help="要上传的文件路径，需在白名单路径下")
    parse.add_argument("--num_threads", type=int, default=2, help="可以根据实际情况调整线程数量")

    args = parse.parse_args().__dict__
    embedding_path: str = args.pop('embedding_path')
    embedding_url: str = args.pop('embedding_url')
    tei_emb: bool = args.pop('tei_emb')
    embedding_dim: int = args.pop('embedding_dim')
    white_path: list[str] = args.pop('white_path')
    file_path: list[str] = args.pop('file_path')
    num_threads: int = args.pop('num_threads')

    try:
        # 离线构建知识库,首先注册文档处理器
        loader_mng = LoaderMng()
        # 加载文档加载器，可以使用mxrag自有的，也可以使用langchain的
        loader_mng.register_loader(loader_class=TextLoader, file_types=[".txt", ".md"])
        loader_mng.register_loader(loader_class=PdfLoader, file_types=[".pdf"])
        loader_mng.register_loader(loader_class=DocxLoader, file_types=[".docx"])
        # 加载文档切分器，使用langchain的
        loader_mng.register_splitter(splitter_class=RecursiveCharacterTextSplitter,
                                     file_types=[".pdf", ".docx", ".txt", ".md"],
                                     splitter_params={"chunk_size": 750,
                                                      "chunk_overlap": 150,
                                                      "keep_separator": False
                                                      }
                                     )
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
        # 初始化知识管理关系数据库
        knowledge_store = KnowledgeStore(db_path="./sql.db")
        # 添加知识库
        knowledge_store.add_knowledge("test", "Default", "admin")
        # 初始化知识库管理
        knowledge_db = KnowledgeDB(knowledge_store=knowledge_store,
                                   chunk_store=chunk_store,
                                   vector_store=vector_store,
                                   knowledge_name="test",
                                   white_paths=white_path,
                                   user_id="Default"
                                   )

        # 多线程上传文件
        batch_size = len(file_path) // num_threads
        if len(file_path) % num_threads != 0:
            batch_size += 1
        file_batchs = [file_path[i:i + batch_size] for i in range(0, len(file_path), batch_size)]

        threads = []
        for batch in file_batchs:
            thread = threading.Thread(target=upload_files,
                                      args=(knowledge_db, batch, loader_mng, emb.embed_documents, True))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 检验文件是否上传成功
        documents = [document.document_name for document in knowledge_db.get_all_documents()]
        logger.info(documents)
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(stack_trace)


if __name__ == '__main__':
    rag_demo_upload()
