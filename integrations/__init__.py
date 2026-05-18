import os
from pathlib import Path

# Exporta todos os routers para registro centralizado na api.py
from integrations.whatsapp import router as whatsapp_router
from integrations.instagram import router as instagram_router
from integrations.crm import router as crm_router

__all__ = ["whatsapp_router", "instagram_router", "crm_router"]
