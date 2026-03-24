# Python测试模式和框架适配

本文档定义Python SDK单元测试的框架适配规则和代码模式。

---

## 1. 测试框架识别

### 1.1 pytest

**识别特征**：
```python
import pytest

def test_function_name():
    # test body
    assert condition

class TestClassName:
    def test_method_name(self):
        assert condition

@pytest.fixture
def sample_data():
    return {"key": "value"}
```

**文件搜索模式**：
- `import pytest`
- `@pytest.` 装饰器
- `test_*.py` 文件命名
- `def test_` 函数命名
- `assert` 语句

### 1.2 unittest

**识别特征**：
```python
import unittest

class TestClassName(unittest.TestCase):
    def setUp(self):
        # setup code
    
    def tearDown(self):
        # teardown code
    
    def test_method_name(self):
        self.assertEqual(a, b)
```

**文件搜索模式**：
- `import unittest`
- `unittest.TestCase`
- `def test_` 方法命名
- `self.assert` 断言

### 1.3 nose/nose2

**识别特征**：
```python
from nose.tools import assert_equal, assert_raises

def test_function():
    assert_equal(actual, expected)
```

**文件搜索模式**：
- `from nose`
- `import nose`
- `@nose.tools` 装饰器

---

## 2. 断言模式

### 2.1 pytest断言

| 断言类型 | 断言语句 | 说明 |
|---------|---------|------|
| 相等检查 | `assert actual == expected` | 相等 |
| 不等检查 | `assert actual != expected` | 不相等 |
| 布尔检查 | `assert condition` | 条件为真 |
| 布尔检查 | `assert not condition` | 条件为假 |
| 包含检查 | `assert item in container` | 包含 |
| 包含检查 | `assert item not in container` | 不包含 |
| 类型检查 | `assert isinstance(obj, type)` | 类型检查 |
| 近似相等 | `assert abs(a - b) < 1e-9` | 浮点近似 |
| 异常检查 | `pytest.raises(Exception)` | 抛出异常 |
| 警告检查 | `pytest.warns(Warning)` | 发出警告 |

### 2.2 unittest断言

| 断言类型 | 断言方法 | 说明 |
|---------|---------|------|
| 相等检查 | `self.assertEqual(a, b)` | 相等 |
| 不等检查 | `self.assertNotEqual(a, b)` | 不相等 |
| 布尔检查 | `self.assertTrue(x)` | 条件为真 |
| 布尔检查 | `self.assertFalse(x)` | 条件为假 |
| 包含检查 | `assertIn(a, b)` | a in b |
| 包含检查 | `assertNotIn(a, b)` | a not in b |
| 空值检查 | `assertIsNone(x)` | x is None |
| 空值检查 | `assertIsNotNone(x)` | x is not None |
| 类型检查 | `assertIsInstance(a, b)` | isinstance(a, b) |
| 异常检查 | `assertRaises(Exception)` | 抛出异常 |
| 近似相等 | `assertAlmostEqual(a, b)` | 浮点近似 |

---

## 3. 测试代码模板

### 3.1 pytest空值测试模板

```python
import pytest

class TestFunctionName:
    def test_none_input(self):
        """测试None输入"""
        result = function_name(None)
        assert result == ERROR_INVALID_PARAM
    
    def test_empty_string_input(self):
        """测试空字符串输入"""
        result = function_name("")
        assert result == SUCCESS
    
    def test_empty_list_input(self):
        """测试空列表输入"""
        result = function_name([])
        assert result == SUCCESS
```

### 3.2 pytest边界值测试模板

```python
import pytest
import sys

class TestFunctionName:
    def test_int_max_input(self):
        """测试整数最大值"""
        result = function_name(sys.maxsize)
        assert result == SUCCESS
    
    def test_int_min_input(self):
        """测试整数最小值"""
        result = function_name(-sys.maxsize - 1)
        assert result == ERROR_INVALID_PARAM
    
    def test_zero_input(self):
        """测试零值"""
        result = function_name(0)
        assert result == SUCCESS
    
    @pytest.mark.parametrize("value,expected", [
        (0, SUCCESS),
        (1, SUCCESS),
        (-1, ERROR_INVALID_PARAM),
        (100, SUCCESS),
    ])
    def test_various_values(self, value, expected):
        """参数化测试多种值"""
        assert function_name(value) == expected
```

