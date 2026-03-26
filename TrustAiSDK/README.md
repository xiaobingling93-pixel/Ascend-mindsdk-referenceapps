# ai_asset_obfuscate
# 介绍

ai_asset_obfuscate 是一个Python工程项目，用于注册混淆因子并进行混淆模型权重的工具。

## 📄 安装依赖

请参阅下文了解快速安装和使用示例。

确保环境安装 [**Python>=3.8**](https://www.python.org/)

```
pip install -r requirements.txt
```

## 功能特性

ai_asset_obfuscate 提供以下核心功能：

* ​**模型资产混淆**​：对模型权重进行混淆保护，支持多种模型类型和自定义配置
* ​**数据资产混淆**​：对推理数据进行混淆保护，支持一维和二维数据
* ​**图片数据混淆**​：对图片数据进行混淆保护，支持Base64和字节数组格式
* ​**视频数据混淆**​：对视频数据进行混淆保护，支持Base64和字节数组格式
* ​**口令管理**​：提供口令加密功能，保护敏感信息
* ​**混淆因子管理**​：支持混淆因子的创建、下发和本地保存

## 支持的模型列表

✅支持，测试验收
⭕️理论支持，测试无需验收
❌不支持

| 模型类型    | 模型名称           | 混淆态推理    | 推荐卡数         | 推理服务 | 推理性能测试 | 混淆态微调 | LoRA   | 推荐卡数 | 微调后精度测试 | 备注 |
| ------------- | -------------------- | --------------- | ------------------ | ---------- | -------------- | ------------ | -------- | ---------- | ---------------- | ------ |
| DeepSeek    | DeepSeek-V3        | ✅(A2,A3)     | A2：16卡 A3：8卡 | MindIE   | ✅(A2,A3)    | ⭕️       | ⭕️   | -        | -              |      |
| DeepSeek    | DeepSeek-R1        | ✅(A2,A3)     | A2：16卡 A3：8卡 | MindIE   | -            | ⭕️       | ⭕️   | -        | -              |      |
| Qwen2.5     | Qwen2.5-0.5B       | ⭕️          | -                | MindIE   | -            | ⭕️       | ⭕️   | -        | -              |      |
| Qwen2.5     | Qwen2.5-1.5B       | ✅(310,A2,A3) | A2：2卡 A3：1卡  | MindIE   | -            | ⭕️       | ⭕️   | -        | -              |      |
| Qwen2.5     | Qwen2.5-3B         | ⭕️          |                  | MindIE   | -            | ⭕️       | ⭕️   | -        | -              |      |
| Qwen2.5     | Qwen2.5-7B         | ✅(310,A2,A3) | A2：2卡 A3：1卡  | MindIE   | -            | ⭕️       | ⭕️   | -        | -              |      |
| Qwen2.5     | Qwen2.5-14B        | ✅(310,A2,A3) | A2：8卡 A3：4卡  | MindIE   | -            | ⭕️       | ⭕️   | -        | -              |      |
| Qwen2.5     | Qwen2.5-32B        | ✅(310,A2,A3) | A2：8卡 A3：4卡  | MindIE   | ✅(A3)       | ✅(A3)     | ✅(A2) | A3：8卡  | ✅(A3)         |      |
| Qwen2.5     | Qwen2.5-72B        | ⭕️          | -                | MindIE   | -            | ⭕️       | ⭕️   | -        | -              |      |
| Qwen3       | Qwen3-0.6B         | ⭕️          | -                | MindIE   | -            | ⭕️       | ⭕️   | -        | -              |      |
| Qwen3       | Qwen3-1.7B         | ✅(A2)        | A2：1卡          | MindIE   | -            | ✅(A2)     | ✅(A2) | A2：8卡  | -              |      |
| Qwen3       | Qwen3-4B           | ⭕️          | -                | MindIE   | -            | ⭕️       | ⭕️   | -        |                | -    |
| Qwen3       | Qwen3-8B           | ✅(A2)        | A2：1卡          | MindIE   | -            | ✅(A2)     | ✅(A2) | A2：8卡  | -              |      |
| Qwen3       | Qwen3-14B          | ✅(310)       | 310：8卡         | MindIE   | ✅(A2)       | ⭕️       | ⭕️   | -        | -              |      |
| Qwen3       | Qwen3-32B          | ⭕️          | -                | MindIE   | -            | ✅(A3)     | ✅(A3) | A3：8卡  | ✅(A3)         |      |
| Qwen3       | Qwen3-30B-A3B      | ✅(A2)        | A2：4卡          | vLLM     | -            | ✅(A2)     | ✅(A2) | A2：16卡 | -              |      |
| Qwen3       | Qwen3-235B-A22B    | ✅(A3)        | A3：8卡          | vLLM     | -            | ⭕️       | ⭕️   | -        | -              |      |
| Qwen3-VL    | Qwen3-VL-2B        | ⭕️          | -                | vLLM     | -            | ⭕️       | ❌     | -        | -              |      |
| Qwen3-VL    | Qwen3-VL-4B        | ⭕️          | -                | vLLM     | -            | ⭕️       | ❌     | -        | -              |      |
| Qwen3-VL    | Qwen3-VL-8B        | ✅(310)       | 310：2卡         | vLLM     | -            | ✅(A2)     | ❌     | A2：8卡  | -              |      |
| Qwen3-VL    | Qwen3-VL-32B       | ✅(A3)        | A3：4卡          | vLLM     | ✅(A3)       | ✅(A3)     | ❌     | A3：8卡  | ✅(A3)         |      |
| Qwen3-VL    | Qwen3-VL-30B-A3B   | ✅(A2)        | A2：2卡          | vLLM     | ✅(A2)       | ✅(A3)     | ❌     | A3：8卡  | -              |      |
| Qwen3-VL    | Qwen3-VL-235B-A22B | ⭕️          | -                | vLLM     | -            | ⭕️       | ❌     | -        | -              |      |
| Qwen3-Omni  | -                  | ❌            | -                | vLLM     | -            | ❌         | ❌     | -        | -              |      |
| Qwen3-Audio | -                  | ❌            | -                | vLLM     | -            | ❌         | ❌     | -        | -              |      |

## 快速开始

### 模型混淆示例

```python
from ai_asset_obfuscate import ModelAssetObfuscation, ErrorCode, ModelType

# 创建模型混淆实例
model = ModelAssetObfuscation.create_model_obfuscation(
    model_path="/path/to/model",
    model_type=ModelType.Qwen3,
    tp_num=4
)

# 设置混淆因子
result = model.set_seed_content(
    seed_type=1,  # 模型混淆因子
    seed_content="your_seed_content_32_chars_min"
)
if result != ErrorCode.SUCCESS.value:
    print(f"设置混淆因子失败: {result}")

# 执行模型混淆
result = model.model_weight_obf(
    obf_type=1,  # 0:使用所有混淆因子, 1:仅使用模型混淆因子, 2:仅使用数据混淆因子
    model_save_path="/path/to/model_save_path",
    device_type = "cpu",
    device_id=[0, 1, 2, 3]
)
if result == ErrorCode.SUCCESS.value:
    print("模型混淆成功")
```

### 数据混淆示例

```python
from ai_asset_obfuscate import DataAssetObfuscation, ErrorCode, ModelType

# 创建数据混淆实例
data_obf = DataAssetObfuscation(
    vocab_size=32000,
    token_white_list=[0, 1]  # 不做混淆的token白名单
)

# 设置混淆因子
result = data_obf.set_seed_content(
    seed_content="your_seed_content_32_chars_min",
    is_local_save=False,
    seed_ciphertext_dir=None
)

# 混淆二维数据
tokens = [[1, 2, 3], [4, 5, 6]]
obf_tokens = data_obf.data_2d_obf(tokens)

# 解混淆二维数据
deobf_tokens = data_obf.data_2d_deobf(obf_tokens)
```

### 图片混淆示例

```python
from ai_asset_obfuscate.vision_api import ImageDataAssetObfuscation

# 创建图片混淆实例
image_obf = ImageDataAssetObfuscation()

# 设置混淆因子
image_obf.set_seed_content("your_seed_content_32_chars_min")

# 混淆Base64格式图片
image_base64 = "iVBORw0KGgoAAAANSUhEUgAA..."
obf_image = image_obf.image_base64_obf(image_base64)
```

### 视频混淆示例

```python
from ai_asset_obfuscate.vision_api import VideoDataAssetObfuscation

# 创建视频混淆实例
image_obf = VideoDataAssetObfuscation()

# 设置混淆因子
image_obf.set_seed_content("your_seed_content_32_chars_min")

# 混淆Base64格式视频
video_base64 = "iVBORw0KGgoAAAANSUhEUgAA..."
obf_video = image_obf.video_base64_obf(video_base64 )
```

## API接口文档

[**接口文档**](https://gitcode.com/Ascend/mindsdk-referenceapps/blob/master/TrustAiSDK/README_INTERFACE.md)

## 混淆因子管理

### 混淆因子类型

* ​**模型混淆因子（类型1）**​：用于模型权重混淆
* ​**数据混淆因子（类型2）**​：用于推理数据混淆

### 混淆因子生命周期

1. ​**创建**​：通过`distribute_obf_seed`或`local_save_obf_seed`创建混淆因子
2. ​**下发**​：通过TLS/PSK安全通道下发到NPU设备
3. ​**使用**​：在混淆/解混淆操作中使用混淆因子
4. ​**管理**​：支持本地保存和远程下发两种方式

### 混淆因子设置方式

* ​**直接设置**​：通过`set_seed_content`方法直接设置混淆因子明文
* ​**安全通道设置**​：通过`set_seed_safer`方法通过TLS/PSK安全通道设置
* ​**本地加载**​：通过`set_seed_content`方法的`is_local_save`参数从本地加载

## 安全特性

### TLS/PSK安全机制

obf_sdk 采用双重安全机制保护混淆因子：

* ​**TLS（Transport Layer Security）**​：提供安全的通信通道，确保混淆因子在传输过程中的安全性
* ​**PSK（Pre-Shared Key）**​：使用预共享密钥进行额外的安全验证

### 口令加密要求

加密口令需满足以下要求：

* 长度：40-64字符
* 必须包含以下至少2种字符类型：
  * 大写字母（A-Z）
  * 小写字母（a-z）
  * 数字（0-9）
  * 特殊字符（如!@#$%^&*等）

### 安全建议

1. 定期更换混淆因子和口令
2. 使用强密码生成器创建混淆因子
3. 妥善保管TLS证书和PSK密钥
4. 限制混淆因子的访问权限
5. 定期审计混淆因子的使用记录

## 错误码

### 常见错误码

| 错误码 | 错误信息                                                                    | 说明                              |
| -------- | ----------------------------------------------------------------------------- | ----------------------------------- |
| 0      | Success                                                                     | 操作成功                          |
| 1      | Failed                                                                      | 操作失败                          |
| 2      | Failed To Load Library                                                                      | 加载库失败                          |
| 1001   | Parameter validation failed                                                 | 参数验证失败                      |
| 1002   | Path validation failed                                                      | 路径验证失败                      |
| 1003   | Obfuscate seed content validation failed                                    | 混淆因子内容验证失败              |
| 1004   | The config param tp number validation failed                                | TP数量验证失败                    |
| 1005   | The obfuscate config path validation failed                                 | 配置路径验证失败                  |
| 1006   | The obfuscate config file is incorrect json format                          | 配置文件JSON格式错误              |
| 1007   | The model type validation failed                                            | 模型类型验证失败                  |
| 1015   | There is insufficient disk space                                            | 磁盘空间不足                      |
| 1016   | Unknown I/O error                                                           | 未知I/O错误                       |
| 2001   | Encryption passwd failed                                                    | 口令加密失败                      |
| 2002   | Decryption passwd failed                                                    | 口令解密失败                      |
| 2003   | Create obfuscate seed failed                                                | 创建混淆因子失败                  |
| 2004   | Query obfuscate seed failed                                                 | 查询混淆因子失败                  |
| 3001   | Generated random list failed                                                | 生成随机列表失败                  |
| 3002   | The size of vocab must be greater than zero                                 | 词汇表大小必须大于0               |
| 3003   | Item type must be int and item must less than vocab_size                   | 元素类型必须为int且小于词汇表大小 |
| 4001   | The op_type is not supported on the model shape                            | 操作类型不支持该模型形状          |
| 5001   | The flag validation failed                                                  | 标志验证失败                      |
| 5002   | Model weight obfuscation for model protection has already been completed    | 模型保护混淆已完成                |
| 5003   | Model weight obfuscation for data protection has already been completed     | 数据保护混淆已完成                |
| 5004   | Model and data protection via weight obfuscation has already been completed | 模型和数据保护混淆已完成          |
| 5005   | Failed to read configuration file                                           | 读取配置文件失败                  |
| 5006   | Failed to update configuration file                                         | 更新配置文件失败                  |
| 5007   | Model weights do not support current de-obfuscation operation               | 模型权重不支持当前解混淆操作      |
| 5008   | Failed to decode base64 string                                              | Base64解码失败                    |
| 5009   | Failed to open image                                                        | 打开图片失败                      |
| 5010   | Failed to open video                                                        | 打开视频失败                      |
| 5011   | The seed content is not set                                                 | 混淆因子内容未设置                |
| 5016   | Failed to create weight obfuscator                                          | 创建权重混淆器失败                |
| 5017   | Failed to apply weight obfuscation                                          | 应用权重混淆失败                  |
| 5018   | Obfuscator is not initialized                                               | 混淆器未初始化                    |


# 构建 whl 包

## 方法一：使用构建脚本

1. 进入 TrustAiSDK 目录：
   ```bash
   cd TrustAiSDK
   ```

2. 运行构建脚本：
   ```bash
   bash build.sh
   ```

   脚本会自动：
   - 检查并安装构建依赖（setuptools、wheel、build）
   - 自动检测系统架构并构建对应架构的 whl 包
   - 下载对应架构的 so 文件并复制到 ai_asset_obfuscate/libs 目录
   - 将生成的 whl 文件复制到 `output` 目录

## 指定架构构建

如果需要为特定架构构建 whl 包，可以使用 `--arch` 参数：

```bash
# 构建 x86_64 架构的 whl 包
bash build.sh --arch=x86_64

# 构建 aarch64 架构的 whl 包
bash build.sh --arch=aarch64
```

## 构建结果

构建完成后，生成的 whl 包会位于 `TrustAiSDK/output` 目录中，文件名为 `ai_asset_obfuscate-1.0.0-py3-none-linux_{arch}.whl`，其中 `{arch}` 为 `x86_64` 或 `aarch64`。