#!/usr/bin/env python3
"""
Script para testar a API de faturas pendentes diretamente no container
"""

import sys
import os
import json
from datetime import date

# Adicionar o diretório do projeto ao path
sys.path.insert(0, '/app')

# Importar as dependências do projeto
from main import SessionLocal, calcular_ciclo_fatura, Cartao, Fatura
from dateutil.relativedelta import relativedelta

def testar_faturas_pendentes():
    """Testa a lógica de faturas pendentes"""
    print("=== TESTE DE FATURAS PENDENTES ===")
    print(f"Data de hoje: {date.today()}")
    print()
    
    db = SessionLocal()
    try:
        # Buscar todos os cartões ativos
        cartoes = db.query(Cartao).filter(Cartao.ativo == True).all()
        print(f"Cartões ativos encontrados: {len(cartoes)}")
        
        for cartao in cartoes:
            print(f"\n--- Cartão: {cartao.nome} ---")
            print(f"Fecha dia: {cartao.dia_fechamento}, Vence dia: {cartao.dia_vencimento}")
            
            if not cartao.dia_fechamento or not cartao.dia_vencimento:
                print("  ❌ Cartão sem dias de fechamento/vencimento configurados")
                continue
            
            # Testar os últimos 4 meses
            hoje_data = date.today()
            faturas_encontradas = []
            
            for meses_atras in range(0, 4):
                data_referencia = hoje_data - relativedelta(months=meses_atras)
                inicio, fim, fechamento, vencimento = calcular_ciclo_fatura(
                    data_referencia, cartao.dia_fechamento, cartao.dia_vencimento
                )
                
                # Verificar se deve mostrar alerta
                limite_alerta = vencimento + relativedelta(months=1)
                deve_alertar = fechamento <= hoje_data <= limite_alerta
                
                print(f"  Referência: {data_referencia}")
                print(f"    Período: {inicio} a {fim}")
                print(f"    Fechamento: {fechamento}, Vencimento: {vencimento}")
                print(f"    Deve alertar: {'✅ SIM' if deve_alertar else '❌ NÃO'}")
                
                if deve_alertar:
                    # Buscar fatura existente
                    fatura = db.query(Fatura).filter(
                        Fatura.cartao_id == cartao.id,
                        Fatura.periodo_inicio == inicio,
                        Fatura.periodo_fim == fim
                    ).first()
                    
                    if fatura:
                        print(f"    Fatura existente: Status={fatura.status}, Valor={fatura.valor_previsto}")
                        if fatura.status != "confirmada":
                            faturas_encontradas.append(fatura)
                    else:
                        print(f"    Fatura NÃO existe - DEVERIA CRIAR")
            
            print(f"  Total de faturas pendentes para este cartão: {len(faturas_encontradas)}")
        
        print(f"\n=== RESUMO ===")
        print(f"Faturas que deveriam aparecer como pendentes:")
        
        # Executar a função real de faturas pendentes
        from main import listar_faturas_pendentes
        
        # Simular um request fake (não é ideal, mas funciona para teste)
        class FakeRequest:
            pass
        
        # Buscar faturas pendentes reais
        faturas_reais = []
        for cartao in cartoes:
            if not cartao.dia_fechamento or not cartao.dia_vencimento:
                continue
                
            hoje_data = date.today()
            for meses_atras in range(0, 4):
                data_referencia = hoje_data - relativedelta(months=meses_atras)
                inicio, fim, fechamento, vencimento = calcular_ciclo_fatura(
                    data_referencia, cartao.dia_fechamento, cartao.dia_vencimento
                )
                
                limite_alerta = vencimento + relativedelta(months=1)
                if fechamento <= hoje_data <= limite_alerta:
                    fatura = db.query(Fatura).filter(
                        Fatura.cartao_id == cartao.id,
                        Fatura.periodo_inicio == inicio,
                        Fatura.periodo_fim == fim
                    ).first()
                    
                    if not fatura:
                        print(f"  CRIAR: {cartao.nome} - Fechamento {fechamento}, Vencimento {vencimento}")
                    elif fatura.status != "confirmada":
                        print(f"  ALERTAR: {cartao.nome} - Fechamento {fechamento}, Vencimento {vencimento}, Status: {fatura.status}")
                        faturas_reais.append(fatura)
        
        print(f"\nTotal de faturas que devem aparecer no alerta: {len(faturas_reais)}")
        
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    testar_faturas_pendentes()