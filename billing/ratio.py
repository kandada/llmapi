import json
import threading
from typing import Dict, Optional

USD = 500
MILLI_USD = 1.0 / 1000 * USD
RMB = USD / 7

MODEL_RATIO_LOCK = threading.RLock()

MODEL_RATIO: Dict[str, float] = {
    "gpt-4": 15,
    "gpt-4-0314": 15,
    "gpt-4-0613": 15,
    "gpt-4-32k": 30,
    "gpt-4-32k-0314": 30,
    "gpt-4-32k-0613": 30,
    "gpt-4-1106-preview": 5,
    "gpt-4-0125-preview": 5,
    "gpt-4-turbo-preview": 5,
    "gpt-4-turbo": 5,
    "gpt-4-turbo-2024-04-09": 5,
    "gpt-4o": 2.5,
    "chatgpt-4o-latest": 2.5,
    "gpt-4o-2024-05-13": 2.5,
    "gpt-4o-2024-08-06": 1.25,
    "gpt-4o-2024-11-20": 1.25,
    "gpt-4o-mini": 0.075,
    "gpt-4o-mini-2024-07-18": 0.075,
    "gpt-4-vision-preview": 5,
    "gpt-3.5-turbo": 0.25,
    "gpt-3.5-turbo-0301": 0.75,
    "gpt-3.5-turbo-0613": 0.75,
    "gpt-3.5-turbo-16k": 1.5,
    "gpt-3.5-turbo-16k-0613": 1.5,
    "gpt-3.5-turbo-instruct": 0.75,
    "gpt-3.5-turbo-1106": 0.5,
    "gpt-3.5-turbo-0125": 0.25,
    "o1": 7.5,
    "o1-2024-12-17": 7.5,
    "o1-preview": 7.5,
    "o1-preview-2024-09-12": 7.5,
    "o1-mini": 1.5,
    "o1-mini-2024-09-12": 1.5,
    "o3-mini": 1.5,
    "o3-mini-2025-01-31": 1.5,
    "davinci-002": 1,
    "babbage-002": 0.2,
    "text-ada-001": 0.2,
    "text-babbage-001": 0.25,
    "text-curie-001": 1,
    "text-davinci-002": 10,
    "text-davinci-003": 10,
    "text-davinci-edit-001": 10,
    "code-davinci-edit-001": 10,
    "whisper-1": 15,
    "tts-1": 7.5,
    "tts-1-1106": 7.5,
    "tts-1-hd": 15,
    "tts-1-hd-1106": 15,
    "davinci": 10,
    "curie": 10,
    "babbage": 10,
    "ada": 10,
    "text-embedding-ada-002": 0.05,
    "text-embedding-3-small": 0.01,
    "text-embedding-3-large": 0.065,
    "text-search-ada-doc-001": 10,
    "text-moderation-stable": 0.1,
    "text-moderation-latest": 0.1,
    "dall-e-2": 0.02 * USD,
    "dall-e-3": 0.04 * USD,
    "claude-instant-1.2": 0.8 / 1000 * USD,
    "claude-2.0": 8.0 / 1000 * USD,
    "claude-2.1": 8.0 / 1000 * USD,
    "claude-3-haiku-20240307": 0.25 / 1000 * USD,
    "claude-3-5-haiku-20241022": 1.0 / 1000 * USD,
    "claude-3-5-haiku-latest": 1.0 / 1000 * USD,
    "claude-3-sonnet-20240229": 3.0 / 1000 * USD,
    "claude-3-5-sonnet-20240620": 3.0 / 1000 * USD,
    "claude-3-5-sonnet-20241022": 3.0 / 1000 * USD,
    "claude-3-5-sonnet-latest": 3.0 / 1000 * USD,
    "claude-3-opus-20240229": 15.0 / 1000 * USD,
    "ERNIE-4.0-8K": 0.120 * RMB,
    "ERNIE-3.5-8K": 0.012 * RMB,
    "ERNIE-3.5-8K-0205": 0.024 * RMB,
    "ERNIE-3.5-8K-1222": 0.012 * RMB,
    "ERNIE-Bot-8K": 0.024 * RMB,
    "ERNIE-3.5-4K-0205": 0.012 * RMB,
    "ERNIE-Speed-8K": 0.004 * RMB,
    "ERNIE-Speed-128K": 0.004 * RMB,
    "ERNIE-Lite-8K-0922": 0.008 * RMB,
    "ERNIE-Lite-8K-0308": 0.003 * RMB,
    "ERNIE-Tiny-8K": 0.001 * RMB,
    "BLOOMZ-7B": 0.004 * RMB,
    "Embedding-V1": 0.002 * RMB,
    "bge-large-zh": 0.002 * RMB,
    "bge-large-en": 0.002 * RMB,
    "tao-8k": 0.002 * RMB,
    "gemini-pro": 0.25 * MILLI_USD,
    "gemini-1.0-pro": 0.125 * MILLI_USD,
    "gemini-1.5-pro": 1.25 * MILLI_USD,
    "gemini-1.5-pro-001": 1.25 * MILLI_USD,
    "gemini-1.5-pro-experimental": 1.25 * MILLI_USD,
    "gemini-1.5-flash": 0.075 * MILLI_USD,
    "gemini-1.5-flash-001": 0.075 * MILLI_USD,
    "gemini-1.5-flash-8b": 0.0375 * MILLI_USD,
    "gemini-2.0-flash-exp": 0.075 * MILLI_USD,
    "gemini-2.0-flash": 0.15 * MILLI_USD,
    "gemini-2.0-flash-001": 0.15 * MILLI_USD,
    "gemini-2.0-flash-lite-preview-02-05": 0.075 * MILLI_USD,
    "gemini-2.0-flash-thinking-exp-01-21": 0.075 * MILLI_USD,
    "gemini-2.0-pro-exp-02-05": 1.25 * MILLI_USD,
    "aqa": 1,
    "glm-zero-preview": 0.01 * RMB,
    "glm-4-plus": 0.05 * RMB,
    "glm-4-0520": 0.1 * RMB,
    "glm-4-airx": 0.01 * RMB,
    "glm-4-air": 0.0005 * RMB,
    "glm-4-long": 0.001 * RMB,
    "glm-4-flashx": 0.0001 * RMB,
    "glm-4-flash": 0,
    "glm-4": 0.1 * RMB,
    "glm-3-turbo": 0.001 * RMB,
    "glm-4v-plus": 0.004 * RMB,
    "glm-4v": 0.05 * RMB,
    "glm-4v-flash": 0,
    "cogview-3-plus": 0.06 * RMB,
    "cogview-3": 0.1 * RMB,
    "cogview-3-flash": 0,
    "cogviewx": 0.5 * RMB,
    "cogviewx-flash": 0,
    "charglm-4": 0.001 * RMB,
    "emohaa": 0.015 * RMB,
    "codegeex-4": 0.0001 * RMB,
    "embedding-2": 0.0005 * RMB,
    "embedding-3": 0.0005 * RMB,
    "qwen-turbo": 0.0003 * RMB,
    "qwen-turbo-latest": 0.0003 * RMB,
    "qwen-plus": 0.0008 * RMB,
    "qwen-plus-latest": 0.0008 * RMB,
    "qwen-max": 0.0024 * RMB,
    "qwen-max-latest": 0.0024 * RMB,
    "qwen-max-longcontext": 0.0005 * RMB,
    "qwen-vl-max": 0.003 * RMB,
    "qwen-vl-max-latest": 0.003 * RMB,
    "qwen-vl-plus": 0.0015 * RMB,
    "qwen-vl-plus-latest": 0.0015 * RMB,
    "qwen-vl-ocr": 0.005 * RMB,
    "qwen-vl-ocr-latest": 0.005 * RMB,
    "qwen-audio-turbo": 1.4286,
    "qwen-math-plus": 0.004 * RMB,
    "qwen-math-plus-latest": 0.004 * RMB,
    "qwen-math-turbo": 0.002 * RMB,
    "qwen-math-turbo-latest": 0.002 * RMB,
    "qwen-coder-plus": 0.0035 * RMB,
    "qwen-coder-plus-latest": 0.0035 * RMB,
    "qwen-coder-turbo": 0.002 * RMB,
    "qwen-coder-turbo-latest": 0.002 * RMB,
    "qwen-mt-plus": 0.015 * RMB,
    "qwen-mt-turbo": 0.001 * RMB,
    "qwq-32b-preview": 0.002 * RMB,
    "qwen2.5-72b-instruct": 0.004 * RMB,
    "qwen2.5-32b-instruct": 0.03 * RMB,
    "qwen2.5-14b-instruct": 0.001 * RMB,
    "qwen2.5-7b-instruct": 0.0005 * RMB,
    "qwen2.5-3b-instruct": 0.006 * RMB,
    "qwen2.5-1.5b-instruct": 0.0003 * RMB,
    "qwen2.5-0.5b-instruct": 0.0003 * RMB,
    "qwen2-72b-instruct": 0.004 * RMB,
    "qwen2-57b-a14b-instruct": 0.0035 * RMB,
    "qwen2-7b-instruct": 0.001 * RMB,
    "qwen2-1.5b-instruct": 0.001 * RMB,
    "qwen2-0.5b-instruct": 0.001 * RMB,
    "qwen1.5-110b-chat": 0.007 * RMB,
    "qwen1.5-72b-chat": 0.005 * RMB,
    "qwen1.5-32b-chat": 0.0035 * RMB,
    "qwen1.5-14b-chat": 0.002 * RMB,
    "qwen1.5-7b-chat": 0.001 * RMB,
    "qwen1.5-1.8b-chat": 0.001 * RMB,
    "qwen1.5-0.5b-chat": 0.001 * RMB,
    "qwen-72b-chat": 0.02 * RMB,
    "qwen-14b-chat": 0.008 * RMB,
    "qwen-7b-chat": 0.006 * RMB,
    "qwen-1.8b-chat": 0.006 * RMB,
    "qwen-1.8b-longcontext-chat": 0.006 * RMB,
    "qvq-72b-preview": 0.012 * RMB,
    "qwen2.5-vl-72b-instruct": 0.016 * RMB,
    "qwen2.5-vl-7b-instruct": 0.002 * RMB,
    "qwen2.5-vl-3b-instruct": 0.0012 * RMB,
    "qwen2-vl-7b-instruct": 0.016 * RMB,
    "qwen2-vl-2b-instruct": 0.002 * RMB,
    "qwen-vl-v1": 0.002 * RMB,
    "qwen-vl-chat-v1": 0.002 * RMB,
    "qwen2-audio-instruct": 0.002 * RMB,
    "qwen-audio-chat": 0.002 * RMB,
    "qwen2.5-math-72b-instruct": 0.004 * RMB,
    "qwen2.5-math-7b-instruct": 0.001 * RMB,
    "qwen2.5-math-1.5b-instruct": 0.001 * RMB,
    "qwen2-math-72b-instruct": 0.004 * RMB,
    "qwen2-math-7b-instruct": 0.001 * RMB,
    "qwen2-math-1.5b-instruct": 0.001 * RMB,
    "qwen2.5-coder-32b-instruct": 0.002 * RMB,
    "qwen2.5-coder-14b-instruct": 0.002 * RMB,
    "qwen2.5-coder-7b-instruct": 0.001 * RMB,
    "qwen2.5-coder-3b-instruct": 0.001 * RMB,
    "qwen2.5-coder-1.5b-instruct": 0.001 * RMB,
    "qwen2.5-coder-0.5b-instruct": 0.001 * RMB,
    "text-embedding-v1": 0.0007 * RMB,
    "text-embedding-v3": 0.0007 * RMB,
    "text-embedding-v2": 0.0007 * RMB,
    "text-embedding-async-v2": 0.0007 * RMB,
    "text-embedding-async-v1": 0.0007 * RMB,
    "deepseek-r1": 0.002 * RMB,
    "deepseek-v3": 0.001 * RMB,
    "deepseek-r1-distill-qwen-1.5b": 0.001 * RMB,
    "deepseek-r1-distill-qwen-7b": 0.0005 * RMB,
    "deepseek-r1-distill-qwen-14b": 0.001 * RMB,
    "deepseek-r1-distill-qwen-32b": 0.002 * RMB,
    "deepseek-r1-distill-llama-8b": 0.0005 * RMB,
    "deepseek-r1-distill-llama-70b": 0.004 * RMB,
    "SparkDesk": 1.2858,
    "SparkDesk-v1.1": 1.2858,
    "SparkDesk-v2.1": 1.2858,
    "SparkDesk-v3.1": 1.2858,
    "SparkDesk-v3.1-128K": 1.2858,
    "SparkDesk-v3.5": 1.2858,
    "SparkDesk-v3.5-32K": 1.2858,
    "SparkDesk-v4.0": 1.2858,
    "360GPT_S2_V9": 0.8572,
    "embedding-bert-512-v1": 0.0715,
    "embedding_s1_v1": 0.0715,
    "semantic_similarity_s1_v1": 0.0715,
    "hunyuan-turbo": 0.015 * RMB,
    "hunyuan-large": 0.004 * RMB,
    "hunyuan-large-longcontext": 0.006 * RMB,
    "hunyuan-standard": 0.0008 * RMB,
    "hunyuan-standard-256K": 0.0005 * RMB,
    "hunyuan-translation-lite": 0.005 * RMB,
    "hunyuan-role": 0.004 * RMB,
    "hunyuan-functioncall": 0.004 * RMB,
    "hunyuan-code": 0.004 * RMB,
    "hunyuan-turbo-vision": 0.08 * RMB,
    "hunyuan-vision": 0.018 * RMB,
    "hunyuan-embedding": 0.0007 * RMB,
    "moonshot-v1-8k": 0.012 * RMB,
    "moonshot-v1-32k": 0.024 * RMB,
    "moonshot-v1-128k": 0.06 * RMB,
    "kimi-k2.5": 0.015 * RMB,
    "MiniMax-M2.7": 0.015 * RMB,
    "MiniMax-M2.5": 0.01 * RMB,
    "minimax-01": 0.55 * RMB,
    "minimax-Text-01": 0.002 * RMB,
    "Baichuan2-Turbo": 0.008 * RMB,
    "Baichuan2-Turbo-192k": 0.016 * RMB,
    "Baichuan2-53B": 0.02 * RMB,
    "abab6.5-chat": 0.03 * RMB,
    "abab6.5s-chat": 0.01 * RMB,
    "abab6-chat": 0.1 * RMB,
    "abab5.5-chat": 0.015 * RMB,
    "abab5.5s-chat": 0.005 * RMB,
    "open-mistral-7b": 0.25 / 1000 * USD,
    "open-mixtral-8x7b": 0.7 / 1000 * USD,
    "mistral-small-latest": 2.0 / 1000 * USD,
    "mistral-medium-latest": 2.7 / 1000 * USD,
    "mistral-large-latest": 8.0 / 1000 * USD,
    "mistral-embed": 0.1 / 1000 * USD,
    "gemma-7b-it": 0.07 / 1000000 * USD,
    "gemma2-9b-it": 0.20 / 1000000 * USD,
    "llama-3.1-70b-versatile": 0.59 / 1000000 * USD,
    "llama-3.1-8b-instant": 0.05 / 1000000 * USD,
    "llama-3.2-11b-text-preview": 0.05 / 1000000 * USD,
    "llama-3.2-11b-vision-preview": 0.05 / 1000000 * USD,
    "llama-3.2-1b-preview": 0.05 / 1000000 * USD,
    "llama-3.2-3b-preview": 0.05 / 1000000 * USD,
    "llama-3.2-90b-text-preview": 0.59 / 1000000 * USD,
    "llama-guard-3-8b": 0.05 / 1000000 * USD,
    "llama3-70b-8192": 0.59 / 1000000 * USD,
    "llama3-8b-8192": 0.05 / 1000000 * USD,
    "llama3-groq-70b-8192-tool-use-preview": 0.89 / 1000000 * USD,
    "llama3-groq-8b-8192-tool-use-preview": 0.19 / 1000000 * USD,
    "mixtral-8x7b-32768": 0.24 / 1000000 * USD,
    "yi-34b-chat-0205": 2.5 / 1000 * RMB,
    "yi-34b-chat-200k": 12.0 / 1000 * RMB,
    "yi-vl-plus": 6.0 / 1000 * RMB,
    "step-1-8k": 0.005 / 1000 * RMB,
    "step-1-32k": 0.015 / 1000 * RMB,
    "step-1-128k": 0.040 / 1000 * RMB,
    "step-1-256k": 0.095 / 1000 * RMB,
    "step-1-flash": 0.001 / 1000 * RMB,
    "step-2-16k": 0.038 / 1000 * RMB,
    "step-1v-8k": 0.005 / 1000 * RMB,
    "step-1v-32k": 0.015 / 1000 * RMB,
    "llama3-8b-8192(33)": 0.0003 / 0.002,
    "llama3-70b-8192(33)": 0.00265 / 0.002,
    "command": 0.5,
    "command-nightly": 0.5,
    "command-light": 0.5,
    "command-light-nightly": 0.5,
    "command-r": 0.5 / 1000 * USD,
    "command-r-plus": 3.0 / 1000 * USD,
    "deepseek-chat": 0.14 * MILLI_USD,
    "deepseek-reasoner": 0.55 * MILLI_USD,
    "deepl-zh": 25.0 / 1000 * USD,
    "deepl-en": 25.0 / 1000 * USD,
    "deepl-ja": 25.0 / 1000 * USD,
    "grok-beta": 5.0 / 1000 * USD,
    "minimax/minimax-01": 0.55,
}

