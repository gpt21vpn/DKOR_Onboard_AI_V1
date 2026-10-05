import time, uuid, httpx
from .base import BaseProvider

class GigaChatProvider(BaseProvider):
    name='gigachat'
    AUTH_URL='https://ngw.devices.sberbank.ru:9443/api/v2/oauth'
    def __init__(self, credentials: str, scope: str, base_url: str, model: str, verify_ssl: bool=True, proxy_url: str=''):
        self.credentials=credentials; self.scope=scope; self.base_url=base_url.rstrip('/'); self.model=model; self.verify_ssl=verify_ssl
        self._token=''; self._expires=0.0; self.proxy_url=proxy_url.strip()

    def configured(self) -> bool:
        return bool(self.credentials and self.model)

    async def _access_token(self) -> str:
        now=time.time()
        if self._token and now < self._expires-60: return self._token
        headers={'Authorization':f'Basic {self.credentials}','RqUID':str(uuid.uuid4()),'Accept':'application/json','Content-Type':'application/x-www-form-urlencoded'}
        async with httpx.AsyncClient(timeout=30, verify=self.verify_ssl, proxy=self.proxy_url or None, trust_env=False) as client:
            r=await client.post(self.AUTH_URL, headers=headers, data={'scope':self.scope})
            r.raise_for_status(); data=r.json()
        self._token=data['access_token']; self._expires=data.get('expires_at', int((now+1800)*1000))/1000
        return self._token

    async def generate(self, messages: list[dict]) -> str:
        if not self.configured(): raise RuntimeError('gigachat: credentials/model not configured')
        token=await self._access_token()
        headers={'Authorization':f'Bearer {token}','Accept':'application/json','Content-Type':'application/json'}
        payload={'model':self.model,'messages':messages,'temperature':0.2,'max_tokens':600,'stream':False}
        async with httpx.AsyncClient(timeout=90, verify=self.verify_ssl, proxy=self.proxy_url or None, trust_env=False) as client:
            r=await client.post(f'{self.base_url}/chat/completions', headers=headers, json=payload)
            r.raise_for_status(); data=r.json()
        return data['choices'][0]['message']['content'].strip()
