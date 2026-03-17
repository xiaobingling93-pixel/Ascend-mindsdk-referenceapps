import pandas as pd
import re
import os
import sys
import logging
from datetime import datetime, timezone
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 120 * 1024

TAG_MAPPING = {
    '[Doc]': '文档问题',
    '[Installation]': '安装问题',
    '[Usage]': '使用问题',
    '[Bug]': '程序Bug',
    '[Performance]': '性能提案',
    '[Feature]': '新功能提案',
    '[RFC]': '架构调整反馈',
    '[Roadmap]': '项目规划',
    'CVE': '漏洞问题'
}


def get_category(title):
    if not title:
        return '其他问题'

    for tag, category in TAG_MAPPING.items():
        if title.startswith(tag) or tag in title:
            return category

    if title.startswith('CVE'):
        return '漏洞问题'

    return '其他问题'


def format_datetime(dt_str):
    if not dt_str:
        return ''
    try:
        dt = datetime.fromisoformat(dt_str.replace('+08:00', '+08:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return dt_str


def escape_markdown_title(title):
    title = title.replace('[', '\\[').replace(']', '\\]')
    return title


def format_comment_text(text):
    if not text:
        return ''

    text = text.strip()

    code_block_pattern = r'```[\s\S]*?```'
    code_blocks = re.findall(code_block_pattern, text)
    for i, block in enumerate(code_blocks):
        text = text.replace(block, f'__CODE_BLOCK_{i}__')

    inline_code_pattern = r'`[^`]+`'
    inline_codes = re.findall(inline_code_pattern, text)
    for i, code in enumerate(inline_codes):
        text = text.replace(code, f'__INLINE_CODE_{i}__')

    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'![\1](\2)', text)

    text = re.sub(r'(?<!!)(?<![\[\(])\[([^\]]+)\]\(([^)]+)\)', r'[\1](\2)', text)

    url_pattern = r'(?<!!)(?<![\]\(])https?://[^\s<>"{}|\\^`\[\]]+'
    text = re.sub(url_pattern, lambda m: f'[{m.group(0)}]({m.group(0)})', text)

    command_patterns = [
        (r'(?<![/\w`])(mkdir\s+-m\s+\d+\s+[^\n,，。]+?)(?=\s*(?:\n|,|，|。|$))', r'`\1`'),
        (r'(?<![/\w`])(mkdir\s+[^\n,，。]+?)(?=\s*(?:\n|,|，|。|$))', r'`\1`'),
        (r'(?<![/\w`])(chown\s+[^\n,，。]+?)(?=\s*(?:\n|,|，|。|$))', r'`\1`'),
        (r'(?<![/\w`])(chmod\s+[^\n,，。]+?)(?=\s*(?:\n|,|，|。|$))', r'`\1`'),
        (r'(?<![/\w`])(kubectl\s+[^\n,，。]+?)(?=\s*(?:\n|,|，|。|$))', r'`\1`'),
        (r'(?<![/\w`])(docker\s+[^\n,，。]+?)(?=\s*(?:\n|,|，|。|$))', r'`\1`'),
        (r'(?<![/\w`])(/label\s+add\s+\w+)', r'`\1`'),
    ]

    for pattern, replacement in command_patterns:
        text = re.sub(pattern, replacement, text)

    for i, code in enumerate(inline_codes):
        text = text.replace(f'__INLINE_CODE_{i}__', code)

    for i, block in enumerate(code_blocks):
        text = text.replace(f'__CODE_BLOCK_{i}__', block)

    text = text.replace('\n', '  \n')

    return text


def parse_all_existing_md(references_dir):
    existing_issues = set()

    if not os.path.exists(references_dir):
        return existing_issues

    for filename in os.listdir(references_dir):
        if filename.startswith('issue_comments_analysis') and filename.endswith('.md'):
            filepath = os.path.join(references_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            issue_pattern = r'\| Issue ID \| `(\d+)` \|'
            matches = re.findall(issue_pattern, content)
            existing_issues.update(matches)

    return existing_issues


def get_next_file_index(references_dir):
    max_index = 0
    if not os.path.exists(references_dir):
        return 0

    for filename in os.listdir(references_dir):
        if filename.startswith('issue_comments_analysis') and filename.endswith('.md'):
            match = re.search(r'issue_comments_analysis_(\d+)\.md', filename)
            if match:
                index = int(match.group(1))
                max_index = max(max_index, index)
            elif filename == 'issue_comments_analysis.md':
                max_index = max(max_index, 0)

    return max_index


def get_output_filename(references_dir, index):
    if index == 0:
        return os.path.join(references_dir, 'issue_comments_analysis.md')
    else:
        return os.path.join(references_dir, f'issue_comments_analysis_{index}.md')


def write_header(f, xlsx_file, file_index, total_files):
    f.write("# Issue 评论分析报告\n\n")
    if total_files > 1:
        f.write(f"**文档分片**: 第 {file_index + 1}/{total_files} 部分\n\n")
    f.write(f"**生成时间**: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n")
    f.write(f"**数据来源**: {os.path.basename(xlsx_file)}\n\n")
    f.write("---\n\n")


def write_toc(f, issue_groups, file_index=0, total_files=1):
    if total_files > 1 and file_index > 0:
        f.write("## 📋 导航\n\n")
        nav_links = []
        for i in range(total_files):
            if i == 0:
                nav_links.append(f"[主文档](issue_comments_analysis.md)")
            else:
                nav_links.append(f"[第{i + 1}部分](issue_comments_analysis_{i}.md)")
        f.write(" | ".join(nav_links) + "\n\n")
        f.write("---\n\n")

    f.write("## 📋 目录\n\n")
    for category in sorted(issue_groups.keys()):
        count = len(issue_groups[category])
        anchor = re.sub(r'[^\w\u4e00-\u9fff-]', '', category).lower()
        f.write(f"- [{category}](#{anchor}) ({count}个Issue)\n")
    f.write("\n---\n\n")


def write_issue(f, idx, issue_id, comments):
    first_comment = comments[0]
    issue_title = first_comment['issue_title']
    safe_title = escape_markdown_title(issue_title)

    f.write(f"### {idx}. {safe_title}\n\n")
    f.write(f"| 属性 | 值 |\n")
    f.write(f"|:-----|:---|\n")
    f.write(f"| Issue ID | `{issue_id}` |\n")
    f.write(f"| 首次评论时间 | {format_datetime(first_comment['created_at'])} |\n")
    f.write(f"| 评论数量 | {len(comments)} |\n\n")

    f.write("**💬 评论汇总**:\n\n")
    for i, comment in enumerate(comments, 1):
        comment_text = format_comment_text(str(comment['comment']))
        if comment_text:
            f.write(f"{i}. {comment_text}\n")
    f.write("\n---\n\n")


def write_statistics(f, issue_groups):
    f.write("## 📊 统计信息\n\n")
    f.write("| 分类 | Issue数量 |\n")
    f.write("|:-----|:----------|\n")
    total = 0
    for category in sorted(issue_groups.keys()):
        count = len(issue_groups[category])
        total += count
        f.write(f"| {category} | {count} |\n")
    f.write(f"\n**总计**: {total} 个Issue\n")


def main():
    if len(sys.argv) < 2:
        logger.error("Missing xlsx file path parameter")
        logger.info("Usage: python classify_issue_comments.py <xlsx_file>")
        logger.info("Example: python classify_issue_comments.py mind-cluster_issue_comments.xlsx")
        return 1

    xlsx_file = sys.argv[1]

    if not os.path.exists(xlsx_file):
        logger.error(f"File {xlsx_file} does not exist")
        return 1

    logger.info(f"Reading {xlsx_file}...")
    df = pd.read_excel(xlsx_file)
    logger.info(f"Successfully read {len(df)} comment records")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    references_dir = os.path.join(os.path.dirname(script_dir), '..', 'references')
    os.makedirs(references_dir, exist_ok=True)

    existing_issues = parse_all_existing_md(references_dir)
    logger.info(f"Successfully parsed {len(existing_issues)} issue IDs from existing markdown files")

    grouped = defaultdict(list)
    for _, row in df.iterrows():
        issue_id = str(row.get('Issue ID', ''))
        issue_title = row.get('Issue标题', '')
        category = get_category(issue_title)

        grouped[category].append({
            'issue_id': issue_id,
            'issue_title': issue_title,
            'comment': row.get('评论内容', ''),
            'created_at': row.get('创建时间', '')
        })

    issue_groups = defaultdict(lambda: defaultdict(list))
    for category, comments in grouped.items():
        for comment in comments:
            issue_id = comment['issue_id']
            issue_groups[category][issue_id].append(comment)

    new_issue_count = 0
    for _, issues in issue_groups.items():
        for issue_id in issues:
            if issue_id not in existing_issues:
                new_issue_count += 1

    logger.info(f"Successfully found {new_issue_count} new Issues")

    if new_issue_count == 0 and existing_issues:
        logger.info("No new Issues need to be added")
        return 0

    all_issues_list = []
    for category in sorted(issue_groups.keys()):
        for issue_id, comments in sorted(issue_groups[category].items()):
            all_issues_list.append({
                'category': category,
                'issue_id': issue_id,
                'comments': comments
            })

    logger.info(f"Successfully classified {len(all_issues_list)} Issues")

    output_files = []
    current_file_index = get_next_file_index(references_dir)
    current_file_path = get_output_filename(references_dir, current_file_index)
    current_file = open(current_file_path, 'w', encoding='utf-8')
    output_files.append(current_file_path)

    write_header(current_file, xlsx_file, current_file_index, 1)
    write_toc(current_file, issue_groups)

    issue_counter = 0
    current_category = None

    for issue_data in all_issues_list:
        category = issue_data['category']
        issue_id = issue_data['issue_id']
        comments = issue_data['comments']

        if category != current_category:
            current_category = category
            anchor = re.sub(r'[^\w\u4e00-\u9fff-]', '', category).lower()
            category_header = f"## {category}\n\n> 共 **{len(issue_groups[category])}** 个Issue\n\n"
            current_file.write(category_header)

        issue_counter += 1

        issue_content = ""
        issue_content_lines = []

        first_comment = comments[0]
        issue_title = first_comment['issue_title']
        safe_title = escape_markdown_title(issue_title)

        issue_content_lines.append(f"### {issue_counter}. {safe_title}\n\n")
        issue_content_lines.append(f"| 属性 | 值 |\n")
        issue_content_lines.append(f"|:-----|:---|\n")
        issue_content_lines.append(f"| Issue ID | `{issue_id}` |\n")
        issue_content_lines.append(f"| 首次评论时间 | {format_datetime(first_comment['created_at'])} |\n")
        issue_content_lines.append(f"| 评论数量 | {len(comments)} |\n\n")
        issue_content_lines.append("**💬 评论汇总**:\n\n")

        for i, comment in enumerate(comments, 1):
            comment_text = format_comment_text(str(comment['comment']))
            if comment_text:
                issue_content_lines.append(f"{i}. {comment_text}\n")
        issue_content_lines.append("\n---\n\n")

        issue_content = ''.join(issue_content_lines)

        current_file.flush()
        current_size = current_file.tell()

        if current_size + len(issue_content.encode('utf-8')) > MAX_FILE_SIZE:
            write_statistics(current_file, issue_groups)
            current_file.close()

            current_file_index += 1
            current_file_path = get_output_filename(references_dir, current_file_index)
            current_file = open(current_file_path, 'w', encoding='utf-8')
            output_files.append(current_file_path)

            logger.info(f"Successfully created new file: {os.path.basename(current_file_path)}")

            write_header(current_file, xlsx_file, current_file_index, current_file_index + 1)
            write_toc(current_file, issue_groups, current_file_index, current_file_index + 1)

            if category != current_category:
                current_category = category
                anchor = re.sub(r'[^\w\u4e00-\u9fff-]', '', category).lower()
                category_header = f"## {category}\n\n> 共 **{len(issue_groups[category])}** 个Issue\n\n"
                current_file.write(category_header)

        current_file.write(issue_content)

    write_statistics(current_file, issue_groups)
    current_file.close()

    total_files = len(output_files)
    if total_files > 1:
        for i, filepath in enumerate(output_files):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            content = re.sub(
                r'\*\*文档分片\*\*: 第 \d+/\d+ 部分',
                f'**文档分片**: 第 {i + 1}/{total_files} 部分',
                content
            )

            nav_section = "## 📋 导航\n\n"
            nav_links = []
            for j in range(total_files):
                if j == 0:
                    nav_links.append(f"[主文档](issue_comments_analysis.md)")
                else:
                    nav_links.append(f"[第{j + 1}部分](issue_comments_analysis_{j}.md)")
            nav_section += " | ".join(nav_links) + "\n\n---\n\n"

            content = re.sub(r'---\n\n## 📋 目录', nav_section + "## 📋 目录", content)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

    logger.info(f"Successfully classified {len(all_issues_list)} Issues into {total_files} files")
    logger.info("Generated files:")
    for filepath in output_files:
        size = os.path.getsize(filepath)
        logger.info(f"  - {os.path.basename(filepath)} ({size / 1024:.1f} KB)")
    logger.info("Statistics:")
    total = 0
    for category in sorted(issue_groups.keys()):
        count = len(issue_groups[category])
        total += count
        logger.info(f"  - {category}: {count} Issues")
    logger.info(f"  Total: {total} Issues")

    return 0


if __name__ == "__main__":
    sys.exit(main())