COMPLETION_RATIO: Dict[str, float] = {
    "llama3-8b-8192(33)": 0.0006 / 0.0003,
    "llama3-70b-8192(33)": 0.0035 / 0.00265,
    "whisper-1": 0,
    "deepseek-chat": 0.28 / 0.14,
    "deepseek-reasoner": 2.19 / 0.55,
    "gpt-3.5": 1,
    "gpt-4": 2,
}

GROUP_RATIO: Dict[str, float] = {
    "default": 1.0,
    "vip": 1.0,
    "svip": 1.0,
}

DEFAULT_MODEL_RATIO = MODEL_RATIO.copy()
DEFAULT_COMPLETION_RATIO = COMPLETION_RATIO.copy()
DEFAULT_GROUP_RATIO = GROUP_RATIO.copy()


class BillingCalculator:
    def __init__(
        self,
        model_ratio: Dict[str, float] = None,
        completion_ratio: Dict[str, float] = None,
        group_ratio: Dict[str, float] = None,
    ):
        self.model_ratio = model_ratio or DEFAULT_MODEL_RATIO.copy()
        self.completion_ratio = completion_ratio or DEFAULT_COMPLETION_RATIO.copy()
        self.group_ratio = group_ratio or DEFAULT_GROUP_RATIO.copy()

    def get_model_ratio(self, model: str, channel_type: int = 0) -> float:
        model_key = f"{model}({channel_type})"
        if model_key in self.model_ratio:
            return self.model_ratio[model_key]
        if model in self.model_ratio:
            return self.model_ratio[model]
        for prefix in self.model_ratio:
            if model.startswith(prefix):
                return self.model_ratio[prefix]
        return 30

    def get_completion_ratio(self, model: str, channel_type: int = 0) -> float:
        model_key = f"{model}({channel_type})"
        if model_key in self.completion_ratio:
            return self.completion_ratio[model_key]
        if model in self.completion_ratio:
            return self.completion_ratio[model]
        if model.startswith("gpt-3.5"):
            if model == "gpt-3.5-turbo" or model.endswith("0125"):
                return 3
            if model.endswith("1106"):
                return 2
            return 4.0 / 3.0
        if model.startswith("gpt-4"):
            if model.startswith("gpt-4o"):
                if model == "gpt-4o-2024-05-13":
                    return 3
                return 4
            if "turbo" in model or "preview" in model:
                return 3
            return 2
        if model.startswith("o1"):
            return 4
        if model == "chatgpt-4o-latest":
            return 3
        if model.startswith("claude-3"):
            return 5
        if model.startswith("claude-"):
            return 3
        if model.startswith("mistral-"):
            return 3
        if model.startswith("gemini-"):
            return 3
        if model.startswith("deepseek-"):
            return 2
        return 1

    def get_group_ratio(self, group: str) -> float:
        return self.group_ratio.get(group, 1.0)

    def calculate_quota(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        group: str = "default",
        channel_type: int = 0,
    ) -> int:
        model_ratio = self.get_model_ratio(model, channel_type)
        completion_ratio = self.get_completion_ratio(model, channel_type)
        group_ratio = self.get_group_ratio(group)

        input_cost = prompt_tokens * model_ratio
        output_cost = completion_tokens * model_ratio * completion_ratio

        total = input_cost + output_cost
        return int(total * group_ratio)

    def calculate_consume(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        group: str = "default",
        channel_type: int = 0,
    ) -> dict:
        quota = self.calculate_quota(model, prompt_tokens, completion_tokens, group, channel_type)
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "quota": quota,
        }


