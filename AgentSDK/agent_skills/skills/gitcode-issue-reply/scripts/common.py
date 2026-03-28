#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared utilities for gitcode-issue-reply scripts."""

import sys
import re
import json
import os
import subprocess
import time
import logging

from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stderr)

GITCODE_API_BASE = "https://api.gitcode.com/api/v5"
API_RETRY_TIMES = 2
API_RETRY_INTERVAL = 2
ENCODING_UTF8 = "utf-8"
POWERSHELL_PATH = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"


def init_windows_encoding():
    """Reconfigure stdout/stderr to UTF-8 on Windows."""
    if sys.platform == "win32":
        try:
            import locale
            sys.stdout.reconfigure(encoding=ENCODING_UTF8)
            sys.stderr.reconfigure(encoding=ENCODING_UTF8)
            if sys.stdin:
                sys.stdin.reconfigure(encoding=ENCODING_UTF8)
        except Exception as e:
            logging.debug("Failed to reconfigure encoding: %s", e)
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleOutputCP(65001)
            kernel32.SetConsoleCP(65001)
        except Exception as e:
            logging.debug("Failed to set console code page: %s", e)


def print_json(data, output_file: str = None):
    """UTF-8 safe JSON output, bypassing Windows stdout encoding issues.
    
    Args:
        data: 要输出的数据
        output_file: 可选的文件路径，如果提供则同时写入文件
    """
    text = json.dumps(data, ensure_ascii=False, indent=2)
    
    if output_file:
        try:
            with open(output_file, 'w', encoding=ENCODING_UTF8) as f:
                f.write(text)
                f.write('\n')
        except Exception as e:
            logging.warning("Failed to write to %s: %s", output_file, e)
    
    try:
        sys.stdout.buffer.write(text.encode(ENCODING_UTF8))
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
    except (AttributeError, OSError):
        logging.info(text)


def get_token(user_provided_token=None):
    """
    Read GITCODE_TOKEN with priority:
    1. User directly provided token (user_provided_token parameter)
    2. Process environment variable GITCODE_TOKEN
    3. Windows User environment variable
    4. Windows Machine environment variable
    """
    if user_provided_token:
        return user_provided_token.strip()
    token = os.environ.get("GITCODE_TOKEN")
    if token:
        return token.strip()
    if sys.platform == "win32":
        for scope in ("User", "Machine"):
            try:
                out = subprocess.check_output(
                    [POWERSHELL_PATH, "-NoProfile", "-Command",
                     "[Environment]::GetEnvironmentVariable('GITCODE_TOKEN','%s')" % scope],
                    creationflags=0x08000000,
                    timeout=5,
                    stderr=subprocess.DEVNULL,
                )
                if out:
                    val = out.decode(ENCODING_UTF8, errors="replace").strip()
                    if val:
                        return val
            except Exception as e:
                logging.debug("Failed to read Windows environment variable (scope=%s): %s", scope, e)
    return None


def parse_issue_url(url):
    """Extract (owner, repo, number) from a GitCode issue URL."""
    m = re.search(r"gitcode\.com[/:]([^/]+)/([^/]+)/issues/(\d+)", url)
    if m:
        return m.group(1), m.group(2), int(m.group(3))
    raise ValueError("Cannot parse owner/repo/number from URL: " + str(url))


def _api_request(token, path, method="GET", data=None, retry_times=API_RETRY_TIMES, retry_interval=API_RETRY_INTERVAL):
    """Internal helper for GitCode API requests with retry and rate-limit handling."""
    url = (GITCODE_API_BASE.rstrip("/") + "/" + path.lstrip("/")).replace(" ", "%20")
    headers = {"PRIVATE-TOKEN": token}
    body = None
    if method == "POST" and data is not None:
        body = json.dumps(data).encode(ENCODING_UTF8)
        headers["Content-Type"] = "application/json"
    req = Request(url, data=body, method=method, headers=headers)
    last_err = None
    for attempt in range(retry_times + 1):
        try:
            with urlopen(req, timeout=30) as f:
                return json.loads(f.read().decode(ENCODING_UTF8))
        except HTTPError as e:
            last_err = e
            if e.code == 429:
                wait = 60
                try:
                    wait = int(e.headers.get("Retry-After", 60))
                except (TypeError, ValueError):
                    pass
                time.sleep(wait)
            elif attempt < retry_times:
                time.sleep(retry_interval)
            else:
                raise last_err from None
        except (URLError, OSError) as e:
            last_err = e
            if attempt < retry_times:
                time.sleep(retry_interval)
            else:
                raise last_err from None
    raise last_err from None


def api_get(token, path, retry_times=API_RETRY_TIMES, retry_interval=API_RETRY_INTERVAL):
    """GET request to GitCode API with retry and rate-limit handling."""
    return _api_request(token, path, method="GET", retry_times=retry_times, retry_interval=retry_interval)


def api_post(token, path, data, retry_times=API_RETRY_TIMES, retry_interval=API_RETRY_INTERVAL):
    """POST request to GitCode API with retry and rate-limit handling."""
    return _api_request(token, path, method="POST", data=data, retry_times=retry_times, retry_interval=retry_interval)
