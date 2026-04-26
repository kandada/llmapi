# Management API

Management API endpoints are prefixed with `/api/`. These endpoints are used for managing users, channels, tokens, and viewing logs.

**Note:** Some endpoints require admin privileges.

## Authentication

Most endpoints require login authentication via cookie:

```bash
curl -b cookies.txt http://localhost:3000/api/channel/
```

Login first:

```bash
curl -c cookies.txt -X POST http://localhost:3000/api/user/login \
  -H "Content-Type: application/json" \
  -d '{"username":"root","password":"123456"}'
```

---

## User Management

### `POST /api/user/register`

Register a new user.

**Request Body:**

```json
{
  "username": "newuser",
  "password": "password123"
}
```

### `POST /api/user/login`

Login and get authentication cookie.

```json
{
  "username": "root",
  "password": "123456"
}
```

### `GET /api/user/self`

Get current user information.

### `PUT /api/user/self`

Update current user information.

### `GET /api/user/token`

Get current user's access token.

### `GET /api/user/`

List all users (admin only).

### `GET /api/user/{user_id}`

Get specific user info.

### `POST /api/user/`

Create new user (admin only).

### `PUT /api/user/`

Update user (admin only).

### `DELETE /api/user/{user_id}`

Delete user (admin only).

---

## Token Management

### `GET /api/token/`

List all tokens.

### `POST /api/token/`

Create a new token.

**Request Body:**

```json
{
  "name": "my-token",
  "remain_quota": 1000000000,
  "expired_time": -1
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Token name |
| `remain_quota` | integer | Yes | Quota limit (-1 for unlimited) |
| `expired_time` | integer | Yes | Expiration timestamp (-1 for never) |
| `group` | string | No | Token group |

### `PUT /api/token/`

Update a token.

### `DELETE /api/token/{token_id}`

Delete a token.

---

## Channel Management

### `GET /api/channel/`

List all channels.

**Query Parameters:**

| Parameter | Description |
|-----------|-------------|
| `group` | Filter by channel group |

```bash
curl http://localhost:3000/api/channel/?group=default
```

### `POST /api/channel/`

Create a new channel.

**Request Body:**

```json
{
  "name": "DeepSeek",
  "type": 40,
  "key": "sk-your-api-key",
  "base_url": "https://api.deepseek.com/v1",
  "models": "deepseek-chat,deepseek-reasoner",
  "group": "default",
  "weight": 100,
  "llm_gateway": "openai"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Channel name |
| `type` | integer | Yes | Channel type (see Channel Types) |
| `key` | string | Yes | API key |
| `base_url` | string | Yes | Base URL of the API |
| `models` | string | Yes | Comma-separated model list |
| `group` | string | No | Channel group (default: "default") |
| `weight` | integer | No | Weight for load balancing |
| `llm_gateway` | string | No | Gateway type: `openai` or `anthropic` |

### `GET /api/channel/{channel_id}`

Get specific channel info.

### `PUT /api/channel/`

Update a channel.

### `DELETE /api/channel/{channel_id}`

Delete a channel.

### `GET /api/channel/test/{channel_id}`

Test a specific channel.

### `GET /api/channel/test`

Test all channels.

### `DELETE /api/channel/disabled`

Delete all disabled channels.

### `GET /api/channel/update_balance/{channel_id}`

Update channel balance.

---

## Channel Groups

### `GET /api/channel/group/`

List all channel groups.

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "name": "default",
      "total": 6,
      "enabled": 5,
      "disabled": 1
    }
  ]
}
```

### `GET /api/channel/group/{group}`

Get channels in a specific group.

---

## Logs

### `GET /api/log/`

Get operation logs.

**Query Parameters:**

| Parameter | Description |
|-----------|-------------|
| `page` | Page number |
| `page_size` | Items per page |

### `GET /api/log/self`

Get current user's logs.

### `DELETE /api/log/`

Delete logs (admin only).

### `GET /api/log/stat`

Get log statistics.

---

## Options

### `GET /api/option/`

Get system options.

### `PUT /api/option/`

Update system options (admin only).

---

## Status

### `GET /api/status`

Get system status.

```json
{
  "success": true,
  "data": {
    "version": "1.0.0",
    "status": "ok",
    "mode": "normal"
  }
}
```

---

## Channel Types

| Type ID | Name |
|---------|------|
| 1 | OpenAI |
| 3 | Azure |
| 29 | Moonshot |
| 31 | MiniMax |
| 40 | DeepSeek |
| 20 | Gemini |
| 21 | Baidu |
| 22 | Zhipu |
| 23 | Tencent |
| 24 | Ollama |
| 27 | Mistral |
| 28 | Groq |
| 30 | Cohere |
| 32 | Cloudflare |
| 33 | DeepL |
| 34 | TogetherAI |
| 35 | NovitaAI |
| 36 | SiliconFlow |
| 37 | xAI |
| 38 | AWS Claude |
| 39 | VertexAI |

---

## Redemptions

### `GET /api/redemption/`

List all redemptions.

### `POST /api/redemption/`

Create a redemption code.

### `PUT /api/redemption/`

Update a redemption.

### `DELETE /api/redemption/{redemption_id}`

Delete a redemption.

---

## Abilities

### `GET /api/ability/list`

List all channel abilities/capabilities.