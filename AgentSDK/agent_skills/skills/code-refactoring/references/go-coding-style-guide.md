# Go 语言编程指导

本文档列出 Go 语言编程规范，参考昇腾社区 Go 语言编程指导（建议稿）。

## 约定

**规则**：编程时必须遵守的约定(must)

**建议**：编程时应该遵守的约定(should)

**例外**：修改和适配外部开源代码、第三方代码时，应该遵守开源代码、第三方代码已有规范，保持风格统一。

---

## 1. 代码风格

### 1.1 命名

Go 使用大小写控制可见性：首字母大写=导出(public)，小写=私有(private)。

| 类型 | 导出 (UpperCamelCase) | 私有 (lowerCamelCase) |
|------|----------------------|----------------------|
| 文件 | lower_with_under.go | - |
| 包 | lower (简短单词，不用下划线或驼峰) | - |
| 类型 | UserInfo | userInfo |
| 函数 | GetUserInfo() | getUserInfo() |
| 常量 | MaxRetryCount | maxRetryCount |
| 变量 | UserName | userName |
| 结构体字段 | Name | name |

```go
// 导出
type UserInfo struct {
    Name string  // 大驼峰
    Age  int
}

func GetUserInfo(id int) (*UserInfo, error) { }

const MaxRetryCount = 3

// 私有
type userInfo struct {
    name string  // 小驼峰
}

func getUserInfo(id int) (*userInfo, error) { }

const maxRetryCount = 3

// 包命名
package user        // Good
package httpclient  // Good
package UserService // Bad
package http_client // Bad
```

### 1.2 格式

| 规则 | 要求 |
|------|------|
| 格式化 | 必须使用 gofmt |
| 行宽 | 不超过 120 字符 |
| 缩进 | Tab（Go 标准） |
| 大括号 | 左大括号不换行（K&R），这是 Go 语言规范 |
| 空行 | 最多连续 2 个，函数间 1 个 |

```go
// Good
func Foo(a int) {
    if a > 0 {
        doSomething()
    }
}

type MyStruct struct {
    Field1 string
    Field2 int
}

// Bad (编译错误)
func Foo(a int)
{
    // ...
}
```

### 1.3 注释

- 所有导出的标识符必须有注释，注释以标识符名称开头
- 代码注释置于对应代码的上方，注释符与内容间 1 空格
- 禁止 TODO/TBD/FIXME
- 不用的代码直接删除，不要注释掉
- 不要写空有格式的函数头注释

```go
// GetUserInfo 根据用户ID获取用户信息
// 如果用户不存在，返回 ErrUserNotFound 错误
func GetUserInfo(id int) (*UserInfo, error) { }

// UserInfo 表示用户信息
type UserInfo struct {
    Name string // 用户名
    Age  int    // 年龄
}

// MaxRetryCount 表示最大重试次数
const MaxRetryCount = 3
```

---

## 2. 通用编码

### 2.1 代码设计

- 函数结果优先使用返回值，避免全局变量
- 删除无效、冗余代码
- 使用 defer 确保资源释放

```go
// Good
func ReadFile(filename string) ([]byte, error) {
    f, err := os.Open(filename)
    if err != nil {
        return nil, err
    }
    defer f.Close()
    return ioutil.ReadAll(f)
}
```

### 2.2 包管理

| 规则 | 要求 |
|------|------|
| 包依赖 | 禁止循环依赖 |
| 未使用包 | 禁止导入 |
| import 分组 | 标准库、第三方库、本地包，空行分隔 |
| 依赖管理 | 使用 go.mod |

```go
import (
    // 标准库
    "fmt"
    "os"
    "time"
    
    // 第三方库
    "github.com/gin-gonic/gin"
    "golang.org/x/crypto/bcrypt"
    
    // 本地包
    "project/internal/config"
    "project/internal/db"
)
```

### 2.3 CGO

- 最小化 CGO 使用，优先纯 Go 实现
- 必须正确管理内存，使用 defer 释放
- 必须进行错误处理和边界检查
- 建议为CGO代码编写详细文档注释

