# U Money AI API 约定

## 1. 通用规则

基础路径示例：

```text
https://<ai-service-domain>
```

除健康检查外，所有接口都要求 Supabase 登录：

```http
Authorization: Bearer <Supabase access token>
Content-Type: application/json
```

通用约定：

- 请求和响应使用 UTF-8 JSON；
- 金额使用十进制字符串，例如 `"35.50"`，避免小数精度问题；
- 日期使用 `YYYY-MM-DD`；
- 月份使用 `YYYY-MM`；
- 类型只允许 `"收入"` 或 `"支出"`；
- 每个响应包含 `request_id`，方便排查问题；
- AI 响应包含 `prompt_version`；
- 前端不得把令牌写入网址参数或日志。

## 2. POST /ai/parse-transactions

### 用途

把一段自然语言解析成一条或多条待确认记录。该接口只解析，不写数据库。

### 请求

```json
{
  "text": "昨天午饭 32 元，坐地铁 4 元",
  "reference_date": "2026-07-26",
  "timezone": "Asia/Shanghai",
  "currency": "CNY"
}
```

字段规则：

| 字段 | 必填 | 规则 |
|---|---:|---|
| `text` | 是 | 去除首尾空格后 1 至 1000 个字符 |
| `reference_date` | 是 | 合法日期，用于理解“今天、昨天”等词 |
| `timezone` | 是 | 第一版只接受允许列表中的时区 |
| `currency` | 是 | 第一版固定为 `CNY` |

一次最多返回 20 条候选记录。

### 成功响应：200

```json
{
  "request_id": "req_01J...",
  "prompt_version": "parse-transactions-v1",
  "needs_confirmation": true,
  "transactions": [
    {
      "candidate_id": "candidate-1",
      "date": "2026-07-25",
      "type": "支出",
      "amount": "32.00",
      "category": "餐饮",
      "note": "午饭",
      "confidence": 0.96,
      "missing_fields": []
    },
    {
      "candidate_id": "candidate-2",
      "date": "2026-07-25",
      "type": "支出",
      "amount": "4.00",
      "category": "交通",
      "note": "地铁",
      "confidence": 0.94,
      "missing_fields": []
    }
  ],
  "warnings": []
}
```

`confidence` 表示模型对解析结果的信心，只能作为界面提示，不能替代用户确认。

如果信息不完整，可以返回：

```json
{
  "candidate_id": "candidate-1",
  "date": "2026-07-26",
  "type": "支出",
  "amount": null,
  "category": "餐饮",
  "note": "午饭",
  "confidence": 0.52,
  "missing_fields": ["amount"]
}
```

前端必须要求用户补齐缺失字段，不能直接保存。

### 业务验证

- `amount` 必须大于 0，并设置合理上限；
- `date` 必须是合法日期；
- `category` 最长 50 个字符；
- `note` 最长 200 个字符；
- 不认识的类型不能自动改成收入或支出；
- 不能根据文本猜测用户身份、账号或数据库记录；
- 模型返回的额外字段一律拒绝。

## 3. POST /ai/monthly-summary

### 用途

生成一个月的简短消费总结。前端用普通代码计算月度汇总后发送给后端；不发送完整账单、日期明细或备注。后端不重新计算金额，只验证格式并要求模型解释汇总。

### 请求

```json
{
  "month": "2026-07",
  "statistics_period_start": "2026-07-01",
  "statistics_period_end": "2026-07-31",
  "currency": "CNY",
  "totals": {
    "income": "8000.00",
    "expense": "3250.50",
    "balance_change": "4749.50",
    "record_count": 42
  },
  "expense_categories": [
    {"category": "餐饮", "amount": "1200.00", "percentage": 36.92}
  ],
  "comparison": {
    "previous_month": "2026-06",
    "available": true,
    "income_change": "0.00",
    "expense_change": "300.00",
    "balance_change": "-300.00"
  }
}
```

### 有数据响应：200

```json
{
  "request_id": "req_01J...",
  "prompt_version": "monthly-summary-v1",
  "month": "2026-07",
  "data_status": "available",
  "statistics_period_start": "2026-07-01",
  "statistics_period_end": "2026-07-31",
  "summary": {
    "overview": "本月收入和支出统计已整理完成。",
    "largest_category_observation": "支出主要集中在餐饮类别。",
    "change_observation": "与上月相比，支出有所增加。",
    "neutral_observation": "这份内容只根据当前选择月份的汇总数据生成。",
    "suggestion": "可以从支出占比较高的类别中挑选一项，观察下次记录时是否有调整空间。"
  },
  "warnings": [
    "该总结只根据当前账单生成，不构成财务建议。"
  ]
}
```

`totals`、`expense_categories` 和 `comparison` 必须由前端普通代码计算。模型只能生成 `summary` 中的文字，且不得在文字中重新计算或补充数字。

### 无数据响应：200

无数据时不调用模型：

```json
{
  "request_id": "req_01J...",
  "prompt_version": "monthly-summary-v1",
  "month": "2026-07",
  "data_status": "empty",
  "statistics_period_start": "2026-07-01",
  "statistics_period_end": "2026-07-31",
  "summary": null,
  "warnings": ["这个月还没有记录。"]
}
```

## 4. GET /health

### 用途

供本地检查和部署平台判断服务是否正在运行。该接口不需要登录，也不调用模型和 Supabase。

### 响应：200

```json
{
  "status": "ok",
  "service": "u-money-ai",
  "version": "0.1.0"
}
```

该接口不能返回环境变量、模型名称、密钥状态或数据库信息。

## 5. 统一错误格式

```json
{
  "error": {
    "code": "MODEL_TIMEOUT",
    "message": "智能服务响应超时，请稍后重试或使用手动记账。",
    "retryable": true,
    "request_id": "req_01J..."
  }
}
```

建议状态码：

| 状态码 | 场景 |
|---:|---|
| 400 | 请求 JSON 无法读取或业务输入不合理 |
| 401 | 未登录、令牌无效或已过期 |
| 403 | 用户没有权限访问该资源 |
| 413 | 请求正文过大 |
| 422 | Pydantic 数据验证失败 |
| 429 | 调用次数超过限制 |
| 502 | 模型供应商返回无效结果 |
| 503 | AI 功能临时不可用 |
| 504 | 模型调用超时 |

前端只显示适合普通用户理解的 `message`。供应商原始错误、内部代码位置和密钥信息不能返回。

## 6. 结构化输出验证

模型返回结果必须经过两层检查：

1. 格式检查：Pydantic 验证字段、类型、必填项、长度、枚举和多余字段。
2. 业务检查：金额范围、日期合理性、候选条数、类别长度和月度统计一致性。

建议模型输出设置为严格 JSON Schema；即使供应商声称已经保证格式，后端仍要用 Pydantic 再验证一次。

验证失败时：

- 最多进行一次结构修复请求；
- 第二次仍失败则返回 `MODEL_INVALID_OUTPUT`；
- 不把未经验证的数据交给前端；
- 不自动写入 Supabase。

## 7. 幂等与写入原则

这三个 AI 接口本身不修改账单，因此重复调用不会产生重复记录。

用户确认自然语言解析结果后，由前端调用现有 Supabase 新增流程。后续实现时应为确认按钮增加防重复点击状态，但本 AI 接口不承担数据库写入职责。
