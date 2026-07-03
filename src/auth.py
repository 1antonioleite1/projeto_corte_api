"""
auth.py
Lógica de controle de acesso da API.

Opção escolhida: API Key (Opção A do enunciado).
A chave é enviada pelo cliente no cabeçalho HTTP `X-API-Key` e comparada
contra o segredo armazenado em `.env`. Requisições sem a chave correta
recebem HTTP 403 (Forbidden).
"""

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

from src.config import get_settings

settings = get_settings()

_api_key_header = APIKeyHeader(name=settings.API_KEY_NAME, auto_error=False)


async def verificar_api_key(api_key: str = Security(_api_key_header)) -> str:
    """
    Dependência do FastAPI que valida o cabeçalho X-API-Key.

    Retorna a própria chave se válida, ou levanta HTTPException 403 caso
    a chave esteja ausente ou incorreta.
    """
    if api_key is None or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: chave de API (X-API-Key) ausente ou inválida.",
        )
    return api_key
