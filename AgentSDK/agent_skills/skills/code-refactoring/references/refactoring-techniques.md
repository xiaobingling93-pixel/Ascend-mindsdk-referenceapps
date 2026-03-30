# 重构手法参考

本文档详细列出常用重构手法及其适用场景。

## 快速索引

| 类别 | 重构手法 | 适用场景 |
|------|----------|----------|
| **组成方法** | [提取方法](#1-提取方法extract-method) | 过长方法、重复代码 |
| | [内联方法](#2-内联方法inline-method) | 过度分解、简单委托 |
| | [提取变量](#3-提取变量extract-variable) | 复杂表达式 |
| | [以查询取代临时变量](#4-以查询取代临时变量replace-temp-with-query) | 临时变量多处使用 |
| | [分解条件表达式](#5-分解条件表达式decompose-conditional) | 复杂条件逻辑 |
| **移动特性** | [移动方法](#6-移动方法move-method) | 特性依恋 |
| | [移动字段](#7-移动字段move-field) | 字段位置不当 |
| | [提取类](#8-提取类extract-class) | 过大类、职责不清 |
| | [内联类](#9-内联类inline-class) | 冗余类 |
| | [隐藏委托](#10-隐藏委托hide-delegate) | 消息链 |
| | [移除中间人](#11-移除中间人remove-middle-man) | 过度委托 |
| **组织数据** | [封装字段](#12-封装字段encapsulate-field) | 公共字段 |
| | [以对象取代基本类型](#13-以对象取代基本类型replace-data-value-with-object) | 基本类型偏执 |
| | [引入参数对象](#14-引入参数对象introduce-parameter-object) | 过长参数列表、数据泥团 |
| **简化条件** | [以多态取代条件表达式](#15-以多态取代条件表达式replace-conditional-with-polymorphism) | Switch语句 |
| | [以策略模式取代条件表达式](#16-以策略模式取代条件表达式replace-conditional-with-strategy) | 条件分支代表不同算法 |
| | [引入空对象](#17-引入空对象introduce-null-object) | 大量null检查 |
| | [合并条件表达式](#18-合并条件表达式consolidate-conditional-expression) | 多个条件相同结果 |
| **简化调用** | [重命名方法](#19-重命名方法rename-method) | 方法名不清晰 |
| | [分离查询与修改](#20-分离查询与修改separate-query-from-modifier) | 方法有副作用 |
| | [以工厂函数取代构造函数](#21-以工厂函数取代构造函数replace-constructor-with-factory-method) | 创建逻辑复杂 |
| **概括关系** | [提取超类](#22-提取超类extract-superclass) | 多个类有相似特性 |
| | [提取接口](#23-提取接口extract-interface) | 需要统一接口 |
| | [折叠继承体系](#24-折叠继承体系collapse-hierarchy) | 子类不再需要 |
| | [以委托取代继承](#25-以委托取代继承replace-inheritance-with-delegation) | 继承关系不合理 |

---

## 组成方法的重构手法

### 1. 提取方法（Extract Method）

**目的**：将一段代码组织成独立的方法。

**适用场景**：过长方法、代码块需要注释才能理解、代码重复

**重构步骤**：
1. 创建新方法，以功能命名
2. 将原代码复制到新方法
3. 检查局部变量和参数
4. 调整参数列表
5. 在原位置调用新方法
6. 运行测试

**示例**：
```python
# 重构前
def print_owing(self, amount):
    print("***********************")
    print("*** Customer Owes ***")
    print("***********************")
    print(f"name: {self.name}")
    print(f"amount: {amount}")

# 重构后
def print_owing(self, amount):
    self._print_banner()
    self._print_details(amount)

def _print_banner(self):
    print("***********************")
    print("*** Customer Owes ***")
    print("***********************")

def _print_details(self, amount):
    print(f"name: {self.name}")
    print(f"amount: {amount}")
```

---

### 2. 内联方法（Inline Method）

**目的**：将方法调用替换为方法体本身。

**适用场景**：方法体与名称一样清晰、方法只是简单委托、过度分解

**重构步骤**：
1. 检查方法不被多态使用
2. 找到所有调用点
3. 将方法调用替换为方法体
4. 删除原方法
5. 运行测试

---

### 3. 提取变量（Extract Variable）

**目的**：将复杂表达式分解为临时变量。

**适用场景**：复杂表达式难以理解、表达式多次使用

**示例**：
```python
# 重构前
if platform.upper().index("MAC") > -1 and browser.upper().index("IE") > -1 and was_initialized() and resize > 0:
    pass

# 重构后
is_mac_os = platform.upper().index("MAC") > -1
is_ie_browser = browser.upper().index("IE") > -1
was_resized = resize > 0

if is_mac_os and is_ie_browser and was_initialized() and was_resized:
    pass
```

---

### 4. 以查询取代临时变量（Replace Temp with Query）

**目的**：将临时变量替换为方法调用。

**适用场景**：临时变量在多处使用、需要在其他方法中访问该值

**示例**：
```python
# 重构前
def calculate_total(self):
    base_price = self.quantity * self.item_price
    if base_price > 1000:
        return base_price * 0.95
    return base_price * 0.98

# 重构后
def calculate_total(self):
    if self._base_price() > 1000:
        return self._base_price() * 0.95
    return self._base_price() * 0.98

def _base_price(self):
    return self.quantity * self.item_price
```

---

### 5. 分解条件表达式（Decompose Conditional）

**目的**：将复杂的条件逻辑分解为独立方法。

**适用场景**：条件表达式复杂难懂、条件分支逻辑复杂

**示例**：
```python
# 重构前
if date.before(SUMMER_START) or date.after(SUMMER_END):
    charge = quantity * winter_rate + winter_service_charge
else:
    charge = quantity * summer_rate

# 重构后
if self._is_summer(date):
    charge = self._summer_charge(quantity)
else:
    charge = self._winter_charge(quantity)

def _is_summer(self, date):
    return not (date.before(SUMMER_START) or date.after(SUMMER_END))
```

---

## 移动特性的重构手法

### 6. 移动方法（Move Method）

**目的**：将方法移动到更合适的类中。

**适用场景**：特性依恋、方法更多使用其他类的数据

**示例**：
```python
# 重构前
class Account:
    def overdraft_charge(self):
        if self.type.is_premium:
            result = 10
            if self.days_overdrawn > 7:
                result += (self.days_overdrawn - 7) * 0.85
            return result
        return self.days_overdrawn * 1.75

# 重构后
class AccountType:
    def overdraft_charge(self, days_overdrawn):
        if self.is_premium:
            result = 10
            if days_overdrawn > 7:
                result += (days_overdrawn - 7) * 0.85
            return result
        return days_overdrawn * 1.75

class Account:
    def overdraft_charge(self):
        return self.type.overdraft_charge(self.days_overdrawn)
```

---

### 7. 移动字段（Move Field）

**目的**：将字段移动到更合适的类中。

**适用场景**：字段更多被其他类使用、字段与另一个类的数据关系更紧密

---

### 8. 提取类（Extract Class）

**目的**：将一个类的部分特性提取到新类中。

**适用场景**：过大类、一个类承担多个职责

**示例**：
```python
# 重构前
class Person:
    def __init__(self):
        self.name = ""
        self.office_area_code = ""
        self.office_number = ""
    
    def get_telephoneNumber(self):
        return f"({self.office_area_code}) {self.office_number}"

# 重构后
class TelephoneNumber:
    def __init__(self):
        self.area_code = ""
        self.number = ""
    
    def get_telephoneNumber(self):
        return f"({self.area_code}) {self.number}"

class Person:
    def __init__(self):
        self.name = ""
        self.office_telephone = TelephoneNumber()
    
    def get_telephoneNumber(self):
        return self.office_telephone.get_telephoneNumber()
```

---

### 9. 内联类（Inline Class）

**目的**：将一个类的特性合并到另一个类中。

**适用场景**：冗余类、类不再承担独立职责

---

### 10. 隐藏委托（Hide Delegate）

**目的**：在类中创建方法来隐藏委托关系。

**适用场景**：消息链、减少客户端对对象结构的依赖

**示例**：
```python
# 重构前
manager = employee.department.manager

# 重构后
class Employee:
    @property
    def manager(self):
        return self.department.manager

manager = employee.manager
```

---

### 11. 移除中间人（Remove Middle Man）

**目的**：让客户端直接访问被委托的对象。

**适用场景**：中间人、委托方法过多

---

## 组织数据的重构手法

### 12. 封装字段（Encapsulate Field）

**目的**：将公共字段改为私有，提供访问方法。

**适用场景**：纯数据类、需要控制字段访问

**示例**：
```cpp
// 重构前
class Person {
public:
    string name;
};

// 重构后
class Person {
private:
    string _name;
public:
    string getName() { return _name; }
    void setName(string name) { _name = name; }
};
```

---

### 13. 以对象取代基本类型（Replace Data Value with Object）

**目的**：将基本类型替换为对象。

**适用场景**：基本类型偏执、基本类型有相关行为

**示例**：
```python
# 重构前
class Order:
    def __init__(self):
        self.customer = ""

# 重构后
class Customer:
    def __init__(self, name):
        self._name = name

class Order:
    def __init__(self):
        self._customer = None
    
    @property
    def customer(self):
        return self._customer.name
```

---

### 14. 引入参数对象（Introduce Parameter Object）

**目的**：将经常一起出现的参数组织成对象。

**适用场景**：过长参数列表、数据泥团

**示例**：
```python
# 重构前
def amount_in_range(start_date, end_date, min_amount, max_amount):
    pass

# 重构后
class DateRange:
    def __init__(self, start_date, end_date):
        self.start = start_date
        self.end = end_date

class AmountRange:
    def __init__(self, min_amount, max_amount):
        self.min = min_amount
        self.max = max_amount

def amount_in_range(date_range: DateRange, amount_range: AmountRange):
    pass
```

---

## 简化条件表达式的重构手法

### 15. 以多态取代条件表达式（Replace Conditional with Polymorphism）

**目的**：用多态替代条件判断。

**适用场景**：Switch语句、基于类型的条件判断

**示例**：
```python
# 重构前
class Employee:
    def pay_amount(self):
        if self.type == "ENGINEER":
            return self.monthly_salary
        elif self.type == "SALESMAN":
            return self.monthly_salary + self.commission
        elif self.type == "MANAGER":
            return self.monthly_salary + self.bonus

# 重构后
class Employee(ABC):
    @abstractmethod
    def pay_amount(self): pass

class Engineer(Employee):
    def pay_amount(self):
        return self.monthly_salary

class Salesman(Employee):
    def pay_amount(self):
        return self.monthly_salary + self.commission

class Manager(Employee):
    def pay_amount(self):
        return self.monthly_salary + self.bonus
```

---

### 16. 以策略模式取代条件表达式（Replace Conditional with Strategy）

**目的**：用策略模式替代条件判断。

**适用场景**：条件分支代表不同算法、需要在运行时切换算法

**示例**：
```go
// 重构前
func calculate(price float64, customerType string) float64 {
    switch customerType {
    case "VIP": return price * 0.8
    case "Regular": return price * 0.95
    default: return price
    }
}

// 重构后
type DiscountStrategy interface {
    Calculate(price float64) float64
}

type VIPDiscount struct{}
func (d *VIPDiscount) Calculate(price float64) float64 { return price * 0.8 }

func calculate(price float64, strategy DiscountStrategy) float64 {
    return strategy.Calculate(price)
}
```

---

### 17. 引入空对象（Introduce Null Object）

**目的**：用空对象替代null检查。

**适用场景**：大量null检查、null有默认行为

**示例**：
```python
# 重构前
if customer is not None:
    plan = customer.get_plan()
else:
    plan = "basic"

# 重构后
class NullCustomer:
    def get_plan(self):
        return "basic"

customer = customer or NullCustomer()
plan = customer.get_plan()
```

---

### 18. 合并条件表达式（Consolidate Conditional Expression）

**目的**：合并多个条件检查为一个。

**适用场景**：多个条件导致相同结果、条件检查语义相关

**示例**：
```python
# 重构前
if self.seniority < 2: return 0
if self.months_disabled > 12: return 0
if self.is_part_time: return 0

# 重构后
def _is_not_eligible(self):
    return (self.seniority < 2 or 
            self.months_disabled > 12 or 
            self.is_part_time)

if self._is_not_eligible(): return 0
```

---

## 简化方法调用的重构手法

### 19. 重命名方法（Rename Method）

**目的**：给方法一个更能表达意图的名称。

**适用场景**：方法名不能表达意图、方法名与实际行为不符

---

### 20. 分离查询与修改（Separate Query from Modifier）

**目的**：将返回值的方法与修改状态的方法分开。

**适用场景**：方法既有返回值又修改状态、需要避免副作用

**示例**：
```python
# 重构前
def get_and_reset_total(self):
    result = self.total
    self.total = 0
    return result

# 重构后
def get_total(self):
    return self.total

def reset_total(self):
    self.total = 0
```

---

### 21. 以工厂函数取代构造函数（Replace Constructor with Factory Method）

**目的**：用工厂方法替代构造函数。

**适用场景**：创建逻辑复杂、需要返回不同类型的对象

**示例**：
```python
# 重构前
engineer = Employee("ENGINEER")

# 重构后
class Employee:
    @staticmethod
    def create_engineer():
        return Employee("ENGINEER")

engineer = Employee.create_engineer()
```

---

## 处理概括关系的重构手法

### 22. 提取超类（Extract Superclass）

**目的**：从多个类中提取公共特性到超类。

**适用场景**：多个类有相似特性、重复代码分布在多个类

**示例**：
```python
# 重构前
class Employee:
    def __init__(self, name, id):
        self.name = name
        self.id = id

class Department:
    def __init__(self, name, id):
        self.name = name
        self.id = id

# 重构后
class Party:
    def __init__(self, name, id):
        self.name = name
        self.id = id

class Employee(Party): pass
class Department(Party): pass
```

---

### 23. 提取接口（Extract Interface）

**目的**：提取公共接口。

**适用场景**：多个类有相同方法、客户端只关心部分方法

**示例**：
```python
# 重构后
from abc import ABC, abstractmethod

class Billable(ABC):
    @abstractmethod
    def get_rate(self): pass

class Employee(Billable):
    def get_rate(self): pass
```

---

### 24. 折叠继承体系（Collapse Hierarchy）

**目的**：合并超类和子类。

**适用场景**：子类不再需要独立存在、超类和子类差异很小

---

### 25. 以委托取代继承（Replace Inheritance with Delegation）

**目的**：用委托替代继承。

**适用场景**：继承关系不合理、子类不需要父类所有特性、被拒绝的遗赠

**示例**：
```python
# 重构前
class Stack(list):
    def push(self, item):
        self.append(item)

# 重构后
class Stack:
    def __init__(self):
        self._data = []
    
    def push(self, item):
        self._data.append(item)
```
