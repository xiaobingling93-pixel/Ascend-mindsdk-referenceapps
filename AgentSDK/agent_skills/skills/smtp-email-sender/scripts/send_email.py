#!/usr/bin/env python3
"""
SMTP邮件发送脚本
用法: python3 send_email.py --to target@email.com --subject "主题" --body "内容" [--html] [--smtp smtp.163.com] [--port 465] [--from your@email.com] [--pass your_password]
"""

import smtplib
import argparse
import logging
from email.mime.text import MIMEText
from email.header import Header
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)




def send_email(to_email, content, smtp_config=None, sender_config=None):
    """发送邮件
    
    参数:
        to_email: 收件人邮箱
        content: 邮件内容配置字典，包含 subject, body, html(可选)
        smtp_config: SMTP服务器配置字典，包含 smtp_server, smtp_port(可选)
        sender_config: 发件人配置字典，包含 from_email, password(可选)
    """
    
    # 默认值处理
    subject = content.get('subject', '')
    body = content.get('body', '')
    html = content.get('html', False)
    
    smtp_server = smtp_config.get('smtp_server', 'smtp.163.com') if smtp_config else 'smtp.163.com'
    smtp_port = smtp_config.get('smtp_port', 465) if smtp_config else 465
    
    from_email = sender_config.get('from_email') if sender_config else None
    password = sender_config.get('password') if sender_config else None
    
    if not from_email:
        from_email = input("请输入发件人邮箱: ")
    if not password:
        import getpass
        password = getpass.getpass("请输入授权码/密码: ")
    
    msg = MIMEText(body, 'html' if html else 'plain', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = from_email
    msg['To'] = to_email
    
    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        
        server.login(from_email, password)
        server.sendmail(from_email, [to_email], msg.as_string())
        server.quit()
        logger.info(f"✅ 邮件发送成功！")
        logger.info(f"   收件人: {to_email}")
        logger.info(f"   主题: {subject}")
        return True
    except Exception as e:
        logger.error(f"❌ 发送失败: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='SMTP邮件发送工具')
    parser.add_argument('--to', required=True, help='收件人邮箱')
    parser.add_argument('--subject', required=True, help='邮件主题')
    parser.add_argument('--body', required=True, help='邮件内容')
    parser.add_argument('--html', action='store_true', help='使用HTML格式')
    parser.add_argument('--smtp', default='smtp.163.com', help='SMTP服务器')
    parser.add_argument('--port', type=int, default=465, help='SMTP端口')
    parser.add_argument('--from', dest='from_email', help='发件人邮箱')
    parser.add_argument('--pass', dest='password', help='授权码/密码')
    
    args = parser.parse_args()
    
    # 准备参数
    content = {
        'subject': args.subject,
        'body': args.body,
        'html': args.html
    }
    
    smtp_config = {
        'smtp_server': args.smtp,
        'smtp_port': args.port
    }
    
    sender_config = {
        'from_email': args.from_email,
        'password': args.password
    }
    
    send_email(
        to_email=args.to,
        content=content,
        smtp_config=smtp_config,
        sender_config=sender_config
    )

if __name__ == '__main__':
    main()
