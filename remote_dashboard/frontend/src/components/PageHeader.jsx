function PageHeader({ title, subtitle, actions, extra }) {
  return (
    <header className="mb-8 flex flex-col gap-4 border-b border-app-border/40 pb-5 animate-fade-in-up">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-app-text">{title}</h1>
          {subtitle ? <p className="mt-1.5 text-sm text-app-muted">{subtitle}</p> : null}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
      </div>
      {extra ? <div>{extra}</div> : null}
    </header>
  );
}

export default PageHeader;
