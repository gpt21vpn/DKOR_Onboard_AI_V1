import httpx

class GroqSTT:
    def __init__(self, api_key: str, base_url: str, model: str, proxy_url: str=''):
        self.api_key=api_key; self.base_url=base_url.rstrip('/'); self.model=model; self.proxy_url=proxy_url.strip()
    def configured(self): return bool(self.api_key and self.model)
    async def transcribe(self, data: bytes, filename: str, content_type: str='audio/webm') -> str:
        if not self.configured(): raise RuntimeError('GROQ_API_KEY is not configured')
        headers={'Authorization':f'Bearer {self.api_key}'}
        files={'file':(filename,data,content_type)}
        form={'model':self.model,'language':'ru','response_format':'json'}
        async with httpx.AsyncClient(timeout=120, proxy=self.proxy_url or None) as client:
            r=await client.post(f'{self.base_url}/audio/transcriptions', headers=headers, files=files, data=form)
            r.raise_for_status(); payload=r.json()
        return payload.get('text','').strip()
