#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数模块 - 提取可独立测试的功能
"""

import re
import sys
import os
import json
import time
import logging
import urllib.request
import urllib.error
from urllib.parse import urlparse
from typing import List, Dict, Optional, Tuple
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stderr)

ENCODING_UTF8 = "utf-8"
MIME_TYPE_JPEG = "image/jpeg"
KEY_ERROR = "error"
STATUS_FAILED = "failed"
STATUS_OK = "ok"
STATUS_SKIPPED = "skipped"


def extract_image_urls(text: str) -> List[str]:
    """
    从文本中提取图片 URL
    
    支持格式：
    - Markdown: ![alt](url) 或 ![alt](url "title")
    - HTML: <img src="url">
    
    Args:
        text: 要解析的文本
    
    Returns:
        去重后的 URL 列表（最多 10 个）
    """
    if not text or not isinstance(text, str):
        return []
    
    urls = []
    
    # Markdown: ![alt](url) 或 ![alt](url "title") - 只提取 URL 部分
    # 修复：处理 URL 中包含空格和 title 的情况
    for match in re.finditer(r'!\[([^\]]*)\]\(([^\s")]+)(?:\s+["\'][^"\']*["\'])?\)', text):
        url = match.group(2).strip()
        if url and url not in urls:
            urls.append(url)
    
    # HTML: <img src="url">
    html_img_pattern = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)
    for match in html_img_pattern.finditer(text):
        url = match.group(1).strip()
        if url and url not in urls:
            urls.append(url)
    
    return urls[:10]


def download_image(url: str, temp_dir: Path, max_retries: int = 3, index: int = 0) -> Optional[Path]:
    """
    下载图片到本地
    
    Args:
        url: 图片 URL
        temp_dir: 临时目录
        max_retries: 最大重试次数
        index: 图片索引，用于生成唯一文件名
    
    Returns:
        下载后的本地路径，失败返回 None
    """
    url = url.strip()
    url = ''.join(char for char in url if 32 <= ord(char) < 127)
    
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path) or "image.png"
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    if not filename or filename == '.':
        filename = "image.png"
    
    filename = f"{index}_{filename}"
    
    local_path = temp_dir / filename
    
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
                }
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                with open(local_path, 'wb') as f:
                    f.write(response.read())
            return local_path
        except Exception as e:
            logging.warning("Failed to download image %s (attempt %d/%d): %s", url, attempt, max_retries, e)
            if attempt == max_retries:
                return None
    
    return None


def image_to_base64(image_path: Path) -> Optional[str]:
    """
    将图片转换为 base64 编码字符串（仅使用标准库）
    
    注意：此函数不进行图片缩放，仅做 base64 编码
    如需缩放，建议在调用前使用其他工具处理
    
    Args:
        image_path: 图片本地路径
    
    Returns:
        base64 编码的字符串（带 data URI 前缀），失败返回 None
    """
    import base64
    
    try:
        with open(image_path, 'rb') as f:
            img_bytes = f.read()
        
        ext = image_path.suffix.lower()
        
        mime_type = MIME_TYPE_JPEG
        
        if img_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            mime_type = 'image/png'
        elif img_bytes.startswith(b'GIF87a') or img_bytes.startswith(b'GIF89a'):
            mime_type = 'image/gif'
        elif img_bytes.startswith(b'RIFF') and img_bytes[8:12] == b'WEBP':
            mime_type = 'image/webp'
        elif img_bytes.startswith(b'BM'):
            mime_type = 'image/bmp'
        elif img_bytes.startswith(b'\xff\xd8\xff'):
            mime_type = 'image/jpeg'
        elif ext == '.png':
            mime_type = 'image/png'
        elif ext == '.gif':
            mime_type = 'image/gif'
        elif ext == '.webp':
            mime_type = 'image/webp'
        elif ext == '.bmp':
            mime_type = 'image/bmp'
        elif ext in ['.jpg', '.jpeg']:
            mime_type = 'image/jpeg'
        
        base64_str = base64.b64encode(img_bytes).decode(ENCODING_UTF8)
        
        return f"data:{mime_type};base64,{base64_str}"
        
    except Exception as e:
        logging.warning("Failed to convert image to base64 %s: %s", image_path, e)
        return None


def process_issue_images(issue_body: str, temp_dir: Path, max_images: int = 5) -> List[Dict]:
    """
    处理 Issue 中的图片：下载并转换为 base64
    
    Args:
        issue_body: Issue 正文内容
        temp_dir: 临时目录
        max_images: 最大处理图片数量
    
    Returns:
        图片信息列表，每项包含：
        - url: 原始 URL
        - local_path: 本地路径
        - base64: base64 编码（带 data URI 前缀）
        - size: 文件大小（字节）
    """
    image_urls = extract_image_urls(issue_body)
    if not image_urls:
        return []
    
    results = []
    for i, url in enumerate(image_urls[:max_images]):
        local_path = download_image(url, temp_dir)
        if not local_path:
            continue
        
        base64_data = image_to_base64(local_path)
        if not base64_data:
            continue
        
        file_size = local_path.stat().st_size
        
        results.append({
            'url': url,
            'local_path': str(local_path),
            'base64': base64_data,
            'size': file_size
        })
        
        logging.info("Processed image %d/%d: %s -> %d bytes", i+1, min(len(image_urls), max_images), url, file_size)
    
    return results


def deepwiki_query(repo: str, question: str, base_timeout: int = 120, max_retries: int = 3) -> Tuple[str, str]:
    """
    调用 DeepWiki MCP 查询
    
    Args:
        repo: 仓库名，格式为 "owner/repo"
        question: 查询问题
        base_timeout: 超时时间（秒）
        max_retries: 最大重试次数
    
    Returns:
        (answer, status) 元组
        - answer: DeepWiki 返回的答案
        - status: "ok", "failed", "skipped"
    """
    if "/" not in repo:
        return "", STATUS_SKIPPED

    class DeepWikiMCPClient:
        def __init__(self, timeout: int = 120, max_retries: int = 3):
            self.base_url = "https://mcp.deepwiki.com/mcp"
            self.request_id = 0
            self.initialized = False
            self.timeout = timeout
            self.max_retries = max_retries

        @staticmethod
        def _parse_sse_response(data: str) -> dict:
            result = {}
            for line in data.split('\n'):
                if line.startswith('data:'):
                    try:
                        result = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        pass
            return result

        def ask_question(self, repo: str, question: str) -> dict:
            if not self.initialized:
                self.initialize()
            return self._make_request("tools/call", {
                "name": "ask_question",
                "arguments": {
                    "repoName": repo,
                    "question": question
                }
            })

        def initialize(self) -> dict:
            result = self._make_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "gitcode-issue-reply",
                    "version": "1.4.1"
                }
            })
            if "result" in result:
                self.initialized = True
                self._send_initialized_notification()
            return result

        def _make_request(self, method: str, params: dict = None) -> dict:
            self.request_id += 1
            payload = {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "method": method,
                "params": params or {}
            }
            data = json.dumps(payload).encode(ENCODING_UTF8)
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/event-stream',
                'User-Agent': 'gitcode-issue-reply/1.4.1',
            }
            req = urllib.request.Request(
                self.base_url,
                data=data,
                headers=headers,
                method='POST'
            )
            last_error = None
            for attempt in range(self.max_retries + 1):
                try:
                    with urllib.request.urlopen(req, timeout=self.timeout) as response:
                        content_type = response.headers.get('Content-Type', '')
                        raw_data = response.read().decode(ENCODING_UTF8)
                        if 'text/event-stream' in content_type:
                            return self._parse_sse_response(raw_data)
                        else:
                            return json.loads(raw_data)
                except urllib.error.HTTPError as e:
                    last_error = f"HTTP {e.code}: {e.reason}"
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)
                except urllib.error.URLError as e:
                    last_error = str(e)
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)
                except json.JSONDecodeError as e:
                    last_error = f"JSON decode error: {e}"
                    break
                except Exception as e:
                    last_error = str(e)
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)
            return {KEY_ERROR: f"Request failed after {self.max_retries + 1} attempts: {last_error}"}

        def _send_initialized_notification(self):
            self._make_request("notifications/initialized", {})

    def extract_text(result) -> str:
        if isinstance(result, dict):
            content = result.get("content", [])
            if content and isinstance(content, list):
                texts = [item.get("text", "") for item in content
                         if isinstance(item, dict) and item.get("type") == "text"]
                return "\n".join(texts)
            if "result" in result.get("structuredContent", {}):
                return result["structuredContent"]["result"]
        return str(result)

    try:
        client = DeepWikiMCPClient(timeout=base_timeout, max_retries=max_retries)
        
        init_result = client.initialize()
        if KEY_ERROR in init_result:
            logging.warning("DeepWiki init error: %s", init_result[KEY_ERROR])
            return "", STATUS_FAILED
        
        data = client.ask_question(repo, question)
        if KEY_ERROR in data:
            logging.warning("DeepWiki query error: %s", data[KEY_ERROR])
            return "", STATUS_FAILED
        
        raw_result = data.get("result", {})
        answer_text = extract_text(raw_result)
        
        if not answer_text or answer_text.strip() == "{}":
            answer_text = (
                f"DeepWiki returned empty result. The question may not match the knowledge base, "
                f"or the repository may not be indexed. Visit https://deepwiki.com/{repo} for docs."
            )
        
        return answer_text, STATUS_OK

    except Exception as e:
        logging.warning("DeepWiki query failed: %s", e)
        return "", STATUS_FAILED


if __name__ == "__main__":
    logging.info("Testing extract_image_urls...")
    
    test_text = """
    ![image.png](https://example.com/image.png 'image.png')
    ![alt text](https://example.com/image2.png)
    <img src="https://example.com/image3.png">
    ![image with space](https://example.com/image 4.png "title")
    """
    urls = extract_image_urls(test_text)
    logging.info("Extracted %d URLs:", len(urls))
    for url in urls:
        logging.info("  - %s", url)
    
    logging.info("Testing deepwiki_query... (Skipped - requires network)")
