#!/bin/bash
ARCH=$(uname -m)

if [[ -n $(id | grep uid=0) ]];then
    usr_id=0
else
    usr_id=1
fi

# 安装cann-toolkit和ops
bash /opt/package/Ascend-cann-toolkit*_linux-${ARCH}.run --install --install-for-all --quiet
bash /opt/package/Ascend-cann-*ops*_linux-${ARCH}.run --install --install-for-all --quiet
#安装 nnal
if [[ $usr_id -eq 0 ]]; then
    bash -c "source /usr/local/Ascend/ascend-toolkit/set_env.sh && bash /opt/package/Ascend-cann-nnal*_linux-${ARCH}.run --install --quiet" 
    
    commands=("source /usr/local/Ascend/ascend-toolkit/set_env.sh" "source /usr/local/Ascend/nnal/atb/set_env.sh" "export ASCEND_VERSION=/usr/local/Ascend/ascend-toolkit/latest" "export ASCEND_HOME=/usr/local/Ascend")
    for cmd in "${commands[@]}";
    do
      if ! grep -Fxq "$cmd" "/root/.bashrc"; then
        # 如果不存在，将命令追加到文件中
        echo "$cmd" >> "/root/.bashrc"
        echo "命令已添加到 /root/.bashrc"
      fi
    done;
    
    source /usr/local/Ascend/ascend-toolkit/set_env.sh
    source /usr/local/Ascend/nnal/atb/set_env.sh
    export ASCEND_VERSION=/usr/local/Ascend/ascend-toolkit/latest
    export ASCEND_HOME=/usr/local/Ascend
    bash /opt/package/Ascend-cann-nnal*_linux-${ARCH}.run --install --quiet
    
    cd /usr/local/Ascend/mxIndex/ops && ./custom_opp_${ARCH}.run && mkdir -p ${MX_INDEX_MODELPATH}
else
    bash -c "source /home/HwHiAiUser/Ascend/ascend-toolkit/set_env.sh && bash /opt/package/Ascend-cann-nnal*_linux-${ARCH}.run --install --quiet" 
    commands=("source /home/HwHiAiUser/Ascend/ascend-toolkit/set_env.sh" "source /home/HwHiAiUser/Ascend/nnal/atb/set_env.sh" "export ASCEND_HOME=/home/HwHiAiUser/Ascend" "export ASCEND_VERSION=/home/HwHiAiUser/Ascend/ascend-toolkit/latest")
    for cmd in "${commands[@]}";
    do
      if ! grep -Fxq "$cmd" "/home/HwHiAiUser/.bashrc"; then
        # 如果不存在，将命令追加到文件中
        echo "$cmd" >> "/home/HwHiAiUser/.bashrc"
        echo "命令已添加到 /home/HwHiAiUser/.bashrc"
      fi
    done;

    source /home/HwHiAiUser/Ascend/ascend-toolkit/set_env.sh
    source /home/HwHiAiUser/Ascend/nnal/atb/set_env.sh
    export ASCEND_HOME=/home/HwHiAiUser/Ascend
    export ASCEND_VERSION=/home/HwHiAiUser/Ascend/ascend-toolkit/latest
    
    cd /home/HwHiAiUser/Ascend/mxIndex/ops && ./custom_opp_${ARCH}.run && mkdir -p ${MX_INDEX_MODELPATH}    
fi


PYTHON_VERSION=python3.11
PYTHON_HEADER=/usr/local/include/${PYTHON_VERSION}/
FAISS_INSTALL_PATH=/usr/local/faiss/faiss1.10.0
DRIVER_INSTALL_PATH=/usr/local/Ascend


rm -rf /tmp/mindsdk-referenceapps-master && unzip -d /tmp /opt/package/master.zip && \
    cd /tmp/mindsdk-referenceapps-master/IndexSDK/faiss-python && \
    swig -python -c++ -Doverride= -module swig_ascendfaiss -I${PYTHON_HEADER} -I${FAISS_INSTALL_PATH}/include -I${MX_INDEX_INSTALL_PATH}/include -DSWIGWORDSIZE64 -o swig_ascendfaiss.cpp swig_ascendfaiss.swig && \
    g++ -std=c++11 -DFINTEGER=int -fopenmp -I/usr/local/include -I${ASCEND_TOOLKIT_HOME}/acllib/include -I${ASCEND_TOOLKIT_HOME}/runtime/include -fPIC -fstack-protector-all -Wall -Wreturn-type -D_FORTIFY_SOURCE=2 -g -O3 -Wall -Wextra -I${PYTHON_HEADER} -I/usr/local/lib/${PYTHON_VERSION}/site-packages/numpy/core/include -I${FAISS_INSTALL_PATH}/include -I${MX_INDEX_INSTALL_PATH}/include -c swig_ascendfaiss.cpp -o swig_ascendfaiss.o && \
    g++ -std=c++11 -shared -fopenmp -L${ASCEND_TOOLKIT_HOME}/lib64 -L${ASCEND_TOOLKIT_HOME}/acllib/lib64 -L${ASCEND_TOOLKIT_HOME}/runtime/lib64 -L${DRIVER_INSTALL_PATH}/driver/lib64 -L${DRIVER_INSTALL_PATH}/driver/lib64/common -L${DRIVER_INSTALL_PATH}/driver/lib64/driver -L${FAISS_INSTALL_PATH}/lib -L${MX_INDEX_INSTALL_PATH}/lib -Wl,-rpath-link=${ASCEND_TOOLKIT_HOME}/acllib/lib64:${ASCEND_TOOLKIT_HOME}/runtime/lib64:${DRIVER_INSTALL_PATH}/driver/lib64:${DRIVER_INSTALL_PATH}/driver/lib64/common:${DRIVER_INSTALL_PATH}/driver/lib64/driver -L/usr/local/lib -Wl,-z,relro -Wl,-z,now -Wl,-z,noexecstack -s -o _swig_ascendfaiss.so swig_ascendfaiss.o -L.. -lascendfaiss -lfaiss -lascend_hal -lc_sec && \
    ${PYTHON_VERSION} -m build --no-isolation && \
    cd dist && pip3 install ascendfaiss*.whl && rm -rf /tmp/mindsdk-referenceapps-master/