## API接口文档

### ModelAssetObfuscation 类

模型资产混淆核心类，提供模型权重混淆功能。

#### create_model_obfuscation

创建标准模型混淆实例。

```python
@staticmethod
def create_model_obfuscation(
    model_path: str,
    model_type: ModelType,
    tp_num: int = None,
    token_white_list: list = None,
    obf_coefficient: float = None,
    is_obfuscation: bool = True
) -> 'ModelAssetObfuscation'
```

**参数：**

* `model_path`: 模型文件路径
* `model_type`: 模型类型（ModelType枚举）
* `tp_num`: 张量并行数量
* `token_white_list`: token白名单，该token不做混淆
* `obf_coefficient`: 混淆系数
* `is_obfuscation`: 是否混淆（True混淆，False不混淆）

**返回值：** ModelAssetObfuscation实例

#### create_custom_model_obfuscation

创建自定义模型混淆实例。

```python
@staticmethod
def create_custom_model_obfuscation(
    model_path: str,
    custom_obf_config_path: str,
    tp_num: int = None,
    token_white_list: list = None,
    obf_coefficient: float = None,
    is_obfuscation: bool = True
) -> 'ModelAssetObfuscation'
```

**参数：**

* `model_path`: 模型文件路径
* `custom_obf_config_path`: 配置文件路径
* `tp_num`: 张量并行数量
* `token_white_list`: token白名单，该token不做混淆
* `obf_coefficient`: 混淆系数
* `is_obfuscation`: 是否混淆（True混淆，False不混淆）

**返回值：** ModelAssetObfuscation实例

#### set_seed_content

设置混淆因子内容。

```python
def set_seed_content(
    seed_type: int = Constant.MODEL_SEED_TYPE,
    seed_content: str = None,
    is_local_save: bool = False,
    seed_ciphertext_dir: str = None
) -> (int, str)
```

**参数：**

* `seed_type`: 混淆因子类型（1:模型混淆因子, 2:数据混淆因子）
* `seed_content`: 混淆因子明文内容（32-112字符）
* `is_local_save`: 是否从本地获取混淆因子
* `seed_ciphertext_dir`: 密文保存路径（is_local_save为True时需要）

**返回值：** (错误码, 错误信息)

#### model_weight_obf

执行模型权重混淆。

```python
def model_weight_obf(
    obf_type: int,
    precision_mode: int = None,
    model_save_path: str = None,
    device_type: str = 'cpu',
    device_id: List[int] = None
) -> int
```

**参数：**

* `obf_type`: 混淆类型（0:使用所有混淆因子, 1:仅使用模型混淆因子, 2:仅使用数据混淆因子）
* `precision_mode`: 精度选择(可选0,1)  0为浮点计算模式  1为量化计算模式
* `model_save_path`:  混淆后模型存储路径
* `device_type`: 使用cpu加速
* `device_id`:当device_type是cpu时，可不传；

**返回值：** (错误码, 错误信息)

### DataAssetObfuscation 类

数据资产混淆核心类，提供推理数据混淆和解混淆功能。

#### set_seed_content

设置混淆因子内容。

```python
def set_seed_content(
    seed_content: str = None,
    is_local_save: bool = False,
    seed_ciphertext_dir: str = None
) -> (int, str)
```

**参数：**

* `seed_content`: 混淆因子明文内容（32-112字符）
* `is_local_save`: 是否从本地获取混淆因子
* `seed_ciphertext_dir`: 密文保存路径（is_local_save为True时需要）

**返回值：** (错误码, 错误信息)

#### set_seed_safer

通过TLS/PSK安全通道设置混淆因子。

```python
def set_seed_safer(
    tls_info: tuple,
    psk_info: tuple
) -> (int, str)
```

**参数：**

* `tls_info`: TLS配置元组 (ca_file, cert_file, pri_keyfile, port, ks_path, ciphertext_path)
* `psk_info`: PSK配置元组 (psk_path, ks_path_psk, ciphertext_path_psk)

