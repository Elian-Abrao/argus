function BusyButton({ busy = false, children, className = '', ...props }) {
  return (
    <button
      {...props}
      disabled={busy || props.disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-xl border border-app-border bg-app-primary px-3.5 py-2 text-sm font-semibold text-[#4b2a75] transition hover:bg-app-accent hover:text-white disabled:cursor-not-allowed disabled:opacity-60 ${className}`}
    >
      {busy ? (
        <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-[#4b2a75]/35 border-t-[#4b2a75]" />
      ) : null}
      {children}
    </button>
  );
}

export default BusyButton;
