from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Boolean, extract, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel, validator
from datetime import datetime, date
from typing import List, Optional
import os
import pandas as pd
from passlib.context import CryptContext
import jwt as PyJWT
import uuid
from dateutil.relativedelta import relativedelta
import io
import math

# Configuração do banco de dados
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin123@localhost:5432/contas_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Configuração de segurança
SECRET_KEY = os.getenv("SECRET_KEY", "sua-chave-secreta-aqui")
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Função para sanitizar valores float para JSON
def sanitize_float(value):
    """Converte valores float inválidos para valores JSON-safe"""
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return 0.0
    elif isinstance(value, (int, str, bool, type(None))):
        return value
    else:
        # Para outros tipos, tenta converter para string
        return str(value)
    return value

def sanitize_dict(data):
    """Sanitiza todos os valores float em um dicionário"""
    if isinstance(data, dict):
        return {k: sanitize_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_dict(item) for item in data]
    else:
        return sanitize_float(data)

# Modelos do banco de dados
class Categoria(Base):
    __tablename__ = "categorias"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False, unique=True)
    ativo = Column(Boolean, default=True)
    
    # Relacionamento
    contas = relationship("Conta", back_populates="categoria")

class Conta(Base):
    __tablename__ = "contas"
    
    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String, nullable=False)
    valor = Column(Float, nullable=False)
    data_vencimento = Column(Date, nullable=False)
    data_pagamento = Column(Date, nullable=True)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=False)
    forma_pagamento = Column(String, nullable=True)  # boleto, dda, pix, cartao_credito, cartao_debito, dinheiro, transferencia
    status = Column(String, default="pendente")  # pendente, pago, vencido
    observacoes = Column(String, nullable=True)
    # Campos para parcelamento
    eh_parcelado = Column(Boolean, default=False)
    numero_parcela = Column(Integer, nullable=True)  # Parcela atual (ex: 3)
    total_parcelas = Column(Integer, nullable=True)  # Total de parcelas (ex: 12)
    valor_total = Column(Float, nullable=True)  # Valor total da compra parcelada
    grupo_parcelamento = Column(String, nullable=True)  # UUID para agrupar parcelas
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento
    categoria = relationship("Categoria", back_populates="contas")

