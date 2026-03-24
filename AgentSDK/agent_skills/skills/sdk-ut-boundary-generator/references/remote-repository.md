# 远程仓库处理指南

本文档描述如何处理 GitCode/GitHub/GitLab 等远程仓库的UT边界测试用例生成请求。

## 支持的仓库类型

| 平台 | HTTPS 格式 | SSH 格式 |
|------|-----------|----------|
| GitCode | `https://gitcode.com/用户名/仓库名` | `git@gitcode.com:用户名/仓库名.git` |
| GitHub | `https://github.com/用户名/仓库名` | `git@github.com:用户名/仓库名.git` |
| GitLab | `https://gitlab.com/用户名/仓库名` | `git@gitlab.com:用户名/仓库名.git` |
| Gitee | `https://gitee.com/用户名/仓库名` | `git@gitee.com:用户名/仓库名.git` |

## URL 解析规则

### 支持的 URL 格式

| URL 格式 | 示例 | 解析结果 |
|---------|------|---------|
| 仅仓库 | `https://gitcode.com/owner/repo` | 默认分支，扫描整个仓库 |
| 指定分支 | `https://gitcode.com/owner/repo/tree/dev` | 分支 `dev`，扫描整个仓库 |
| 指定分支和目录 | `https://gitcode.com/owner/repo/tree/dev/src` | 分支 `dev`，扫描 `src` 目录 |
| 指定分支和文件 | `https://gitcode.com/owner/repo/tree/dev/src/main.cpp` | 分支 `dev`，扫描 `src/main.cpp` 文件 |
| GitHub 格式 | `https://github.com/owner/repo/tree/main/lib` | 分支 `main`，扫描 `lib` 目录 |
| GitLab 格式 | `https://gitlab.com/owner/repo/tree/v1.0/api` | 分支 `v1.0`，扫描 `api` 目录 |

### 解析算法

```
输入: https://gitcode.com/owner/repo/tree/branch/path/to/dir

解析步骤:
1. 提取平台: gitcode.com
2. 提取所有者: owner
3. 提取仓库名: repo
4. 检查是否包含 /tree/
   - 如果包含: 提取分支名和路径
   - 如果不包含: 使用默认分支，路径为根目录
5. 构建克隆 URL: https://gitcode.com/owner/repo.git
```

### 解析示例

| 输入 URL | 克隆 URL | 分支 | 扫描路径 |
|---------|---------|------|---------|
| `https://gitcode.com/Ascend/RecSDK` | `https://gitcode.com/Ascend/RecSDK.git` | 默认 | `/` |
| `https://gitcode.com/Ascend/RecSDK/tree/master` | `https://gitcode.com/Ascend/RecSDK.git` | `master` | `/` |
| `https://gitcode.com/Ascend/RecSDK/tree/master/training` | `https://gitcode.com/Ascend/RecSDK.git` | `master` | `/training` |
| `https://gitcode.com/Ascend/RecSDK/tree/dev/src/core/utils.cpp` | `https://gitcode.com/Ascend/RecSDK.git` | `dev` | `/src/core/utils.cpp` |
| `https://github.com/torvalds/linux/tree/master/kernel` | `https://github.com/torvalds/linux.git` | `master` | `/kernel` |

## 仓库克隆流程

### 第一步：解析用户输入

```
输入类型判断规则：
1. 如果输入以 http://、https://、git@ 开头 → 远程仓库
2. 如果输入是本地路径且存在 → 本地仓库
3. 如果输入是函数名、模块名或问题描述 → 当前工作目录
```

### 第二步：提取仓库信息

从 URL 中提取：
- **仓库平台**：GitCode / GitHub / GitLab / Gitee / 其他
- **仓库所有者**：用户名或组织名
- **仓库名称**：项目名称
- **指定分支**：从 `/tree/branch` 路径中提取
- **扫描路径**：从 `/tree/branch/path` 路径中提取

### 第三步：克隆仓库

```bash
# 默认分支（浅克隆）
git clone --depth 1 https://gitcode.com/owner/repo.git sdk-ut-repo-20260319

# 指定分支（浅克隆）
git clone --depth 1 -b branch_name https://gitcode.com/owner/repo.git sdk-ut-repo-20260319
```

**目录命名规则**：`sdk-ut-{repo_name}-{date}`

### 第四步：确认克隆成功

- 检查目录是否存在
- 检查 `.git` 目录是否存在
- 检查是否有源代码文件
- 检查扫描路径是否存在（如果指定了目录/文件）

## 扫描范围处理

### 扫描范围与上下文

| 用户指定 | 扫描范围 | 上下文范围 | 报告范围 |
|---------|---------|-----------|---------|
| 整个仓库 | 整个仓库 | 整个仓库 | 整个仓库 |
| 指定目录 | 指定目录及其子目录 | 整个仓库 | 指定目录 |
| 指定文件 | 指定文件 | 整个仓库 | 指定文件 |

**关键原则**：
- 扫描范围可以缩小，但上下文分析必须基于完整仓库
- SDK 入口识别需要基于完整仓库
- API 文档读取需要基于完整仓库
- 只报告扫描范围内的测试用例

### 扫描范围验证

在分析开始前，验证扫描路径是否存在：

```
检查项:
1. 如果指定了目录，检查目录是否存在
2. 如果指定了文件，检查文件是否存在
3. 如果路径不存在，提示用户并退出
```

## 用户输入格式示例

| 场景 | 示例输入 |
|------|---------|
| 仅仓库 URL | `https://gitcode.com/user/sdk-project` |
| 指定分支 | `https://gitcode.com/user/sdk-project/tree/dev` |
| 指定分支和目录 | `https://gitcode.com/user/sdk-project/tree/dev/src/core` |
| 指定分支和文件 | `https://gitcode.com/user/sdk-project/tree/dev/src/main.cpp` |
| GitHub 仓库 | `https://github.com/user/sdk-project/tree/main/include` |
| GitLab 仓库 | `https://gitlab.com/user/sdk-project/tree/v2.0/api` |

## 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| 网络连接失败 | 提示检查网络，建议使用镜像或代理 |
| 仓库不存在 | 提示检查 URL 正确性 |
| 无访问权限 | 提示确认访问权限 |
| 分支不存在 | 列出可用分支，建议选择正确分支 |
| 扫描路径不存在 | 提示路径不存在，列出可能的目录 |
| 克隆超时 | 建议使用浅克隆 `--depth 1` |

## 克隆后处理

1. **确认工作目录**：切换到克隆的仓库目录
2. **验证扫描路径**：检查用户指定的目录/文件是否存在
3. **识别项目结构**：
   - 源代码目录：`src/`、`source/`
   - 头文件目录：`include/`、`inc/`
   - API文档目录：`docs/`
   - 测试目录：`test/`、`tests/`
   - 构建配置：`CMakeLists.txt`、`Makefile`
4. **识别编程语言**：确认主要语言是 C/C++ 还是 Python
5. **读取API文档**：从docs目录读取API文档提取边界值
6. **开始测试用例生成**：执行标准生成流程

## 完成后清理

**自动删除** 克隆的仓库目录，无需用户确认：
- 测试报告输出完成后，立即删除克隆目录
- 使用 `Remove-Item -Recurse -Force` (Windows) 或 `rm -rf` (Linux/macOS) 命令
- 确保删除成功，避免占用磁盘空间
