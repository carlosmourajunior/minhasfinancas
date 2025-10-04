#!/usr/bin/env python3
"""
Script para verificar exatamente o que a API retorna
"""

import sys
import os
import json
from datetime import date

sys.path.insert(0, '/app')
from main import app, SessionLocal, get_db
from fastapi.testclient import TestClient

def testar_api_faturas():
    """Testa a API de faturas pendentes diretamente"""
    print("=== TESTE DA API DE FATURAS PENDENTES ===")
    
    client = TestClient(app)
    
    # Primeiro, fazer login
    login_response = client.post("/auth/login", json={
        "email": "admin@teste.com",
        "senha": "secret"
    })
    
    if login_response.status_code != 200:
        print(f"Erro no login: {login_response.status_code} - {login_response.text}")
        
        # Tentar registrar
        register_response = client.post("/auth/register", json={
            "email": "admin@teste.com",
            "senha": "secret",
            "nome": "Admin"
        })
        print(f"Registro: {register_response.status_code}")
        
        if register_response.status_code == 200:
            token = register_response.json()["access_token"]
        else:
            print("Não foi possível fazer login nem registrar")
            return
    else:
        token = login_response.json()["access_token"]
    
    print(f"Token obtido: {token[:20]}...")
    
    # Testar a API de faturas pendentes
    headers = {"Authorization": f"Bearer {token}"}
    
    faturas_response = client.get("/cartoes/faturas/pendentes", headers=headers)
    print(f"Status da resposta: {faturas_response.status_code}")
    
    if faturas_response.status_code == 200:
        faturas = faturas_response.json()
        print(f"Faturas retornadas: {len(faturas)}")
        
        for i, fatura in enumerate(faturas):
            print(f"\nFatura {i+1}:")
            print(f"  ID: {fatura.get('id')}")
            print(f"  Cartão ID: {fatura.get('cartao_id')}")
            print(f"  Cartão Nome: {fatura.get('cartao_nome')}")
            print(f"  Período: {fatura.get('periodo_inicio')} a {fatura.get('periodo_fim')}")
            print(f"  Fechamento: {fatura.get('data_fechamento')}")
            print(f"  Vencimento: {fatura.get('data_vencimento')}")
            print(f"  Valor Previsto: {fatura.get('valor_previsto')}")
            print(f"  Status: {fatura.get('status')}")
    else:
        print(f"Erro na API: {faturas_response.text}")

if __name__ == "__main__":
    testar_api_faturas()