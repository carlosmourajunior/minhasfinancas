import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Paper,
  CircularProgress,
  FormControlLabel,
  Checkbox,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
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

interface FaturaPendente {
  id: number;
  cartao_id: number;
  cartao_nome?: string;
  periodo_inicio: string;
  periodo_fim: string;
  data_fechamento: string;
  data_vencimento: string;
  valor_previsto?: number;
  valor_real?: number;
  status: string;
}

const Dashboard: React.FC = () => {
  const [resumo, setResumo] = useState<ResumoData | null>(null);
  const [dadosGrafico, setDadosGrafico] = useState<DadosGrafico[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingGrafico, setLoadingGrafico] = useState(true);
  const [mesAno, setMesAno] = useState(dayjs()); // Mês/ano atual por padrão
  const [mostrarTodos, setMostrarTodos] = useState(false); // Checkbox para mostrar todos os dados
  const [faturasPendentes, setFaturasPendentes] = useState<FaturaPendente[]>([]);
  const [contasVencemHoje, setContasVencemHoje] = useState<any[]>([]);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [faturaParaConfirmar, setFaturaParaConfirmar] = useState<FaturaPendente | null>(null);
  const [valorFatura, setValorFatura] = useState('');

  useEffect(() => {
    const fetchResumo = async () => {
      try {
        const params: any = {};
        
        // Se não for "mostrar todos", incluir filtros de mês/ano
        if (!mostrarTodos) {
          params.mes = mesAno.month() + 1; // dayjs months são 0-indexed
          params.ano = mesAno.year();
        }
        
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

    const fetchFaturasPendentes = async () => {
      try {
        const res = await axios.get('/cartoes/faturas/pendentes');
        setFaturasPendentes(res.data || []);
      } catch (error) {
        console.error('Erro ao carregar faturas pendentes:', error);
      }
    };

    const fetchContasVencemHoje = async () => {
      try {
        const res = await axios.get('/contas/vencem-hoje');
        setContasVencemHoje(res.data || []);
      } catch (error) {
        console.error('Erro ao carregar contas que vencem hoje:', error);
      }
    };

    fetchResumo();
    fetchDadosGrafico();
    fetchFaturasPendentes();
    fetchContasVencemHoje();
  }, [mesAno, mostrarTodos]); // Recarregar quando o filtro de mês/ano mudar ou checkbox

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

  const formatDateBr = (input: string) => {
    if (!input) return '-';
    // Se vier no formato ISO (YYYY-MM-DD ou ISO completo), usar dayjs
    if (input.includes('-')) {
      const d = dayjs(input);
      return d.isValid() ? d.format('DD/MM/YYYY') : input;
    }
    // Se vier com barras, assumir que já está em DD/MM/YYYY e retornar como está
    if (input.includes('/')) {
      return input;
    }
    // Fallback
    try {
      const d = new Date(input);
      return d.toLocaleDateString('pt-BR');
    } catch {
      return input;
    }
  };

  const abrirConfirmacaoFatura = (fatura: FaturaPendente) => {
    setFaturaParaConfirmar(fatura);
    setValorFatura(fatura.valor_previsto ? fatura.valor_previsto.toString() : '');
    setConfirmDialogOpen(true);
  };

  const confirmarFatura = async () => {
    if (!faturaParaConfirmar) return;
    const valor = parseFloat(valorFatura);
    if (!valor || valor <= 0) {
      alert('Informe um valor válido para a fatura.');
      return;
    }
    try {
      await axios.post(`/cartoes/faturas/${faturaParaConfirmar.id}/confirmar`, { valor_real: valor });
      setConfirmDialogOpen(false);
      setFaturaParaConfirmar(null);
      // Recarregar dados essenciais
      const [resumoRes, faturasRes] = await Promise.all([
        axios.get('/relatorios/resumo', !mostrarTodos ? { params: { mes: mesAno.month() + 1, ano: mesAno.year() } } : {}),
        axios.get('/cartoes/faturas/pendentes'),
      ]);
      setResumo(resumoRes.data);
      setFaturasPendentes(faturasRes.data || []);
    } catch (error: any) {
      console.error('Erro ao confirmar fatura:', error);
      alert(error.response?.data?.detail || 'Erro ao confirmar fatura');
    }
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

      {/* Alertas de Faturas Pendentes */}
      {faturasPendentes.length > 0 && (
        <Paper sx={{ p: 3, mb: 3, borderRadius: 2, border: '1px solid #ff980040' }}>
          <Typography variant="h6" gutterBottom color="warning.main">
            Faturas fechadas aguardando confirmação
          </Typography>
          {faturasPendentes.map((f) => (
            <Box key={f.id} display="flex" alignItems="center" justifyContent="space-between" py={1}>
              <Box>
                <Typography variant="body1">
                  Cartão {f.cartao_nome || `#${f.cartao_id}`} • Vencimento {formatDateBr(f.data_vencimento)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Período: {formatDateBr(f.periodo_inicio)} — {formatDateBr(f.periodo_fim)} · Previsto: {formatCurrency(f.valor_previsto || 0)}
                </Typography>
              </Box>
              <Button variant="contained" color="warning" onClick={() => abrirConfirmacaoFatura(f)}>
                Confirmar Valor
              </Button>
            </Box>
          ))}
        </Paper>
      )}

      {/* Alertas de Contas que Vencem Hoje */}
      {contasVencemHoje.length > 0 && (
        <Paper sx={{ p: 3, mb: 3, borderRadius: 2, border: '1px solid #1976d240' }}>
          <Typography variant="h6" gutterBottom color="primary.main">
            Contas que vencem hoje
          </Typography>
          {contasVencemHoje.map((c) => (
            <Box key={c.id} display="flex" alignItems="center" justifyContent="space-between" py={1}>
              <Box>
                <Typography variant="body1">
                  {c.descricao} • {new Date(c.data_vencimento).toLocaleDateString('pt-BR')} • {formatCurrency(c.valor)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Categoria: {c.categoria?.nome || '-'}{c.cartao?.nome ? ` • Cartão: ${c.cartao?.nome}` : ''}
                </Typography>
              </Box>
              <Button variant="contained" onClick={() => window.location.href = '/contas'}>
                Ver Contas
              </Button>
            </Box>
          ))}
        </Paper>
      )}
      
      {/* Filtros */}
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
            label="Mostrar resumo geral (sem filtro de período)"
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
              ? 'Resumo de todo o período' 
              : `Período: ${mesAno.format('MM/YYYY')}`
            }
          </Typography>
        </Box>
      </Paper>

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

      {/* Diálogo de Confirmação de Fatura */}
      <Dialog open={confirmDialogOpen} onClose={() => setConfirmDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Confirmar valor da fatura</DialogTitle>
        <DialogContent>
          {faturaParaConfirmar && (
            <Box sx={{ pt: 1 }}>
              <Typography variant="body2" color="text.secondary">
                Vencimento: {new Date(faturaParaConfirmar.data_vencimento).toLocaleDateString('pt-BR')}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Valor previsto: {formatCurrency(faturaParaConfirmar.valor_previsto || 0)}
              </Typography>
              <TextField
                fullWidth
                label="Valor real da fatura"
                type="number"
                value={valorFatura}
                onChange={(e) => setValorFatura(e.target.value)}
                inputProps={{ step: '0.01', min: '0' }}
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDialogOpen(false)}>Cancelar</Button>
          <Button onClick={confirmarFatura} variant="contained" color="warning">Confirmar</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default Dashboard;