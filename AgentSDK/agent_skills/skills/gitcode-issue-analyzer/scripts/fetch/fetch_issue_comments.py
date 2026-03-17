import http.client
import json
import logging
import os
import sys
import time
import pandas as pd
import winreg

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SYSTEM_CONFIG_TOKEN_NAME = "GITCODE_TOKEN"


def get_gitcode_token():
    token = os.environ.get(SYSTEM_CONFIG_TOKEN_NAME)
    if token:
        return token

    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")
        token, _ = winreg.QueryValueEx(key, SYSTEM_CONFIG_TOKEN_NAME)
        winreg.CloseKey(key)
        return token
    except (OSError, WindowsError) as e:
        logger.warning(f"Failed to read {SYSTEM_CONFIG_TOKEN_NAME} from system environment: {e}")

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment")
        token, _ = winreg.QueryValueEx(key, SYSTEM_CONFIG_TOKEN_NAME)
        winreg.CloseKey(key)
        return token
    except (OSError, WindowsError) as e:
        logger.warning(f"Failed to read {SYSTEM_CONFIG_TOKEN_NAME} from user environment: {e}")

    return None


def fetch_comments(git_code_token, repo, page):
    conn = http.client.HTTPSConnection("api.gitcode.com")
    payload = ''
    headers = {
        'Accept': 'application/json'
    }
    url = f"/api/v5/repos/Ascend/{repo}/issues/comments?access_token={git_code_token}&page={page}&per_page=100"
    conn.request("GET", url, payload, headers)
    res = conn.getresponse()
    data = res.read()
    return json.loads(data)


def process_comments(comments):
    comments_data = []
    for comment in comments:
        target = comment.get('target', {})
        issue = target.get('issue', {})
        comments_data.append({
            'ID': comment.get('id'),
            '评论内容': comment.get('body'),
            'Issue ID': issue.get('id'),
            'Issue标题': issue.get('title'),
            '创建时间': comment.get('created_at')
        })
    return comments_data


def main():
    if len(sys.argv) < 2:
        logger.error("Missing repo parameter")
        logger.info("Usage: python fetch_issue_comments.py <repo>")
        logger.info("Example: python fetch_issue_comments.py mind-cluster")
        return 1

    repo = sys.argv[1]
    git_code_token = get_gitcode_token()

    if not git_code_token:
        logger.error(f"{SYSTEM_CONFIG_TOKEN_NAME} environment variable is not set")
        logger.info("Please set the environment variable:")
        logger.info("Windows PowerShell: $env:GITCODE_TOKEN = 'your_token_here'")
        logger.info(
            "Or set permanently: [Environment]::SetEnvironmentVariable('GITCODE_TOKEN', 'your_token_here', 'User')")
        return 1

    logger.info(f"Retrieving {repo} information about issue comments in the repository...")
    logger.info(f"Token found: {git_code_token[:10]}...")

    all_comments = []
    page = 1

    try:
        while True:
            logger.info(f"Retrieving comments on page {page}...")
            comments = fetch_comments(git_code_token, repo, page)

            if not comments:
                logger.info(f"Page {page} returns an empty list, stop fetching")
                break

            processed = process_comments(comments)
            all_comments.extend(processed)
            logger.info(
                f"Successfully retrieved {len(comments)} comments on page {page}, total {len(all_comments)} comments")

            if len(comments) < 100:
                logger.info("All comments have been retrieved")
                break

            page += 1
            logger.info("Waiting 2 seconds...")
            time.sleep(2)

        logger.info(f"Successfully retrieved {len(all_comments)} comments on {repo}")

        df_comments = pd.DataFrame(all_comments)
        output_file = f'{repo}_issue_comments.xlsx'
        df_comments.to_excel(output_file, index=False, engine='openpyxl')
        logger.info(f"Successfully saved {output_file}")

    except Exception as e:
        logger.error(f"Failed to retrieve comments: {e}")
        if all_comments:
            logger.info(f"Attempting to save {len(all_comments)} comments...")
            df_comments = pd.DataFrame(all_comments)
            output_file = f'{repo}_issue_comments.xlsx'
            df_comments.to_excel(output_file, index=False, engine='openpyxl')
            logger.info(f"Successfully saved {output_file}")
        return 1

    logger.info("Finished!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
