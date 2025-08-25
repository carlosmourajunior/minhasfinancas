import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Paper,
  CircularProgress,
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  MonetizationOn,
  Warning,
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import dayjs from 'dayjs';
import axios from 'axios';

interface ResumoData {
  total_pendente: number;
  total_pago: number;
  total_vencido: number;
  valor_total_pendente: number;
}

interface DadosGrafico {
  mes: number;
  ano: number;
  mes_nome: string;
  valor_previsto: number;
  valor_pago: number;
  eh_mes_atual: boolean;
}

const Dashboard: React.FC = () => {
  const [resumo, setResumo] = useState<ResumoData | null>(null);
  const [dadosGrafico, setDadosGrafico] = useState<DadosGrafico[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingGrafico, setLoadingGrafico] = useState(true);
  const [mesAno, setMesAno] = useState(dayjs()); // Mês/ano atual por padrão

  useEffect(() => {
    const fetchResumo = async () => {
      try {
        const params = {
          mes: mesAno.month() + 1, // dayjs months são 0-indexed
          ano: mesAno.year()
        };
        
        const response = await axios.get('/relatorios/resumo', { params });
        setResumo(response.data);
      } catch (error) {
        console.error('Erro ao carregar resumo:', error);
      } finally {
        setLoading(false);
      }
    };

    const fetchDadosGrafico = async () => {
      try {
        const response = await axios.get('/relatorios/grafico-evolucao');
        setDadosGrafico(response.data);
      } catch (error) {
        console.error('Erro ao carregar dados do gráfico:', error);
      } finally {
        setLoadingGrafico(false);
      }
    };

    fetchResumo();
    fetchDadosGrafico();
  }, [mesAno]); // Recarregar quando o filtro de mês/ano mudar

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

  const cardData = [
    {
      title: 'Contas Pendentes',
      value: resumo?.total_pendente || 0,
      icon: <TrendingUp />,
      color: '#ff9800',
      bgColor: '#fff3e0',
    },
    {
      title: 'Contas Pagas',
      value: resumo?.total_pago || 0,
      icon: <MonetizationOn />,
      color: '#4caf50',
      bgColor: '#e8f5e8',
    },
    {
      title: 'Contas Vencidas',
      value: resumo?.total_vencido || 0,
      icon: <Warning />,
      color: '#f44336',
      bgColor: '#ffebee',
    },
    {
      title: 'Valor Total Pendente',
      value: formatCurrency(resumo?.valor_total_pendente || 0),
      icon: <TrendingDown />,
      color: '#2196f3',
      bgColor: '#e3f2fd',
      isMonetary: true,
    },
  ];

  return (
    <>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      
      {/* Filtro de Mês/Ano */}
      <Box display="flex" alignItems="center" mb={3} gap={2}>
        <Typography variant="h6">Período:</Typography>
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

      {/* Gráfico de Evolução dos Gastos */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Evolução dos Gastos (2 meses anteriores + 9 posteriores)
        </Typography>
        {loadingGrafico ? (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight="300px">
            <CircularProgress />
          </Box>
        ) : (
          <Box sx={{ height: 300, display: 'flex', alignItems: 'end', gap: 1, mt: 2 }}>
            {dadosGrafico.map((item, index) => {
              const maxValue = Math.max(...dadosGrafico.map(d => Math.max(d.valor_previsto, d.valor_pago)));
              const heightPrevisto = (item.valor_previsto / maxValue) * 250;
              const heightPago = (item.valor_pago / maxValue) * 250;
              
              return (
                <Box key={index} sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'end', gap: '2px', mb: 1, height: '250px' }}>
                    <Box
                      sx={{
                        width: '15px',
                        height: `${heightPrevisto}px`,
                        backgroundColor: item.eh_mes_atual ? '#1976d2' : '#90caf9',
                        borderRadius: '2px 2px 0 0',
                        position: 'relative',
                      }}
                      title={`Previsto: ${formatCurrency(item.valor_previsto)}`}
                    />
                    <Box
                      sx={{
                        width: '15px',
                        height: `${heightPago}px`,
                        backgroundColor: item.eh_mes_atual ? '#388e3c' : '#81c784',
                        borderRadius: '2px 2px 0 0',
                        position: 'relative',
                      }}
                      title={`Pago: ${formatCurrency(item.valor_pago)}`}
                    />
                  </Box>
                  <Typography variant="caption" sx={{ fontSize: '10px', textAlign: 'center' }}>
                    {item.mes_nome}
                  </Typography>
                </Box>
              );
            })}
          </Box>
        )}
        
        {/* Legenda */}
        <Box display="flex" justifyContent="center" gap={3} mt={2}>
          <Box display="flex" alignItems="center" gap={1}>
            <Box sx={{ width: 15, height: 15, backgroundColor: '#90caf9', borderRadius: '2px' }} />
            <Typography variant="caption">Previsto</Typography>
          </Box>
          <Box display="flex" alignItems="center" gap={1}>
            <Box sx={{ width: 15, height: 15, backgroundColor: '#81c784', borderRadius: '2px' }} />
            <Typography variant="caption">Pago</Typography>
          </Box>
          <Box display="flex" alignItems="center" gap={1}>
            <Box sx={{ width: 15, height: 15, backgroundColor: '#1976d2', borderRadius: '2px' }} />
            <Typography variant="caption">Mês Atual (Previsto)</Typography>
          </Box>
          <Box display="flex" alignItems="center" gap={1}>
            <Box sx={{ width: 15, height: 15, backgroundColor: '#388e3c', borderRadius: '2px' }} />
            <Typography variant="caption">Mês Atual (Pago)</Typography>
          </Box>
        </Box>
      </Paper>
      
      <Grid container spacing={3}>
        {cardData.map((card, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card
              sx={{
                backgroundColor: card.bgColor,
                border: `1px solid ${card.color}20`,
                borderRadius: 2,
                transition: 'transform 0.2s, box-shadow 0.2s',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: '0 4px 20px rgba(0,0,0,0.12)',
                },
              }}
            >
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography
                      variant="h6"
                      component="div"
                      sx={{ fontSize: '0.9rem', color: 'text.secondary', mb: 1 }}
                    >
                      {card.title}
                    </Typography>
                    <Typography
                      variant="h4"
                      component="div"
                      sx={{ color: card.color, fontWeight: 'bold' }}
                    >
                      {card.value}
                    </Typography>
                  </Box>
                  <Box
                    sx={{
                      backgroundColor: card.color,
                      color: 'white',
                      borderRadius: '50%',
                      width: 56,
                      height: 56,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    {card.icon}
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3} sx={{ mt: 2 }}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, borderRadius: 2 }}>
            <Typography variant="h6" gutterBottom>
              Resumo Financeiro
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Aqui você pode acompanhar o resumo das suas contas. 
              Mantenha sempre em dia com os pagamentos para evitar juros e multas.
            </Typography>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, borderRadius: 2 }}>
            <Typography variant="h6" gutterBottom>
              Ações Rápidas
            </Typography>
            <Typography variant="body2" color="text.secondary">
              • Adicionar nova conta
              <br />
              • Visualizar vencimentos
              <br />
              • Gerar relatórios
              <br />
              • Importar dados do Excel
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    </>
  );
};

export default Dashboard;