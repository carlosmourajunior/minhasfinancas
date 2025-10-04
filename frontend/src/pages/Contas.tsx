import React, { useState, useEffect, useCallback, ChangeEvent, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Chip,
  FormControlLabel,
  Checkbox,
  Grid,
  FormControl,
  InputLabel,
  Select,
} from '@mui/material';
import { Tooltip, Switch } from '@mui/material';
// Tipagem leve para evento do Select (evita depender de path interno de tipos)
type SimpleSelectChangeEvent = { target: { value: unknown } };
import TotalizadoresMeses, { TotalizadorValores, MesInfo } from '../components/TotalizadoresMeses';
import { DataGrid, GridColDef, GridActionsCellItem, GridRenderCellParams, GridRowParams, GridPaginationModel } from '@mui/x-data-grid';
import {
  Add,
  Edit,
  Delete,
  Payment,
  Undo,
  Warning,
  Download,
  AccountTree,
  Repeat,
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import dayjs from 'dayjs';
import axios from 'axios';

interface Categoria {
  id: number;
  nome: string;
  ativo: boolean;
}

interface Conta {
  id: number;
  descricao: string;
  valor: number;
  data_vencimento: string;
  data_pagamento?: string;
  categoria_id: number;
  categoria?: Categoria;
  cartao_id?: number;
  forma_pagamento?: string;
  status: string;
  observacoes?: string;
  // Campos de parcelamento
  eh_parcelado?: boolean;
  numero_parcela?: number;
  total_parcelas?: number;
  parcelas_restantes?: number;
  valor_total?: number;
  grupo_parcelamento?: string;
  // Campos de contas recorrentes
  eh_recorrente?: boolean;
  grupo_recorrencia?: string;
  valor_previsto?: number;
  valor_pago?: number;
}
interface Cartao {
  id: number;
  nome: string;
}

const Contas: React.FC = () => {
  const [contas, setContas] = useState<Conta[]>([]);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [cartoes, setCartoes] = useState<Cartao[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingConta, setEditingConta] = useState<Conta | null>(null);
  
  // Estados para o modal de exclusão
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [contaToDelete, setContaToDelete] = useState<number | null>(null);
  const [parcelamentoInfo, setParcelamentoInfo] = useState<any>(null);
  
  // Estados para o modal de importação
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  
  // Estados para filtros
  const [mesAno, setMesAno] = useState(dayjs()); // Mês/ano atual por padrão
  const [pageSize, setPageSize] = useState(() => {
    // Carregar preferência salva do localStorage ou usar 10 como padrão
    const saved = localStorage.getItem('contas-page-size');
    return saved ? Number(saved) : 10;
  }); // Quantidade de itens por página

  // Estados para modal de pagamento
  const [pagamentoDialogOpen, setPagamentoDialogOpen] = useState(false);
  const [contaParaPagar, setContaParaPagar] = useState<Conta | null>(null);
  const [valorPagamento, setValorPagamento] = useState('');

  // Estados para filtros
  const [filtroParceladas, setFiltroParceladas] = useState(false);
  const [filtroRecorrentes, setFiltroRecorrentes] = useState(false);
  const [excluirComprasCartao, setExcluirComprasCartao] = useState(false);

  // Totalizadores (mês atual + 5 próximos)
  interface MesResumo { key: string; label: string; mes: number; ano: number; }
  const meses: MesResumo[] = useMemo<MesResumo[]>(() => {
    const base = dayjs();
    return Array.from({ length: 6 }, (_: unknown, i: number) => {
      const d = base.add(i, 'month');
      return { key: `m_${d.year()}_${d.month() + 1}`, label: d.format('MM/YYYY'), mes: d.month() + 1, ano: d.year() } as MesResumo;
    });
  }, []);
  interface TotaisMes { previsto: number; pago: number; vencido: number; }
  const [totaisMeses, setTotaisMeses] = useState<Record<string, TotaisMes>>({});
  const [carregandoTotais, setCarregandoTotais] = useState(false);
  const [mostrarZeros, setMostrarZeros] = useState(false);
  
  const [formData, setFormData] = useState({
    descricao: '',
    valor: '',
    data_vencimento: dayjs(),
    categoria_id: '',
    cartao_id: '',
    forma_pagamento: '',
    observacoes: '',
    // Campos de parcelamento
    eh_parcelado: false,
    total_parcelas: '',
    parcelas_restantes: '',
    valor_total: '',
    // Campos de contas recorrentes
    eh_recorrente: false,
  });

  const formasPagamento = [
    'Boleto',
    'DDA',
    'PIX',
    'Cartão de Crédito',
    'Cartão de Débito',
    'Dinheiro',
    'Transferência Bancária',
    'Débito Automático',
  ];

  const fetchContas = useCallback(async () => {
    try {
      const params = {
        mes: mesAno.month() + 1, // dayjs months são 0-indexed
        ano: mesAno.year(),
        excluir_compras_cartao: excluirComprasCartao
      };
      
      const response = await axios.get('/contas', { params });
      setContas(response.data);
    } catch (error) {
      console.error('Erro ao carregar contas:', error);
    } finally {
      setLoading(false);
    }
  }, [mesAno, excluirComprasCartao]);

  const fetchCategorias = async () => {
    try {
      const response = await axios.get('/categorias');
      setCategorias(response.data);
    } catch (error) {
      console.error('Erro ao carregar categorias:', error);
    }
  };
  const fetchCartoes = async () => {
    try {
      const response = await axios.get('/cartoes');
      setCartoes(response.data);
    } catch (error) {
      console.error('Erro ao carregar cartões:', error);
    }
  };

  useEffect(() => {
    fetchCategorias();
    fetchCartoes();
    fetchContas();
  }, [fetchContas]); // Recarregar quando o filtro de mês/ano mudar

  // Carregar totalizadores via endpoint agregado /contas/resumo-meses
  useEffect(() => {
    const carregarTotais = async () => {
      setCarregandoTotais(true);
      try {
        const r = await axios.get('/contas/resumo-meses', { params: { meses: 6, excluir_compras_cartao: excluirComprasCartao } });
        const lista = r.data as { mes: number; ano: number; valor_previsto: number; valor_pago: number; valor_vencido: number }[];
        const base: Record<string, TotaisMes> = {};
        lista.forEach(item => {
          const key = `m_${item.ano}_${item.mes}`;
          base[key] = { previsto: item.valor_previsto || 0, pago: item.valor_pago || 0, vencido: item.valor_vencido || 0 };
        });
        // Garantir meses sem dados explícitos
        meses.forEach(m => { if(!base[m.key]) base[m.key] = { previsto:0, pago:0, vencido:0 }; });
        setTotaisMeses(base);
      } catch (err) {
        console.error('Erro ao carregar resumo meses', err);
      } finally {
        setCarregandoTotais(false);
      }
    };
    carregarTotais();
  }, [excluirComprasCartao, meses]);

  const handleSave = async () => {
    try {
      console.log('DEBUG: Estado formData antes de submeter:', formData); // Debug
      
      const data = {
        descricao: formData.descricao,
        valor: parseFloat(formData.valor),
        data_vencimento: formData.data_vencimento.format('YYYY-MM-DD'),
        categoria_id: parseInt(formData.categoria_id),
        cartao_id: formData.cartao_id ? parseInt(formData.cartao_id) : null,
        forma_pagamento: formData.forma_pagamento || null,
        observacoes: formData.observacoes || null,
        // Campos de parcelamento - garantir que boolean seja enviado corretamente
        eh_parcelado: Boolean(formData.eh_parcelado),
        total_parcelas: formData.eh_parcelado && formData.total_parcelas ? parseInt(formData.total_parcelas) : null,
        parcelas_restantes: formData.eh_parcelado && formData.parcelas_restantes ? parseInt(formData.parcelas_restantes) : null,
        valor_total: formData.eh_parcelado && formData.valor_total ? parseFloat(formData.valor_total) : null,
        // Campos de conta recorrente
        eh_recorrente: Boolean(formData.eh_recorrente),
      };

      console.log('DEBUG: Dados sendo enviados:', data); // Debug
      console.log('DEBUG: formData.eh_parcelado original:', formData.eh_parcelado, 'tipo:', typeof formData.eh_parcelado); // Debug
      
      if (editingConta) {
        // Para edição, incluir campos de parcelamento e recorrente
        const response = await axios.put(`/contas/${editingConta.id}`, data);
        
        // Se criou parcelas durante a edição, mostrar mensagem de sucesso
        if (response.data.parcelas_criadas) {
          alert(`Conta parcelada! ${response.data.parcelas_criadas} parcelas adicionais criadas (total: ${response.data.total_parcelas} parcelas)`);
        }
        
        // Se transformou em conta recorrente durante a edição
        if (formData.eh_recorrente && !editingConta.eh_recorrente) {
          alert(`Conta transformada em recorrente! 5 contas adicionais criadas para os próximos 5 meses.`);
        }
      } else {
        const response = await axios.post('/contas', data);
        
        // Se criou múltiplas parcelas, mostrar mensagem de sucesso
        if (Array.isArray(response.data) && response.data.length > 1) {
          if (formData.eh_parcelado) {
            alert(`${response.data.length} parcelas criadas com sucesso!`);
          } else if (formData.eh_recorrente) {
            alert(`${response.data.length} contas recorrentes criadas para os próximos 6 meses!`);
          }
        }
      }

      await fetchContas();
      handleCloseDialog();
    } catch (error) {
      console.error('Erro ao salvar conta:', error);
      alert('Erro ao salvar conta. Verifique os dados e tente novamente.');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      // Primeiro verifica se a conta faz parte de um parcelamento
      const infoResponse = await axios.get(`http://localhost:8000/contas/${id}/info-parcelamento`);
      const info = infoResponse.data;

      // Armazena as informações e abre o modal
      setContaToDelete(id);
      setParcelamentoInfo(info);
      setDeleteDialogOpen(true);
    } catch (error) {
      console.error('Erro ao verificar parcelamento:', error);
      alert('Erro ao verificar informações da conta');
    }
  };

  const confirmDelete = async (deleteAllParcelas: boolean) => {
    if (!contaToDelete) return;

    try {
      await axios.delete(`http://localhost:8000/contas/${contaToDelete}`, {
        params: { deletar_todas_parcelas: deleteAllParcelas }
      });

      setDeleteDialogOpen(false);
      setContaToDelete(null);
      setParcelamentoInfo(null);
      fetchContas();
    } catch (error) {
      console.error('Erro ao excluir conta:', error);
      alert('Erro ao excluir conta');
    }
  };

  const cancelDelete = () => {
    setDeleteDialogOpen(false);
    setContaToDelete(null);
    setParcelamentoInfo(null);
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    setSelectedFile(file || null);
  };

  const handleImportExcel = async () => {
    if (!selectedFile) {
      alert('Por favor, selecione um arquivo Excel');
      return;
    }

    setImporting(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await axios.post('http://localhost:8000/importar-excel', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const result = response.data;
      
      // Mostrar resultado da importação
      let message = `Importação concluída!\n\n`;
      message += `✅ Contas criadas: ${result.contas_criadas}\n`;
      
      if (result.contas_com_erro > 0) {
        message += `❌ Contas com erro: ${result.contas_com_erro}\n`;
      }
      
      if (result.categorias_criadas.length > 0) {
        message += `📁 Categorias criadas: ${result.categorias_criadas.join(', ')}\n`;
      }

      alert(message);
      
      // Fechar modal e recarregar dados
      setImportDialogOpen(false);
      setSelectedFile(null);
      fetchContas();
      
    } catch (error: any) {
      console.error('Erro ao importar Excel:', error);
      alert(`Erro ao importar: ${error.response?.data?.detail || error.message}`);
    } finally {
      setImporting(false);
    }
  };

  const closeImportDialog = () => {
    setImportDialogOpen(false);
    setSelectedFile(null);
  };

  const handleExportModel = async () => {
    try {
      const response = await axios.get('http://localhost:8000/exportar-modelo-excel', {
        responseType: 'blob',
      });

      // Criar URL do blob para download
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'modelo_importacao_contas.xlsx';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
    } catch (error) {
      console.error('Erro ao exportar modelo:', error);
      alert('Erro ao exportar modelo Excel');
    }
  };

  const handlePagar = async (id: number) => {
  const conta = contas.find((c: Conta) => c.id === id);
    if (conta) {
      setContaParaPagar(conta);
      setValorPagamento(conta.valor.toString());
      setPagamentoDialogOpen(true);
    }
  };

  const confirmarPagamento = async () => {
    if (!contaParaPagar) return;
    
    try {
      await axios.post(`/contas/${contaParaPagar.id}/pagar`, {
        valor_pago: parseFloat(valorPagamento)
      });
      await fetchContas();
      setPagamentoDialogOpen(false);
      setContaParaPagar(null);
      setValorPagamento('');
    } catch (error) {
      console.error('Erro ao marcar como pago:', error);
    }
  };

  const handleDesmarcarPagamento = async (id: number) => {
    try {
      await axios.post(`/contas/${id}/desmarcar-pagamento`);
      await fetchContas();
    } catch (error) {
      console.error('Erro ao desmarcar pagamento:', error);
    }
  };

  const handleEdit = (conta: Conta) => {
    setEditingConta(conta);
    setFormData({
      ...formData, // Mantém os valores padrão
      descricao: conta.descricao,
      valor: conta.valor.toString(),
      data_vencimento: dayjs(conta.data_vencimento),
      categoria_id: conta.categoria_id?.toString() || '',
      cartao_id: conta.cartao_id?.toString() || '',
      forma_pagamento: conta.forma_pagamento || '',
      observacoes: conta.observacoes || '',
      eh_parcelado: conta.eh_parcelado || false,
      total_parcelas: conta.total_parcelas?.toString() || '',
      parcelas_restantes: conta.parcelas_restantes?.toString() || '',
      valor_total: conta.valor_total?.toString() || '',
      eh_recorrente: conta.eh_recorrente || false,
    });
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingConta(null);
    setFormData({
      descricao: '',
      valor: '',
      data_vencimento: dayjs(),
      categoria_id: '',
      cartao_id: '',
      forma_pagamento: '',
      observacoes: '',
      // Limpar campos de parcelamento
      eh_parcelado: false,
      total_parcelas: '',
      parcelas_restantes: '',
      valor_total: '',
      // Limpar campos de conta recorrente
      eh_recorrente: false,
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pago':
        return 'success';
      case 'vencido':
        return 'error';
      default:
        return 'warning';
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(value);
  };

  // Função para filtrar contas baseada nos filtros ativos
  const getContasFiltradas = () => {
    let contasFiltradas = [...contas];

    if (filtroParceladas) {
      contasFiltradas = contasFiltradas.filter(conta => conta.eh_parcelado === true);
    }

    if (filtroRecorrentes) {
      contasFiltradas = contasFiltradas.filter(conta => conta.eh_recorrente === true);
    }

    return contasFiltradas;
  };

  const contasFiltradas = getContasFiltradas();

  const columns: GridColDef[] = [
    { field: 'id', headerName: 'ID', width: 70 },
    {
      field: 'descricao',
      headerName: 'Descrição',
      width: 200,
      editable: false,
    },
    {
      field: 'valor',
      headerName: 'Valor',
      width: 120,
  renderCell: (params: GridRenderCellParams) => formatCurrency(params.value as number),
    },
    {
      field: 'parcelamento',
      headerName: 'Parcelas',
      width: 100,
  renderCell: (params: GridRenderCellParams<any>) => {
        if (params.row.eh_parcelado) {
          return (
            <Chip
              label={`${params.row.numero_parcela}/${params.row.total_parcelas}`}
              color="info"
              size="small"
            />
          );
        }
        return '-';
      },
    },
    {
      field: 'data_vencimento',
      headerName: 'Vencimento',
      width: 130,
  renderCell: (params: GridRenderCellParams) => dayjs(params.value as string).format('DD/MM/YYYY'),
    },
    {
      field: 'categoria',
      headerName: 'Categoria',
      width: 130,
  renderCell: (params: GridRenderCellParams<any>) => params.row.categoria?.nome || '-',
    },
    {
      field: 'tipo',
      headerName: 'Tipo',
      width: 80,
  renderCell: (params: GridRenderCellParams<any>) => (
        <Box display="flex" gap={0.5}>
          {params.row.eh_parcelado && (
            <AccountTree 
              fontSize="small" 
              color="primary"
              titleAccess="Conta Parcelada"
            />
          )}
          {params.row.eh_recorrente && (
            <Repeat 
              fontSize="small" 
              color="secondary"
              titleAccess="Conta Recorrente"
            />
          )}
          {!params.row.eh_parcelado && !params.row.eh_recorrente && '-'}
        </Box>
      ),
    },
    {
      field: 'forma_pagamento',
      headerName: 'Forma Pagamento',
      width: 150,
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 120,
  renderCell: (params: GridRenderCellParams<any>) => (
        <Chip
          label={params.value}
          color={getStatusColor(params.value) as any}
          size="small"
        />
      ),
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Ações',
      width: 150,
  getActions: (params: GridRowParams) => [
        <GridActionsCellItem
          icon={<Edit />}
          label="Editar"
          onClick={() => handleEdit(params.row)}
        />,
        <GridActionsCellItem
          icon={<Payment />}
          label="Pagar"
          onClick={() => handlePagar(params.id as number)}
          disabled={params.row.status === 'pago'}
        />,
        <GridActionsCellItem
          icon={<Undo />}
          label="Desmarcar"
          onClick={() => handleDesmarcarPagamento(params.id as number)}
          disabled={params.row.status !== 'pago'}
        />,
        <GridActionsCellItem
          icon={<Delete />}
          label="Deletar"
          onClick={() => handleDelete(params.id as number)}
        />,
      ],
    },
  ];

  const shouldShowCartaoSelect = () => {
  const categoria = categorias.find((c: Categoria) => c.id === Number(formData.categoria_id));
    const isCategoriaCartao = categoria?.nome?.toLowerCase().includes('cart') || false;
    const isFormaCartao = (formData.forma_pagamento || '').toLowerCase().includes('cartão');
    return isCategoriaCartao || isFormaCartao;
  };

  return (
    <>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Contas</Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            color="secondary"
            startIcon={<Download />}
            onClick={handleExportModel}
          >
            Baixar Modelo
          </Button>
          <Button
            variant="outlined"
            startIcon={<Add />}
            onClick={() => setImportDialogOpen(true)}
          >
            Importar Excel
          </Button>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setDialogOpen(true)}
          >
            Nova Conta
          </Button>
        </Box>
      </Box>

      {/* Filtro de Mês/Ano */}
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
        <Box display="flex" alignItems="center" gap={2}>
          <Typography variant="h6">Filtrar por período:</Typography>
          <DatePicker
            label="Mês/Ano"
            value={mesAno}
            onChange={(newValue: dayjs.Dayjs | null) => setMesAno(newValue || dayjs())}
            views={['year', 'month']}
            format="MM/YYYY"
            slotProps={{
              textField: {
                size: 'small',
                sx: { minWidth: 150 }
              }
            }}
          />
        </Box>
        
        {/* Seletor de quantidade de itens por página */}
        <Box display="flex" alignItems="center" gap={2}>
          <Typography variant="body2">Itens por página:</Typography>
          <FormControl size="small" sx={{ minWidth: 80 }}>
            <Select
              value={pageSize}
              onChange={(e: any) => {
                const newSize = Number(e.target.value as string);
                setPageSize(newSize);
                localStorage.setItem('contas-page-size', newSize.toString());
              }}
              displayEmpty
            >
              <MenuItem value={5}>5</MenuItem>
              <MenuItem value={10}>10</MenuItem>
              <MenuItem value={25}>25</MenuItem>
              <MenuItem value={50}>50</MenuItem>
              <MenuItem value={100}>100</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </Box>

      {(() => {
        const map: Record<string, TotalizadorValores> = {};
        meses.forEach(m => {
          const t = totaisMeses[m.key];
          map[m.key] = { previsto: t?.previsto||0, pago: t?.pago||0, vencido: t?.vencido||0 };
        });
        return (
          <TotalizadoresMeses
            meses={meses as MesInfo[]}
            data={map}
            title='Totalizadores (todos os tipos) - Mês atual + 5 próximos'
            loading={carregandoTotais}
            showZeros={mostrarZeros}
            setShowZeros={setMostrarZeros}
            colorScheme='dark'
            onSelectMes={(_label: string, mes: number, ano: number) => setMesAno(dayjs(`${ano}-${String(mes).padStart(2,'0')}-01`))}
          />
        );
      })()}

      {/* Filtros de Tipo de Conta */}
      <Box display="flex" alignItems="center" gap={3} mb={3} sx={{ flexWrap: 'wrap' }}>
        <Typography variant="h6">Filtros:</Typography>
        
        <FormControlLabel
          control={
            <Checkbox
              checked={filtroParceladas}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFiltroParceladas(e.target.checked)}
              color="primary"
            />
          }
          label="Apenas Parceladas"
        />
        
        <FormControlLabel
          control={
            <Checkbox
              checked={filtroRecorrentes}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFiltroRecorrentes(e.target.checked)}
              color="secondary"
            />
          }
          label="Apenas Recorrentes"
        />

        <FormControlLabel
          control={
            <Checkbox
              checked={excluirComprasCartao}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setExcluirComprasCartao(e.target.checked)}
              color="warning"
            />
          }
          label="Excluir compras no cartão (manter faturas)"
        />
        
        {(filtroParceladas || filtroRecorrentes || excluirComprasCartao) && (
          <Button
            variant="outlined"
            size="small"
            onClick={() => {
              setFiltroParceladas(false);
              setFiltroRecorrentes(false);
              setExcluirComprasCartao(false);
            }}
            sx={{ ml: 2 }}
          >
            Limpar Filtros
          </Button>
        )}
        
        <Typography variant="body2" color="text.secondary" sx={{ ml: 'auto' }}>
          Exibindo {contasFiltradas.length} de {contas.length} contas
        </Typography>
      </Box>

      <Paper sx={{ height: 600, width: '100%' }}>
        <DataGrid
          rows={contasFiltradas}
          columns={columns}
          loading={loading}
          pageSizeOptions={[5, 10, 25, 50, 100]}
          initialState={{
            pagination: {
              paginationModel: { page: 0, pageSize: pageSize },
            },
          }}
          paginationModel={{
            page: 0,
            pageSize: pageSize,
          }}
          onPaginationModelChange={(model: GridPaginationModel) => {
            const newSize = model.pageSize;
            setPageSize(newSize);
            localStorage.setItem('contas-page-size', newSize.toString());
          }}
          disableRowSelectionOnClick
        />
      </Paper>

      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingConta ? 'Editar Conta' : 'Nova Conta'}
        </DialogTitle>
        <DialogContent>
          <TextField
            margin="dense"
            label="Descrição"
            fullWidth
            variant="outlined"
            value={formData.descricao}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, descricao: e.target.value })}
          />
          <TextField
            margin="dense"
            label="Valor"
            type="number"
            fullWidth
            variant="outlined"
            value={formData.valor}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, valor: e.target.value })}
          />
          <DatePicker
            label="Data de Vencimento"
            value={formData.data_vencimento}
            onChange={(newValue: dayjs.Dayjs | null) =>
              setFormData({ ...formData, data_vencimento: newValue || dayjs() })
            }
            slotProps={{
              textField: {
                fullWidth: true,
                margin: 'dense',
                variant: 'outlined',
              },
            }}
          />
          <TextField
            margin="dense"
            label="Categoria"
            select
            fullWidth
            variant="outlined"
            value={formData.categoria_id}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, categoria_id: e.target.value })}
          >
            {categorias.map((categoria: Categoria) => (
              <MenuItem key={categoria.id} value={categoria.id}>
                {categoria.nome}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            margin="dense"
            label="Forma de Pagamento"
            fullWidth
            variant="outlined"
            select
            value={formData.forma_pagamento}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, forma_pagamento: e.target.value })}
          >
            <MenuItem value="">
              <em>Selecione uma forma de pagamento</em>
            </MenuItem>
            {formasPagamento.map((forma) => (
              <MenuItem key={forma} value={forma}>
                {forma}
              </MenuItem>
            ))}
          </TextField>
          {shouldShowCartaoSelect() && (
            <TextField
              margin="dense"
              label="Cartão"
              select
              fullWidth
              variant="outlined"
              value={formData.cartao_id}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, cartao_id: e.target.value })}
            >
              <MenuItem value="">
                <em>Selecione o cartão</em>
              </MenuItem>
              {cartoes.map((c: Cartao) => (
                <MenuItem key={c.id} value={c.id}>
                  {c.nome}
                </MenuItem>
              ))}
            </TextField>
          )}
          
          {/* Campos de Parcelamento */}
          <FormControlLabel
            control={
              <Checkbox
                checked={formData.eh_parcelado}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                  console.log('DEBUG: Checkbox alterado para:', e.target.checked);
                  setFormData({ 
                    ...formData, 
                    eh_parcelado: e.target.checked,
                    total_parcelas: e.target.checked ? formData.total_parcelas : '',
                    parcelas_restantes: e.target.checked ? formData.parcelas_restantes : '',
                    valor_total: e.target.checked ? formData.valor_total : '',
                    // Desabilitar recorrente se parcelado estiver ativo
                    eh_recorrente: e.target.checked ? false : formData.eh_recorrente,
                  });
                  console.log('DEBUG: FormData após mudança:', { ...formData, eh_parcelado: e.target.checked });
                }}
              />
            }
            label="Compra Parcelada"
            sx={{ mt: 2, mb: 1 }}
          />
          
          {/* Campos de Conta Recorrente */}
          <FormControlLabel
            control={
              <Checkbox
                checked={formData.eh_recorrente}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                  setFormData({ 
                    ...formData, 
                    eh_recorrente: e.target.checked,
                    // Desabilitar parcelamento se recorrente estiver ativo
                    eh_parcelado: e.target.checked ? false : formData.eh_parcelado,
                    total_parcelas: e.target.checked ? '' : formData.total_parcelas,
                    parcelas_restantes: e.target.checked ? '' : formData.parcelas_restantes,
                    valor_total: e.target.checked ? '' : formData.valor_total,
                  });
                }}
                disabled={formData.eh_parcelado} // Desabilitar se for parcelado
              />
            }
            label="Conta Recorrente (6 meses)"
            sx={{ mt: 1, mb: 1 }}
          />
          
          {formData.eh_recorrente && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 2 }}>
              ℹ️ Esta conta será criada automaticamente para os próximos 6 meses.
            </Typography>
          )}
          
          {formData.eh_parcelado && (
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={6}>
                <TextField
                  margin="dense"
                  label="Total de Parcelas"
                  fullWidth
                  variant="outlined"
                  type="number"
                  value={formData.total_parcelas}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, total_parcelas: e.target.value })}
                  helperText="Ex: 12 parcelas"
                />
              </Grid>
              <Grid item xs={6}>
                <TextField
                  margin="dense"
                  label="Parcelas Restantes"
                  fullWidth
                  variant="outlined"
                  type="number"
                  value={formData.parcelas_restantes}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, parcelas_restantes: e.target.value })}
                  helperText="Parcelas restantes (anteriores serão criadas como pagas)"
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  margin="dense"
                  label="Valor Total da Compra (Opcional)"
                  fullWidth
                  variant="outlined"
                  type="number"
                  value={formData.valor_total}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, valor_total: e.target.value })}
                  helperText="Se vazio, será calculado como valor da parcela × total de parcelas"
                />
              </Grid>
            </Grid>
          )}
          
          <TextField
            margin="dense"
            label="Observações"
            fullWidth
            multiline
            rows={3}
            variant="outlined"
            value={formData.observacoes}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, observacoes: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancelar</Button>
          <Button onClick={handleSave} variant="contained">
            Salvar
          </Button>
        </DialogActions>
      </Dialog>

      {/* Modal de Confirmação de Exclusão */}
      <Dialog
        open={deleteDialogOpen}
        onClose={cancelDelete}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Warning color="warning" />
          Confirmar Exclusão
        </DialogTitle>
        <DialogContent>
          {parcelamentoInfo && (
            <Box>
              {parcelamentoInfo.eh_parcelado ? (
                <Box>
                  <Typography variant="body1" gutterBottom>
                    <strong>Esta conta faz parte de um parcelamento:</strong>
                  </Typography>
                  <Box sx={{ pl: 2, mt: 1 }}>
                    <Typography variant="body2">
                      • Parcela atual: {parcelamentoInfo.parcela_atual} de {parcelamentoInfo.total_parcelas}
                    </Typography>
                    <Typography variant="body2">
                      • Valor total: R$ {Number(parcelamentoInfo.valor_total).toFixed(2)}
                    </Typography>
                    <Typography variant="body2">
                      • Total de parcelas: {parcelamentoInfo.total_parcelas}
                    </Typography>
                  </Box>
                  <Typography variant="body1" sx={{ mt: 2 }}>
                    O que você deseja fazer?
                  </Typography>
                </Box>
              ) : (
                <Typography variant="body1">
                  Tem certeza que deseja excluir esta conta?
                </Typography>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ p: 2, gap: 1 }}>
          <Button
            onClick={cancelDelete}
            variant="outlined"
            startIcon={<Undo />}
          >
            Cancelar
          </Button>
          {parcelamentoInfo?.eh_parcelado ? (
            <>
              <Button
                onClick={() => confirmDelete(false)}
                variant="contained"
                color="warning"
                startIcon={<Delete />}
              >
                Excluir Apenas Esta Parcela
              </Button>
              <Button
                onClick={() => confirmDelete(true)}
                variant="contained"
                color="error"
                startIcon={<Delete />}
              >
                Excluir Todas as Parcelas
              </Button>
            </>
          ) : (
            <Button
              onClick={() => confirmDelete(false)}
              variant="contained"
              color="error"
              startIcon={<Delete />}
            >
              Confirmar Exclusão
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Modal de Pagamento */}
      <Dialog
        open={pagamentoDialogOpen}
        onClose={() => setPagamentoDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          Confirmar Pagamento
        </DialogTitle>
        <DialogContent>
          {contaParaPagar && (
            <Box sx={{ pt: 2 }}>
              <Typography variant="body1" gutterBottom>
                <strong>Conta:</strong> {contaParaPagar.descricao}
              </Typography>
              
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Valor original: {formatCurrency(contaParaPagar.valor)}
              </Typography>
              
              {contaParaPagar.valor_previsto && contaParaPagar.valor_previsto !== contaParaPagar.valor && (
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Valor previsto: {formatCurrency(contaParaPagar.valor_previsto)}
                </Typography>
              )}
              
              <TextField
                fullWidth
                label="Valor Pago"
                type="number"
                value={valorPagamento}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setValorPagamento(e.target.value)}
                sx={{ mt: 2 }}
                inputProps={{
                  step: "0.01",
                  min: "0"
                }}
                helperText="Informe o valor real que foi pago. Pode ser diferente do valor original se houver juros, desconto ou alteração no valor."
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPagamentoDialogOpen(false)}>
            Cancelar
          </Button>
          <Button 
            onClick={confirmarPagamento}
            variant="contained"
            color="primary"
            disabled={!valorPagamento || parseFloat(valorPagamento) <= 0}
          >
            Confirmar Pagamento
          </Button>
        </DialogActions>
      </Dialog>

      {/* Modal de Importação de Excel */}
      <Dialog
        open={importDialogOpen}
        onClose={closeImportDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          Importar Contas via Excel
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <Typography variant="body2" gutterBottom>
              <strong>📋 Dica:</strong> Use o botão "Baixar Modelo" para obter um arquivo Excel com o formato correto e exemplos.
            </Typography>
            
            <Typography variant="body2" gutterBottom sx={{ mt: 2 }}>
              <strong>Formato do arquivo Excel:</strong>
            </Typography>
            <Typography variant="body2" sx={{ mb: 2, pl: 2 }}>
              • <strong>Descricao</strong>: Descrição da conta<br/>
              • <strong>Data de Pagamento</strong>: Data no formato DD/MM/AAAA<br/>
              • <strong>Categoria</strong>: Nome da categoria (será criada se não existir)<br/>
              • <strong>Valor</strong>: Valor numérico da conta
            </Typography>
            
            <input
              type="file"
              accept=".xlsx,.xls"
              onChange={handleFileSelect}
              style={{ marginBottom: '16px' }}
            />
            
            {selectedFile && (
              <Typography variant="body2" color="primary">
                Arquivo selecionado: {selectedFile.name}
              </Typography>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeImportDialog}>
            Cancelar
          </Button>
          <Button 
            onClick={handleImportExcel}
            variant="contained"
            disabled={!selectedFile || importing}
          >
            {importing ? 'Importando...' : 'Importar'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default Contas;