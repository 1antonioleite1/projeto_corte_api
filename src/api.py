"""
api.py
Configuração da aplicação FastAPI e definição das rotas (endpoints) da API
de Otimização para o Problema de Corte Unidimensional.
"""

import logging

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.auth import verificar_api_key
from src.config import get_settings
from src.schemas import (
    ErrorResponse,
    HealthResponse,
    OtimizacaoRequest,
    OtimizacaoResponse,
)
from src.solver import ItemEntrada, resolver_corte

settings = get_settings()

logger = logging.getLogger("corte_api")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "API RESTful para resolução do Problema de Corte Unidimensional "
        "(One-Dimensional Cutting Stock Problem), utilizando a formulação "
        "de Kantorovich resolvida com o Google OR-Tools (CP-SAT).\n\n"
        "Autenticação via cabeçalho `X-API-Key`."
    ),
    contact={"name": "Laboratório de Otimização — UFC"},
)


# ---------------------------------------------------------------------------
# Tratamento de exceções: nunca expor traceback ao cliente
# ---------------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Padroniza erros de validação do Pydantic como HTTP 422."""
    mensagens = "; ".join(
        f"{'.'.join(str(p) for p in erro['loc'])}: {erro['msg']}" for erro in exc.errors()
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(detail=f"Erro de validação: {mensagens}").model_dump(),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Captura qualquer exceção não tratada, ocultando o traceback do cliente."""
    logger.exception("Erro interno não tratado: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(detail="Erro interno no servidor.").model_dump(),
    )


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Monitoramento"],
    summary="Verifica se a API está online",
    description="Endpoint público (sem autenticação) para checagem de disponibilidade do serviço.",
)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", app_name=settings.APP_NAME, version=settings.APP_VERSION)


@app.post(
    "/otimizar",
    response_model=OtimizacaoResponse,
    tags=["Otimização"],
    summary="Resolve o Problema de Corte Unidimensional",
    description=(
        "Recebe o comprimento da barra padrão e a lista de itens demandados "
        "e retorna o plano de corte ótimo (ou a melhor solução encontrada "
        "dentro do tempo limite), minimizando o número de barras utilizadas."
    ),
    responses={
        403: {"model": ErrorResponse, "description": "Chave de API ausente ou inválida."},
        422: {"model": ErrorResponse, "description": "Parâmetros de entrada inválidos."},
    },
    dependencies=[Depends(verificar_api_key)],
)
async def otimizar(payload: OtimizacaoRequest) -> OtimizacaoResponse:
    time_limit = payload.time_limit or settings.DEFAULT_TIME_LIMIT
    time_limit = min(time_limit, settings.MAX_TIME_LIMIT)

    itens = [
        ItemEntrada(id=item.id, comprimento=item.comprimento, quantidade=item.quantidade)
        for item in payload.itens
    ]

    resultado = resolver_corte(
        comprimento_padrao=payload.comprimento_padrao,
        itens=itens,
        time_limit_segundos=time_limit,
    )

    return OtimizacaoResponse(
        status_solver=resultado.status_solver,
        tempo_execucao_segundos=resultado.tempo_execucao_segundos,
        barras_utilizadas=resultado.barras_utilizadas,
        desperdicio_total_mm=resultado.desperdicio_total_mm,
        plano_corte=resultado.plano_corte,
    )
