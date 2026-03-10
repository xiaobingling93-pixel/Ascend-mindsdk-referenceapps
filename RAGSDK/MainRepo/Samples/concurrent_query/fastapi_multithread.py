import argparse
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException
from paddle.base import libpaddle
from langchain.text_splitter import RecursiveCharacterTextSplitter
from mx_rag.chain import SingleText2TextChain
from mx_rag.document import LoaderMng
from mx_rag.document.loader import DocxLoader
from mx_rag.embedding.local import TextEmbedding
from mx_rag.embedding.service import TEIEmbedding
from mx_rag.knowledge import KnowledgeDB
from mx_rag.knowledge.handler import upload_files
from mx_rag.knowledge.knowledge import KnowledgeStore
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


text_retriever = any
llm = any
reranker = any


def rag_init():
    parse = argparse.ArgumentParser(formatter_class=CustomFormatter)
    parse.add_argument("--embedding_path", type=str, default="/home/mxaiagent/data/acge_text_embedding",
                       help="embedding模型本地路径")
    parse.add_argument("--embedding_url", type=str, default="http://127.0.0.1:8080/embed",
                       help="使用TEI服务化的embedding模型url地址")
    parse.add_argument("--tei_emb", type=bool, default=False, help="是否使用TEI服务化的embedding模型")
    parse.add_argument("--llm_url", type=str, default="http://127.0.0.1:1025/v1/chat/completions", help="大模型url地址")
    parse.add_argument("--model_name", type=str, default="Llama3-8B-Chinese-Chat", help="大模型名称")
    parse.add_argument("--score_threshold", type=float, default=0.5,
                       help="相似性得分的阈值，大于阈值认为检索的信息与问题越相关,取值范围[0,1]")
    parse.add_argument("--reranker_path", type=str,
                       default="/home/mxaiagent/data/bge-reranker-v2-m3", help="reranker模型本地路径")
    parse.add_argument("--reranker_url", type=str, default="http://127.0.0.1:8080/rerank",
                       help="使用TEI服务化的embedding模型url地址")
    parse.add_argument("--tei_reranker", type=bool, default=False, help="是否使用TEI服务化的reranker模型")
    parse.add_argument("--white_path", type=str, nargs='+', default=["/home"], help="文件白名单路径")
    parse.add_argument("--up_files", type=str, nargs='+', default=None, help="要上传的文件路径，需在白名单路径下")
    parse.add_argument("--sql_path", type=str, nargs='+', default="./sql.db", help="关系数据库文件保存路径")
    parse.add_argument("--vector_path", type=str, nargs='+', default="./faiss.index", help="向量数据库文件保存路径")
    parse.add_argument("--question", type=str, default="描述一下地球的内部结构", help="用户问题")
    args = parse.parse_args().__dict__
    embedding_path: str = args.pop('embedding_path')
    embedding_url: str = args.pop('embedding_url')
    tei_emb: bool = args.pop('tei_emb')
    llm_url: str = args.pop('llm_url')
    model_name: str = args.pop('model_name')
    score_threshold: int = args.pop('score_threshold')
    reranker_path: str = args.pop('reranker_path')
    reranker_url: str = args.pop('reranker_url')
    tei_reranker: bool = args.pop('tei_reranker')
    white_path: str = args.pop('white_path')
    up_files: list[str] = args.pop('up_files')
    sql_path: str = args.pop('sql_path')
    vector_path: str = args.pop('vector_path')
    question: str = args.pop('question')

    dev = 0
    if tei_emb:
        emb = TEIEmbedding(url=embedding_url, client_param=ClientParam(use_http=True))
    else:
        emb = TextEmbedding(model_path=embedding_path, dev_id=dev)
    chunk_store = SQLiteDocstore(db_path=sql_path)
    vector_store = MindFAISS(1024, [dev], load_local_index=vector_path)
    global text_retriever
    text_retriever = Retriever(vector_store=vector_store, document_store=chunk_store,
                               embed_func=emb.embed_documents, k=1, score_threshold=score_threshold)

    # 创建知识管理
    knowledge_store = KnowledgeStore(db_path=sql_path)
    knowledge_store.add_knowledge("test", "Default01", "admin")
    knowledge_db = KnowledgeDB(knowledge_store=knowledge_store, chunk_store=chunk_store, vector_store=vector_store,
                               knowledge_name="test", white_paths=white_path, user_id="Default01")

    # 上传文档到知识库
    if up_files:
        loader_mng = LoaderMng()
        loader_mng.register_loader(DocxLoader, [".docx"])
        loader_mng.register_splitter(RecursiveCharacterTextSplitter, [".xlsx", ".docx", ".pdf"],
                                     {"chunk_size": 750, "chunk_overlap": 150, "keep_separator": False})
        upload_files(knowledge_db, up_files, loader_mng=loader_mng, embed_func=emb.embed_documents, force=True)
    # 上传文档结束

    global reranker
    if tei_reranker:
        reranker = TEIReranker(url=reranker_url, client_param=ClientParam(use_http=True))
    else:
        reranker = LocalReranker(reranker_path, dev_id=dev)
    global llm
    llm = Text2TextLLM(base_url=llm_url, model_name=model_name, client_param=ClientParam(use_http=True))


app = FastAPI()


def fun(input_string: str) -> str:
    text2text_chain = SingleText2TextChain(retriever=text_retriever, llm=llm, reranker=reranker)
    res = text2text_chain.query(input_string)
    return f"{res}"


# 创建一个线程池执行器
thread_pool_executor = ThreadPoolExecutor(max_workers=10)


@app.post("/query/")
async def call_fun(items: dict):
    # 使用线程池异步调用 fun 函数
    future = thread_pool_executor.submit(fun, items['question'])
    try:
        result = future.result()
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500) from e


if __name__ == "__main__":
    rag_init()
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
