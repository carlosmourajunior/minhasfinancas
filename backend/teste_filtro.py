#!/usr/bin/env python3
"""
Script para testar o filtro de corte de faturas
"""

import sys
import os
from datetime import date

# Adicionar o diretório do projeto ao path
sys.path.insert(0, '/app')

# Importar as dependências do projeto
from main import SessionLocal, calcular_ciclo_fatura, Cartao, Fatura
from dateutil.relativedelta import relativedelta

def testar_filtro_corte():
    """Testa o filtro de corte de setembro/2025"""
    print("=== TESTE DO FILTRO DE CORTE ===")
    print(f"Data de hoje: {date.today()}")
    print("Data de corte: 01/09/2025")
    print()
    
    db = SessionLocal()
    try:
        # Verificar faturas no banco
        todas_faturas = db.query(Fatura).all()
        print(f"Total de faturas no banco: {len(todas_faturas)}")
        
        faturas_validas = db.query(Fatura).filter(Fatura.data_vencimento >= date(2025, 9, 1)).all()
        print(f"Faturas válidas (>= setembro/2025): {len(faturas_validas)}")
        
        faturas_antigas = db.query(Fatura).filter(Fatura.data_vencimento < date(2025, 9, 1)).all()
        print(f"Faturas antigas (< setembro/2025): {len(faturas_antigas)}")
        
        print("\n--- FATURAS VÁLIDAS ---")
        for fatura in faturas_validas:
            cartao = db.query(Cartao).filter(Cartao.id == fatura.cartao_id).first()
            cartao_nome = cartao.nome if cartao else f"ID {fatura.cartao_id}"
            print(f"  {cartao_nome}: Vence {fatura.data_vencimento}, Status: {fatura.status}")
        
        if faturas_antigas:
            print("\n--- FATURAS ANTIGAS (DEVEM SER IGNORADAS) ---")
            for fatura in faturas_antigas:
                cartao = db.query(Cartao).filter(Cartao.id == fatura.cartao_id).first()
                cartao_nome = cartao.nome if cartao else f"ID {fatura.cartao_id}"
                print(f"  ❌ {cartao_nome}: Vence {fatura.data_vencimento}, Status: {fatura.status}")
        
        # Testar lógica de alertas com filtro
        print("\n--- TESTE DA LÓGICA COM FILTRO ---")
        hoje_data = date.today()
        data_corte_vencimento = date(2025, 9, 1)
        cartoes = db.query(Cartao).filter(Cartao.ativo == True).all()
        faturas_devem_alertar = []
        
        for cartao in cartoes:
            if not cartao.dia_fechamento or not cartao.dia_vencimento:
                continue
                
            print(f"\nCartão: {cartao.nome}")
            
            for meses_atras in range(0, 4):
                data_referencia = hoje_data - relativedelta(months=meses_atras)
                inicio, fim, fechamento, vencimento = calcular_ciclo_fatura(
                    data_referencia, cartao.dia_fechamento, cartao.dia_vencimento
                )
                
                # Aplicar filtro de corte
                if vencimento < data_corte_vencimento:
                    print(f"  ❌ IGNORADO: Vencimento {vencimento} < {data_corte_vencimento}")
                    continue
                
                # Verificar se deve alertar
                limite_alerta = vencimento + relativedelta(months=1)
                deve_alertar = fechamento <= hoje_data <= limite_alerta
                
                if deve_alertar:
                    fatura = db.query(Fatura).filter(
                        Fatura.cartao_id == cartao.id,
                        Fatura.periodo_inicio == inicio,
                        Fatura.periodo_fim == fim
                    ).first()
                    
                    if fatura and fatura.status != "confirmada":
                        print(f"  ✅ DEVE ALERTAR: Vence {vencimento}, Status: {fatura.status}")
                        faturas_devem_alertar.append(fatura)
                    elif not fatura:
                        print(f"  🆕 CRIAR FATURA: Vence {vencimento}")
        
        print(f"\n=== RESULTADO FINAL ===")
        print(f"Faturas que devem aparecer no alerta: {len(faturas_devem_alertar)}")
        
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    testar_filtro_corte()