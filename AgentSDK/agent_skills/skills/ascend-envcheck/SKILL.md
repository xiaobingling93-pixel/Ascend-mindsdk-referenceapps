---
name: ascend-envcheck
description: 执行 K8s Master 节点的 envCheck.sh 环境检测脚本。当用户询问"集群状态"、"K8s集群状态"、"环境检测"、"Ascend环境检查"、"任务为什么没调度起来"、"任务为什么pendding"、"NPU状态"或要求执行集群状态检测时使用。需要用户提供 master 节点 IP、用户名，以及密码或 SSH 密钥路径其中之一。
---

# Ascend 环境检测

## 触发条件

当用户提出以下需求时激活此 skill：
- 询问集群状态 / K8s 集群状态
- 执行环境检测 / Ascend 环境检查
- 检查 NPU 设备状态
- 验证节点标签配置

## 重要前提/约束
- `envCheck.sh` 依赖 `kubectl`（这些依赖在**脚本实际运行的那台机器上**必须存在，部分检测内容依赖jq工具，非强制，如需要jq工具但没有时，可以提示用户安装）
- 不支持在windows系统上执行。
- 不要在返回内容里泄露用户的密码/私钥内容；日志里需要对敏感字段做脱敏。

## 必需信息

执行前必须向用户获取：
- **Master IP**: K8s master 节点的 IP 地址
- **用户名**: SSH 登录用户名（通常为 root）
- **认证方式**（二选一）:
  - **密码**: SSH 登录密码
  - **密钥路径**: SSH 私钥文件路径（如 `~/.ssh/id_rsa`）

## 连接方式

### 方式一：密码认证

```
检查集群状态，IP 192.168.9.143，用户 root，密码 ***
```

### 方式二：SSH 密钥认证

```
检查集群状态，IP 192.168.9.143，用户 root，密钥 ~/.ssh/id_rsa
```

密钥方式无需提供密码，适合已配置 SSH 密钥登录的环境。

## 执行方式

1. 通过 SSH 连接到 master 节点（密码或密钥）
2. 上传 `scripts/envCheck.sh` 到目标主机 `/tmp/` 目录，并在文件名后增加当前时间，如 `/tmp/envCheck_20260316_174737.sh`
3. 执行脚本并输出执行结果（不做任何修改或摘要）
4. 对结果进行摘要、解释和格式化，预测下一步可能需要的操作
5. 执行结束后，删除目标主机上上传的临时脚本(保证只安全删除对应脚本，不得删除其他文件)

## 脚本参数

`envCheck.sh` 支持以下参数：

```
用法: ./envCheck.sh [期望NPU卡数量] [产品类型] [-r|--resources]
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 期望NPU卡数量 | 预期的 NPU 卡数量 | 16 |
| 产品类型 | 产品配置类型 | none |
| -r, --resources | 启用内存和 CPU 资源检查 | 关闭 |

### 可选产品类型

| 类型 | 说明 |
|------|------|
| none | 不检测标签（默认） |
| full-910 | Atlas 800 训练服务器（NPU满配） |
| half-910 | Atlas 800 训练服务器（NPU半配） |
| a2-pod | Atlas 800T A2 / Atlas 900 A2 PoD |
| a3-superpod | Atlas 900 A3 SuperPoD 超节点 |
| a3-box8 | A200T A3 Box8 超节点服务器 |
| a2-infer | Atlas 800I A2 推理服务器 |
| a2-box | A200I A2 Box 异构组件 |
| a2-box16 | Atlas 200T A2 Box16 异构子框 |
| train-card | 训练服务器（Atlas 300T 训练卡） |
| infer-card | 推理服务器（Atlas 300I 推理卡） |
| infer-series | Atlas 推理系列产品 |
| soc-core | Atlas 200I SoC A1 核心板 |

## 执行示例

**密码认证：**
```
检查集群状态，IP 192.168.9.143，用户 root，密码 ***
```

**密钥认证：**
```
检查集群状态，IP 192.168.9.143，用户 root，密钥 ~/.ssh/id_rsa
```

**带脚本参数：**
```
检查集群状态，8卡 half-910 配置，检查资源
```

## 输出要求

**先直接原样输出 envCheck.sh 的执行结果**，包括：
- 所有检测项的输出
- 错误信息（如有）
- 最终检测结果

再对输出做摘要、解释或格式化，以及下一步可能需要的操作。

## 技术实现

### 密码认证方式

```bash
# 1. 上传脚本
sshpass -p '<password>' scp -o StrictHostKeyChecking=no \
  scripts/envCheck.sh <user>@<ip>:/tmp/envCheck.sh

# 2. 执行脚本
sshpass -p '<password>' ssh -o StrictHostKeyChecking=no \
  <user>@<ip> "chmod +x /tmp/envCheck.sh && bash /tmp/envCheck.sh <args>"
```

### SSH 密钥认证方式

```bash
# 1. 上传脚本
scp -o StrictHostKeyChecking=no -i <key_path> \
  scripts/envCheck.sh <user>@<ip>:/tmp/envCheck.sh

# 2. 执行脚本
ssh -o StrictHostKeyChecking=no -i <key_path> \
  <user>@<ip> "chmod +x /tmp/envCheck.sh && bash /tmp/envCheck.sh <args>"
```

## 依赖

- 本地:
  - `sshpass` (密码认证时需要)
  - `ssh`/`scp` (密钥认证时使用)
- 远程: `kubectl`, `jq` (可选，如无 jq 部分检测项会降级)

## Resources

### scripts/
- `envCheck.sh` - 主检测脚本，检查 K8s 集群、NPU 设备、节点标签、资源状态等
