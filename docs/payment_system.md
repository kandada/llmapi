# Payment System - Token Package Sales

## Overview

LLM API Gateway includes a complete payment system for selling token packages. This allows operators to create token packages (monthly subscriptions or prepaid plans) and accept payments through various payment providers.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM API Gateway                          │
├──────────────────────┬──────────────────────────────────────┤
│   Admin Backend      │         Shop Frontend                │
│   /admin/package/   │         /shop/                       │
│   /admin/order/     │         /shop/package/               │
│                      │         /shop/order/                 │
├──────────────────────┴──────────────────────────────────────┤
│                    Payment Service                           │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  PaymentRegistry (Plugin System)                    │   │
│   │  ├── StripeAdapter                                 │   │
│   │  └── PayPalAdapter                                │   │
│   └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    Callback Handlers                         │
│   /callback/stripe   /callback/paypal                       │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ Webhook
                              ▼
                    ┌─────────────────┐
                    │ Payment Platform│
                    │ Stripe / PayPal │
                    └─────────────────┘
```

## Features

- **Package Management**: Create, update, delete token packages
- **Multiple Package Types**: Monthly subscriptions, prepaid plans, one-time purchases
- **Multi-currency Support**: USD, HKD, CNY, EUR, etc.
- **Multiple Payment Providers**: Stripe, PayPal (extensible)
- **Order Management**: Track order status, view statistics
- **Automatic Quota Assignment**: Automatically add quota when payment succeeds
- **Plugin Architecture**: Easy to add new payment providers

## Quick Start: Running Without Payment

LLM API Gateway can run **completely without payment system**. By default, it's just a LLM API gateway.

### Default Mode (No Payment)

Without any payment configuration, llmapi works as a pure LLM API gateway:

```
1. Admin creates channels (fills in API keys)
2. Users register/login and get API keys
3. Users call /v1/chat/completions with their API key
4. Admin can manually add quota to users
```

### How to Get Quota Without Payment

| Method | Description |
|--------|-------------|
| Admin manually adds | Admin sets quota directly in admin panel |
| Redemption code | Admin generates codes, users redeem |
| OAuth login bonus | Optional initial quota for OAuth users |

### Example: Private Use

```bash
# No payment configuration needed
# Just set up channels and use

# 1. Login as admin
curl -X POST http://localhost:3000/api/user/login \
  -H "Content-Type: application/json" \
  -d '{"username":"root","password":"123456"}'

# 2. Create a channel with your API key

# 3. Users register and get their own API keys

# 4. Admin adds quota to users manually
```

## Configuration

### Modes of Operation

LLM API Gateway has **two modes**:

| Mode | Payment System | Use Case |
|------|---------------|----------|
| **Basic Mode** | Disabled | Private use, internal deployment |
| **Commerce Mode** | Enabled | Selling tokens to users |

### All Environment Variables

#### Payment System (Optional)

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_live_xxx              # Stripe secret key
STRIPE_WEBHOOK_SECRET=whsec_xxx           # Stripe webhook secret
STRIPE_MODE=test                           # test or live

# PayPal Configuration
PAYPAL_CLIENT_ID=xxx                      # PayPal client ID
PAYPAL_CLIENT_SECRET=xxx                  # PayPal client secret
PAYPAL_MODE=sandbox                        # sandbox or live
```

#### External App Integration (Optional)

```bash
# System API tokens for external apps (comma-separated)
# Used by aacode, fastclaw to integrate with llmapi
SYSTEM_API_TOKENS=your-app-token-1,your-app-token-2

# Allow external apps to auto-create users
EXTERNAL_APP_AUTO_CREATE_USER=true          # true or false
```

#### Core System (Required for Basic Mode)

```bash
# Server
PORT=3000                                  # Server port
SESSION_SECRET=your-secret-here           # Session secret (change in production!)

# Database
SQL_DSN=                                   # Optional, defaults to SQLite

# New User Quota (when users register themselves)
QUOTA_FOR_NEW_USER=5000000                 # Default quota for new users
```

