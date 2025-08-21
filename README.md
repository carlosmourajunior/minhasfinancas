# Sistema de Controle de Contas

Sistema completo para gerenciar contas a pagar, desenvolvido com **Python (FastAPI)**, **React (Material-UI)** e **Docker**.

## 🚀 Características

- ✅ **Backend REST API** com FastAPI e PostgreSQL
- ✅ **Frontend responsivo** com React e Material-UI
- ✅ **Autenticação JWT** segura
- ✅ **Interface moderna** e intuitiva
- ✅ **Relatórios visuais** com gráficos
- ✅ **Dockerizado** para fácil deployment
- ✅ **Gerenciamento completo** de contas a pagar
- ✅ **Categorização** de gastos
- ✅ **Dashboard** com métricas importantes

## 📋 Funcionalidades

### Dashboard
- Resumo visual das contas (pendentes, pagas, vencidas)
- Valor total pendente
- Cards informativos com status coloridos

### Gestão de Contas
- ➕ Criar novas contas
- ✏️ Editar contas existentes
- 🗑️ Deletar contas
- 💰 Marcar como pago
- 📊 Visualizar em tabela dinâmica
- 🏷️ Categorização por tipo

### Relatórios
- 📈 Gráfico de barras por categoria
- 🥧 Gráfico de pizza da distribuição
- 📋 Tabela de resumo detalhado

### Autenticação
- 🔐 Login seguro
- 👤 Registro de usuários
- 🔑 JWT tokens

## 🛠️ Tecnologias

### Backend
- **FastAPI** - Framework web moderno e rápido
- **SQLAlchemy** - ORM para Python
- **PostgreSQL** - Banco de dados
- **JWT** - Autenticação
- **Pydantic** - Validação de dados

### Frontend
- **React 18** - Biblioteca UI
- **Material-UI (MUI)** - Componentes de design
- **TypeScript** - Tipagem estática
- **Axios** - Cliente HTTP
- **Recharts** - Gráficos
- **Day.js** - Manipulação de datas

### DevOps
- **Docker** - Containerização
- **Docker Compose** - Orquestração

## 🏃‍♂️ Como Executar

### Pré-requisitos
- Docker e Docker Compose instalados
- Git

### 1. Clone o repositório
```bash
git clone <url-do-repositorio>
cd App-ContaAPagar
```

### 2. Execute com Docker Compose
```bash
docker-compose up --build
```

### 3. Acesse a aplicação
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Documentação da API**: http://localhost:8000/docs

## 🗂️ Estrutura do Projeto

```
App-ContaAPagar/
├── backend/                 # API Python FastAPI
│   ├── main.py             # Aplicação principal
│   ├── requirements.txt    # Dependências Python
│   └── Dockerfile         # Container do backend
├── frontend/               # Aplicação React
│   ├── src/
│   │   ├── components/    # Componentes reutilizáveis
│   │   ├── pages/        # Páginas da aplicação
│   │   ├── services/     # Serviços e contextos
│   │   ├── App.tsx       # Componente principal
│   │   └── index.tsx     # Ponto de entrada
│   ├── package.json      # Dependências Node.js
│   └── Dockerfile       # Container do frontend
├── docker-compose.yml    # Orquestração dos serviços
└── README.md            # Documentação
```

## 📊 API Endpoints

### Autenticação
- `POST /auth/register` - Registrar usuário
- `POST /auth/login` - Login

### Contas
- `GET /contas` - Listar contas
- `POST /contas` - Criar conta
- `GET /contas/{id}` - Obter conta
- `PUT /contas/{id}` - Atualizar conta
- `DELETE /contas/{id}` - Deletar conta
- `POST /contas/{id}/pagar` - Marcar como pago

### Relatórios
- `GET /relatorios/resumo` - Resumo geral
- `GET /relatorios/categorias` - Relatório por categoria

## 🎨 Interface

O sistema utiliza **Material Design** através do Material-UI, oferecendo:

- 📱 **Design responsivo** para desktop e mobile
- 🎨 **Tema consistente** com cores profissionais
- ⚡ **Navegação fluida** entre as páginas
- 📊 **Gráficos interativos** para visualização de dados
- 🔔 **Feedback visual** para ações do usuário

## 🔧 Desenvolvimento

### Backend Local
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Local
```bash
cd frontend
npm install
npm start
```

### Banco de Dados
O PostgreSQL é configurado automaticamente via Docker com:
- **Usuário**: admin
- **Senha**: admin123
- **Database**: contas_db
- **Porta**: 5432

## 📝 Próximas Funcionalidades

- [ ] Importação de dados do Excel
- [ ] Notificações de vencimento
- [ ] Backup automático
- [ ] Relatórios em PDF
- [ ] Filtros avançados
- [ ] API para integração

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT.

---

**Desenvolvido com ❤️ para facilitar o controle de suas finanças!**