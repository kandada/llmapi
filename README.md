# LLMAPI

OpenAI-compatible API Gateway with Anthropic support and token package sales.

## Features

- **OpenAI Compatible**: Fully compatible with OpenAI API format
- **Anthropic Support**: Native support for Anthropic API
- **Multi-Channel Management**: Support for multiple AI providers (DeepSeek, Moonshot, MiniMax, Claude, Gemini, etc.)
- **Token Package Sales**: Built-in shop system for selling token packages
- **User Management**: Complete user and quota management system
- **Usage Logging**: Detailed API usage logs and statistics
- **OAuth Support**: GitHub, Lark, OIDC authentication

## Installation

```bash
pip install x-llmapi
```

## Quick Start

```bash
# Start the server
llmapi run

# Or with uvicorn directly
uvicorn llmapi.main:app --host 0.0.0.0 --port 3000

# Run with custom port
llmapi run -p 8080
```

## Configuration

Configure via environment variables:

```bash
export SESSION_SECRET="your-secret-key"
export SQL_DSN="sqlite:///one-api.db"
export QUOTA_FOR_NEW_USER=1000000
```

See `llmapi/config.py` for all available options.

## Development

```bash
# Clone the repository
git clone https://github.com/kandada/llmapi.git
cd llmapi

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest
```

## Acknowledgments

This project is inspired by [one-api](https://github.com/songquanpeng/one-api) and [LiteLLM](https://github.com/BerriAI/litellm). Thank you for their excellent work in the open source community.

## Author

**xiefujin**
- Email: 490021684@qq.com
- GitHub: [github.com/kandada/llmapi](https://github.com/kandada/llmapi)

## License

GNU General Public License v3.0
