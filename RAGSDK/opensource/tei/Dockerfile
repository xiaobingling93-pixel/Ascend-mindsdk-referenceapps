FROM ubuntu:20.04

ARG ARCH=aarch64
ARG TORCH_VERSION=2.1.0
# 请根据在服务器上执行npu-smi info 命令进行查询，将查询到的"Name"字段最后一位数字删除后值修改PLATFORM字段
ARG PLATFORM=310P
ARG CANN_VERSION=8.0.0
ARG RAG_SDK_VERSION=7.3.0
ENV no_proxy=172.17.0.1,$no_proxy
# 设置时区禁用交互式配置
ENV DEBIAN_FRONTEND=noninteractive
ENV GIT_SSL_NO_VERIFY=1
# 配置环境变量
ENV RUSTUP_DIST_SERVER=https://mirrors.ustc.edu.cn/rust-static
ENV RUSTUP_UPDATE_ROOT=https://mirrors.ustc.edu.cn/rust-static/rustup
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

RUN apt-get update && apt-get install -y software-properties-common 
RUN apt-get update && apt-get install -y curl wget git git-lfs ca-certificates libssl-dev zlib1g-dev unzip tar gcc make cmake libffi-dev g++ libprotobuf-dev pkg-config build-essential libbz2-dev libreadline-dev libsqlite3-dev llvm xz-utils liblzma-dev libopenblas-dev vim

#RUN wget https://github.com/protocolbuffers/protobuf/releases/download/v29.2/protoc-29.2-linux-aarch_64.zip
COPY ./package/protoc-*-linux-aarch_64.zip .
RUN mv protoc-*-linux-aarch_64.zip /tmp && \
	unzip /tmp/protoc-*-linux-aarch_64.zip -d /tmp/protoc3 && \
	mv /tmp/protoc3/bin/protoc /usr/local/bin && \
	mv /tmp/protoc3/include/* /usr/local/include && \
	rm -rf /tmp/*

ARG PYTHON_VERSION=python3.11
RUN wget https://www.python.org/ftp/python/3.11.0/Python-3.11.0.tgz && tar -xzvf Python-3.11.0.tgz && cd Python-3.11.0 && ./configure --enable-optimizations --prefix=/usr/local && make && make install
RUN ln -s /usr/local/bin/python3 /usr/local/bin/python && ln -s /usr/local/bin/pip3 /usr/local/bin/pip
ENV PATH=/usr/local/bin:$PATH

RUN pip3 install grpcio-tools mypy-protobuf


RUN groupadd HwHiAiUser && useradd -g HwHiAiUser -d /home/HwHiAiUser -m HwHiAiUser -s /bin/bash

WORKDIR /tmp

# 安装torch
RUN pip3 install torch=="${TORCH_VERSION}" --index-url https://download.pytorch.org/whl/cpu 
# 安装torch-npu
RUN pip3 install torch-npu=="${TORCH_VERSION}".post13


#安装CANN 依赖
RUN pip3 install --upgrade setuptools && pip3 install --ignore-installed numpy==1.26.4 decorator==5.1.1 sympy==1.12 cffi==1.16.0 pyyaml==6.0.1 pathlib2==2.3.7.post1 protobuf==5.26.0 scipy==1.12.0 requests==2.31.0 psutil==5.9.8 absl-py==2.1.0 attrs==23.2.0

ENV LD_LIBRARY_PATH=/usr/local/Ascend/driver/lib64:/usr/local/Ascend/driver/lib64/common:/usr/local/Ascend/driver/lib64/driver:$LD_LIBRARY_PATH

#安装pip依赖
RUN pip3 install poetry transformers==4.41.1 scikit-learn



# 安装gcc10
RUN apt-get remove -y gcc g++
RUN apt update && apt install -y gcc-10 g++-10
RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-10 60 && update-alternatives --install /usr/bin/cc cc /usr/bin/gcc-10 60 && update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-10 60 && update-alternatives --install /usr/bin/c++ c++ /usr/bin/g++-10 60


#ENV RUSTUP_DIST_SERVER=""
#ENV RUSTUP_UPDATE_ROOT=""
ENV PIP_INDEX_URL=""

USER HwHiAiUser:HwHiAiUser

#安装RUST
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y --no-update-default-toolchain
#RUN bash -c "source  $HOME/.cargo/env && rustup toolchain install 1.83.0"

#安装 TEI
WORKDIR /home/HwHiAiUser

RUN git clone https://github.com/huggingface/text-embeddings-inference.git && cd text-embeddings-inference && git checkout v1.8.3
COPY ./package/tei.patch /tmp
RUN cd /home/HwHiAiUser/text-embeddings-inference && patch -p1 < /tmp/tei.patch
RUN sed -i 's/channel = .*/channel = "1.88.0"/g' /home/HwHiAiUser/text-embeddings-inference/rust-toolchain.toml
WORKDIR /home/HwHiAiUser/text-embeddings-inference
#ENV RUSTUP_DIST_SERVER=""
#ENV RUSTUP_UPDATE_ROOT=""
RUN  bash -c "source $HOME/.cargo/env && cargo install --path router -F python -F http --no-default-features"

