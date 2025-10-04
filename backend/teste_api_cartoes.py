#!/usr/bin/env python3
"""
Script para testar a API de listagem de cartões com estimativas
"""

import sys
import os
from datetime import date

# Adicionar o diretório do projeto ao path
sys.path.insert(0, '/app')

from main import SessionLocal, Cartao, Fatura, Conta, calcular_ciclo_fatura
from dateutil.relativedelta import relativedelta

def testar_api_cartoes():
    """Testa a nova API de cartões com estimativas"""
    print("=== TESTE DA API DE CARTÕES COM ESTIMATIVAS ===")
    print()
    
    db = SessionLocal()
    try:
        # Simular a lógica da nova API
        cartoes = db.query(Cartao).filter(Cartao.ativo == True).all()
        
        cartoes_com_estimativa = []
        hoje_data = date.today()
        data_corte_vencimento = date(2025, 9, 1)
        
        for cartao in cartoes:
            print(f"🏧 Processando: {cartao.nome}")
            
            # Calcular estimativa atual
            valor_previsto_atual = 0.0
            data_proxima_fatura = None
            status_fatura = None
            
            if cartao.dia_fechamento and cartao.dia_vencimento:
                # Verificar se há fatura pendente atual
                for meses_atras in range(0, 4):
                    data_referencia = hoje_data - relativedelta(months=meses_atras)
                    inicio, fim, fechamento, vencimento = calcular_ciclo_fatura(
                        data_referencia, cartao.dia_fechamento, cartao.dia_vencimento
                    )
                    
                    if vencimento < data_corte_vencimento:
                        continue
                    
                    limite_alerta = vencimento + relativedelta(months=1)
                    
                    if fechamento <= hoje_data <= limite_alerta:
                        # Buscar fatura pendente
                        fatura = db.query(Fatura).filter(
                            Fatura.cartao_id == cartao.id,
                            Fatura.periodo_inicio == inicio,
                            Fatura.periodo_fim == fim,
                            Fatura.status == "pendente"
                        ).first()
                        
                        if fatura:
                            # Calcular valor atualizado
                            contas_periodo = db.query(Conta).filter(
                                Conta.cartao_id == cartao.id,
                                Conta.data_vencimento >= inicio,
                                Conta.data_vencimento <= fim
                            ).all()
                            valor_previsto_atual = sum(ct.valor for ct in contas_periodo) or 0.0
                            data_proxima_fatura = vencimento
                            status_fatura = "pendente"
                            print(f"  📊 Fatura encontrada: {valor_previsto_atual}")
                            break
            
            # Criar resposta simulada
            cartao_resultado = {
                "id": cartao.id,
                "nome": cartao.nome,
                "bandeira": cartao.bandeira,
                "limite": cartao.limite,
                "dia_fechamento": cartao.dia_fechamento,
                "dia_vencimento": cartao.dia_vencimento,
                "ativo": cartao.ativo,
                "valor_previsto_atual": valor_previsto_atual,
                "data_proxima_fatura": data_proxima_fatura.strftime('%Y-%m-%d') if data_proxima_fatura else None,
                "status_fatura": status_fatura
            }
            
            cartoes_com_estimativa.append(cartao_resultado)
            
            print(f"  💰 Valor previsto: R$ {valor_previsto_atual:.2f}")
            print(f"  📅 Próxima fatura: {data_proxima_fatura or 'N/A'}")
            print(f"  📊 Status: {status_fatura or 'Sem fatura pendente'}")
            print()
        
        print("=== RESULTADO FINAL ===")
        print(f"Total de cartões processados: {len(cartoes_com_estimativa)}")
        
        for cartao in cartoes_com_estimativa:
            if cartao["valor_previsto_atual"] > 0:
                print(f"✅ {cartao['nome']}: R$ {cartao['valor_previsto_atual']:.2f}")
            else:
                print(f"⚪ {cartao['nome']}: R$ 0,00")
        
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    testar_api_cartoes()