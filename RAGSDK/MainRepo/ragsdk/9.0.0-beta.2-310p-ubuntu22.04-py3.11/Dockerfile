FROM swr.cn-south-1.myhuaweicloud.com/ascendhub/cann:9.0.0-beta.2-310p-ubuntu22.04-py3.11

ARG PLATFORM=310P
ARG PYTHON_VERSION=python3.11

RUN pip3 config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip3 config set install.trusted-host mirrors.aliyun.com

RUN apt-get update && apt-get install -y vim tar zip unzip git curl wget dos2unix make gcc g++ ccache gfortran libssl-dev libpq-dev swig ffmpeg

RUN apt-get update && apt-get install -y build-essential ${PYTHON_VERSION}  ${PYTHON_VERSION}-dev ${PYTHON_VERSION}-distutils ${PYTHON_VERSION}-venv

RUN pip3 install numpy==1.26.4

# 先删除cmake老版本
RUN rm -rf /usr/local/bin/cmake /usr/local/share/cmake-* /usr/bin/cmake /usr/share/cmake-*

# 安装cmake
RUN wget https://cmake.org/files/v3.24/cmake-3.24.3.tar.gz && \
    tar -zxf cmake-3.24.3.tar.gz && \
    cd cmake-3.24.3 && \
    ./bootstrap && make -j$(nproc)  && make install

# 安装openblas
ARG OPENBLAS_INSTALL_PATH=/usr/local/Ascend/OpenBLAS
RUN cd /tmp && git clone https://github.com/OpenMathLib/OpenBLAS.git && \
	cd OpenBLAS && \
	git checkout v0.3.10 && \
    make FC=gfortran USE_OPENMP=1 -j$(nproc) && \
	make PREFIX=${OPENBLAS_INSTALL_PATH} install
ENV LD_LIBRARY_PATH=${OPENBLAS_INSTALL_PATH}/lib:$LD_LIBRARY_PATH

# 安装faiss
ARG FAISS_INSTALL_PATH=/usr/local/faiss/faiss1.10.0
RUN cd /tmp && wget https://github.com/facebookresearch/faiss/archive/v1.10.0.tar.gz && \
    tar -xf v1.10.0.tar.gz && \
    cd faiss-1.10.0/faiss && \
    sed -i "149 i virtual void search_with_filter (idx_t n, const float *x, idx_t k, float *distances, idx_t *lables, const void *mask = nullptr) const{}" Index.h && \
    sed -i "49 i template <typename IndexT> IndexIDMapTemplate<IndexT>::IndexIDMapTemplate (IndexT *index, std::vector<idx_t> &ids): index (index), own_fields (false) { this->is_trained = index->is_trained; this->metric_type = index->metric_type; this->verbose = index->verbose; this->d = index->d; id_map = ids; }" IndexIDMap.cpp && \
    sed -i "30 i explicit IndexIDMapTemplate (IndexT *index, std::vector<idx_t> &ids);" IndexIDMap.h && \
    sed -i "217 i utils/sorting.h" CMakeLists.txt && \
    cd .. && cmake -B build . -DFAISS_ENABLE_GPU=OFF -DPython_EXECUTABLE=$(python3 -c "import sys; print(sys.executable)") -DBUILD_TESTING=OFF -DBUILD_SHARED_LIBS=ON -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=${FAISS_INSTALL_PATH} && \
    make -C build -j$(nproc) faiss && \
    make -C build -j$(nproc) swigfaiss && \
    cd build/faiss/python && python3 setup.py bdist_wheel && \
    cd ../../.. && make -C build install && \
    cd build/faiss/python && cp libfaiss_python_callbacks.so ${FAISS_INSTALL_PATH}/lib && \
    cd dist && \
    pip3 install faiss-1.10.0*.whl

COPY ./package/Ascend-* /tmp/
# 安装index
ARG MX_INDEX_INSTALL_PATH=/usr/local/Ascend/mxIndex
ARG MX_INDEX_MODELPATH=/home/ascend/modelpath
RUN ARCH=$(uname -m) && \
    bash /tmp/Ascend-mindxsdk-mxindex*_linux-${ARCH}.run --quiet --install --install-path=/usr/local/Ascend --platform=${PLATFORM} && \
    cd ${MX_INDEX_INSTALL_PATH}/ops && ./custom_opp_${ARCH}.run && \
    mkdir -p ${MX_INDEX_MODELPATH}

# 安装torch
RUN pip3 install torch==2.1.0 --index-url https://download.pytorch.org/whl/cpu --trusted-host download.pytorch.org --trusted-host download-r2.pytorch.org
# 安装torch-npu
RUN pip3 install torch-npu==2.1.0.post13

# 安装mxrag
RUN ARCH=$(uname -m) && \
    bash /tmp/Ascend-mindxsdk-mxrag_*_linux-${ARCH}.run --install --install-path=/usr/local/Ascend --quiet --platform=${PLATFORM} && \
    pip3 install -r /usr/local/Ascend/mxRag/requirements.txt
# 安装mxrag第三方依赖
RUN pip3 install rank_bm25==0.2.2 langchain-opengauss==0.1.5 streamlit mineru numpy==1.26.4 fastapi build

