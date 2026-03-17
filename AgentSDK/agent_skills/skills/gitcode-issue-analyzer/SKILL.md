---
name: gitcode-issue-analyzer
description: "获取并分析GitCode仓库的issue信息（open/closed）。当用户想从GitCode收集issue、分析已关闭issue的解决方案、或获取开启issue的处理建议时调用。支持Ascend项目如mind-cluster、RecSDK等。"
---

# GitCode Issue 分析器

本技能帮助您从GitCode仓库获取并分析issue信息，特别是针对Ascend项目。

## 调用时机

在以下情况下调用此技能：
- 用户想从GitCode仓库收集issue信息
- 用户想分析已关闭的issue以寻找解决方案
- 用户想获取开启issue的处理建议
- 用户提到GitCode、issue或Ascend项目（mind-cluster、RecSDK等）

## 支持的仓库

对于Ascend项目，支持以下仓库：
- mind-cluster
- RecSDK
- IndexSDK
- DrivingSDK
- AgentSDK
- VisionSDK
- MultimodalSDK
- RAGSDK
- MindInferenceService
- MEF
- OMSDK
- ascend-deployer
- memfabric_hybrid
- memcache

您也可以在以下链接中查找更多仓库：`https://gitcode.com/Ascend`

## 前置条件

### 环境变量配置

此技能需要在环境变量 `GITCODE_TOKEN` 中存储GitCode API token。

**在使用此技能之前，引导用户设置token：**

#### Windows (PowerShell):
```powershell
# 临时设置（仅当前会话有效）
$env:GITCODE_TOKEN = "your_token_here"

# 永久设置（用户级别）
[Environment]::SetEnvironmentVariable("GITCODE_TOKEN", "your_token_here", "User")

# 永久设置（系统级别 - 需要管理员权限）
[Environment]::SetEnvironmentVariable("GITCODE_TOKEN", "your_token_here", "Machine")
```

#### Linux/macOS:
```bash
# 临时设置（仅当前会话有效）
export GITCODE_TOKEN="your_token_here"

# 永久设置 - 添加到 ~/.bashrc 或 ~/.zshrc
echo 'export GITCODE_TOKEN="your_token_here"' >> ~/.bashrc
source ~/.bashrc
```

