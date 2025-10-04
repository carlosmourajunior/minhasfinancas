from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Boolean, extract, ForeignKey, or_, and_, not_
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

class Cartao(Base):
    __tablename__ = "cartoes"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False, unique=True)
    bandeira = Column(String, nullable=True)
    limite = Column(Float, nullable=True)
    dia_fechamento = Column(Integer, nullable=True)
    dia_vencimento = Column(Integer, nullable=True)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    contas = relationship("Conta", back_populates="cartao")

class Fatura(Base):
    __tablename__ = "faturas"
    
    id = Column(Integer, primary_key=True, index=True)
    cartao_id = Column(Integer, ForeignKey("cartoes.id"), nullable=False)
    periodo_inicio = Column(Date, nullable=False)
    periodo_fim = Column(Date, nullable=False)
    data_fechamento = Column(Date, nullable=False)
    data_vencimento = Column(Date, nullable=False)
    valor_previsto = Column(Float, nullable=True)
    valor_real = Column(Float, nullable=True)
    status = Column(String, default="pendente")  # pendente, confirmada
    conta_id = Column(Integer, ForeignKey("contas.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    cartao = relationship("Cartao")

    # Propriedade para expor o nome do cartão no schema de resposta
    @property
    def cartao_nome(self):
        try:
            return self.cartao.nome if self.cartao else None
        except Exception:
            return None

class Conta(Base):
    __tablename__ = "contas"
    
    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String, nullable=False)
    valor = Column(Float, nullable=False)
    data_vencimento = Column(Date, nullable=False)
    data_pagamento = Column(Date, nullable=True)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=False)
    cartao_id = Column(Integer, ForeignKey("cartoes.id"), nullable=True)
    forma_pagamento = Column(String, nullable=True)  # boleto, dda, pix, cartao_credito, cartao_debito, dinheiro, transferencia
    status = Column(String, default="pendente")  # pendente, pago, vencido
    observacoes = Column(String, nullable=True)
    # Campos para parcelamento
    eh_parcelado = Column(Boolean, default=False)
    numero_parcela = Column(Integer, nullable=True)  # Parcela atual (ex: 3)
    total_parcelas = Column(Integer, nullable=True)  # Total de parcelas (ex: 12)
    valor_total = Column(Float, nullable=True)  # Valor total da compra parcelada
    grupo_parcelamento = Column(String, nullable=True)  # UUID para agrupar parcelas
    # Campos para contas recorrentes
    eh_recorrente = Column(Boolean, default=False)
    grupo_recorrencia = Column(String, nullable=True)  # UUID para agrupar contas recorrentes
    valor_previsto = Column(Float, nullable=True)  # Valor original previsto
    valor_pago = Column(Float, nullable=True)  # Valor real que foi pago (pode ser diferente do previsto)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento
    categoria = relationship("Categoria", back_populates="contas")
    cartao = relationship("Cartao", back_populates="contas")

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

class CartaoBase(BaseModel):
    nome: str
    bandeira: Optional[str] = None
    limite: Optional[float] = None
    dia_fechamento: Optional[int] = None
    dia_vencimento: Optional[int] = None
    ativo: Optional[bool] = True

class CartaoCreate(CartaoBase):
    pass

class CartaoUpdate(BaseModel):
    nome: Optional[str] = None
    bandeira: Optional[str] = None
    limite: Optional[float] = None
    dia_fechamento: Optional[int] = None
    dia_vencimento: Optional[int] = None
    ativo: Optional[bool] = None

