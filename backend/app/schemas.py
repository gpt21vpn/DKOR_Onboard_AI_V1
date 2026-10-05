from typing import Literal
from pydantic import BaseModel, Field

ProviderName = Literal['auto','gigachat','groq','qwen','openai','local']

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    session_id: str = Field(min_length=4, max_length=64, pattern=r'^[A-Za-z0-9_-]+$')
    provider: ProviderName = 'auto'
    role: str = Field('Не выбрана', max_length=60)
    stage: str = Field('Не выбран', max_length=60)

class SourceItem(BaseModel):
    source: str
    section: str
    chunk_id: str
    score: float
    preview: str

class ChatResponse(BaseModel):
    answer: str
    provider: str
    model: str
    sources: list[SourceItem]
    escalations: list[str]
    session_id: str

class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    voice: Literal['primary','secondary','groq_en'] = 'primary'

class HealthResponse(BaseModel):
    ok: bool
    app: str
    providers: dict
    voice: dict
    chunks: int
