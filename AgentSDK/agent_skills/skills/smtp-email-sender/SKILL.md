---
name: smtp-email-sender
description: 通过SMTP发送邮件。触发条件：(1) 用户要求"发送邮件"；(2) 用户要求"发邮件到xxx"；(3) 用户要求"把内容发送到邮箱"。支持纯文本和HTML格式，需要用户提供SMTP服务器、端口、邮箱地址和授权码/密码。
---

# SMTP Email Sender

本技能用于通过SMTP协议发送邮件。

## 使用前提

用户需提供：
1. SMTP服务器地址（如 smtp.163.com, smtp.gmail.com）
2. SMTP端口（通常 587 或 465）
3. 邮箱地址
4. 授权码或密码

## 发送流程

### 1. 纯文本邮件

```python
import smtplib
from email.mime.text import MIMEText
from email.header import Header

msg = MIMEText(邮件内容, 'plain', 'utf-8')
msg['Subject'] = Header('邮件主题', 'utf-8')
msg['From'] = 发件人邮箱
msg['To'] = 收件人邮箱

server = smtplib.SMTP_SSL(smtp服务器, smtp端口)
server.login(邮箱, 授权码)
server.sendmail(发件人, [收件人], msg.as_string())
server.quit()
```

### 2. HTML邮件

```python
msg = MIMEText(HTML内容, 'html', 'utf-8')
# 其他同上
```

### 3. Markdown转HTML发送

将Markdown转换为HTML后发送：
- 移除标题符号 (# ## ###)
- 转换加粗 (**text**) → <b>text</b>
- 转换链接 [text](url) → text (url)
- 保持换行

## 常见SMTP配置

| 邮箱 | SMTP服务器 | 端口 | SSL端口 |
|------|-----------|------|---------|
| 163邮箱 | smtp.163.com | 587 | 465 |
| QQ邮箱 | smtp.qq.com | 587 | 465 |
| Gmail | smtp.gmail.com | 587 | 465 |

## 注意事项

- 163/QQ邮箱需使用授权码而非登录密码
- Gmail需开启"低安全性应用访问"或使用应用专用密码
- 发送HTML邮件时确保格式正确
