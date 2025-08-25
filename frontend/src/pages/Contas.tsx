import React, { useState, useEffect, useCallback } from 'react';
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
} from '@mui/material';
import { DataGrid, GridColDef, GridActionsCellItem } from '@mui/x-data-grid';
import {
  Add,
  Edit,
  Delete,
  Payment,
  Undo,
  Warning,
  Download,
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
}

const Contas: React.FC = () => {
  const [contas, setContas] = useState<Conta[]>([]);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
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
  
  const [formData, setFormData] = useState({
    descricao: '',
    valor: '',
    data_vencimento: dayjs(),
    categoria_id: '',
    forma_pagamento: '',
    observacoes: '',
    // Campos de parcelamento
    eh_parcelado: false,
    total_parcelas: '',
    parcelas_restantes: '',
    valor_total: '',
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
        ano: mesAno.year()
      };
      
      const response = await axios.get('/contas', { params });
      setContas(response.data);
    } catch (error) {
      console.error('Erro ao carregar contas:', error);
    } finally {
      setLoading(false);
    }
  }, [mesAno]);

  const fetchCategorias = async () => {
    try {
      const response = await axios.get('/categorias');
      setCategorias(response.data);
    } catch (error) {
      console.error('Erro ao carregar categorias:', error);
    }
  };

  useEffect(() => {
    fetchCategorias();
    fetchContas();
  }, [fetchContas]); // Recarregar quando o filtro de mês/ano mudar

  const handleSave = async () => {
    try {
      const data = {
        descricao: formData.descricao,
        valor: parseFloat(formData.valor),
        data_vencimento: formData.data_vencimento.format('YYYY-MM-DD'),
        categoria_id: parseInt(formData.categoria_id),
        forma_pagamento: formData.forma_pagamento || null,
        observacoes: formData.observacoes || null,
        // Campos de parcelamento
        eh_parcelado: formData.eh_parcelado,
        total_parcelas: formData.eh_parcelado && formData.total_parcelas ? parseInt(formData.total_parcelas) : null,
        parcelas_restantes: formData.eh_parcelado && formData.parcelas_restantes ? parseInt(formData.parcelas_restantes) : null,
        valor_total: formData.eh_parcelado && formData.valor_total ? parseFloat(formData.valor_total) : null,
      };

      if (editingConta) {
        // Para edição, não permitir alterar parcelamento (por enquanto)
        const { eh_parcelado, total_parcelas, parcelas_restantes, valor_total, ...editData } = data;
        await axios.put(`/contas/${editingConta.id}`, editData);
      } else {
        const response = await axios.post('/contas', data);
        
        // Se criou múltiplas parcelas, mostrar mensagem de sucesso
        if (Array.isArray(response.data) && response.data.length > 1) {
          alert(`${response.data.length} parcelas criadas com sucesso!`);
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
    try {
      await axios.post(`/contas/${id}/pagar`);
      await fetchContas();
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
      forma_pagamento: conta.forma_pagamento || '',
      observacoes: conta.observacoes || '',
      eh_parcelado: conta.eh_parcelado || false,
      total_parcelas: conta.total_parcelas?.toString() || '',
      parcelas_restantes: conta.parcelas_restantes?.toString() || '',
      valor_total: conta.valor_total?.toString() || '',
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
      forma_pagamento: '',
      observacoes: '',
      // Limpar campos de parcelamento
      eh_parcelado: false,
      total_parcelas: '',
      parcelas_restantes: '',
      valor_total: '',
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
      renderCell: (params) => formatCurrency(params.value),
    },
    {
      field: 'parcelamento',
      headerName: 'Parcelas',
      width: 100,
      renderCell: (params) => {
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
      renderCell: (params) => dayjs(params.value).format('DD/MM/YYYY'),
    },
    {
      field: 'categoria',
      headerName: 'Categoria',
      width: 130,
      renderCell: (params) => params.row.categoria?.nome || '-',
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
      renderCell: (params) => (
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
      getActions: (params) => [
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
      <Box display="flex" alignItems="center" mb={3} gap={2}>
        <Typography variant="h6">Filtrar por período:</Typography>
        <DatePicker
          label="Mês/Ano"
          value={mesAno}
          onChange={(newValue) => setMesAno(newValue || dayjs())}
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

      <Paper sx={{ height: 600, width: '100%' }}>
        <DataGrid
          rows={contas}
          columns={columns}
          loading={loading}
          pageSizeOptions={[10, 25, 50]}
          initialState={{
            pagination: {
              paginationModel: { page: 0, pageSize: 10 },
            },
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
            onChange={(e) => setFormData({ ...formData, descricao: e.target.value })}
          />
          <TextField
            margin="dense"
            label="Valor"
            type="number"
            fullWidth
            variant="outlined"
            value={formData.valor}
            onChange={(e) => setFormData({ ...formData, valor: e.target.value })}
          />
          <DatePicker
            label="Data de Vencimento"
            value={formData.data_vencimento}
            onChange={(newValue) =>
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
            onChange={(e) => setFormData({ ...formData, categoria_id: e.target.value })}
          >
            {categorias.map((categoria) => (
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
            onChange={(e) => setFormData({ ...formData, forma_pagamento: e.target.value })}
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
          
          {/* Campos de Parcelamento */}
          <FormControlLabel
            control={
              <Checkbox
                checked={formData.eh_parcelado}
                onChange={(e) => setFormData({ 
                  ...formData, 
                  eh_parcelado: e.target.checked,
                  total_parcelas: e.target.checked ? formData.total_parcelas : '',
                  parcelas_restantes: e.target.checked ? formData.parcelas_restantes : '',
                  valor_total: e.target.checked ? formData.valor_total : '',
                })}
              />
            }
            label="Compra Parcelada"
            sx={{ mt: 2, mb: 1 }}
          />
          
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
                  onChange={(e) => setFormData({ ...formData, total_parcelas: e.target.value })}
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
                  onChange={(e) => setFormData({ ...formData, parcelas_restantes: e.target.value })}
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
                  onChange={(e) => setFormData({ ...formData, valor_total: e.target.value })}
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
            onChange={(e) => setFormData({ ...formData, observacoes: e.target.value })}
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