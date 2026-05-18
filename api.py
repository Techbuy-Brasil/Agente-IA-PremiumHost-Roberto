import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from agent import Agent
from storage import ConversationStore
from integrations import whatsapp_router, instagram_router, crm_router
import uvicorn
import os

app = FastAPI(title="Agente de Hospedagem Inteligente", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra routers de integracao
app.include_router(whatsapp_router)
app.include_router(instagram_router)
app.include_router(crm_router)

agent = Agent()
store = ConversationStore()


# --- Models ---
class MessageRequest(BaseModel):
    message: str = Field(..., description="Mensagem do hospede")
    guest_name: Optional[str] = Field(None, description="Nome do hospede")
    guest_id: Optional[str] = Field(None, description="ID unico do hospede")
    platform: Optional[str] = Field("api", description="Plataforma de origem (api, whatsapp, instagram, web)")

class QuoteRequest(BaseModel):
    property_key: str = Field(..., description="Chave do imovel")
    checkin: str = Field(..., description="Data check-in (DD/MM/AAAA)")
    checkout: str = Field(..., description="Data check-out (DD/MM/AAAA)")
    guests: int = Field(2, ge=1, le=6, description="Numero de hospedes")


# --- Static files ---
HTML_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(HTML_DIR, exist_ok=True)


# --- Endpoints ---
@app.get("/")
def root():
    return {
        "servico": "Agente de Hospedagem Inteligente",
        "versao": "1.0.0",
        "imoveis": list(agent.pm.properties.keys()),
        "endpoints": {
            "chat": "/chat",
            "cotacao": "/cotacao",
            "imoveis": "/imoveis",
            "webhook": "/webhook/mensagem",
            "chat_web": "/webchat",
            "health": "/health"
        }
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/imoveis")
def list_properties():
    result = {}
    for key in agent.pm.list_properties():
        p = agent.pm.get_property(key)
        result[key] = {
            "nome": p.name,
            "localizacao": p.location,
            "capacidade": p.capacity,
            "diaria_base": p.base_price,
            "hospedes_base": p.base_guests,
            "taxa_extra": p.extra_guest_fee,
            "taxa_limpeza": p.cleaning_fee,
            "comodidades": p.amenities,
            "descricao": p.description,
        }
    return result

@app.post("/chat")
def chat(req: MessageRequest):
    try:
        guest_id = req.guest_id or req.guest_name or "anon"
        response = agent.respond(req.message, req.guest_name, guest_id)
        return {"response": response, "guest_id": guest_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cotacao")
def quote(req: QuoteRequest):
    from datetime import datetime

    prop = agent.pm.get_property(req.property_key)
    if not prop:
        raise HTTPException(status_code=404, detail=f"Imovel '{req.property_key}' nao encontrado")

    try:
        checkin = datetime.strptime(req.checkin, "%d/%m/%Y").date()
        checkout = datetime.strptime(req.checkout, "%d/%m/%Y").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data invalido. Use DD/MM/AAAA")

    engine = __import__("pricing").PricingEngine(prop, agent.calendar)

    avail, msg = engine.check_availability(checkin, checkout)
    if not avail:
        return {"disponivel": False, "motivo": msg}

    breakdown = engine.calculate_total(checkin, checkout, req.guests)
    return {
        "disponivel": True,
        "imovel": prop.name,
        "checkin": checkin.strftime("%d/%m/%Y"),
        "checkout": checkout.strftime("%d/%m/%Y"),
        "noites": breakdown["nights"],
        "hospedes": req.guests,
        "total": breakdown["total"],
        "media_noite": breakdown["nightly_avg"],
        "taxa_hospedes_extras": breakdown.get("extra_guests_fee", 0),
        "taxa_limpeza": breakdown.get("cleaning_fee", 0),
        "temporada": agent.calendar.get_season_label(checkin, checkout),
    }

@app.post("/webhook/mensagem")
async def webhook_message(request: Request):
    body = await request.json()
    platform = body.get("platform", "unknown")
    message = body.get("message", "")
    guest_name = body.get("guest_name")
    guest_id = body.get("guest_id")

    if not message:
        return JSONResponse(status_code=400, content={"erro": "Mensagem vazia"})

    response = agent.respond(message, guest_name, guest_id)

    return {
        "platform": platform,
        "response": response,
        "guest_id": guest_id or "anon"
    }

@app.get("/webchat", response_class=HTMLResponse)
def web_chat():
    return HTMLResponse(content=WEBCHAT_HTML, status_code=200)

@app.get("/estatisticas")
def stats():
    return store.get_stats()

@app.get("/conversas/{guest_id}")
def get_conversations(guest_id: str):
    data = store.get_guest(guest_id)
    return data


# --- Web Chat HTML ---
WEBCHAT_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agente de Hospedagem</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); height: 100vh; display: flex; align-items: center; justify-content: center; }
        .chat-container { width: 420px; max-width: 95vw; height: 700px; max-height: 95vh; background: #fff; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); display: flex; flex-direction: column; overflow: hidden; }
        .chat-header { background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 20px 24px; }
        .chat-header h2 { font-size: 18px; font-weight: 600; }
        .chat-header p { font-size: 13px; opacity: 0.85; margin-top: 4px; }
        .messages { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 12px; background: #f8f9fe; }
        .message { max-width: 85%; padding: 12px 16px; border-radius: 16px; font-size: 14px; line-height: 1.5; animation: fadeIn 0.3s ease; }
        .message.bot { align-self: flex-start; background: #fff; color: #333; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-bottom-left-radius: 4px; }
        .message.user { align-self: flex-end; background: #667eea; color: #fff; border-bottom-right-radius: 4px; }
        .message.system { align-self: center; background: #e8e8e8; color: #666; font-size: 12px; border-radius: 8px; padding: 6px 16px; }
        .message .time { font-size: 11px; opacity: 0.6; margin-top: 4px; display: block; }
        .input-area { padding: 16px 20px; background: #fff; border-top: 1px solid #eee; display: flex; gap: 10px; }
        .input-area input { flex: 1; padding: 12px 16px; border: 2px solid #eee; border-radius: 25px; font-size: 14px; outline: none; transition: border 0.2s; }
        .input-area input:focus { border-color: #667eea; }
        .input-area button { width: 50px; height: 50px; border-radius: 50%; border: none; background: linear-gradient(135deg, #667eea, #764ba2); color: #fff; font-size: 20px; cursor: pointer; transition: transform 0.2s; display: flex; align-items: center; justify-content: center; }
        .input-area button:hover { transform: scale(1.05); }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .typing { align-self: flex-start; background: #e8e8e8; padding: 12px 20px; border-radius: 16px; display: flex; gap: 4px; }
        .typing span { width: 8px; height: 8px; background: #999; border-radius: 50%; animation: typing 1.4s infinite; }
        .typing span:nth-child(2) { animation-delay: 0.2s; }
        .typing span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes typing { 0%, 60%, 100% { opacity: 0.3; transform: translateY(0); } 30% { opacity: 1; transform: translateY(-4px); } }
        .whatsapp-link { display: block; text-align: center; padding: 8px; background: #25D366; color: white; text-decoration: none; font-size: 13px; font-weight: 500; }
        .whatsapp-link:hover { background: #1da851; }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h2>Agente de Hospedagem</h2>
            <p>Imoveis em Salvador | Atendimento instantaneo</p>
        </div>
        <a class="whatsapp-link" href="https://wa.me/5571999999999?text=Ola!%20Quero%20informacoes%20sobre%20hospedagem" target="_blank">Fale conosco pelo WhatsApp</a>
        <div class="messages" id="messages">
            <div class="message system">
                <span>Atendimento iniciado</span>
            </div>
        </div>
        <div class="input-area">
            <input type="text" id="input" placeholder="Digite sua mensagem..." autofocus>
            <button id="send" onclick="sendMessage()">→</button>
        </div>
    </div>
    <script>
        const messages = document.getElementById('messages');
        const input = document.getElementById('input');
        let guestId = 'web_' + Date.now();

        const BOT_AVATAR = '🤖';
        const USER_AVATAR = '👤';

        function addMessage(text, type) {
            const div = document.createElement('div');
            div.className = 'message ' + type;
            const time = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });

            if (type === 'bot') {
                div.innerHTML = text.replace(/\\n/g, '<br>') + '<span class="time">' + time + '</span>';
            } else {
                div.innerHTML = text.replace(/\\n/g, '<br>') + '<span class="time">' + time + '</span>';
            }
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        }

        function showTyping() {
            const div = document.createElement('div');
            div.className = 'typing';
            div.id = 'typing';
            div.innerHTML = '<span></span><span></span><span></span>';
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        }

        function hideTyping() {
            const t = document.getElementById('typing');
            if (t) t.remove();
        }

        function cleanText(text) {
            return text.replace(/\\*\\*/g, '');
        }

        async function sendMessage() {
            const text = input.value.trim();
            if (!text) return;
            input.value = '';
            addMessage(text, 'user');
            showTyping();

            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text, guest_id: guestId, platform: 'web' })
                });
                const data = await res.json();
                hideTyping();
                addMessage(cleanText(data.response), 'bot');
            } catch (e) {
                hideTyping();
                addMessage('Desculpe, ocorreu um erro. Tente novamente.', 'bot');
            }
        }

        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        // Mensagem inicial
        setTimeout(async () => {
            showTyping();
            const res = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: 'Ola', guest_id: guestId, platform: 'web' })
            });
            const data = await res.json();
            hideTyping();
            addMessage(cleanText(data.response), 'bot');
        }, 500);
    </script>
</body>
</html>
"""


# --- iCal Sync Endpoints ---
@app.post("/ical/sync")
async def ical_sync(background_tasks: BackgroundTasks):
    from integrations.ical_sync import ICalSync
    background_tasks.add_task(ICalSync.sync_all)
    return {"status": "sync_started", "message": "Sincronizacao iCal iniciada em segundo plano"}


@app.get("/ical/status")
async def ical_status():
    from integrations.ical_sync import ICalSync
    result = {}
    for key in ICAL_URLS:
        cached = ICalSync.load_cache(key)
        result[key] = {"blocked_dates": len(cached)}
    return result


ICAL_URLS = {
    "farol_barra_flat_214": os.getenv(
        "ICAL_FAROL_BARRA",
        "https://www.airbnb.com.br/calendar/ical/41662018.ics",
    ),
    "ondina_apt_hotel_441": os.getenv(
        "ICAL_ONDINA",
        "https://www.airbnb.com.br/calendar/ical/986288391373272410.ics",
    ),
    "the_plaza_407": os.getenv(
        "ICAL_THE_PLAZA",
        "https://www.airbnb.com.br/calendar/ical/1544328946353777106.ics",
    ),
    "smart_convencoes_509": os.getenv(
        "ICAL_SMART",
        "https://www.airbnb.com.br/calendar/ical/1320242268460204756.ics",
    ),
}


@app.on_event("startup")
async def startup_ical_sync():
    from integrations.ical_sync import ICalSync
    try:
        await ICalSync.sync_all()
        print("[iCal] Sincronizado na inicializacao")
    except Exception as e:
        print(f"[iCal] Erro na sincronizacao inicial: {e}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
