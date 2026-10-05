from .openai_compatible import OpenAICompatibleProvider
from .gigachat import GigaChatProvider
from .local import LocalFallbackProvider

class ProviderRouter:
    def __init__(self, settings):
        self.settings=settings
        self.providers={
            'gigachat': GigaChatProvider(settings.gigachat_credentials, settings.gigachat_scope, settings.gigachat_base_url, settings.gigachat_chat_model, settings.gigachat_verify_ssl, settings.outbound_proxy_url),
            'groq': OpenAICompatibleProvider('groq', settings.groq_api_key, settings.groq_base_url, settings.groq_chat_model, proxy_url=settings.outbound_proxy_url),
            'qwen': OpenAICompatibleProvider('qwen', settings.qwen_api_key, settings.qwen_base_url, settings.qwen_chat_model, proxy_url=settings.outbound_proxy_url),
            'openai': OpenAICompatibleProvider('openai', settings.openai_api_key, settings.openai_base_url, settings.openai_chat_model, proxy_url=settings.outbound_proxy_url),
            'local': LocalFallbackProvider(),
        }

    def status(self):
        return {name:{'configured':p.configured(),'model':p.model} for name,p in self.providers.items()}

    async def generate(self, requested: str, messages: list[dict]):
        order=self.settings.provider_order if requested=='auto' else [requested]
        errors=[]
        for name in order:
            p=self.providers.get(name)
            if not p or not p.configured(): continue
            try:
                text=await p.generate(messages)
                return text, name, p.model
            except Exception as e:
                errors.append(f'{name}: {type(e).__name__}: {e}')
                if requested!='auto': raise
        raise RuntimeError('No provider available. ' + ' | '.join(errors))