class CartaoResponse(CartaoBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CartaoComEstimativaResponse(CartaoBase):
    id: int
    created_at: datetime
    updated_at: datetime
    valor_previsto_atual: Optional[float] = 0.0
    data_proxima_fatura: Optional[date] = None
    status_fatura: Optional[str] = None
    fatura_paga_mes_atual: Optional[bool] = False
    valor_fatura_pago: Optional[float] = None
    
    class Config:
        from_attributes = True

class FaturaResponse(BaseModel):
    id: int
    cartao_id: int
    periodo_inicio: date
    periodo_fim: date
    data_fechamento: date
    data_vencimento: date
    valor_previsto: Optional[float] = None
    valor_real: Optional[float] = None
    status: str
    conta_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    cartao_nome: Optional[str] = None
    
    class Config:
        from_attributes = True

class FaturaConfirmRequest(BaseModel):
    valor_real: float

class ContaBase(BaseModel):
    descricao: str
    valor: float
    data_vencimento: date
    categoria_id: int
    cartao_id: Optional[int] = None
    forma_pagamento: Optional[str] = None  # boleto, dda, pix, cartao_credito, cartao_debito, dinheiro, transferencia
    observacoes: Optional[str] = None
    # Campos para parcelamento
    eh_parcelado: Optional[bool] = False
    numero_parcela: Optional[int] = None
    total_parcelas: Optional[int] = None
    valor_total: Optional[float] = None
    grupo_parcelamento: Optional[str] = None
    # Campos para contas recorrentes
    eh_recorrente: Optional[bool] = False
    grupo_recorrencia: Optional[str] = None
    valor_previsto: Optional[float] = None

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
    cartao_id: Optional[int] = None
    forma_pagamento: Optional[str] = None
    status: Optional[str] = None
    observacoes: Optional[str] = None
    eh_parcelado: Optional[bool] = None
    numero_parcela: Optional[int] = None
    total_parcelas: Optional[int] = None
    parcelas_restantes: Optional[int] = None
    valor_total: Optional[float] = None
    grupo_parcelamento: Optional[str] = None
    # Campos para contas recorrentes
    eh_recorrente: Optional[bool] = None
    grupo_recorrencia: Optional[str] = None
    valor_previsto: Optional[float] = None
    valor_pago: Optional[float] = None

class ContaResponse(ContaBase):
    id: int
    data_pagamento: Optional[date] = None
    status: str
    created_at: datetime
    updated_at: datetime
    categoria: Optional[CategoriaResponse] = None
    cartao: Optional[CartaoResponse] = None
    
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

# Rotas dos cartões
@app.get("/cartoes", response_model=List[CartaoComEstimativaResponse])
def listar_cartoes(
    skip: int = 0,
    limit: int = 100,
    ativo: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    query = db.query(Cartao)
    if ativo is not None:
        query = query.filter(Cartao.ativo == ativo)
    cartoes = query.offset(skip).limit(limit).all()
    
    # Enriquecer com dados de estimativa
    cartoes_com_estimativa = []
    hoje_data = date.today()
    data_corte_vencimento = date(2025, 9, 1)
    
    for cartao in cartoes:
        # Calcular estimativa atual
        valor_previsto_atual = 0.0
        data_proxima_fatura = None
        status_fatura = None
        fatura_paga_mes_atual = False
        valor_fatura_pago = None
        
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
                        break
        
        # Verificar se existe fatura confirmada e paga para o mês atual
        hoje = date.today()
        faturas_confirmadas = db.query(Fatura).filter(
            Fatura.cartao_id == cartao.id,
            Fatura.status == "confirmada"
        ).all()
        for f in faturas_confirmadas:
            # Fatura vinculada a uma conta
            conta_fatura = db.query(Conta).filter(Conta.id == f.conta_id).first() if f.conta_id else None
            if conta_fatura and conta_fatura.status == 'pago':
                # Considerar mês/ano do vencimento como referência para "mês atual" de pagamento
                if f.data_vencimento.year == hoje.year and f.data_vencimento.month == hoje.month:
                    fatura_paga_mes_atual = True
                    valor_fatura_pago = conta_fatura.valor_pago or conta_fatura.valor
                    status_fatura = 'paga'
                    break

        # Criar objeto com estimativa
        cartao_dict = {
            "id": cartao.id,
            "nome": cartao.nome,
            "bandeira": cartao.bandeira,
            "limite": cartao.limite,
            "dia_fechamento": cartao.dia_fechamento,
            "dia_vencimento": cartao.dia_vencimento,
            "ativo": cartao.ativo,
            "created_at": cartao.created_at,
            "updated_at": cartao.updated_at,
            "valor_previsto_atual": valor_previsto_atual,
            "data_proxima_fatura": data_proxima_fatura,
            "status_fatura": status_fatura,
            "fatura_paga_mes_atual": fatura_paga_mes_atual,
            "valor_fatura_pago": sanitize_float(valor_fatura_pago) if valor_fatura_pago is not None else None
        }
        
        cartoes_com_estimativa.append(cartao_dict)
    
    return cartoes_com_estimativa

@app.get("/cartoes/resumo-faturas")
def resumo_faturas_cartoes(
    meses: int = 6,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Resumo mensal de valores de faturas pagas e pendentes (vencidas) para os próximos N meses a partir do mês atual."""
    if meses < 1:
        meses = 1
    hoje = datetime.now()
    # Obter categoria de fatura de cartão
    categoria_fatura = db.query(Categoria).filter(Categoria.nome == "Fatura de Cartão").first()
    categoria_fatura_id = categoria_fatura.id if categoria_fatura else None

    resultado = []
    for i in range(0, meses):
        data_ref = hoje + relativedelta(months=i)
        ano = data_ref.year
        mes = data_ref.month

        # Total pago: contas da categoria fatura marcadas como pagas com data_vencimento no mês/ano
        total_pago = 0.0
        if categoria_fatura_id:
            contas_pagas = db.query(Conta).filter(
                Conta.categoria_id == categoria_fatura_id,
                Conta.status == "pago",
                extract('year', Conta.data_vencimento) == ano,
                extract('month', Conta.data_vencimento) == mes
            ).all()
            total_pago = sum(c.valor for c in contas_pagas if c.valor is not None) or 0.0

        # Faturas pendentes (status pendente) no mês/ano
        faturas_mes = db.query(Fatura).filter(
            extract('year', Fatura.data_vencimento) == ano,
            extract('month', Fatura.data_vencimento) == mes,
            Fatura.status == "pendente"
        ).all()

        # Separar vencidas (data_vencimento < hoje.date())
        pendente_vencido = 0.0
        for f in faturas_mes:
            if f.data_vencimento < hoje.date():
                pendente_vencido += f.valor_previsto or 0.0

        resultado.append({
            "mes": mes,
            "ano": ano,
            "mes_nome": data_ref.strftime("%b/%Y"),
            "valor_faturas_pagas": sanitize_float(total_pago),
            "valor_faturas_pendentes_vencidas": sanitize_float(pendente_vencido)
        })

    return resultado

@app.get("/cartoes/{cartao_id}/resumo-faturas")
def resumo_faturas_cartao_especifico(
    cartao_id: int,
    meses: int = 6,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Resumo mensal (por cartão) de valores de faturas pagas e pendentes (vencidas) para os próximos N meses a partir do mês atual."""
    if meses < 1:
        meses = 1
    hoje = datetime.now()
    cartao = db.query(Cartao).filter(Cartao.id == cartao_id).first()
    if not cartao:
        raise HTTPException(status_code=404, detail="Cartão não encontrado")

    # Categoria de fatura
    categoria_fatura = db.query(Categoria).filter(Categoria.nome == "Fatura de Cartão").first()
    categoria_fatura_id = categoria_fatura.id if categoria_fatura else None

    resultado = []
    for i in range(0, meses):
        data_ref = hoje + relativedelta(months=i)
        ano = data_ref.year
        mes = data_ref.month

        # Contas de fatura pagas deste cartão
        total_pago = 0.0
        if categoria_fatura_id:
            contas_pagas = db.query(Conta).join(Fatura, Fatura.conta_id == Conta.id, isouter=True).filter(
                Conta.categoria_id == categoria_fatura_id,
                Conta.status == 'pago',
                extract('year', Conta.data_vencimento) == ano,
                extract('month', Conta.data_vencimento) == mes,
                # Vinculadas a fatura que é deste cartão ou descrição contendo nome do cartão
                or_(Fatura.cartao_id == cartao_id, Conta.descricao.ilike(f"%{cartao.nome}%"))
            ).all()
            total_pago = sum(c.valor for c in contas_pagas if c.valor is not None) or 0.0

        # Faturas pendentes deste cartão para o mês
        faturas_mes = db.query(Fatura).filter(
            Fatura.cartao_id == cartao_id,
            extract('year', Fatura.data_vencimento) == ano,
            extract('month', Fatura.data_vencimento) == mes,
            Fatura.status == 'pendente'
        ).all()

        pendente_vencido = 0.0
        for f in faturas_mes:
            if f.data_vencimento < hoje.date():
                pendente_vencido += f.valor_previsto or 0.0

        resultado.append({
            'mes': mes,
            'ano': ano,
            'mes_nome': data_ref.strftime('%b/%Y'),
            'valor_faturas_pagas': sanitize_float(total_pago),
            'valor_faturas_pendentes_vencidas': sanitize_float(pendente_vencido)
        })

    return resultado

@app.post("/cartoes", response_model=CartaoResponse)
def criar_cartao(
    cartao: CartaoCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    db_cartao = Cartao(**cartao.dict())
    db.add(db_cartao)
    db.commit()
    db.refresh(db_cartao)
    return db_cartao

@app.put("/cartoes/{cartao_id}", response_model=CartaoResponse)
def atualizar_cartao(
    cartao_id: int,
    cartao_update: CartaoUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    db_cartao = db.query(Cartao).filter(Cartao.id == cartao_id).first()
    if not db_cartao:
        raise HTTPException(status_code=404, detail="Cartão não encontrado")
    for key, value in cartao_update.dict(exclude_unset=True).items():
        setattr(db_cartao, key, value)
    db.commit()
    db.refresh(db_cartao)
    return db_cartao

@app.delete("/cartoes/{cartao_id}")
def deletar_cartao(
    cartao_id: int,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    db_cartao = db.query(Cartao).filter(Cartao.id == cartao_id).first()
    if not db_cartao:
        raise HTTPException(status_code=404, detail="Cartão não encontrado")
    
    # Verificar se há contas associadas
    contas_associadas = db.query(Conta).filter(Conta.cartao_id == cartao_id).all()
    
    # Verificar se há faturas associadas
    faturas_associadas = db.query(Fatura).filter(Fatura.cartao_id == cartao_id).all()
    
    if (len(contas_associadas) > 0 or len(faturas_associadas) > 0) and not force:
        detalhes = []
        if len(contas_associadas) > 0:
            detalhes.append(f"{len(contas_associadas)} contas")
        if len(faturas_associadas) > 0:
            detalhes.append(f"{len(faturas_associadas)} faturas")
        
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível deletar o cartão. Existem {' e '.join(detalhes)} associadas a ele. Use force=true para deletar tudo."
        )
    
    # Se force=true, deletar todas as dependências primeiro
    if force:
        contas_deletadas = 0
        faturas_deletadas = 0
        
        # Deletar contas associadas
        for conta in contas_associadas:
            db.delete(conta)
            contas_deletadas += 1
        
        # Deletar faturas associadas
        for fatura in faturas_associadas:
            db.delete(fatura)
            faturas_deletadas += 1
        
        # Deletar o cartão
        db.delete(db_cartao)
        db.commit()
        
        message = f"Cartão '{db_cartao.nome}' deletado com sucesso"
        if contas_deletadas > 0 or faturas_deletadas > 0:
            detalhes_deletados = []
            if contas_deletadas > 0:
                detalhes_deletados.append(f"{contas_deletadas} contas")
            if faturas_deletadas > 0:
                detalhes_deletados.append(f"{faturas_deletadas} faturas")
            message += f" junto com {' e '.join(detalhes_deletados)}"
        
        return {
            "message": message,
            "contas_deletadas": contas_deletadas,
            "faturas_deletadas": faturas_deletadas
        }
    else:
        # Caso não haja dependências, deletar normalmente
        db.delete(db_cartao)
        db.commit()
        return {"message": f"Cartão '{db_cartao.nome}' deletado com sucesso"}

# Helpers de fatura
def calcular_ciclo_fatura(referencia: date, dia_fechamento: int, dia_vencimento: int):
    """
    Calcula o ciclo de fatura do cartão de crédito.
    
    Regras:
    - Se dia_vencimento > dia_fechamento: vencimento no mesmo mês do fechamento
    - Se dia_vencimento <= dia_fechamento: vencimento no mês seguinte ao fechamento
    
    Exemplo: fechamento dia 25, vencimento dia 1
    - Fechamento 25/09 -> Vencimento 01/10
    """
    from calendar import monthrange
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

def limpar_faturas_antigas(db: Session):
    """
    Remove faturas antigas que vencem antes do mês de corte (setembro/2025)
    """
    data_corte = date(2025, 9, 1)
    faturas_removidas = db.query(Fatura).filter(Fatura.data_vencimento < data_corte).delete(synchronize_session=False)
    db.commit()
    if faturas_removidas > 0:
        print(f"Removidas {faturas_removidas} faturas antigas (vencimento anterior a {data_corte})")
    return faturas_removidas

# Helper: verifica se a fatura (conta de fatura confirmada/paga) de um cartão para ano/mes está paga
def fatura_mes_paga(db: Session, cartao_id: int, ano: int, mes: int) -> bool:
    fatura = db.query(Fatura).filter(
        Fatura.cartao_id == cartao_id,
        extract('year', Fatura.data_vencimento) == ano,
        extract('month', Fatura.data_vencimento) == mes,
        Fatura.conta_id != None
    ).first()
    if not fatura:
        return False
    conta_fatura = db.query(Conta).filter(Conta.id == fatura.conta_id, Conta.status == 'pago').first()
    return conta_fatura is not None

@app.get("/cartoes/faturas/pendentes", response_model=List[FaturaResponse])
def listar_faturas_pendentes(
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    hoje_data = date.today()
    faturas_pendentes: List[Fatura] = []
    cartoes = db.query(Cartao).filter(Cartao.ativo == True).all()
    
    # Data de corte: considerar apenas faturas que vencem a partir de setembro/2025
    data_corte_vencimento = date(2025, 9, 1)
    
    for c in cartoes:
        if not c.dia_fechamento or not c.dia_vencimento:
            continue
            
        # Verificar TODOS os ciclos que precisam de alerta
        # 1. Ciclo atual (se já fechou e não foi confirmado)
        # 2. Ciclos anteriores vencidos (se não foram confirmados)
        
        # Calcular até 3 meses para trás para capturar ciclos pendentes
        for meses_atras in range(0, 4):
            data_referencia = hoje_data - relativedelta(months=meses_atras)
            inicio, fim, fechamento, vencimento = calcular_ciclo_fatura(data_referencia, c.dia_fechamento, c.dia_vencimento)
            
            # FILTRO: Ignorar faturas que vencem antes de setembro/2025
            if vencimento < data_corte_vencimento:
                continue
            
            # Mostrar alerta se:
            # - O fechamento já passou (fechamento <= hoje)
            # - E ainda não passou muito tempo do vencimento (máximo 1 mês após vencimento)
            limite_alerta = vencimento + relativedelta(months=1)
            
            if fechamento <= hoje_data <= limite_alerta:
                # Buscar/Calcular valor previsto: somar contas do cartão no período
                contas_periodo = db.query(Conta).filter(
                    Conta.cartao_id == c.id,
                    Conta.data_vencimento >= inicio,
                    Conta.data_vencimento <= fim
                ).all()
                valor_previsto = sum(ct.valor for ct in contas_periodo) or 0.0
                
                # Verificar se já existe fatura para este período
                fatura = db.query(Fatura).filter(
                    Fatura.cartao_id == c.id,
                    Fatura.periodo_inicio == inicio,
                    Fatura.periodo_fim == fim
                ).first()
                
                if not fatura:
                    fatura = Fatura(
                        cartao_id=c.id,
                        periodo_inicio=inicio,
                        periodo_fim=fim,
                        data_fechamento=fechamento,
                        data_vencimento=vencimento,
                        valor_previsto=valor_previsto,
                        status="pendente"
                    )
                    db.add(fatura)
                    db.flush()
                else:
                    # Atualizar valores calculados para garantir consistência
                    fatura.valor_previsto = valor_previsto
                    fatura.periodo_inicio = inicio
                    fatura.periodo_fim = fim
                    fatura.data_fechamento = fechamento
                    fatura.data_vencimento = vencimento
                
                # Incluir no alerta apenas se ainda não confirmada
                if fatura.status != "confirmada":
                    # Verificar se já está na lista (evitar duplicatas)
                    if not any(f.id == fatura.id for f in faturas_pendentes if hasattr(f, 'id')):
                        faturas_pendentes.append(fatura)
    
    db.commit()
    return faturas_pendentes

@app.delete("/cartoes/faturas/antigas")
def limpar_faturas_antigas_endpoint(
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """
    Remove faturas antigas que vencem antes de setembro/2025
    """
    data_corte = date(2025, 9, 1)
    faturas_removidas = db.query(Fatura).filter(Fatura.data_vencimento < data_corte).delete(synchronize_session=False)
    db.commit()
    
    return {
        "message": f"Limpeza concluída",
        "faturas_removidas": faturas_removidas,
        "data_corte": data_corte.isoformat()
    }

@app.post("/cartoes/faturas/{fatura_id}/confirmar", response_model=FaturaResponse)
def confirmar_fatura(
    fatura_id: int,
    body: FaturaConfirmRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    fatura = db.query(Fatura).filter(Fatura.id == fatura_id).first()
    if not fatura:
        raise HTTPException(status_code=404, detail="Fatura não encontrada")
    if fatura.status == "confirmada":
        return fatura
    # Criar conta nas contas a pagar referente à fatura
    cartao = db.query(Cartao).filter(Cartao.id == fatura.cartao_id).first()
    if not cartao:
        raise HTTPException(status_code=400, detail="Cartão inválido na fatura")
    descricao = f"Fatura Cartão {cartao.nome} - {fatura.data_vencimento.strftime('%m/%Y')}"
    # Garantir categoria apropriada para faturas
    categoria_fatura = db.query(Categoria).filter(Categoria.nome == "Fatura de Cartão").first()
    if not categoria_fatura:
        categoria_fatura = Categoria(nome="Fatura de Cartão", ativo=True)
        db.add(categoria_fatura)
        db.flush()
    conta = Conta(
        descricao=descricao,
        valor=body.valor_real,
        data_vencimento=fatura.data_vencimento,
        categoria_id=categoria_fatura.id,
        forma_pagamento="Boleto",
        status="pendente",
        observacoes="Fatura confirmada pelo usuário"
    )
    db.add(conta)
    db.flush()
    fatura.valor_real = body.valor_real
    fatura.status = "confirmada"
    fatura.conta_id = conta.id
    db.commit()
    db.refresh(fatura)
    return fatura

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
    cartao_id: Optional[int] = None,
    excluir_compras_cartao: Optional[bool] = False,
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
    # Filtro por cartão (usado na nova tela de abas de cartões)
    if cartao_id:
        query = query.filter(Conta.cartao_id == cartao_id)
    # Filtro opcional para excluir compras pagas no cartão (mantém faturas)
    if excluir_compras_cartao:
        query = query.filter(
            or_(
                Categoria.nome == "Fatura de Cartão",
                and_(
                    Conta.cartao_id == None,
                    or_(
                        Conta.forma_pagamento == None,
                        not_(
                            or_(
                                Conta.forma_pagamento.ilike('%cartao%'),
                                Conta.forma_pagamento.ilike('%cartão%')
                            )
                        )
                    )
                )
            )
        )
    
    contas = query.offset(skip).limit(limit).all()
    return contas

@app.get("/contas/resumo-meses")
def resumo_meses_contas(
    meses: int = 6,
    excluir_compras_cartao: bool = False,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Resumo agregado dos próximos N meses (a partir do mês atual) com valores:
    - previsto: soma de valor_previsto (fallback valor)
    - pago: soma de valor_pago (fallback valor) para status=pago
    - vencido: soma de valor (status=vencido)
    Opcionalmente aplica a mesma regra de exclusão de compras de cartão (excluir_compras_cartao=true)
    que a listagem de contas usa (mantendo faturas de cartão).
    """
    if meses < 1:
        meses = 1
    hoje = datetime.now()
    resultado = []
    for i in range(meses):
        data_ref = hoje + relativedelta(months=i)
        mes = data_ref.month
        ano = data_ref.year
        query = db.query(Conta).join(Categoria).filter(
            extract('month', Conta.data_vencimento) == mes,
            extract('year', Conta.data_vencimento) == ano
        )
        if excluir_compras_cartao:
            query = query.filter(
                or_(
                    Categoria.nome == "Fatura de Cartão",
                    and_(
                        Conta.cartao_id == None,
                        or_(
                            Conta.forma_pagamento == None,
                            not_(
                                or_(
                                    Conta.forma_pagamento.ilike('%cartao%'),
                                    Conta.forma_pagamento.ilike('%cartão%')
                                )
                            )
                        )
                    )
                )
            )
        contas_mes: List[Conta] = query.all()
        previsto = 0.0
        pago = 0.0
        vencido = 0.0
        for c in contas_mes:
            previsto += (c.valor_previsto if c.valor_previsto is not None else c.valor or 0.0) or 0.0
            if c.status == 'pago':
                pago += (c.valor_pago if c.valor_pago is not None else c.valor or 0.0) or 0.0
            if c.status == 'vencido':
                vencido += c.valor or 0.0
        resultado.append({
            'mes': mes,
            'ano': ano,
            'mes_nome': data_ref.strftime('%m/%Y'),
            'valor_previsto': sanitize_float(previsto),
            'valor_pago': sanitize_float(pago),
            'valor_vencido': sanitize_float(vencido)
        })
    return resultado

@app.get("/contas/vencem-hoje", response_model=List[ContaResponse])
def listar_contas_vencem_hoje(
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    hoje_data = date.today()
    # Incluir faturas e excluir compras no cartão, somente pendentes com vencimento hoje
    query = db.query(Conta).join(Categoria).filter(
        Conta.status == "pendente",
        Conta.data_vencimento == hoje_data,
        or_(
            Categoria.nome == "Fatura de Cartão",
            and_(
                Conta.cartao_id == None,
                or_(
                    Conta.forma_pagamento == None,
                    not_(
                        or_(
                            Conta.forma_pagamento.ilike('%cartao%'),
                            Conta.forma_pagamento.ilike('%cartão%')
                        )
                    )
                )
            )
        )
    ).order_by(Conta.valor.desc())
    return query.all()

@app.post("/contas", response_model=List[ContaResponse])
def criar_conta(
    conta: ContaCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    contas_criadas = []
    
    # Se é conta recorrente, criar para os próximos 6 meses
    if conta.eh_recorrente:
        # Gerar ID único para agrupar as contas recorrentes
        grupo_id = str(uuid.uuid4())
        
        # Criar 6 contas mensais (incluindo a atual)
        for i in range(6):
            # Calcular data de vencimento (mês atual + i meses)
            data_vencimento = conta.data_vencimento + relativedelta(months=i)
            
            # Criar descrição com mês/ano
            nome_mes = data_vencimento.strftime("%m/%Y")
            descricao_recorrente = f"{conta.descricao} - {nome_mes}"
            
            db_conta = Conta(
                descricao=descricao_recorrente,
                valor=conta.valor,
                data_vencimento=data_vencimento,
                categoria_id=conta.categoria_id,
                cartao_id=conta.cartao_id,
                forma_pagamento=conta.forma_pagamento,
                observacoes=conta.observacoes,
                eh_recorrente=True,
                grupo_recorrencia=grupo_id,
                valor_previsto=conta.valor,  # Salvar valor original como previsto
                status="pendente"
            )
            
            db.add(db_conta)
            contas_criadas.append(db_conta)
        
        db.commit()
        
        # Atualizar as contas criadas com os IDs
        for conta_criada in contas_criadas:
            db.refresh(conta_criada)
        
        return contas_criadas
    
    # Se não é parcelado nem recorrente, criar conta única
    if not conta.eh_parcelado or not conta.parcelas_restantes or not conta.total_parcelas:
        db_conta = Conta(
            descricao=conta.descricao,
            valor=conta.valor,
            data_vencimento=conta.data_vencimento,
            categoria_id=conta.categoria_id,
            cartao_id=conta.cartao_id,
            forma_pagamento=conta.forma_pagamento,
            observacoes=conta.observacoes,
            eh_parcelado=conta.eh_parcelado or False,
            numero_parcela=conta.numero_parcela,
            total_parcelas=conta.total_parcelas,
            valor_total=conta.valor_total,
            grupo_parcelamento=conta.grupo_parcelamento,
            eh_recorrente=conta.eh_recorrente or False,
            grupo_recorrencia=conta.grupo_recorrencia,
            valor_previsto=conta.valor_previsto,
            status="pendente"
        )
        db.add(db_conta)
        db.commit()
        db.refresh(db_conta)
        return [db_conta]
    
    # Se é parcelado, criar múltiplas contas (lógica existente)
    if conta.parcelas_restantes and conta.total_parcelas:
        # Gerar ID único para agrupar as parcelas
        grupo_id = str(uuid.uuid4())
        
        # Calcular parcela atual
        parcela_atual = conta.total_parcelas - conta.parcelas_restantes + 1
        
        # Valor total da compra (se não informado, usar valor * total_parcelas)
        valor_total_compra = conta.valor_total or (conta.valor * conta.total_parcelas)
        
        # Criar TODAS as parcelas (anteriores + restantes)
        for numero_parcela in range(1, conta.total_parcelas + 1):
            meses_diferenca = numero_parcela - parcela_atual
            data_vencimento = conta.data_vencimento + relativedelta(months=meses_diferenca)

            status_parcela = "pendente"
            data_pagamento = None
            if numero_parcela < parcela_atual:
                status_parcela = "pago"
                data_pagamento = data_vencimento
            elif numero_parcela == parcela_atual:
                # Parcela correspondente ao "momento" atual. Se a fatura deste mes já foi paga, marcar paga.
                if conta.cartao_id and fatura_mes_paga(db, conta.cartao_id, data_vencimento.year, data_vencimento.month):
                    status_parcela = "pago"
                    data_pagamento = date.today()
            # Futuras permanecem pendentes
            
            # Criar descrição com número da parcela
            descricao_parcela = f"{conta.descricao} - Parcela {numero_parcela}/{conta.total_parcelas}"
            
            db_conta = Conta(
                descricao=descricao_parcela,
                valor=conta.valor,
                data_vencimento=data_vencimento,
                data_pagamento=data_pagamento,
                categoria_id=conta.categoria_id,
                cartao_id=conta.cartao_id,
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
    print(f"DEBUG: Atualizando conta {conta_id}")  # Debug
    print(f"DEBUG: Dados recebidos: {conta_update.dict(exclude_unset=True)}")  # Debug
    
    conta = db.query(Conta).filter(Conta.id == conta_id).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    
    print(f"DEBUG: Conta atual eh_parcelado: {conta.eh_parcelado}")  # Debug
    print(f"DEBUG: Novo eh_parcelado: {conta_update.eh_parcelado}")  # Debug
    
    # Verificar se está sendo marcada como parcelada
    if conta_update.eh_parcelado and not conta.eh_parcelado:
        print("DEBUG: Iniciando processo de parcelamento")  # Debug
        
        # Está sendo transformada em conta parcelada
        if not conta_update.total_parcelas or not conta_update.parcelas_restantes:
            print("DEBUG: Faltam dados para parcelamento")  # Debug
            raise HTTPException(
                status_code=400, 
                detail="Para tornar uma conta parcelada, é necessário informar total_parcelas e parcelas_restantes"
            )
        
        print(f"DEBUG: Total parcelas: {conta_update.total_parcelas}, Restantes: {conta_update.parcelas_restantes}")  # Debug
        
        # Gerar ID único para agrupar as parcelas
        grupo_id = str(uuid.uuid4())
        
        # Calcular parcela atual
        parcela_atual = conta_update.total_parcelas - conta_update.parcelas_restantes + 1
        print(f"DEBUG: Parcela atual calculada: {parcela_atual}")  # Debug
        
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
            meses_diferenca = numero_parcela - parcela_atual
            data_vencimento = conta.data_vencimento + relativedelta(months=meses_diferenca)

            if numero_parcela == parcela_atual:
                # Atualizar a conta existente (parcela atual) e decidir status conforme fatura
                if conta.cartao_id and fatura_mes_paga(db, conta.cartao_id, data_vencimento.year, data_vencimento.month):
                    conta.status = "pago"
                    conta.data_pagamento = data_vencimento
                continue

            # Determinar status
            status_parcela = "pendente"
            data_pagamento = None
            if numero_parcela < parcela_atual:
                status_parcela = "pago"
                data_pagamento = data_vencimento
            
            # Criar descrição com número da parcela
            descricao_original = conta.descricao.split(" - Parcela")[0]  # Remove sufixo se já existir
            descricao_parcela = f"{descricao_original} - Parcela {numero_parcela}/{conta_update.total_parcelas}"
            
            nova_conta = Conta(
                descricao=descricao_parcela,
                valor=conta.valor,
                data_vencimento=data_vencimento,
                data_pagamento=data_pagamento,
                categoria_id=conta.categoria_id,
                cartao_id=conta.cartao_id,
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
        
        print(f"DEBUG: Criadas {len(contas_criadas)} parcelas")  # Debug
        
        conta.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(conta)
        
        print("DEBUG: Parcelamento concluído com sucesso")  # Debug
        
        # Retornar apenas a conta atualizada (compatível com ContaResponse)
        return conta
    
    # Verificar se está sendo marcada como recorrente
    if conta_update.eh_recorrente and not conta.eh_recorrente:
        print("DEBUG: Iniciando processo de criação de contas recorrentes")  # Debug
        
        # Gerar ID único para agrupar as contas recorrentes
        grupo_id = str(uuid.uuid4())
        
        # Atualizar a conta atual para ser recorrente
        conta.eh_recorrente = True
        conta.grupo_recorrencia = grupo_id
        conta.valor_previsto = conta.valor  # Valor previsto = valor atual
        
        # Criar 5 contas adicionais (próximos 5 meses) - total 6 meses
        contas_criadas = []
        for mes in range(1, 6):  # 1 a 5 meses no futuro
            data_vencimento = conta.data_vencimento + relativedelta(months=mes)
            
            # Criar descrição com mês/ano
            descricao_recorrente = f"{conta.descricao} - {data_vencimento.strftime('%m/%Y')}"
            
            nova_conta = Conta(
                descricao=descricao_recorrente,
                valor=conta.valor,
                data_vencimento=data_vencimento,
                categoria_id=conta.categoria_id,
                cartao_id=conta.cartao_id,
                forma_pagamento=conta.forma_pagamento,
                observacoes=conta.observacoes,
                eh_recorrente=True,
                grupo_recorrencia=grupo_id,
                valor_previsto=conta.valor,
                status="pendente"
            )
            
            db.add(nova_conta)
            contas_criadas.append(nova_conta)
        
        print(f"DEBUG: Criadas {len(contas_criadas)} contas recorrentes")  # Debug
        
        conta.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(conta)
        
        print("DEBUG: Contas recorrentes criadas com sucesso")  # Debug
        
        # Retornar apenas a conta atualizada (compatível com ContaResponse)
        return conta
    
    print("DEBUG: Atualização normal (não parcelamento nem recorrente)")  # Debug
    
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

@app.get("/contas/recorrencia/{grupo_id}", response_model=List[ContaResponse])
def obter_contas_recorrentes_por_grupo(
    grupo_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Buscar todas as contas de um grupo de recorrência"""
    contas = db.query(Conta).filter(
        Conta.grupo_recorrencia == grupo_id
    ).order_by(Conta.data_vencimento).all()
    
    if not contas:
        raise HTTPException(status_code=404, detail="Grupo de contas recorrentes não encontrado")
    
    return contas

@app.delete("/contas")
def deletar_todas_as_contas(
    confirm: bool = False,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Exclui todas as contas do sistema. Requer confirm=true na query string."""
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirme a exclusão passando confirm=true")

    try:
        # Antes de deletar, reverter todas as faturas confirmadas para pendente
        categoria_fatura = db.query(Categoria).filter(Categoria.nome == "Fatura de Cartão").first()
        faturas_revertidas = 0
        
        if categoria_fatura:
            # Buscar todas as contas de fatura que serão deletadas
            contas_fatura = db.query(Conta).filter(Conta.categoria_id == categoria_fatura.id).all()
            
            for conta_fatura in contas_fatura:
                # Buscar fatura vinculada e reverter
                fatura = db.query(Fatura).filter(Fatura.conta_id == conta_fatura.id).first()
                if fatura:
                    fatura.status = "pendente"
                    fatura.conta_id = None
                    fatura.valor_real = None
                    faturas_revertidas += 1
        
        # Deletar todas as contas
        deletadas = db.query(Conta).delete(synchronize_session=False)
        db.commit()
        
        message = f"{deletadas} contas deletadas com sucesso"
        if faturas_revertidas > 0:
            message += f" e {faturas_revertidas} faturas revertidas para status pendente"
        
        return {"message": message, "faturas_revertidas": faturas_revertidas}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao deletar contas: {str(e)}")

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
    
    # Verificar se esta conta é de uma fatura de cartão confirmada
    fatura_vinculada = None
    categoria_fatura = db.query(Categoria).filter(Categoria.nome == "Fatura de Cartão").first()
    
    if categoria_fatura and conta.categoria_id == categoria_fatura.id:
        # Buscar a fatura que criou esta conta
        fatura_vinculada = db.query(Fatura).filter(Fatura.conta_id == conta_id).first()
    
    # Se a conta é parcelada e o usuário quer deletar todas as parcelas
    if conta.eh_parcelado and conta.grupo_parcelamento and deletar_todas_parcelas:
        # Deletar todas as contas do mesmo grupo de parcelamento
        contas_grupo = db.query(Conta).filter(Conta.grupo_parcelamento == conta.grupo_parcelamento).all()
        for conta_parcela in contas_grupo:
            db.delete(conta_parcela)
        db.commit()
        return {"message": f"Todas as {len(contas_grupo)} parcelas foram deletadas com sucesso"}
    else:
        # Reverter fatura para status pendente se for uma conta de fatura
        if fatura_vinculada:
            fatura_vinculada.status = "pendente"
            fatura_vinculada.conta_id = None
            fatura_vinculada.valor_real = None
            print(f"Fatura ID {fatura_vinculada.id} revertida para status pendente")
        
        # Deletar apenas a conta específica
        db.delete(conta)
        db.commit()
        
        if fatura_vinculada:
            return {
                "message": "Conta deletada com sucesso", 
                "fatura_revertida": True,
                "fatura_id": fatura_vinculada.id,
                "info": "A fatura voltará a aparecer nos alertas da dashboard"
            }
        else:
            return {"message": "Conta deletada com sucesso"}

class PagamentoRequest(BaseModel):
    data_pagamento: Optional[date] = None
    valor_pago: Optional[float] = None

@app.post("/contas/{conta_id}/pagar")
def marcar_como_pago(
    conta_id: int,
    pagamento: PagamentoRequest = PagamentoRequest(),
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    conta = db.query(Conta).filter(Conta.id == conta_id).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    # Detecta categoria fatura de cartão
    categoria_fatura = db.query(Categoria).filter(Categoria.nome == "Fatura de Cartão").first()
    eh_fatura = categoria_fatura and conta.categoria_id == categoria_fatura.id

    # Bloquear pagamento individual de compras de cartão (conta.cartao_id set) que NÃO sejam a conta de fatura
    if conta.cartao_id is not None and not eh_fatura:
        raise HTTPException(status_code=400, detail="Compras de cartão são liquidadas automaticamente ao pagar a fatura. Pague a fatura correspondente.")

    # Marcar a conta (fatura ou conta normal) como paga
    conta.status = "pago"
    conta.data_pagamento = pagamento.data_pagamento or date.today()

    if pagamento.valor_pago is not None:
        conta.valor_pago = pagamento.valor_pago
        if conta.valor_previsto is None:
            conta.valor_previsto = conta.valor
        conta.valor = pagamento.valor_pago
    else:
        conta.valor_pago = conta.valor

    # Se for fatura, localizar registro de fatura e marcar compras associadas como pagas
    if eh_fatura:
        fatura = db.query(Fatura).filter(Fatura.conta_id == conta.id).first()
        if fatura and fatura.status == "confirmada":
            compras = db.query(Conta).filter(
                Conta.cartao_id == fatura.cartao_id,
                Conta.data_vencimento >= fatura.periodo_inicio,
                Conta.data_vencimento <= fatura.periodo_fim,
                Conta.status != "pago"
            ).all()
            for compra in compras:
                compra.status = "pago"
                compra.data_pagamento = conta.data_pagamento
                if compra.valor_pago is None:
                    compra.valor_pago = compra.valor
                if compra.valor_previsto is None:
                    compra.valor_previsto = compra.valor
                compra.updated_at = datetime.utcnow()
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
    categoria_fatura = db.query(Categoria).filter(Categoria.nome == "Fatura de Cartão").first()
    eh_fatura = categoria_fatura and conta.categoria_id == categoria_fatura.id

    # Bloquear desmarcar pagamento individual de compras de cartão (somente via desfazer pagamento da fatura)
    if conta.cartao_id is not None and not eh_fatura:
        raise HTTPException(status_code=400, detail="Não é possível desmarcar individualmente compras de cartão. Reprocesse a fatura se necessário.")

    conta.status = "pendente"
    conta.data_pagamento = None
    if conta.valor_previsto is not None:
        conta.valor = conta.valor_previsto
    conta.valor_pago = None
    conta.updated_at = datetime.utcnow()

    # Se for fatura, reverter compras do período para pendente
    if eh_fatura:
        fatura = db.query(Fatura).filter(Fatura.conta_id == conta.id).first()
        if fatura and fatura.status == "confirmada":
            compras = db.query(Conta).filter(
                Conta.cartao_id == fatura.cartao_id,
                Conta.data_vencimento >= fatura.periodo_inicio,
                Conta.data_vencimento <= fatura.periodo_fim
            ).all()
            for compra in compras:
                # Só reverter compras que não sejam faturas e que estavam pagas
                if compra.status == "pago":
                    compra.status = "pendente"
                    compra.data_pagamento = None
                    if compra.valor_previsto is not None:
                        compra.valor = compra.valor_previsto
                    compra.valor_pago = None
                    compra.updated_at = datetime.utcnow()

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
    # Regra: incluir SEMPRE faturas (categoria "Fatura de Cartão");
    # para demais contas, incluir apenas quando NÃO são compras pagas no cartão
    # (sem cartao_id e forma_pagamento não contém "cartao").
    query_base = db.query(Conta).join(Categoria).filter(
        or_(
            Categoria.nome == "Fatura de Cartão",
            and_(
                Conta.cartao_id == None,
                or_(
                    Conta.forma_pagamento == None,
                    not_(
                        or_(
                            Conta.forma_pagamento.ilike('%cartao%'),
                            Conta.forma_pagamento.ilike('%cartão%')
                        )
                    )
                )
            )
        )
    )
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
        
        # Buscar contas do mês aplicando mesma regra de inclusão das demais rotas
        contas_mes = db.query(Conta).join(Categoria).filter(
            or_(
                Categoria.nome == "Fatura de Cartão",
                and_(
                    Conta.cartao_id == None,
                    or_(
                        Conta.forma_pagamento == None,
                        not_(
                            or_(
                                Conta.forma_pagamento.ilike('%cartao%'),
                                Conta.forma_pagamento.ilike('%cartão%')
                            )
                        )
                    )
                )
            ),
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
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    # Query base com mesma regra de inclusão
    query = db.query(Conta).join(Categoria).filter(
        or_(
            Categoria.nome == "Fatura de Cartão",
            and_(
                Conta.cartao_id == None,
                or_(
                    Conta.forma_pagamento == None,
                    not_(
                        or_(
                            Conta.forma_pagamento.ilike('%cartao%'),
                            Conta.forma_pagamento.ilike('%cartão%')
                        )
                    )
                )
            )
        )
    )
    
    # Aplicar filtros de mês e ano se fornecidos
    if mes is not None and ano is not None:
        query = query.filter(
            extract('month', Conta.data_vencimento) == mes,
            extract('year', Conta.data_vencimento) == ano
        )
    
    contas = query.all()
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

# Estimativa por cartão (próximos meses)
@app.get("/cartoes/{cartao_id}/estimativa")
def estimativa_cartao(
    cartao_id: int,
    meses: int = 6,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    if meses < 1:
        meses = 1
    hoje = datetime.now()
    estimativa = []
    for i in range(0, meses):
        data_mes = hoje + relativedelta(months=i)
        mes = data_mes.month
        ano = data_mes.year
        contas_mes = db.query(Conta).filter(
            Conta.cartao_id == cartao_id,
            extract('month', Conta.data_vencimento) == mes,
            extract('year', Conta.data_vencimento) == ano
        ).all()
        valor_previsto = sum(conta.valor for conta in contas_mes) or 0.0
        valor_pago = sum(conta.valor for conta in contas_mes if conta.status == "pago") or 0.0
        estimativa.append({
            "mes": mes,
            "ano": ano,
            "mes_nome": data_mes.strftime("%b/%Y"),
            "valor_previsto": sanitize_float(valor_previsto),
            "valor_pago": sanitize_float(valor_pago),
            "quantidade_itens": len(contas_mes)
        })
    return estimativa

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
        
        # Tentar diferentes engines para ler o Excel
        try:
            # Primeiro tenta com openpyxl (para .xlsx)
            df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
        except Exception as e1:
            try:
                # Se falhar, tenta com xlrd (para .xls)
                df = pd.read_excel(io.BytesIO(contents), engine='xlrd')
            except Exception as e2:
                # Se ambos falharem, reporta o erro
                raise HTTPException(
                    status_code=400,
                    detail=f"Erro ao ler arquivo Excel. Verifique se o arquivo não está corrompido. Erro original: {str(e1)}"
                )
        
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