import re


def count_messages_tokens(messages: list, model: str = "gpt-4") -> int:
    if not messages:
        return 0

    total_tokens = 0

    if model.startswith("gpt-4") or model.startswith("gpt-3.5"):
        total_tokens = count_openai_messages_tokens(messages)
    elif model.startswith("claude-"):
        total_tokens = count_anthropic_messages_tokens(messages)
    elif model.startswith("gemini-"):
        total_tokens = count_gemini_messages_tokens(messages)
    else:
        total_tokens = count_openai_messages_tokens(messages)

    return total_tokens


def count_openai_messages_tokens(messages: list) -> int:
    total_tokens = 0

    for message in messages:
        total_tokens += 4
        for key, value in message.items():
            if value:
                total_tokens += len(str(value))
        total_tokens += 2

    total_tokens += 3
    return total_tokens


def count_anthropic_messages_tokens(messages: list) -> int:
    total_tokens = 0

    for message in messages:
        role = message.get("role", "")
        content = message.get("content", "")

        if role == "user":
            total_tokens += 5
        elif role == "assistant":
            total_tokens += 5
        elif role == "system":
            total_tokens += 5

        if isinstance(content, str):
            total_tokens += len(content) // 4
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        total_tokens += len(item.get("text", "")) // 4
                    elif item.get("type") == "tool_use":
                        total_tokens += 50

    total_tokens += 5
    return total_tokens


def count_gemini_messages_tokens(messages: list) -> int:
    total_tokens = 0

    for message in messages:
        role = message.get("role", "")
        parts = message.get("parts", [])

        if role == "user":
            total_tokens += 5
        elif role == "model":
            total_tokens += 5

        for part in parts:
            if isinstance(part, dict):
                if "text" in part:
                    total_tokens += len(part["text"]) // 4

    total_tokens += 5
    return total_tokens


def count_text_tokens(text: str) -> int:
    return len(text) // 4


def estimate_tokens(model: str, messages: list = None, text: str = None, prompt: str = None) -> int:
    if messages:
        return count_messages_tokens(messages, model)
    elif text:
        return count_text_tokens(text)
    elif prompt:
        return count_text_tokens(prompt)
    return 0