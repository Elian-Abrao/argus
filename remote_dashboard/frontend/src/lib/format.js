const DATE_FORMATTER = new Intl.DateTimeFormat('pt-BR', {
  dateStyle: 'short',
  timeStyle: 'medium',
});

const TIME_FORMATTER = new Intl.DateTimeFormat('pt-BR', {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
});

export function formatDateTime(value) {
  if (!value) return '-';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value);
  return DATE_FORMATTER.format(parsed);
}

export function formatTime(value) {
  if (!value) return '-';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value);
  return TIME_FORMATTER.format(parsed);
}

export function formatDuration(startedAt, finishedAt) {
  if (!startedAt) return '-';
  const start = new Date(startedAt);
  const end = finishedAt ? new Date(finishedAt) : new Date();
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return '-';
  const minutes = Math.max(0, Math.floor((end.getTime() - start.getTime()) / 60000));
  const hours = Math.floor(minutes / 60);
  const restMinutes = minutes % 60;
  if (hours === 0) return `${restMinutes}m`;
  return `${hours}h ${String(restMinutes).padStart(2, '0')}m`;
}

export function normalizeStatus(status) {
  const normalized = String(status || '').toLowerCase();
  if (['running', 'in_progress'].includes(normalized)) return 'running';
  if (['completed', 'success', 'finished'].includes(normalized)) return 'completed';
  if (['failed', 'error', 'stopped', 'cancelled'].includes(normalized)) return 'failed';
  return 'unknown';
}

export function toNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function getErrorMessage(error) {
  if (!error) return 'Erro desconhecido.';
  if (typeof error === 'string') return error;
  return error.message || 'Erro inesperado.';
}

export function parseFlag(message) {
  if (!message) return { flagType: null, flagLines: [] };
  const upper = message.toUpperCase();
  let flagType = null;
  if (upper.includes('PROCESSO INICIADO')) flagType = 'start';
  if (upper.includes('PROCESSO FINALIZADO')) flagType = 'end';
  if (!flagType) return { flagType: null, flagLines: [] };

  const lines = message
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => {
      if (!line) return false;
      const upperLine = line.toUpperCase();
      return (
        upperLine.includes('PROCESSO INICIADO') ||
        upperLine.includes('PROCESSO FINALIZADO') ||
        line.startsWith('Data:') ||
        line.startsWith('Hora:') ||
        line.startsWith('Script:') ||
        line.startsWith('Pasta:')
      );
    });

  if (!lines.length) {
    lines.push(flagType === 'start' ? 'PROCESSO INICIADO' : 'PROCESSO FINALIZADO');
  }

  return { flagType, flagLines: lines };
}

export function mapLevelColor(level) {
  const normalized = String(level || '').toUpperCase();
  if (normalized === 'DEBUG') return 'text-indigo-700';
  if (normalized === 'INFO') return 'text-sky-700';
  if (normalized === 'WARNING') return 'text-amber-700';
  if (normalized === 'ERROR') return 'text-rose-700';
  if (normalized === 'CRITICAL') return 'text-fuchsia-700';
  return 'text-slate-700';
}
