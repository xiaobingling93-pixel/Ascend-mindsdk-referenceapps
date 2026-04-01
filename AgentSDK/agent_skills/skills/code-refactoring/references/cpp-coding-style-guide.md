# C++ 语言编程指导

本文档列出 C++ 语言编程规范，参考昇腾社区 C++ 语言编程指导（建议稿）。

## 约定

**规则**：编程时必须遵守的约定(must)

**建议**：编程时应该遵守的约定(should)

**例外**：修改和适配外部开源代码、第三方代码时，应该遵守开源代码、第三方代码已有规范，保持风格统一。

---

## 1. 代码风格

### 1.1 命名

| 类型                | 命名风格 | 示例 |
|-------------------|----------|------|
| 类、结构体、枚举、联合体、命名空间 | 大驼峰 | `class UrlTable {}` |
| 函数（全局/成员）         | 大驼峰 | `void AddElement()` |
| 变量（全局/局部/参数）   | 小驼峰 | `int tableName` |
| 成员变量              | 小驼峰+后下划线 | `int fileName_` |
| 全局变量              | g_前缀+小驼峰 | `int g_activeCount` |
| 宏、枚举值、全局常量        | 全大写+下划线 | `MAX_BUFFER_SIZE` |

注意：常量指全局作用域、namespace域、类静态成员下的 const/constexpr 基本类型、枚举、字符串；函数局部 const 常量使用小驼峰。

**文件命名**：小写+下划线，头文件 `.h`，源文件 `.cpp`

```cpp
class List {
public:
    void AddElement(const Element& element);
    Element GetElement(const unsigned int index) const;
    bool IsEmpty() const;
private:
    std::string fileName_;
};

namespace FileUtils {
    void DeleteUser();
}

enum TintColor {
    RED,
    DARK_RED,
    GREEN
};

namespace Utils {
    const unsigned int DEFAULT_FILE_SIZE_KB = 200;
}

int g_activeConnectCount;

void Func() {
    const unsigned int bufferSize = 100;  // 函数局部常量用小驼峰
}
```

### 1.2 格式

| 规则 | 要求                     |
|------|------------------------|
| 行宽 | 不超过 120 字符             |
| 缩进 | 4 空格，禁止 Tab            |
| 指针/引用 | `*`、`&` 跟随变量名，另一边留空格   |
| if/for/while | 必须使用大括号，即使只有一条语句       |
| 大括号风格 | K&R：函数左大括号另起一行，其他放行末   |
| 表达式换行 | 运算符放行末，保持对齐或 4 空格缩进    |
| 变量定义 | 每行一个变量                 |
| 空行 | 最多连续 2 个空行，大括号内首尾不加空行，但namespace的大括号内不作要求 |

```cpp
int Foo(int a)
{
    if (cond) {
        DoSomething();
    }
}

char *c;
const std::string &str;

for (int i = 0; i < someRange; i++) {
    DoSomething();
}

while (condition) { }

if ((currentValue > threshold) &&
    someCondition) {
    DoSomething();
}
```

### 1.3 注释

- 代码注释置于对应代码的上方或右边，使用 `//`，不用 `/**/`
- 注释符与内容间 1 空格，右置注释与前面代码至少 1 空格
- 禁止 TODO/TBD/FIXME等注释
- 不用的代码直接删除，不要注释掉（包括 `#if 0` 等）
- 不要写空有格式的函数头注释，按需写有价值的信息

```cpp
// this is multi-
// line comment
int foo; // this single-line comment

/*
 * 返回实际写入的字节数，-1表示写入失败
 * 注意，内存 buf 由调用者负责释放
 */
int WriteString(const char *buf, int len);
```

---

## 2. 通用编码

### 2.1 代码设计

| 规则 | 要求 |
|------|------|
| 外部数据 | 必须进行合法性检查（函数入参、外部输入、文件、环境变量、用户数据等） |
| 函数结果传递 | 优先使用返回值，尽量避免出参 |
| 无效代码 | 必须删除 |
| 异常捕获 | 禁止 `catch(...)`，必须指定异常类型 |

```cpp
// 正确示范
try {
    // do something;
} catch (const std::bad_alloc &e) {
    // do something;
}
```

### 2.2 头文件和预处理

