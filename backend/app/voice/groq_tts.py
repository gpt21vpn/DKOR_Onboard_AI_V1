import httpx

class GroqTTS:
    def __init__(self, api_key: str, base_url: str, model: str, voice: str, proxy_url: str=''):
        self.api_key=api_key; self.base_url=base_url.rstrip('/'); self.model=model; self.voice=voice; self.proxy_url=proxy_url.strip()
    def configured(self): return bool(self.api_key and self.model and self.voice)
    async def synthesize(self, text: str) -> bytes:
        if not self.configured(): raise RuntimeError('Groq TTS is not configured')
        # Current Orpheus endpoint supports English/Arabic models. Keep this as optional EN voice.
        payload={'model':self.model,'voice':self.voice,'input':text[:200],'response_format':'wav'}
        headers={'Authorization':f'Bearer {self.api_key}','Content-Type':'application/json'}
        async with httpx.AsyncClient(timeout=90, proxy=self.proxy_url or None) as client:
            r=await client.post(f'{self.base_url}/audio/speech', headers=headers, json=payload)
            r.raise_for_status()
        return r.content
