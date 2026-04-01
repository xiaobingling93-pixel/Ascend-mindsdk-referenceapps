# 代码坏味道清单

本文档列出常见的代码坏味道（Code Smells）及其识别方法。

## 快速索引

| 类别 | 坏味道 | 优先级 | 推荐重构手法 |
|------|--------|--------|-------------|
| **膨胀者** | [重复代码](#1-重复代码duplicated-code) | 高 | 提取方法、提取超类 |
| | [过长函数](#2-过长函数long-method) | 高 | 提取方法、以查询取代临时变量 |
| | [过大类](#3-过大类large-class) | 中 | 提取类、提取子类 |
| | [过长参数列表](#4-过长参数列表long-parameter-list) | 中 | 引入参数对象、保持对象完整 |
| | [数据泥团](#5-数据泥团data-clumps) | 中 | 引入参数对象、提取类 |
| **面向对象滥用** | [发散式变化](#6-发散式变化divergent-change) | 高 | 提取类 |
| | [霰弹式修改](#7-霰弹式修改shotgun-surgery) | 高 | 移动方法、移动字段 |
| | [平行继承体系](#8-平行继承体系parallel-inheritance-hierarchies) | 中 | 移动方法、移动字段 |
| | [特性依恋](#9-特性依恋feature-envy) | 中 | 移动方法 |
| **耦合者** | [消息链](#10-消息链message-chains) | 低 | 隐藏委托 |
| | [中间人](#11-中间人middle-man) | 低 | 移除中间人 |
| | [狎昵关系](#12-狎昵关系inappropriate-intimacy) | 中 | 移动方法、移动字段 |
| | [异曲同工的类](#13-异曲同工的类alternative-classes-with-different-interfaces) | 低 | 重命名方法 |
| | [不完美的库类](#14-不完美的库类incomplete-library-class) | 低 | 引入本地扩展 |
| **可有可无者** | [冗余类](#15-冗余类lazy-class) | 低 | 内联类、折叠继承体系 |
| | [夸夸其谈未来性](#16-夸夸其谈未来性speculative-generality) | 低 | 折叠继承体系、内联类 |
| | [暂时字段](#17-暂时字段temporary-field) | 低 | 提取类 |
| | [过多注释](#18-过多注释comments) | 低 | 提取方法、重命名方法 |
| **其他** | [纯数据类](#19-纯数据类data-class) | 中 | 移动方法、封装字段 |
| | [被拒绝的遗赠](#20-被拒绝的遗赠refused-bequest) | 低 | 以委托取代继承 |
| | [基本类型偏执](#21-基本类型偏执primitive-obsession) | 中 | 以对象取代基本类型 |
| | [Switch语句](#22-switch语句switch-statements) | 中 | 以多态取代条件表达式 |

---

## 膨胀者（Bloaters）

这类坏味道随着代码增长而逐渐积累，通常不易察觉，直到变成严重问题。

### 1. 重复代码（Duplicated Code）

**定义**：相同的代码结构出现在多个地方。

**识别标准**：
- 多个方法中有相同的代码块
- 两个子类中有相同的代码
- 不同类中有相似的逻辑

**示例**：
```python
def calculate_order_total(items):
    total = 0
    for item in items:
        total += item.price * item.quantity
    return total

def calculate_invoice_total(items):
    total = 0
    for item in items:
        total += item.price * item.quantity
    return total
```

**推荐重构手法**：提取方法、提取超类、以方法取代代码链

---

### 2. 过长函数（Long Method）

**定义**：方法过长，难以理解和维护。

**识别标准**：
- 方法超过 20-30 行
- 需要大量注释解释代码
- 嵌套层次超过 3 层
- 单个方法承担多个职责

**推荐重构手法**：提取方法、以查询取代临时变量、引入参数对象、分解条件表达式

---

### 3. 过大类（Large Class）

**定义**：类承担过多职责，字段和方法过多。

**识别标准**：
- 类超过 200-300 行
- 字段超过 10-15 个
- 方法超过 15-20 个
- 类名无法准确描述其职责

**示例**：
```go
type UserManager struct {
    users []User
    logger *Logger
    cache *Cache
    db *Database
    emailSender *EmailSender
}
```

**推荐重构手法**：提取类、提取子类、提取接口

---

### 4. 过长参数列表（Long Parameter List）

**定义**：方法参数过多，难以理解和使用。

**识别标准**：
- 参数超过 3-4 个
- 调用时需要频繁查看方法签名
- 参数顺序容易混淆

**示例**：
```python
def create_user(name, email, age, address, phone, department, role, manager, start_date, salary):
    pass
```

**推荐重构手法**：引入参数对象、保持对象完整、以方法取代参数

---

### 5. 数据泥团（Data Clumps）

**定义**：多个数据项经常一起出现，但未被组织成对象。

**识别标准**：
- 多个字段经常一起作为参数传递
- 多个字段一起出现在多个类中
- 删除其中一个字段会导致其他字段失去意义

**示例**：
```cpp
void printAddress(string street, string city, string state, string zip);
void validateAddress(string street, string city, string state, string zip);
bool isLocalAddress(string street, string city, string state, string zip);
```

**推荐重构手法**：提取类、引入参数对象

---

## 面向对象滥用者

这类坏味道表示面向对象原则的不完整或不正确应用。

### 6. 发散式变化（Divergent Change）

**定义**：一个类因多种不同原因被修改。

**识别标准**：
- 修改数据库时需要改这个类
- 修改UI时也需要改这个类
- 修改业务规则时还需要改这个类

**示例**：
```python
class Employee:
    def calculate_pay(self): pass
    def save_to_database(self): pass
    def generate_report(self): pass
    def send_notification(self): pass
```

**推荐重构手法**：提取类

---

### 7. 霰弹式修改（Shotgun Surgery）

**定义**：一个变化需要修改多个类。

**识别标准**：
- 添加新功能需要修改多个文件
- 修改一个字段影响多个类
- 每次变化都涉及大量小改动

**推荐重构手法**：移动方法、移动字段、内联类

---

### 8. 平行继承体系（Parallel Inheritance Hierarchies）

**定义**：霰弹式修改的特殊情况，为一个类增加子类时需要为另一个类也增加子类。

**识别标准**：
- 两个继承体系结构相似
- 在一个继承体系添加子类时，必须在另一个继承体系也添加

**示例**：
```
Customer → CorporateCustomer → PersonalCustomer
CustomerParser → CorporateCustomerParser → PersonalCustomerParser
```

**推荐重构手法**：移动方法、移动字段

---

### 9. 特性依恋（Feature Envy）

**定义**：方法对其他类的数据更感兴趣。

**识别标准**：
- 方法频繁访问其他类的数据
- 方法中大量使用其他类的getter
- 方法似乎应该属于另一个类

**示例**：
```python
class OrderPrinter:
    def print_order(self, order):
        print(f"Order: {order.id}")
        print(f"Customer: {order.customer.name}")
        print(f"Total: {order.calculate_total()}")
```

**推荐重构手法**：移动方法、提取方法

---

## 耦合者

这类坏味道导致类之间过度耦合。

### 10. 消息链（Message Chains）

**定义**：客户端需要通过一长串对象获取目标对象。

**识别标准**：
- 链式调用如 `a.b().c().d().e()`
- 对象结构变化影响多处代码

**示例**：
```python
customer.get_orders()[0].get_items()[0].get_product().get_category().get_name()
```

**推荐重构手法**：隐藏委托、提取方法

---

### 11. 中间人（Middle Man）

**定义**：类过度委托给其他类。

**识别标准**：
- 类中大部分方法只是委托
- 方法只是调用其他类的同名方法

**示例**：
```python
class Manager:
    def __init__(self, delegate):
        self.delegate = delegate
    
    def do_something(self):
        return self.delegate.do_something()
```

**推荐重构手法**：移除中间人、内联方法

---

### 12. 狎昵关系（Inappropriate Intimacy）

**定义**：类之间过度了解彼此的内部细节。

**识别标准**：
- 类频繁访问其他类的私有成员
- 类之间有循环依赖
- 类共享过多内部数据

**推荐重构手法**：移动方法、移动字段、将双向关联改为单向

---

### 13. 异曲同工的类（Alternative Classes with Different Interfaces）

**定义**：两个类做相同的事但接口不同。

**识别标准**：
- 类有相似的功能但方法名不同
- 可以用策略模式统一

**推荐重构手法**：重命名方法、移动方法

---

### 14. 不完美的库类（Incomplete Library Class）

**定义**：库类缺少需要的功能。

**识别标准**：
- 需要修改库类但无法修改
- 需要扩展库类功能

**推荐重构手法**：引入本地扩展

---

## 可有可无者

这类坏味道代表可以删除的代码。

### 15. 冗余类（Lazy Class）

**定义**：类的作用太小，不值得存在。

**识别标准**：
- 类只有少量方法
- 类只是数据容器
- 类的功能可以合并到其他类

**推荐重构手法**：内联类、折叠继承体系

---

### 16. 夸夸其谈未来性（Speculative Generality）

**定义**：为未来可能不会发生的需求添加的代码。

**识别标准**：
- 抽象层只有单一实现
- 参数或配置从未使用
- 注释说"将来可能需要"

**推荐重构手法**：折叠继承体系、内联类、移除参数

---

### 17. 暂时字段（Temporary Field）

**定义**：对象在某些情况下包含未使用的字段。

**识别标准**：
- 字段只在特定场景使用
- 字段值为 null/nil/None 时表示"不使用"

**推荐重构手法**：提取类

---

### 18. 过多注释（Comments）

**定义**：需要大量注释解释的代码。

**识别标准**：
- 代码需要注释才能理解
- 注释标记TODO/FIXME长期未处理

**推荐重构手法**：提取方法、引入断言、重命名方法

---

## 其他坏味道

### 19. 纯数据类（Data Class）

**定义**：只有字段和getter/setter的类，没有行为。

**识别标准**：
- 类只有数据字段
- 只有getter/setter方法
- 其他类频繁操作这些数据

**示例**：
```cpp
class User {
public:
    std::string name;
    std::string email;
    int age;
};
```

**推荐重构手法**：移动方法、封装字段

---

### 20. 被拒绝的遗赠（Refused Bequest）

**定义**：子类只使用父类部分功能。

**识别标准**：
- 子类不需要父类的某些方法
- 子类抛出"不支持"异常

**推荐重构手法**：以委托取代继承、提取超类

---

### 21. 基本类型偏执（Primitive Obsession）

**定义**：过度使用基本类型而非小对象。

**识别标准**：
- 使用基本类型表示概念（如用int表示金额）
- 大量字符串操作
- 缺乏领域模型

**示例**：
```python
def transfer(from_account: str, to_account: str, amount: float, currency: str):
    pass
```

**推荐重构手法**：以对象取代基本类型、引入参数对象

---

### 22. Switch语句（Switch Statements）

**定义**：复杂的switch/if-else链，难以扩展。

**识别标准**：
- switch语句分散在多处
- 添加新case需要修改多处
- 条件基于类型码

**示例**：
```go
func calculate(employee *Employee) float64 {
    switch employee.Type {
    case "ENGINEER":
        return employee.MonthlySalary
    case "SALESMAN":
        return employee.MonthlySalary + employee.Commission
    case "MANAGER":
        return employee.MonthlySalary + employee.Bonus
    }
    return 0
}
```

**推荐重构手法**：以多态取代条件表达式、以策略模式取代条件表达式
