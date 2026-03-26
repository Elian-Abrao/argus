function MetricCard({ label, value, icon: Icon, tone = 'primary', detail }) {
  const toneClass = {
    primary: 'text-[#6d3bb2] bg-app-primary/20',
    success: 'text-app-success bg-app-success/15',
    warning: 'text-app-warning bg-app-warning/15',
    danger: 'text-app-danger bg-app-danger/15',
    neutral: 'text-app-accent bg-app-accent/15',
  }[tone] || 'text-[#6d3bb2] bg-app-primary/20';

  return (
    <article className="rounded-2xl border border-app-border bg-app-elevated/80 p-4 shadow-card animate-fade-in-up">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.12em] text-app-muted">{label}</p>
          <p className="mt-2 text-2xl font-semibold text-app-text">{value}</p>
          {detail ? <p className="mt-1 text-xs text-app-muted">{detail}</p> : null}
        </div>
        {Icon ? (
          <span className={`inline-flex h-10 w-10 items-center justify-center rounded-xl ${toneClass}`}>
            <Icon className="h-5 w-5" />
          </span>
        ) : null}
      </div>
    </article>
  );
}

export default MetricCard;
