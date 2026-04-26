# Multi-Format Response

llmAPI supports outputting responses in both OpenAI and Anthropic formats, giving you the flexibility to use whichever format best suits your needs.

## Overview

| Format | Use Case | Endpoint |
|--------|----------|----------|
| OpenAI | Standard OpenAI SDK clients | `/v1/chat/completions` with `response_format=openai` |
| Anthropic | Anthropic SDK clients, thinking content | `/v1/messages` or `/v1/chat/completions` with `response_format=anthropic` |

---

## OpenAI Format (Default)

By default, all responses are returned in OpenAI format:

```bash
curl -X POST http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

**Response:**

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
      "content": "Hello! How can I help you today?"
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

---

## Anthropic Format

### Option 1: Using `response_format` parameter

```bash
curl -X POST http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "model": "MiniMax-M2.5",
    "messages": [{"role": "user", "content": "Hello"}],
    "response_format": "anthropic"
  }'
```

### Option 2: Using `/v1/messages` endpoint

```bash
curl -X POST http://localhost:3000/v1/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "model": "MiniMax-M2.5",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

**Anthropic Response Format:**

```json
{
  "type": "message",
  "id": "msg_xxx",
  "role": "assistant",
  "model": "MiniMax-M2.5",
  "content": [
    {
      "type": "thinking",
      "thinking": "The user said hello, I should respond warmly...",
      "signature": "abc123..."
    },
    {
      "type": "text",
      "text": "Hello! How can I help you today?"
    }
  ],
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 10,
    "output_tokens": 9
  }
}
```

---

## Thinking Content

Thinking content allows models to show their reasoning process. llmAPI handles this in both formats.

### OpenAI Format with Thinking

Models like Moonshot (Kimi) return thinking as `reasoning_content`:

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "The answer is 42.",
      "reasoning_content": "Let me think about this... The question asks for the meaning of life..."
    }
  }]
}
```

### Anthropic Format with Thinking

```json
{
  "content": [
    {
      "type": "thinking",
      "thinking": "Let me calculate: 2+2=4",
      "signature": "abc123..."
    },
    {
      "type": "text",
      "text": "The answer is 4."
    }
  ]
}
```

---

## Streaming Responses

### OpenAI Stream Format

```bash
curl -X POST http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Count to 3"}],
    "stream": true
  }'
```

**Stream Response:**

```
data: {"choices":[{"delta":{"role":"assistant"},"finish_reason":null}]}
data: {"choices":[{"delta":{"content":"1"},"finish_reason":null}]}
data: {"choices":[{"delta":{"content":","},"finish_reason":null}]}
data: {"choices":[{"delta":{"content":" 2"},"finish_reason":null}]}
data: {"choices":[{"delta":{"content":","},"finish_reason":null}]}
data: {"choices":[{"delta":{"content":" 3"},"finish_reason":null}]}
data: {"choices":[{"delta":{}],"finish_reason":"stop"}]}
data: [DONE]
```

### Anthropic Stream Format

```bash
curl -X POST http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "model": "MiniMax-M2.5",
    "messages": [{"role": "user", "content": "Count to 3"}],
    "stream": true,
    "response_format": "anthropic"
  }'
```

**Anthropic Stream Events:**

```
event: content_block_start
data: {"index":0,"content_block":{"type":"thinking","thinking":""}}

event: content_block_delta
data: {"index":0,"content_block":{"type":"thinking_delta","thinking":"Let"}}

event: content_block_delta
data: {"index":0,"content_block":{"type":"thinking_delta","thinking":" me"}}

event: content_block_delta
data: {"index":0,"content_block":{"type":"text_delta","text":"1,"}}

event: content_block_delta
data: {"index":0,"content_block":{"type":"text_delta","text":" 2,"}}

event: content_block_delta
data: {"index":0,"content_block":{"type":"text_delta","text":" 3"}}

event: message_delta
data: {"usage":{"output_tokens":10}}

event: message_stop
```

---

## Choosing the Right Format

### Use OpenAI Format When:

- Using standard OpenAI SDKs or clients
- You don't need thinking content
- You want maximum compatibility
- You're proxying to existing OpenAI-based applications

### Use Anthropic Format When:

- Using Anthropic SDKs or clients
- You need access to thinking content
- You're building applications that benefit from seeing the model's reasoning
- You want the full response with structured content blocks

---

## Compatibility Matrix

| Feature | OpenAI Format | Anthropic Format |
|---------|--------------|------------------|
| Basic chat | ✅ | ✅ |
| Streaming | ✅ | ✅ |
| Thinking content | ✅ (as `reasoning_content`) | ✅ (as `thinking` block) |
| Tool use | ✅ | ✅ |
| Token usage | ✅ | ✅ |
| Stop reason | ✅ | ✅ |

---

## Examples

### Python - OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-token",
    base_url="http://localhost:3000/v1"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "Hello"}]
)
print(response.choices[0].message.content)
```

### Python - Anthropic SDK

```python
from anthropic import Anthropic

client = Anthropic(
    api_key="your-token",
    base_url="http://localhost:3000"
)

response = client.messages.create(
    model="MiniMax-M2.5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}]
)
print(response.content[0].text)
```

### JavaScript - OpenAI SDK

```javascript
import OpenAI from 'openai';

const client = new OpenAI({
  apiKey: 'your-token',
  baseURL: 'http://localhost:3000/v1'
});

const response = await client.chat.completions.create({
  model: 'deepseek-chat',
  messages: [{ role: 'user', content: 'Hello' }]
});
```

### JavaScript - Anthropic SDK

```javascript
import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic({
  apiKey: 'your-token',
  baseURL: 'http://localhost:3000'
});

const response = await client.messages.create({
  model: 'MiniMax-M2.5',
  max_tokens: 1024,
  messages: [{ role: 'user', content: 'Hello' }]
});
```