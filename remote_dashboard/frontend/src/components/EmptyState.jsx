function EmptyState({ title = 'Sem dados', message = 'Nenhum registro encontrado para o filtro atual.' }) {
  return (
    <div className="rounded-2xl border border-dashed border-app-border bg-app-elevated/60 px-6 py-10 text-center">
      <h3 className="text-base font-semibold text-app-text">{title}</h3>
      <p className="mt-1 text-sm text-app-muted">{message}</p>
    </div>
  );
}

export default EmptyState;