**返回值：** (错误码, 错误信息)

#### data_2d_obf

混淆二维数据。

```python
def data_2d_obf(tokens: List[List[int]]) -> List[List[int]]
```

**参数：**

* `tokens`: 待混淆的tokens（二维列表，内层元素为int）

**返回值：** 混淆后的tokens

#### data_1d_obf

混淆一维数据。

```python
def data_1d_obf(tokens: List[int]) -> List[int]
```

**参数：**

* `tokens`: 待混淆的tokens（一维列表，元素为int）

**返回值：** 混淆后的tokens

#### data_2d_deobf

解混淆二维数据。

```python
def data_2d_deobf(tokens: List[List[int]]) -> List[List[int]]
```

**参数：**

* `tokens`: 待解混淆的tokens（二维列表，内层元素为int）

**返回值：** 解混淆后的tokens

#### data_1d_deobf

解混淆一维数据。

```python
def data_1d_deobf(tokens: List[int]) -> List[int]
```

**参数：**

* `tokens`: 待解混淆的tokens（一维列表，元素为int）

**返回值：** 解混淆后的tokens

#### token_obf

混淆单个token。

```python
def token_obf(token: int) -> int
```

**参数：**

* `token`: 待混淆的token

**返回值：** 混淆后的token

#### token_deobf

解混淆单个token。

```python
def token_deobf(token: int) -> int
```

**参数：**

* `token`: 待解混淆的token

**返回值：** 解混淆后的token

### ImageDataAssetObfuscation 类

图片数据混淆类，提供图片数据的混淆功能。

#### create_by_config

通过配置创建图片混淆实例。

```python
@staticmethod
def create_by_config(config_path: str) -> 'ImageDataAssetObfuscation'
```

**参数：**

* `config_path`: 配置文件路径

**返回值：** ImageDataAssetObfuscation实例

#### set_seed_content

设置混淆因子内容。

```python
def set_seed_content(
    seed_content: str = None,
    is_local_save: bool = False,
    seed_ciphertext_dir: str = None
) -> (int, str)
```

**参数：**

* `seed_content`: 混淆因子明文内容（32-112字符）
* `is_local_save`: 是否从本地获取混淆因子
* `seed_ciphertext_dir`: 密文保存路径（is_local_save为True时需要）

**返回值：** (错误码, 错误信息)

#### image_base64_obf

混淆Base64格式图片。

```python
def image_base64_obf(image_base64: str) -> str
```

**参数：**

* `image_base64`: Base64格式的图片数据

**返回值：** 混淆后的Base64图片数据

#### image_bytearray_obf

混淆字节数组格式图片。

```python
def image_bytearray_obf(image_bytearray: bytearray) -> bytearray
```

**参数：**

* `image_bytearray`: 字节数组格式的图片数据

**返回值：** 混淆后的字节数组图片数据

### VideoDataAssetObfuscation 类

视频数据混淆类，提供视频数据的混淆功能。

#### create_by_config

通过配置创建视频混淆实例。

```python
@staticmethod
def create_by_config(config_path: str) -> 'VideoDataAssetObfuscation'
```

**参数：**

* `config_path`: 配置文件路径

**返回值：** VideoDataAssetObfuscation实例

#### set_seed_content

设置混淆因子内容。

```python
def set_seed_content(
    seed_content: str = None,
    is_local_save: bool = False,
    seed_ciphertext_dir: str = None
) -> (int, str)
```

**参数：**

* `seed_content`: 混淆因子明文内容（32-112字符）
* `is_local_save`: 是否从本地获取混淆因子
* `seed_ciphertext_dir`: 密文保存路径（is_local_save为True时需要）

**返回值：** (错误码, 错误信息)

#### video_base64_obf

混淆Base64格式视频。

```python
def video_base64_obf(video_base64: str) -> str
```

**参数：**

* `video_base64`: Base64格式的视频数据

**返回值：** 混淆后的Base64视频数据

