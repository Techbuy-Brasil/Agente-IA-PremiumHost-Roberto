import os
import json
import hashlib
import hmac
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
import httpx

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

EVOLUTION_API_URL = os.getenv("WHATSAPP_BASE_URL", "http://localhost:8080")
INSTANCE = os.getenv("WHATSAPP_INSTANCE", "agente_hospedagem")
API_KEY = os.getenv("WHATSAPP_API_KEY", "")
WEBHOOK_SECRET = os.getenv("WHATSAPP_WEBHOOK_SECRET", "secret")


def _get_evolution_headers():
    return {
        "Content-Type": "application/json",
        "apikey": API_KEY,
    }


# --- Recebimento de mensagens via Webhook Evolution API ---
@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    body = await request.json()
    event = body.get("event", "")

    if event == "messages.upsert":
        messages = body.get("data", {}).get("messages", [])
        for msg in messages:
            if msg.get("key", {}).get("fromMe"):
                continue
            push_name = msg.get("pushName", "Cliente")
            remote_jid = msg.get("key", {}).get("remoteJid", "")
            message_text = ""
            msg_type = msg.get("message", {})

            if "conversation" in msg_type:
                message_text = msg_type["conversation"]
            elif "extendedTextMessage" in msg_type:
                message_text = msg_type["extendedTextMessage"].get("text", "")

            if not message_text:
                continue

            from api import agent
            response = agent.respond(message_text, push_name, remote_jid)

            await send_whatsapp(remote_jid, response)

    return {"status": "ok"}


# --- Envio de mensagens via Evolution API ---
async def send_whatsapp(to: str, text: str):
    url = f"{EVOLUTION_API_URL}/message/sendText/{INSTANCE}"
    payload = {
        "number": to,
        "text": text,
        "options": {"delay": 1000, "presence": "composing"},
    }
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(url, json=payload, headers=_get_evolution_headers(), timeout=15)
            return r.json()
        except Exception as e:
            print(f"[WhatsApp] Erro ao enviar: {e}")
            return None


# --- Verificacao de conexao com Evolution API ---
@router.get("/status")
async def whatsapp_status():
    url = f"{EVOLUTION_API_URL}/instance/connectionState/{INSTANCE}"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, headers=_get_evolution_headers(), timeout=10)
            return r.json()
        except Exception as e:
            return {"error": str(e), "message": "Evolution API nao acessivel. Verifique se o container esta rodando."}


# --- QR Code para conexao do WhatsApp ---
@router.get("/qrcode")
async def get_qrcode():
    url = f"{EVOLUTION_API_URL}/instance/qrcode/{INSTANCE}"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, headers=_get_evolution_headers(), timeout=10)
            return r.json()
        except Exception as e:
            return {"error": str(e)}


# --- Instanciar/Conectar Evolution API ---
@router.post("/conectar")
async def connect_instance():
    url = f"{EVOLUTION_API_URL}/instance/create"
    payload = {
        "instanceName": INSTANCE,
        "token": API_KEY,
        "qrcode": True,
        "webhook": {
            "url": f"{os.getenv('API_URL', 'http://localhost:8000')}/whatsapp/webhook",
            "enabled": True,
            "events": ["messages.upsert"],
        },
    }
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(url, json=payload, headers=_get_evolution_headers(), timeout=15)
            return r.json()
        except Exception as e:
            return {"error": str(e)}
