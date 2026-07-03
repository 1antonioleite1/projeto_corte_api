"""
config.py
Carregamento de configurações e variáveis de ambiente (.env) para a aplicação.
"""

import os
from functools import lru_cache

from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env, se existir
load_dotenv()


class Settings:
    """Configurações globais da aplicação, lidas do ambiente (.env)."""

    # --- Metadados da API ---
    APP_NAME: str = os.getenv("APP_NAME", "API de Otimização - Corte Unidimensional")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")

    # --- Segurança: API Key ---
    API_KEY: str = os.getenv("API_KEY", "changeme-super-secret-key")
    API_KEY_NAME: str = "X-API-Key"

    # --- Solver / confiabilidade ---
    # Tempo limite padrão (segundos) aplicado ao solver quando o cliente não informa.
    DEFAULT_TIME_LIMIT: float = float(os.getenv("DEFAULT_TIME_LIMIT", "60"))
    # Tempo limite máximo que a API aceita, mesmo que o cliente peça mais.
    MAX_TIME_LIMIT: float = float(os.getenv("MAX_TIME_LIMIT", "120"))

    # --- Ambiente ---
    ENV: str = os.getenv("ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"


@lru_cache
def get_settings() -> Settings:
    """Retorna uma instância cacheada das configurações (evita reler o .env)."""
    return Settings()
