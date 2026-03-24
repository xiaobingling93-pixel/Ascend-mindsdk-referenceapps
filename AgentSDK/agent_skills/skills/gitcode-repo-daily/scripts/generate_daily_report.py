#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitCode 仓库运营报表：日报拉 API 写 DB；周/月报优先从 DB 聚合，当某仓无当日/当周/当月数据时用该周周一+周日或该月首日+末日调 API 补拉并合并。仅向 stdout 输出单份 JSON。

Usage:
  python generate_daily_report.py [--type day|week|month] [--date YYYY-MM-DD]
"""

import sys
import re
import json
import argparse
import os
import subprocess
import time
import sqlite3
import logging
import shutil
from datetime import datetime, timedelta, date, timezone
from pathlib import Path
from dataclasses import dataclass

from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

GITCODE_API_BASE = "https://api.gitcode.com/api/v5"
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
CONFIG_FILE = SKILL_ROOT / "config.json"
RESOURCES_DIR = SKILL_ROOT / "resources"
DB_PATH = RESOURCES_DIR / "report.db"

ENCODING_UTF8 = "utf-8"
ENCODING_UTF8_SIG = "utf-8-sig"
STR_STATUS = "status"
STR_OK = "ok"
STR_ERROR = "error"
STR_MESSAGE = "message"
STR_DAY = "day"
STR_WEEK = "week"
STR_MONTH = "month"
STR_REPOS = "repos"
STR_REPORT = "report"
STR_DATE = "date"
STR_TODAY = "today"
STR_TITLE = "title"
STR_NUMBER = "number"
STR_REPO = "repo"
STR_SCHEMA_VERSION = "schema_version"
STR_GENERATED_AT = "generated_at"
STR_REPOS_SAVED = "repos_saved"
STR_REPOS_SAVED_MESSAGE = "repos_saved_message"
MSG_REPOS_SAVED = "已保存为默认仓库列表，下次若不指定仓库将使用此列表。"
FILE_REPORT_JSON = "report.json"
FMT_DATETIME_UTC = "%Y-%m-%dT%H:%M:%SZ"
MD_LIST_PREFIX = "- %s\n"
POWERSHELL_EXE = shutil.which("powershell") or r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"

STR_FETCH_ERROR = "fetch_error"
STR_CREATED_AT = "created_at"
STR_USER = "user"
STR_USERNAME = "username"
STR_LOGIN = "login"
STR_ADDITIONS = "additions"
STR_PRS_MERGED = "prs_merged"
STR_PRS_CLOSED = "prs_closed"
STR_REPO_SUMMARY = "repo_summary"
STR_PRS_OPENED = "prs_opened"
STR_ISSUES_OPENED = "issues_opened"
STR_ISSUES_CLOSED = "issues_closed"
STR_ISSUES_OPENED_TODAY_LIST = "issues_opened_today_list"
STR_ISSUES_CLOSED_TODAY_LIST = "issues_closed_today_list"
STR_PRS_OPENED_TODAY_LIST = "prs_opened_today_list"
STR_MERGED_PRS_TODAY_LIST = "merged_prs_today_list"
STR_ACTIVE_CONTRIBUTORS = "active_contributors"
STR_CODE_ADDITIONS = "code_additions"
STR_CODE_DELETIONS = "code_deletions"
STR_MAJOR_PRS = "major_prs"
STR_HOT_ISSUES = "hot_issues"
STR_MERGED_PRS_FOR_AI = "merged_prs_for_ai"
STR_PATH = "PATH"
STR_SAVED_TO = "saved_to"
SCHEMA_VERSION_VALUE = "1.0"

# 默认 config 键值（与 README §5 一致）
DEFAULTS = {
    STR_REPOS: [],
    "timezone": "Asia/Shanghai",
    "request_timeout_seconds": 30,
    "request_retry_times": 2,
    "request_retry_interval_seconds": 2,
    "request_sleep_seconds": 0.1,
    "stale_days": 30,
    "stale_issue_exclude_keywords": ["RFC", "CVE", "Roadmap"],
    "major_pr_additions_threshold": 500,
    "hot_issue_comments_threshold": 5,
    "max_repos_per_report": 50,
    "merged_pr_body_max_chars": 2000,
}


@dataclass
class ApiConfig:
    """API 请求配置参数。"""
    token: str
    timeout_sec: int
    retry_times: int
    retry_interval_sec: float
    sleep_sec: float


@dataclass
class DailyMetricsData:
    """每日指标数据。"""
    report_date: date
    repo: str
    today: dict
    major_prs: list
    hot_issues: list
    merged_prs_for_ai: list


@dataclass
class PaginatedApiConfig:
    """分页 API 配置参数。"""
    path_template: str
    api_config: ApiConfig
    per_page: int = 100
    page_stop: callable = None


@dataclass
class RepoFetchParams:
    """仓库数据拉取参数。"""
    token: str
    owner: str
    repo: str
    report_date: date
    cfg: dict
    tz_offset: float


@dataclass
class FallbackFetchParams:
    """补拉缺失仓库数据参数。"""
    report: dict
    token: str
    start_date: date
    end_date: date
    cfg: dict
    tz_offset: float
    error_keyword: str


def load_config():
    cfg = dict(DEFAULTS)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding=ENCODING_UTF8) as f:
                data = json.load(f)
                if isinstance(data, dict):
                    cfg.update(data)
                    if not isinstance(cfg.get(STR_REPOS), list):
                        cfg[STR_REPOS] = DEFAULTS[STR_REPOS]
                    for int_key in ("request_timeout_seconds", "request_retry_times", "stale_days",
                                    "major_pr_additions_threshold", "hot_issue_comments_threshold",
                                    "max_repos_per_report", "merged_pr_body_max_chars"):
                        try:
                            cfg[int_key] = int(cfg[int_key])
                        except (TypeError, ValueError):
                            cfg[int_key] = DEFAULTS[int_key]
        except Exception as e:
            logger.warning("failed to load config.json: %s", e)
    return cfg


def save_config_repos(repos_list):
    """将仓库列表写入 config.json 的 repos，保留其余配置项。"""
    cfg = load_config()
    cfg[STR_REPOS] = [r.strip() for r in repos_list if isinstance(r, str) and "/" in r.strip()]
    try:
        with open(CONFIG_FILE, "w", encoding=ENCODING_UTF8) as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("failed to write config.json: %s", e)


def _get_token_windows_user():
    try:
        out = subprocess.check_output(
            [POWERSHELL_EXE, "-NoProfile", "-Command",
             "[Environment]::GetEnvironmentVariable('GITCODE_TOKEN','User')"],
            creationflags=0x08000000 if sys.platform == "win32" else 0,
            timeout=5,
            stderr=subprocess.DEVNULL,
        )
        if out:
            return out.decode(ENCODING_UTF8, errors="replace").strip()
    except Exception as e:
        logger.debug("Failed to get GITCODE_TOKEN from Windows User environment: %s", e)
    return None


def _get_token_windows_machine():
    try:
        out = subprocess.check_output(
            [POWERSHELL_EXE, "-NoProfile", "-Command",
             "[Environment]::GetEnvironmentVariable('GITCODE_TOKEN','Machine')"],
            creationflags=0x08000000 if sys.platform == "win32" else 0,
            timeout=5,
            stderr=subprocess.DEVNULL,
        )
        if out:
            return out.decode(ENCODING_UTF8, errors="replace").strip()
    except Exception as e:
        logger.debug("Failed to get GITCODE_TOKEN from Windows Machine environment: %s", e)
    return None


def get_token():
    """GITCODE_TOKEN：当前进程 → Windows 用户级 → 系统级。"""
    token = os.environ.get("GITCODE_TOKEN")
    if token:
        return token.strip()
    if sys.platform == "win32":
        t = _get_token_windows_user()
        if t:
            return t
        t = _get_token_windows_machine()
        if t:
            return t
    return None


def _parse_iso_to_date(iso_str, tz_offset_hours):
    """将 API 返回的 ISO8601 转为在配置时区下的日期。"""
    if not iso_str or not isinstance(iso_str, str):
        return None
    try:
        s = iso_str.strip()
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        local_dt = dt.astimezone(timezone(timedelta(hours=tz_offset_hours)))
        return local_dt.date()
    except (ValueError, TypeError, OverflowError):
        try:
            return datetime.strptime(iso_str[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None


_TIMEZONE_OFFSETS = {
    "Asia/Shanghai": 8, "Asia/Beijing": 8, "Asia/Chongqing": 8,
    "Asia/Hong_Kong": 8, "Asia/Taipei": 8, "Asia/Singapore": 8,
    "Asia/Tokyo": 9, "Asia/Seoul": 9,
    "Asia/Kolkata": 5.5, "Asia/Calcutta": 5.5,
    "Asia/Dubai": 4,
    "Europe/London": 0, "Europe/Berlin": 1, "Europe/Paris": 1,
    "Europe/Moscow": 3,
    "America/New_York": -5, "America/Chicago": -6,
    "America/Denver": -7, "America/Los_Angeles": -8,
    "America/Sao_Paulo": -3,
    "Australia/Sydney": 11, "Australia/Melbourne": 11,
    "Pacific/Auckland": 13,
    "UTC": 0,
}


def _get_tz_offset_hours(cfg):
    """从 config timezone 得到相对 UTC 的小时偏移。"""
    tz = (cfg.get("timezone") or "Asia/Shanghai").strip()
    if tz in _TIMEZONE_OFFSETS:
        return _TIMEZONE_OFFSETS[tz]
    m = re.search(r"UTC([+-])(\d+(?:\.\d+)?)", tz, re.I)
    if m:
        val = float(m.group(2))
        return val if m.group(1) == "+" else -val
    return 8


def _get_report_date(cfg, args_date):
    """报表日期：args --date 优先，否则为 config timezone 下的「今日」。
    使用 timezone 偏移保证容器为 UTC 时仍按配置时区算「今日」。"""
    if args_date:
        try:
            return datetime.strptime(args_date, "%Y-%m-%d").date()
        except ValueError:
            pass
    offset = _get_tz_offset_hours(cfg)
    try:
        utc_now = datetime.now(timezone.utc)
        local_now = utc_now + timedelta(hours=offset)
        return local_now.date()
    except Exception:
        return date.today()


def api_get(api_config, path):
    """拉取 GitCode API；请求后 sleep；失败重试；429 时等待 Retry-After 或 60s。返回 (data, error_msg)。"""
    url = (GITCODE_API_BASE.rstrip("/") + "/" + path.lstrip("/")).replace(" ", "%20")
    req = Request(url, headers={"PRIVATE-TOKEN": api_config.token})
    last_err = None
    for _ in range(api_config.retry_times + 1):
        try:
            with urlopen(req, timeout=api_config.timeout_sec) as f:
                time.sleep(api_config.sleep_sec)
                return json.loads(f.read().decode(ENCODING_UTF8)), None
        except HTTPError as e:
            last_err = "HTTP %s" % e.code
            if e.code == 429:
                wait = 60
                if e.headers.get("Retry-After"):
                    try:
                        wait = int(e.headers["Retry-After"])
                    except ValueError:
                        pass
                time.sleep(wait)
            else:
                time.sleep(api_config.retry_interval_sec)
        except (URLError, OSError, ValueError) as e:
            last_err = str(e)
            time.sleep(api_config.retry_interval_sec)
        except Exception as e:
            last_err = str(e)
            break
    return None, (last_err or "请求失败")


CURRENT_DB_VERSION = 2


def _get_db_version(conn):
    try:
        row = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1").fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return 0


def _migrate_db(conn, from_version):
    """渐进式迁移：每个 if 块负责从 version N 升级到 N+1。"""
    if from_version < 1:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER NOT NULL,
                applied_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS snapshots (
                date TEXT NOT NULL, repo TEXT NOT NULL,
                stars INTEGER NOT NULL, forks INTEGER NOT NULL, open_issues INTEGER NOT NULL,
                PRIMARY KEY (date, repo)
            );
            CREATE TABLE IF NOT EXISTS daily_metrics (
                date TEXT NOT NULL, repo TEXT NOT NULL,
                prs_merged INTEGER NOT NULL, prs_closed INTEGER NOT NULL,
                issues_opened INTEGER NOT NULL, issues_closed INTEGER NOT NULL,
                code_additions INTEGER NOT NULL, code_deletions INTEGER NOT NULL,
                active_contributors INTEGER NOT NULL,
                stale_issues_count INTEGER NOT NULL, stale_prs_count INTEGER NOT NULL,
                major_prs_json TEXT, hot_issues_json TEXT, merged_prs_for_ai_json TEXT,
                PRIMARY KEY (date, repo)
            );
            CREATE TABLE IF NOT EXISTS daily_summaries (
                date TEXT NOT NULL, repo TEXT NOT NULL, summary_text TEXT NOT NULL,
                PRIMARY KEY (date, repo)
            );
            CREATE TABLE IF NOT EXISTS weekly_metrics (
                week_start_date TEXT NOT NULL, repo TEXT NOT NULL,
                prs_merged INTEGER NOT NULL, prs_closed INTEGER NOT NULL,
                issues_opened INTEGER NOT NULL, issues_closed INTEGER NOT NULL,
                code_additions INTEGER NOT NULL, code_deletions INTEGER NOT NULL,
                active_contributors INTEGER NOT NULL,
                stale_issues_count INTEGER NOT NULL, stale_prs_count INTEGER NOT NULL,
                stars_delta INTEGER,
                PRIMARY KEY (week_start_date, repo)
            );
            CREATE TABLE IF NOT EXISTS weekly_summaries (
                week_start_date TEXT NOT NULL, repo TEXT NOT NULL, summary_text TEXT NOT NULL,
                PRIMARY KEY (week_start_date, repo)
            );
            CREATE TABLE IF NOT EXISTS monthly_metrics (
                month_start_date TEXT NOT NULL, repo TEXT NOT NULL,
                prs_merged INTEGER NOT NULL, prs_closed INTEGER NOT NULL,
                issues_opened INTEGER NOT NULL, issues_closed INTEGER NOT NULL,
                code_additions INTEGER NOT NULL, code_deletions INTEGER NOT NULL,
                active_contributors INTEGER NOT NULL,
                stale_issues_count INTEGER NOT NULL, stale_prs_count INTEGER NOT NULL,
                stars_delta INTEGER,
                PRIMARY KEY (month_start_date, repo)
            );
            CREATE TABLE IF NOT EXISTS monthly_summaries (
                month_start_date TEXT NOT NULL, repo TEXT NOT NULL, summary_text TEXT NOT NULL,
                PRIMARY KEY (month_start_date, repo)
            );
        """)
        conn.execute("INSERT INTO schema_version (version, applied_at) VALUES (1, datetime('now'))")

    if from_version < 2:
        existing = {r[1] for r in conn.execute("PRAGMA table_info(daily_metrics)").fetchall()}
        if "prs_opened" not in existing:
            conn.execute("ALTER TABLE daily_metrics ADD COLUMN prs_opened INTEGER DEFAULT 0")
        conn.execute("INSERT INTO schema_version (version, applied_at) VALUES (2, datetime('now'))")

    conn.commit()


