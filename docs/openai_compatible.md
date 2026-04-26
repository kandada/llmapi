# OpenAI Compatible API

All endpoints are prefixed with `/v1/`. These endpoints are compatible with OpenAI API specifications.

## Authentication

All endpoints require Bearer token authentication:

```
Authorization: Bearer <your-token>
```

---

## Chat Completions

Create a chat completion.

### `POST /v1/chat/completions`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | string | Yes | Model name (e.g., `deepseek-chat`, `kimi-k2.5`, `MiniMax-M2.5`) |
| `messages` | array | Yes | Array of message objects |
| `max_tokens` | integer | No | Maximum tokens to generate |
| `temperature` | float | No | Sampling temperature (0-2) |
| `top_p` | float | No | Nucleus sampling parameter |
| `stream` | boolean | No | Enable streaming response |
| `response_format` | string | No | Output format: `openai` (default) or `anthropic` |
| `tools` | array | No | Function/tools definition |
| `tool_choice` | string | No | Tool selection mode |

**Messages Format:**

```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"},
    {"role": "assistant", "content": "Hello! How can I help you?"},
    {"role": "user", "content": "What is 2+2?"}
  ]
}
```

**Example Request:**

```bash
curl -X POST http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-token>" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Say hi in 5 words"}],
    "max_tokens": 50
  }'
```

**Example Response (OpenAI format):**

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "deepseek-chat",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Hi there! How are you?"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 9,
    "total_tokens": 19
  }
}
```

**Example Response with Thinking (Moonshot):**

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "model": "kimi-k2.5",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "The answer is 4.",
      "reasoning_content": "Let me calculate: 2+2=4"
    },
    "finish_reason": "stop"
  }]
}
```

**Example Response (Anthropic format - when `response_format=anthropic`):**

```json
{
  "type": "message",
  "id": "msg_xxx",
  "role": "assistant",
  "content": [
    {"type": "thinking", "thinking": "I need to answer this question...", "signature": "xxx"},
    {"type": "text", "text": "The answer is 4."}
  ],
  "stop_reason": "end_turn",
  "usage": {"input_tokens": 10, "output_tokens": 9}
}
```

---

## Messages (Anthropic Native)

Create a chat completion with Anthropic native response format.

### `POST /v1/messages`

This endpoint automatically returns responses in Anthropic format.

**Request Body:** Same as `/v1/chat/completions`

**Response:** Always in Anthropic format:

```json
{
  "type": "message",
  "id": "msg_xxx",
  "role": "assistant",
  "content": [
    {"type": "thinking", "thinking": "...", "signature": "..."},
    {"type": "text", "text": "Hello!"}
  ],
  "stop_reason": "end_turn",
  "usage": {"input_tokens": 10, "output_tokens": 9}
}
```

---

## Completions

Create a text completion (legacy).

### `POST /v1/completions`

Delegates to `/v1/chat/completions` with message conversion.

---

## Embeddings

Get vector embeddings for text.

### `POST /v1/embeddings`

**Request Body:**

```json
{
  "model": "text-embedding-ada-002",
  "input": "The food was delicious and the service..."
}
```

---

## Images

Generate images.

### `POST /v1/images/generations`

**Request Body:**

```json
{
  "model": "dall-e-3",
  "prompt": "A cute baby sea otter",
  "n": 1,
  "size": "1024x1024"
}
```

---

## Audio

### `POST /v1/audio/transcriptions`

Transcribe audio to text.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | Audio file |
| `model` | string | Yes | Whisper model |

### `POST /v1/audio/translations`

Translate audio to English text.

### `POST /v1/audio/speech`

Convert text to speech.

---

## Models

### `GET /v1/models`

List all available models.

**Response:**

```json
{
  "object": "list",
  "data": [
    {"id": "deepseek-chat", "object": "model"},
    {"id": "kimi-k2.5", "object": "model"},
    {"id": "MiniMax-M2.5", "object": "model"}
  ]
}
```

### `GET /v1/models/{model}`

Get information about a specific model.

---

## Other Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/edits` | POST | Text edits |
| `/v1/moderations` | POST | Content moderation |

---

## Streaming

Enable streaming by setting `stream: true`:

```bash
curl -X POST http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-token>" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Count to 5"}],
    "stream": true
  }'
```

**Stream Response Format:**

```
data: {"choices":[{"delta":{"content":"1"},"finish_reason":null}]}
data: {"choices":[{"delta":{"content":","},"finish_reason":null}]}
data: {"choices":[{"delta":{"content":" 2"},"finish_reason":null}]}
data: [DONE]
```

---

## Error Responses

```json
{
  "error": {
    "message": "Invalid token",
    "type": "invalid_request_error",
    "code": "invalid_token"
  }
}
```

Common status codes:
- `400` - Bad request
- `401` - Invalid or missing token
- `403` - Token doesn't have permission for this model
- `404` - Model not found
- `429` - Rate limit exceeded
- `500` - Internal server error
- `503` - No available channel for model