# GitCode API文档参考

本文档包含GitCode API的相关端点说明，用于PR安全审查技能。

## API端点

### 1. 获取Pull Request列表

**端点：**
```
GET https://gitcode.com/api/v5/repos/{owner}/{repo}/pulls
```

**请求头：**
```
Authorization: Bearer {token}
```

**查询参数：**
- `state`: PR状态，可选值：`open`, `closed`, `all`，默认为`open`
- `page`: 页码，默认为1
- `per_page`: 每页数量，默认为30，最大为100

**响应示例：**
```json
[
  {
    "id": 1,
    "number": 1,
    "state": "open",
    "title": "PR标题",
    "body": "PR描述",
    "user": {
      "login": "用户名",
      "id": 123
    },
    "head": {
      "label": "分支名",
      "ref": "分支名",
      "sha": "commit SHA",
      "repo": {
        "id": 456,
        "name": "仓库名",
        "full_name": "owner/repo"
      }
    },
    "base": {
      "label": "分支名",
      "ref": "分支名",
      "sha": "commit SHA",
      "repo": {
        "id": 456,
        "name": "仓库名",
        "full_name": "owner/repo"
      }
    },
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "merged_at": null,
    "html_url": "https://gitcode.com/owner/repo/pull/1"
  }
]
```

**参考文档：**
https://docs.gitcode.com/docs/apis/get-api-v-5-repos-owner-repo-pulls

### 2. 获取PR的文件变更

**端点：**
```
GET https://gitcode.com/api/v5/repos/{owner}/{repo}/pulls/{number}/files
```

**请求头：**
```
Authorization: Bearer {token}
```

**路径参数：**
- `owner`: 仓库所有者用户名或组织名
- `repo`: 仓库名称
- `number`: PR编号

**响应示例：**
```json
[
  {
    "sha": "文件SHA",
    "filename": "src/main.py",
    "status": "modified",
    "additions": 10,
    "deletions": 5,
    "changes": 15,
    "blob_url": "https://gitcode.com/owner/repo/blob/commit/sha/src/main.py",
    "raw_url": "https://gitcode.com/owner/repo/raw/commit/sha/src/main.py",
    "contents_url": "https://gitcode.com/api/v5/repos/owner/repo/contents/src/main.py?ref=commit/sha",
    "patch": "@@ -1,4 +1,5 @@\n-old line\n+new line\n unchanged line"
  }
]
```

**文件状态（status）：**
- `added`: 新增文件
- `modified`: 修改文件
- `deleted`: 删除文件
- `renamed`: 重命名文件

**参考文档：**
https://docs.gitcode.com/docs/apis/get-api-v-5-repos-owner-repo-pulls-number-files-json

### 3. 在PR中创建评论

**端点：**
```
POST https://gitcode.com/api/v5/repos/{owner}/{repo}/pulls/{number}/comments
```

**请求头：**
```
Authorization: Bearer {token}
Content-Type: application/json
```

**路径参数：**
- `owner`: 仓库所有者用户名或组织名
- `repo`: 仓库名称
- `number`: PR编号

**请求体：**
```json
{
  "body": "评论内容",
  "commit_id": "commit SHA",
  "path": "文件路径",
  "position": 10
}
```

**请求体参数说明：**
- `body`: 评论内容，支持Markdown格式
- `commit_id`: PR的最新commit ID
- `path`: 文件路径
- `position`: 代码行号（从1开始）

**响应示例：**
```json
{
  "id": 1,
  "body": "评论内容",
  "commit_id": "commit SHA",
  "path": "文件路径",
  "position": 10,
  "user": {
    "login": "用户名",
    "id": 123
  },
  "created_at": "2024-01-01T00:00:00Z",
  "html_url": "https://gitcode.com/owner/repo/pull/1#discussion_r1"
}
```

**参考文档：**
https://docs.gitcode.com/docs/apis/post-api-v-5-repos-owner-repo-pulls-number-comments

## 认证

所有API请求都需要在请求头中包含认证信息：

```
Authorization: Bearer {token}
```

其中 `{token}` 是GitCode访问令牌（Personal Access Token）。

## 错误处理

API可能返回以下HTTP状态码：

- `200 OK`: 请求成功
- `401 Unauthorized`: 认证失败，token无效或过期
- `403 Forbidden`: 权限不足
- `404 Not Found`: 资源不存在
- `422 Unprocessable Entity`: 请求参数错误
- `429 Too Many Requests`: 请求频率超限
- `500 Internal Server Error`: 服务器内部错误

错误响应示例：
```json
{
  "message": "错误信息",
  "documentation_url": "https://docs.gitcode.com"
}
```

## 分页

对于可能返回大量数据的API端点（如获取PR列表），支持分页查询：

- `page`: 页码，从1开始
- `per_page`: 每页数量，默认为30，最大为100

示例查询第2页，每页50条记录：
```
GET https://gitcode.com/api/v5/repos/{owner}/{repo}/pulls?page=2&per_page=50
```

响应头包含分页信息：
```
Link: <https://gitcode.com/api/v5/repos/owner/repo/pulls?page=1>; rel="prev",
      <https://gitcode.com/api/v5/repos/owner/repo/pulls?page=3>; rel="next",
      <https://gitcode.com/api/v5/repos/owner/repo/pulls?page=1>; rel="first",
      <https://gitcode.com/api/v5/repos/owner/repo/pulls?page=10>; rel="last"
```
