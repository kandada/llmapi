# 额度设计文档 (Quota Design)

## 1. 设计原则

### 1.1 核心原则
- **消耗必须记录**：无论谁、用什么Token，消耗都要记录到 `User.used_quota`
- **额度基于用户**：用户额度存储在 `User.quota` 和 `User.used_quota`，Token 只是访问凭证
- **Token 额度可选**：所有用户都能选择"有限额度"或"无限额度"的Token
- **用户额度用完则无法使用**：Token 有限 + 用户额度用完 → 无法使用

### 1.2 角色定义

| 角色 | 值 | 说明 |
|------|-----|------|
| Guest | 0 | 访客，未登录 |
| User | 1 | 普通用户 |
| Admin | 10 | 管理员 |
| Root | 100 | 超级管理员 |

---

## 2. 数据模型

### 2.1 User 模型

```
User
├── id: 主键
├── username: 用户名
├── quota: 账户总预算（充值、兑换码、管理员调整获得）
├── used_quota: 累计已消耗
└── role: 角色 (0=guest, 1=user, 10=admin, 100=root)
```

**计算公式**：
```
User.remain_quota = User.quota - User.used_quota  (计算得出，不存储)
```

### 2.2 Token 模型

```
Token
├── id: 主键
├── user_id: 关联用户
├── unlimited_quota: True/False
│   ├── True:  不检查额度限制，但仍记录消耗
│   └── False: 检查 Token.remain_quota 和 User.remain_quota
├── remain_quota: 剩余额度（仅对有限Token有意义）
└── used_quota: 该Token累计已消耗
```

---

## 3. 消耗流程

### 3.1 通用消耗流程

```
API请求进入
    │
    ▼
┌─────────────────────────────────────────┐
│ 1. 计算消耗量 (BillingCalculator)        │
│    estimated_quota = calculate(...)      │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ 2. User 额度检查                         │
│    if User.quota - User.used_quota <= 0: │
│        if not Token.unlimited_quota:     │
│            return 拒绝                   │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ 3. 记录消耗                             │
│    User.used_quota += estimated_quota    │
│    (Token 额度扣减见下方)               │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ 4. Token 额度扣减（仅有限Token）         │
│    if not Token.unlimited_quota:        │
│        Token.remain_quota -= est_quota  │
│        Token.used_quota += est_quota    │
└─────────────────────────────────────────┘
    │
    ▼
    成功响应
```

### 3.2 角色与额度策略

| 角色 | User.quota | User.used_quota | Token.remain_quota | 说明 |
|------|-----------|----------------|-------------------|------|
| **Root** | 无限 (1e15) | 记录 | 不检查 | 超级管理员，额度无限制 |
| **Admin** | 无限 (1e15) | 记录 | 不检查 | 管理员，额度无限制 |
| **User** | 充值获得 | 记录 | 检查 | 普通用户，受额度限制 |

### 3.3 额度检查规则

```
def check_quota(token, user, estimated_quota):
    # 1. Admin/Root 用户：跳过 User 级别额度检查
    if user.role >= 10:  # Admin or Root
        return True

    # 2. 检查 User 级别剩余额度
    user_remain = user.quota - user.used_quota
    if user_remain <= 0:
        if not token.unlimited_quota:
            return False  # 拒绝

    # 3. 有限 Token 检查
    if not token.unlimited_quota:
        if token.remain_quota < estimated_quota:
            return False  # 拒绝

    return True
```

---

## 4. 仪表盘显示

### 4.1 显示规则

| 角色 | 可用额度显示 | 已用额度显示 |
|------|-------------|-------------|
| **Root** | "不限额度" | 真实消耗值 |
| **Admin** | "不限额度" | 真实消耗值 |
| **User** | `User.quota - User.used_quota` | 真实消耗值 |

### 4.2 前端交互

- **充值/兑换码兑换后**：刷新 `userInfo`，可用额度自动更新
- **Admin/Root**：前端不显示 `userInfo.quota` 数值，显示"不限额度"

---

## 5. Token 创建规则

### 5.1 所有用户都可以

- 创建"有限额度" Token
- 创建"无限额度" Token
- 设置 Token 的有效期、可用模型、IP限制等

### 5.2 有限 Token 的限制

- `Token.remain_quota > 0` 才能使用
- 当 `Token.remain_quota < estimated_quota` 时拒绝
- 当 `User.quota - User.used_quota <= 0` 时拒绝

### 5.3 无限 Token 的特点

- `Token.unlimited_quota = True`
- 不检查 `Token.remain_quota`
- 仍受 `User.quota - User.used_quota` 限制（Admin/Root 除外）
- 仍记录消耗到 `User.used_quota`

---

## 6. 兑换码规则

### 6.1 普通用户

- 兑换码兑换到 `User.quota`
- 兑换后 `User.remain_quota` 增加

### 6.2 Admin/Root

- Admin/Root 也可以使用兑换码
- 兑换后额度增加，但由于 Admin/Root 是"无限额度"，实际不检查

---

## 7. 代码关键位置

### 7.1 额度检查入口
- `llmapi/middleware/auth.py:64` - Token 级别额度检查
- `llmapi/billing/calculator.py:262-277` - PreconsumeQuotaService.preconsume()

### 7.2 消耗记录
- `llmapi/billing/calculator.py:275-276` - User.used_quota 增加
- `llmapi/billing/calculator.py:284-289` - Post-consume 调整

### 7.3 仪表盘数据
- `llmapi/routers/external.py:93` - 返回 user.quota, user.used_quota
- `llmapi/web/index.html:448` - 显示可用额度
- `llmapi/web/index.html:452` - 显示已用额度

---

## 8. 数据库字段

### users 表
```sql
quota BIGINT DEFAULT 0        -- 账户总预算
used_quota BIGINT DEFAULT 0   -- 已消耗总量
```

### tokens 表
```sql
unlimited_quota BOOLEAN DEFAULT FALSE  -- 是否无限额度
remain_quota BIGINT DEFAULT 0          -- 剩余额度
used_quota BIGINT DEFAULT 0             -- 该Token已消耗
```

---

## 9. 版本历史

| 版本 | 日期 | 修改内容 |
|------|------|---------|
| 1.0 | 2026-04-25 | 初始文档，定义额度设计规则 |