### 3.3 pytest异常测试模板

```python
import pytest

class TestFunctionName:
    def test_raises_on_invalid_input(self):
        """测试非法输入抛出异常"""
        with pytest.raises(ValueError):
            function_name("invalid")
    
    def test_raises_type_error(self):
        """测试类型错误"""
        with pytest.raises(TypeError):
            function_name(123)  # 期望字符串
    
    def test_no_exception_on_valid_input(self):
        """测试合法输入不抛出异常"""
        try:
            result = function_name("valid")
            assert result is not None
        except Exception:
            pytest.fail("Unexpected exception raised")
```

### 3.4 pytest Fixture模板

```python
import pytest

@pytest.fixture
def sample_data():
    """测试数据fixture"""
    return {"key": "value", "number": 42}

@pytest.fixture
def mock_dependency(mocker):
    """Mock依赖fixture"""
    mock = mocker.MagicMock()
    mock.method.return_value = "mocked"
    return mock

class TestFunctionName:
    def test_with_sample_data(self, sample_data):
        """使用fixture测试"""
        result = function_name(sample_data)
        assert result == SUCCESS
    
    def test_with_mock(self, mock_dependency):
        """使用mock测试"""
        result = function_under_test(mock_dependency)
        assert result == "expected"
```

### 3.5 unittest测试模板

```python
import unittest

class TestFunctionName(unittest.TestCase):
    def setUp(self):
        """每个测试前的初始化"""
        self.test_data = {"key": "value"}
    
    def tearDown(self):
        """每个测试后的清理"""
        pass
    
    def test_none_input(self):
        """测试None输入"""
        result = function_name(None)
        self.assertEqual(result, ERROR_INVALID_PARAM)
    
    def test_empty_string_input(self):
        """测试空字符串输入"""
        result = function_name("")
        self.assertEqual(result, SUCCESS)
    
    def test_raises_exception(self):
        """测试异常抛出"""
        with self.assertRaises(ValueError):
            function_name("invalid")

if __name__ == "__main__":
    unittest.main()
```

---

## 4. 测试文件组织

### 4.1 目录结构

```
project/
├── src/
│   └── module/
│       ├── __init__.py
│       └── api.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── module/
        ├── __init__.py
        └── test_api.py
```

### 4.2 命名规范

| 类型 | 命名规范 | 示例 |
|------|---------|------|
| 测试文件 | `test_<模块名>.py` | `test_api.py` |
| 测试类 | `Test<类名/功能名>` | `TestApiClient`, `TestProcessData` |
| 测试方法 | `test_<场景描述>` | `test_none_input`, `test_max_value` |

### 4.3 conftest.py配置

```python
# tests/conftest.py
import pytest

@pytest.fixture(scope="session")
def test_config():
    """全局测试配置"""
    return {"api_url": "http://localhost:8080"}

@pytest.fixture(scope="function")
def clean_database():
    """每个测试前清理数据库"""
    # setup
    yield
    # teardown
```

---

## 5. 边界场景代码生成

### 5.1 None/null场景

```python
# 原函数: def process_data(data: Optional[dict]) -> Status
def test_process_data_none_input():
    """测试None输入"""
    result = process_data(None)
    assert result == Status.INVALID_PARAM
```

### 5.2 空字符串场景

```python
# 原函数: def parse_config(config: str) -> Status
def test_parse_config_empty_string():
    """测试空字符串"""
    result = parse_config("")
    assert result == Status.SUCCESS

def test_parse_config_none_string():
    """测试None字符串"""
    with pytest.raises(TypeError):
        parse_config(None)
```

### 5.3 数值边界场景

