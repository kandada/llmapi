# API Documentation

Welcome to the llmAPI documentation. llmAPI is an OpenAI-compatible API gateway that supports multiple LLM providers with unified interface.

## Quick Start

### Authentication

All API requests require authentication via Bearer token:

```
Authorization: Bearer <your-token>
```

Get your token from `/api/user/token` after login.

### Base URL

```
http://localhost:3000
```

## Table of Contents

1. [OpenAI Compatible API](./openai_compatible.md) - `/v1/*` endpoints
2. [Management API](./management_api.md) - `/api/*` endpoints
3. [Multi-Format Response](./multi_format_response.md) - Output format control
4. [Payment System](./payment_system.md) - Token package sales and external app integration

## Key Features

- **OpenAI Compatible**: Use standard OpenAI SDKs and clients
- **Multi-Format Output**: Switch between OpenAI and Anthropic response formats
- **Channel Groups**: Organize channels by group with weighted load balancing
- **Thinking Content**: Support for reasoning/thinking content from supported models
- **Token Management**: Create and manage multiple API tokens
- **Usage Tracking**: Monitor quota usage per token and channel

## Getting Started

```bash
# 1. Login
curl -X POST http://localhost:3000/api/user/login \
  -H "Content-Type: application/json" \
  -d '{"username":"root","password":"123456"}'

# 2. Get token
curl -X GET http://localhost:3000/api/user/token \
  -H "Authorization: Bearer <cookie>"

# 3. List available models
curl -X GET http://localhost:3000/v1/models \
  -H "Authorization: Bearer <your-token>"

# 4. Make a chat request
curl -X POST http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-token>" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"Hello"}]}'
```

## Support

For issues and feature requests, please contact the development team.