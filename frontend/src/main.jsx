import React,{useEffect,useMemo,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Mic,Send,Volume2,ChevronDown,ShieldCheck,Database,Zap,RefreshCw,Square,Trash2} from 'lucide-react';
import './styles.css';
import './dkor-polish.css';

const roles=['Не выбрана','UI/UX-дизайнер','3D-визуализатор','Дизайнер интерьера','AI-видеограф','Видеомонтажёр','Backend-разработчик','Менеджер по продажам','Маркетолог','HR','Документооборот','IT-поддержка'];
const stages=['Не выбран','Первый день','Первая неделя','Первый месяц','Испытательный срок'];
const quick=['Что сделать в первый день?','Какие доступы мне нужны?','Как оформить отпуск?','Не работает VPN','К кому обратиться?'];

function newSession(){return crypto.randomUUID?.()||Math.random().toString(36).slice(2)}

class ErrorBoundary extends React.Component{
 constructor(props){super(props);this.state={error:null}}
 static getDerivedStateFromError(error){return {error}}
 componentDidCatch(error,info){console.error('DKOR UI render error',error,info)}
 render(){if(this.state.error){return <div style={{padding:24,color:'#fff',background:'#0c0f14',minHeight:'100vh',fontFamily:'system-ui'}}><h2>Ошибка интерфейса</h2><p>Frontend не скрыт: показана реальная ошибка.</p><pre style={{whiteSpace:'pre-wrap',color:'#ffb4b4'}}>{String(this.state.error?.stack||this.state.error)}</pre><button onClick={()=>location.reload()}>Перезагрузить</button></div>}return this.props.children}
}

