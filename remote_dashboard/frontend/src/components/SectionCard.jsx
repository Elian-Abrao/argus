function SectionCard({ id, title, subtitle, actions, children, className = '' }) {
  return (
    <section id={id} className={`rounded-2xl border border-app-border bg-app-elevated/80 shadow-card ${className}`}>
      {(title || subtitle || actions) && (
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-app-border/80 px-5 py-4">
          <div>
            {title ? <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-app-muted">{title}</h2> : null}
            {subtitle ? <p className="mt-0.5 text-xs text-app-muted">{subtitle}</p> : null}
          </div>
          {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export default SectionCard;