### Configuration Priority

```
Environment Variables > Code Defaults
```

All configurations are read from environment variables. There is no configuration file or database-stored config for now.

### Changing Configuration

1. **Stop the server**
2. **Modify environment variables** (or `.env` file)
3. **Restart the server**

Note: For production, use a proper process manager (systemd, supervisord) and environment variable management.

## Deployment Architecture

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Server (Internal)                    │
│                                                              │
│   ┌───────────────────┐                                     │
│   │      llmapi       │  ← Always runs locally             │
│   │      :3000        │     127.0.0.1:3000                  │
│   └─────────┬─────────┘                                     │
│             │                                                 │
│             │ Nginx forwards requests                        │
│             │ based on path/IP rules                        │
└─────────────┼───────────────────────────────────────────────┘
              │
     ┌───────┴───────┐
     │     Nginx       │
     │                  │
     │  /shop/*  → Public
     │  /v1/*    → Public   ← LLM API
     │  /callback/* → Public
     │  /admin/* → Internal IP only
     └─────────────────┘
```

### Key Points

- **llmapi never exposed directly** - Nginx is the only entry point
- **Public paths**: `/shop/`, `/v1/`, `/callback/` - accessible from internet
- **Admin paths**: `/admin/`, `/api/` (management) - only internal IP access
- **IP whitelist**: Only configured internal IPs can access admin endpoints

---

### Option A: Subdomain Separation (Recommended)

Use different subdomains for admin and public access.

```
admin.example.com  → Admin only (internal)
api.example.com   → LLM API (public)
shop.example.com  → Shop page (public)
```

#### Nginx Configuration

```nginx
# Admin (internal network only)
server {
    listen 80;
    server_name admin.example.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
    }

    # IP whitelist
    allow 10.0.0.0/8;       # Internal network
    allow 172.16.0.0/12;    # Internal network
    allow 192.168.0.0/16;   # Internal network
    allow 127.0.0.1;        # Localhost
    deny all;                 # Deny all other IPs
}

# API & Shop (public)
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
    }
}

# Shop page (public)
server {
    listen 80;
    server_name shop.example.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
    }
}
```

#### DNS Setup

```
# External DNS (public)
api.example.com     → Server Public IP
shop.example.com   → Server Public IP

# Internal DNS (or /etc/hosts)
admin.example.com  → Server Internal IP
```

---

### Option D: Path-Based Separation

Single domain with path-based access control.

```
example.com/admin/*  → Internal IP only
example.com/shop/*   → Public
example.com/v1/*    → Public
```

#### Nginx Configuration

```nginx
upstream llmapi {
    server 127.0.0.1:3000;
}

server {
    listen 80;
    server_name example.com;

    # === PUBLIC PATHS ===

    # Shop page (public)
    location /shop/ {
        proxy_pass http://llmapi;
        proxy_set_header Host $host;
    }

    # LLM API (public)
    location /v1/ {
        proxy_pass http://llmapi;
        proxy_set_header Host $host;
    }

    # Payment callbacks (public - Stripe/PayPal webhooks)
    location /callback/ {
        proxy_pass http://llmapi;
        proxy_set_header Host $host;
    }

    # Shop API (public)
    location /api/external/ {
        proxy_pass http://llmapi;
        proxy_set_header Host $host;
    }

    # === ADMIN PATHS (Internal IP only) ===

    location /admin/ {
        proxy_pass http://llmapi;

        # IP whitelist
        allow 10.0.0.0/8;       # Internal network
        allow 172.16.0.0/12;    # Internal network
        allow 192.168.0.0/16;   # Internal network
        allow 127.0.0.1;        # Localhost
        deny all;                 # Deny all other IPs
    }

    # Management API (internal only)
    location /api/user/ {
        proxy_pass http://llmapi;

        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        allow 127.0.0.1;
        deny all;
    }

    location /api/channel/ {
        proxy_pass http://llmapi;

        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        allow 127.0.0.1;
        deny all;
    }
}
```

---

### Which Option to Choose?

| Scenario | Recommended |
|----------|-------------|
| Simple personal use | Option A |
| Clear separation of concerns | Option A |
| Single domain, simpler DNS | Option D |
| Enterprise/multi-tenant | Option D |

---

### Security Checklist

- [ ] Change `SESSION_SECRET` to a strong random value
- [ ] Configure firewall to block direct access to port 3000
- [ ] Use HTTPS (Let's Encrypt recommended)
- [ ] Set up IP whitelist for admin paths
- [ ] Use strong passwords for admin accounts
- [ ] Regularly update llmapi to latest version

---

## Payment System Setup (Optional)

### When to Enable Payment

Enable payment system when you want:
- Sell token packages to users
- Accept online payments (Stripe/PayPal)
- Allow users to self-service purchase quota

### When NOT to Enable Payment

- Private/internal use
- Just sharing with friends
- Using manual quota assignment
- Any scenario where you don't need online payments

## Configuration

### Environment Variables

#### Stripe Configuration
```bash
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_MODE=test  # or live
```

#### PayPal Configuration
```bash
PAYPAL_CLIENT_ID=xxx
PAYPAL_CLIENT_SECRET=xxx
PAYPAL_MODE=sandbox  # or live
```

### Payment Provider Setup

#### Stripe Setup

1. Create a Stripe account at https://stripe.com
2. Get your API keys from the Stripe Dashboard
3. Set up webhook endpoint: `https://your-domain.com/callback/stripe`
4. Enable the following events for the webhook:
   - `checkout.session.completed`
5. Configure the environment variables

#### PayPal Setup

1. Create a PayPal Developer account at https://developer.paypal.com
2. Create a sandbox/live app
3. Get Client ID and Secret
4. Set the webhook to: `https://your-domain.com/callback/paypal`
5. Configure the environment variables

## API Reference

### Shop API (Public/User)

#### List Packages
```
GET /shop/package/
```
Returns all enabled packages.

Response:
```json
{
  "success": true,
  "data": {
    "packages": [
      {
        "id": 1,
        "name": "Basic Plan",
        "description": "1000000 tokens",
        "package_type": "prepaid",
        "quota": 1000000,
        "prices": {"USD": 19.99, "HKD": 156},
        "payment_providers": "stripe,paypal"
      }
    ]
  }
}
```

#### Get Package Detail
```
GET /shop/package/{id}
```

#### List Payment Providers
```
GET /shop/payment/providers
```

#### Create Order
```
POST /shop/order/create
```
Requires user authentication.

Request:
```json
{
  "package_id": 1,
  "currency": "USD",
  "payment_provider": "stripe",
  "return_url": "https://your-app.com/success",
  "cancel_url": "https://your-app.com/shop"
}
```

Response:
```json
{
  "success": true,
  "data": {
    "order_no": "ORD-ABCD1234EFGH5678",
    "payment_url": "https://checkout.stripe.com/xxx",
    "external_order_no": "cs_xxx"
  }
}
```

#### Get Order Status
```
GET /shop/order/{order_no}
```
Requires user authentication.

#### List User Orders
```
GET /shop/order/
```
Requires user authentication.

### Admin API

#### List All Packages
```
GET /admin/package/
```
Requires admin authentication.

#### Create Package
```
POST /admin/package/
```

Request:
```json
{
  "name": "Basic Plan",
  "description": "1000000 tokens",
  "package_type": "prepaid",
  "quota": 1000000,
  "prices": {"USD": 19.99, "HKD": 156},
  "duration_days": -1,
  "payment_providers": "stripe,paypal",
  "sort_order": 0
}
```

#### Package Field Reference

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | - | Package display name |
| `description` | string | No | "" | Package description shown to users |
| `package_type` | string | No | `prepaid` | Type: `prepaid`, `monthly`, or `once` |
| `quota` | integer | Yes | 0 | Token quota (e.g., 10000000 = 10M tokens) |
| `prices` | object | Yes | `{}` | Price per currency: `{"USD": 20.00, "HKD": 156}` |
| `duration_days` | integer | No | -1 | Validity period in days; `-1` = unlimited |
| `max_tokens` | integer | No | -1 | Max tokens per request; `-1` = unlimited |
| `allowed_models` | string | No | "" | Allowed models (comma-separated), empty = all |
| `status` | integer | No | 1 | `1` = enabled, `0` = disabled |
| `payment_providers` | string | No | `stripe` | Enabled providers: `stripe`, `paypal`, or both `stripe,paypal` |
| `sort_order` | integer | No | 0 | Display order (smaller number = higher priority) |

**Important: Package Visibility Filtering**

The shop page automatically filters packages based on configured payment providers:

1. **Shop loads packages** via `GET /shop/package/` (only enabled packages)
2. **Shop loads payment providers** via `GET /shop/payment/providers`
3. **Packages are filtered** - only packages whose `payment_providers` overlap with configured providers are shown

**Example:**
- Package A has `payment_providers: "stripe"`
- Package B has `payment_providers: "paypal"`
- Package C has `payment_providers: "stripe,paypal"`

If only Stripe is configured (`STRIPE_SECRET_KEY` set, no PayPal):
- Package A: **Visible** (stripe matches)
- Package B: **Hidden** (paypal not configured)
- Package C: **Visible** (stripe is one of the providers)

If both Stripe and PayPal are configured:
- All packages visible

This prevents users from seeing packages they cannot pay for.

**Package Type Options:**

| Type | Description |
|------|-------------|
| `prepaid` | Prepaid tokens, consumed over time |
| `monthly` | Monthly subscription with recurring quota |
| `once` | One-time purchase, no recurring |

**Price Configuration:**

```json
{
  "prices": {
    "USD": 20.00,
    "HKD": 156.00,
    "CNY": 145.00,
    "EUR": 18.50
  }
}
```

Frontend displays price based on user's selected currency or browser locale.

**Example Package Configurations:**

```json
{
  "name": "Starter",
  "description": "1M tokens - perfect for getting started",
  "package_type": "prepaid",
  "quota": 1000000,
  "prices": {"USD": 2.00},
  "duration_days": -1,
  "sort_order": 1
}
```

```json
{
  "name": "Pro Monthly",
  "description": "10M tokens/month subscription",
  "package_type": "monthly",
  "quota": 10000000,
  "prices": {"USD": 18.00},
  "duration_days": 30,
  "sort_order": 2
}
```

```json
{
  "name": "Enterprise",
  "description": "100M tokens, all models, priority support",
  "package_type": "prepaid",
  "quota": 100000000,
  "prices": {"USD": 150.00},
  "duration_days": -1,
  "max_tokens": -1,
  "allowed_models": "",
  "sort_order": 3
}
```

#### Admin UI: Package Management

The easiest way to manage packages is via the Admin UI:

1. **Access Admin Panel:** Open `http://localhost:3000/` (or your domain)
2. **Login:** Use admin credentials
3. **Navigate to Shop:** Click the **Shop** tab in the top navigation
4. **Manage Packages:**
   - View all packages in the list
   - Click **Edit** to modify a package
   - Click **Delete** to remove a package
   - Click **New Package** to create a new one

**Shop Tab Features:**
- Package list with name, quota, price, status, type
- Quick enable/disable toggle
- Sort order drag handles (if implemented)
- Create/Edit/Delete operations

#### Update Package
```
PUT /admin/package/{id}
```

#### Delete Package
```
DELETE /admin/package/{id}
```

#### List All Orders
```
GET /admin/order/
```

#### Get Order Statistics
```
GET /admin/order/stats
```

Response:
```json
{
  "success": true,
  "data": {
    "total": 100,
    "pending": 5,
    "paid": 90,
    "cancelled": 5
  }
}
```

### Callback API

#### Stripe Callback
```
POST /callback/stripe
```
Handles Stripe webhook events. Signature verification is done automatically.

#### PayPal Callback
```
POST /callback/paypal
```
Handles PayPal webhook events.

## Payment Flow

```
1. User browses packages at /shop
   → GET /shop/package/

2. User selects a package and clicks "Purchase"
   → If not logged in: redirect to login
   → If logged in: proceed to checkout

3. User selects payment provider and confirms
   → POST /shop/order/create
   → Returns payment URL

4. User is redirected to payment provider
   → Completes payment

5. Payment provider sends webhook to /callback/{provider}
   → System verifies signature
   → Updates order status to "paid"
   → Adds quota to user account

6. User is redirected back to return_url
   → Page can poll /shop/order/{order_no} for status
```

## Payment Adapter Plugin System

### Creating a New Payment Adapter

1. Create a new file in `payment/adapters/`:

```python
# payment/adapters/my_adapter.py
from payment.adapter import PaymentAdapter, PaymentResult, CallbackResult, register_payment_adapter

@register_payment_adapter("myprovider")
class MyProviderAdapter(PaymentAdapter):
    name = "myprovider"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("MYPROVIDER_API_KEY")
        self._enabled = bool(self.api_key)

    def get_config_schema(self) -> dict:
        return {
            "name": "My Provider",
            "description": "My custom payment provider",
            "fields": []
        }

    async def create_payment(self, order_no, amount, currency, description, metadata=None):
        # Implement payment creation
        return PaymentResult(success=True, payment_url="...")

    async def verify_callback(self, request):
        # Verify webhook signature
        return CallbackResult(success=True, order_no="...")

    async def handle_callback(self, request):
        return await self.verify_callback(request)

    async def refund(self, order_no, external_order_no, amount=None):
        # Implement refund logic
        return True

    async def cancel_order(self, order_no, external_order_no):
        # Implement order cancellation
        return True
```

2. Import the adapter in `routers/main.py`:

```python
import payment.adapters.my_adapter
```

## Database Schema

### packages Table
| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Primary key |
| name | VARCHAR(100) | Package name |
| description | TEXT | Package description |
| package_type | VARCHAR(20) | prepaid/monthly/once |
| quota | BIGINT | Token quota |
| prices | TEXT | JSON: {"USD": 19.99, "HKD": 156} |
| duration_days | INTEGER | Validity period, -1 = forever |
| status | INTEGER | 1=enabled, 0=disabled |
| payment_providers | TEXT | Comma-separated: stripe,paypal |
| sort_order | INTEGER | Display order |

### orders Table
| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Primary key |
| order_no | VARCHAR(64) | Internal order number |
| user_id | INTEGER | User ID |
| package_id | INTEGER | Package ID |
| payment_provider | VARCHAR(20) | stripe/paypal |
| external_order_no | VARCHAR(128) | External payment order ID |
| amount | NUMERIC(10,2) | Payment amount |
| currency | VARCHAR(10) | Currency code |
| status | VARCHAR(20) | pending/paid/cancelled/refunded |
| created_time | BIGINT | Creation timestamp |
| paid_time | BIGINT | Payment timestamp |
| callback_data | TEXT | Raw callback data |

## Frontend Integration

### Shop Page
Access the shop page at: `/shop`

The shop page allows users to:
- Browse available packages
- Select currency
- Choose payment provider
- Complete purchase
- View order history

### Integration with External Apps (aacode, fastclaw)

To integrate token purchase into your application:

1. **Open shop in new window/tab:**
```javascript
window.open('https://your-llmapi-domain.com/shop', '_blank');
```

2. **After payment, return to your app:**
Set `return_url` parameter when creating order to point back to your app.

3. **Check payment status:**
```javascript
// Poll order status
const checkOrder = async (orderNo) => {
  const response = await fetch(`/shop/order/${orderNo}`);
  const result = await response.json();
  if (result.success && result.data.status === 'paid') {
    // Payment completed, quota added
  }
};
```

## Security Notes

1. **Webhook Signature Verification**: All payment callbacks are verified using the provider's signature mechanism
2. **Idempotency**: The system handles duplicate callbacks gracefully
3. **Order Validation**: Order status transitions are validated before processing
4. **Quota Assignment**: Only completed payments trigger quota assignment

## Troubleshooting

### Payment not processing
1. Check webhook is properly configured
2. Verify callback URL is accessible
3. Check payment provider dashboard for error details

### Quota not added
1. Check order status in admin panel
2. Verify callback was received
3. Check server logs for errors

### Stripe checkout not loading
1. Verify Stripe keys are correct
2. Check Stripe dashboard for API errors
3. Ensure webhook is properly configured

---

## External App Integration (aacode, fastclaw)

LLM API Gateway can be integrated with external applications like aacode and fastclaw to provide token purchasing functionality.

### Configuration

Set the following environment variables to enable external app integration:

```bash
# System API tokens (comma-separated) - tokens for external apps
SYSTEM_API_TOKENS=your-app-token-1,your-app-token-2

# Allow external apps to auto-create users
EXTERNAL_APP_AUTO_CREATE_USER=true
```

### API Endpoints

#### Link or Create User
```
POST /api/external/user/link-or-create
```
Links an existing user or creates a new user based on email.

Headers:
```
Authorization: Bearer <system-api-token>
```

Request:
```json
{
  "email": "user@example.com",
  "username": "username",      // optional
  "display_name": "User Name"    // optional
}
```

Response:
```json
{
  "success": true,
  "data": {
    "user_id": 1,
    "username": "user",
    "email": "user@example.com",
    "quota": 1000000,
    "used_quota": 0,
    "api_key": "sk-xxxx-xxxx-xxxx",
    "created": true
  }
}
```

#### Get User Quota
```
GET /api/external/user/{user_id}/quota
```

Headers:
```
Authorization: Bearer <system-api-token>
```

Response:
```json
{
  "success": true,
  "data": {
    "user_id": 1,
    "username": "user",
    "email": "user@example.com",
    "quota": 1000000,
    "used_quota": 0,
    "tokens": [
      {
        "id": 1,
        "name": "API Key",
        "key": "sk-xxxx-xxxx-xxxx",
        "remain_quota": 1000000,
        "unlimited_quota": false,
        "status": 1
      }
    ]
  }
}
```

#### Get User API Key
```
GET /api/external/user/{user_id}/api-key
```

Headers:
```
Authorization: Bearer <system-api-token>
```

Response:
```json
{
  "success": true,
  "data": {
    "user_id": 1,
    "api_key": "sk-xxxx-xxxx-xxxx",
    "remain_quota": 1000000,
    "unlimited_quota": false
  }
}
```

### Integration Example (aacode)

```python
# aacode: user logs in with email
async def on_user_login(email: str):
    # Call llmapi to link/create user and get API key
    response = await llmapi.post('/api/external/user/link-or-create', {
        'email': email
    }, headers={
        'Authorization': 'Bearer your-system-api-token'
    })

    if response['success']:
        api_key = response['data']['api_key']
        quota = response['data']['quota']

        # Save to aacode config
        save_config(
            LLM_API_KEY=api_key,
            LLM_QUOTA=quota
        )

        # Update UI to show remaining quota
        update_quota_display(quota)

# aacode: check quota before each request
async def check_and_refresh_quota():
    config = load_config()
    response = await llmapi.get(f'/api/external/user/{config.user_id}/quota',
        headers={'Authorization': f'Bearer {SYSTEM_API_TOKEN}'})

    if response['success']:
        new_quota = response['data']['quota']
        if new_quota != config.LLM_QUOTA:
            update_config(LLM_QUOTA=new_quota)
            if new_quota <= 0:
                show_purchase_warning()
```

### Security Notes

1. **System API Token**: Keep this token secret. It allows external apps to manage users.
2. **Auto-create Users**: When enabled, external apps can create users without password (they use llmapi for quota only).
3. **No Password**: External app users don't have passwords in llmapi - they authenticate through your external app.