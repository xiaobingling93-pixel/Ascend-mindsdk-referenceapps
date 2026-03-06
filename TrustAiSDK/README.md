# ai_asset_obfuscate

华为昇腾ai_asset_obfuscate混淆SDK, 提供模型、数据的预混淆处理能力

## 构建 whl 包

### 方法一：使用构建脚本

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

### 指定架构构建

如果需要为特定架构构建 whl 包，可以使用 `--arch` 参数：

```bash
# 构建 x86_64 架构的 whl 包
bash build.sh --arch=x86_64

# 构建 aarch64 架构的 whl 包
bash build.sh --arch=aarch64
```

### 构建结果

构建完成后，生成的 whl 包会位于 `TrustAiSDK/output` 目录中，文件名为 `ai_asset_obfuscate-1.0.0-py3-none-linux_{arch}.whl`，其中 `{arch}` 为 `x86_64` 或 `aarch64`。