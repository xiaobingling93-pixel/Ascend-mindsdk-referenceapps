# Python 语言编程指导

本文档列出 Python 语言编程规范，参考昇腾社区 python 语言编程指导（建议稿）。

## 约定

**规则**：编程时必须遵守的约定(must)

**建议**：编程时应该遵守的约定(should)

**例外**：修改和适配外部开源代码、第三方代码时，应该遵守开源代码、第三方代码已有规范，保持风格统一。

---

## 1. 排版

### 1.1 缩进与行宽

| 规则 | 要求 |
|------|------|
| 缩进 | 4 空格，禁止 Tab |
| 禁止混用 | 禁止混合使用空格和 Tab |
| 行宽 | 不超过 120 字符 |
| 空行 | 相对独立的程序块之间、变量说明之后必须加空行 |

### 1.2 空格

- 逗号、分号（假如用到）只在后面加空格
- 双目操作符（比较、赋值、算术、逻辑）前后加空格

```python
# Good
print(a, b, c)
a = b + c
a += 2
if current_time >= MAX_TIME_VALUE:

# Bad
print(a,b , c)
a=b+ c
a+=2
if current_time>= MAX_TIME_VALUE
```

### 1.3 导入

- 每个模块单独一行
- 禁止 `from xxx import *`

```python
# Good
import sys
import os
from sys import stdin, stdout

# Bad
import sys, os
from xxx import *
```

---

## 2. 注释

- 有效注释量（包括文档字符串）建议在 20% 以上
- 避免在注释中使用缩写，如使用需说明
- 修改代码时优先更新相应注释
- 全局变量建议添加详细注释

### 2.1 文档字符串

- 多行时，末尾 `"""` 独占一行
- 公共函数文档字符串写在函数声明下一行，缩进 4 空格
- 公共属性注释在属性声明上方，保持同样缩进。行内注释以 `#` 和一个空格开始

```python
def load_batch(fpath):
    """
    功能描述：
    参数：
    返回值：
    异常描述：
    """
    pass

# 单行文档字符串
"""API for interacting with the volume manager."""

# Compensate for border
x = x + 1
```

---

## 3. 命名

| 类型 | Public | Internal |
|------|--------|----------|
| 模块 | lower_with_under | _lower_with_under |
| 包 | lower_with_under | - |
| 类 | CapWords | CapWords |
| 异常 | CapWords | - |
| 函数/方法 | lower_with_under() | _lower_with_under() |
| 全局/类常量 | CAPS_WITH_UNDER | _CAPS_WITH_UNDER |
| 全局/类变量 | lower_with_under | lower_with_under |
| 实例变量 | lower_with_under | _lower_with_under 或 __lower_with_under |
| 参数 | lower_with_under | _lower_with_under |
| 局部变量 | lower_with_under | _lower_with_under |

**说明**：
- `lower_with_under`：小写字母+下划线
- `CapWords`：大写字母开头(驼峰)
- `CAPS_WITH_UNDER`：大写字母+下划线
- 单下划线开头：暗示仅供内部使用
- 双下划线开头：会被解释器改名，避免与派生类成员重名

```python
sample_global_variable = 0
M_SAMPLE_GLOBAL_CONSTANT = 0

class SampleClass:
    SAMPLE_CLASS_CONSTANT = 0
    
    def sample_member_method(self, sample_parameter):
        pass
    
    def _private_method(self):
        self._member = 1  # 单下划线：暗示内部使用

class Mapping:
    def __init__(self, iterable):
        self.items_list = []
        self.__update(iterable)  # 双下划线：会被改名为 _Mapping__update
```

---

## 4. 编码

### 4.1 类型检查

- 与 None 比较使用 `is` 或 `is not`，不用 `==`
- 使用 `isinstance` 进行类型检查，不用 `type`

```python
# Good
if value is None:
if isinstance(obj, list):

# Bad
if value == None:
if type(obj) == list:
```

### 4.2 推导式

- 使用推导式代替重复逻辑
- 不在一个推导式中使用 3 个以上 for 语句

```python
# Good
odd_num_list = [i for i in range(100) if i % 2 == 1]

# Bad
odd_num_list = []
for i in range(100):
    if i % 2 == 1:
        odd_num_list.append(i)
```

### 4.3 变量

- 避免在无关变量或概念之间重用名字
- 避免变量类型在生命周期内变化
- 函数接口可使用类型注解

```python
def func(name: str, age: int) -> bool:
    pass
```

---

## 5. 异常处理

- 使用 `try...except...finally` 或 `with` 语句确保资源释放

```python
# Good
with open(filename) as f:
    data = f.read()

# 或
try:
    f = open(filename)
    data = f.read()
finally:
    f.close()
```

---

## 6. 测试用例

- 可变参数默认值使用 `None`

```python
# Good
def func(items=None):
    if items is None:
        items = []

# Bad
def func(items=[]):
    pass
```

- 禁止注释失效测试用例，应删除或使用级别控制
