FROM ubuntu:20.04

WORKDIR /tmp

ARG ARCH=aarch64
ARG PYTHON_VERSION=python3.11
ARG TORCH_VERSION=2.1.0
# 设置时区禁用交互式配置
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y software-properties-common && add-apt-repository -y ppa:deadsnakes/ppa && apt-get update
RUN apt-get update && apt-get install -y curl wget git git-lfs ca-certificates libssl-dev zlib1g-dev unzip tar gcc make cmake libffi-dev g++ libprotobuf-dev pkg-config build-essential libbz2-dev libreadline-dev libsqlite3-dev llvm xz-utils liblzma-dev libopenblas-dev vim gfortran libpq-dev swig ffmpeg

RUN wget https://www.python.org/ftp/python/3.11.0/Python-3.11.0.tgz && tar -xzvf Python-3.11.0.tgz && cd Python-3.11.0 && ./configure --enable-optimizations --prefix=/usr/local && make && make install
RUN ln -s /usr/local/bin/python3 /usr/local/bin/python && ln -s /usr/local/bin/pip3 /usr/local/bin/pip

#配置 python3-config
RUN ln -sf /usr/local/bin/${PYTHON_VERSION}-config /usr/local/bin/python3-config

# 安装cmake
RUN . /tmp/urls.conf && wget -q $CMAKE_URL && \
    tar -zxf cmake-3.24.3.tar.gz && \
    cd cmake-3.24.3 && \
    ./bootstrap && make -j && make install

# 请根据在服务器上执行npu-smi info 命令进行查询，将查询到的"Name"字段最后一位数字删除后值修改PLATFORM字段
ARG PLATFORM=310P

#解决blinker无法卸载的问题
RUN apt-get remove -y python3-blinker && apt-get autoremove -y

# 安装cann 依赖
RUN pip3 install --upgrade setuptools && pip3 install numpy==1.26.4 decorator==5.1.1 sympy==1.12 cffi==1.16.0 pyyaml==6.0.1 pathlib2==2.3.7.post1 protobuf==5.26.0 scipy==1.12.0 requests==2.31.0 psutil==5.9.8 absl-py==2.1.0 attrs==23.2.0

RUN useradd -d /home/HwHiAiUser -u 1000 -m -s /bin/bash HwHiAiUser

ENV LD_LIBRARY_PATH=/usr/local/Ascend/driver/lib64:/usr/local/Ascend/driver/lib64/common:/usr/local/Ascend/driver/lib64/driver:$LD_LIBRARY_PATH

RUN pip3 install build wheel

# 安装openblas
ARG OPENBLAS_INSTALL_PATH=/usr/local/Ascend/OpenBLAS
RUN . /tmp/urls.conf && cd /tmp && \
    git clone $OPENBLAS_URL && \
	cd OpenBLAS && \
	git checkout v0.3.10 && \
    make FC=gfortran USE_OPENMP=1 -j && \
	make PREFIX=${OPENBLAS_INSTALL_PATH} install
ENV LD_LIBRARY_PATH=${OPENBLAS_INSTALL_PATH}/lib:$LD_LIBRARY_PATH


# 安装faiss
ARG FAISS_INSTALL_PATH=/usr/local/faiss/faiss1.10.0
RUN . /tmp/urls.conf && wget $FAISS_URL && \
    tar -xf v1.10.0.tar.gz && \
    cd faiss-1.10.0/faiss && \
    sed -i "149 i virtual void search_with_filter (idx_t n, const float *x, idx_t k, float *distances, idx_t *lables, const void *mask = nullptr) const{}" Index.h && \
    sed -i "49 i template <typename IndexT> IndexIDMapTemplate<IndexT>::IndexIDMapTemplate (IndexT *index, std::vector<idx_t> &ids): index (index), own_fields (false) { this->is_trained = index->is_trained; this->metric_type = index->metric_type; this->verbose = index->verbose; this->d = index->d; id_map = ids; }" IndexIDMap.cpp && \
    sed -i "30 i explicit IndexIDMapTemplate (IndexT *index, std::vector<idx_t> &ids);" IndexIDMap.h && \
    sed -i "217 i utils/sorting.h" CMakeLists.txt && \
    cd .. && cmake -B build . -DFAISS_ENABLE_GPU=OFF -DPython_EXECUTABLE=/usr/local/bin/python3 -DBUILD_TESTING=OFF -DBUILD_SHARED_LIBS=ON -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=${FAISS_INSTALL_PATH} && \
    make -C build -j faiss && \
    make -C build -j swigfaiss && \
    cd build/faiss/python && python3 setup.py bdist_wheel && \
    cd ../../.. && make -C build install && \
    cd build/faiss/python && cp libfaiss_python_callbacks.so ${FAISS_INSTALL_PATH}/lib && \
    cd dist && \
    pip3 install faiss-1.10.0*.whl

# 安装index
COPY ./package/Ascend-mindxsdk-mxindex*_linux-${ARCH}.run /tmp/
RUN bash /tmp/Ascend-mindxsdk-mxindex*_linux-${ARCH}.run --quiet --install --install-path=/usr/local/Ascend --platform=${PLATFORM}


# 安装ascendfaiss
ARG FAISS_INSTALL_PATH=/usr/local/faiss/faiss1.10.0
ARG MXINDEX_INSTALL_PATH=/usr/local/Ascend/mxIndex

COPY ./package/driver /usr/local/Ascend/driver

