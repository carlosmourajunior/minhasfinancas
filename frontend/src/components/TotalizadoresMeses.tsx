import React, { useState } from 'react';
import { Box, Paper, Typography, FormControlLabel, Switch, Tooltip } from '@mui/material';

export interface MesInfo { key: string; label: string; mes: number; ano: number; }
export interface TotalizadorValores { previsto: number; pago: number; vencido: number; }

interface TotalizadoresMesesProps {
  meses: MesInfo[];
  data: Record<string, TotalizadorValores>; // chave = mes.key
  loading?: boolean;
  title?: string;
  onSelectMes?: (label: string, mes: number, ano: number) => void;
  showZeros?: boolean;               // controle externo opcional
  setShowZeros?: (v: boolean) => void; // se fornecido, mostra toggle
  colorScheme?: 'dark' | 'blue';
  tooltipFormatter?: (val: TotalizadorValores) => string;
}

const schemeBackground: Record<string,string> = {
  dark: 'linear-gradient(135deg,#334155,#1e293b)',
  blue: 'linear-gradient(135deg,#1e3a8a,#1d4ed8)'
};

const TotalizadoresMeses: React.FC<TotalizadoresMesesProps> = ({
  meses,
  data,
  loading,
  title,
  onSelectMes,
  showZeros,
  setShowZeros,
  colorScheme = 'blue',
  tooltipFormatter
}) => {
  const [internalShowZeros, setInternalShowZeros] = useState(false);
  const effectiveShowZeros = showZeros ?? internalShowZeros;
  const toggleShowZeros = (v: boolean) => {
    if (setShowZeros) setShowZeros(v); else setInternalShowZeros(v);
  };

  const formatCurrency = (v: number) => new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(v||0);

  const defaultTooltip = (t: TotalizadorValores) => `Previsto: ${formatCurrency(t.previsto)} | Pago: ${formatCurrency(t.pago)} | Vencido: ${formatCurrency(t.vencido)}`;

  return (
    <Paper sx={{ p:2, mb:3, background: schemeBackground[colorScheme], color:'#fff' }}>
      <Box display='flex' alignItems='center' justifyContent='space-between' mb={1} flexWrap='wrap' gap={2}>
        {title && <Typography variant='subtitle1' fontWeight={600}>{title}</Typography>}
        { (setShowZeros || showZeros === undefined) && (
          <FormControlLabel control={<Switch size='small' checked={effectiveShowZeros} onChange={(e)=> toggleShowZeros(e.target.checked)} />} label={<Typography variant='caption' sx={{ color:'#fff' }}>Mostrar meses zerados</Typography>} />
        ) }
      </Box>
      <Box display='flex' gap={2} sx={{ overflowX:'auto' }}>
        {meses.map(m => {
          const t = data[m.key] || { previsto:0, pago:0, vencido:0 };
          const isZero = t.previsto===0 && t.pago===0 && t.vencido===0;
          if(!effectiveShowZeros && !loading && isZero) return null;
          const tooltip = tooltipFormatter? tooltipFormatter(t) : defaultTooltip(t);
          return (
            <Tooltip key={m.key} title={tooltip}>
              <Box onClick={()=> onSelectMes && onSelectMes(m.label, m.mes, m.ano)}
                   sx={{ minWidth:160, p:1.1, borderRadius:2, backgroundColor:'rgba(255,255,255,0.15)', backdropFilter:'blur(4px)', cursor: onSelectMes? 'pointer':'default', boxShadow:'inset 0 0 0 1px rgba(255,255,255,0.15)', transition:'0.2s', '&:hover': { backgroundColor:'rgba(255,255,255,0.22)' } }}>
                <Typography variant='caption' sx={{ opacity:0.85 }}>{m.label}</Typography>
                {loading && !data[m.key] ? (
                  <Typography variant='body2' fontWeight={600}>Carregando...</Typography>
                ) : (
                  <>
                    <Typography variant='body2' fontWeight={600}>{formatCurrency(t.previsto)}</Typography>
                    {t.pago>0 && <Typography variant='caption' sx={{ display:'block', color:'#bbf7d0' }}>Pago: {formatCurrency(t.pago)}</Typography>}
                    {t.vencido>0 && <Typography variant='caption' sx={{ display:'block', color:'#fecaca' }}>Vencido: {formatCurrency(t.vencido)}</Typography>}
                  </>
                )}
              </Box>
            </Tooltip>
          );
        })}
      </Box>
    </Paper>
  );
};

export default TotalizadoresMeses;
