from sqlalchemy import Column, Integer, String, BigInteger, Text, Float
from .base import BaseModel


class Channel(BaseModel):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(Integer, default=0)
    key = Column(Text, nullable=False)
    status = Column(Integer, default=1)  # 0=unknown, 1=enabled, 2=disabled, 3=auto_disabled
    name = Column(String(255), index=True)
    weight = Column(Integer, default=0)
    created_time = Column(BigInteger, nullable=False)
    test_time = Column(BigInteger, nullable=False)
    response_time = Column(Integer, default=0)
    base_url = Column(String(500), default="")
    other = Column(Text)
    balance = Column(Float, default=0.0)
    balance_updated_time = Column(BigInteger, nullable=False)
    models = Column(String(2000), nullable=False)
    group = Column(String(32), default="default")
    used_quota = Column(BigInteger, default=0)
    model_mapping = Column(String(1024), default="")
    priority = Column(BigInteger, default=0)
    config = Column(Text)
    system_prompt = Column(Text)
    llm_gateway = Column(String(32), default="openai")


class ChannelStatus:
    UNKNOWN = 0
    ENABLED = 1
    MANUALLY_DISABLED = 2
    AUTO_DISABLED = 3


class ChannelType:
    UNKNOWN = 0
    OPENAI = 1
    API2D = 2
    AZURE = 3
    CLOSEAI = 4
    OPENAISB = 5
    OPENAIMAX = 6
    OHMYGPT = 7
    CUSTOM = 8
    AILS = 9
    AIPROXY = 10
    PALM = 11
    API2GPT = 12
    AIGC2D = 13
    ANTHROPIC = 18
    BAIDU = 19
    ZHIPU = 20
    ALI = 21
    XUNFEI = 22
    AI360 = 23
    OPENROUTER = 24
    AIPROXYLIBRARY = 25
    FASTGPT = 26
    TENCENT = 27
    GEMINI = 28
    MOONSHOT = 29
    BAICHUAN = 30
    MINIMAX = 31
    MISTRAL = 32
    GROQ = 33
    OLLAMA = 34
    LINGYIWANWU = 35
    STEPFUN = 36
    AWSCLAUDE = 37
    COZE = 38
    COHERE = 39
    DEEPSEEK = 40
    CLOUDFLARE = 41
    DEEPL = 42
    TOGETHERAI = 43
    DOUBAO = 44
    NOVITA = 45
    VERTEXAI = 46
    PROXY = 47
    SILICONFLOW = 48
    XAI = 49
    REPLICATE = 50
    BAIDUV2 = 51
    XUNFEIV2 = 52
    ALIBAILIAN = 53
    OPENAICOMPATIBLE = 54
    GEMINIOPENAICOMPATIBLE = 55
    DUMMY = 56
