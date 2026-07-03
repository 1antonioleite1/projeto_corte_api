"""
test_solver.py
Testes unitários da modelagem matemática (src/solver.py), cobrindo casos
simples e instâncias clássicas com desperdício conhecido.
"""

import pytest

from src.solver import ItemEntrada, resolver_corte


def test_uma_barra_exata_sem_desperdicio():
    """Um único item que preenche exatamente a barra: 1 barra, 0 de sobra."""
    itens = [ItemEntrada(id="A", comprimento=3000, quantidade=1)]
    resultado = resolver_corte(comprimento_padrao=3000, itens=itens, time_limit_segundos=10)

    assert resultado.status_solver in ("OPTIMAL", "FEASIBLE")
    assert resultado.barras_utilizadas == 1
    assert resultado.desperdicio_total_mm == pytest.approx(0.0)


def test_dois_itens_cabem_em_uma_barra():
    """Dois itens que juntos cabem em uma única barra padrão."""
    itens = [
        ItemEntrada(id="A", comprimento=1000, quantidade=1),
        ItemEntrada(id="B", comprimento=1500, quantidade=1),
    ]
    resultado = resolver_corte(comprimento_padrao=3000, itens=itens, time_limit_segundos=10)

    assert resultado.barras_utilizadas == 1
    assert resultado.desperdicio_total_mm == pytest.approx(500.0)


def test_demanda_maior_exige_multiplas_barras():
    """Instância clássica: item de 1100 em barra de 3000, 7 unidades -> 3 barras."""
    itens = [ItemEntrada(id="A", comprimento=1100, quantidade=7)]
    resultado = resolver_corte(comprimento_padrao=3000, itens=itens, time_limit_segundos=15)

    # floor(3000/1100) = 2 itens por barra -> ceil(7/2) = 4 barras no mínimo
    assert resultado.status_solver in ("OPTIMAL", "FEASIBLE")
    assert resultado.barras_utilizadas == 4


def test_toda_demanda_e_atendida():
    """A soma das quantidades cortadas deve satisfazer (>=) a demanda de cada item."""
    itens = [
        ItemEntrada(id="item_A", comprimento=1150, quantidade=3),
        ItemEntrada(id="item_B", comprimento=800, quantidade=4),
        ItemEntrada(id="item_C", comprimento=450, quantidade=5),
    ]
    resultado = resolver_corte(comprimento_padrao=3000, itens=itens, time_limit_segundos=20)

    totais = {"item_A": 0, "item_B": 0, "item_C": 0}
    for barra in resultado.plano_corte:
        for item_cortado in barra.itens_cortados:
            totais[item_cortado["item_id"]] += item_cortado["quantidade"]

    assert totais["item_A"] >= 3
    assert totais["item_B"] >= 4
    assert totais["item_C"] >= 5


def test_nenhuma_barra_excede_comprimento_padrao():
    """Nenhuma barra do plano de corte pode ultrapassar o comprimento útil L."""
    itens = [
        ItemEntrada(id="item_A", comprimento=1150, quantidade=3),
        ItemEntrada(id="item_B", comprimento=800, quantidade=4),
        ItemEntrada(id="item_C", comprimento=450, quantidade=5),
    ]
    L = 3000
    resultado = resolver_corte(comprimento_padrao=L, itens=itens, time_limit_segundos=20)

    for barra in resultado.plano_corte:
        assert barra.comprimento_utilizado <= L
        assert barra.comprimento_utilizado + barra.sobra == pytest.approx(L)


def test_multiplos_itens_identicos_por_barra():
    """Itens pequenos o suficiente para caber múltiplas vezes na mesma barra."""
    itens = [ItemEntrada(id="A", comprimento=500, quantidade=6)]
    resultado = resolver_corte(comprimento_padrao=3000, itens=itens, time_limit_segundos=10)

    # 6 itens de 500 cabem exatamente em 1 barra de 3000
    assert resultado.barras_utilizadas == 1
    assert resultado.desperdicio_total_mm == pytest.approx(0.0)


def test_item_com_quantidade_unica_e_barra_grande():
    """Item único muito menor que a barra: 1 barra, desperdício conhecido."""
    itens = [ItemEntrada(id="A", comprimento=250, quantidade=1)]
    resultado = resolver_corte(comprimento_padrao=6000, itens=itens, time_limit_segundos=10)

    assert resultado.barras_utilizadas == 1
    assert resultado.desperdicio_total_mm == pytest.approx(5750.0)


def test_status_optimal_ou_feasible_para_instancia_pequena():
    """Instâncias pequenas devem ser resolvidas com status ótimo dentro do tempo limite."""
    itens = [ItemEntrada(id="A", comprimento=2000, quantidade=2)]
    resultado = resolver_corte(comprimento_padrao=3000, itens=itens, time_limit_segundos=10)

    assert resultado.status_solver == "OPTIMAL"
    assert resultado.barras_utilizadas == 2


def test_numero_de_barras_no_plano_bate_com_barras_utilizadas():
    """O tamanho da lista plano_corte deve ser igual ao total de barras_utilizadas."""
    itens = [
        ItemEntrada(id="A", comprimento=1150, quantidade=3),
        ItemEntrada(id="B", comprimento=800, quantidade=4),
    ]
    resultado = resolver_corte(comprimento_padrao=3000, itens=itens, time_limit_segundos=15)

    assert len(resultado.plano_corte) == resultado.barras_utilizadas


def test_respeita_tempo_limite_customizado():
    """O solver deve retornar dentro de uma margem razoável do tempo limite informado."""
    itens = [ItemEntrada(id="A", comprimento=333, quantidade=20)]
    resultado = resolver_corte(comprimento_padrao=1000, itens=itens, time_limit_segundos=5)

    assert resultado.tempo_execucao_segundos <= 5 + 2  # margem de segurança
    assert resultado.status_solver in ("OPTIMAL", "FEASIBLE")