class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    nome = Column(String, nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# Criar tabelas
Base.metadata.create_all(bind=engine)

# Função para criar categorias padrão
def criar_categorias_padrao():
    db = SessionLocal()
    try:
        # Verificar se já existem categorias
        categorias_existentes = db.query(Categoria).count()
        if categorias_existentes == 0:
            categorias_padrao = [
                "Alimentação",
                "Transporte", 
                "Moradia",
                "Saúde",
                "Educação",
                "Lazer",
                "Vestuário",
                "Serviços",
                "Impostos",
                "Outros"
            ]
            
            for nome_categoria in categorias_padrao:
                categoria = Categoria(nome=nome_categoria, ativo=True)
                db.add(categoria)
            
            db.commit()
            print("Categorias padrão criadas com sucesso!")
    except Exception as e:
        print(f"Erro ao criar categorias padrão: {e}")
        db.rollback()
    finally:
        db.close()

# Criar categorias padrão na inicialização
criar_categorias_padrao()

# Schemas Pydantic
class CategoriaBase(BaseModel):
    nome: str
    ativo: Optional[bool] = True

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaUpdate(BaseModel):
    nome: Optional[str] = None
    ativo: Optional[bool] = None

class CategoriaResponse(CategoriaBase):
    id: int
    
    class Config:
        from_attributes = True

class ContaBase(BaseModel):
    descricao: str
    valor: float
    data_vencimento: date
    categoria_id: int
    forma_pagamento: Optional[str] = None  # boleto, dda, pix, cartao_credito, cartao_debito, dinheiro, transferencia
    observacoes: Optional[str] = None
    # Campos para parcelamento
    eh_parcelado: Optional[bool] = False
    numero_parcela: Optional[int] = None
    total_parcelas: Optional[int] = None
    valor_total: Optional[float] = None
    grupo_parcelamento: Optional[str] = None

class ContaCreate(ContaBase):
    # Campos específicos para criação de parcelamento
    parcelas_restantes: Optional[int] = None  # Quantas parcelas faltam
    pass

class ContaUpdate(BaseModel):
    descricao: Optional[str] = None
    valor: Optional[float] = None
    data_vencimento: Optional[date] = None
    data_pagamento: Optional[date] = None
    categoria_id: Optional[int] = None
    forma_pagamento: Optional[str] = None
    status: Optional[str] = None
    observacoes: Optional[str] = None
    eh_parcelado: Optional[bool] = None
    numero_parcela: Optional[int] = None
    total_parcelas: Optional[int] = None
    valor_total: Optional[float] = None
    grupo_parcelamento: Optional[str] = None

class ContaResponse(ContaBase):
    id: int
    data_pagamento: Optional[date] = None
    status: str
    created_at: datetime
    updated_at: datetime
    categoria: Optional[CategoriaResponse] = None
    
    class Config:
        from_attributes = True

class UsuarioCreate(BaseModel):
    email: str
    senha: str
    nome: str

class UsuarioLogin(BaseModel):
    email: str
    senha: str

class Token(BaseModel):
    access_token: str
    token_type: str

# FastAPI app
app = FastAPI(title="Sistema de Controle de Contas", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency para obter sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Funções de segurança
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    return PyJWT.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = PyJWT.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return email
    except PyJWT.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return verify_token(credentials)

# Rotas de autenticação
@app.post("/auth/register", response_model=Token)
def register(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    # Verificar se usuário já existe
    db_user = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    # Criar usuário
    hashed_password = get_password_hash(usuario.senha)
    db_user = Usuario(
        email=usuario.email,
        senha_hash=hashed_password,
        nome=usuario.nome
    )
    db.add(db_user)
    db.commit()
    
    # Gerar token
    access_token = create_access_token(data={"sub": usuario.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/login", response_model=Token)
def login(usuario: UsuarioLogin, db: Session = Depends(get_db)):
    db_user = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if not db_user or not verify_password(usuario.senha, db_user.senha_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    
    access_token = create_access_token(data={"sub": usuario.email})
    return {"access_token": access_token, "token_type": "bearer"}

# Rotas das categorias
@app.get("/categorias", response_model=List[CategoriaResponse])
def listar_categorias(
    skip: int = 0,
    limit: int = 100,
    ativo: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    query = db.query(Categoria)
    if ativo is not None:
        query = query.filter(Categoria.ativo == ativo)
    categorias = query.offset(skip).limit(limit).all()
    return categorias

@app.post("/categorias", response_model=CategoriaResponse)
def criar_categoria(
    categoria: CategoriaCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    db_categoria = Categoria(**categoria.dict())
    db.add(db_categoria)
    db.commit()
    db.refresh(db_categoria)
    return db_categoria

@app.put("/categorias/{categoria_id}", response_model=CategoriaResponse)
def atualizar_categoria(
    categoria_id: int,
    categoria: CategoriaUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    db_categoria = db.query(Categoria).filter(Categoria.id == categoria_id).first()
    if not db_categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    for key, value in categoria.dict(exclude_unset=True).items():
        setattr(db_categoria, key, value)
    
    db.commit()
    db.refresh(db_categoria)
    return db_categoria

@app.delete("/categorias/{categoria_id}")
def deletar_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    db_categoria = db.query(Categoria).filter(Categoria.id == categoria_id).first()
    if not db_categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    # Verificar se há contas associadas à categoria
    contas_associadas = db.query(Conta).filter(Conta.categoria_id == categoria_id).count()
    if contas_associadas > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Não é possível deletar a categoria. Existem {contas_associadas} contas associadas a ela."
        )
    
    db.delete(db_categoria)
    db.commit()
    return {"message": "Categoria deletada com sucesso"}

# Rotas das contas
@app.get("/contas", response_model=List[ContaResponse])
def listar_contas(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    categoria_id: Optional[int] = None,
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    query = db.query(Conta).join(Categoria)
    
    # Se não especificar mês/ano, usar mês atual
    if mes is None and ano is None:
        hoje = datetime.now()
        mes = hoje.month
        ano = hoje.year
    
    # Aplicar filtro de mês/ano se especificados
    if mes is not None:
        query = query.filter(extract('month', Conta.data_vencimento) == mes)
    if ano is not None:
        query = query.filter(extract('year', Conta.data_vencimento) == ano)
    
    if status:
        query = query.filter(Conta.status == status)
    if categoria_id:
        query = query.filter(Conta.categoria_id == categoria_id)
    
    contas = query.offset(skip).limit(limit).all()
    return contas

@app.post("/contas", response_model=List[ContaResponse])
def criar_conta(
    conta: ContaCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    contas_criadas = []
    
    # Se não é parcelado, criar conta única
    if not conta.eh_parcelado or not conta.parcelas_restantes or not conta.total_parcelas:
        db_conta = Conta(
            descricao=conta.descricao,
            valor=conta.valor,
            data_vencimento=conta.data_vencimento,
            categoria_id=conta.categoria_id,
            forma_pagamento=conta.forma_pagamento,
            observacoes=conta.observacoes,
            eh_parcelado=conta.eh_parcelado or False,
            numero_parcela=conta.numero_parcela,
            total_parcelas=conta.total_parcelas,
            valor_total=conta.valor_total,
            grupo_parcelamento=conta.grupo_parcelamento,
            status="pendente"
        )
        db.add(db_conta)
        db.commit()
        db.refresh(db_conta)
        return [db_conta]
    
    # Se é parcelado, criar múltiplas contas
    if conta.parcelas_restantes and conta.total_parcelas:
        # Gerar ID único para agrupar as parcelas
        grupo_id = str(uuid.uuid4())
        
        # Calcular parcela atual
        parcela_atual = conta.total_parcelas - conta.parcelas_restantes + 1
        
        # Valor total da compra (se não informado, usar valor * total_parcelas)
        valor_total_compra = conta.valor_total or (conta.valor * conta.total_parcelas)
        
        # Criar TODAS as parcelas (anteriores + restantes)
        for numero_parcela in range(1, conta.total_parcelas + 1):
            
            # Calcular quantos meses antes/depois da data informada esta parcela deve vencer
            # Se parcela atual é 8 e estamos criando a parcela 1, ela deve vencer 7 meses antes
            # Se parcela atual é 8 e estamos criando a parcela 10, ela deve vencer 2 meses depois
            meses_diferenca = numero_parcela - parcela_atual
            data_vencimento = conta.data_vencimento + relativedelta(months=meses_diferenca)
            
            # Determinar status da parcela
            if numero_parcela < parcela_atual:
                # Parcelas anteriores são marcadas como pagas
                status_parcela = "pago"
                data_pagamento = data_vencimento  # Assume que foi paga na data de vencimento
            else:
                # Parcelas atual e futuras são pendentes
                status_parcela = "pendente"
                data_pagamento = None
            
            # Criar descrição com número da parcela
            descricao_parcela = f"{conta.descricao} - Parcela {numero_parcela}/{conta.total_parcelas}"
            
            db_conta = Conta(
                descricao=descricao_parcela,
                valor=conta.valor,
                data_vencimento=data_vencimento,
                data_pagamento=data_pagamento,
                categoria_id=conta.categoria_id,
                forma_pagamento=conta.forma_pagamento,
                observacoes=conta.observacoes,
                eh_parcelado=True,
                numero_parcela=numero_parcela,
                total_parcelas=conta.total_parcelas,
                valor_total=valor_total_compra,
                grupo_parcelamento=grupo_id,
                status=status_parcela
            )
            
            db.add(db_conta)
            contas_criadas.append(db_conta)
        
        db.commit()
        
        # Atualizar as contas criadas com os IDs
        for conta_criada in contas_criadas:
            db.refresh(conta_criada)
    
    return contas_criadas

@app.get("/contas/{conta_id}", response_model=ContaResponse)
def obter_conta(
    conta_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    conta = db.query(Conta).filter(Conta.id == conta_id).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    return conta

@app.get("/contas/{conta_id}/info-parcelamento")
def info_parcelamento_conta(
    conta_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    conta = db.query(Conta).filter(Conta.id == conta_id).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    
    if conta.eh_parcelado and conta.grupo_parcelamento:
        # Buscar todas as parcelas do grupo
        parcelas = db.query(Conta).filter(Conta.grupo_parcelamento == conta.grupo_parcelamento).all()
        return {
            "eh_parcelado": True,
            "numero_parcela": conta.numero_parcela,
            "total_parcelas": conta.total_parcelas,
            "total_parcelas_grupo": len(parcelas),
            "grupo_parcelamento": conta.grupo_parcelamento
        }
    else:
        return {
            "eh_parcelado": False
        }

@app.put("/contas/{conta_id}", response_model=ContaResponse)
def atualizar_conta(
    conta_id: int,
    conta_update: ContaUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    conta = db.query(Conta).filter(Conta.id == conta_id).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    
    # Verificar se está sendo marcada como parcelada
    if conta_update.eh_parcelado and not conta.eh_parcelado:
        # Está sendo transformada em conta parcelada
        if not conta_update.total_parcelas or not conta_update.parcelas_restantes:
            raise HTTPException(
                status_code=400, 
                detail="Para tornar uma conta parcelada, é necessário informar total_parcelas e parcelas_restantes"
            )
        
        # Gerar ID único para agrupar as parcelas
        grupo_id = str(uuid.uuid4())
        
        # Calcular parcela atual
        parcela_atual = conta_update.total_parcelas - conta_update.parcelas_restantes + 1
        
        # Valor total da compra (se não informado, usar valor * total_parcelas)
        valor_total_compra = conta_update.valor_total or (conta.valor * conta_update.total_parcelas)
        
        # Atualizar a conta atual para ser a parcela atual
        conta.eh_parcelado = True
        conta.numero_parcela = parcela_atual
        conta.total_parcelas = conta_update.total_parcelas
        conta.valor_total = valor_total_compra
        conta.grupo_parcelamento = grupo_id
        conta.descricao = f"{conta.descricao} - Parcela {parcela_atual}/{conta_update.total_parcelas}"
        
        # Criar as outras parcelas (anteriores e futuras)
        contas_criadas = []
        for numero_parcela in range(1, conta_update.total_parcelas + 1):
            if numero_parcela == parcela_atual:
                continue  # Pular a parcela atual que já existe
            
            # Calcular quantos meses antes/depois da data atual esta parcela deve vencer
            meses_diferenca = numero_parcela - parcela_atual
            data_vencimento = conta.data_vencimento + relativedelta(months=meses_diferenca)
            
            # Determinar status da parcela
            if numero_parcela < parcela_atual:
                # Parcelas anteriores são marcadas como pagas
                status_parcela = "pago"
                data_pagamento = data_vencimento  # Assume que foi paga na data de vencimento
            else:
                # Parcelas futuras são pendentes
                status_parcela = "pendente"
                data_pagamento = None
            
            # Criar descrição com número da parcela
            descricao_original = conta.descricao.split(" - Parcela")[0]  # Remove sufixo se já existir
            descricao_parcela = f"{descricao_original} - Parcela {numero_parcela}/{conta_update.total_parcelas}"
            
            nova_conta = Conta(
                descricao=descricao_parcela,
                valor=conta.valor,
                data_vencimento=data_vencimento,
                data_pagamento=data_pagamento,
                categoria_id=conta.categoria_id,
                forma_pagamento=conta.forma_pagamento,
                observacoes=conta.observacoes,
                eh_parcelado=True,
                numero_parcela=numero_parcela,
                total_parcelas=conta_update.total_parcelas,
                valor_total=valor_total_compra,
                grupo_parcelamento=grupo_id,
                status=status_parcela
            )
            
            db.add(nova_conta)
            contas_criadas.append(nova_conta)
        
        conta.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(conta)
        
        return {
            "conta_atualizada": conta,
            "parcelas_criadas": len(contas_criadas),
            "total_parcelas": conta_update.total_parcelas,
            "grupo_parcelamento": grupo_id
        }
    
    # Atualização normal (não parcelamento)
    update_data = conta_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(conta, field, value)
    
    conta.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(conta)
    return conta

@app.get("/contas/grupo/{grupo_id}", response_model=List[ContaResponse])
def obter_parcelas_por_grupo(
    grupo_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Buscar todas as parcelas de um grupo de parcelamento"""
    parcelas = db.query(Conta).filter(
        Conta.grupo_parcelamento == grupo_id
    ).order_by(Conta.numero_parcela).all()
    
    if not parcelas:
        raise HTTPException(status_code=404, detail="Grupo de parcelas não encontrado")
    
    return parcelas

@app.delete("/contas/{conta_id}")
def deletar_conta(
    conta_id: int,
    deletar_todas_parcelas: bool = False,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    conta = db.query(Conta).filter(Conta.id == conta_id).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    
    # Se a conta é parcelada e o usuário quer deletar todas as parcelas
    if conta.eh_parcelado and conta.grupo_parcelamento and deletar_todas_parcelas:
        # Deletar todas as contas do mesmo grupo de parcelamento
        contas_grupo = db.query(Conta).filter(Conta.grupo_parcelamento == conta.grupo_parcelamento).all()
        for conta_parcela in contas_grupo:
            db.delete(conta_parcela)
        db.commit()
        return {"message": f"Todas as {len(contas_grupo)} parcelas foram deletadas com sucesso"}
    else:
        # Deletar apenas a conta específica
        db.delete(conta)
        db.commit()
        return {"message": "Conta deletada com sucesso"}

@app.post("/contas/{conta_id}/pagar")
def marcar_como_pago(
    conta_id: int,
    data_pagamento: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    conta = db.query(Conta).filter(Conta.id == conta_id).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    
    conta.status = "pago"
    conta.data_pagamento = data_pagamento or date.today()
    conta.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(conta)
    return conta

@app.post("/contas/{conta_id}/desmarcar-pagamento")
def desmarcar_pagamento(
    conta_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    conta = db.query(Conta).filter(Conta.id == conta_id).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    
    conta.status = "pendente"
    conta.data_pagamento = None
    conta.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(conta)
    return conta

# Rotas de relatórios
@app.get("/relatorios/resumo")
def resumo_contas(
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    # Se não especificar mês/ano, usar mês atual
    if mes is None and ano is None:
        hoje = datetime.now()
        mes = hoje.month
        ano = hoje.year
    
    # Construir query base com filtro de mês/ano
    query_base = db.query(Conta)
    if mes is not None:
        query_base = query_base.filter(extract('month', Conta.data_vencimento) == mes)
    if ano is not None:
        query_base = query_base.filter(extract('year', Conta.data_vencimento) == ano)
    
    total_pendente = query_base.filter(Conta.status == "pendente").count()
    total_pago = query_base.filter(Conta.status == "pago").count()
    total_vencido = query_base.filter(
        Conta.status == "pendente",
        Conta.data_vencimento < date.today()
    ).count()
    
    valor_pendente = query_base.filter(Conta.status == "pendente").all()
    valor_total_pendente = sum(conta.valor for conta in valor_pendente) or 0.0
    
    return {
        "total_pendente": total_pendente,
        "total_pago": total_pago,
        "total_vencido": total_vencido,
        "valor_total_pendente": sanitize_float(valor_total_pendente)
    }

@app.get("/relatorios/grafico-evolucao")
def grafico_evolucao_mensal(
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """
    Retorna dados para gráfico com 2 meses anteriores e 9 posteriores ao atual
    Com valores previstos e pagos para cada mês
    """
    hoje = datetime.now()
    dados_grafico = []
    
    # Gerar dados para 12 meses (2 anteriores + atual + 9 posteriores)
    for i in range(-2, 10):
        data_mes = hoje + relativedelta(months=i)
        mes = data_mes.month
        ano = data_mes.year
        
        # Buscar contas do mês
        contas_mes = db.query(Conta).filter(
            extract('month', Conta.data_vencimento) == mes,
            extract('year', Conta.data_vencimento) == ano
        ).all()
        
        valor_previsto = sum(conta.valor for conta in contas_mes) or 0.0
        valor_pago = sum(conta.valor for conta in contas_mes if conta.status == "pago") or 0.0
        
        dados_grafico.append({
            "mes": mes,
            "ano": ano,
            "mes_nome": data_mes.strftime("%b/%Y"),
            "valor_previsto": sanitize_float(valor_previsto),
            "valor_pago": sanitize_float(valor_pago),
            "eh_mes_atual": i == 0
        })
    
    return dados_grafico

@app.get("/relatorios/categorias")
def relatorio_por_categoria(
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    # Buscar contas com suas categorias
    contas = db.query(Conta).join(Categoria).all()
    categorias = {}
    
    for conta in contas:
        nome_categoria = conta.categoria.nome
        if nome_categoria not in categorias:
            categorias[nome_categoria] = {"total": 0.0, "pendente": 0.0, "pago": 0.0}
        
        valor_sanitizado = sanitize_float(conta.valor)
        categorias[nome_categoria]["total"] += valor_sanitizado
        if conta.status == "pendente":
            categorias[nome_categoria]["pendente"] += valor_sanitizado
        else:
            categorias[nome_categoria]["pago"] += valor_sanitizado
    
    # Sanitizar toda a resposta
    return sanitize_dict(categorias)

# Rota para importar dados do Excel
@app.get("/exportar-modelo-excel")
def exportar_modelo_excel():
    """
    Exporta um arquivo Excel modelo para importação de contas.
    """
    # Dados de exemplo para o modelo
    dados_exemplo = {
        'Descricao': [
            'Conta de Luz',
            'Supermercado',
            'Gasolina',
            'Internet',
            'Farmácia'
        ],
        'Data de Pagamento': [
            '15/08/2025',
            '20/08/2025',
            '22/08/2025',
            '01/08/2025',
            '18/08/2025'
        ],
        'Categoria': [
            'Utilidades',
            'Alimentação',
            'Transporte',
            'Tecnologia',
            'Saúde'
        ],
        'Valor': [
            150.50,
            200.00,
            120.75,
            99.90,
            45.30
        ]
    }
    
    # Criar DataFrame
    df = pd.DataFrame(dados_exemplo)
    
    # Criar arquivo Excel em memória
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Escrever dados de exemplo
        df.to_excel(writer, sheet_name='Exemplo', index=False)
        
        # Criar uma planilha em branco para o usuário preencher
        df_vazio = pd.DataFrame(columns=['Descricao', 'Data de Pagamento', 'Categoria', 'Valor'])
        df_vazio.to_excel(writer, sheet_name='Importar Aqui', index=False)
        
        # Adicionar instruções
        instrucoes = pd.DataFrame({
            'INSTRUÇÕES PARA IMPORTAÇÃO': [
                '1. Use a aba "Importar Aqui" para suas contas',
                '2. Preencha todas as colunas obrigatórias:',
                '   - Descricao: Descrição da conta',
                '   - Data de Pagamento: Data no formato DD/MM/AAAA',
                '   - Categoria: Nome da categoria',
                '   - Valor: Valor numérico da conta',
                '3. Categorias serão criadas automaticamente se não existirem',
                '4. Contas importadas serão marcadas como pagas',
                '5. Veja a aba "Exemplo" para referência',
                '',
                'FORMATO DAS DATAS: DD/MM/AAAA (ex: 15/08/2025)',
                'FORMATO DOS VALORES: Use ponto como separador decimal (ex: 150.50)'
            ]
        })
        instrucoes.to_excel(writer, sheet_name='Instruções', index=False)
    
    output.seek(0)
    
    # Preparar resposta para download
    headers = {
        'Content-Disposition': 'attachment; filename="modelo_importacao_contas.xlsx"'
    }
    
    return StreamingResponse(
        io.BytesIO(output.read()),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers=headers
    )

@app.post("/importar-excel")
async def importar_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Importa contas a partir de um arquivo Excel.
    Formato esperado: Descricao, Data de Pagamento, Categoria, Valor
    """
    
    # Verificar se o arquivo é Excel
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Arquivo deve ser um Excel (.xlsx ou .xls)"
        )
    
    try:
        # Ler o arquivo Excel
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # Verificar se tem pelo menos 4 colunas
        if len(df.columns) < 4:
            raise HTTPException(
                status_code=400,
                detail=f"O arquivo deve ter pelo menos 4 colunas. Encontradas: {len(df.columns)} colunas"
            )
        
        # Renomear colunas para padrão esperado (usar posição, não nome)
        colunas_padrao = ['Descricao', 'Data de Pagamento', 'Categoria', 'Valor']
        df.columns = colunas_padrao[:len(df.columns)]
        
        print(f"Arquivo tem {len(df.columns)} colunas. Usando as 4 primeiras como: {colunas_padrao[:4]}")  # Debug
        
        contas_criadas = []
        contas_com_erro = []
        categorias_criadas = []
        
        for index, row in df.iterrows():
            try:
                print(f"Processando linha {index + 2}: {row.to_dict()}")  # Debug
                
                # Verificar se a categoria existe, se não, criar
                categoria_nome = str(row['Categoria']).strip()
                if not categoria_nome or categoria_nome.lower() in ['nan', 'none', '']:
                    raise ValueError("Categoria não pode estar vazia")
                    
                categoria = db.query(Categoria).filter(Categoria.nome == categoria_nome).first()
                
                if not categoria:
                    # Criar nova categoria
                    categoria = Categoria(
                        nome=categoria_nome
                    )
                    db.add(categoria)
                    db.flush()  # Para obter o ID
                    categorias_criadas.append(categoria_nome)
                    print(f"Categoria criada: {categoria_nome}")  # Debug
                
                # Converter data
                try:
                    data_raw = row['Data de Pagamento']
                    print(f"Data bruta: {data_raw} (tipo: {type(data_raw)})")  # Debug
                    
                    # Se a data for um número (dia do mês), assumir mês/ano atual (agosto/2025)
                    if isinstance(data_raw, (int, float)) and not pd.isna(data_raw):
                        dia = int(data_raw)
                        if dia < 1 or dia > 31:
                            raise ValueError(f"Dia inválido: {dia}")
                        # Usar mês atual (agosto) e ano atual (2025)
                        from datetime import datetime
                        data_pagamento = datetime(2025, 8, dia).date()
                    else:
                        # Tentar diferentes formatos de data
                        data_str = str(data_raw)
                        data_pagamento = None
                        formatos = ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y']
                        
                        for formato in formatos:
                            try:
                                data_pagamento = datetime.strptime(data_str, formato).date()
                                break
                            except ValueError:
                                continue
                        
                        if data_pagamento is None:
                            raise ValueError(f"Formato de data não reconhecido: {data_str}")
                    
                    print(f"Data convertida: {data_pagamento}")  # Debug
                except Exception as e:
                    raise ValueError(f"Data inválida: {row['Data de Pagamento']} - {str(e)}")
                
                # Converter valor com validação
                try:
                    valor_raw = row['Valor']
                    print(f"Valor bruto: {valor_raw} (tipo: {type(valor_raw)})")  # Debug
                    
                    # Verificar se é NaN ou vazio
                    if pd.isna(valor_raw) or valor_raw == '':
                        raise ValueError("Valor não pode estar vazio")
                    
                    valor = float(valor_raw)
                    
                    # Verificar se é um número válido
                    if math.isnan(valor) or math.isinf(valor):
                        raise ValueError(f"Valor inválido: {valor_raw}")
                    
                    if valor < 0:
                        raise ValueError(f"Valor deve ser positivo: {valor}")
                        
                    print(f"Valor convertido: {valor}")  # Debug
                        
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Valor inválido na linha {index + 2}: {row['Valor']} - {str(e)}")
                
                # Validar descrição
                descricao = str(row['Descricao']).strip()
                if not descricao or descricao.lower() in ['nan', 'none', '']:
                    raise ValueError(f"Descrição não pode estar vazia na linha {index + 2}")
                
                print(f"Descrição: {descricao}")  # Debug
                
                # Criar a conta
                nova_conta = Conta(
                    descricao=descricao,
                    valor=valor,
                    data_vencimento=data_pagamento,
                    data_pagamento=data_pagamento,
                    categoria_id=categoria.id,
                    forma_pagamento="Não especificado",
                    status="pago",  # Como tem data de pagamento, assumimos que está paga
                    observacoes=f"Importada via Excel em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                )
                
                db.add(nova_conta)
                contas_criadas.append({
                    "descricao": nova_conta.descricao,
                    "valor": sanitize_float(nova_conta.valor),
                    "categoria": categoria_nome
                })
                
                print(f"Conta criada com sucesso: {descricao}")  # Debug
                
            except Exception as e:
                error_msg = str(e)
                print(f"ERRO na linha {index + 2}: {error_msg}")  # Debug
                
                # Sanitizar dados da linha que causou erro
                try:
                    row_dict = row.to_dict()
                    row_dict_sanitized = sanitize_dict(row_dict)
                except:
                    row_dict_sanitized = {"erro": "Não foi possível processar dados da linha"}
                
                contas_com_erro.append({
                    "linha": index + 2,  # +2 porque Excel começa na linha 1 e temos cabeçalho
                    "erro": error_msg,
                    "dados": row_dict_sanitized
                })
        
        # Commit das alterações
        db.commit()
        
        # Sanitizar resposta final
        try:
            response_data = {
                "message": f"Importação concluída com sucesso!",
                "contas_criadas": len(contas_criadas),
                "contas_com_erro": len(contas_com_erro),
                "categorias_criadas": categorias_criadas,
                "detalhes": {
                    "contas_criadas": contas_criadas,
                    "contas_com_erro": contas_com_erro
                }
            }
            
            sanitized_response = sanitize_dict(response_data)
            return sanitized_response
            
        except Exception as json_error:
            # Se houver erro na serialização, retornar resposta mais simples
            return {
                "message": f"Importação concluída com sucesso!",
                "contas_criadas": len(contas_criadas),
                "contas_com_erro": len(contas_com_erro),
                "categorias_criadas": len(categorias_criadas),
                "erro_detalhes": str(json_error)
            }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar arquivo: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)