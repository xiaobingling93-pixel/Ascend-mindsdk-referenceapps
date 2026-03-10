### 配套版本说明
dify:0.15.3

milvus: v2.5.0 及以上

streamlit

### 使用步骤：

1 部署milvus服务（[部署参考链接](https://milvus.io/docs/zh/install_standalone-docker.md)）

2 部署mis-tei emb,reranker服务（[部署参考链接](https://www.hiascend.com/developer/ascendhub/detail/07a016975cc341f3a5ae131f2b52399d)）

3 如果需要解析docx、pdf文件中的图片进行图文并茂回答，启动demo时请配置 --parse_image 使能图片解析功能,需部署VLM模型服务（[部署参考链接](https://www.hiascend.com/developer/ascendhub/detail/9eedc82e0c0644b2a2a9d0821ed5e7ad)）, LLM服务（[部署参考链接](https://www.hiascend.com/developer/ascendhub/detail/125b5fb4e7184b8dabc3ae4b18c6ff99)），注意如果图片尺寸长或宽小于256，由于信息小，将被丢弃处理。

4 执行dify_demo.py运行服务,具体参数可执行 --help查看
```
python3 dify_demo.py
```
5 通过接口上传、删除、查看文档等操作

6 支持在dify界面配置外接知识库，[部署参考参考链接](https://docs.dify.ai/zh-hans/guides/knowledge-base/connect-external-knowledge-base)

7 可调用/query接口问答测试,代码执行路径下存放了LLM回答文件response.md，可通过如下代码启动web网页可直观展示答复内容，复制如下代码在dify_demo.py同级目录下创建st.py

```
import streamlit as st
import re

# 读取 Markdown 文件
with open("./response.md", "r", encoding="utf-8") as file:
    markdown_text = file.read()

# 在 Streamlit 应用中显示 Markdown 内容，同时处理图片
def render_markdown_with_images(markdown_text):
    # 匹配 Markdown 图片语法 ![alt text](image_url)
    pattern = re.compile(r'!\[.*?\]\((.*?)\)')

    # 记录上一个位置
    last_pos = 0

    # 查找所有匹配项
    for match in pattern.finditer(markdown_text):
        # 显示上一个位置到匹配位置之间的文本
        st.markdown(markdown_text[last_pos:match.start()], unsafe_allow_html=True)

        # 显示图片
        img_url = match.group(1)
        st.image(img_url)

        # 更新上一个位置
        last_pos = match.end()

    # 显示剩余的文本
    st.markdown(markdown_text[last_pos:], unsafe_allow_html=True)

render_markdown_with_images(markdown_text)	
```

# 调用函数显示内容
这里只是简单提供展示样例，如果需考虑安全，请开启https安全认证功能

WEB服务启动命令：
```
streamlit run st.py --server.address "127.0.0.1" --server.port 服务端口
```