def get_model_ratio_from_db(model: str, channel_type: int = 0) -> float:
    with MODEL_RATIO_LOCK:
        model_key = f"{model}({channel_type})"
        if model_key in MODEL_RATIO:
            return MODEL_RATIO[model_key]
        if model in MODEL_RATIO:
            return MODEL_RATIO[model]
    return 30


def get_completion_ratio_from_db(model: str, channel_type: int = 0) -> float:
    model_key = f"{model}({channel_type})"
    if model_key in COMPLETION_RATIO:
        return COMPLETION_RATIO[model_key]
    if model in COMPLETION_RATIO:
        return COMPLETION_RATIO[model]
    if model.startswith("gpt-3.5"):
        if model == "gpt-3.5-turbo" or model.endswith("0125"):
            return 3
        if model.endswith("1106"):
            return 2
        return 4.0 / 3.0
    if model.startswith("gpt-4"):
        if model.startswith("gpt-4o"):
            if model == "gpt-4o-2024-05-13":
                return 3
            return 4
        if "turbo" in model or "preview" in model:
            return 3
        return 2
    if model.startswith("o1"):
        return 4
    if model == "chatgpt-4o-latest":
        return 3
    if model.startswith("claude-3"):
        return 5
    if model.startswith("claude-"):
        return 3
    if model.startswith("mistral-"):
        return 3
    if model.startswith("gemini-"):
        return 3
    if model.startswith("deepseek-"):
        return 2
    return 1


def get_group_ratio_from_db(group: str) -> float:
    return GROUP_RATIO.get(group, 1.0)


def update_model_ratio(json_str: str) -> bool:
    global MODEL_RATIO
    try:
        with MODEL_RATIO_LOCK:
            new_ratio = json.loads(json_str)
            MODEL_RATIO = new_ratio
        return True
    except Exception:
        return False


def update_completion_ratio(json_str: str) -> bool:
    global COMPLETION_RATIO
    try:
        with MODEL_RATIO_LOCK:
            COMPLETION_RATIO = json.loads(json_str)
        return True
    except Exception:
        return False


def update_group_ratio(json_str: str) -> bool:
    global GROUP_RATIO
    try:
        with MODEL_RATIO_LOCK:
            GROUP_RATIO = json.loads(json_str)
        return True
    except Exception:
        return False


def model_ratio_to_json() -> str:
    return json.dumps(MODEL_RATIO)


def completion_ratio_to_json() -> str:
    return json.dumps(COMPLETION_RATIO)


def group_ratio_to_json() -> str:
    return json.dumps(GROUP_RATIO)