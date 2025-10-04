// Nova implementação: abas por cartão com listagem de contas do cartão, criação de conta e totalizadores (mês atual + 5 próximos)
import React, { useEffect, useMemo, useState, useCallback } from 'react';
import {
  Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, TextField,
  Typography, Paper, IconButton, Divider, Tabs, Tab, Chip, Grid, Checkbox, FormControlLabel, MenuItem, LinearProgress, Tooltip, Snackbar, Alert, Switch
} from '@mui/material';
import { DataGrid, GridColDef, GridActionsCellItem } from '@mui/x-data-grid';
import { Add, Edit, Delete, Payment, Undo, AccountTree, Repeat } from '@mui/icons-material';
import dayjs, { Dayjs } from 'dayjs';
import TotalizadoresMeses, { TotalizadorValores } from '../components/TotalizadoresMeses';
import axios from 'axios';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';

interface Cartao {
  id: number;
  nome: string;
  bandeira?: string;
  limite?: number;
  dia_fechamento?: number;
  dia_vencimento?: number;
  ativo: boolean;
  created_at: string;
  updated_at: string;
  fatura_paga_mes_atual?: boolean;
  valor_fatura_pago?: number | null;
}

interface Categoria { id: number; nome: string; }

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
  eh_parcelado?: boolean;
  numero_parcela?: number;
  total_parcelas?: number;
  parcelas_restantes?: number;
  valor_total?: number;
  grupo_parcelamento?: string;
  eh_recorrente?: boolean;
  grupo_recorrencia?: string;
  valor_previsto?: number;
  valor_pago?: number;
}

const formasPagamento = [
  'Boleto', 'DDA', 'PIX', 'Cartão de Crédito', 'Cartão de Débito', 'Dinheiro', 'Transferência Bancária', 'Débito Automático'
];

