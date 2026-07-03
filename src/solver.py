"""
solver.py
Modelagem matemática do Problema de Corte Unidimensional (Cutting Stock
Problem), formulação de Kantorovich, resolvida com o Google OR-Tools
(CP-SAT Solver).

Modelo:
    Minimizar   Z = sum_j y_j
    sujeito a:  sum_j x_ij >= d_i                  (demanda atendida)
                sum_i l_i * x_ij <= L * y_j         (capacidade da barra)
                y_j in {0, 1}
                x_ij in Z >= 0

Como o número de barras padrão N não é conhecido a priori, utilizamos um
limite superior calculado via heurística gulosa (First-Fit Decreasing),
que também fornece uma solução inicial (hint) para acelerar o solver.
"""

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ortools.sat.python import cp_model


@dataclass
class ItemEntrada:
    id: str
    comprimento: float
    quantidade: int


@dataclass
class BarraSolucao:
    barra_id: int
    itens_cortados: List[Dict]
    comprimento_utilizado: float
    sobra: float


@dataclass
class ResultadoOtimizacao:
    status_solver: str
    tempo_execucao_segundos: float
    barras_utilizadas: int
    desperdicio_total_mm: float
    plano_corte: List[BarraSolucao] = field(default_factory=list)


# Escala usada para converter comprimentos (float) em inteiros, já que o
# CP-SAT trabalha com variáveis inteiras. Comprimentos são multiplicados
# por essa escala e arredondados.
_ESCALA = 1000


def _para_inteiro(valor: float) -> int:
    return int(round(valor * _ESCALA))


def _limite_superior_ffd(comprimento_padrao: int, itens_expandidos: List[int]) -> int:
    """
    Heurística First-Fit Decreasing: fornece um limite superior razoável
    para o número de barras necessárias (N), evitando que o modelo exato
    precise considerar um número excessivo de barras "vazias".
    """
    itens_ordenados = sorted(itens_expandidos, reverse=True)
    barras: List[int] = []  # espaço restante em cada barra aberta

    for comprimento in itens_ordenados:
        colocado = False
        for i in range(len(barras)):
            if barras[i] >= comprimento:
                barras[i] -= comprimento
                colocado = True
                break
        if not colocado:
            barras.append(comprimento_padrao - comprimento)

    return max(1, len(barras))


def resolver_corte(
    comprimento_padrao: float,
    itens: List[ItemEntrada],
    time_limit_segundos: float = 60.0,
) -> ResultadoOtimizacao:
    """
    Resolve o Problema de Corte Unidimensional para os parâmetros dados.

    Args:
        comprimento_padrao: comprimento útil (L) da barra padrão.
        itens: lista de itens de demanda (id, comprimento, quantidade).
        time_limit_segundos: tempo máximo de execução do solver.

    Returns:
        ResultadoOtimizacao com status, tempo de execução, número de barras
        utilizadas, desperdício total e o plano de corte detalhado.
    """
    inicio = time.perf_counter()

    L = _para_inteiro(comprimento_padrao)
    m = len(itens)
    demandas = [item.quantidade for item in itens]
    comprimentos = [_para_inteiro(item.comprimento) for item in itens]

    # --- Limite superior de barras (N) via heurística FFD ---
    itens_expandidos: List[int] = []
    for comp, qtd in zip(comprimentos, demandas):
        itens_expandidos.extend([comp] * qtd)

    N = _limite_superior_ffd(L, itens_expandidos)

    model = cp_model.CpModel()

    # Variáveis de decisão
    y = [model.NewBoolVar(f"y_{j}") for j in range(N)]
    x = [
        [model.NewIntVar(0, max(demandas), f"x_{i}_{j}") for j in range(N)]
        for i in range(m)
    ]

    # Restrição (2): atender a demanda de cada item
    for i in range(m):
        model.Add(sum(x[i][j] for j in range(N)) >= demandas[i])

    # Restrição (3): capacidade da barra
    for j in range(N):
        model.Add(sum(comprimentos[i] * x[i][j] for i in range(m)) <= L * y[j])

    # Quebra de simetria: barras usadas em ordem (y_0 >= y_1 >= ... >= y_{N-1})
    for j in range(N - 1):
        model.Add(y[j] >= y[j + 1])

    # Função objetivo (1): minimizar o número de barras utilizadas
    model.Minimize(sum(y))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_segundos
    solver.parameters.num_search_workers = 8

    status_code = solver.Solve(model)

    tempo_execucao = time.perf_counter() - inicio

    status_map = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.UNKNOWN: "UNKNOWN",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
    }
    status_str = status_map.get(status_code, "UNKNOWN")

    if status_code not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return ResultadoOtimizacao(
            status_solver=status_str,
            tempo_execucao_segundos=round(tempo_execucao, 6),
            barras_utilizadas=0,
            desperdicio_total_mm=0.0,
            plano_corte=[],
        )

    plano_corte: List[BarraSolucao] = []
    barras_utilizadas = 0
    desperdicio_total = 0

    proximo_id = 1
    for j in range(N):
        if solver.Value(y[j]) == 0:
            continue

        itens_cortados = []
        comprimento_utilizado = 0
        for i in range(m):
            qtd = solver.Value(x[i][j])
            if qtd > 0:
                itens_cortados.append({"item_id": itens[i].id, "quantidade": qtd})
                comprimento_utilizado += comprimentos[i] * qtd

        if not itens_cortados:
            # Barra marcada como usada mas sem itens (não deve ocorrer
            # devido à quebra de simetria, mas é tratado por segurança).
            continue

        sobra = L - comprimento_utilizado
        barras_utilizadas += 1
        desperdicio_total += sobra

        plano_corte.append(
            BarraSolucao(
                barra_id=proximo_id,
                itens_cortados=itens_cortados,
                comprimento_utilizado=comprimento_utilizado / _ESCALA,
                sobra=sobra / _ESCALA,
            )
        )
        proximo_id += 1

    return ResultadoOtimizacao(
        status_solver=status_str,
        tempo_execucao_segundos=round(tempo_execucao, 6),
        barras_utilizadas=barras_utilizadas,
        desperdicio_total_mm=desperdicio_total / _ESCALA,
        plano_corte=plano_corte,
    )