#### video_bytearray_obf

混淆字节数组格式视频。

```python
def video_bytearray_obf(video_bytearray: bytearray) -> bytearray
```

**参数：**

* `video_bytearray`: 字节数组格式的视频数据

**返回值：** 混淆后的字节数组视频数据

### passwd_enc 函数

对口令进行加密保护。

```python
def passwd_enc(
    ks_path: str,
    passwd: str,
    ciphertext_path: str
) -> (int, str)
```

**参数：**

* `ks_path`: 加密工具路径
* `passwd`: 待加密口令（40-64字符，需包含大小写字母、数字、特殊字符中的至少2种）
* `ciphertext_path`: 加密口令保存路径

**返回值：** (错误码, 错误信息)

**示例：**

```python
from ai_asset_obfuscate import passwd_enc, ErrorCode

result = passwd_enc(
    ks_path="/path/to/ks_tool",
    passwd="YourSecurePassword123!@",
    ciphertext_path="/path/to/ciphertext"
)
if result == ErrorCode.SUCCESS.value:
    print("口令加密成功")
```

### distribute_obf_seed 函数

下发混淆因子到NPU设备。

```python
def distribute_obf_seed(
    seed_type: int,
    tls_conf: TLSConfig,
    psk_conf: PskConfig,
    seed_content: str,
    device_id: List[int] = None
) -> (int, str)
```

**参数：**

* `seed_type`: 混淆因子类型（1:模型混淆因子, 2:数据混淆因子）
* `tls_conf`: TLS通信配置对象
* `psk_conf`: PSK私钥配置对象
* `seed_content`: 混淆因子明文（32-112字符）
* `device_id`: 需要下发的设备ID列表（0-15），可选

**返回值：** (错误码, 错误信息)

**示例：**

```python
from ai_asset_obfuscate import distribute_obf_seed, ErrorCode
from ai_asset_obfuscate.model import TLSConfig, PskConfig

# 创建TLS配置
tls_conf = TLSConfig(
    ca_file="/path/to/ca.pem",
    cert_file="/path/to/cert.pem",
    pri_keyfile="/path/to/key.pem",
    ks_path="/path/to/ks_tool",
    ciphertext_path="/path/to/ciphertext"
)
tls_conf.set_port(1024)

# 创建PSK配置
psk_conf = PskConfig(
    psk_path="/path/to/psk",
    ks_path_psk="/path/to/ks_tool",
    ciphertext_path_psk="/path/to/psk_ciphertext"
)

# 下发混淆因子
result = distribute_obf_seed(
    seed_type=1,
    tls_conf=tls_conf,
    psk_conf=psk_conf,
    seed_content="your_seed_content_32_chars_min",
    device_id=[0, 1]
)
if result == ErrorCode.SUCCESS.value:
    print("混淆因子下发成功")
```

### local_save_obf_seed 函数

本地保存混淆因子。

```python
def local_save_obf_seed(
    seed_type: int,
    seed_ciphertext_dir: str,
    seed_content: str = None
) -> (int, str)
```

**参数：**

* `seed_type`: 混淆因子类型（1:模型混淆因子, 2:数据混淆因子）
* `seed_ciphertext_dir`: 密文保存目录路径
* `seed_content`: 混淆因子明文（32-112字符），如果为None则自动生成随机混淆因子

**返回值：** (错误码, 错误信息)

**示例：**

```python
from ai_asset_obfuscate import local_save_obf_seed, ErrorCode

# 本地保存混淆因子（自动生成）
result = local_save_obf_seed(
    seed_type=1,
    seed_ciphertext_dir="/path/to/save_dir"
)

# 本地保存混淆因子（指定内容）
result = local_save_obf_seed(
    seed_type=1,
    seed_ciphertext_dir="/path/to/save_dir",
    seed_content="your_seed_content_32_chars_min"
)
if result == ErrorCode.SUCCESS.value:
    print("混淆因子保存成功")
```