const Cartoes: React.FC = () => {
  // Cartões e abas
  const [cartoes, setCartoes] = useState<Cartao[]>([]);
  const [abaAtual, setAbaAtual] = useState(0);
  const cartaoSelecionado = cartoes[abaAtual];
  const [carregandoCartoes, setCarregandoCartoes] = useState(true);

  // Contas do cartão selecionado
  const [contasCartao, setContasCartao] = useState<Conta[]>([]);
  const [loadingContas, setLoadingContas] = useState(false);
  const [mesFiltro, setMesFiltro] = useState<Dayjs>(dayjs());

  // Categorias (para criar contas)
  const [categorias, setCategorias] = useState<Categoria[]>([]);

  // Dialog de criação/edição de cartão
  const [dialogCartaoOpen, setDialogCartaoOpen] = useState(false);
  const [editingCartao, setEditingCartao] = useState<Cartao | null>(null);
  const [formCartao, setFormCartao] = useState({
    nome: '', bandeira: '', limite: '', dia_fechamento: '', dia_vencimento: ''
  });

  // Dialog de criação/edição de conta para o cartão
  const [dialogContaOpen, setDialogContaOpen] = useState(false);
  const [editingConta, setEditingConta] = useState<Conta | null>(null);
  const [formConta, setFormConta] = useState({
    descricao: '', valor: '', data_vencimento: dayjs(), categoria_id: '', forma_pagamento: '', observacoes: '',
    eh_parcelado: false as boolean, total_parcelas: '', parcelas_restantes: '', valor_total: '', eh_recorrente: false as boolean
  });

  // Dialog remover conta
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [contaParaDeletar, setContaParaDeletar] = useState<Conta | null>(null);
  const [parcelamentoInfo, setParcelamentoInfo] = useState<any>(null);

  // Pagamento
  const [pagamentoDialogOpen, setPagamentoDialogOpen] = useState(false);
  const [contaParaPagar, setContaParaPagar] = useState<Conta | null>(null);
  const [valorPagamento, setValorPagamento] = useState('');

  // Meses totalizadores (atual + 5 próximos)
  const meses = useMemo(() => {
    const base = dayjs();
    return Array.from({ length: 6 }, (_, i) => {
      const d = base.add(i, 'month');
      return { key: `m_${d.year()}_${d.month()+1}`, label: d.format('MM/YYYY'), mes: d.month()+1, ano: d.year() };
    });
  }, []);

  const formatCurrency = (v: number) => new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(v||0);

  const fetchCartoes = useCallback(async () => {
    setCarregandoCartoes(true);
    try {
      const res = await axios.get('/cartoes');
      setCartoes(res.data);
    } catch (e) { console.error(e); }
    finally { setCarregandoCartoes(false); }
  }, []);

  const fetchCategorias = useCallback(async () => {
    try { const r = await axios.get('/categorias'); setCategorias(r.data); } catch(e){ console.error(e);} }, []);

  const fetchContasCartao = useCallback(async () => {
    if(!cartaoSelecionado) { setContasCartao([]); return; }
    setLoadingContas(true);
    try {
      const r = await axios.get('/contas', { params: { cartao_id: cartaoSelecionado.id, mes: mesFiltro.month()+1, ano: mesFiltro.year() } });
      setContasCartao(r.data);
    } catch(e){ console.error(e);} finally { setLoadingContas(false);} }, [cartaoSelecionado, mesFiltro]);

  // (Removido placeholder de estimativasCartoes não utilizado)

  useEffect(() => { fetchCartoes(); fetchCategorias(); }, [fetchCartoes, fetchCategorias]);
  useEffect(() => { fetchContasCartao(); }, [fetchContasCartao]);
  useEffect(() => { setAbaAtual(0); }, [cartoes.length]);

  // (Removido bloco duplicado de totais agregados / resumo faturas - consolidado mais abaixo)

  // CRUD Cartão
  const salvarCartao = async () => {
    try {
      const payload = {
        nome: formCartao.nome,
        bandeira: formCartao.bandeira||null,
        limite: formCartao.limite? parseFloat(formCartao.limite): null,
        dia_fechamento: formCartao.dia_fechamento? parseInt(formCartao.dia_fechamento): null,
        dia_vencimento: formCartao.dia_vencimento? parseInt(formCartao.dia_vencimento): null,
        ativo: true
      };
      if(editingCartao) await axios.put(`/cartoes/${editingCartao.id}`, payload); else await axios.post('/cartoes', payload);
      setDialogCartaoOpen(false); setEditingCartao(null); setFormCartao({ nome:'', bandeira:'', limite:'', dia_fechamento:'', dia_vencimento:'' });
      fetchCartoes();
    } catch(e){ console.error(e); alert('Erro ao salvar cartão'); }
  };
  const deletarCartao = async (id:number) => { if(!window.confirm('Excluir cartão?')) return; try { await axios.delete(`/cartoes/${id}`); fetchCartoes(); } catch(e:any){ alert(e.response?.data?.detail||'Erro'); } };

  // CRUD Conta associada ao cartão
  const abrirNovaConta = () => { setEditingConta(null); setFormConta({ descricao:'', valor:'', data_vencimento: mesFiltro.startOf('month'), categoria_id:'', forma_pagamento:'Cartão de Crédito', observacoes:'', eh_parcelado:false, total_parcelas:'', parcelas_restantes:'', valor_total:'', eh_recorrente:false }); setDialogContaOpen(true); };
  const salvarConta = async () => {
    if(!cartaoSelecionado) return;
    try {
      const data = {
        descricao: formConta.descricao,
        valor: parseFloat(formConta.valor),
        data_vencimento: formConta.data_vencimento.format('YYYY-MM-DD'),
        categoria_id: parseInt(formConta.categoria_id),
        cartao_id: cartaoSelecionado.id,
        forma_pagamento: formConta.forma_pagamento || 'Cartão de Crédito',
        observacoes: formConta.observacoes || null,
        eh_parcelado: formConta.eh_parcelado,
        total_parcelas: formConta.eh_parcelado && formConta.total_parcelas? parseInt(formConta.total_parcelas): null,
        parcelas_restantes: formConta.eh_parcelado && formConta.parcelas_restantes? parseInt(formConta.parcelas_restantes): null,
        valor_total: formConta.eh_parcelado && formConta.valor_total? parseFloat(formConta.valor_total): null,
        eh_recorrente: formConta.eh_recorrente
      };
      if(editingConta) await axios.put(`/contas/${editingConta.id}`, data); else await axios.post('/contas', data);
      setDialogContaOpen(false); fetchContasCartao();
    } catch(e){ console.error(e); alert('Erro ao salvar conta'); }
  };
  const deletarConta = async (conta: Conta) => {
    setContaParaDeletar(conta);
    setParcelamentoInfo(null);
    try {
      const r = await axios.get(`/contas/${conta.id}/info-parcelamento`);
      setParcelamentoInfo(r.data);
    } catch(e){
      console.error('Erro ao buscar info parcelamento', e);
    } finally {
      setDeleteDialogOpen(true);
    }
  };
  const confirmarDeleteConta = async (deleteAll: boolean) => {
    if(!contaParaDeletar) return;
    try {
      await axios.delete(`/contas/${contaParaDeletar.id}`, { params: { deletar_todas_parcelas: deleteAll } });
      setDeleteDialogOpen(false);
      setContaParaDeletar(null);
      setParcelamentoInfo(null);
      fetchContasCartao();
    } catch(e){ console.error(e); alert('Erro ao deletar conta'); }
  };

  const pagarConta = (conta: Conta) => { setContaParaPagar(conta); setValorPagamento(conta.valor.toString()); setPagamentoDialogOpen(true); };
  const confirmarPagamento = async () => { if(!contaParaPagar) return; try { await axios.post(`/contas/${contaParaPagar.id}/pagar`, { valor_pago: parseFloat(valorPagamento) }); setPagamentoDialogOpen(false); setContaParaPagar(null); fetchContasCartao(); } catch(e){ console.error(e); } };
  const desmarcarPagamento = async (conta: Conta) => { try { await axios.post(`/contas/${conta.id}/desmarcar-pagamento`); fetchContasCartao(); } catch(e){ console.error(e);} };

  // Colunas contas do cartão
  const colContas: GridColDef[] = [
    { field: 'descricao', headerName: 'Descrição', flex: 1, minWidth: 200 },
  { field: 'valor', headerName: 'Valor', width: 110, renderCell: (p: any)=> formatCurrency(p.value) },
  { field: 'data_vencimento', headerName: 'Vencimento', width: 120, renderCell: (p: any)=> dayjs(p.value).format('DD/MM/YYYY') },
  { field: 'categoria', headerName: 'Categoria', width: 140, renderCell: (p: any)=> p.row.categoria?.nome || '-' },
  { field: 'tipo', headerName: 'Tipo', width: 90, renderCell: (p: any)=> <Box display='flex' gap={0.5}>{p.row.eh_parcelado && <AccountTree fontSize='small' color='primary'/>}{p.row.eh_recorrente && <Repeat fontSize='small' color='secondary'/>}{!p.row.eh_parcelado && !p.row.eh_recorrente && '-'}</Box> },
  { field: 'status', headerName: 'Status', width: 110, renderCell: (p: any)=> <Chip size='small' label={p.value} color={p.value==='pago'?'success': p.value==='vencido'?'error':'warning'} /> },
    { field: 'actions', type:'actions', headerName: 'Ações', width: 170, getActions: (params: any)=> {
      const conta: Conta = params.row as Conta;
      const ehFatura = /^Fatura Cartão/i.test(conta.descricao || '');
      const acoes = [
        <GridActionsCellItem key='edit' icon={<Edit/>} label='Editar' onClick={()=> { const c = conta; setEditingConta(c); setFormConta({ descricao:c.descricao, valor:c.valor.toString(), data_vencimento: dayjs(c.data_vencimento), categoria_id: c.categoria_id.toString(), forma_pagamento: c.forma_pagamento||'Cartão de Crédito', observacoes: c.observacoes||'', eh_parcelado: c.eh_parcelado||false, total_parcelas: c.total_parcelas?.toString()||'', parcelas_restantes: c.parcelas_restantes?.toString()||'', valor_total: c.valor_total?.toString()||'', eh_recorrente: c.eh_recorrente||false }); setDialogContaOpen(true); } }/>
      ];
      if (ehFatura) {
        acoes.push(
          <GridActionsCellItem key='pay' icon={<Payment/>} label='Pagar' onClick={()=> pagarConta(conta)} disabled={conta.status==='pago'} />,
          <GridActionsCellItem key='undo' icon={<Undo/>} label='Desmarcar' onClick={()=> desmarcarPagamento(conta)} disabled={conta.status!=='pago'} />
        );
      }
      acoes.push(<GridActionsCellItem key='del' icon={<Delete/>} label='Deletar' onClick={()=> deletarConta(conta)} />);
      return acoes;
    } }
  ];

  // Totalizadores do cartão selecionado (6 meses) - reutiliza endpoint estimativa
  const [estimativaCartaoMeses, setEstimativaCartaoMeses] = useState<any[]>([]);
  useEffect(()=> { const carregar = async ()=> { if(!cartaoSelecionado){ setEstimativaCartaoMeses([]); return;} try { const r = await axios.get(`/cartoes/${cartaoSelecionado.id}/estimativa`, { params: { meses: 6 } }); setEstimativaCartaoMeses(r.data); } catch(e){ console.error(e);} }; carregar(); }, [cartaoSelecionado]);

  const totalCartaoAtual = useMemo(()=> {
  const map: Record<string, number> = {}; meses.forEach((m: any,i: number)=> { map[m.key] = Number(estimativaCartaoMeses[i]?.valor_previsto||0); }); return map;
  }, [estimativaCartaoMeses, meses]);

  const shouldShowParcelamento = formConta.eh_parcelado;
  // Estados adicionais (inseridos posteriormente nas melhorias)
  const [totaisAgregados, setTotaisAgregados] = useState<Record<string, number>>({});
  const [resumoFaturas, setResumoFaturas] = useState<Record<string,{pago:number;vencido:number}>>({});
  const [resumoFaturasCartao, setResumoFaturasCartao] = useState<Record<string,{pago:number;vencido:number}>>({});
  const [snackbar, setSnackbar] = useState<{open:boolean;message:string;severity:'success'|'error'|'info'|'warning'}>({open:false,message:'',severity:'info'});
  const [mostrarZeros, setMostrarZeros] = useState(false);

  // Carregar totais agregados e resumo de faturas globais
  useEffect(()=> {
    const carregar = async () => {
      const base: Record<string, number> = {}; meses.forEach((m: any)=> base[m.key]=0);
      await Promise.all(cartoes.map(async (c: Cartao) => {
        try { const r = await axios.get(`/cartoes/${c.id}/estimativa`, { params: { meses: 6 } });
          r.data.forEach((d: any, idx: number)=> { const mKey = meses[idx]?.key; if(mKey) base[mKey] += Number(d.valor_previsto || 0); });
        } catch(err){ console.error('estimativa cartao', c.id, err); }
      }));
      setTotaisAgregados(base);
      try {
        const rf = await axios.get('/cartoes/resumo-faturas', { params: { meses: 6 } });
        const map: Record<string,{pago:number;vencido:number}> = {};
        rf.data.forEach((item:any)=> { const key = `m_${item.ano}_${item.mes}`; map[key] = { pago:Number(item.valor_faturas_pagas||0), vencido:Number(item.valor_faturas_pendentes_vencidas||0) }; });
        setResumoFaturas(map);
      } catch(err){ console.error('resumo faturas', err); }
    };
    if(cartoes.length>0) carregar(); else { setTotaisAgregados({}); setResumoFaturas({}); }
  }, [cartoes, meses]);

  // Resumo por cartão selecionado
  useEffect(()=> {
    const carregar = async () => {
      if(!cartaoSelecionado){ setResumoFaturasCartao({}); return; }
      try {
        const r = await axios.get(`/cartoes/${cartaoSelecionado.id}/resumo-faturas`, { params: { meses: 6 } });
        const map: Record<string,{pago:number;vencido:number}> = {};
        r.data.forEach((item:any)=> { const key = `m_${item.ano}_${item.mes}`; map[key] = { pago:Number(item.valor_faturas_pagas||0), vencido:Number(item.valor_faturas_pendentes_vencidas||0) }; });
        setResumoFaturasCartao(map);
      } catch(err){ console.error('resumo faturas cartao', err); }
    };
    carregar();
  }, [cartaoSelecionado]);
  
  const handleCloseSnackbar = (_e?: React.SyntheticEvent | Event, reason?: string) => {
    if (reason === 'clickaway') return;
    setSnackbar((s: {open:boolean;message:string;severity:'success'|'error'|'info'|'warning'}) => ({ ...s, open:false }));
  };
  return (
    <>
      <Box display='flex' justifyContent='space-between' alignItems='center' mb={3}>
        <Typography variant='h4'>Cartões</Typography>
        <Box display='flex' gap={2}>
          <Button variant='outlined' startIcon={<Add/>} onClick={()=> { setEditingCartao(null); setFormCartao({ nome:'', bandeira:'', limite:'', dia_fechamento:'', dia_vencimento:'' }); setDialogCartaoOpen(true); }}>Novo Cartão</Button>
          {cartaoSelecionado && (
            <Button variant='contained' startIcon={<Add/>} onClick={abrirNovaConta}>Nova Conta neste Cartão</Button>
          )}
        </Box>
      </Box>

      {/* Totalizadores agregados reutilizando componente */}
      {(() => {
        const dataMap: Record<string, TotalizadorValores> = {};
        meses.forEach((m: any) => {
          dataMap[m.key] = {
            previsto: Number(totaisAgregados[m.key] || 0),
            pago: Number(resumoFaturas[m.key]?.pago || 0),
            vencido: Number(resumoFaturas[m.key]?.vencido || 0)
          };
        });
        return (
          <TotalizadoresMeses
            meses={meses}
            data={dataMap}
            title='Totais (todos os cartões) - Mês atual + 5 próximos'
            showZeros={mostrarZeros}
            setShowZeros={setMostrarZeros}
            colorScheme='blue'
            onSelectMes={(_label: string, mes: number, ano: number) => {
              setMesFiltro(dayjs(`${ano}-${String(mes).padStart(2,'0')}-01`));
              setSnackbar({ open:true, message:`Filtro geral ajustado para ${String(mes).padStart(2,'0')}/${ano}`, severity:'info' });
            }}
          />
        );
      })()}

      {/* Abas de cartões */}
      <Paper sx={{ p:0 }}>
        <Tabs
          value={abaAtual}
          onChange={(_e: any, v: number)=> setAbaAtual(v)}
          variant='scrollable'
          scrollButtons='auto'
          sx={{ px:1, '& .MuiTab-root': { textTransform:'none', fontWeight:500, minHeight:48 }, '& .Mui-selected': { backgroundColor:'#f1f5f9', borderRadius:'8px 8px 0 0' } }}
        >
          {cartoes.map((c: Cartao)=> (
            <Tab key={c.id} label={<Typography variant='body2' fontWeight={600}>{c.nome}</Typography>} />
          ))}
        </Tabs>
        <Divider/>
        {cartaoSelecionado ? (
          <Box p={2}>
            <Box display='flex' alignItems='center' gap={2} mb={2}>
              <DatePicker
                label='Mês'
                value={mesFiltro}
                onChange={(nv: Dayjs | null)=> setMesFiltro(nv||dayjs())}
                views={['year','month']}
                format='MM/YYYY'
              />
              <Typography variant='body2' color='text.secondary'>Exibindo contas do mês selecionado para este cartão.</Typography>
            </Box>
            <Box mb={2}>
              <Typography variant='subtitle2' gutterBottom>Estimativa / Faturas - Mês atual + 5</Typography>
              <Box display='flex' gap={2} sx={{ overflowX:'auto' }}>
                {meses.map((m: any, idx: number) => {
                  const valorPrevisto = totalCartaoAtual[m.key]||0;
                  const resumo = resumoFaturasCartao[m.key];
                  if(!mostrarZeros && valorPrevisto===0 && (!resumo || (resumo.pago===0 && resumo.vencido===0))) return null;
                  const isMesAtual = idx===0;
                  const pago = resumo?.pago||0;
                  const vencido = resumo?.vencido||0;
                  const faturaPaga = isMesAtual && cartaoSelecionado?.fatura_paga_mes_atual;
                  const progressoLimite = cartaoSelecionado?.limite ? Math.min(100, (valorPrevisto/(cartaoSelecionado.limite||1))*100): null;
                  return (
                    <Tooltip key={m.key} title={`Previsto: ${formatCurrency(valorPrevisto)} | Pago: ${formatCurrency(pago)} | Vencido: ${formatCurrency(vencido)}`}>
                      <Box sx={{ minWidth:170, p:1.1, borderRadius:2, backgroundColor: faturaPaga? '#ecfdf5' : (isMesAtual? '#f0f9ff':'#f8fafc'), border:'1px solid', borderColor: faturaPaga? '#34d399': (isMesAtual? '#38bdf8':'#e2e8f0'), display:'flex', flexDirection:'column', gap:0.35, cursor:'pointer' }}
                        onClick={()=> { const [mm,yy]=m.label.split('/'); setMesFiltro(dayjs(`${yy}-${mm}-01`)); setSnackbar({open:true,message:`Filtro do cartão ajustado para ${m.label}`,severity:'info'}); }}>
                        <Typography variant='caption' color='text.secondary'>{m.label}</Typography>
                        <Typography variant='body2' fontWeight={600}>{formatCurrency(valorPrevisto)}</Typography>
                        {pago>0 && <Typography variant='caption' color='success.main'>Pago: {formatCurrency(pago)}</Typography>}
                        {vencido>0 && <Typography variant='caption' color='error.main'>Vencido: {formatCurrency(vencido)}</Typography>}
                        {faturaPaga && <Chip size='small' color='success' label='Fatura Paga' />}
                        {progressoLimite !== null && (
                          <Box mt={0.3}>
                            <LinearProgress variant='determinate' value={progressoLimite} sx={{ height:6, borderRadius:3 }} />
                            <Typography variant='caption' color='text.secondary'>Limite: {progressoLimite.toFixed(0)}%</Typography>
                          </Box>
                        )}
                      </Box>
                    </Tooltip>
                  );
                })}
              </Box>
            </Box>
            <div style={{ height: 520, width: '100%' }}>
              <DataGrid
                rows={contasCartao}
                columns={colContas}
                loading={loadingContas}
                getRowId={(r: any)=> r.id}
                disableRowSelectionOnClick
              />
            </div>
          </Box>
        ) : (
          <Box p={3}><Typography>Nenhum cartão cadastrado.</Typography></Box>
        )}
      </Paper>

      {/* Dialog Cartão */}
      <Dialog open={dialogCartaoOpen} onClose={()=> setDialogCartaoOpen(false)} maxWidth='sm' fullWidth>
        <DialogTitle>{editingCartao? 'Editar Cartão':'Novo Cartão'}</DialogTitle>
        <DialogContent>
          <TextField fullWidth margin='dense' label='Nome' value={formCartao.nome} onChange={(e: React.ChangeEvent<HTMLInputElement>)=> setFormCartao({...formCartao, nome:e.target.value})} />
          <TextField fullWidth margin='dense' label='Bandeira' value={formCartao.bandeira} onChange={(e: React.ChangeEvent<HTMLInputElement>)=> setFormCartao({...formCartao, bandeira:e.target.value})} />
            <TextField fullWidth margin='dense' type='number' label='Limite' value={formCartao.limite} onChange={(e: React.ChangeEvent<HTMLInputElement>)=> setFormCartao({...formCartao, limite:e.target.value})} />
            <TextField fullWidth margin='dense' type='number' label='Dia de Fechamento' value={formCartao.dia_fechamento} onChange={(e: React.ChangeEvent<HTMLInputElement>)=> setFormCartao({...formCartao, dia_fechamento:e.target.value})} />
            <TextField fullWidth margin='dense' type='number' label='Dia de Vencimento' value={formCartao.dia_vencimento} onChange={(e: React.ChangeEvent<HTMLInputElement>)=> setFormCartao({...formCartao, dia_vencimento:e.target.value})} />
          {editingCartao && (
            <Button color='error' sx={{ mt:1 }} onClick={()=> deletarCartao(editingCartao.id)}>Excluir Cartão</Button>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={()=> setDialogCartaoOpen(false)}>Cancelar</Button>
          <Button variant='contained' onClick={salvarCartao}>Salvar</Button>
        </DialogActions>
      </Dialog>

      {/* Dialog Conta */}
      <Dialog open={dialogContaOpen} onClose={()=> setDialogContaOpen(false)} maxWidth='sm' fullWidth>
        <DialogTitle>{editingConta? 'Editar Conta do Cartão':'Nova Conta do Cartão'}</DialogTitle>
        <DialogContent>
          <TextField margin='dense' label='Descrição' fullWidth value={formConta.descricao} onChange={(e: React.ChangeEvent<HTMLInputElement>)=> setFormConta({...formConta, descricao:e.target.value})} />
          <TextField margin='dense' label='Valor' type='number' fullWidth value={formConta.valor} onChange={(e: React.ChangeEvent<HTMLInputElement>)=> setFormConta({...formConta, valor:e.target.value})} />
          <DatePicker label='Data de Vencimento' value={formConta.data_vencimento} onChange={(nv: Dayjs | null)=> setFormConta({...formConta, data_vencimento: nv||dayjs()})} slotProps={{ textField: { fullWidth:true, margin:'dense' } }} />
          <TextField margin='dense' label='Categoria' select fullWidth value={formConta.categoria_id} onChange={(e: any)=> setFormConta({...formConta, categoria_id:e.target.value})}>
            {categorias.map((c: Categoria)=> <MenuItem key={c.id} value={c.id}>{c.nome}</MenuItem>)}
          </TextField>
          <TextField margin='dense' label='Forma de Pagamento' select fullWidth value={formConta.forma_pagamento} onChange={(e: any)=> setFormConta({...formConta, forma_pagamento:e.target.value})}>
            {formasPagamento.map((f: string)=> <MenuItem key={f} value={f}>{f}</MenuItem>)}
          </TextField>
          <FormControlLabel control={<Checkbox checked={formConta.eh_parcelado} onChange={(e: React.ChangeEvent<HTMLInputElement>)=> setFormConta({ ...formConta, eh_parcelado: e.target.checked, eh_recorrente: e.target.checked? false: formConta.eh_recorrente })} />} label='Compra Parcelada'/>
          <FormControlLabel control={<Checkbox checked={formConta.eh_recorrente} onChange={(e: React.ChangeEvent<HTMLInputElement>)=> setFormConta({ ...formConta, eh_recorrente: e.target.checked, eh_parcelado: e.target.checked? false: formConta.eh_parcelado })} disabled={formConta.eh_parcelado} />} label='Conta Recorrente (6 meses)'/>
          {formConta.eh_recorrente && (<Typography variant='caption' color='text.secondary'>Serão criadas cópias para os próximos 6 meses.</Typography>)}
          {shouldShowParcelamento && (
            <Grid container spacing={2} sx={{ mt:1 }}>
              <Grid item xs={6}><TextField fullWidth margin='dense' type='number' label='Total de Parcelas' value={formConta.total_parcelas} onChange={(e: React.ChangeEvent<HTMLInputElement>)=> setFormConta({...formConta, total_parcelas:e.target.value})} /></Grid>
              <Grid item xs={6}><TextField fullWidth margin='dense' type='number' label='Parcelas Restantes' value={formConta.parcelas_restantes} onChange={(e: React.ChangeEvent<HTMLInputElement>)=> setFormConta({...formConta, parcelas_restantes:e.target.value})} /></Grid>
              <Grid item xs={12}><TextField fullWidth margin='dense' type='number' label='Valor Total (opcional)' value={formConta.valor_total} onChange={(e: React.ChangeEvent<HTMLInputElement>)=> setFormConta({...formConta, valor_total:e.target.value})} /></Grid>
            </Grid>
          )}
          <TextField margin='dense' label='Observações' fullWidth multiline rows={3} value={formConta.observacoes} onChange={(e: React.ChangeEvent<HTMLInputElement>)=> setFormConta({...formConta, observacoes:e.target.value})} />
        </DialogContent>
        <DialogActions>
          <Button onClick={()=> setDialogContaOpen(false)}>Cancelar</Button>
          <Button variant='contained' onClick={salvarConta}>Salvar</Button>
        </DialogActions>
      </Dialog>

      {/* Dialog Delete Conta */}
      <Dialog open={deleteDialogOpen} onClose={()=> { setDeleteDialogOpen(false); setParcelamentoInfo(null); }} maxWidth='sm' fullWidth>
        <DialogTitle>Confirmar Exclusão</DialogTitle>
        <DialogContent>
          {parcelamentoInfo?.eh_parcelado ? (
            <Box>
              <Typography variant='body2' gutterBottom>
                Esta conta faz parte de um parcelamento ({parcelamentoInfo.numero_parcela}/{parcelamentoInfo.total_parcelas}).
              </Typography>
              <Typography variant='body2' gutterBottom>
                O que deseja fazer?
              </Typography>
            </Box>
          ) : (
            <Typography variant='body2'>Deseja remover a conta '{contaParaDeletar?.descricao}'?</Typography>
          )}
        </DialogContent>
        <DialogActions sx={{ display:'flex', flexWrap:'wrap', gap:1 }}>
          <Button onClick={()=> { setDeleteDialogOpen(false); setParcelamentoInfo(null); }}>Cancelar</Button>
          {parcelamentoInfo?.eh_parcelado ? (
            <>
              <Button variant='contained' color='warning' onClick={()=> confirmarDeleteConta(false)}>Excluir Apenas Esta Parcela</Button>
              <Button variant='contained' color='error' onClick={()=> confirmarDeleteConta(true)}>Excluir Todas as Parcelas</Button>
            </>
          ) : (
            <Button variant='contained' color='error' onClick={()=> confirmarDeleteConta(false)}>Excluir</Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Pagamento */}
      <Dialog open={pagamentoDialogOpen} onClose={()=> setPagamentoDialogOpen(false)} maxWidth='xs' fullWidth>
        <DialogTitle>Confirmar Pagamento</DialogTitle>
        <DialogContent>
          <Typography variant='body2'><strong>Conta:</strong> {contaParaPagar?.descricao}</Typography>
          <Typography variant='body2' color='text.secondary'>Valor original: {contaParaPagar && formatCurrency(contaParaPagar.valor)}</Typography>
          <TextField fullWidth margin='dense' label='Valor Pago' type='number' value={valorPagamento} onChange={e=> setValorPagamento(e.target.value)} />
        </DialogContent>
        <DialogActions>
          <Button onClick={()=> setPagamentoDialogOpen(false)}>Cancelar</Button>
          <Button variant='contained' onClick={confirmarPagamento} disabled={!valorPagamento}>Confirmar</Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar Feedback */}
      <Snackbar open={snackbar.open} autoHideDuration={3000} onClose={handleCloseSnackbar} anchorOrigin={{ vertical:'bottom', horizontal:'right' }}>
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} variant='filled' sx={{ width:'100%' }}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </>
  );
};

export default Cartoes;
