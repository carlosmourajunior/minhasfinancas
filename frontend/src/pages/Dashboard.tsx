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
import axios from 'axios';

interface ResumoData {
  total_pendente: number;
  total_pago: number;
  total_vencido: number;
  valor_total_pendente: number;
}

const Dashboard: React.FC = () => {
  const [resumo, setResumo] = useState<ResumoData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchResumo = async () => {
      try {
        const response = await axios.get('/relatorios/resumo');
        setResumo(response.data);
      } catch (error) {
        console.error('Erro ao carregar resumo:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchResumo();
  }, []);

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