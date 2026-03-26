function FilterBar({ children, onSubmit, className = '' }) {
  return (
    <form
      onSubmit={onSubmit}
      className={`grid gap-3 rounded-xl border border-app-border bg-app-surface/45 p-4 md:grid-cols-2 lg:grid-cols-4 ${className}`}
    >
      {children}
    </form>
  );
}

export default FilterBar;
