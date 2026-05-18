import sys
from agent import Agent
from datetime import date
from api import app
from fastapi.testclient import TestClient

agent = Agent()
results = []

def log(msg):
    results.append(msg)

# --- Test 1 ---
resp = agent.respond("Quero o Farol Barra Flat do dia 15 ao dia 18 de marco para 4 pessoas", "Roberto")
assert "R$" in resp
log("[OK] Farol Barra baixa temporada")

# --- Test 2 ---
resp = agent.respond("Smart Convencoes dia 10 a 13 de maio, 2 pessoas")
assert "R$" in resp
log("[OK] Smart Convencoes")

# --- Test 3 ---
resp = agent.respond("Ondina Apart Hotel dia 20 a 25 de janeiro, 2 hospedes")
assert "Alta Temporada" in resp
log("[OK] Ondina alta temporada")

# --- Test 4 ---
resp = agent.respond("The Plaza 407 05/06/2026 a 08/06/2026, 3 hospedes")
assert "R$" in resp
log("[OK] The Plaza")

# --- Test 5 ---
resp = agent.respond("Smart Convencoes dia 1 a 5 de abril, 5 pessoas")
assert "capacidade" in resp
log("[OK] Capacidade excedida")

# --- Test 6 ---
resp = agent.respond("Quero alugar o The Plaza")
assert "check-in" in resp or "check-out" in resp
log("[OK] Info incompleta")

# --- Test 7 ---
prop = agent.pm.get_property("farol_barra_flat_214")
engine = __import__("pricing").PricingEngine(prop, agent.calendar)
assert engine.calculate_daily_rate(date(2026, 3, 16)) == 249
assert engine.calculate_daily_rate(date(2026, 3, 20)) == 298.8
assert engine.calculate_daily_rate(date(2026, 3, 21)) == 311.25
assert engine.calculate_daily_rate(date(2026, 3, 22)) == 298.8
log("[OK] Precificacao dia da semana")

# --- Test 8: API ---
client = TestClient(app)
r = client.get("/health")
assert r.status_code == 200
r = client.post("/chat", json={"message": "Farol Barra Flat 15 a 18 marco 2 pessoas", "guest_id": "test_api"})
assert r.status_code == 200
assert "R$" in r.json()["response"]
r = client.get("/webchat")
assert r.status_code == 200
assert "Agente" in r.text
r = client.get("/imoveis")
assert r.status_code == 200
assert "farol_barra_flat_214" in r.json()
r = client.post("/cotacao", json={"property_key": "farol_barra_flat_214", "checkin": "15/03/2026", "checkout": "18/03/2026", "guests": 2})
assert r.status_code == 200
assert r.json()["disponivel"] == True
log("[OK] API endpoints")

# --- Summary ---
print("=" * 40)
print("RESULTADO DOS TESTES:")
for r in results:
    print(f"  {r}")
print(f"\n{len(results)}/{len(results)} testes passaram!")
print("=" * 40)
