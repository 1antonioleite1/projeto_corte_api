"""
test_api.py
Testes de integração das rotas da API (FastAPI TestClient), cobrindo:
- validações Pydantic inválidas (422)
- bloqueios de segurança / autenticação (403)
- limite de tempo do solver
- respostas de sucesso (200)
"""

import pytest
from fastapi.testclient import TestClient

from src.api import app
from src.config import get_settings

settings = get_settings()
client = TestClient(app)

CHAVE_VALIDA = settings.API_KEY
CHAVE_INVALIDA = "chave-incorreta-qualquer"

PAYLOAD_VALIDO = {
    "comprimento_padrao": 3000,
    "itens": [
        {"id": "item_A", "comprimento": 1150, "quantidade": 3},
        {"id": "item_B", "comprimento": 800, "quantidade": 4},
        {"id": "item_C", "comprimento": 450, "quantidade": 5},
    ],
}


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

def test_health_endpoint_esta_online():
    resposta = client.get("/health")
    assert resposta.status_code == 200
    body = resposta.json()
    assert body["status"] == "ok"
    assert "app_name" in body


# ---------------------------------------------------------------------------
# Segurança / autenticação
# ---------------------------------------------------------------------------

def test_otimizar_sem_api_key_retorna_403():
    resposta = client.post("/otimizar", json=PAYLOAD_VALIDO)
    assert resposta.status_code == 403


def test_otimizar_com_api_key_invalida_retorna_403():
    resposta = client.post(
        "/otimizar",
        json=PAYLOAD_VALIDO,
        headers={"X-API-Key": CHAVE_INVALIDA},
    )
    assert resposta.status_code == 403


def test_otimizar_com_api_key_valida_retorna_200():
    resposta = client.post(
        "/otimizar",
        json=PAYLOAD_VALIDO,
        headers={"X-API-Key": CHAVE_VALIDA},
    )
    assert resposta.status_code == 200
    body = resposta.json()
    assert body["status_solver"] in ("OPTIMAL", "FEASIBLE")
    assert body["barras_utilizadas"] > 0
    assert "plano_corte" in body


# ---------------------------------------------------------------------------
# Validações Pydantic (422)
# ---------------------------------------------------------------------------

def test_comprimento_padrao_negativo_retorna_422():
    payload = {**PAYLOAD_VALIDO, "comprimento_padrao": -100}
    resposta = client.post("/otimizar", json=payload, headers={"X-API-Key": CHAVE_VALIDA})
    assert resposta.status_code == 422


def test_item_maior_que_barra_padrao_retorna_422():
    payload = {
        "comprimento_padrao": 1000,
        "itens": [{"id": "item_X", "comprimento": 1500, "quantidade": 1}],
    }
    resposta = client.post("/otimizar", json=payload, headers={"X-API-Key": CHAVE_VALIDA})
    assert resposta.status_code == 422


def test_quantidade_zero_retorna_422():
    payload = {
        "comprimento_padrao": 3000,
        "itens": [{"id": "item_X", "comprimento": 500, "quantidade": 0}],
    }
    resposta = client.post("/otimizar", json=payload, headers={"X-API-Key": CHAVE_VALIDA})
    assert resposta.status_code == 422


def test_lista_de_itens_vazia_retorna_422():
    payload = {"comprimento_padrao": 3000, "itens": []}
    resposta = client.post("/otimizar", json=payload, headers={"X-API-Key": CHAVE_VALIDA})
    assert resposta.status_code == 422


def test_tipagem_invalida_retorna_422():
    payload = {
        "comprimento_padrao": "nao-e-um-numero",
        "itens": [{"id": "item_X", "comprimento": 500, "quantidade": 1}],
    }
    resposta = client.post("/otimizar", json=payload, headers={"X-API-Key": CHAVE_VALIDA})
    assert resposta.status_code == 422


def test_ids_de_itens_duplicados_retorna_422():
    payload = {
        "comprimento_padrao": 3000,
        "itens": [
            {"id": "item_A", "comprimento": 500, "quantidade": 1},
            {"id": "item_A", "comprimento": 700, "quantidade": 2},
        ],
    }
    resposta = client.post("/otimizar", json=payload, headers={"X-API-Key": CHAVE_VALIDA})
    assert resposta.status_code == 422


# ---------------------------------------------------------------------------
# Time limit
# ---------------------------------------------------------------------------

def test_time_limit_customizado_e_aceito():
    payload = {**PAYLOAD_VALIDO, "time_limit": 5}
    resposta = client.post("/otimizar", json=payload, headers={"X-API-Key": CHAVE_VALIDA})
    assert resposta.status_code == 200
    assert resposta.json()["tempo_execucao_segundos"] <= 5 + 2


def test_time_limit_negativo_retorna_422():
    payload = {**PAYLOAD_VALIDO, "time_limit": -5}
    resposta = client.post("/otimizar", json=payload, headers={"X-API-Key": CHAVE_VALIDA})
    assert resposta.status_code == 422


def test_time_limit_acima_do_maximo_e_limitado_internamente():
    """Mesmo pedindo um tempo muito alto, a API deve limitar ao MAX_TIME_LIMIT."""
    payload = {
        "comprimento_padrao": 3000,
        "itens": [{"id": "item_A", "comprimento": 2000, "quantidade": 2}],
        "time_limit": 10_000,
    }
    resposta = client.post("/otimizar", json=payload, headers={"X-API-Key": CHAVE_VALIDA})
    assert resposta.status_code == 200
    assert resposta.json()["tempo_execucao_segundos"] <= settings.MAX_TIME_LIMIT + 5
