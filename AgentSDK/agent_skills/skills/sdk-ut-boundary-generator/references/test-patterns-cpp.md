# C/C++测试模式和框架适配

本文档定义C/C++ SDK单元测试的框架适配规则和代码模式。

---

## 1. 测试框架识别

### 1.1 Google Test (GTest)

**识别特征**：
```cpp
#include <gtest/gtest.h>
#include <gmock/gmock.h>

TEST(TestSuiteName, TestName) {
    // test body
}

TEST_F(TestFixture, TestName) {
    // test body with fixture
}
```

**文件搜索模式**：
- `gtest/gtest.h`
- `gmock/gmock.h`
- `TEST(` 宏
- `TEST_F(` 宏
- `EXPECT_` 断言
- `ASSERT_` 断言

### 1.2 Google Mock (GMock)

**识别特征**：
```cpp
#include <gmock/gmock.h>

class MockClass : public RealClass {
public:
    MOCK_METHOD(ReturnType, MethodName, (Args...));
};

using ::testing::_;
using ::testing::Return;
using ::testing::Throw;
```

### 1.3 Catch2

**识别特征**：
```cpp
#include <catch2/catch.hpp>

TEST_CASE("Test description", "[tag]") {
    // test body
}

SECTION("Section description") {
    // section body
}
```

**文件搜索模式**：
- `catch.hpp`
- `catch2/catch.hpp`
- `TEST_CASE(`
- `SECTION(`
- `REQUIRE` 断言

### 1.4 Boost.Test

**识别特征**：
```cpp
#include <boost/test/unit_test.hpp>

BOOST_AUTO_TEST_CASE(test_name) {
    // test body
}

BOOST_AUTO_TEST_SUITE(suite_name)
BOOST_AUTO_TEST_CASE(test_name) {
    // test body
}
BOOST_AUTO_TEST_SUITE_END()
```

**文件搜索模式**：
- `boost/test/`
- `BOOST_AUTO_TEST`
- `BOOST_CHECK` 断言
- `BOOST_REQUIRE` 断言

### 1.5 CppUTest

**识别特征**：
```cpp
#include <CppUTest/TestHarness.h>

TEST_GROUP(TestGroup) {
    void setup() override {}
    void teardown() override {}
};

TEST(TestGroup, TestName) {
    // test body
}
```

---

## 2. 断言模式

### 2.1 Google Test断言

| 断言类型 | 断言宏 | 说明 |
|---------|--------|------|
| 布尔检查 | `EXPECT_TRUE(condition)` | 条件为真（非致命） |
| 布尔检查 | `ASSERT_TRUE(condition)` | 条件为真（致命） |
| 布尔检查 | `EXPECT_FALSE(condition)` | 条件为假 |
| 相等检查 | `EXPECT_EQ(expected, actual)` | 相等 |
| 相等检查 | `EXPECT_NE(val1, val2)` | 不相等 |
| 比较检查 | `EXPECT_LT(val1, val2)` | 小于 |
| 比较检查 | `EXPECT_LE(val1, val2)` | 小于等于 |
| 比较检查 | `EXPECT_GT(val1, val2)` | 大于 |
| 比较检查 | `EXPECT_GE(val1, val2)` | 大于等于 |
| 字符串检查 | `EXPECT_STREQ(expected, actual)` | C字符串相等 |
| 字符串检查 | `EXPECT_STRCASEEQ(expected, actual)` | C字符串相等（忽略大小写） |
| 浮点检查 | `EXPECT_FLOAT_EQ(expected, actual)` | 浮点数近似相等 |
| 浮点检查 | `EXPECT_DOUBLE_EQ(expected, actual)` | 双精度近似相等 |
| 异常检查 | `EXPECT_THROW(statement, exception_type)` | 抛出指定异常 |
| 异常检查 | `EXPECT_NO_THROW(statement)` | 不抛出异常 |
| 空指针检查 | `EXPECT_EQ(ptr, nullptr)` | 指针为空 |
| 空指针检查 | `EXPECT_NE(ptr, nullptr)` | 指针非空 |

### 2.2 Catch2断言

