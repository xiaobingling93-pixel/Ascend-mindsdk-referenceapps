---
name: refactor-code-review
description: Analyzes pull requests and codebases for implementation and architecture issues, outputs structured analysis reports and refactoring suggestions. Use when reviewing PRs, examining code changes, conducting periodic codebase reviews, or when the user asks for refactoring/architecture analysis.
---

# 重构与代码审视

针对 PR 提交和定期代码仓审视，分析当前实现与架构问题，输出分析报告和重构优化建议。

## 使用场景

- **PR 审视**：每次提交的 pull request，聚焦变更范围内的实现质量与架构一致性
- **拉取已有 PR**：根据 PR 地址拉取远程分支，切到该分支后进行审视与重构
- **定期审视**：对整体代码仓进行架构与实现层面的梳理

## 分析维度

### PR 级别审视（变更驱动）

| 维度 | 关注点 |
|------|--------|
| 实现一致性 | 变更是否与现有风格、模式保持一致 |
| 依赖引入 | 新增依赖是否必要，是否引入循环依赖 |
| 边界与异常 | 错误处理、边界条件是否充分 |
| 可测试性 | 变更是否便于单测、集成测试 |
| 向后兼容 | 接口/行为变更是否兼容既有用法 |

### 代码仓审视（架构驱动）

| 维度 | 关注点 |
|------|--------|
| 分层与职责 | 模块边界是否清晰，是否违反分层原则 |
| 耦合度 | 模块间耦合是否过高，是否存在循环依赖 |
| 可扩展性 | 扩展新功能是否需要大量修改 |
| 重复代码 | 是否存在可抽取的公共逻辑 |
| 技术债 | 过时模式、TODO、临时实现等 |

## 分析报告模板

```markdown
# [项目/PR] 重构分析报告

## 概览
- **审视范围**: [PR #xxx / 代码仓路径]
- **审视日期**: YYYY-MM-DD
- **风险等级**: 🔴 高 / 🟡 中 / 🟢 低

## 一、发现的问题

### 1. [问题类别]
- **位置**: 文件路径:行号
- **描述**: 具体问题说明
- **影响**: 对质量、维护性、性能的影响
- **建议**: 具体重构或优化建议

### 2. ...
（按优先级排序）

## 二、架构层面

- **当前结构**: 简要描述
- **问题点**: 列出主要架构问题
- **改进方向**: 高层次的改进建议

## 三、重构优先级建议

| 优先级 | 项目 | 预估工作量 | 预期收益 |
|--------|------|------------|----------|
| P0 | ... | ... | ... |
| P1 | ... | ... | ... |
| P2 | ... | ... | ... |

## 四、总结与行动计划

- 关键结论（3–5 条）
- 建议的下一步行动
```

## 工作流程

### 拉取已有 PR 流程

当用户提供 PR 地址（如 `https://gitcode.com/Ascend/RecSDK/pull/2303/diffs`）时，先拉取 PR 分支再进行分析：

1. **解析 PR 地址**：从 URL 提取仓库地址与 PR 编号（如 `Ascend/RecSDK`、`2303`）
2. **更新远程代码**：`git fetch origin`
3. **拉取 PR 分支**：`git fetch https://gitcode.com/Ascend/RecSDK.git +refs/merge-requests/2303/head:pr_2303`
   - 将 `2303` 替换为实际 PR 编号，本地分支名为 `pr_2303`
   - GitLab/GitCode 使用 `refs/merge-requests/`；GitHub 使用 `refs/pull/2303/head`
4. **切换到 PR 分支**：`git checkout pr_2303`
5. **执行审视**：按下方「PR 审视流程」进行分析与报告生成

### 目标分支确定

PR 的 diff 需与目标分支（合并目标）对比。目标分支应：

- **优先从用户请求中提取**：如「合入 develop 分支的 …/pull/2303/diffs」→ 目标分支为 `develop`；「合并到 main 的 PR #100」→ `main`
- **常见表述**：合入/合并/merge 到 `X` 分支、target base 为 `X`
- **未明确时**：询问用户（如「PR 的目标合并分支是？默认为 main」），或按仓库惯例使用 `main` / `master` / `develop`

### 获取 PR 变更范围与 diff

**对比分支使用 upstream**，以 upstream 的目标分支为基准（PR 将合入 upstream 仓库的该分支）：

在 PR 分支上（如 `pr_2303`），使用以下命令（`BASE_BRANCH` 替换为上述目标分支，如 `develop`）：

```bash
# 确保 upstream 已配置，无则添加：git remote add upstream <仓库URL>
git fetch upstream

# 变更文件列表（含状态：A=新增, M=修改, D=删除）
git diff --name-status upstream/BASE_BRANCH...HEAD

# 带增删行数统计
git diff --stat upstream/BASE_BRANCH...HEAD

# 完整 diff（可重定向到文件）
git diff upstream/BASE_BRANCH...HEAD
```

指定目录：`git diff upstream/BASE_BRANCH...HEAD -- path/to/dir/`

### PR 审视流程

1. **获取变更范围**：按上节命令获取 diff，确定改动文件
2. **逐文件分析**：对照上述 PR 维度检查实现与依赖
3. **上下文关联**：结合调用链、依赖关系评估影响范围
4. **生成报告**：按模板填写，突出与本次 PR 相关的发现

### 代码仓审视流程

1. **了解项目结构**：阅读 README、主要入口、目录结构
2. **识别核心模块**：找出核心业务、公共库、边界层
3. **依赖与耦合分析**：梳理模块依赖，识别循环依赖与高耦合
4. **模式与重复**：查找重复实现和可抽取模式
5. **生成报告**：按模板填写，重点在架构与长期可维护性

## 输出规范

- **问题分级**：🔴 必须修复 / 🟡 建议修复 / 🟢 可优化
- **建议要具体**：给出可执行步骤或代码示例，避免泛泛而谈
- **量化优先**：如能给出数量、占比、影响范围，尽量量化
- **语言**：报告主体使用中文，技术术语保留英文

## 额外参考

- 更详细的架构分析模式与反模式，见 [reference.md](reference.md)
