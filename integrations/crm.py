import os
import json
from datetime import datetime
from typing import Optional, Dict
from fastapi import APIRouter, HTTPException
import httpx

router = APIRouter(prefix="/crm", tags=["crm"])

CRM_TYPE = os.getenv("CRM_TYPE", "hubspot").lower()
CRM_API_KEY = os.getenv("CRM_API_KEY", "")
CRM_EMAIL = os.getenv("CRM_EMAIL", "")


class CRMClient:
    @staticmethod
    async def send_to_hubspot(contact: Dict):
        url = "https://api.hubapi.com/crm/v3/objects/contacts"
        headers = {
            "Authorization": f"Bearer {CRM_API_KEY}",
            "Content-Type": "application/json",
        }
        properties = {
            "email": contact.get("email", ""),
            "firstname": contact.get("name", ""),
            "phone": contact.get("phone", ""),
            "hs_lead_status": "NEW",
            "lead_source": contact.get("source", "airbnb_chat"),
            "description": json.dumps(contact.get("notes", ""), ensure_ascii=False),
        }
        payload = {"properties": properties}
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(url, json=payload, headers=headers, timeout=15)
                return r.json()
            except Exception as e:
                return {"error": str(e)}

    @staticmethod
    async def send_to_pipedrive(contact: Dict):
        url = f"https://api.pipedrive.com/v1/persons?api_token={CRM_API_KEY}"
        payload = {
            "name": contact.get("name", "Cliente"),
            "email": contact.get("email", ""),
            "phone": contact.get("phone", ""),
            "cf_source": contact.get("source", "airbnb_chat"),
        }
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(url, json=payload, timeout=15)
                return r.json()
            except Exception as e:
                return {"error": str(e)}

    @staticmethod
    async def send_to_sheets(contact: Dict):
        """
        Envia para Google Sheets via webhook do n8n / Make / Zapier
        Configure CRM_API_KEY como a URL do webhook
        """
        if not CRM_API_KEY:
            return {"error": "URL do webhook nao configurada em CRM_API_KEY"}
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(CRM_API_KEY, json=contact, timeout=15)
                return r.json()
            except Exception as e:
                return {"error": str(e)}

    @staticmethod
    async def sync(contact: Dict):
        if CRM_TYPE == "hubspot":
            return await CRMClient.send_to_hubspot(contact)
        elif CRM_TYPE == "pipedrive":
            return await CRMClient.send_to_pipedrive(contact)
        elif CRM_TYPE == "sheets":
            return await CRMClient.send_to_sheets(contact)
        else:
            return {"error": f"CRM type '{CRM_TYPE}' nao suportado"}


# --- Endpoint para criar/atualizar contato no CRM ---
@router.post("/contato")
async def create_contact(data: dict):
    required = ["name"]
    for field in required:
        if field not in data:
            raise HTTPException(status_code=400, detail=f"Campo obrigatorio: {field}")

    contact = {
        "name": data["name"],
        "email": data.get("email", ""),
        "phone": data.get("phone", ""),
        "source": data.get("source", "web_chat"),
        "notes": data.get("notes", ""),
        "timestamp": datetime.now().isoformat(),
    }

    result = await CRMClient.sync(contact)
    return {"synced": True, "crm": CRM_TYPE, "result": result}


# --- Endpoint para registrar orcamento como negocio ---
@router.post("/negocio")
async def create_deal(data: dict):
    required = ["property", "total", "guest_name"]
    for field in required:
        if field not in data:
            raise HTTPException(status_code=400, detail=f"Campo obrigatorio: {field}")

    deal = {
        "title": f"{data['guest_name']} - {data['property']}",
        "value": data["total"],
        "stage": data.get("stage", "negociacao"),
        "notes": data.get("notes", ""),
    }

    if CRM_TYPE == "hubspot":
        url = "https://api.hubapi.com/crm/v3/objects/deals"
        headers = {
            "Authorization": f"Bearer {CRM_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "properties": {
                "dealname": deal["title"],
                "amount": str(deal["value"]),
                "dealstage": deal["stage"],
                "description": deal["notes"],
            }
        }
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(url, json=payload, headers=headers, timeout=15)
                return {"synced": True, "crm": CRM_TYPE, "result": r.json()}
            except Exception as e:
                return {"synced": False, "error": str(e)}

    return {"synced": False, "message": f"CRM {CRM_TYPE} nao suporta negocios via API"}