| 断言类型 | 断言宏 | 说明 |
|---------|--------|------|
| 基本检查 | `REQUIRE(expression)` | 条件为真（致命） |
| 基本检查 | `CHECK(expression)` | 条件为真（非致命） |
| 相等检查 | `REQUIRE(actual == expected)` | 相等 |
| 异常检查 | `REQUIRE_THROWS(expression)` | 抛出异常 |
| 异常检查 | `REQUIRE_THROWS_AS(expression, type)` | 抛出指定类型异常 |
| 异常检查 | `REQUIRE_NOTHROW(expression)` | 不抛出异常 |

### 2.3 Boost.Test断言

| 断言类型 | 断言宏 | 说明 |
|---------|--------|------|
| 基本检查 | `BOOST_CHECK(condition)` | 条件为真 |
| 基本检查 | `BOOST_REQUIRE(condition)` | 条件为真（致命） |
| 相等检查 | `BOOST_CHECK_EQUAL(expected, actual)` | 相等 |
| 相等检查 | `BOOST_CHECK_NE(val1, val2)` | 不相等 |
| 异常检查 | `BOOST_CHECK_THROW(statement, type)` | 抛出指定异常 |
| 异常检查 | `BOOST_CHECK_NO_THROW(statement)` | 不抛出异常 |

---

## 3. 测试代码模板

### 3.1 GTest空值测试模板

```cpp
TEST(FunctionNameTest, NullPointerInput) {
    // Arrange
    ReturnType expected = ERROR_INVALID_PARAM;
    
    // Act
    ReturnType result = FunctionName(nullptr);
    
    // Assert
    EXPECT_EQ(result, expected);
}

TEST(FunctionNameTest, NullStringInput) {
    // Arrange
    const char* nullStr = nullptr;
    
    // Act & Assert
    EXPECT_EQ(FunctionName(nullStr), ERROR_INVALID_PARAM);
}

TEST(FunctionNameTest, EmptyStringInput) {
    // Arrange
    const char* emptyStr = "";
    
    // Act & Assert
    EXPECT_EQ(FunctionName(emptyStr), SUCCESS);
}
```

### 3.2 GTest边界值测试模板

```cpp
TEST(FunctionNameTest, IntMaxInput) {
    // Arrange
    int maxValue = INT_MAX;
    
    // Act
    ReturnType result = FunctionName(maxValue);
    
    // Assert
    EXPECT_EQ(result, SUCCESS);
}

TEST(FunctionNameTest, IntMinInput) {
    // Arrange
    int minValue = INT_MIN;
    
    // Act
    ReturnType result = FunctionName(minValue);
    
    // Assert
    EXPECT_EQ(result, ERROR_INVALID_PARAM);
}

TEST(FunctionNameTest, ZeroInput) {
    // Arrange & Act & Assert
    EXPECT_EQ(FunctionName(0), SUCCESS);
}
```

### 3.3 GTest异常测试模板

```cpp
TEST(FunctionNameTest, ThrowsOnInvalidInput) {
    // Arrange
    InvalidType invalidInput;
    
    // Act & Assert
    EXPECT_THROW(FunctionName(invalidInput), std::invalid_argument);
}

TEST(FunctionNameTest, NoThrowOnValidInput) {
    // Arrange
    ValidType validInput;
    
    // Act & Assert
    EXPECT_NO_THROW(FunctionName(validInput));
}
```

### 3.4 GTest Fixture模板

```cpp
class FunctionNameTest : public ::testing::Test {
protected:
    void SetUp() override {
        // 初始化代码
    }
    
    void TearDown() override {
        // 清理代码
    }
    
    // 测试辅助成员
    TestHelper helper_;
};

TEST_F(FunctionNameTest, TestCaseWithFixture) {
    // 使用fixture成员
    EXPECT_TRUE(helper_.IsReady());
}
```

### 3.5 GMock Mock模板

