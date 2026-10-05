import httpx

class YandexSpeechKitTTS:
    def __init__(self, api_key: str, iam_token: str, folder_id: str, url: str, proxy_url: str=''):
        self.api_key=api_key; self.iam_token=iam_token; self.folder_id=folder_id; self.url=url; self.proxy_url=proxy_url.strip()
    def configured(self): return bool(self.api_key or (self.iam_token and self.folder_id))
    async def synthesize(self, text: str, voice: str, role: str='neutral') -> bytes:
        if not self.configured(): raise RuntimeError('Yandex SpeechKit credentials are not configured')
        headers={}
        data={'text':text[:5000],'lang':'ru-RU','voice':voice,'format':'oggopus'}
        if role and role not in ('neutral',''):
            data['emotion']=role if role in ('good','evil') else 'neutral'
        if self.api_key:
            headers['Authorization']=f'Api-Key {self.api_key}'
        else:
            headers['Authorization']=f'Bearer {self.iam_token}'
            data['folderId']=self.folder_id
        async with httpx.AsyncClient(timeout=90, proxy=self.proxy_url or None) as client:
            r=await client.post(self.url, headers=headers, data=data)
            r.raise_for_status()
        return r.content