# 安装ascendfaiss
ARG FAISS_INSTALL_PATH=/usr/local/faiss/faiss1.10.0
ARG DRIVER_INSTALL_PATH=/usr/local/Ascend

RUN cd /tmp && wget https://gitee.com/ascend/mindsdk-referenceapps/repository/archive/master.zip && \
    unzip master.zip && \
    cd ./mindsdk-referenceapps-master/IndexSDK/faiss-python && \
    PYTHON_HEADER=$(${PYTHON_VERSION} -c "from sysconfig import get_paths; print(get_paths()['include'])") && \
    PYTHON_NUMPY_INCLUDE=$(${PYTHON_VERSION} -c "import numpy; print(numpy.get_include())") && \
    DRIVER_INSTALL_PATH=/usr/local/Ascend && \    
    swig -python -c++ -Doverride= -module swig_ascendfaiss -I${PYTHON_HEADER} -I${FAISS_INSTALL_PATH}/include -I${MX_INDEX_INSTALL_PATH}/include -DSWIGWORDSIZE64 -o swig_ascendfaiss.cpp swig_ascendfaiss.swig && \
    g++ -std=c++11 -DFINTEGER=int -fopenmp -I/usr/local/include -I${ASCEND_TOOLKIT_HOME}/acllib/include -I${ASCEND_TOOLKIT_HOME}/runtime/include -fPIC -fstack-protector-all -Wall -Wreturn-type -D_FORTIFY_SOURCE=2 -g -O3 -Wall -Wextra -I${PYTHON_HEADER} -I${PYTHON_NUMPY_INCLUDE} -I${FAISS_INSTALL_PATH}/include -I${MX_INDEX_INSTALL_PATH}/include -c swig_ascendfaiss.cpp -o swig_ascendfaiss.o && \
    g++ -std=c++11 -shared -fopenmp -L${ASCEND_TOOLKIT_HOME}/lib64 -L${ASCEND_TOOLKIT_HOME}/acllib/lib64 -L${ASCEND_TOOLKIT_HOME}/runtime/lib64 -L${DRIVER_INSTALL_PATH}/driver/lib64 -L${DRIVER_INSTALL_PATH}/driver/lib64/common -L${DRIVER_INSTALL_PATH}/driver/lib64/driver -L${FAISS_INSTALL_PATH}/lib -L${MX_INDEX_INSTALL_PATH}/lib -Wl,-rpath-link=${ASCEND_TOOLKIT_HOME}/acllib/lib64:${ASCEND_TOOLKIT_HOME}/runtime/lib64:${DRIVER_INSTALL_PATH}/driver/lib64:${DRIVER_INSTALL_PATH}/driver/lib64/common:${DRIVER_INSTALL_PATH}/driver/lib64/driver -L${ASCEND_TOOLKIT_HOME}/devlib -L${ASCEND_TOOLKIT_HOME}/devlib/device -L/usr/local/lib -Wl,-z,relro -Wl,-z,now -Wl,-z,noexecstack -s -o _swig_ascendfaiss.so swig_ascendfaiss.o -L.. -lascendfaiss -lfaiss -lascend_hal -lc_sec && \
    ${PYTHON_VERSION} -m build --no-isolation && \
    cd dist && pip3 install ascendfaiss*.whl && rm -rf /tmp/mindsdk-referenceapps-master/

RUN pip3 uninstall -y pynvml

# 添加环境变量
RUN sed -i '$a\export LD_PRELOAD=\$(find \$(python3 -c "import sklearn; print(sklearn.__path__[0])")/../scikit_learn.libs -name "libgomp-*" | head -1):\$LD_PRELOAD' /root/.bashrc && \
	sed -i '$a\source /usr/local/Ascend/mxRag/script/set_env.sh' /root/.bashrc && \
    sed -i '$a\export LD_LIBRARY_PATH=/usr/local/Ascend/mxIndex/lib:/usr/local/faiss/faiss1.10.0/lib:/usr/local/Ascend/OpenBLAS/lib:$LD_LIBRARY_PATH' /root/.bashrc && \
    sed -i '$a\export PATH=/usr/local/bin:$PATH' /root/.bashrc && \
    sed -i '$a\export ASCEND_HOME=/usr/local/Ascend' /root/.bashrc && \
    sed -i '$a\export ASCEND_VERSION=/usr/local/Ascend/ascend-toolkit/latest' /root/.bashrc && \
    sed -i '$a\export MX_INDEX_MODELPATH=/home/ascend/modelpath' /root/.bashrc && \
    sed -i '$a\export MX_INDEX_INSTALL_PATH=/usr/local/Ascend/mxIndex' /root/.bashrc && \
    sed -i 's/$PYTHON_VERSION/'"$PYTHON_VERSION"'/g' /root/.bashrc && \
	sed -i '$a\export LOGURU_FORMAT="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message!r}</level>"' /root/.bashrc

ENV MX_INDEX_MULTITHREAD=1
ENV MX_INDEX_FINALIZE=0

USER root

WORKDIR /worksapce