def ensure_db():
    """初始化 resources 目录与 SQLite，支持渐进式 schema 迁移。"""
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    ver = _get_db_version(conn)
    if ver < CURRENT_DB_VERSION:
        _migrate_db(conn, ver)
    conn.close()


def get_yesterday_snapshot(repo, report_date):
    """从 snapshots 表读取昨日快照，用于 Star/Fork 增量。"""
    yesterday = report_date - timedelta(days=1)
    date_str = yesterday.strftime("%Y-%m-%d")
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute(
        "SELECT stars, forks FROM snapshots WHERE date = ? AND repo = ?",
        (date_str, repo),
    ).fetchone()
    conn.close()
    if row:
        return {"stars": row[0], "forks": row[1]}
    return None


def write_snapshot(report_date, repo, stars, forks, open_issues):
    """写入当日快照。"""
    date_str = report_date.strftime("%Y-%m-%d")
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "INSERT OR REPLACE INTO snapshots (date, repo, stars, forks, open_issues) VALUES (?, ?, ?, ?, ?)",
        (date_str, repo, stars, forks, open_issues),
    )
    conn.commit()
    conn.close()


def write_daily_metrics(metrics_data):
    """写入当日指标到 daily_metrics，供周报/月报从 DB 聚合，无需再调 API。"""
    date_str = metrics_data.report_date.strftime("%Y-%m-%d")
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """INSERT OR REPLACE INTO daily_metrics (
            date, repo, prs_merged, prs_closed, prs_opened, issues_opened, issues_closed,
            code_additions, code_deletions, active_contributors,
            stale_issues_count, stale_prs_count, major_prs_json, hot_issues_json, merged_prs_for_ai_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            date_str,
            metrics_data.repo,
            metrics_data.today.get(STR_PRS_MERGED, 0),
            metrics_data.today.get(STR_PRS_CLOSED, 0),
            metrics_data.today.get(STR_PRS_OPENED, 0),
            metrics_data.today.get(STR_ISSUES_OPENED, 0),
            metrics_data.today.get(STR_ISSUES_CLOSED, 0),
            metrics_data.today.get(STR_CODE_ADDITIONS, 0),
            metrics_data.today.get(STR_CODE_DELETIONS, 0),
            metrics_data.today.get(STR_ACTIVE_CONTRIBUTORS, 0),
            metrics_data.today.get("stale_issues_count", 0),
            metrics_data.today.get("stale_prs_count", 0),
            json.dumps(metrics_data.major_prs, ensure_ascii=False),
            json.dumps(metrics_data.hot_issues, ensure_ascii=False),
            json.dumps(metrics_data.merged_prs_for_ai, ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()


def _paginated_api_get(paginated_config):
    """通用分页拉取。path_template 需包含 %s 占位符用于填入 page。
    page_stop: 可选 callable(page_items)->bool，当前页数据保留但不再请求下一页。
    返回 (all_items_list, error_string_or_None)。
    """
    result = []
    page = 1
    while True:
        path = paginated_config.path_template % page
        data, err = api_get(paginated_config.api_config, path)
        if err:
            return result, err
        lst = data if isinstance(data, list) else []
        if not lst:
            break
        result.extend(lst)
        if len(lst) < paginated_config.per_page:
            break
        if paginated_config.page_stop and paginated_config.page_stop(lst):
            break
        page += 1
    return result, None


def fetch_one_repo(params):
    """拉取单仓数据并计算指标。使用 sort/since/提前终止优化 API 调用量。"""
    repo_key = "%s/%s" % (params.owner, params.repo)
    timeout_sec = params.cfg.get("request_timeout_seconds") or 30
    retry_times = params.cfg.get("request_retry_times") or 2
    retry_interval = params.cfg.get("request_retry_interval_seconds") or 2
    sleep_sec = params.cfg.get("request_sleep_seconds") or 0.1
    stale_days = params.cfg.get("stale_days") or 30
    exclude_kw = [s.strip().lower() for s in (params.cfg.get("stale_issue_exclude_keywords") or [])]
    major_threshold = params.cfg.get("major_pr_additions_threshold") or 500
    hot_threshold = params.cfg.get("hot_issue_comments_threshold") or 5
    body_max = params.cfg.get("merged_pr_body_max_chars") or 2000
    stale_cutoff = params.report_date - timedelta(days=stale_days)

    api_config = ApiConfig(
        token=params.token,
        timeout_sec=timeout_sec,
        retry_times=retry_times,
        retry_interval_sec=retry_interval,
        sleep_sec=sleep_sec,
    )

    _utc_start = datetime(params.report_date.year, params.report_date.month, params.report_date.day) - timedelta(hours=params.tz_offset)
    since_utc = _utc_start.strftime(FMT_DATETIME_UTC)

    def is_same_day(iso_str):
        d = _parse_iso_to_date(iso_str, params.tz_offset)
        return d == params.report_date if d else False

    def _all_updated_before(items):
        for item in items:
            d = _parse_iso_to_date(item.get("updated_at") or "", params.tz_offset)
            if d is None or d >= params.report_date:
                return False
        return True

    def _all_created_after_cutoff(items):
        for item in items:
            d = _parse_iso_to_date(item.get(STR_CREATED_AT) or "", params.tz_offset)
            if d is None or d < stale_cutoff:
                return False
        return True

    # 1) 仓库详情
    data_repo, err = api_get(api_config, "repos/%s/%s" % (params.owner, params.repo))
    if err:
        return {STR_REPO: repo_key, STR_FETCH_ERROR: err}, err
    stars = int(data_repo.get("stargazers_count") or 0)
    forks = int(data_repo.get("forks_count") or 0)
    open_issues_count = int(data_repo.get("open_issues_count") or 0)

    yesterday_snap = get_yesterday_snapshot(repo_key, params.report_date)
    stars_delta = (stars - yesterday_snap["stars"]) if yesterday_snap else None
    forks_delta = (forks - yesterday_snap["forks"]) if yesterday_snap else None

    # 2) PR：sort=updated desc + 整页过旧时停止翻页
    pulls_config = PaginatedApiConfig(
        path_template="repos/%s/%s/pulls?state=all&sort=updated&direction=desc&per_page=100&page=%%s" % (params.owner, params.repo),
        api_config=api_config,
        page_stop=_all_updated_before,
    )
    pulls_recent, err = _paginated_api_get(pulls_config)
    if err:
        return {STR_REPO: repo_key, STR_FETCH_ERROR: "pulls: " + err}, err

    prs_merged_today = [p for p in pulls_recent if is_same_day(p.get("merged_at") or "")]
    prs_closed_today = [p for p in pulls_recent if is_same_day(p.get("closed_at") or "")]
    prs_opened_today = [p for p in pulls_recent if is_same_day(p.get(STR_CREATED_AT) or "")]
    pr_merge_rate = (len(prs_merged_today) / len(prs_closed_today)) if prs_closed_today else None

    # 陈旧 PR：仅拉 state=open，按 created asc，全页都新于 cutoff 时停止
    pulls_open_config = PaginatedApiConfig(
        path_template="repos/%s/%s/pulls?state=open&sort=created&direction=asc&per_page=100&page=%%s" % (params.owner, params.repo),
        api_config=api_config,
        page_stop=_all_created_after_cutoff,
    )
    pulls_open, _ = _paginated_api_get(pulls_open_config)
    stale_prs_count = sum(
        1 for p in pulls_open
        if (lambda d: d is not None and d < stale_cutoff)(_parse_iso_to_date(p.get(STR_CREATED_AT) or "", params.tz_offset))
    )

    # 当日合并 PR 拉详情
    code_additions = 0
    code_deletions = 0
    major_prs = []
    merged_prs_for_ai = []
    contributors = set()

    for p in prs_merged_today:
        num = p.get(STR_NUMBER)
        user = p.get(STR_USER) or {}
        uname = user.get(STR_USERNAME) or user.get(STR_LOGIN) or ""
        if uname:
            contributors.add(uname)
        detail, de = api_get(api_config, "repos/%s/%s/pulls/%s" % (params.owner, params.repo, num))
        if de:
            continue
        add = int(detail.get(STR_ADDITIONS) or 0)
        dec = int(detail.get("deletions") or 0)
        code_additions += add
        code_deletions += dec
        if add > major_threshold:
            major_prs.append({STR_NUMBER: num, STR_TITLE: (detail.get(STR_TITLE) or "")[:200], STR_ADDITIONS: add})
        merged_prs_for_ai.append({STR_NUMBER: num, STR_TITLE: (detail.get(STR_TITLE) or "")[:500], "body": (detail.get("body") or "")[:body_max]})

    for p in prs_opened_today:
        uname = ((p.get(STR_USER) or {}).get(STR_USERNAME) or (p.get(STR_USER) or {}).get(STR_LOGIN) or "")
        if uname:
            contributors.add(uname)

    # 3) Issue：使用 since 参数只拉近期有更新的
    issues_config = PaginatedApiConfig(
        path_template="repos/%s/%s/issues?state=all&since=%s&per_page=100&page=%%s" % (params.owner, params.repo, since_utc),
        api_config=api_config,
    )
    issues_recent, err = _paginated_api_get(issues_config)
    if err:
        return {STR_REPO: repo_key, STR_FETCH_ERROR: "issues: " + err}, err

    issues_opened_today = [i for i in issues_recent if is_same_day(i.get(STR_CREATED_AT) or "")]
    issues_closed_today = [i for i in issues_recent if is_same_day(i.get("closed_at") or "")]
    issues_opened_today_list = [{STR_NUMBER: i.get(STR_NUMBER), STR_TITLE: (i.get(STR_TITLE) or "")[:200]} for i in issues_opened_today]
    issues_closed_today_list = [{STR_NUMBER: i.get(STR_NUMBER), STR_TITLE: (i.get(STR_TITLE) or "")[:200]} for i in issues_closed_today]
    for i in issues_opened_today + issues_closed_today:
        uname = ((i.get(STR_USER) or {}).get(STR_USERNAME) or (i.get(STR_USER) or {}).get(STR_LOGIN) or "")
        if uname:
            contributors.add(uname)

    # 陈旧 Issue：state=open，按 created asc，全页都新于 cutoff 时停止
    issues_open_config = PaginatedApiConfig(
        path_template="repos/%s/%s/issues?state=open&sort=created&direction=asc&per_page=100&page=%%s" % (params.owner, params.repo),
        api_config=api_config,
        page_stop=_all_created_after_cutoff,
    )
    issues_open, _ = _paginated_api_get(issues_open_config)

    def _is_stale_issue(issue):
        d = _parse_iso_to_date(issue.get(STR_CREATED_AT) or "", params.tz_offset)
        if d is None or d >= stale_cutoff:
            return False
        title_lower = (issue.get(STR_TITLE) or "").lower()
        return not any(kw and kw in title_lower for kw in exclude_kw)

    stale_issues_count = sum(1 for i in issues_open if _is_stale_issue(i))

    # 4) 评论：since 参数只拉今日评论
    comments_config = PaginatedApiConfig(
        path_template="repos/%s/%s/issues/comments?since=%s&per_page=100&page=%%s" % (params.owner, params.repo, since_utc),
        api_config=api_config,
    )
    all_comments, _ = _paginated_api_get(comments_config)
    issue_comment_count_today = {}
    for c in all_comments:
        if is_same_day(c.get(STR_CREATED_AT) or ""):
            issue_num = c.get("issue_id") or c.get("issue_number") or 0
            if issue_num:
                issue_comment_count_today[issue_num] = issue_comment_count_today.get(issue_num, 0) + 1
            uname = ((c.get(STR_USER) or {}).get(STR_USERNAME) or (c.get(STR_USER) or {}).get(STR_LOGIN) or "")
            if uname:
                contributors.add(uname)

    hot_issues = []
    for i in issues_recent:
        num = i.get(STR_NUMBER)
        cnt = issue_comment_count_today.get(num, 0)
        if cnt >= hot_threshold:
            hot_issues.append({STR_NUMBER: num, STR_TITLE: (i.get(STR_TITLE) or "")[:200], "comments_today": cnt})

    active_contributors = len(contributors)

    write_snapshot(params.report_date, repo_key, stars, forks, open_issues_count)
    today_for_db = {
        STR_PRS_MERGED: len(prs_merged_today),
        STR_PRS_CLOSED: len(prs_closed_today),
        STR_ISSUES_OPENED: len(issues_opened_today),
        STR_ISSUES_CLOSED: len(issues_closed_today),
        STR_CODE_ADDITIONS: code_additions,
        STR_CODE_DELETIONS: code_deletions,
        STR_ACTIVE_CONTRIBUTORS: active_contributors,
        "stale_issues_count": stale_issues_count,
        "stale_prs_count": stale_prs_count,
    }
    metrics_data = DailyMetricsData(
        report_date=params.report_date,
        repo=repo_key,
        today=today_for_db,
        major_prs=major_prs,
        hot_issues=hot_issues,
        merged_prs_for_ai=merged_prs_for_ai,
    )
    write_daily_metrics(metrics_data)

    prs_opened_today_list = [{STR_NUMBER: p.get(STR_NUMBER), STR_TITLE: (p.get(STR_TITLE) or "")[:200]} for p in prs_opened_today]
    merged_prs_today_list = [{STR_NUMBER: p.get(STR_NUMBER), STR_TITLE: (p.get(STR_TITLE) or "")[:200],
                              STR_ADDITIONS: next((m[STR_ADDITIONS] for m in major_prs if m[STR_NUMBER] == p.get(STR_NUMBER)), None)}
                             for p in prs_merged_today]

    return {
        STR_REPO: repo_key,
        STR_FETCH_ERROR: None,
        STR_REPO_SUMMARY: {
            "stars": stars, "stars_delta": stars_delta,
            "forks": forks, "forks_delta": forks_delta,
            "open_issues": open_issues_count,
        },
        STR_TODAY: {
            STR_PRS_MERGED: len(prs_merged_today),
            STR_PRS_CLOSED: len(prs_closed_today),
            STR_PRS_OPENED: len(prs_opened_today),
            "pr_merge_rate": round(pr_merge_rate, 2) if pr_merge_rate is not None else None,
            STR_ISSUES_OPENED: len(issues_opened_today),
            STR_ISSUES_CLOSED: len(issues_closed_today),
            STR_ISSUES_OPENED_TODAY_LIST: issues_opened_today_list,
            STR_ISSUES_CLOSED_TODAY_LIST: issues_closed_today_list,
            STR_PRS_OPENED_TODAY_LIST: prs_opened_today_list,
            STR_MERGED_PRS_TODAY_LIST: merged_prs_today_list,
            STR_ACTIVE_CONTRIBUTORS: active_contributors,
            STR_CODE_ADDITIONS: code_additions,
            STR_CODE_DELETIONS: code_deletions,
            STR_MAJOR_PRS: major_prs,
            STR_HOT_ISSUES: hot_issues,
            "stale_issues_count": stale_issues_count,
            "stale_prs_count": stale_prs_count,
        },
        STR_MERGED_PRS_FOR_AI: merged_prs_for_ai,
    }, None


def _merge_two_daily_repo_results(data1, data2):
    """将两天的 fetch_one_repo 结果合并为一份周期数据（用于周/月无 DB 数据时用首尾日 API 补拉）。"""
    t1 = data1.get(STR_TODAY) or {}
    t2 = data2.get(STR_TODAY) or {}
    prs_merged = t1.get(STR_PRS_MERGED, 0) + t2.get(STR_PRS_MERGED, 0)
    prs_closed = t1.get(STR_PRS_CLOSED, 0) + t2.get(STR_PRS_CLOSED, 0)
    return {
        STR_REPO: data2.get(STR_REPO) or data1.get(STR_REPO),
        STR_FETCH_ERROR: None,
        STR_REPO_SUMMARY: data2.get(STR_REPO_SUMMARY) or data1.get(STR_REPO_SUMMARY),
        STR_TODAY: {
            STR_PRS_MERGED: prs_merged,
            STR_PRS_CLOSED: prs_closed,
            STR_PRS_OPENED: t1.get(STR_PRS_OPENED, 0) + t2.get(STR_PRS_OPENED, 0),
            "pr_merge_rate": round(prs_merged / prs_closed, 2) if prs_closed else None,
            STR_ISSUES_OPENED: t1.get(STR_ISSUES_OPENED, 0) + t2.get(STR_ISSUES_OPENED, 0),
            STR_ISSUES_CLOSED: t1.get(STR_ISSUES_CLOSED, 0) + t2.get(STR_ISSUES_CLOSED, 0),
            STR_ISSUES_OPENED_TODAY_LIST: (t1.get(STR_ISSUES_OPENED_TODAY_LIST) or []) + (t2.get(STR_ISSUES_OPENED_TODAY_LIST) or []),
            STR_ISSUES_CLOSED_TODAY_LIST: (t1.get(STR_ISSUES_CLOSED_TODAY_LIST) or []) + (t2.get(STR_ISSUES_CLOSED_TODAY_LIST) or []),
            STR_PRS_OPENED_TODAY_LIST: (t1.get(STR_PRS_OPENED_TODAY_LIST) or []) + (t2.get(STR_PRS_OPENED_TODAY_LIST) or []),
            STR_MERGED_PRS_TODAY_LIST: (t1.get(STR_MERGED_PRS_TODAY_LIST) or []) + (t2.get(STR_MERGED_PRS_TODAY_LIST) or []),
            STR_ACTIVE_CONTRIBUTORS: max(t1.get(STR_ACTIVE_CONTRIBUTORS, 0), t2.get(STR_ACTIVE_CONTRIBUTORS, 0)),
            STR_CODE_ADDITIONS: t1.get(STR_CODE_ADDITIONS, 0) + t2.get(STR_CODE_ADDITIONS, 0),
            STR_CODE_DELETIONS: t1.get(STR_CODE_DELETIONS, 0) + t2.get(STR_CODE_DELETIONS, 0),
            STR_MAJOR_PRS: (t1.get(STR_MAJOR_PRS) or []) + (t2.get(STR_MAJOR_PRS) or []),
            STR_HOT_ISSUES: (t1.get(STR_HOT_ISSUES) or []) + (t2.get(STR_HOT_ISSUES) or []),
            "stale_issues_count": t2.get("stale_issues_count", 0),
            "stale_prs_count": t2.get("stale_prs_count", 0),
        },
        STR_MERGED_PRS_FOR_AI: (data1.get(STR_MERGED_PRS_FOR_AI) or []) + (data2.get(STR_MERGED_PRS_FOR_AI) or []),
        "daily_summaries_for_ai": [],
    }


def _week_monday(d):
    """某日所在周的周一（ISO 周一为一周开始）。"""
    wd = d.weekday()
    return d - timedelta(days=wd)


def _month_start(d):
    """某日所在月的 1 号。"""
    return d.replace(day=1)


def _month_end(d):
    """某日所在月的最后一天。"""
    if d.month == 12:
        return d.replace(day=31)
    return (d.replace(month=d.month + 1, day=1)) - timedelta(days=1)


def _build_report_from_db_period(period_start, period_end, cfg, period_type):
    """周报/月报通用：从 DB 读取 [period_start, period_end] 区间每日指标与摘要并聚合。
    period_type 为 "week" 或 "month"，决定写入的汇总表和 period_type 字段。
    某仓无数据时标记 fetch_error，由 main() 用 API 补拉。
    """
    start_str = period_start.strftime("%Y-%m-%d")
    end_str = period_end.strftime("%Y-%m-%d")
    repos = [r.strip() for r in (cfg.get(STR_REPOS) or []) if "/" in r.strip()]
    max_repos = cfg.get("max_repos_per_report") or 50
    repos = repos[:max_repos]
    timezone_str = cfg.get("timezone") or "Asia/Shanghai"

    metrics_table = "weekly_metrics" if period_type == STR_WEEK else "monthly_metrics"
    date_column = "week_start_date" if period_type == STR_WEEK else "month_start_date"
    no_data_msg = "无该周每日数据，请先生成日报" if period_type == STR_WEEK else "无该月每日数据，请先生成日报"

    conn = sqlite3.connect(str(DB_PATH))
    repos_data = []
    global_prs_merged = 0
    global_prs_closed = 0
    global_issues_opened = 0
    global_issues_closed = 0
    global_stale_issues = 0
    global_stale_prs = 0
    global_stars = 0
    global_forks = 0
    repos_active = 0

    for repo_spec in repos:
        rows = conn.execute(
            """SELECT date, prs_merged, prs_closed, issues_opened, issues_closed,
                      code_additions, code_deletions, active_contributors,
                      stale_issues_count, stale_prs_count, COALESCE(prs_opened, 0)
               FROM daily_metrics WHERE repo = ? AND date >= ? AND date <= ? ORDER BY date""",
            (repo_spec, start_str, end_str),
        ).fetchall()
        if not rows:
            repos_data.append({STR_REPO: repo_spec, STR_FETCH_ERROR: no_data_msg})
            continue
        prs_merged = sum(r[1] for r in rows)
        prs_closed = sum(r[2] for r in rows)
        issues_opened = sum(r[3] for r in rows)
        issues_closed = sum(r[4] for r in rows)
        code_additions = sum(r[5] for r in rows)
        code_deletions = sum(r[6] for r in rows)
        active_contributors = max(r[7] for r in rows) if rows else 0
        stale_issues_count = rows[-1][8] if rows else 0
        stale_prs_count = rows[-1][9] if rows else 0
        prs_opened = sum(r[10] for r in rows)
        pr_merge_rate = round(prs_merged / prs_closed, 2) if prs_closed else None
        summary_rows = conn.execute(
            "SELECT date, summary_text FROM daily_summaries WHERE repo = ? AND date >= ? AND date <= ? ORDER BY date",
            (repo_spec, start_str, end_str),
        ).fetchall()
        daily_summaries_for_ai = [{STR_DATE: r[0], "summary": r[1]} for r in summary_rows]
        snap_start = conn.execute("SELECT stars, forks FROM snapshots WHERE date = ? AND repo = ?", (start_str, repo_spec)).fetchone()
        snap_end = conn.execute("SELECT stars, forks FROM snapshots WHERE date = ? AND repo = ?", (end_str, repo_spec)).fetchone()
        stars = snap_end[0] if snap_end else 0
        forks = snap_end[1] if snap_end else 0
        stars_delta = (snap_end[0] - snap_start[0]) if (snap_start and snap_end) else None
        forks_delta = (snap_end[1] - snap_start[1]) if (snap_start and snap_end) else None
        conn.execute(
            "INSERT OR REPLACE INTO %s (%s, repo, prs_merged, prs_closed, issues_opened, issues_closed,"
            " code_additions, code_deletions, active_contributors, stale_issues_count, stale_prs_count, stars_delta)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)" % (metrics_table, date_column),
            (start_str, repo_spec, prs_merged, prs_closed, issues_opened, issues_closed,
             code_additions, code_deletions, active_contributors, stale_issues_count, stale_prs_count, stars_delta),
        )
        global_prs_merged += prs_merged
        global_prs_closed += prs_closed
        global_issues_opened += issues_opened
        global_issues_closed += issues_closed
        global_stale_issues += stale_issues_count
        global_stale_prs += stale_prs_count
        global_stars += stars
        global_forks += forks
        if prs_merged + issues_opened + issues_closed > 0:
            repos_active += 1
        repos_data.append({
            STR_REPO: repo_spec,
            STR_FETCH_ERROR: None,
            STR_REPO_SUMMARY: {"stars": stars, "stars_delta": stars_delta, "forks": forks, "forks_delta": forks_delta, "open_issues": None},
            STR_TODAY: {
                STR_PRS_MERGED: prs_merged, STR_PRS_CLOSED: prs_closed, STR_PRS_OPENED: prs_opened, "pr_merge_rate": pr_merge_rate,
                STR_ISSUES_OPENED: issues_opened, STR_ISSUES_CLOSED: issues_closed,
                STR_ISSUES_OPENED_TODAY_LIST: [], STR_ISSUES_CLOSED_TODAY_LIST: [],
                STR_PRS_OPENED_TODAY_LIST: [], STR_MERGED_PRS_TODAY_LIST: [],
                STR_ACTIVE_CONTRIBUTORS: active_contributors, STR_CODE_ADDITIONS: code_additions, STR_CODE_DELETIONS: code_deletions,
                STR_MAJOR_PRS: [], STR_HOT_ISSUES: [], "stale_issues_count": stale_issues_count, "stale_prs_count": stale_prs_count,
            },
            STR_MERGED_PRS_FOR_AI: [],
            "daily_summaries_for_ai": daily_summaries_for_ai,
        })

    global_summary_rows = conn.execute(
        "SELECT date, summary_text FROM daily_summaries WHERE repo = ? AND date >= ? AND date <= ? ORDER BY date",
        ("__global__", start_str, end_str),
    ).fetchall()
    global_daily_summaries_for_ai = [{STR_DATE: r[0], "summary": r[1]} for r in global_summary_rows]
    conn.commit()
    conn.close()
    return {
        "period_type": period_type,
        STR_DATE: start_str,
        "date_start": start_str,
        "date_end": end_str,
        "timezone": timezone_str,
        "global": {
            "repos_total": len(repos),
            "repos_active_today": repos_active,
            "stars_total": global_stars,
            "stars_delta_today": None,
            "issues_opened_today": global_issues_opened,
            "issues_closed_today": global_issues_closed,
            "prs_merged_today": global_prs_merged,
            "prs_closed_today": global_prs_closed,
            "prs_opened_today": 0,
            "forks_total": global_forks,
            "forks_delta_today": None,
            "stale_issues_total": global_stale_issues,
            "stale_prs_total": global_stale_prs,
            "fetch_errors": [],
        },
        "global_daily_summaries_for_ai": global_daily_summaries_for_ai,
        STR_REPOS: repos_data,
    }


def build_report_from_db_week(week_start, cfg):
    """周报：从 DB 聚合 [周一, 周日] 指标。"""
    return _build_report_from_db_period(week_start, week_start + timedelta(days=6), cfg, STR_WEEK)


def build_report_from_db_month(month_start, cfg):
    """月报：从 DB 聚合 [月首, 月末] 指标。"""
    return _build_report_from_db_period(month_start, _month_end(month_start), cfg, STR_MONTH)


GLOBAL_REPO = "__global__"
DEFAULT_DAILY_TEMPLATE = SKILL_ROOT / "resources" / "daily_report.md"
DEFAULT_WEEKLY_TEMPLATE = SKILL_ROOT / "resources" / "weekly_report.md"
DEFAULT_MONTHLY_TEMPLATE = SKILL_ROOT / "resources" / "monthly_report.md"
_PERIOD_TEMPLATES = {STR_DAY: DEFAULT_DAILY_TEMPLATE, STR_WEEK: DEFAULT_WEEKLY_TEMPLATE, STR_MONTH: DEFAULT_MONTHLY_TEMPLATE}
DEFAULT_TEMP_DIR = SKILL_ROOT / "temp_dir"


def _print_json(data, save_to=None):
    """以 UTF-8 安全方式输出 JSON。
    save_to 有值时：完整 JSON 写入文件，stdout 仅输出简短状态（避免大量中文 JSON 在 Windows 管道乱码）。
    save_to 无值时：完整 JSON 输出到 stdout。
    """
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if save_to:
        p = Path(save_to)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding=ENCODING_UTF8)
        brief = json.dumps({STR_STATUS: data.get(STR_STATUS, STR_OK), STR_SAVED_TO: str(p.resolve())}, ensure_ascii=False)
        logger.info(brief)
        return
    logger.info(text)


def _resolve_skill_path(p):
    """将相对路径解析为相对于 SKILL_ROOT 的绝对路径；绝对路径保持不变。"""
    if not p:
        return p
    pp = Path(p)
    if pp.is_absolute():
        return str(pp)
    return str(SKILL_ROOT / pp)


def _fmt(x):
    """格式化为报告中的显示值；None 转为 —。"""
    if x is None:
        return "—"
    return str(x)


def _md_issue_link(owner_repo, number, title=""):
    url = "https://gitcode.com/%s/issues/%s" % (owner_repo, number)
    if title:
        return "[#%s](%s) %s" % (number, url, title.strip())
    return "[#%s](%s)" % (number, url)


def _md_pr_link(owner_repo, number, title="", extra=""):
    url = "https://gitcode.com/%s/pulls/%s" % (owner_repo, number)
    parts = ["[#%s](%s)" % (number, url)]
    if title:
        parts.append(title.strip())
    if extra:
        parts.append(extra)
    return " ".join(parts)