```go
// Good
/*
#include <stdlib.h>
*/
import "C"
import "unsafe"

func ProcessString(s string) {
    cstr := C.CString(s)
    defer C.free(unsafe.Pointer(cstr))  // 确保释放
    C.someCFunction(cstr)
}

func ProcessBuffer(data []byte, maxSize int) error {
    if len(data) > maxSize {
        return errors.New("data too large")
    }
    // ...
}
```

### 2.4 常量

- 使用 const 定义，禁止用变量作为常量
- 禁止魔鬼数字
- 建议每个常量单一职责

```go
// Good
const MaxRetryCount = 3
const DefaultTimeout = 30 * time.Second
if count > MaxRetryCount { }

// Bad
var MaxRetryCount = 3
if count > 100 { }
```

### 2.5 表达式

- 使用括号明确操作符优先级

```go
// Good
if cond1 || (cond2 && cond3) { }

// Bad
if cond1 || cond2 && cond3 { }
```

### 2.6 控制语句

- switch 必须有 default 分支
- 尽早返回，减少嵌套

```go
// Good
func Process(data []byte) error {
    if len(data) == 0 {
        return errors.New("data is empty")
    }
    if err := validate(data); err != nil {
        return err
    }
    // 处理逻辑
    return nil
}

// Bad
func Process(data []byte) error {
    if len(data) > 0 {
        if err := validate(data); err == nil {
            // 处理逻辑
            return nil
        } else {
            return err
        }
    } else {
        return errors.New("data is empty")
    }
}
```

### 2.7 字符串

拼接超过3个字符串时，优先使用`strings.Builder`或`fmt.Sprintf`，避免使用`+`操作符进行大量拼接

```go
// Good
var builder strings.Builder
for _, s := range strings {
    builder.WriteString(s)
}
result := builder.String()

// Bad (大量拼接时)
result := ""
for _, s := range strings {
    result += s
}
```

### 2.8 结构体和接口

- 结构体字段：导出用大驼峰，私有用小驼峰
- 接口应该小而专注，避免过于庞大
- 初始化使用字段名，避免位置参数

```go
// Good
type User struct {
    Name  string  // 导出
    Age   int
    email string  // 私有
}

type Reader interface {
    Read([]byte) (int, error)
}

user := User{Name: "Alice", Age: 30}

// Bad
type ReadWriteCloser interface {
    Read([]byte) (int, error)
    Write([]byte) (int, error)
    Close() error
    Flush() error
    // ... 太多方法
}

user := User{"Alice", 30}  // 位置参数
```

### 2.9 函数设计

| 规则 | 要求                  |
|------|---------------------|
| 长度 | 不超过 50 行，单一职责       |
| 参数 | 超过 5 个时考虑使用结构体      |
| 返回值 | 必须包含 error（除非不可能失败） |
| 命名返回值 | 简单场景可用，复杂场景避免       |

```go
// Good
type CreateUserRequest struct {
    Name, Email string
    Age         int
    Phone, Address string
}

func CreateUser(req CreateUserRequest) error { }

func GetUser(id int) (*User, error) { }

func Divide(a, b float64) (result float64, err error) {
    if b == 0 {
        return 0, errors.New("division by zero")
    }
    result = a / b
    return
}

// Bad
func CreateUser(name, email string, age int, phone string, address string, city string, country string) error { }

func GetUser(id int) *User {  // 如果失败怎么办？
    // ...
}
```

### 2.10 错误处理

- 必须检查并处理所有错误，禁止忽略
- 错误信息应提供上下文
- 使用 `errors.New` 或 `fmt.Errorf` 创建错误，禁止使用字符串
- 导出的错误变量以 `Err` 开头

```go
// Good
data, err := ioutil.ReadFile(filename)
if err != nil {
    return fmt.Errorf("failed to read config file %s: %w", filename, err)
}

var ErrUserNotFound = errors.New("user not found")
var ErrInvalidInput = errors.New("invalid input")

return errors.New("user not found")
return fmt.Errorf("user %d not found", id)

// Bad
data, _ := ioutil.ReadFile(filename)  // 忽略错误

if err != nil {
    return err  // 缺少上下文
}

return "user not found"  // 使用字符串
```