# 以HwHiAiUser用户安装RAG SDK
RUN wget -q http://172.17.0.1:3000/Ascend-mindxsdk-mxrag_${RAG_SDK_VERSION}_linux-${ARCH}.run -P /tmp
RUN bash /tmp/Ascend-mindxsdk-mxrag_*_linux-${ARCH}.run --install --install-path=/home/HwHiAiUser/Ascend --quiet --platform=${PLATFORM} --whitelist=operator

USER root

ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
RUN cd /home/HwHiAiUser/text-embeddings-inference/backends/python/server && make -j16 && make install

#升级python依赖软件
RUN pip3 install einops

# 以root用户安装RAG SDK
COPY ./package/Ascend-mindxsdk-mxrag_*_linux-${ARCH}.run /tmp
RUN bash /tmp/Ascend-mindxsdk-mxrag_*_linux-${ARCH}.run --install --install-path=/usr/local/Ascend --quiet --platform=${PLATFORM} --whitelist=operator

# 安装cann-toolkit和kernel
RUN wget -q http://172.17.0.1:3000/Ascend-cann-toolkit_${CANN_VERSION}_linux-aarch64.run -P /tmp && \
	platform=$(echo $PLATFORM | tr '[A-Z]' '[a-z]') && \
    wget -q http://172.17.0.1:3000/Ascend-cann-${platform}-ops_${CANN_VERSION}_linux-aarch64.run -P /tmp && \
    wget -q http://172.17.0.1:3000/Ascend-cann-nnal_${CANN_VERSION}_linux-aarch64.run -P /tmp


RUN bash /tmp/Ascend-cann-toolkit*_linux-${ARCH}.run --install --quiet
RUN bash /tmp/Ascend-cann-*ops*_linux-${ARCH}.run --install --quiet

# 安装nnal
RUN bash -c "source /usr/local/Ascend/ascend-toolkit/set_env.sh && bash /tmp/Ascend-cann-nnal*_linux-${ARCH}.run --install --quiet"

#拷贝执行脚本
COPY --chown=HwHiAiUser:HwHiAiUser ./package/start.sh /home/HwHiAiUser

RUN chmod 751 /home/HwHiAiUser/start.sh
# 添加环境变量
ENV PATH=/usr/local/bin:$PATH

#清理临时目录
USER root
RUN rm -rf /tmp/* && rm -rf /home/HwHiAiUser/text-embeddings-inference/target

# 设置容器默认启动用户为HwHiAiUser
USER HwHiAiUser:HwHiAiUser

WORKDIR /home/HwHiAiUser

ENTRYPOINT ["bash", "/home/HwHiAiUser/start.sh"]

CMD ["BAAI/bge-large-zh-v1.5", "127.0.0.1", "8080"]


