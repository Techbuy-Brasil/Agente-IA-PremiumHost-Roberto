import os
import json
from typing import Optional
from fastapi import APIRouter, Request
import httpx

router = APIRouter(prefix="/instagram", tags=["instagram"])

ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
BUSINESS_ID = os.getenv("INSTAGRAM_BUSINESS_ID", "")
API_URL = os.getenv("API_URL", "http://localhost:8000")
VERIFY_TOKEN = os.getenv("WHATSAPP_WEBHOOK_SECRET", "agente_secret_2026")


# --- Webhook para Instagram (via Meta Cloud API) ---
@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = None,
    hub_verify_token: str = None,
    hub_challenge: str = None,
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return int(hub_challenge) if hub_challenge else 200
    return {"error": "Verification failed"}, 403


@router.post("/webhook")
async def instagram_webhook(request: Request):
    body = await request.json()

    entries = body.get("entry", [])
    for entry in entries:
        messaging = entry.get("messaging", [])
        for msg in messaging:
            sender_id = msg.get("sender", {}).get("id", "")
            message = msg.get("message", {})
            message_text = message.get("text", "")

            if not message_text:
                continue

            from api import agent
            response = agent.respond(message_text, None, f"ig_{sender_id}")

            await send_instagram(sender_id, response)

    return {"status": "ok"}


# --- Envio de mensagens via Instagram Graph API ---
async def send_instagram(recipient_id: str, text: str):
    if not ACCESS_TOKEN or not BUSINESS_ID:
        print("[Instagram] Token ou Business ID nao configurados")
        return

    url = f"https://graph.facebook.com/v18.0/{BUSINESS_ID}/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
        "messaging_type": "RESPONSE",
    }
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(url, json=payload, headers=headers, timeout=15)
            return r.json()
        except Exception as e:
            print(f"[Instagram] Erro ao enviar: {e}")
            return None


# --- Status da integracao ---
@router.get("/status")
async def status():
    if not ACCESS_TOKEN:
        return {
            "connected": False,
            "message": "INSTAGRAM_ACCESS_TOKEN nao configurado",
        }
    url = f"https://graph.facebook.com/v18.0/{BUSINESS_ID}?fields=name,username"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, headers=headers, timeout=10)
            data = r.json()
            return {
                "connected": True,
                "name": data.get("name"),
                "username": data.get("username"),
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}
