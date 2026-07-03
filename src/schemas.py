"""
schemas.py
Modelos Pydantic responsáveis pela validação dos dados de entrada (requisição)
e pela estruturação dos dados de saída (resposta) da API.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# ENTRADA
# ---------------------------------------------------------------------------

class ItemDemanda(BaseModel):
    """Representa um item (subpeça) a ser cortado a partir da barra padrão."""

    id: str = Field(
        ...,
        min_length=1,
        description="Identificador único do item.",
        examples=["item_A"],
    )
    comprimento: float = Field(
        ...,
        gt=0,
        description="Comprimento necessário do item (li). Deve ser estritamente positivo.",
        examples=[1150],
    )
    quantidade: int = Field(
        ...,
        gt=0,
        description="Demanda total exigida do item (di). Deve ser estritamente positiva.",
        examples=[3],
    )

    model_config = {
        "json_schema_extra": {
            "example": {"id": "item_A", "comprimento": 1150, "quantidade": 3}
        }
    }


class OtimizacaoRequest(BaseModel):
    """Corpo da requisição do endpoint POST /otimizar."""

    comprimento_padrao: float = Field(
        ...,
        gt=0,
        description="Comprimento útil (L) de cada barra padrão em estoque.",
        examples=[3000],
    )
    itens: List[ItemDemanda] = Field(
        ...,
        min_length=1,
        description="Lista de itens desejados com seus respectivos comprimentos e quantidades.",
    )
    time_limit: Optional[float] = Field(
        default=None,
        gt=0,
        description=(
            "Tempo limite (em segundos) de processamento do solver. "
            "Opcional; se omitido, usa o valor padrão da API (60s), "
            "limitado a um máximo de 120s."
        ),
        examples=[60],
    )

    @model_validator(mode="after")
    def validar_itens_menores_que_barra(self) -> "OtimizacaoRequest":
        """Garante que nenhum item tenha comprimento maior que a barra padrão."""
        for item in self.itens:
            if item.comprimento > self.comprimento_padrao:
                raise ValueError(
                    f"O item '{item.id}' possui comprimento ({item.comprimento}) "
                    f"maior que o comprimento padrão da barra ({self.comprimento_padrao})."
                )

        ids = [item.id for item in self.itens]
        if len(ids) != len(set(ids)):
            raise ValueError("Os ids dos itens devem ser únicos dentro da requisição.")

        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "comprimento_padrao": 3000,
                "itens": [
                    {"id": "item_A", "comprimento": 1150, "quantidade": 3},
                    {"id": "item_B", "comprimento": 800, "quantidade": 4},
                    {"id": "item_C", "comprimento": 450, "quantidade": 5},
                ],
                "time_limit": 60,
            }
        }
    }


# ---------------------------------------------------------------------------
# SAÍDA
# ---------------------------------------------------------------------------

class ItemCortado(BaseModel):
    """Quantidade de um item específico cortado em uma barra."""

    item_id: str
    quantidade: int


class BarraPlano(BaseModel):
    """Plano de corte detalhado de uma única barra utilizada."""

    model_config = ConfigDict(from_attributes=True)

    barra_id: int
    itens_cortados: List[ItemCortado]
    comprimento_utilizado: float
    sobra: float


class OtimizacaoResponse(BaseModel):
    """Corpo da resposta do endpoint POST /otimizar."""

    status_solver: str = Field(
        ..., description="Status retornado pelo solver (ex: OPTIMAL, FEASIBLE, INFEASIBLE)."
    )
    tempo_execucao_segundos: float
    barras_utilizadas: int
    desperdicio_total_mm: float
    plano_corte: List[BarraPlano]

    model_config = {
        "json_schema_extra": {
            "example": {
                "status_solver": "OPTIMAL",
                "tempo_execucao_segundos": 0.045,
                "barras_utilizadas": 4,
                "desperdicio_total_mm": 3100,
                "plano_corte": [
                    {
                        "barra_id": 1,
                        "itens_cortados": [{"item_id": "item_A", "quantidade": 2}],
                        "comprimento_utilizado": 2300,
                        "sobra": 700,
                    }
                ],
            }
        }
    }


class HealthResponse(BaseModel):
    """Corpo da resposta do endpoint GET /health."""

    status: str = "ok"
    app_name: str
    version: str


class ErrorResponse(BaseModel):
    """Formato padronizado de erro retornado pela API (traceback nunca exposto)."""

    detail: str
