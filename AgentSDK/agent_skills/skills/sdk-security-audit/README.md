# SDK Security Audit Skill

C/C++ 和 Python SDK 代码安全审计技能，用于自动识别代码中的安全漏洞并生成具备完整证据链的问题报告。

## 功能特性

- **多语言支持**：支持 C/C++ 和 Python 代码安全审计
- **远程仓库审计**：支持 GitHub、GitLab、GitCode 等远程仓库 URL
- **SDK 入口识别**：自动识别对外 SDK 函数入口，聚焦外部可达路径
- **证据链完整**：每个报告问题都有完整的调用路径、代码位置和规则编号
- **误报抑制**：严格遵循"宁漏勿误"原则，避免误报浪费开发者时间

## 使用方法

### 触发场景

当用户请求以下任务时自动触发：

- 安全审计
- 代码审计
- 漏洞扫描
- 安全检查

### 使用示例

```
# 审计本地仓库
对当前仓库进行安全审计

# 审计远程仓库
审计 https://github.com/user/repo 的安全问题

# 指定分支和目录
审计 https://github.com/user/repo/tree/main/src 的内存安全问题

# 关注特定问题类型
审计 Python 代码的命令注入风险
```

## 支持的安全规则

### C/C++ 规则

| 类别 | 规则示例 |
|------|---------|
| 内存安全 | 缓冲区溢出、空指针解引用、UAF |
| 整数安全 | 有符号整数溢出、无符号整数回绕 |
| 资源管理 | 内存泄漏、双重释放 |
| 并发安全 | 竞争条件、死锁风险 |
| 输入验证 | 路径遍历、格式化字符串漏洞 |

### Python 规则

| 类别 | 规则示例 |
|------|---------|
| 代码注入 | eval/exec 使用、命令注入 |
| 反序列化 | pickle 不安全反序列化 |
| 输入验证 | SQL 注入、路径遍历 |
| 敏感信息 | 硬编码密码、日志泄露 |

## 输出格式

审计报告采用精简格式，包含：

```markdown
## [风险等级] 问题标题

**违规规则**：规则编号及名称
**入口函数**：函数名 (文件路径:行号)
**风险位置**：文件路径:行号
**外部可达性**：externally_reachable / conditionally_reachable

### 证据链
- **调用路径**：完整的函数调用链
- **输入传播**：外部输入如何到达危险点
- **缺失检查**：缺少的安全检查

### 触发条件
漏洞成立的必要条件

### 修复建议
具体的代码修复方案
```

## 测试效果

### 测试配置

| 项目 | 说明 |
|------|------|
| 测试仓库 | RecSDK (推荐系统框架) |
| 代码规模 | 200+ C/C++ 文件, 200+ Python 文件 |
| 测试重点 | 内存安全问题 |

### 对比结果

| 指标 | 使用 Skill | 不使用 Skill | 改进 |
|------|-----------|-------------|------|
| **通过率** | 100% | 33% | +67% |
| **耗时** | 45秒 | 60秒 | -25% |
| **Token 消耗** | 85K | 120K | -29% |
| **问题数量** | 2 (高置信度) | 47 (含误报) | 更精准 |
| **SDK 入口识别** | ✅ 81个入口 | ❌ 未识别 | 明确 |
| **规则编号关联** | ✅ 有 | ❌ 无 | 规范 |

### 样例输出

#### 使用 Skill 的报告（精准）

```markdown
# SDK 安全审计报告

## 审计摘要

- **审计范围**：RecSDK 全仓库代码
- **编程语言**：C++ / Python 混合
- **SDK 入口数**：已识别 81 个 `extern "C"` 导出入口
- **发现问题数**：Critical: 0 / High: 2 / Medium: 0 / Low: 0

---

## SDK 入口识别

| 入口函数 | 文件位置 | 识别依据 | 风险等级 |
|---------|---------|---------|---------|
| `unique_op` | training/torch_rec_v2/dynamic_emb/csrc/ops/unique_op/unique_op.cpp:29 | extern "C" | 中 |
| `reduce_grad_op` | training/torch_rec_v2/dynamic_emb/csrc/ops/reduce_grads/reduce_grad.cpp:20 | extern "C" | 中 |
| `pooling_embeddings` | training/torch_rec_v2/dynamic_emb/csrc/ops/pooling_embeddings/pooling_embeddings.cpp:24 | extern "C" | 中 |

---

## [HIGH] 整数溢出风险 - 内存分配乘法运算未检查溢出

**违规规则**：1.3.2 确保无符号整数运算不回绕
**入口函数**：`EmbeddingDynamic::MallocEmbeddingBlock` (embedding_dynamic.cpp:130)
**风险位置**：training/tf_rec_v1/src/core/emb_table/embedding_dynamic.cpp:130
**外部可达性**：conditionally_reachable

### 证据链
- **调用路径**：`EmbeddingDynamic::EmbeddingDynamic` → `MallocEmbeddingBlock` → `aclrtMalloc`
- **输入传播**：`embNum` 和 `extEmbSize_` 来自配置参数，直接传入 `aclrtMalloc`
- **缺失检查**：未验证乘法运算 `embNum * extEmbSize_ * sizeof(float)` 是否溢出

### 触发条件
当 `embNum * extEmbSize_ * sizeof(float)` 超过 `SIZE_MAX` 时，乘法结果回绕，
导致分配的内存远小于预期，后续内存操作将越界访问。

### 修复建议
```cpp
size_t embSize = static_cast<size_t>(extEmbSize_);
size_t embNumSize = static_cast<size_t>(embNum);
if (embSize > 0 && embNumSize > SIZE_MAX / embSize / sizeof(float)) {
    LOG_ERROR("Memory allocation size overflow");
    throw std::bad_alloc();
}
```
```

#### 不使用 Skill 的报告（宽泛）

- 报告了 47 个问题，其中部分可能存在误报
- 未识别 SDK 入口，直接扫描所有代码
- 缺少规则编号关联
- 问题缺少完整的证据链

### 关键优势

1. **精准定位**：从 SDK 入口出发，只报告外部可达的安全问题
2. **证据完整**：每个问题都有调用路径、代码位置、规则编号
3. **无误报**：严格验证，避免浪费开发者时间
4. **高效**：减少 29% Token 消耗，缩短 25% 审计时间

## 文件结构

```
sdk-security-audit/
├── SKILL.md                    # 主技能定义
├── README.md                   # 本文档
├── evals/
│   └── evals.json              # 测试用例
└── references/
    ├── output-format.md        # 输出报告格式
    ├── remote-repository.md    # 远程仓库处理
    ├── security-issues-cpp.md  # C/C++ 安全规则
    ├── security-issues-design.md # 通用安全设计规范
    └── security-issues-python.md # Python 安全规则
```

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| 1.6.0 | 2026-03-17 | 优化触发描述，精简输出格式，移除重复定义 |
| 1.5.0 | - | 初始版本 |

## 许可证

MIT License
