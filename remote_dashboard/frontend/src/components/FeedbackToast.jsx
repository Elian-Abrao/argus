import { CheckCircle2, XCircle } from 'lucide-react';

function FeedbackToast({ type = 'success', message, onClose }) {
  if (!message) return null;

  const isSuccess = type === 'success';

  return (
    <div
      role="status"
      className={`fixed bottom-4 right-4 z-50 flex max-w-sm items-center gap-3 rounded-xl border px-4 py-3 shadow-glow ${
        isSuccess
          ? 'border-emerald-400/45 bg-emerald-500/90 text-emerald-50'
          : 'border-rose-400/45 bg-rose-500/90 text-rose-50'
      }`}
    >
      {isSuccess ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
      <p className="text-sm">{message}</p>
      <button
        type="button"
        onClick={onClose}
        className="ml-auto rounded-md px-2 py-1 text-xs font-semibold text-current/90 transition hover:bg-white/25"
      >
        Fechar
      </button>
    </div>
  );
}

export default FeedbackToast;
