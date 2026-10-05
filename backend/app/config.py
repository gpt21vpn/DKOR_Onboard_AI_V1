from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'DKOR Onboard'
    environment: str = 'development'
    cors_origins: str = 'http://localhost:5173,http://127.0.0.1:5173'
    knowledge_dir: str = str(ROOT / 'knowledge')
    system_prompt_path: str = str(ROOT / 'knowledge' / '_system_prompt_filled.md')
    top_k: int = 5
    memory_turns: int = 6
    rate_limit_enabled: bool = True
    trust_proxy_headers: bool = False

    # Optional proxy for external API calls only.
    outbound_proxy_url: str = ''

    default_provider: str = 'auto'
    auto_provider_order: str = 'gigachat,groq,qwen,openai,local'

    groq_api_key: str = ''
    groq_base_url: str = 'https://api.groq.com/openai/v1'
    groq_chat_model: str = 'openai/gpt-oss-120b'
    groq_stt_model: str = 'whisper-large-v3-turbo'

    openai_api_key: str = ''
    openai_base_url: str = 'https://api.openai.com/v1'
    openai_chat_model: str = ''

    qwen_api_key: str = ''
    qwen_base_url: str = 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1'
    qwen_chat_model: str = ''

    gigachat_credentials: str = ''
    gigachat_scope: str = 'GIGACHAT_API_PERS'
    gigachat_base_url: str = 'https://api.giga.chat/v1'
    gigachat_chat_model: str = 'GigaChat-2-Max'
    gigachat_verify_ssl: bool = True

    # Natural Russian TTS. Two UI voices use the same API key.
    yandex_speechkit_api_key: str = ''
    yandex_speechkit_iam_token: str = ''
    yandex_speechkit_folder_id: str = ''
    yandex_tts_url: str = 'https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize'
    tts_voice_primary: str = 'marina'
    tts_voice_primary_role: str = 'neutral'
    tts_voice_secondary: str = 'ermil'
    tts_voice_secondary_role: str = 'neutral'

    # Optional Groq Orpheus for English TTS only.
    groq_tts_model: str = 'canopylabs/orpheus-v1-english'
    groq_tts_voice: str = 'troy'

    admin_token: str = 'change-me'

    @property
    def provider_order(self) -> list[str]:
        return [x.strip().lower() for x in self.auto_provider_order.split(',') if x.strip()]

    @property
    def cors_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(',') if x.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
