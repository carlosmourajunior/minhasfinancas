import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Paper,
  CircularProgress,
  Button,
  FormControlLabel,
  Checkbox,
} from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from 'recharts';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import dayjs from 'dayjs';
import axios from 'axios';

interface CategoriaData {
  total: number;
  pendente: number;
  pago: number;
}

const Relatorios: React.FC = () => {
  const [categorias, setCategorias] = useState<Record<string, CategoriaData>>({});
  const [loading, setLoading] = useState(true);
  const [mesAno, setMesAno] = useState(dayjs()); // Mês/ano atual por padrão
  const [mostrarTodos, setMostrarTodos] = useState(false); // Checkbox para mostrar todos os dados

  useEffect(() => {
    const fetchRelatorios = async () => {
      try {
        const params: any = {};
        
        // Se não for "mostrar todos", incluir filtros de mês/ano
        if (!mostrarTodos) {
          params.mes = mesAno.month() + 1; // dayjs months são 0-indexed
          params.ano = mesAno.year();
        }
        
        const response = await axios.get('/relatorios/categorias', { params });
        setCategorias(response.data);
      } catch (error) {
        console.error('Erro ao carregar relatórios:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchRelatorios();
  }, [mesAno, mostrarTodos]); // Recarregar quando mudar mês/ano ou checkbox

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(value);
  };

  // Preparar dados para o gráfico de barras
  const chartData = Object.entries(categorias).map(([categoria, data]) => ({
    categoria,
    pendente: data.pendente,
    pago: data.pago,
    total: data.total,
  }));

  // Preparar dados para o gráfico de pizza
  const pieData = Object.entries(categorias).map(([categoria, data]) => ({
    name: categoria,
    value: data.total,
  }));

  const COLORS = [
    '#0088FE',
    '#00C49F',
    '#FFBB28',
    '#FF8042',
    '#8884D8',
    '#82CA9D',
    '#FFC658',
    '#FF7C7C',
    '#8DD1E1',
  ];

  return (
    <>
      <Typography variant="h4" gutterBottom>
        Relatórios
      </Typography>

      {/* Controles de Filtro */}
      <Paper sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Box display="flex" alignItems="center" gap={3} flexWrap="wrap">
          <Typography variant="h6">Filtros:</Typography>
          
          <FormControlLabel
            control={
              <Checkbox
                checked={mostrarTodos}
                onChange={(e) => setMostrarTodos(e.target.checked)}
                color="primary"
              />
            }
            label="Mostrar todos os dados (sem filtro de período)"
          />
          
          {!mostrarTodos && (
            <DatePicker
              label="Período"
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
          )}
          
          <Typography variant="body2" color="text.secondary" sx={{ ml: 'auto' }}>
            {mostrarTodos 
              ? 'Exibindo dados de todo o período' 
              : `Período: ${mesAno.format('MM/YYYY')}`
            }
          </Typography>
        </Box>
      </Paper>

      <Grid container spacing={3}>
        {/* Gráfico de barras */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, borderRadius: 2 }}>
            <Typography variant="h6" gutterBottom>
              Gastos por Categoria
            </Typography>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="categoria" />
                <YAxis />
                <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                <Legend />
                <Bar dataKey="pendente" fill="#ff9800" name="Pendente" />
                <Bar dataKey="pago" fill="#4caf50" name="Pago" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Gráfico de pizza */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, borderRadius: 2 }}>
            <Typography variant="h6" gutterBottom>
              Distribuição por Categoria
            </Typography>
            <ResponsiveContainer width="100%" height={400}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) =>
                    `${name}: ${(percent * 100).toFixed(1)}%`
                  }
                  outerRadius={120}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => formatCurrency(Number(value))} />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Tabela de resumo */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3, borderRadius: 2 }}>
            <Typography variant="h6" gutterBottom>
              Resumo por Categoria
            </Typography>
            <Grid container spacing={2}>
              {Object.entries(categorias).map(([categoria, data]) => (
                <Grid item xs={12} sm={6} md={4} key={categoria}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" component="div" gutterBottom>
                        {categoria}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Total: {formatCurrency(data.total)}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Pendente: {formatCurrency(data.pendente)}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Pago: {formatCurrency(data.pago)}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </>
  );
};

export default Relatorios;