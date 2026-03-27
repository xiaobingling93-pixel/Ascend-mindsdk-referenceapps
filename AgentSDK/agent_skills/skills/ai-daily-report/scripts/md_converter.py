#!/usr/bin/env python3
"""
AI每日报告转换脚本
将Markdown报告转换为HTML和PDF格式
"""

import os
import re
import sys
import subprocess
import logging
import importlib
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# HTML模板
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.8;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 2px 20px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 40px;
            text-align: center;
        }}
        header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        .meta {{
            font-size: 14px;
            opacity: 0.9;
            margin-top: 15px;
        }}
        .meta span {{
            margin: 0 10px;
        }}
        .content {{
            padding: 40px;
        }}
        h2 {{
            color: #667eea;
            font-size: 22px;
            margin: 35px 0 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
        }}
        h3 {{
            color: #444;
            font-size: 18px;
            margin: 25px 0 15px;
        }}
        h4 {{
            color: #555;
            font-size: 16px;
            margin: 20px 0 10px;
        }}
        .news-item, .paper-item, .tool-item {{
            background: #fafafa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid #667eea;
        }}
        .paper-item {{
            border-left-color: #764ba2;
        }}
        .tool-item {{
            border-left-color: #f093fb;
        }}
        .item-title {{
            font-size: 16px;
            font-weight: 600;
            color: #333;
            margin-bottom: 10px;
        }}
        .item-abstract {{
            font-size: 14px;
            color: #666;
            margin-bottom: 12px;
        }}
        .item-meta {{
            font-size: 12px;
            color: #999;
        }}
        .item-meta a {{
            color: #667eea;
            text-decoration: none;
        }}
        .item-meta a:hover {{
            text-decoration: underline;
        }}
        .summary {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 12px;
            padding: 30px;
            margin-top: 40px;
        }}
        .summary h2 {{
            border-bottom: none;
            margin-bottom: 20px;
        }}
        .trend-item, .concern-item {{
            margin-bottom: 15px;
        }}
        .conclusion {{
            background: #667eea;
            color: #fff;
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
            font-size: 16px;
            text-align: center;
        }}
        .icon {{
            margin-right: 5px;
        }}
        @media print {{
            body {{
                background: #fff;
                padding: 0;
            }}
            .container {{
                box-shadow: none;
                border-radius: 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{title}</h1>
            <div class="meta">
                <span>📅 {date}</span>
                <span>📁 {category}</span>
                <span>📊 {count}条/类</span>
            </div>
        </header>
        <div class="content">
            {body}
        </div>
    </div>
</body>
</html>
'''

def get_title_date_category(md_content):
    """从MD内容中提取标题、日期、领域"""
    # 提取标题
    title_match = re.search(r'^#\s+(.+)$', md_content, re.MULTILINE)
    title = title_match.group(1) if title_match else "AI领域热门速递"
    
    # 提取日期
    date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', md_content)
    if date_match:
        date = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
    else:
        date = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
    
    # 提取领域
    category_match = re.search(r'（(.+?)）', title)
    category = category_match.group(1) if category_match else "全领域"
    
    return title, date, category


def parse_md_content(md_content):
    """解析MD内容，生成HTML片段"""
    html_parts = []
    
    # 分割sections
    sections = re.split(r'^##\s+', md_content, flags=re.MULTILINE)
    
    for section in sections:
        if not section.strip():
            continue
            
        section = section.strip()
        
        # 跳过标题
        if section.startswith('📰') or section.startswith('#'):
            continue
        
        # 表驱动：根据关键词查找对应的解析函数
        parsed = False
        for keyword, parser_func in SECTION_PARSERS.items():
            if keyword in section:
                html_parts.append(parser_func(section))
                parsed = True
                break
        
        # 未匹配到任何类型，使用默认处理
        if not parsed:
            html_parts.append(f"<div>{section}</div>")
    
    return '\n'.join(html_parts)

def parse_news_section(section):
    """解析新闻section"""
    lines = section.split('\n')
    html = ['<h2>📰 热门新闻</h2>']
    
    items = re.split(r'^###\s+\d+\.\s+', section, flags=re.MULTILINE)
    for item in items[1:]:
        if not item.strip():
            continue
        title_match = re.search(r'\[([^\]]+)\]', item)
        title = title_match.group(1) if title_match else '无标题'
        abstract = re.sub(r'^>\\s*', '', item.split('\n')[0])
        abstract = re.sub(r'\[.*?\]\(.*?\)', '', abstract).strip()
        
        link_match = re.search(r'\[.*?\]\((.*?)\)', item)
        link = link_match.group(1) if link_match else '#'
        
        date_match = re.search(r'📅\s*(\d{4}-\d{2}-\d{2})', item)
        date = date_match.group(1) if date_match else ''
        
        html.append(f'''<div class="news-item">
            <div class="item-title">{title}</div>
            <div class="item-abstract">{abstract}</div>
            <div class="item-meta">📅 {date} | <a href="{link}" target="_blank">查看原文</a></div>
        </div>''')
    
    return '\n'.join(html)

def parse_paper_section(section):
    """解析论文section"""
    html = ['<h2>📄 热门论文</h2>']
    
    items = re.split(r'^###\s+\d+\.\s+', section, flags=re.MULTILINE)
    for item in items[1:]:
        if not item.strip():
            continue
        title_match = re.search(r'\[([^\]]+)\]', item)
        title = title_match.group(1) if title_match else '无标题'
        
        link_match = re.search(r'\[.*?\]\((.*?)\)', item)
        link = link_match.group(1) if link_match else '#'
        
        arxiv_match = re.search(r'arXiv[:\s]*([\w\.-]+)', item, re.IGNORECASE)
        arxiv_id = arxiv_match.group(1) if arxiv_match else ''
        
        html.append(f'''<div class="paper-item">
            <div class="item-title">{title}</div>
            <div class="item-meta">📄 arXiv: {arxiv_id} | <a href="{link}" target="_blank">查看论文</a></div>
        </div>''')
    
    return '\n'.join(html)

def parse_tool_section(section):
    """解析工具section"""
    html = ['<h2>🛠️ 热门技术/工具</h2>']
    
    items = re.split(r'^###\s+\d+\.\s+', section, flags=re.MULTILINE)
    for item in items[1:]:
        if not item.strip():
            continue
        title_match = re.search(r'\[([^\]]+)\]', item)
        title = title_match.group(1) if title_match else '无标题'
        
        link_match = re.search(r'\[.*?\]\((.*?)\)', item)
        link = link_match.group(1) if link_match else '#'
        
        html.append(f'''<div class="tool-item">
            <div class="item-title">{title}</div>
            <div class="item-meta"><a href="{link}" target="_blank">查看项目</a></div>
        </div>''')
    
    return '\n'.join(html)

def parse_summary_section(section):
    """解析总结section"""
    html = ['<div class="summary"><h2>📊 总体总结</h2>']
    
    # 核心趋势
    trends = re.findall(r'^\d+\.\s+(.+)$', section, re.MULTILINE)
    if trends:
        html.append('<div class="trend-item"><h3>核心趋势</h3><ul>')
        for trend in trends:
            html.append(f'<li>{trend}</li>')
        html.append('</ul></div>')
    
    # 需要关注的问题
    concerns = re.findall(r'^[-*]\s+(.+)$', section, re.MULTILINE)
    if concerns:
        html.append('<div class="concern-item"><h3>需要关注的问题</h3><ul>')
        for concern in concerns:
            html.append(f'<li>{concern}</li>')
        html.append('</ul></div>')
    
    # 一句话总结
    conclusion_match = re.search(r'一句话总结[：:]\s*(.+)$', section, re.MULTILINE)
    if conclusion_match:
        html.append(f'<div class="conclusion">{conclusion_match.group(1)}</div>')
    
    html.append('</div>')
    return '\n'.join(html)

SECTION_PARSERS = {
    '热门新闻': parse_news_section,
    '热门论文': parse_paper_section,
    '热门技术': parse_tool_section,
    '总体总结': parse_summary_section,
}

def convert_md_to_html(md_content):
    """将Markdown转换为美观的HTML"""
    title, date, category = get_title_date_category(md_content)
    body = parse_md_content(md_content)
    
    # 统计条数
    count = len(re.findall(r'^###\s+\d+\.', md_content, re.MULTILINE))
    
    return HTML_TEMPLATE.format(
        title=title,
        date=date,
        category=category,
        count=count,
        body=body
    )

# Python库依赖列表（按优先级）
PDF_DEPS = [
    {'name': 'weasyprint', 'install_cmd': 'pip install weasyprint', 'priority': 1},  # 推荐，效果最好
    {'name': 'pdfkit', 'install_cmd': 'pip install pdfkit', 'priority': 2},
    {'name': 'xhtml2pdf', 'install_cmd': 'pip install xhtml2pdf', 'priority': 3},
    {'name': 'fpdf2', 'install_cmd': 'pip install fpdf2', 'priority': 4},  # 纯Python但样式简化
]

def get_pip_cmd():
    """获取pip命令"""
    for cmd in ['pip3', 'pip', 'python3 -m pip', 'python -m pip']:
        try:
            result = subprocess.run(
                cmd.split() + ['--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return cmd
        except Exception as e:
            logger.info(f"尝试pip命令 '{cmd}' 失败: {e}")
            continue
    return None

def ensure_dependencies():
    """确保PDF转换依赖已安装，自动下载缺失的库"""
    available_libs = []
    pip_cmd = get_pip_cmd()
    
    # 检查已安装的库
    for dep in PDF_DEPS:
        try:
            importlib.import_module(dep['name'].replace('-', '_'))
            available_libs.append(dep)
        except ImportError:
            logger.info(f"⚠ {dep['name']} 未安装")
    
    # 如果有可用库，直接返回
    if available_libs:
        return sorted(available_libs, key=lambda x: x['priority'])
    
    # 没有可用库，尝试自动安装
    if not pip_cmd:
        logger.warning("⚠ 未找到pip，无法自动安装PDF库")
        return []
    
    logger.info("📦 正在自动安装PDF转换库...")
    installed = []
    for dep in PDF_DEPS:
        logger.info(f"   尝试安装 {dep['name']}...")
        try:
            result = subprocess.run(
                f"{pip_cmd} install {dep['name']}".split(),
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                logger.info(f"   ✅ {dep['name']} 安装成功")
                installed.append(dep)
                break  # 安装成功一个就退出
            else:
                logger.warning(f"   ⚠ {dep['name']} 安装失败")
        except Exception as e:
            logger.error(f"   ⚠ {dep['name']} 安装失败: {e}")
            continue
    
    return sorted(installed, key=lambda x: x['priority'])

def convert_md_to_pdf(html_content, output_path):
    """将HTML转换为PDF（自动安装依赖）"""
    # 确保依赖已安装
    available_libs = ensure_dependencies()
    
    if not available_libs:
        # 提示用户使用浏览器打印
        html_path = output_path.replace('.pdf', '.html')
        return False, f"请手动安装PDF库: pip install weasyprint\n或使用浏览器打开 {html_path} 然后 Ctrl+P 另存为PDF"
    
    weasyprint_name = 'weasyprint'
    pdfkit_name = 'pdfkit'
    xhtml2pdf_name = 'xhtml2pdf'
    fpdf2_name = 'fpdf2'
    name_key = 'name'
    # 方法1: weasyprint (效果最好)
    for dep in available_libs:
        try:
            if dep[name_key] == weasyprint_name:
                from weasyprint import HTML
                HTML(string=html_content).write_pdf(output_path)
                return True, output_path
            elif dep[name_key] == pdfkit_name:
                import pdfkit
                pdfkit.from_string(html_content, output_path)
                return True, output_path
            elif dep[name_key] == xhtml2pdf_name:
                from xhtml2pdf import pml
                pml.PMLProcessor().process_buffer(html_content.encode(), output_path)
                return True, output_path
            elif dep[name_key] == fpdf2_name:
                from fpdf import FPDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                
                # 简单提取文本（去除HTML标签）
                text = re.sub(r'<[^>]+>', '', html_content)
                text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
                
                for line in text.split('\n'):
                    if line.strip():
                        pdf.cell(0, 10, line.encode('latin-1', 'replace').decode('latin-1'), ln=True)
                
                pdf.output(output_path)
                return True, output_path
        except Exception as e:
            logger.error(f"⚠ {dep[name_key]} 转换失败: {e}")
            continue
    
    # 兜底：浏览器打印
    html_path = output_path.replace('.pdf', '.html')
    return False, f"请使用浏览器打开 {html_path} 然后 Ctrl+P 另存为PDF"

def main():
    """主函数"""
    if len(sys.argv) < 2:
        logger.info("Usage: python md_converter.py <input.md> [output_dir]")
        logger.info("Example: python md_converter.py AI-报告-LLM-2026-03-18.md")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(input_file))
    
    if not os.path.exists(input_file):
        logger.error(f"Error: File not found: {input_file}")
        sys.exit(1)
    
    # 读取MD内容
    with open(input_file, 'r', os.O_WRONLY, encoding='utf-8') as f:
        md_content = f.read()
    
    # 获取基础文件名
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    
    # 转换为HTML
    html_content = convert_md_to_html(md_content)
    html_path = os.path.join(output_dir, f"{base_name}.html")
    with open(html_path, 'w', os.O_WRONLY,encoding='utf-8') as f:
        f.write(html_content)
    logger.info(f"✓ HTML generated: {html_path}")
    
    # 转换为PDF
    pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
    success, msg = convert_md_to_pdf(html_content, pdf_path)
    if success:
        logger.info(f"✓ PDF generated: {pdf_path}")
    else:
        logger.warning(f"⚠ PDF generation failed: {msg}")
    
    logger.info(f"\nDone! Output files:")
    logger.info(f"  - {input_file}")
    logger.info(f"  - {html_path}")
    if success:
        logger.info(f"  - {pdf_path}")

if __name__ == '__main__':
    main()
