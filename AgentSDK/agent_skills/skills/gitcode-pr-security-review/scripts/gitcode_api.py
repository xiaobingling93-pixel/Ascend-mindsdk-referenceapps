#!/usr/bin/env python3
"""
GitCode API交互工具
"""

import os
import sys
import json
import logging
import requests
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PullCommentRequest:
    """PR评论请求参数"""
    owner: str
    repo: str
    pull_number: int
    body: str
    commit_id: str
    path: str
    position: int


class GitCodeAPI:
    """GitCode API客户端"""
    
    DEFAULT_TIMEOUT = 30
    
    def __init__(self, token: Optional[str] = None, timeout: Optional[int] = None):
        """
        初始化GitCode API客户端
        
        Args:
            token: GitCode访问令牌，如果为None则从环境变量GITCODE_TOKEN获取
            timeout: 请求超时时间（秒），默认为30秒
        """
        self.token = token or os.environ.get('GITCODE_TOKEN')
        if not self.token:
            raise ValueError("GitCode token not found. Please set GITCODE_TOKEN environment variable or provide token.")
        
        self.base_url = "https://gitcode.com/api/v5"
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    @staticmethod
    def parse_repo_url(repo_url: str) -> Tuple[str, str]:
        """
        解析仓库URL，提取owner和repo
        
        Args:
            repo_url: 仓库URL
        
        Returns:
            (owner, repo) 元组
        
        Raises:
            ValueError: URL格式不正确
        """
        if repo_url.startswith("https://gitcode.com/"):
            path = repo_url[len("https://gitcode.com/"):]
        elif repo_url.startswith("https://gitcode.net/"):
            path = repo_url[len("https://gitcode.net/"):]
        else:
            raise ValueError(f"Unsupported URL format: {repo_url}")
        
        parts = path.split("/")
        if len(parts) < 2:
            raise ValueError(f"Invalid repository URL: {repo_url}")
        
        owner = parts[0]
        repo = parts[1]
        
        if repo.endswith(".git"):
            repo = repo[:-4]
        
        return owner, repo
    
    def get_pulls(self, owner: str, repo: str, state: str = "open") -> List[Dict[str, Any]]:
        """
        获取仓库的Pull Request列表
        
        Args:
            owner: 仓库所有者（用户名或组织名）
            repo: 仓库名称
            state: PR状态，默认为"open"
        
        Returns:
            PR列表
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls"
        params = {"state": state}
        
        response = requests.get(url, headers=self.headers, params=params, timeout=self.timeout)
        response.raise_for_status()
        
        return response.json()
    
    def get_pull_files(self, owner: str, repo: str, pull_number: int) -> List[Dict[str, Any]]:
        """
        获取PR的文件变更
        
        Args:
            owner: 仓库所有者（用户名或组织名）
            repo: 仓库名称
            pull_number: PR编号
        
        Returns:
            文件变更列表
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}/files"
        
        response = requests.get(url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        
        return response.json()
    
    def create_pull_comment(self, request: PullCommentRequest) -> Dict[str, Any]:
        """
        在PR中创建评论
        
        Args:
            request: PR评论请求参数
        
        Returns:
            创建的评论信息
        """
        url = f"{self.base_url}/repos/{request.owner}/{request.repo}/pulls/{request.pull_number}/comments"
        
        data = {
            "body": request.body,
            "commit_id": request.commit_id,
            "path": request.path,
            "position": request.position
        }
        
        response = requests.post(url, headers=self.headers, json=data, timeout=self.timeout)
        response.raise_for_status()
        
        return response.json()


def extract_code_from_patch(patch: str) -> Dict[int, str]:
    """
    从patch中提取新增的代码行
    
    Args:
        patch: Git diff patch内容
    
    Returns:
        字典，key为行号，value为代码内容
    """
    lines = {}
    current_line = 0
    
    for line in patch.split('\n'):
        if line.startswith('@@'):
            # 解析行号信息，例如：@@ -1,4 +1,5 @@
            parts = line.split()
            if len(parts) >= 3:
                new_file_info = parts[2]
                if new_file_info.startswith('+'):
                    # 提取起始行号
                    line_info = new_file_info[1:]
                    if ',' in line_info:
                        start_line = int(line_info.split(',')[0])
                    else:
                        start_line = int(line_info)
                    current_line = start_line
        elif line.startswith('+') and not line.startswith('++'):
            # 新增的代码行
            code = line[1:]
            lines[current_line] = code
            current_line += 1
        elif line.startswith('-') and not line.startswith('--'):
            # 删除的代码行，不记录
            pass
        elif line.startswith(' '):
            # 未变更的代码行
            current_line += 1
    
    return lines


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    if len(sys.argv) < 2:
        logger.info("Usage: python gitcode_api.py <command> [args...]")
        logger.info("Commands:")
        logger.info("  get-pulls <owner> <repo> [state]")
        logger.info("  get-files <owner> <repo> <pull_number>")
        logger.info("  parse-url <repo_url>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        if command == "get-pulls":
            if len(sys.argv) < 4:
                logger.info("Usage: python gitcode_api.py get-pulls <owner> <repo> [state]")
                sys.exit(1)
            
            owner = sys.argv[2]
            repo = sys.argv[3]
            state = sys.argv[4] if len(sys.argv) > 4 else "open"
            
            api = GitCodeAPI()
            pulls = api.get_pulls(owner, repo, state)
            logger.info(json.dumps(pulls, indent=2))
        
        elif command == "get-files":
            if len(sys.argv) < 5:
                logger.info("Usage: python gitcode_api.py get-files <owner> <repo> <pull_number>")
                sys.exit(1)
            
            owner = sys.argv[2]
            repo = sys.argv[3]
            pull_number = int(sys.argv[4])
            
            api = GitCodeAPI()
            files = api.get_pull_files(owner, repo, pull_number)
            logger.info(json.dumps(files, indent=2))
        
        elif command == "parse-url":
            if len(sys.argv) < 3:
                logger.info("Usage: python gitcode_api.py parse-url <repo_url>")
                sys.exit(1)
            
            repo_url = sys.argv[2]
            owner, repo = GitCodeAPI.parse_repo_url(repo_url)
            logger.info(f"Owner: {owner}")
            logger.info(f"Repo: {repo}")
        
        else:
            logger.error(f"Unknown command: {command}")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
