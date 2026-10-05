import httpx
from .base import BaseProvider

class OpenAICompatibleProvider(BaseProvider):
    def __init__(self, name: str, api_key: str, base_url: str, model: str, timeout: float = 90, proxy_url: str = ''):
        self.name=name; self.api_key=api_key; self.base_url=base_url.rstrip('/'); self.model=model; self.timeout=timeout; self.proxy_url=proxy_url.strip()

    def configured(self) -> bool:
        return bool(self.api_key and self.model)

    async def generate(self, messages: list[dict]) -> str:
        if not self.configured():
            raise RuntimeError(f'{self.name}: API key/model not configured')
        headers={'Authorization':f'Bearer {self.api_key}','Content-Type':'application/json'}
        payload={'model':self.model,'messages':messages,'temperature':0.2,'stream':False}
        if self.name in ('openai','groq'):
            payload['max_completion_tokens']=600
        else:
            payload['max_tokens']=600
        async with httpx.AsyncClient(timeout=self.timeout, proxy=self.proxy_url or None) as client:
            r=await client.post(f'{self.base_url}/chat/completions', headers=headers, json=payload)
            r.raise_for_status()
            data=r.json()
        return data['choices'][0]['message']['content'].strip()
