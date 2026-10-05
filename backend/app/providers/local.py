from .base import BaseProvider

class LocalFallbackProvider(BaseProvider):
    name='local'; model='extractive-demo'
    def configured(self) -> bool: return True
    async def generate(self, messages: list[dict]) -> str:
        user=next((m['content'] for m in reversed(messages) if m['role']=='user'), '')
        ctx=next((m['content'] for m in messages if m['role']=='system' and 'КОНТЕКСТ ИЗ БАЗЫ' in m['content']), '')
        ctx = ctx.split('## КОНТЕКСТ ИЗ БАЗЫ', 1)[-1]
        # Local mode deliberately does not invent; it exposes retrieval when no cloud key is present.
        snippets=[]
        for block in ctx.split('---'):
            block=block.strip()
            if block and '[SOURCE' in block:
                snippets.append(block[:900])
        body='\n\n'.join(snippets[:3]) or 'Релевантные сведения в локальной базе не найдены.'
        return ('Сейчас приложение работает в локальном демо-режиме без подключённой LLM. '
                'Я не буду достраивать ответ. Ниже — найденные фрагменты базы:\n\n'+body+'\n\n'
                'Следующий шаг: подключите GigaChat, Groq, Qwen или OpenAI в .env для полноценного ответа.')
