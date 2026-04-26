# LLMAPI

支持 OpenAI 和 Anthropic 格式的 API 网关，带有 Token 套餐销售功能。

## 功能特性

- **OpenAI 兼容**：完全兼容 OpenAI API 格式
- **Anthropic 支持**：原生支持 Anthropic API
- **多渠道管理**：支持多个 AI 提供商（DeepSeek、Moonshot、MiniMax、Claude、Gemini 等）
- **Token 套餐销售**：内置商城系统，支持销售 Token 套餐
- **用户管理**：完整的用户和额度管理系统
- **使用日志**：详细的 API 使用日志和统计
- **OAuth 支持**：支持 GitHub、Lark、OIDC 认证

## 安装

```bash
pip install x-llmapi
```

## 快速开始

```bash
# 启动服务器
llmapi run

# 或使用 uvicorn 直接启动
uvicorn llmapi.main:app --host 0.0.0.0 --port 3000

# 自定义端口
llmapi run -p 8080
```

## 配置

通过环境变量配置：

```bash
export SESSION_SECRET="your-secret-key"
export SQL_DSN="sqlite:///one-api.db"
export QUOTA_FOR_NEW_USER=1000000
```

更多配置选项请查看 `llmapi/config.py`。

## 开发

```bash
# 克隆仓库
git clone https://github.com/kandada/llmapi.git
cd llmapi

# 开发模式安装
pip install -e ".[dev]"

# 运行测试
pytest
```

## 致谢

本项目受 [one-api](https://github.com/songquanpeng/one-api) 和 [LiteLLM](https://github.com/BerriAI/litellm) 启发，感谢他们在开源社区的出色工作。

## 作者

**xiefujin**
- 邮箱：490021684@qq.com
- GitHub：[github.com/kandada/llmapi](https://github.com/kandada/llmapi)

## 许可证

GNU General Public License v3.0
