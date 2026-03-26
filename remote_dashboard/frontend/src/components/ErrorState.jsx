import BusyButton from './BusyButton';

function ErrorState({ title = 'Falha ao carregar', message, onRetry, busy = false }) {
  return (
    <div className="rounded-2xl border border-rose-300/55 bg-rose-100/65 px-6 py-7 text-center text-rose-900">
      <h3 className="text-base font-semibold">{title}</h3>
      <p className="mt-1 text-sm text-rose-900/80">{message || 'Tente novamente em instantes.'}</p>
      {onRetry ? (
        <div className="mt-4">
          <BusyButton busy={busy} type="button" onClick={onRetry}>
            Tentar novamente
          </BusyButton>
        </div>
      ) : null}
    </div>
  );
}

export default ErrorState;