```cpp
class MockDependency : public IDependency {
public:
    MOCK_METHOD(ReturnType, MethodName, (ParamType), (override));
    MOCK_METHOD(void, VoidMethod, (), (override));
};

TEST(FunctionNameTest, WithMock) {
    // Arrange
    MockDependency mock;
    EXPECT_CALL(mock, MethodName(_))
        .WillOnce(Return(expectedValue));
    
    // Act
    auto result = FunctionUnderTest(&mock);
    
    // Assert
    EXPECT_EQ(result, expectedResult);
}
```

---

## 4. 测试文件组织

### 4.1 目录结构

```
project/
├── src/
│   └── module/
│       ├── api.cpp
│       └── api.h
└── test/
    ├── CMakeLists.txt
    ├── test_main.cpp
    └── module/
        └── api_test.cpp
```

### 4.2 命名规范

| 类型 | 命名规范 | 示例 |
|------|---------|------|
| 测试文件 | `<源文件名>_test.cpp` | `api_test.cpp` |
| 测试套件 | `<类名/函数名>Test` | `ApiTest`, `ProcessDataTest` |
| 测试用例 | `<场景描述>` | `NullPointerInput`, `IntMaxValue` |

### 4.3 测试main函数

```cpp
// test_main.cpp
#include <gtest/gtest.h>

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
```

---

## 5. 边界场景代码生成

### 5.1 空指针场景

```cpp
// 原函数: Status ProcessData(const Data* data);
TEST(ProcessDataTest, NullPointerInput) {
    EXPECT_EQ(ProcessData(nullptr), STATUS_INVALID_PARAM);
}
```

### 5.2 空字符串场景

```cpp
// 原函数: Status ParseConfig(const char* config);
TEST(ParseConfigTest, EmptyStringInput) {
    EXPECT_EQ(ParseConfig(""), STATUS_SUCCESS);
}

TEST(ParseConfigTest, NullStringInput) {
    EXPECT_EQ(ParseConfig(nullptr), STATUS_INVALID_PARAM);
}
```

### 5.3 数值边界场景

```cpp
// 原函数: Status SetBufferSize(size_t size);
TEST(SetBufferSizeTest, ZeroSize) {
    EXPECT_EQ(SetBufferSize(0), STATUS_INVALID_PARAM);
}

TEST(SetBufferSizeTest, MaxSize) {
    EXPECT_EQ(SetBufferSize(SIZE_MAX), STATUS_ERROR);
}

TEST(SetBufferSizeTest, ValidSize) {
    EXPECT_EQ(SetBufferSize(1024), STATUS_SUCCESS);
}
```

### 5.4 数组边界场景

```cpp
// 原函数: Status GetElement(const Array* arr, size_t index, Element* out);
TEST(GetElementTest, EmptyArray) {
    Array emptyArr = {0, nullptr};
    Element out;
    EXPECT_EQ(GetElement(&emptyArr, 0, &out), STATUS_OUT_OF_RANGE);
}

TEST(GetElementTest, FirstElement) {
    Array arr = {10, data};
    Element out;
    EXPECT_EQ(GetElement(&arr, 0, &out), STATUS_SUCCESS);
}

TEST(GetElementTest, LastElement) {
    Array arr = {10, data};
    Element out;
    EXPECT_EQ(GetElement(&arr, 9, &out), STATUS_SUCCESS);
}

TEST(GetElementTest, OutOfRange) {
    Array arr = {10, data};
    Element out;
    EXPECT_EQ(GetElement(&arr, 10, &out), STATUS_OUT_OF_RANGE);
}
```

---

## 6. 手工测试建议格式

对于无法自动生成的场景，使用以下格式给出建议：

```markdown
### 手工测试建议: [场景名称]

**场景编号**: R-001
**场景类型**: 资源限制

**测试目的**:
验证在内存分配失败时的错误处理。

**前置条件**:
1. 系统内存接近耗尽
2. 或使用内存限制工具（如ulimit）

**测试步骤**:
1. 设置进程内存限制为较小值
2. 调用需要大内存的API
3. 观察返回值和行为

**预期结果**:
- 返回内存不足错误码
- 不发生崩溃
- 资源正确释放

**测试工具**:
- Linux: `ulimit -v <KB>`
- Windows: Job Object API
```
