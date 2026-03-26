function LoadingState({ label = 'Carregando dados...' }) {
  return (
    <div className="rounded-2xl border border-app-border bg-app-elevated/70 p-8 text-center shadow-card animate-fade-in-up">
      <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-app-primary/30 border-t-app-primary" />
      <p className="mt-3 text-sm text-app-muted">{label}</p>
    </div>
  );
}

export default LoadingState;
