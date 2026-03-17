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


def fetch_issues(git_code_token, repo, state, page):
    conn = http.client.HTTPSConnection("api.gitcode.com")
    payload = ''
    headers = {
        'Accept': 'application/json'
    }
    url = f"/api/v5/repos/Ascend/{repo}/issues?access_token={git_code_token}&state={state}&page={page}&per_page=100"
    conn.request("GET", url, payload, headers)
    res = conn.getresponse()
    data = res.read()
    return json.loads(data)


def process_issues(issues):
    issues_data = []
    for issue in issues:
        issues_data.append({
            'ID': issue.get('id'),
            'URL': issue.get('html_url'),
            '状态': issue.get('state'),
            '标题': issue.get('title'),
            '内容': issue.get('body'),
            '仓库': issue.get('repository', {}).get('path', ''),
            '创建时间': issue.get('created_at'),
            'Issue状态': issue.get('issue_state'),
            '评论数': issue.get('comments'),
            'Issue类型': issue.get('issue_type')
        })
    return issues_data


def main():
    if len(sys.argv) < 2:
        logger.error("Missing repo parameter")
        logger.info("Usage: python fetch_open_issues.py <repo>")
        logger.info("Example: python fetch_open_issues.py mind-cluster")
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

    logger.info(f"Retrieving {repo} open issues from repository...")
    logger.info(f"Token found: {git_code_token[:10]}...")

    try:
        all_issues = []
        page = 1

        while True:
            logger.info(f"Fetching page {page}...")
            issues = fetch_issues(git_code_token, repo, "open", page)

            if not issues:
                logger.info(f"Page {page} returned empty, stopping pagination")
                break

            processed = process_issues(issues)
            all_issues.extend(processed)
            logger.info(f"Page {page}: Retrieved {len(issues)} issues, Total: {len(all_issues)}")

            if len(issues) < 100:
                logger.info("Last page reached (less than 100 items)")
                break

            page += 1
            time.sleep(2)

        logger.info(f"Total open issues retrieved: {len(all_issues)}")

        if all_issues:
            df_open = pd.DataFrame(all_issues)
            output_file = f'{repo}_open_issue.xlsx'
            df_open.to_excel(output_file, index=False, engine='openpyxl')
            logger.info(f"Successfully saved {output_file}")
        else:
            logger.warning("No open issues found")

    except Exception as e:
        logger.error(f"Failed to retrieve open issues: {e}")
        return 1

    logger.info("Finished!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
