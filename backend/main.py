from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, validator
from datetime import datetime, date
from typing import List, Optional
import os
import pandas as pd
from passlib.context import CryptContext
import jwt as PyJWT

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

# Modelos do banco de dados
class Conta(Base):
    __tablename__ = "contas"
    
    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String, nullable=False)
    valor = Column(Float, nullable=False)
    data_vencimento = Column(Date, nullable=False)
    data_pagamento = Column(Date, nullable=True)
    categoria = Column(String, nullable=False)
    cartao = Column(String, nullable=True)
    status = Column(String, default="pendente")  # pendente, pago, vencido
    observacoes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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

# Schemas Pydantic
class ContaBase(BaseModel):
    descricao: str
    valor: float
    data_vencimento: date
    categoria: str
    cartao: Optional[str] = None
    observacoes: Optional[str] = None

class ContaCreate(ContaBase):
    pass

class ContaUpdate(BaseModel):
    descricao: Optional[str] = None
    valor: Optional[float] = None
    data_vencimento: Optional[date] = None
    data_pagamento: Optional[date] = None
    categoria: Optional[str] = None
    cartao: Optional[str] = None
    status: Optional[str] = None
    observacoes: Optional[str] = None

class ContaResponse(ContaBase):
    id: int
    data_pagamento: Optional[date] = None
    status: str
    created_at: datetime
    updated_at: datetime
    
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

# Rotas das contas
@app.get("/contas", response_model=List[ContaResponse])
def listar_contas(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    categoria: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    query = db.query(Conta)
    
    if status:
        query = query.filter(Conta.status == status)
    if categoria:
        query = query.filter(Conta.categoria == categoria)
    
    contas = query.offset(skip).limit(limit).all()
    return contas

@app.post("/contas", response_model=ContaResponse)
def criar_conta(
    conta: ContaCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    db_conta = Conta(**conta.dict())
    db.add(db_conta)
    db.commit()
    db.refresh(db_conta)
    return db_conta

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
    
    update_data = conta_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(conta, field, value)
    
    conta.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(conta)
    return conta

@app.delete("/contas/{conta_id}")
def deletar_conta(
    conta_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    conta = db.query(Conta).filter(Conta.id == conta_id).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    
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

# Rotas de relatórios
@app.get("/relatorios/resumo")
def resumo_contas(
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    total_pendente = db.query(Conta).filter(Conta.status == "pendente").count()
    total_pago = db.query(Conta).filter(Conta.status == "pago").count()
    total_vencido = db.query(Conta).filter(
        Conta.status == "pendente",
        Conta.data_vencimento < date.today()
    ).count()
    
    valor_pendente = db.query(Conta).filter(Conta.status == "pendente").all()
    valor_total_pendente = sum(conta.valor for conta in valor_pendente)
    
    return {
        "total_pendente": total_pendente,
        "total_pago": total_pago,
        "total_vencido": total_vencido,
        "valor_total_pendente": valor_total_pendente
    }

@app.get("/relatorios/categorias")
def relatorio_por_categoria(
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    contas = db.query(Conta).all()
    categorias = {}
    
    for conta in contas:
        if conta.categoria not in categorias:
            categorias[conta.categoria] = {"total": 0, "pendente": 0, "pago": 0}
        
        categorias[conta.categoria]["total"] += conta.valor
        if conta.status == "pendente":
            categorias[conta.categoria]["pendente"] += conta.valor
        else:
            categorias[conta.categoria]["pago"] += conta.valor
    
    return categorias

# Rota para importar dados do Excel
@app.post("/importar-excel")
def importar_excel(
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    # Esta rota seria implementada para ler o arquivo Excel
    # Por enquanto, retorna uma mensagem
    return {"message": "Funcionalidade de importação será implementada"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)