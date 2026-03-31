---
name: gitcode-pr-security-review
description: GitCode PR安全审查技能。用于自动审查GitCode仓库的Pull Request中的代码安全问题，使用sdk-security-audit技能进行代码安全分析，并将审查结果作为评论发布到对应的PR上。当用户需要对GitCode仓库的PR进行安全代码审查时使用此技能。
---

# GitCode PR Security Review

## Overview

自动审查GitCode仓库Pull Request中的代码安全问题，使用sdk-security-audit技能进行安全分析，并将审查结果作为评论发布到对应的PR。

## Workflow

### 1. 获取GitCode访问令牌

从环境变量 `GITCODE_TOKEN` 获取GitCode访问令牌。如果环境变量不存在，使用 `question` 工具提示用户输入GitCode访问令牌。

### 2. 获取仓库URL

使用 `question` 工具提示用户输入GitCode仓库URL地址。

解析仓库URL，提取 `owner` 和 `repo` 信息。

支持的URL格式：
- `https://gitcode.com/owner/repo`
- `https://gitcode.net/owner/repo`

### 3. 获取所有Open状态的Pull Request

使用GitCode API获取仓库的所有Open状态的Pull Request：

```
GET https://gitcode.com/api/v5/repos/{owner}/{repo}/pulls?state=open
```

请求头：
```
Authorization: Bearer {GITCODE_TOKEN}
```

### 4. 遍历每个Pull Request

对于每个Pull Request，执行以下步骤：

#### 4.1 获取PR的文件变更

使用GitCode API获取PR的所有文件变更：

```
GET https://gitcode.com/api/v5/repos/{owner}/{repo}/pulls/{number}/files
```

请求头：
```
Authorization: Bearer {GITCODE_TOKEN}
```

响应包含每个文件的变更信息，包括：
- `filename`: 文件路径
- `patch`: 变更的diff内容
- `additions`: 新增行数
- `deletions`: 删除行数

#### 4.2 提取变更的代码

对于每个文件，从 `patch` 字段中提取变更的代码内容。

解析diff格式，识别新增的代码行及其行号。

**重要**：代码检视应该只是针对新增的代码，忽略删除的代码。

#### 4.3 执行代码安全审查

**尝试使用 sdk-security-audit 技能**：

首先尝试使用 `skill` 工具加载 `sdk-security-audit` 技能，对变更的代码进行安全审查。

将以下信息传递给 `sdk-security-audit` 技能：
- 文件路径
- 变更的代码内容
- 对应的行号范围

**Fallback 机制**：

如果 `sdk-security-audit` 技能不存在或加载失败，则使用内置的严格审计逻辑：

1. **审计原则**：
   - **0误报**：宁可漏报，绝不误报
   - **证据驱动**：只报告有明确证据的问题
   - **保守严格**：只报告100%确定的安全问题

2. **检查范围**（仅检查新增代码）：
   - 缓冲区溢出：未检查边界就直接使用用户输入的长度/索引
   - 空指针解引用：未检查NULL就直接解引用指针
   - 内存泄漏：malloc/new后没有对应的free/delete
   - 未初始化变量：使用未初始化的局部变量
   - 格式化字符串漏洞：用户输入直接作为printf格式化字符串
   - 整数溢出：算术运算可能导致溢出且未检查
   - SQL注入：用户输入直接拼接到SQL语句
   - 命令注入：用户输入直接拼接到system/exec命令

3. **证据要求**：
   - 必须能看到完整的代码上下文
   - 必须能明确证明问题存在
   - 必须能确定从外部输入可达
   - 必须能确定缺少必要的检查

4. **报告格式**：
   ```
   ## [HIGH] {问题标题}
   
   - **问题类型**：{类型}
   - **文件位置**：{file_path}:{line_number}
   - **问题代码**：{问题代码片段}
   - **风险描述**：{详细描述}
   - **修复建议**：{具体修复方案}
   ```

5. **静默规则**：
   - 不确定的潜在问题 → 不报告
   - 缺少上下文无法判断 → 不报告
   - 可能存在但无法证明 → 不报告
   - 代码风格问题 → 不报告
   - 性能建议 → 不报告

#### 4.4 生成审查结果

根据 `sdk-security-audit` 技能的输出，生成审查结果，包括：
- 安全问题描述
- 严重程度
- 代码位置（文件路径和行号）
- 修复建议

**重要**：只处理高置信度的安全问题，忽略低风险和中等风险的问题。

#### 4.5 用户确认

使用 `question` 工具向用户展示审查结果，并询问是否继续发布评论。

如果用户确认，继续下一步；否则，跳过当前PR。

#### 4.6 发布评论到PR

对于每个高置信度的安全问题，使用GitCode API发布评论到对应的PR：

```
POST https://gitcode.com/api/v5/repos/{owner}/{repo}/pulls/{number}/comments
```

请求头：
```
Authorization: Bearer {GITCODE_TOKEN}
Content-Type: application/json
```

请求体：
```json
{
  "body": "安全问题描述和修复建议",
  "commit_id": "{commit_id}",
  "path": "{file_path}",
  "position": {line_number}
}
```

其中：
- `body`: 安全问题描述和修复建议
- `commit_id`: PR的最新commit ID
- `path`: 文件路径
- `position`: 代码行号

**重要**：每个问题发布为单独的评论，不要将多个问题合并在一个评论中。

### 5. 处理下一个PR

完成当前PR的审查后，判断是否发现高置信度安全问题：

- **如果发现高置信度问题**：发布评论后，询问用户是否继续审查下一个PR
- **如果未发现高置信度问题**：自动继续审查下一个PR，无需用户确认

### 6. 完成审查

完成所有PR的审查后，向用户报告审查结果摘要。

## Resources

### scripts/

此技能使用以下脚本：

- `gitcode_api.py`: GitCode API交互工具，包含以下功能：
  - 获取PR列表
  - 获取PR文件变更
  - 发布PR评论

### references/

- `gitcode_api_docs.md`: GitCode API文档参考，包含使用的API端点说明
