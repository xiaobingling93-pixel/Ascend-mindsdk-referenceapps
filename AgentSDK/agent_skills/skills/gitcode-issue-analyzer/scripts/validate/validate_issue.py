import sys
import os
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def find_xlsx_file(fetch_dir, filename):
    search_paths = [
        filename,
        os.path.join(fetch_dir, filename),
    ]
    for path in search_paths:
        if os.path.exists(path):
            return path
    return None


def main():
    if len(sys.argv) < 2:
        logger.error("Missing repo parameter")
        logger.info("Usage: python validate_issue.py <repo>")
        return 1

    repo = sys.argv[1]

    script_dir = os.path.dirname(os.path.abspath(__file__))
    fetch_dir = os.path.join(os.path.dirname(script_dir), 'fetch')

    logger.info("=" * 60)
    logger.info("Open Issues Summary:")
    logger.info("=" * 60)

    open_file = find_xlsx_file(fetch_dir, f"{repo}_open_issue.xlsx")
    if not open_file:
        logger.error(f"File not found: {repo}_open_issue.xlsx")
        logger.info(f"  Searched paths:")
        logger.info(f"    - Current directory")
        logger.info(f"    - {fetch_dir}")
        return 1

    df_open = pd.read_excel(open_file)
    logger.info(f"Total: {len(df_open)} opened Issues")
    logger.info(f"File: {open_file}")

    logger.info("=" * 60)
    logger.info("Closed Issues Summary:")
    logger.info("=" * 60)

    closed_file = find_xlsx_file(fetch_dir, f"{repo}_closed_issue.xlsx")
    if not closed_file:
        logger.error(f"File not found: {repo}_closed_issue.xlsx")
        return 1

    df_closed = pd.read_excel(closed_file)
    logger.info(f"Total: {len(df_closed)} closed Issues")
    logger.info(f"File: {closed_file}")

    logger.info("=" * 60)
    logger.info("Issues Comments Summary:")
    logger.info("=" * 60)

    comments_file = find_xlsx_file(fetch_dir, f"{repo}_issue_comments.xlsx")
    if not comments_file:
        logger.warning(f"File not found: {repo}_issue_comments.xlsx")
        logger.info("Skipping comments summary...")
    else:
        df_comments = pd.read_excel(comments_file)
        logger.info(f"Total: {len(df_comments)} comments on Issues")
        logger.info(f"File: {comments_file}")

    logger.info("=" * 60)
    logger.info("Issue Type Distribution:")
    logger.info("=" * 60)
    logger.info("Open Issue Types:")
    if 'Issue类型' in df_open.columns:
        logger.info(f"\n{df_open['Issue类型'].value_counts()}")
    elif 'issue_type' in df_open.columns:
        logger.info(f"\n{df_open['issue_type'].value_counts()}")
    else:
        logger.warning("No issue_type column found")

    logger.info("Closed Issue Types:")
    if 'Issue类型' in df_closed.columns:
        logger.info(f"\n{df_closed['Issue类型'].value_counts()}")
    elif 'issue_type' in df_closed.columns:
        logger.info(f"\n{df_closed['issue_type'].value_counts()}")
    else:
        logger.warning("No issue_type column found")

    return 0


if __name__ == "__main__":
    sys.exit(main())
