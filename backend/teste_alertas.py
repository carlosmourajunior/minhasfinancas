#!/usr/bin/env python3
"""
Script para testar os alertas de cartão de crédito
"""

from datetime import date
from dateutil.relativedelta import relativedelta
from calendar import monthrange

def calcular_ciclo_fatura(referencia: date, dia_fechamento: int, dia_vencimento: int):
    """
    Calcula o ciclo de fatura do cartão de crédito.
    
    Regras:
    - Se dia_vencimento > dia_fechamento: vencimento no mesmo mês do fechamento
    - Se dia_vencimento <= dia_fechamento: vencimento no mês seguinte ao fechamento
    
    Exemplo: fechamento dia 25, vencimento dia 1
    - Fechamento 25/09 -> Vencimento 01/10
    """
    ano = referencia.year
    mes = referencia.month

    # Fechamento no mês da referência
    fechamento_no_mes_ref = date(ano, mes, min(dia_fechamento, monthrange(ano, mes)[1]))

    # Último fechamento que já ocorreu (<= hoje)
    if referencia >= fechamento_no_mes_ref:
        fechamento_recente = fechamento_no_mes_ref
    else:
        # Fechamento é do mês anterior
        if mes == 1:
            ano_prev = ano - 1
            mes_prev = 12
        else:
            ano_prev = ano
            mes_prev = mes - 1
        fechamento_recente = date(ano_prev, mes_prev, min(dia_fechamento, monthrange(ano_prev, mes_prev)[1]))

    # Fechamento anterior ao recente (para delimitar o início do período)
    if fechamento_recente.month == 1:
        ano_prev_prev = fechamento_recente.year - 1
        mes_prev_prev = 12
    else:
        ano_prev_prev = fechamento_recente.year
        mes_prev_prev = fechamento_recente.month - 1
    fechamento_anterior = date(ano_prev_prev, mes_prev_prev, min(dia_fechamento, monthrange(ano_prev_prev, mes_prev_prev)[1]))

    # Período fechado: dia seguinte ao fechamento anterior até o último fechamento
    periodo_inicio = fechamento_anterior + relativedelta(days=1)
    periodo_fim = fechamento_recente

    # Vencimento baseado no fechamento recente
    # REGRA CORRIGIDA: Se dia_vencimento <= dia_fechamento, vencimento é no mês seguinte
    if dia_vencimento > dia_fechamento:
        # Vencimento no mesmo mês do fechamento
        venc_ano = fechamento_recente.year
        venc_mes = fechamento_recente.month
    else:
        # Vencimento no mês seguinte ao fechamento
        prox = fechamento_recente + relativedelta(months=1)
        venc_ano = prox.year
        venc_mes = prox.month
    
    vencimento = date(venc_ano, venc_mes, min(dia_vencimento, monthrange(venc_ano, venc_mes)[1]))

    return periodo_inicio, periodo_fim, fechamento_recente, vencimento

def deve_mostrar_alerta(hoje_data, fechamento, vencimento):
    """
    Verifica se deve mostrar alerta baseado na nova lógica
    """
    limite_alerta = vencimento + relativedelta(months=1)
    return fechamento <= hoje_data <= limite_alerta

def testar_cenarios():
    print("=== TESTE DE ALERTAS DE CARTÃO ===\n")
    
    # Cenário 1: Cartão fecha dia 25, vence dia 1
    print("Cenário 1: Cartão fecha dia 25, vence dia 1º")
    print("-" * 50)
    
    cenarios_data = [
        date(2025, 9, 22),  # Antes do fechamento de 25/09
        date(2025, 9, 24),  # Véspera do fechamento
        date(2025, 9, 25),  # Dia do fechamento
        date(2025, 9, 26),  # Após fechamento (deve alertar)
        date(2025, 10, 1),  # Dia do vencimento (deve alertar)
        date(2025, 10, 5),  # Após vencimento (deve alertar)
        date(2025, 10, 15), # Bem após vencimento (deve alertar)
        date(2025, 11, 5),  # Muito tempo após (não deve alertar)
    ]
    
    for hoje in cenarios_data:
        inicio, fim, fechamento, vencimento = calcular_ciclo_fatura(hoje, 25, 1)
        deve_alertar = deve_mostrar_alerta(hoje, fechamento, vencimento)
        
        print(f"Hoje: {hoje.strftime('%d/%m/%Y')}")
        print(f"  Período fatura: {inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}")
        print(f"  Fechamento: {fechamento.strftime('%d/%m/%Y')}")
        print(f"  Vencimento: {vencimento.strftime('%d/%m/%Y')}")
        print(f"  Deve alertar: {'✅ SIM' if deve_alertar else '❌ NÃO'}")
        print()
    
    # Cenário 2: Cartão fecha dia 5, vence dia 20 (mesmo mês)
    print("\nCenário 2: Cartão fecha dia 5, vence dia 20 (mesmo mês)")
    print("-" * 50)
    
    cenarios_data_2 = [
        date(2025, 9, 3),   # Antes do fechamento
        date(2025, 9, 5),   # Dia do fechamento
        date(2025, 9, 6),   # Após fechamento (deve alertar)
        date(2025, 9, 20),  # Dia do vencimento (deve alertar)
        date(2025, 10, 15), # Após vencimento (deve alertar até 20/10)
        date(2025, 10, 25), # Muito tempo após (não deve alertar)
    ]
    
    for hoje in cenarios_data_2:
        inicio, fim, fechamento, vencimento = calcular_ciclo_fatura(hoje, 5, 20)
        deve_alertar = deve_mostrar_alerta(hoje, fechamento, vencimento)
        
        print(f"Hoje: {hoje.strftime('%d/%m/%Y')}")
        print(f"  Período fatura: {inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}")
        print(f"  Fechamento: {fechamento.strftime('%d/%m/%Y')}")
        print(f"  Vencimento: {vencimento.strftime('%d/%m/%Y')}")
        print(f"  Deve alertar: {'✅ SIM' if deve_alertar else '❌ NÃO'}")
        print()

if __name__ == "__main__":
    testar_cenarios()