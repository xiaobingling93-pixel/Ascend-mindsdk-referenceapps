#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prepare data for replying to a GitCode issue.
Read-only: fetches issue, comments, DeepWiki; outputs JSON. No comments posted.

Usage:
  python prepare_issue_reply.py --issue-url "https://gitcode.com/owner/repo/issues/123"
"""

import sys
import re
import json
import argparse
import time
import hashlib
import os
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stderr)

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
CONFIG_FILE = SKILL_ROOT / "config.json"
PROMPTS_DIR = SKILL_ROOT / "references" / "prompts"

sys.path.append(str(SCRIPT_DIR))
from common import get_token, print_json, parse_issue_url, api_get, init_windows_encoding
from security_filter import PromptInjectionDetector
from utils import extract_image_urls, download_image, deepwiki_query, image_to_base64

ENCODING_UTF8 = "utf-8"
KEY_BODY = "body"
KEY_TITLE = "title"
KEY_NUMBER = "number"
KEY_STATE = "state"
KEY_LABELS = "labels"
KEY_USER = "user"
KEY_LOGIN = "login"
KEY_CREATED_AT = "created_at"
KEY_UPDATED_AT = "updated_at"
KEY_STATUS = "status"
KEY_ERROR = "error"
KEY_MESSAGE = "message"
KEY_USERNAME = "username"
KEY_DEEPWIKI_STATUS = "deepwiki_status"
KEY_SECURITY_WARNINGS = "security_warnings"
TEXT_NONE = "（无）"


@dataclass
class ContributorCheckParams:
    token: str
    owner: str
    repo: str
    number: int
    author_id: Optional[int]
    author_login: str

DEFAULT_CONFIG = {
    "issue_content_max_chars": 3000,
    "deepwiki_timeout": 120,
    "deepwiki_max_retries": 3,
    "dry_run": False,
    "enable_deepwiki": True,
    "api_timeout": 30,
    "cache_ttl_seconds": 300,
    "enable_cache": True,
}

BOT_INDICATORS = ["bot", "[bot]", "ci-bot", "gitcode-bot", "webhook"]


def load_config() -> Dict:
    cfg = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding=ENCODING_UTF8) as f:
                user_cfg = json.load(f)
                cfg.update(user_cfg)
        except Exception as e:
            logging.warning("Failed to load config.json: %s", e)
    return cfg


def replace_images_with_placeholder(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "[图片]", text)
    text = re.sub(
        r"https?://[^\s)]+\.(?:png|jpe?g|gif|webp|bmp|svg)(?:\?[^\s)]*)?",
        "[图片链接]", text, flags=re.I,
    )
    return text.strip()


def _is_bot_user(user_dict: Dict) -> bool:
    if not user_dict:
        return False
    if (user_dict.get("type") or "").lower() == "bot":
        return True
    login = (user_dict.get(KEY_LOGIN) or user_dict.get("username") or "").lower()
    return any(ind in login for ind in BOT_INDICATORS)


def _is_substantive_comment(body_text: str) -> bool:
    if not body_text:
        return False
    stripped = body_text.strip()
    if stripped.startswith("/"):
        return False
    return len(stripped) >= 10


def fetch_issue(token: str, owner: str, repo: str, number: int) -> Dict:
    return api_get(token, f"repos/{owner}/{repo}/issues/{number}")


def fetch_comments(token: str, owner: str, repo: str, number: int) -> List[Dict]:
    comments = []
    page = 1
    while True:
        try:
            batch = api_get(token,
                            f"repos/{owner}/{repo}/issues/{number}/comments?per_page=100&page={page}")
        except Exception as e:
            logging.warning("Failed to fetch comments page %d: %s", page, e)
            break
        if not isinstance(batch, list) or not batch:
            break
        comments.extend(batch)
        if len(batch) < 100:
            break
        page += 1
        if page > 10:
            break
    return comments


def check_new_contributor(params: ContributorCheckParams) -> bool:
    is_new_contributor = True
    try:
        if params.author_login:
            check_issues = api_get(
                params.token,
                f"repos/{params.owner}/{params.repo}/issues?state=all"
                f"&creator={quote(params.author_login)}&per_page=5")
            other_issues = [i for i in (check_issues or []) if i.get(KEY_NUMBER) != params.number]
            if other_issues:
                is_new_contributor = False
        if is_new_contributor and params.author_login:
            check_pulls = api_get(
                params.token,
                f"repos/{params.owner}/{params.repo}/pulls?state=all&per_page=20")
            for p in (check_pulls or []):
                u = p.get(KEY_USER) or {}
                if (u.get("id") == params.author_id
                        or (u.get(KEY_LOGIN) or u.get("username") or "") == params.author_login):
                    is_new_contributor = False
                    break
    except Exception as e:
        logging.warning("New contributor check failed: %s", e)
    return is_new_contributor


def get_issue_temp_dir(owner: str, repo: str, issue_number: int) -> Path:
    """获取当前 Issue 的临时目录（按 owner_repo_issuenumber 组织）"""
    base_dir = SKILL_ROOT / "temp_dir" / f"{owner}_{repo}_{issue_number}"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def get_cache_dir() -> Path:
    """获取缓存目录（位于 skill 目录下的 temp_dir）"""
    base_dir = SKILL_ROOT / "temp_dir" / "cache"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def get_cache_key(prefix: str, *args) -> str:
    """生成缓存键"""
    content = "|".join(str(a) for a in args)
    return f"{prefix}_{hashlib.md5(content.encode()).hexdigest()[:16]}"


def get_cached_data(cache_key: str, ttl_seconds: int) -> Optional[Dict]:
    """获取缓存数据"""
    cache_file = get_cache_dir() / f"{cache_key}.json"
    if not cache_file.exists():
        return None

    try:
        mtime = cache_file.stat().st_mtime
        if time.time() - mtime > ttl_seconds:
            cache_file.unlink()
            return None

        with open(cache_file, "r", encoding=ENCODING_UTF8) as f:
            return json.load(f)
    except Exception:
        return None


def set_cached_data(cache_key: str, data: Dict) -> bool:
    """设置缓存数据"""
    try:
        cache_file = get_cache_dir() / f"{cache_key}.json"
        with open(cache_file, "w", encoding=ENCODING_UTF8) as f:
            json.dump(data, f, ensure_ascii=False)
        return True
    except Exception:
        return False


def security_check_content(detector: PromptInjectionDetector, content: str, 
                           content_type: str) -> Optional[Dict]:
    if not content:
        return None

    result = detector.check(content)
    if not result.passed:
        return {
            "content_type": content_type,
            "risk_level": result.risk_level.value,
            "threats": result.threats,
            "suggestion": result.suggestion,
        }
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Prepare issue reply data (read-only, no comments posted)")
    parser.add_argument("--issue-url", required=True, help="Full issue URL")
    parser.add_argument("--token", help="GitCode API token (optional, will use GITCODE_TOKEN env var if not provided)")
    parser.add_argument("--no-cache", action="store_true", help="Disable cache, force fresh data fetch")
    args = parser.parse_args()

    init_windows_encoding()

    token = get_token(args.token)
    if not token:
        print_json({KEY_STATUS: KEY_ERROR,
                     KEY_MESSAGE: "GITCODE_TOKEN 未配置。请访问 https://gitcode.com/setting/token-classic 创建令牌。"})
        sys.exit(1)

    try:
        owner, repo, number = parse_issue_url(args.issue_url)
    except ValueError as e:
        print_json({KEY_STATUS: KEY_ERROR, KEY_MESSAGE: str(e)})
        sys.exit(1)

    config = load_config()
    content_max = config.get("issue_content_max_chars", 3000)
    enable_deepwiki = config.get("enable_deepwiki", True)
    enable_cache = config.get("enable_cache", True) and not args.no_cache
    cache_ttl = config.get("cache_ttl_seconds", 300)

    if enable_cache:
        cache_key = get_cache_key("issue_reply", owner, repo, number, token[:8])
        cached_result = get_cached_data(cache_key, cache_ttl)
        if cached_result:
            logging.info("Using cached data (use --no-cache to force refresh)")
            print_json(cached_result)
            return

    security_detector = PromptInjectionDetector()

    issue = None
    comments = []
    deepwiki_answer = ""
    deepwiki_status = "skipped"

    deepwiki_timeout = config.get("deepwiki_timeout", 120)

    try:
        issue = fetch_issue(token, owner, repo, number)
    except HTTPError as e:
        body = e.read().decode(ENCODING_UTF8, errors="replace") if e.fp else ""
        error_msg = "Issue 不存在或无权限访问" if e.code == 404 else f"获取 Issue 失败: {e.code}"
        print_json({KEY_STATUS: KEY_ERROR, KEY_MESSAGE: error_msg})
        sys.exit(1)
    except Exception as e:
        print_json({KEY_STATUS: KEY_ERROR, KEY_MESSAGE: "获取 Issue 失败: %s" % str(e)})
        sys.exit(1)

    try:
        comments = fetch_comments(token, owner, repo, number)
    except Exception as e:
        logging.warning("Failed to fetch comments: %s", e)
        comments = []

    security_warnings = []

    issue_body = issue.get(KEY_BODY) or ""
    body_security = security_check_content(security_detector, issue_body, "issue_body")
    if body_security:
        security_warnings.append(body_security)

    for idx, c in enumerate(comments):
        comment_body = c.get(KEY_BODY) or ""
        comment_security = security_check_content(security_detector, comment_body, 
                                                   f"comment_{idx}")
        if comment_security:
            security_warnings.append(comment_security)

    if security_warnings:
        logging.warning("Security warnings detected: %d issues", len(security_warnings))
        for w in security_warnings:
            logging.warning("  - %s: %s", w["content_type"], w["risk_level"])

    author_id = (issue.get(KEY_USER) or {}).get("id")
    author_login = ((issue.get(KEY_USER) or {}).get(KEY_LOGIN)
                    or (issue.get(KEY_USER) or {}).get(KEY_USERNAME) or "")

    has_other_reply = False
    for c in comments:
        u = c.get(KEY_USER) or {}
        if _is_bot_user(u):
            continue
        uid = u.get("id")
        ulogin = u.get(KEY_LOGIN) or u.get(KEY_USERNAME) or ""
        if uid == author_id or (ulogin and ulogin == author_login):
            continue
        if _is_substantive_comment(c.get(KEY_BODY, "")):
            has_other_reply = True
            break

    if has_other_reply:
        print_json({
            KEY_STATUS: "already_replied",
            "owner": owner, "repo": repo, "issue_number": number,
            KEY_MESSAGE: "该 Issue 已有其他人回复，已跳过",
        })
        return

    has_label_comment = any("/label add" in (c.get(KEY_BODY) or "").lower() for c in comments)
    dry_run = config.get("dry_run", False)
    label_needed = not has_label_comment and not dry_run

    parts = [issue.get(KEY_TITLE) or "", "\n\n", issue.get(KEY_BODY) or ""]
    for c in sorted(comments, key=lambda x: (x.get(KEY_CREATED_AT) or "")):
        body_text = (c.get(KEY_BODY) or "").strip()
        if body_text.startswith("/"):
            continue
        parts.append("\n\n[评论] ")
        parts.append((c.get(KEY_USER) or {}).get(KEY_LOGIN)
                      or (c.get(KEY_USER) or {}).get(KEY_USERNAME) or "?")
        parts.append(": ")
        parts.append(body_text)
    issue_content_plain = replace_images_with_placeholder("".join(parts))

    if len(issue_content_plain) > content_max:
        issue_content_plain = issue_content_plain[:content_max] + "\n\n[内容已截断]"

    if enable_deepwiki:
        try:
            query_text = ((issue.get(KEY_TITLE) or "") + "\n"
                          + ((issue.get(KEY_BODY) or "")[:500]))
            if query_text.strip():
                deepwiki_answer, deepwiki_status = deepwiki_query(
                    f"{owner}/{repo}",
                    query_text.strip(),
                    base_timeout=config.get("deepwiki_timeout", 120),
                    max_retries=config.get("deepwiki_max_retries", 3),
                )
        except Exception as e:
            logging.warning("DeepWiki query failed: %s", e)
            deepwiki_status = "failed"

    contributor_params = ContributorCheckParams(
        token=token, owner=owner, repo=repo, number=number,
        author_id=author_id, author_login=author_login
    )
    is_new_contributor = check_new_contributor(contributor_params)

    labels = [lb.get("name") for lb in (issue.get(KEY_LABELS) or []) if lb.get("name")]
    meta = {
        KEY_TITLE: (issue.get(KEY_TITLE) or "")[:500],
        KEY_LABELS: labels,
        "is_new_contributor": is_new_contributor,
    }

    image_urls = extract_image_urls(issue.get(KEY_BODY) or "")
    for c in comments:
        image_urls.extend(extract_image_urls(c.get(KEY_BODY) or ""))
    image_urls = list(dict.fromkeys(image_urls))

    prompt_draft_partial = ""
    if PROMPTS_DIR.exists():
        draft_path = PROMPTS_DIR / "draft_reply.txt"
        if draft_path.exists():
            try:
                issue_base_url = "https://gitcode.com/%s/%s" % (owner, repo)
                tpl = draft_path.read_text(encoding=ENCODING_UTF8)
                tpl = tpl.replace("{issue_content_plain}", issue_content_plain)
                tpl = tpl.replace("{issue_metadata.title}", meta[KEY_TITLE])
                tpl = tpl.replace("{issue_metadata.labels}",
                                  ", ".join(meta[KEY_LABELS]) if meta[KEY_LABELS] else TEXT_NONE)
                tpl = tpl.replace("{issue_metadata.is_new_contributor}",
                                  "是" if meta["is_new_contributor"] else "否")
                tpl = tpl.replace("{deepwiki_answer}",
                                  deepwiki_answer if deepwiki_answer else TEXT_NONE)
                tpl = tpl.replace("{issue_base_url}", issue_base_url)
                if image_urls:
                    image_info_lines = ["检测到以下图片（AI 助手必须查看这些图片）："]
                    for i, url in enumerate(image_urls[:5], 1):
                        image_info_lines.append(f"  - 图片{i}: {url}")
                    image_info = "\n".join(image_info_lines)
                else:
                    image_info = "（无图片）"
                tpl = tpl.replace("{image_info}", image_info)
                prompt_draft_partial = tpl
            except Exception as e:
                logging.warning("Failed to read draft prompt: %s", e)

    image_local_paths = []
    image_base64_list = []
    if image_urls:
        issue_temp_dir = get_issue_temp_dir(owner, repo, number)
        images_dir = issue_temp_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        for i, url in enumerate(image_urls[:5]):
            local_path = download_image(url, images_dir, index=i)
            if local_path:
                image_local_paths.append(str(local_path))
                base64_data = image_to_base64(local_path)
                if base64_data:
                    image_base64_list.append(base64_data)

    warnings = []
    if security_warnings:
        warnings.extend([w.get("suggestion", str(w)) for w in security_warnings])
    if deepwiki_status == "failed":
        warnings.append("DeepWiki 查询失败，回复可能缺少项目背景信息")

    out = {
        KEY_STATUS: "ok",
        "owner": owner,
        "repo": repo,
        "issue_number": number,
        "issue_url": args.issue_url,
        "issue_content_plain": issue_content_plain,
        "issue_metadata": meta,
        "image_urls": image_urls,
        "image_local_paths": image_local_paths,
        "image_base64_list": image_base64_list,
        "deepwiki_answer": deepwiki_answer,
        KEY_DEEPWIKI_STATUS: deepwiki_status,
        "label_needed": label_needed,
        "prompt_draft_partial": prompt_draft_partial,
        KEY_SECURITY_WARNINGS: security_warnings if security_warnings else None,
        "warnings": warnings if warnings else None,
        "cached": False,
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }

    if enable_cache:
        set_cached_data(cache_key, out)

    output_file = SKILL_ROOT / f"output_{owner}_{repo}_{number}.json"
    try:
        with open(output_file, 'w', encoding=ENCODING_UTF8) as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
            f.write('\n')
    except Exception as e:
        logging.error("Failed to write output file: %s", e)
        sys.exit(1)

    logging.info("")
    logging.info("=" * 60)
    logging.info("Output file: %s", output_file)

    if image_urls:
        logging.warning("")
        logging.warning("=" * 40)
        logging.warning("Important: This Issue contains %d images!", len(image_urls))
        logging.warning("You must view these images before generating a reply!")
        for i, path in enumerate(image_local_paths, 1):
            logging.warning("   Image %d: %s", i, path)
        logging.warning("=" * 40)

    logging.info("")
    logging.info("Checklist:")
    logging.info("   [OK] status: %s", out.get('status', 'unknown'))
    logging.info("   [%s] image_urls: %d images%s", 'OK' if image_urls else '  ', len(image_urls), ' (must view!)' if image_urls else '')
    logging.info("   [%s] deepwiki_status: %s", 'OK' if out.get('deepwiki_status') == 'ok' else '  ', out.get('deepwiki_status', 'unknown'))
    if out.get('security_warnings'):
        logging.warning("   [WARN] security_warnings: %d issues detected", len(out.get('security_warnings', [])))
    logging.info("=" * 60)


if __name__ == "__main__":
    main()
