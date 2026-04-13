# RAGSDK镜像构建指导

## 镜像准备目录结构如下
```
.
├── Dockerfile
└── package
    ├── Ascend-mindxsdk-mxindex_7.3.0_linux-aarch64.run
    ├── Ascend-mindxsdk-mxrag_7.3.0_linux-aarch64.run
```
# 准备步骤

1. 在Dockerfile同级目录创建package目录

2. package目录存放Ascend-mindxsdk-mxrag、Ascend-mindxsdk-mxindex相关软件包，确保正确配套系统架构

3. 根据cpu架构构建环境上提前准备好cann基础镜像

4. 在Dockerfile同级目录下执行构建命令
```bash
docker build -t 镜像tag --network host --build-arg ARCH=$(uname -m)  --build-arg PLATFORM=<chip-type> -f Dockerfile .
```
<chip-type>取值请根据在服务器上执行`npu-smi info` 命令进行查询，将查询到的"Name"字段最后一位数字删除后值
