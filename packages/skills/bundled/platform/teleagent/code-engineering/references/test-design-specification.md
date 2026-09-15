
# Test Design Specification

Rules for writing correct unit tests. Every test MUST pass this checklist before being finalized.

## Pre-Writing: Understand What You're Testing

Before writing any test code, answer these questions for each test case:

| Question | Why It Matters |
|----------|---------------|
| What specific code path does this test exercise? | Prevents "testing everything" or "testing nothing" |
| What are the exact inputs? | Including edge values |
| What is the exact expected output? | **Must calculate manually, never estimate** |
| What assertion method? | `assertEqual` for exact, `assertRaises` for errors, `pytest.approx` for floats |

## Expected Value Calculation Rules

### Rule 1: Calculate, Never Guess
For every `assertEqual(expected, actual)`, the `expected` value must be derived by:
- Mentally executing the code path with the test inputs
- Writing out the calculation step-by-step
- NOT relying on "it should be about X" intuition

### Rule 2: Boundary Precision
Before writing a test involving thresholds/ranges, explicitly document:
```
threshold = 20
Items: A(stock=5), B(stock=10), C(stock=30)
Match condition: stock < threshold
Expected matches: A(5<20 ✓), B(10<20 ✓), C(30<20 ✗) → 2 items
```

### Rule 3: Combined Conditions
For tests with multiple filter conditions, check each item against ALL conditions:
```
Filters: keyword="蓝牙" AND min_price=100 AND in_stock_only=True
Items:
  A: "蓝牙耳机" price=199 stock=50 → keyword ✓ price ✓ stock ✓ → MATCH
  B: "蓝牙音箱" price=399 stock=30 → keyword ✓ price ✓ stock ✓ → MATCH
  C: "有线耳机" price=59 stock=0   → keyword ✗ → SKIP (first fail)
Expected: 2 items (A and B)
```

### Rule 4: String Matching
- `"abc" in "abc"` → True
- `"abc" in "a bc"` → False (space matters)
- `"ABC" in "abc"` → False (case matters unless `.lower()` is used)
- Always verify: does the function do case-insensitive matching? Don't assume.

## Test Structure Template

```python
class Test[MethodName](unittest.TestCase):
    """[方法名] 的测试"""

    def setUp(self):
        """每个测试前的公共初始化"""
        self.system = InventorySystem()
        self.system.add_product("A001", "商品A", 10.0, 100, "电子")

    # --- 正常路径 ---

    def test_[method]_basic(self):
        """基本功能：[一句话描述]"""
        result = self.system.method(args)
        self.assertEqual(result, expected)  # expected 已手动计算

    # --- 边界值 ---

    def test_[method]_empty_input(self):
        """空输入"""
        result = self.system.method(empty_input)
        self.assertEqual(result, expected_empty_result)

    def test_[method]_zero_value(self):
        """零值处理"""
        # 明确：0 是合法输入还是应该报错？
        ...

    def test_[method]_boundary_threshold(self):
        """阈值边界"""
        # 明确：是 < 还是 <= ？列出所有测试数据及其预期匹配
        ...

    # --- 异常路径 ---

    def test_[method]_invalid_input_raises(self):
        """非法输入应抛出异常"""
        with self.assertRaises(ValueError):
            self.system.method(invalid_input)

    def test_[method]_duplicate_rejected(self):
        """重复数据被拒绝"""
        ...

    # --- 组合/复杂场景 ---

    def test_[method]_combined_conditions(self):
        """组合条件"""
        # 逐条列出每个测试数据点是否匹配每个条件
        ...
```

## Anti-Patterns (DO NOT)

| Anti-Pattern | Why Wrong | Fix |
|-------------|----------|-----|
| Guess expected value from "general understanding" | Math errors | Calculate step by step |
| Write threshold test without listing all items and their match status | Off-by-one | Document every item |
| Test "keyword search" with spaces in the keyword | False negative | Match what the function actually does |
| Use `NamedTemporaryFile` without `encoding="utf-8"` | GBK on Windows | Always specify encoding |
| Assert count=1 when actually 2 items match | Wrong expectation | List and count manually |
| Write test for "combined search" but only check one condition | Incomplete | Verify ALL conditions per item |

## Post-Writing: Dry Run Checklist

After writing all tests, BEFORE running them:

1. For each assertion, re-read the production code and trace the execution with the test inputs
2. Verify: does the code actually implement what the test assumes? (e.g., does it use `<` or `<=`?)
3. Verify: are test data items correctly set up? (stock values, prices, names)
4. Count expected results manually one more time
5. Only then run the tests