function App(){
 const [session,setSession]=useState(()=>localStorage.getItem('dkor_session')||newSession());
 const [messages,setMessages]=useState([{role:'assistant',content:'Здравствуйте. Я DKOR Onboard. Помогу с первым днём, доступами, документами, ролевыми треками и эскалациями. Что хотите уточнить?',sources:[]}]);
 const [text,setText]=useState(''); const [provider,setProvider]=useState('auto'); const [role,setRole]=useState('Не выбрана'); const [stage,setStage]=useState('Не выбран');
 const [voice,setVoice]=useState('primary'); const [autoVoice,setAutoVoice]=useState(false); const [speechRate,setSpeechRate]=useState(1.25); const [loading,setLoading]=useState(false); const [health,setHealth]=useState(null);
 const [recording,setRecording]=useState(false); const [voicePreview,setVoicePreview]=useState(''); const recRef=useRef(null); const chunksRef=useRef([]); const chatRef=useRef(null); const speechRecRef=useRef(null); const recordingActiveRef=useRef(false); const voiceCommittedRef=useRef(''); const voiceSessionRef=useRef('');
 useEffect(()=>{localStorage.setItem('dkor_session',session); fetch('/api/health').then(r=>r.json()).then(setHealth).catch(()=>{}); if(import.meta.env.PROD && 'serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(()=>{});},[session]);
 useEffect(()=>{const el=chatRef.current;if(el) requestAnimationFrame(()=>{el.scrollTop=el.scrollHeight;});},[messages,loading,voicePreview]);
  function browserSpeak(content){
   const value=String(content||'').trim();
   if(!value)return;

   if(!('speechSynthesis' in window) ||
      typeof SpeechSynthesisUtterance==='undefined'){
     throw new Error('System speech synthesis unavailable');
   }

   window.speechSynthesis.cancel();

   const u=new SpeechSynthesisUtterance(value);
   u.lang='ru-RU';
   u.rate=speechRate;
   u.pitch=1;

   const voices=window.speechSynthesis.getVoices();
   const ru=voices.find(v=>
     String(v?.lang||'').toLowerCase().startsWith('ru')
   );

   if(ru)u.voice=ru;

   window.speechSynthesis.speak(u);
 }

 async function speak(content){
   const value=String(content||'').trim();
   if(!value)return;

   const backendRussianTTS=Boolean(health?.voice?.yandex_tts);

   if(!backendRussianTTS){
     try{
       browserSpeak(value);
     }catch(e){
       alert('\u041e\u0437\u0432\u0443\u0447\u043a\u0430 \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u0430 \u0432 \u044d\u0442\u043e\u043c \u0431\u0440\u0430\u0443\u0437\u0435\u0440\u0435');
     }
     return;
   }

   try{
     const r=await fetch('/api/voice/synthesize',{
       method:'POST',
       headers:{'Content-Type':'application/json'},
       body:JSON.stringify({text:value,voice})
     });

     if(!r.ok){
       let detail='TTS error';
       try{
         const d=await r.json();
         detail=d?.detail||detail;
       }catch{}
       throw new Error(detail);
     }

     const blob=await r.blob();
     const url=URL.createObjectURL(blob);
     const a=new Audio(url);

     a.onended=()=>URL.revokeObjectURL(url);
     a.onerror=()=>URL.revokeObjectURL(url);

     await a.play();
   }catch(e){
     try{
       browserSpeak(value);
     }catch{
       alert('\u041e\u0437\u0432\u0443\u0447\u043a\u0430: '+String(e?.message||e));
     }
   }
 }

 function mergeSpeechParts(parts){
   let out='';

   for(const raw of parts){
     const t=String(raw||'').replace(/\s+/g,' ').trim();
     if(!t)continue;

     if(!out){
       out=t;
       continue;
     }

     const a=out.toLowerCase();
     const b=t.toLowerCase();

     if(b.startsWith(a)){
       out=t;
       continue;
     }

     if(a.includes(b) || a.endsWith(b)){
       continue;
     }

     out=(out+' '+t).trim();
   }

   return out.trim();
 }
 async function send(q=text){const question=String(q??'').trim(); if(!question||loading)return; setText(''); setMessages(m=>[...m,{role:'user',content:question,sources:[]}]); setLoading(true); try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:question,session_id:session,provider,role,stage})}); const data=await r.json(); if(!r.ok) throw new Error(String(data?.detail||'Ошибка')); const safeSources=Array.isArray(data?.sources)?data.sources.map((s,i)=>({source:String(s?.source??''),section:String(s?.section??'Источник'),chunk_id:String(s?.chunk_id??i),score:Number.isFinite(Number(s?.score))?Number(s.score):0,preview:String(s?.preview??'')})):[]; const msg={role:'assistant',content:String(data?.answer??''),sources:safeSources,provider:String(data?.provider??''),model:String(data?.model??''),escalations:Array.isArray(data?.escalations)?data.escalations.map(String):[]}; setMessages(m=>[...m,msg]); if(autoVoice&&msg.content) speak(msg.content);}catch(e){setMessages(m=>[...m,{role:'assistant',content:'Ошибка: '+String(e?.message||e),sources:[],error:true}])}finally{setLoading(false)}}
  async function toggleRecord(){
   if(recording){
     recordingActiveRef.current=false;

     try{
       speechRecRef.current?.stop();
     }catch{}

     speechRecRef.current=null;
     recRef.current?.stop();
     return;
   }

   try{
     const stream=await navigator.mediaDevices.getUserMedia({audio:true});
     const rec=new MediaRecorder(stream);

     chunksRef.current=[];
     voiceCommittedRef.current='';
     voiceSessionRef.current='';
     recordingActiveRef.current=true;

     setVoicePreview(
       '\u0413\u043e\u0432\u043e\u0440\u0438\u0442\u0435\u2026'
     );

     const SpeechRecognition=
       window.SpeechRecognition ||
       window.webkitSpeechRecognition;

     if(SpeechRecognition){
       const sr=new SpeechRecognition();

       sr.lang='ru-RU';
       sr.interimResults=true;

       const isAndroid=/Android/i.test(navigator.userAgent);
       sr.continuous=!isAndroid;

       sr.onresult=(e)=>{
         const parts=[];

         for(let i=0;i<e.results.length;i++){
           const t=e.results[i]?.[0]?.transcript;
           if(t)parts.push(t);
         }

         const current=mergeSpeechParts(parts);

         if(current){
           voiceSessionRef.current=current;

           const visible=mergeSpeechParts([
             voiceCommittedRef.current,
             current
           ]);

           if(visible)setVoicePreview(visible);
         }
       };

       sr.onerror=()=>{};

       sr.onend=()=>{
         if(!recordingActiveRef.current)return;

         if(voiceSessionRef.current){
           voiceCommittedRef.current=mergeSpeechParts([
             voiceCommittedRef.current,
             voiceSessionRef.current
           ]);

           voiceSessionRef.current='';
         }

         if(isAndroid){
           setTimeout(()=>{
             if(recordingActiveRef.current){
               try{sr.start()}catch{}
             }
           },120);
         }
       };

       try{
         sr.start();
         speechRecRef.current=sr;
       }catch{}
     }

     rec.ondataavailable=e=>{
       if(e.data?.size)chunksRef.current.push(e.data);
     };

     rec.onstop=async()=>{
       recordingActiveRef.current=false;
       setRecording(false);

       try{
         speechRecRef.current?.stop();
       }catch{}

       speechRecRef.current=null;

       stream.getTracks().forEach(t=>t.stop());

       setVoicePreview(
         '\u0420\u0430\u0441\u043f\u043e\u0437\u043d\u0430\u044e \u0437\u0430\u043f\u0438\u0441\u044c\u2026'
       );

       const blob=new Blob(
         chunksRef.current,
         {type:rec.mimeType||'audio/webm'}
       );

       const fd=new FormData();
       fd.append('file',blob,'voice.webm');

       setLoading(true);

       try{
         const r=await fetch(
           '/api/voice/transcribe',
           {method:'POST',body:fd}
         );

         const d=await r.json();

         if(!r.ok){
           throw new Error(d?.detail||'STT error');
         }

         const finalText=String(d?.text||'').trim();

         if(finalText){
           setText(finalText);
         }

         setVoicePreview('');
       }catch(e){
         setVoicePreview('');

         alert(
           '\u0420\u0430\u0441\u043f\u043e\u0437\u043d\u0430\u0432\u0430\u043d\u0438\u0435: '+
           String(e?.message||e)
         );
       }finally{
         setLoading(false);
       }
     };

     rec.start();
     recRef.current=rec;
     setRecording(true);

   }catch(e){
     recordingActiveRef.current=false;
     setVoicePreview('');

     alert(
       '\u041c\u0438\u043a\u0440\u043e\u0444\u043e\u043d \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d: '+
       String(e?.message||e)
     );
   }
 }
 async function clearChat(){await fetch('/api/session/'+session,{method:'DELETE'}).catch(()=>{}); const ns=newSession(); setSession(ns); setMessages([{role:'assistant',content:'Новая сессия создана. Контекст предыдущего диалога очищен.',sources:[]}])}
 return <div className="shell">
   <aside className="sidebar">
    <div className="brand"><div className="mark">D</div><div><b>DKOR Onboard</b><span>AI Employee Assistant</span></div></div>
    <div className="status"><ShieldCheck size={16}/><div><b>Учебный контур</b><span>Контакты и сотрудники вымышлены</span></div></div>
    <label>Модель<select value={provider} onChange={e=>setProvider(e.target.value)}><option value="auto">Auto</option><option value="gigachat">GigaChat</option><option value="groq">Groq</option><option value="qwen">Qwen</option><option value="openai">ChatGPT / OpenAI</option><option value="local">Local demo</option></select></label>
    <label>Роль<select value={role} onChange={e=>setRole(e.target.value)}>{roles.map(x=><option key={x}>{x}</option>)}</select></label>
    <label>Этап<select value={stage} onChange={e=>setStage(e.target.value)}>{stages.map(x=><option key={x}>{x}</option>)}</select></label>
    <div className="voicebox">
      <span>{'\u0413\u043e\u043b\u043e\u0441 \u043e\u0442\u0432\u0435\u0442\u0430'}</span>

      {health?.voice?.yandex_tts
        ? <div className="voiceBtns">
            <button className={voice==='primary'?'on':''} onClick={()=>setVoice('primary')}>
              {'\u041c\u0430\u0440\u0438\u043d\u0430'}
            </button>
            <button className={voice==='secondary'?'on':''} onClick={()=>setVoice('secondary')}>
              {'\u0415\u0440\u043c\u0438\u043b'}
            </button>
          </div>
        : <div className="voiceBtns">
            <button className="on" disabled>
              {'\u0421\u0438\u0441\u0442\u0435\u043c\u043d\u044b\u0439 \u0433\u043e\u043b\u043e\u0441'}
            </button>
          </div>
      }

      
      <label className="voiceRate">
        <span>{'\u0421\u043a\u043e\u0440\u043e\u0441\u0442\u044c'}</span>
        <select
          value={speechRate}
          onChange={e=>setSpeechRate(Number(e.target.value))}
        >
          <option value={1}>1.0\u00d7</option>
          <option value={1.25}>1.25\u00d7</option>
          <option value={1.5}>1.5\u00d7</option>
        </select>
      </label>