# 安装torch
RUN pip3 install torch=="${TORCH_VERSION}" --index-url https://download.pytorch.org/whl/cpu
# 安装torch-npu
RUN pip3 install torch-npu=="${TORCH_VERSION}".post13

# 安装mxrag
COPY ./package/Ascend-mindxsdk-mxrag_*_linux-${ARCH}.run /tmp/
RUN bash /tmp/Ascend-mindxsdk-mxrag_*_linux-${ARCH}.run --install --install-path=/usr/local/Ascend --quiet --platform=${PLATFORM}
RUN pip3 install -r /usr/local/Ascend/mxRag/requirements.txt
# 安装mxrag第三方依赖
RUN pip3 install rank_bm25==0.2.2 langchain-opengauss==0.1.5 streamlit mineru numpy==1.26.4 fastapi
#清理临时目录

# 添加环境变量
RUN sed -i '$a\export PYTHONPATH=/root/.local/lib/$PYTHON_VERSION/site-packages/mx_rag/libs/:$PYTHONPATH' /root/.bashrc  && \
    sed -i '$a\export LD_PRELOAD=$(ls /usr/local/lib/$PYTHON_VERSION/site-packages/scikit_learn.libs/libgomp-*):$LD_PRELOAD' /root/.bashrc && \
	sed -i '$a\source /usr/local/Ascend/mxRag/script/set_env.sh' /root/.bashrc && \
    sed -i '$a\export LD_LIBRARY_PATH=/usr/local/Ascend/mxIndex/lib:/usr/local/faiss/faiss1.10.0/lib:$LD_LIBRARY_PATH' /root/.bashrc && \
    sed -i '$a\export PATH=/usr/local/bin:$PATH' /root/.bashrc && \
    sed -i '$a\export ASCEND_HOME=/usr/local/Ascend' /root/.bashrc && \
    sed -i '$a\export ASCEND_VERSION=/usr/local/Ascend/ascend-toolkit/latest' /root/.bashrc && \
    sed -i '$a\export MX_INDEX_MODELPATH=/home/ascend/modelpath' /root/.bashrc && \
    sed -i '$a\export MX_INDEX_INSTALL_PATH=/usr/local/Ascend/mxIndex' /root/.bashrc && \
    sed -i 's/$PYTHON_VERSION/'"$PYTHON_VERSION"'/g' /root/.bashrc && \
	sed -i '$a\export LOGURU_FORMAT="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message!r}</level>"' /root/.bashrc

USER HwHiAiUser:HwHiAiUser

# 安装index for HwHiAiUser
COPY ./package/Ascend-mindxsdk-mxindex*_linux-${ARCH}.run /tmp/
RUN bash /tmp/Ascend-mindxsdk-mxindex*_linux-${ARCH}.run --quiet --install --install-path=/home/HwHiAiUser/Ascend --platform=${PLATFORM}

# 安装mxrag for HwHiAiUser
COPY ./package/Ascend-mindxsdk-mxrag_*_linux-${ARCH}.run /tmp/
RUN bash /tmp/Ascend-mindxsdk-mxrag_*_linux-${ARCH}.run --install --install-path=/home/HwHiAiUser/Ascend --quiet --platform=${PLATFORM}

# 添加环境变量 for HwHiAiUser用户
RUN sed -i '$a\export PYTHONPATH=/home/HwHiAiUser/.local/lib/$PYTHON_VERSION/site-packages/mx_rag/libs/:$PYTHONPATH' /home/HwHiAiUser/.bashrc  && \
    sed -i '$a\export LD_PRELOAD=$(ls /usr/local/lib/$PYTHON_VERSION/site-packages/scikit_learn.libs/libgomp-*):$LD_PRELOAD' /home/HwHiAiUser/.bashrc && \
	sed -i '$a\source /home/HwHiAiUser/Ascend/mxRag/script/set_env.sh' /home/HwHiAiUser/.bashrc && \
    sed -i '$a\export LD_LIBRARY_PATH=/home/HwHiAiUser/Ascend/mxIndex/lib:/usr/local/faiss/faiss1.10.0/lib:$LD_LIBRARY_PATH' /home/HwHiAiUser/.bashrc && \
	sed -i '$a\export PATH=/usr/local/bin:$PATH' /home/HwHiAiUser/.bashrc && \
    sed -i '$a\export MX_INDEX_MODELPATH=/home/HwHiAiUser/Ascend/modelpath' /home/HwHiAiUser/.bashrc && \
    sed -i '$a\export MX_INDEX_INSTALL_PATH=/home/HwHiAiUser/Ascend/mxIndex' /home/HwHiAiUser/.bashrc&& \
    sed -i 's/$PYTHON_VERSION/'"$PYTHON_VERSION"'/g' /home/HwHiAiUser/.bashrc && \
	sed -i '$a\export LOGURU_FORMAT="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message!r}</level>"' /home/HwHiAiUser/.bashrc

ENV MX_INDEX_MULTITHREAD=1
ENV MX_INDEX_FINALIZE=0

USER root
RUN mkdir -p /opt/package/
COPY ./package/Ascend-cann*_linux-${ARCH}.run /opt/package/
RUN . /tmp/urls.conf && wget $ASCENDFAISS_URL -P /opt/package/
COPY ./package/install.sh /opt/package/

RUN rm -rf /tmp/*
USER HwHiAiUser:HwHiAiUser

WORKDIR /home/HwHiAiUser
