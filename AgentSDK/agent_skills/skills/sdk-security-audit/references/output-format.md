# 审计报告输出格式

本文档定义 SDK 安全审计报告的标准输出格式。

## 报告结构

### 1. 审计摘要

```markdown
## 审计摘要

- **审计范围**：[扫描的模块/文件]
- **编程语言**：[C++/Python/混合]
- **SDK 入口数**：[已识别的入口数量]
- **发现问题数**：[按严重度统计：Critical/High/Medium/Low]
```

### 2. SDK 入口识别

以表格形式输出：

| 入口函数 | 文件位置 | 识别依据 | 风险等级 |
|---------|---------|---------|---------|
| 函数名 | 完整路径:行号 | 导出符号/头文件/命名规范 | 高/中/低 |

### 3. 问题详情

每个问题使用以下精简格式：

```markdown
## [风险等级] 问题标题

**违规规则**：规则编号及名称（如 1.1.3 内存拷贝前必须校验目标缓冲区大小）
**入口函数**：`SDK_ProcessData` (src/sdk/api.cpp:123)
**风险位置**：src/core/buffer.cpp:456
**外部可达性**：externally_reachable / conditionally_reachable / internal_only

### 证据链
- **调用路径**：SDK_ProcessData → ProcessBuffer → memcpy
- **输入传播**：用户参数 `size` 直接传入 `memcpy(dest, src, size)`
- **缺失检查**：未验证 `size <= MAX_BUFFER_SIZE`

### 触发条件
用户传入 `size > MAX_BUFFER_SIZE` 时触发缓冲区溢出。

### 修复建议
添加 size 上限检查：
```cpp
if (size > MAX_BUFFER_SIZE) {
    return ERROR_INVALID_SIZE;
}
```
```

### 4. 未覆盖范围

明确指出审计过程中未覆盖的范围：

- **宏展开限制**：复杂宏导致的分析限制
- **条件编译**：不同编译条件下的代码路径
- **未审计模块**：未包含在审计范围内的模块

---

## 问题报告示例

```markdown
## [HIGH] 缓冲区溢出风险 - memcpy 未检查目标缓冲区大小

**违规规则**：1.1.3 内存拷贝前必须校验目标缓冲区大小
**入口函数**：`SDK_ProcessData` (src/sdk/api.cpp:123)
**风险位置**：src/core/buffer.cpp:456
**外部可达性**：externally_reachable

### 证据链
- **调用路径**：SDK_ProcessData → ProcessBuffer → memcpy
- **输入传播**：用户参数 `size` 直接传入 `memcpy(dest, src, size)`
- **缺失检查**：仅检查 `size > 0`，未验证 `size <= MAX_BUFFER_SIZE`

### 触发条件
用户传入 `size > MAX_BUFFER_SIZE` 时触发缓冲区溢出。

### 修复建议
```cpp
if (size > MAX_BUFFER_SIZE) {
    return ERROR_INVALID_SIZE;
}
```
```

---

## 未发现漏洞时的输出

如果未发现高置信度漏洞，输出：

```markdown
## 审计结论

**未发现高置信度安全问题**

### 已审计范围
- [列出已扫描的模块和文件]

### 已检查规则
- [列出已检查的规则类型]

### 建议关注点
- [列出可能需要人工复核的薄弱点]
```

---

## 风险等级定义

| 等级 | 条件 | 影响 |
|------|------|------|
| **Critical** | 外部可达 | RCE、任意代码执行、严重权限绕过 |
| **High** | 外部可达 | 越界读写、信息泄露、SQL/命令注入 |
| **Medium** | 条件可达 | DoS、资源泄漏、错误处理失配 |
| **Low** | 内部风险 | 安全边界弱化、编码缺陷 |