<label className="toggle">
        <input
          type="checkbox"
          checked={autoVoice}
          onChange={e=>setAutoVoice(e.target.checked)}
        />
        {'\u041e\u0437\u0432\u0443\u0447\u0438\u0432\u0430\u0442\u044c \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438'}
      </label>
    </div>
    <div className="health"><Database size={15}/><span>{health?`${health.chunks} фрагментов базы`:'Проверяю базу…'}</span></div>
    <button className="ghost" onClick={clearChat}><Trash2 size={16}/>Новая сессия</button>
   </aside>
   <main className="main">
    <header><div><h1>Адаптация без догадок</h1><p>RAG по внутренней базе · источники · эскалации · голос</p></div><div className="providerState"><Zap size={16}/> {provider==='auto'?'Auto routing':(health?.providers?.[provider]?.configured===false?'не настроен':'готов')}</div></header>
    <div className="quick">{quick.map(q=><button key={q} onClick={()=>send(q)}>{q}</button>)}</div>
    <section className="chat" ref={chatRef}>
     {messages.map((m,i)=><div key={i} className={'row '+m.role}><div className={'bubble '+(m.error?'error':'')}><div className="msgText">{String(m.content??'')}</div>{m.role==='assistant'&&<div className="meta"><button onClick={()=>speak(m.content)}><Volume2 size={15}/>Озвучить</button>{m.provider&&<span>{m.provider} · {m.model}</span>}</div>}{Array.isArray(m.sources)&&m.sources.length>0&&<details><summary><ChevronDown size={14}/>Почему такой ответ? · {m.sources.length} источников</summary><div className="sources">{m.sources.map(s=><div key={s.chunk_id}><b>{s.section}</b><span>{s.source} · score {s.score}</span><p>{s.preview}</p></div>)}</div></details>}</div></div>)}
     {loading&&<div className="row assistant"><div className="bubble typing"><RefreshCw size={16} className="spin"/>Думаю…</div></div>}
    </section>
    <footer><textarea className={(recording||voicePreview)?'voiceInputLive':''} maxLength={500} value={(recording||voicePreview)?voicePreview:text} readOnly={recording||Boolean(voicePreview)} onChange={e=>setText(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}} placeholder="Спросите про первый день, доступы, документы…"/><button className={'mic '+(recording?'rec':'')} onClick={toggleRecord}>{recording?<Square size={20}/>:<Mic size={20}/>}</button><button className="send" onClick={()=>send()} disabled={loading}><Send size={20}/></button></footer>
   </main>
 </div>
}
createRoot(document.getElementById('root')).render(<ErrorBoundary><App/></ErrorBoundary>);
