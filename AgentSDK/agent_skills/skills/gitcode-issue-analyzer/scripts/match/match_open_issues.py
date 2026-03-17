import pandas as pd
import re
import os
import sys
import logging
from datetime import datetime, timezone
from collections import defaultdict
from difflib import SequenceMatcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.8

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


def should_skip(title):
    if not title:
        return False
    return '[Roadmap]' in title


def normalize_title(title):
    if not title:
        return ''
    title = re.sub(r'\[.*?\]', '', title)
    title = re.sub(r'[^\w\u4e00-\u9fff]', '', title)
    return title.lower().strip()


def calculate_similarity(title1, title2):
    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)

    if not norm1 or not norm2:
        return 0

    return SequenceMatcher(None, norm1, norm2).ratio()


def escape_markdown(text):
    if not text:
        return ''
    text = text.replace('[', '\\[').replace(']', '\\]')
    return text


def format_datetime(dt_str):
    if not dt_str:
        return ''
    try:
        dt = datetime.fromisoformat(dt_str.replace('+08:00', '+08:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return dt_str


def parse_reference_md(md_file):
    issues_data = []

    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()

    issue_blocks = re.split(r'### \d+\.', content)

    for block in issue_blocks[1:]:
        issue_data = {}

        issue_id_match = re.search(r'\| Issue ID \| `(\d+)` \|', block)
        if issue_id_match:
            issue_data['issue_id'] = issue_id_match.group(1)

        lines = block.strip().split('\n')
        if lines:
            title_line = lines[0].strip()
            title_line = title_line.replace('\\[', '[').replace('\\]', ']')
            issue_data['title'] = title_line

        comments_match = re.search(r'\*\*💬 评论汇总\*\*:\n\n(.*?)(?=\n---|\n## |$)', block, re.DOTALL)
        if comments_match:
            comments_text = comments_match.group(1)
            comments = []
            for line in comments_text.split('\n'):
                line = line.strip()
                if re.match(r'^\d+\.', line):
                    comment = re.sub(r'^\d+\.\s*', '', line)
                    if comment:
                        comments.append(comment)
            issue_data['comments'] = comments

        if issue_data.get('issue_id') and issue_data.get('title'):
            issues_data.append(issue_data)

    return issues_data


def load_all_references(references_dir):
    all_issues = []

    if not os.path.exists(references_dir):
        return all_issues

    for filename in os.listdir(references_dir):
        if filename.startswith('issue_comments_analysis') and filename.endswith('.md'):
            filepath = os.path.join(references_dir, filename)
            issues = parse_reference_md(filepath)
            for issue in issues:
                issue['source_file'] = filename
            all_issues.extend(issues)

    return all_issues


def find_best_match(open_issue_title, reference_issues):
    best_match = None
    best_similarity = 0

    for ref_issue in reference_issues:
        ref_title = ref_issue.get('title', '')
        similarity = calculate_similarity(open_issue_title, ref_title)

        if similarity >= SIMILARITY_THRESHOLD and similarity > best_similarity:
            best_similarity = similarity
            best_match = ref_issue
            best_match['similarity'] = similarity

    return best_match


def main():
    if len(sys.argv) < 2:
        logger.error("Missing xlsx file path parameter")
        logger.info("Usage: python match_open_issues.py <xlsx_file>")
        logger.info("Example: python match_open_issues.py mind-cluster_open_issue.xlsx")
        return 1

    xlsx_file = sys.argv[1]

    if not os.path.exists(xlsx_file):
        logger.error(f"File {xlsx_file} not exists")
        return 1

    logger.info(f"Ready to read {xlsx_file}...")
    df = pd.read_excel(xlsx_file)
    logger.info(f"Read {len(df)} a record of an opened Issue")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    skill_dir = os.path.join(os.path.dirname(script_dir), '..')
    references_dir = os.path.join(skill_dir, 'references')
    output_dir = os.path.join(skill_dir, 'output')
    os.makedirs(output_dir, exist_ok=True)

    repo_match = re.search(r'([^/\\]+)_open_issue\.xlsx', os.path.basename(xlsx_file))
    repo = repo_match.group(1) if repo_match else 'unknown'

    logger.info(f"Repo name: {repo}")

    logger.info("Loading references suggested processing documents in the directory...")
    reference_issues = load_all_references(references_dir)
    logger.info(f"Loading {len(reference_issues)} Issue")

    logger.info("Ready to match...")
    matched_issues = defaultdict(list)
    skipped_count = 0
    unmatched_count = 0

    for _, row in df.iterrows():
        issue_id = row.get('ID')
        issue_title = row.get('标题', '')
        issue_url = row.get('URL', '')
        issue_state = row.get('状态', '')
        issue_created = row.get('创建时间', '')

        if should_skip(issue_title):
            skipped_count += 1
            logger.info(f"Skip [Roadmap] Issue: {issue_title[:50]}...")
            continue

        category = get_category(issue_title)

        best_match = find_best_match(issue_title, reference_issues)

        if best_match:
            matched_issues[category].append({
                'issue_id': issue_id,
                'title': issue_title,
                'url': issue_url,
                'state': issue_state,
                'created_at': issue_created,
                'repo': repo,
                'match': best_match
            })
            logger.info(f"Match success ({best_match['similarity']:.0%}): {issue_title[:40]}...")
        else:
            unmatched_count += 1
            logger.info(f"Not match: {issue_title[:40]}...")

    logger.info("Matching statistics:")
    logger.info(f"Skip (Roadmap): {skipped_count}")
    logger.info(f"Match success: {sum(len(issues) for issues in matched_issues.values())}")
    logger.info(f"Not match: {unmatched_count}")

    if not matched_issues:
        logger.info("No matching Issues were found, so no output file will be generated.")
        return 0

    output_file = os.path.join(output_dir, f'{repo}_open_issue_suggestions.md')

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# {repo} Open Issue 处理建议\n\n")
        f.write(f"**生成时间**: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n")
        f.write(f"**数据来源**: {os.path.basename(xlsx_file)}\n\n")
        f.write(f"**匹配阈值**: {SIMILARITY_THRESHOLD:.0%}\n\n")
        f.write("---\n\n")

        f.write("## 📋 目录\n\n")
        for category in sorted(matched_issues.keys()):
            count = len(matched_issues[category])
            anchor = re.sub(r'[^\w\u4e00-\u9fff-]', '', category).lower()
            f.write(f"- [{category}](#{anchor}) ({count}个Issue)\n")
        f.write("\n---\n\n")

        for category in sorted(matched_issues.keys()):
            issues = matched_issues[category]

            f.write(f"## {category}\n\n")
            f.write(f"> 共 **{len(issues)}** 个Issue匹配到处理建议\n\n")

            for idx, issue in enumerate(issues, 1):
                safe_title = escape_markdown(issue['title'])
                match = issue['match']

                f.write(f"### {idx}. {safe_title}\n\n")

                f.write(f"| 属性 | 值 |\n")
                f.write(f"|:-----|:---|\n")
                f.write(f"| Issue ID | `{issue['issue_id']}` |\n")
                f.write(f"| URL | [{issue['url']}]({issue['url']}) |\n")
                f.write(f"| 状态 | {issue['state']} |\n")
                f.write(f"| 仓库 | {issue['repo']} |\n")
                f.write(f"| 创建时间 | {format_datetime(issue['created_at'])} |\n\n")

                f.write(f"**📋 Issue处理建议**:\n\n")
                f.write(f"> 匹配来源: `{match['source_file']}`  \n")
                f.write(f"> 相似度: **{match['similarity']:.0%}**  \n")
                f.write(f"> 参考Issue ID: `{match['issue_id']}`\n\n")

                comments = match.get('comments', [])
                if comments:
                    f.write("**参考评论**:\n\n")
                    for i, comment in enumerate(comments, 1):
                        comment_text = comment.replace('\n', '  \n')
                        f.write(f"{i}. {comment_text}\n")

                f.write("\n---\n\n")

        f.write("## 📊 统计信息\n\n")
        f.write("| 分类 | 匹配数量 |\n")
        f.write("|:-----|:----------|\n")
        total = 0
        for category in sorted(matched_issues.keys()):
            count = len(matched_issues[category])
            total += count
            f.write(f"| {category} | {count} |\n")
        f.write(f"\n**总计**: {total} 个Issue匹配到处理建议\n")

    logger.info("Matching completed successfully!")
    logger.info(f"Output file: {output_file}")
    size = os.path.getsize(output_file)
    logger.info(f"File size: {size / 1024:.1f} KB")

    return 0


if __name__ == "__main__":
    sys.exit(main())
