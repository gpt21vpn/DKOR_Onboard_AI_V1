from pathlib import Path
import hmac, logging
from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings, ROOT
from .limits import Limits
from .security import resolve_static
from .schemas import ChatRequest, ChatResponse, TTSRequest, HealthResponse
from .retrieval import KnowledgeIndex
from .memory import SessionMemory
from .providers import ProviderRouter
from .services.chat import ChatService
from .voice.groq_stt import GroqSTT
from .voice.yandex_tts import YandexSpeechKitTTS
from .voice.groq_tts import GroqTTS

settings=get_settings()
index=KnowledgeIndex(settings.knowledge_dir)
router=ProviderRouter(settings)
memory=SessionMemory(settings.memory_turns)
chat_service=ChatService(settings,index,router,memory)
stt=GroqSTT(settings.groq_api_key,settings.groq_base_url,settings.groq_stt_model,settings.outbound_proxy_url)
yandex_tts=YandexSpeechKitTTS(settings.yandex_speechkit_api_key,settings.yandex_speechkit_iam_token,settings.yandex_speechkit_folder_id,settings.yandex_tts_url,settings.outbound_proxy_url)
groq_tts=GroqTTS(settings.groq_api_key,settings.groq_base_url,settings.groq_tts_model,settings.groq_tts_voice,settings.outbound_proxy_url)

log=logging.getLogger('dkor')
limits=Limits(enabled=settings.rate_limit_enabled,
              trust_proxy=settings.trust_proxy_headers,
              admin_token=settings.admin_token if settings.admin_token!='change-me' else None)
MAX_AUDIO_BYTES=2*1024*1024   # ~30-60 секунд речи

app=FastAPI(title='DKOR Onboard API',version='1.0.0')
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_list,allow_credentials=True,allow_methods=['*'],allow_headers=['*'])

@app.get('/api/health',response_model=HealthResponse)
async def health():
    return {'ok':True,'app':settings.app_name,'providers':router.status(),'voice':{
        'groq_stt':stt.configured(),'yandex_tts':yandex_tts.configured(),'groq_tts_en':groq_tts.configured(),
        'voices':['primary','secondary'] + (['groq_en'] if groq_tts.configured() else [])
    },'chunks':len(index.chunks)}

@app.post('/api/chat',response_model=ChatResponse)
async def chat(req:ChatRequest, request:Request):
    limits.check(request,'chat',req.session_id)
    async with limits.one_at_a_time(req.session_id):
        if req.provider!='local' and not limits.spend('chat'):
            req.provider='local'          # суточный бюджет исчерпан: отвечаем локально, без платных вызовов
        try: return await chat_service.answer(req)
        except HTTPException: raise
        except Exception:
            log.exception('chat failed')   # подробности только в логе сервера
            raise HTTPException(status_code=502,detail='Сервис временно недоступен. Попробуйте позже.')

@app.delete('/api/session/{session_id}')
async def clear_session(session_id:str):
    memory.clear(session_id); return {'ok':True}

@app.post('/api/voice/transcribe')
async def transcribe(request:Request, file:UploadFile=File(...)):
    limits.check(request,'stt')
    try:
        data=await file.read(MAX_AUDIO_BYTES+1)
        if len(data)>MAX_AUDIO_BYTES: raise HTTPException(413,'Запись слишком длинная. Скажите короче, до 30 секунд.')
        if not (file.content_type or 'audio/webm').startswith(('audio/','video/webm')): raise HTTPException(415,'Нужен аудиофайл')
        if not limits.spend('stt'): raise HTTPException(503,'Голосовой ввод на сегодня недоступен. Напишите вопрос текстом.')
        text=await stt.transcribe(data,file.filename or 'recording.webm',file.content_type or 'audio/webm')
        return {'text':text,'provider':'groq','model':settings.groq_stt_model}
    except HTTPException: raise
    except Exception:
        log.exception('stt failed'); raise HTTPException(status_code=502,detail='Не удалось распознать речь.')

@app.post('/api/voice/synthesize')
async def synthesize(req:TTSRequest, request:Request):
    limits.check(request,'tts')
    if not limits.spend('tts'): raise HTTPException(503,'Озвучка на сегодня недоступна.')
    try:
        if req.voice=='groq_en':
            audio=await groq_tts.synthesize(req.text); return Response(audio,media_type='audio/wav')
        if req.voice=='secondary':
            voice=settings.tts_voice_secondary; role=settings.tts_voice_secondary_role
        else:
            voice=settings.tts_voice_primary; role=settings.tts_voice_primary_role
        audio=await yandex_tts.synthesize(req.text,voice,role)
        return Response(audio,media_type='audio/ogg')
    except Exception:
        log.exception('tts failed'); raise HTTPException(status_code=502,detail='Не удалось озвучить ответ.')

@app.post('/api/admin/reindex')
async def reindex(x_admin_token:str|None=Header(None)):
    if settings.admin_token=='change-me' or not x_admin_token or not hmac.compare_digest(x_admin_token,settings.admin_token): raise HTTPException(403,'Forbidden')
    count=index.rebuild(); return {'ok':True,'chunks':count}

# Production build is copied to ROOT/frontend_dist by Dockerfile.
static_dir=ROOT/'frontend_dist'
if static_dir.exists():
    app.mount('/assets',StaticFiles(directory=static_dir/'assets'),name='assets')
    @app.get('/manifest.webmanifest')
    async def manifest(): return FileResponse(static_dir/'manifest.webmanifest')
    @app.get('/sw.js')
    async def sw(): return FileResponse(static_dir/'sw.js')
    @app.get('/{full_path:path}')
    async def spa(full_path:str):
        if full_path.startswith('api/'): raise HTTPException(404)
        safe=resolve_static(static_dir, full_path) if full_path else None
        if safe: return FileResponse(safe)
        return FileResponse(static_dir/'index.html')
