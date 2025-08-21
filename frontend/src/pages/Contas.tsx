import React, { useState, useEffect } from 'react';
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
} from '@mui/material';
import { DataGrid, GridColDef, GridActionsCellItem } from '@mui/x-data-grid';
import {
  Add,
  Edit,
  Delete,
  Payment,
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import dayjs from 'dayjs';
import axios from 'axios';

interface Conta {
  id: number;
  descricao: string;
  valor: number;
  data_vencimento: string;
  data_pagamento?: string;
  categoria: string;
  cartao?: string;
  status: string;
  observacoes?: string;
}

const Contas: React.FC = () => {
  const [contas, setContas] = useState<Conta[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingConta, setEditingConta] = useState<Conta | null>(null);
  const [formData, setFormData] = useState({
    descricao: '',
    valor: '',
    data_vencimento: dayjs(),
    categoria: '',
    cartao: '',
    observacoes: '',
  });

  const categorias = [
    'Alimentação',
    'Transporte',
    'Moradia',
    'Saúde',
    'Educação',
    'Lazer',
    'Compras',
    'Serviços',
    'Outros',
  ];

  useEffect(() => {
    fetchContas();
  }, []);

  const fetchContas = async () => {
    try {
      const response = await axios.get('/contas');
      setContas(response.data);
    } catch (error) {
      console.error('Erro ao carregar contas:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      const data = {
        descricao: formData.descricao,
        valor: parseFloat(formData.valor),
        data_vencimento: formData.data_vencimento.format('YYYY-MM-DD'),
        categoria: formData.categoria,
        cartao: formData.cartao || null,
        observacoes: formData.observacoes || null,
      };

      if (editingConta) {
        await axios.put(`/contas/${editingConta.id}`, data);
      } else {
        await axios.post('/contas', data);
      }

      await fetchContas();
      handleCloseDialog();
    } catch (error) {
      console.error('Erro ao salvar conta:', error);
    }
  };

  const handleDelete = async (id: number) => {
    if (window.confirm('Deseja realmente deletar esta conta?')) {
      try {
        await axios.delete(`/contas/${id}`);
        await fetchContas();
      } catch (error) {
        console.error('Erro ao deletar conta:', error);
      }
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

  const handleEdit = (conta: Conta) => {
    setEditingConta(conta);
    setFormData({
      descricao: conta.descricao,
      valor: conta.valor.toString(),
      data_vencimento: dayjs(conta.data_vencimento),
      categoria: conta.categoria,
      cartao: conta.cartao || '',
      observacoes: conta.observacoes || '',
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
      categoria: '',
      cartao: '',
      observacoes: '',
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
      field: 'data_vencimento',
      headerName: 'Vencimento',
      width: 130,
      renderCell: (params) => dayjs(params.value).format('DD/MM/YYYY'),
    },
    {
      field: 'categoria',
      headerName: 'Categoria',
      width: 130,
    },
    {
      field: 'cartao',
      headerName: 'Cartão',
      width: 130,
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
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => setDialogOpen(true)}
        >
          Nova Conta
        </Button>
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
            value={formData.categoria}
            onChange={(e) => setFormData({ ...formData, categoria: e.target.value })}
          >
            {categorias.map((categoria) => (
              <MenuItem key={categoria} value={categoria}>
                {categoria}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            margin="dense"
            label="Cartão"
            fullWidth
            variant="outlined"
            value={formData.cartao}
            onChange={(e) => setFormData({ ...formData, cartao: e.target.value })}
          />
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
    </>
  );
};

export default Contas;