```python
import sys

# 原函数: def set_buffer_size(size: int) -> Status
def test_set_buffer_size_zero():
    """测试零值"""
    assert set_buffer_size(0) == Status.INVALID_PARAM

def test_set_buffer_size_max():
    """测试最大值"""
    assert set_buffer_size(sys.maxsize) == Status.ERROR

def test_set_buffer_size_negative():
    """测试负值"""
    assert set_buffer_size(-1) == Status.INVALID_PARAM

def test_set_buffer_size_valid():
    """测试合法值"""
    assert set_buffer_size(1024) == Status.SUCCESS
```

### 5.4 列表边界场景

```python
# 原函数: def get_element(arr: list, index: int) -> Any
def test_get_element_empty_list():
    """测试空列表"""
    with pytest.raises(IndexError):
        get_element([], 0)

def test_get_element_first():
    """测试首元素"""
    result = get_element([1, 2, 3], 0)
    assert result == 1

def test_get_element_last():
    """测试末元素"""
    result = get_element([1, 2, 3], 2)
    assert result == 3

def test_get_element_out_of_range():
    """测试越界"""
    with pytest.raises(IndexError):
        get_element([1, 2, 3], 3)
```

### 5.5 字典边界场景

```python
# 原函数: def get_value(data: dict, key: str) -> Any
def test_get_value_empty_dict():
    """测试空字典"""
    with pytest.raises(KeyError):
        get_value({}, "key")

def test_get_value_missing_key():
    """测试缺失键"""
    with pytest.raises(KeyError):
        get_value({"a": 1}, "b")

def test_get_value_existing_key():
    """测试存在键"""
    result = get_value({"a": 1}, "a")
    assert result == 1
```

---

## 6. Mock和Patch

### 6.1 使用unittest.mock

```python
from unittest.mock import Mock, patch, MagicMock

def test_with_mock():
    """使用Mock对象"""
    mock_obj = Mock()
    mock_obj.method.return_value = "mocked"
    
    result = function_under_test(mock_obj)
    assert result == "expected"
    mock_obj.method.assert_called_once()

@patch('module.external_function')
def test_with_patch(mock_func):
    """使用patch装饰器"""
    mock_func.return_value = "mocked"
    
    result = function_under_test()
    assert result == "expected"
```

### 6.2 使用pytest-mock

```python
import pytest

def test_with_mocker(mocker):
    """使用pytest-mock"""
    mock_func = mocker.patch('module.external_function')
    mock_func.return_value = "mocked"
    
    result = function_under_test()
    assert result == "expected"
    mock_func.assert_called_once()
```

---

## 7. 参数化测试

### 7.1 pytest参数化

```python
import pytest

@pytest.mark.parametrize("input,expected", [
    (None, Status.INVALID_PARAM),
    ("", Status.SUCCESS),
    ("valid", Status.SUCCESS),
    ("invalid", Status.ERROR),
])
def test_various_inputs(input, expected):
    """参数化测试多种输入"""
    assert process_input(input) == expected

@pytest.mark.parametrize("x", [0, 1, 2])
@pytest.mark.parametrize("y", [0, 1, 2])
def test_combinations(x, y):
    """组合参数化测试"""
    result = calculate(x, y)
    assert result >= 0
```

---

## 8. 手工测试建议格式

对于无法自动生成的场景，使用以下格式给出建议：

```markdown
### 手工测试建议: [场景名称]

**场景编号**: R-020
**场景类型**: 资源限制

**测试目的**:
验证网络连接超时时的错误处理。

**前置条件**:
1. 配置防火墙阻断目标端口
2. 或使用网络模拟工具

**测试步骤**:
1. 配置网络超时时间为较短值（如1秒）
2. 调用需要网络连接的API
3. 观察返回值和行为

**预期结果**:
- 抛出TimeoutError或返回超时错误码
- 不发生无限等待
- 资源正确释放

**测试工具**:
- Linux: `iptables -A INPUT -p tcp --dport <port> -j DROP`
- Python: `pytest-timeout` 插件
```