**获取GitCode token的方法：**
1. 登录GitCode (https://gitcode.com)
2. 进入 设置 -> 访问令牌
3. 生成具有适当权限的新token

## 工作流程

### 步骤1：提取仓库名称

从用户的prompt中，使用以下模式提取仓库名称：

1. **直接仓库名称**："收集mind-cluster仓库下的issue信息" -> repo = "mind-cluster"
2. **从URL提取**："https://gitcode.com/Ascend/mind-cluster" -> repo = "mind-cluster"
3. **部分匹配**：如果用户提到项目名称，将其与支持的仓库列表进行匹配

### 步骤2：获取Issue

通过bash命令调用脚本获取issue，将 ${repo} 替换为从用户prompt中提取的仓库名称：

获取脚本位于skill目录下：`.opencode/skill/gitcode-issue-analyzer/scripts/fetch/`

#### 获取开启的Issue：
将xlsx文件保存到此目录下：`.opencode/skill/gitcode-issue-analyzer/`
```bash
python scripts/fetch/fetch_open_issues.py ${repo}
```

#### 获取已关闭的Issue：
将xlsx文件保存到此目录下：`.opencode/skill/gitcode-issue-analyzer/`
```bash
python scripts/fetch/fetch_closed_issues.py ${repo}
```

#### 获取仓库Issue下的所有评论：
将xlsx文件保存到此目录下：`.opencode/skill/gitcode-issue-analyzer/`
```bash
python scripts/fetch/fetch_issue_comments.py ${repo}
```

#### 验证是否成功创建Issue表格：
```bash
python scripts/validate/validate_issue.py ${repo}
```

脚本会自动：
1. 从环境变量读取GITCODE_TOKEN
2. 调用GitCode API获取issue数据
3. 将数据保存为 `${repo_open_issue.xlsx}` 和 `${repo_closed_issue.xlsx}` 以及 `${repo_issue_comments.xlsx}`
4. 验证issue表格是否创建成功

### 步骤3：生成Issue评论处理文档

通过bash命令调用脚本处理issue，将 ${repo} 替换为从用户prompt中提取的仓库名称：

分类脚本位于skill目录下：`.opencode/skill/gitcode-issue-analyzer/scripts/classify/`

#### 生成issue评论处理文档:
```bash
python scripts/classify/classify_issue_comments.py ${repo_issue_comments.xlsx}
```

生成的issue评论处理文档放于skill目录的references目录下：`.opencode/skill/gitcode-issue-analyzer/references/`

注意，先生成完成issue评论处理文档后再进行步骤4：分析Issue

### 步骤4：分析Issue

#### 从本地处理建议文档匹配

匹配脚本位于skill目录下：`.opencode/skill/gitcode-issue-analyzer/scripts/match/`

首先从references目录下的本地issue处理建议文档中匹配，调用python脚本：
```bash
python scripts/match/match_open_issues.py ${repo_open_issue.xlsx}
```

脚本会自动：
1. 读取 `${repo_open_issue.xlsx}` 文件
2. 加载 references 目录下的 issue 处理建议文档
3. 基于标题相似度（阈值80%）进行匹配
4. 将匹配结果按tag分类写入 output 目录

对于没有匹配到的open_issue，则从网络对应仓库上查找。
如果匹配度高，则写入匹配建议到references目录下的markdown文档：`.opencode/skill/gitcode-issue-analyzer/references/`

#### 从仓库文档匹配处理建议

每个仓库的doc目录下文档匹配处理建议：

查找仓库下的README文档和docs目录下的文档：
- README文档：`https://gitcode.com/Ascend/{repo}/blob/master/README.md`
- docs目录：`https://gitcode.com/Ascend/{repo}/tree/master/docs`

例如mind-cluster仓库：
- `https://gitcode.com/Ascend/mind-cluster/blob/master/README.md`
- `https://gitcode.com/Ascend/mind-cluster/tree/master/docs`

#### 从网络公开资料匹配

如果在网络对应仓库上查找都没有匹配的，则采用网络上的公开资料：

**重要要求：**
- 必须有可靠可信的信息来源
- 需要给出来源链接
- 不能胡乱编造

如果匹配度高，则写入匹配建议到references目录下的markdown文档：`.opencode/skill/gitcode-issue-analyzer/references/`

#### 分析已关闭的Issue：
分析已关闭的issue时，关注以下内容：
1. **常见模式** - issue标题和内容中的共同模式
2. **解决指标** - issue_state字段中的状态（如"DONE"）
3. **相关issue** - 具有相似关键词或标签的issue
4. **评论活动** - 评论较多的issue可能有详细的讨论


## 使用示例

### 用户请求：
"帮我收集mind-cluster仓库下的issue信息，并分析closed的issue给出处理建议"

### 执行步骤：
1. 提取 repo = "mind-cluster"
2. 检查GITCODE_TOKEN环境变量
3. 执行 `python scripts/fetch/fetch_open_issues.py mind-cluster`
4. 执行 `python scripts/fetch/fetch_closed_issues.py mind-cluster`
5. 执行 `python scripts/fetch/fetch_issue_comments.py mind-cluster`
6. 执行 `python scripts/validate/validate_issue.py mind-cluster`
6. 执行脚本分析issue的处理评论
7. 为开启的issue提供处理建议

## 输出格式

### Excel文件：
- `mind-cluster_open_issue.xlsx` - 包含所有开启的issue
- `mind-cluster_closed_issue.xlsx` - 包含所有已关闭的issue
- `mind-cluster_issue_comments.xlsx` - 包含所有issue的评论

### 分析报告：
提供摘要，包括：
1. 开启/已关闭issue的总数
2. 常见issue类型及其分布
3. 在已关闭issue中发现的关键模式
4. 针对开启issue的具体处理建议
5. 相似已关闭issue的参考链接

## 错误处理

1. **Token未找到**：引导用户设置GITCODE_TOKEN环境变量
2. **仓库未找到**：验证仓库名称并建议检查URL
3. **API速率限制**：等待并重试，或建议用户等待
4. **空结果**：通知用户未找到任何issue

## 注意事项

- 确保Excel文件使用UTF-8编码保存，以防止字符编码问题
- API可能返回分页结果；如需要请处理分页
- 遵守API速率限制，在请求之间实现适当的延迟