- 禁止头文件循环依赖
- 禁止包含用不到的头文件
- 禁止 `extern` 声明引用外部函数/变量
- 禁止在 `extern "C"` 中包含头文件
- 禁止在头文件中或 `#include` 之前使用 `using` 导入命名空间

### 2.3 常量

- 禁止使用宏表示常量
- 禁止使用魔鬼数字（看不懂、难以理解的数字）
- 建议每个常量保证单一职责

### 2.4 表达式

- 使用括号明确操作符优先级，避免低级错误

```cpp
// 正确示范
if (cond1 || (cond2 && cond3)) { }

// 错误示范
if (cond1 || cond2 && cond3) { }
```

### 2.5 转换

- 使用C++提供的类型转换，而不是C风格的类型转换
- 避免使用 `const_cast` 和 `reinterpret_cast`

### 2.6 控制语句

- switch 语句必须有 default 分支

### 2.7 字符串

- 字符串存储操作必须确保有 `\0` 结束符

### 2.8 断言

- 断言不能用于校验程序在运行期间可能导致的错误，可能发生的运行错误要用错误处理代码来处理

### 2.9 类和对象

- 单个对象释放使用 `delete`，数组对象释放使用 `delete[]`
- 禁止 `std::move` 操作 const 对象
- 严格使用 `virtual`/`override`/`final` 修饰虚函数

```cpp
class Base {
public:
    virtual void Func();
};

class Derived : public Base {
public:
    void Func() override;
};

class FinalDerived : public Derived {
public:
    void Func() final;
};

// 内存释放
int *numberArray = new int[5];
int *number = new int();
delete[] numberArray;
numberArray = nullptr;
delete number;
number = nullptr;
```

### 2.10 函数设计

- 使用 RAII 特性来帮助追踪动态分配
- 非局部范围使用 lambda 时，避免按引用捕获
- 禁止虚函数使用缺省参数值
- 建议使用强类型参数，避免使用 `void*`

```cpp
// RAII 示例
{
    std::lock_guard<std::mutex> lock(mutex_);
    // ...
}

// lambda 按引用捕获问题
{
    int local_var = 1;
    auto func = [&]() { std::cout << local_var << std::endl; };
    thread_pool.commit(func);  // 危险：local_var 可能已销毁
}
```

### 2.11 函数使用

| 规则 | 要求 |
|------|------|
| 参数顺序 | 入参在前，出参在后 |
| 入参类型 | `const T &` |
| 出参类型 | `T *` |
| 不涉及所有权 | 使用 `T *` 或 `const T &` 作为参数，而不是智能指针 |
| 传递所有权 | 使用 `shared_ptr` + `move` 传参 |
| 单参数构造函数 | 必须用 `explicit` 修饰 |
| 多参数构造函数 | 禁止用 `explicit` 修饰 |
| 拷贝构造和赋值 | 应该成对出现或者禁止 |
| 指针参数 | 禁止保存、delete 指针参数 |

```cpp
bool Func(const std::string &in, FooBar *out1, FooBar *out2);

// 正确示范
bool Func(const FooBar &in);

// 错误示范
bool Func(std::shared_ptr<FooBar> in);

// explicit 使用
explicit Foo(int x);          // Good
explicit Foo(int x, int y=0); // Good: 有默认参数的单参数
Foo(int x, int y=0);          // Bad: 有默认参数的单参数未用 explicit
explicit Foo(int x, int y);   // Bad: 多参数用了 explicit

// 拷贝控制
class Foo {
private:
    Foo(const Foo&) = default;
    Foo& operator=(const Foo&) = default;
    Foo(Foo&&) = delete;
    Foo& operator=(Foo&&) = delete;
};
```

### 2.12 内存

- 内存分配后必须判断是否成功
- 禁止引用未初始化的内存（malloc、new 分配的内存没有被初始化为 0）

### 2.13 文件

- 必须对文件路径进行规范化后再使用（Linux: `realpath`，Windows: `PathCanonicalize`）
- 不要在共享目录中创建临时文件

```cpp
char *fileName = GetMsgFromRemote();
sprintf_s(untrustPath, sizeof(untrustPath), "/tmp/%s", fileName);
char path[PATH_MAX] = {0};
if (realpath(untrustPath, path) == NULL) {
    // error
}
if (!IsValidPath(path)) {
    // error
}
char *text = ReadFileContent(path);
```
