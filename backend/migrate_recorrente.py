#!/usr/bin/env python3
"""
Script de migrações pontuais (recorrentes e cartões)
"""

import psycopg2
import os
from sqlalchemy import create_engine, text

# Configurações do banco
DATABASE_URL = "postgresql://admin:admin123@postgres:5432/contas_db"

def run_migration():
    """Executa migrações: recorrentes e cartões/cartao_id"""
    
    try:
        # Conectar ao banco
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as connection:
            # Verificar se as colunas já existem (recorrentes)
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'contas' AND column_name IN ('eh_recorrente', 'grupo_recorrencia', 'valor_previsto', 'valor_pago')
            """))
            
            existing_columns = [row[0] for row in result]
            print(f"Colunas existentes: {existing_columns}")
            
            # Adicionar colunas que não existem
            migrations = []
            
            if 'eh_recorrente' not in existing_columns:
                migrations.append("ALTER TABLE contas ADD COLUMN eh_recorrente BOOLEAN DEFAULT FALSE")
                
            if 'grupo_recorrencia' not in existing_columns:
                migrations.append("ALTER TABLE contas ADD COLUMN grupo_recorrencia VARCHAR(255)")
                
            if 'valor_previsto' not in existing_columns:
                migrations.append("ALTER TABLE contas ADD COLUMN valor_previsto DECIMAL(10,2)")
                
            if 'valor_pago' not in existing_columns:
                migrations.append("ALTER TABLE contas ADD COLUMN valor_pago DECIMAL(10,2)")
            
            # Executar migrações
            for migration in migrations:
                print(f"Executando: {migration}")
                connection.execute(text(migration))
                connection.commit()
            
            if migrations:
                print(f"✅ Migração recorrentes concluída! {len(migrations)} colunas adicionadas.")
            else:
                print("✅ Colunas recorrentes já existem. Nenhuma migração necessária.")

            # Criar tabela cartoes se não existir
            print("🔎 Verificando tabela cartoes...")
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS cartoes (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(255) NOT NULL UNIQUE,
                    bandeira VARCHAR(100),
                    limite DOUBLE PRECISION,
                    dia_fechamento INTEGER,
                    dia_vencimento INTEGER,
                    ativo BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            connection.commit()
            print("✅ Tabela cartoes verificada/criada.")

            # Adicionar coluna cartao_id em contas, se não existir
            print("🔎 Verificando coluna cartao_id na tabela contas...")
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'contas' AND column_name = 'cartao_id'
            """))
            has_cartao_id = result.first() is not None
            if not has_cartao_id:
                connection.execute(text("""
                    ALTER TABLE contas ADD COLUMN cartao_id INTEGER NULL
                """))
                connection.execute(text("""
                    ALTER TABLE contas
                    ADD CONSTRAINT fk_contas_cartoes
                    FOREIGN KEY (cartao_id) REFERENCES cartoes(id)
                    ON DELETE SET NULL
                """))
                connection.commit()
                print("✅ Coluna cartao_id adicionada com FK para cartoes.")
            else:
                print("✅ Coluna cartao_id já existe.")

            # Criar tabela faturas se não existir
            print("🔎 Verificando tabela faturas...")
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS faturas (
                    id SERIAL PRIMARY KEY,
                    cartao_id INTEGER NOT NULL REFERENCES cartoes(id),
                    periodo_inicio DATE NOT NULL,
                    periodo_fim DATE NOT NULL,
                    data_fechamento DATE NOT NULL,
                    data_vencimento DATE NOT NULL,
                    valor_previsto DOUBLE PRECISION,
                    valor_real DOUBLE PRECISION,
                    status VARCHAR(50) DEFAULT 'pendente',
                    conta_id INTEGER REFERENCES contas(id),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            connection.commit()
            print("✅ Tabela faturas verificada/criada.")
                
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        return False
        
    return True

if __name__ == "__main__":
    print("🔄 Iniciando migração para contas recorrentes...")
    success = run_migration()
    
    if success:
        print("🎉 Migração concluída com sucesso!")
    else:
        print("💥 Falha na migração!")