"""配置文件"""

import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - python-dotenv is installed in normal setup
    load_dotenv = None


def _first_env(*names: str) -> Optional[str]:
    """Return the first non-empty environment variable value."""
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return None


def normalize_base_url(base_url: Optional[str]) -> Optional[str]:
    """Normalize common OpenAI-compatible gateway URL input mistakes."""
    if not base_url:
        return None

    normalized = base_url.strip().rstrip("/")
    for suffix in ("/chat/completions", "/completions"):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break
    return normalized.rstrip("/")


_normalize_base_url = normalize_base_url


def _set_env_if_missing(name: str, value: Optional[str]) -> None:
    if value and not os.getenv(name):
        os.environ[name] = value


def load_runtime_env() -> None:
    """Load .env and normalize aliases for third-party LLM gateways.

    hello-agents reads LLM_API_KEY, LLM_BASE_URL and LLM_MODEL_ID directly from
    process environment variables. This function keeps the project friendly to
    common OpenAI-compatible gateway names while preserving explicit LLM_* values.
    """
    env_path = Path(__file__).with_name(".env")
    if load_dotenv and env_path.exists():
        load_dotenv(env_path, override=False)

    api_key = _first_env("LLM_API_KEY", "OPENAI_API_KEY", "API_KEY")
    base_url = normalize_base_url(
        _first_env("LLM_BASE_URL", "OPENAI_BASE_URL", "BASE_URL")
    )
    model_id = _first_env("LLM_MODEL_ID", "LLM_MODEL", "OPENAI_MODEL", "MODEL")
    affinity_api_key = _first_env("LLM_AFFINITY_API_KEY", "AFFINITY_API_KEY")
    affinity_base_url = normalize_base_url(
        _first_env("LLM_AFFINITY_BASE_URL", "AFFINITY_BASE_URL")
    )
    affinity_model_id = _first_env(
        "LLM_AFFINITY_MODEL_ID", "LLM_AFFINITY_MODEL", "AFFINITY_MODEL"
    )

    _set_env_if_missing("LLM_API_KEY", api_key)
    _set_env_if_missing("LLM_BASE_URL", base_url)
    _set_env_if_missing("LLM_MODEL_ID", model_id)
    _set_env_if_missing("LLM_AFFINITY_API_KEY", affinity_api_key)
    _set_env_if_missing("LLM_AFFINITY_BASE_URL", affinity_base_url)
    _set_env_if_missing("LLM_AFFINITY_MODEL_ID", affinity_model_id)


load_runtime_env()

class Settings:
    """应用配置"""
    
    # API配置
    API_TITLE = "赛博小镇 API"
    API_VERSION = "1.0.0"
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    
    # NPC配置
    NPC_UPDATE_INTERVAL = int(os.getenv("NPC_UPDATE_INTERVAL", "30"))  # NPC状态更新间隔(秒)
    
    # LLM配置 (从环境变量读取)
    # 第三方OpenAI兼容中转站推荐使用 LLM_* 变量；config 会兼容常见别名。
    LLM_MODEL_ID: str = os.getenv("LLM_MODEL_ID", "Qwen/Qwen2.5-72B-Instruct")
    LLM_API_KEY: Optional[str] = os.getenv("LLM_API_KEY")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api-inference.modelscope.cn/v1/")

    # CORS配置
    CORS_ORIGINS = ["*"]  # 生产环境应限制具体域名

    @classmethod
    def validate(cls):
        """验证配置"""
        if not cls.LLM_API_KEY:
            print("⚠️  警告: 未设置LLM_API_KEY环境变量")
            print("   请在backend/.env文件中配置LLM_API_KEY, 或配置OPENAI_API_KEY别名")
            print("   示例: LLM_API_KEY=\"your-api-key\"")
            return False

        print(f"✅ LLM配置:")
        print(f"   模型: {cls.LLM_MODEL_ID}")
        print(f"   服务地址: {cls.LLM_BASE_URL}")
        if cls.LLM_BASE_URL.endswith("/chat/completions"):
            print("⚠️  LLM_BASE_URL应填写到/v1, 不要填写完整/chat/completions路径")
        return True

settings = Settings()
