import { formatTime } from '../lib/format';
import StatusBadge from './StatusBadge';

function EmailCard({ email, active, onClick }) {
    const sender = email.sender || 'smtp@logger.module';
    const initials = sender
        .split('@')[0]
        .substring(0, 1)
        .toUpperCase();

    return (
        <div
            onClick={() => onClick(email)}
            className={`group relative flex cursor-pointer gap-3 border-b border-app-border/40 p-3 transition-colors hover:bg-app-primary/10 ${active ? 'bg-app-primary/20' : ''
                }`}
        >
            {/* Selected indicator bar (Outlook style) */}
            {active && (
                <div className="absolute left-0 top-0 h-full w-1 bg-app-accent" />
            )}

            {/* Avatar */}
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-app-accent/20 text-sm font-bold text-app-accent">
                {initials}
            </div>

            <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                <div className="flex items-center justify-between gap-2 text-[11px]">
                    <span className="truncate font-semibold text-app-text">
                        {sender}
                    </span>
                    <span className="shrink-0 text-app-muted">
                        {formatTime(email.sent_at)}
                    </span>
                </div>

                <div className="flex items-center justify-between gap-1">
                    <span className="truncate text-sm font-bold text-app-text">
                        {email.subject || '(Sem assunto)'}
                    </span>
                    <StatusBadge
                        status={email.status === 'falha' ? 'failed' : 'completed'}
                        className="h-4 !px-1.5 !py-0 !text-[8px]"
                    />
                </div>

                <p className="line-clamp-1 text-[11px] leading-tight text-app-muted">
                    {email.body_text || email.body_html?.replace(/<[^>]*>/g, '') || 'Sem conteúdo'}
                </p>
            </div>
        </div>
    );
}

export default EmailCard;
