import { X, Mail, Paperclip, Download, Eye, FileSpreadsheet, FileText, FileImage, FileArchive, File } from 'lucide-react';
import { formatDateTime } from '../lib/format';
import { getEmailAttachmentUrl } from '../lib/api';

// ─── File type helpers ────────────────────────────────────────────────────────

const FILE_TYPE_MAP = {
    // Spreadsheets
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': { label: 'Excel (.xlsx)', icon: FileSpreadsheet, color: 'text-emerald-600', bg: 'bg-emerald-100' },
    'application/vnd.ms-excel': { label: 'Excel (.xls)', icon: FileSpreadsheet, color: 'text-emerald-600', bg: 'bg-emerald-100' },
    // Word
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': { label: 'Word (.docx)', icon: FileText, color: 'text-blue-600', bg: 'bg-blue-100' },
    'application/msword': { label: 'Word (.doc)', icon: FileText, color: 'text-blue-600', bg: 'bg-blue-100' },
    // PowerPoint
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': { label: 'PowerPoint (.pptx)', icon: File, color: 'text-orange-600', bg: 'bg-orange-100' },
    // PDF
    'application/pdf': { label: 'PDF', icon: FileText, color: 'text-red-600', bg: 'bg-red-100' },
    // Archives
    'application/zip': { label: 'ZIP', icon: FileArchive, color: 'text-yellow-600', bg: 'bg-yellow-100' },
    'application/vnd.rar': { label: 'RAR', icon: FileArchive, color: 'text-yellow-600', bg: 'bg-yellow-100' },
    'application/x-7z-compressed': { label: '7-Zip', icon: FileArchive, color: 'text-yellow-600', bg: 'bg-yellow-100' },
    'application/gzip': { label: 'GZip', icon: FileArchive, color: 'text-yellow-600', bg: 'bg-yellow-100' },
    // Text
    'text/plain': { label: 'Texto', icon: FileText, color: 'text-gray-600', bg: 'bg-gray-100' },
    'text/csv': { label: 'CSV', icon: FileSpreadsheet, color: 'text-teal-600', bg: 'bg-teal-100' },
    // Images
    'image/png': { label: 'Imagem PNG', icon: FileImage, color: 'text-purple-600', bg: 'bg-purple-100' },
    'image/jpeg': { label: 'Imagem JPG', icon: FileImage, color: 'text-purple-600', bg: 'bg-purple-100' },
    'image/gif': { label: 'Imagem GIF', icon: FileImage, color: 'text-purple-600', bg: 'bg-purple-100' },
    'image/webp': { label: 'Imagem WebP', icon: FileImage, color: 'text-purple-600', bg: 'bg-purple-100' },
    'image/svg+xml': { label: 'Imagem SVG', icon: FileImage, color: 'text-purple-600', bg: 'bg-purple-100' },
};

function getFileType(mimeType) {
    return FILE_TYPE_MAP[mimeType] || { label: mimeType || 'Arquivo', icon: File, color: 'text-gray-500', bg: 'bg-gray-100' };
}

function canPreviewInBrowser(attachment) {
    if (!attachment.preview_supported) return false;
    const mime = attachment.mime_type || '';
    // Only types the browser can natively render
    return mime.startsWith('image/') || mime === 'application/pdf' || mime === 'text/plain' || mime === 'text/csv';
}

// ─── Component ────────────────────────────────────────────────────────────────

function EmailDetailModal({ email, onClose }) {
    if (!email) return null;

    const sender = email.sender || 'smtp@logger.module';
    const initials = sender.split('@')[0].substring(0, 1).toUpperCase();

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm" onClick={onClose}>
            <div
                className="flex h-full max-h-[90vh] w-full max-w-4xl flex-col rounded-2xl border border-app-border bg-app-elevated shadow-2xl overflow-hidden"
                onClick={e => e.stopPropagation()}
            >
                {/* Modal Header */}
                <div className="flex items-center justify-between border-b border-app-border/60 px-6 py-4">
                    <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-app-primary/10 text-app-accent">
                            <Mail className="h-4 w-4" />
                        </div>
                        <h2 className="text-base font-semibold text-app-text truncate max-w-xl">
                            {email.subject || '(Sem assunto)'}
                        </h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="rounded-lg p-2 text-app-muted transition-colors hover:bg-app-primary/10 hover:text-app-text"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>

                {/* Email Reading Area */}
                <div className="flex-1 overflow-auto p-6 space-y-8">
                    {/* Sender / Recipients / Time */}
                    <div className="flex items-start gap-4">
                        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-app-accent/20 text-lg font-bold text-app-accent">
                            {initials}
                        </div>
                        <div className="flex flex-col gap-1 min-w-0 flex-1">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <span className="text-sm font-bold text-app-text">{sender}</span>
                                <span className="text-xs text-app-muted">{formatDateTime(email.sent_at)}</span>
                            </div>
                            <div className="text-xs text-app-muted flex flex-wrap gap-1">
                                <span className="font-semibold">Para:</span>
                                <span>{(email.recipients || []).join('; ') || 'Nenhum'}</span>
                            </div>
                            {email.bcc_recipients?.length > 0 && (
                                <div className="text-xs text-app-muted flex flex-wrap gap-1">
                                    <span className="font-semibold">Cco:</span>
                                    <span>{email.bcc_recipients.join('; ')}</span>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Attachments Section */}
                    {email.attachments?.length > 0 && (
                        <div className="rounded-xl border border-app-border bg-app-primary/5 p-4">
                            <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-app-muted">
                                <Paperclip className="h-3 w-3" />
                                Anexos ({email.attachments.length})
                            </div>
                            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                                {email.attachments.map((attachment) => {
                                    const fileType = getFileType(attachment.mime_type);
                                    const FileIcon = fileType.icon;
                                    const showPreview = canPreviewInBrowser(attachment);

                                    return (
                                        <div
                                            key={attachment.id}
                                            className="flex items-center justify-between gap-3 rounded-lg border border-app-border/60 bg-app-elevated/60 p-2.5"
                                        >
                                            <div className="flex items-center gap-2.5 min-w-0">
                                                <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${fileType.bg}`}>
                                                    <FileIcon className={`h-4 w-4 ${fileType.color}`} />
                                                </div>
                                                <div className="min-w-0">
                                                    <p className="truncate text-xs font-medium text-app-text" title={attachment.filename}>
                                                        {attachment.filename}
                                                    </p>
                                                    <p className="text-[10px] text-app-muted">
                                                        {fileType.label} · {formatBytes(attachment.size_bytes)}
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-1 shrink-0">
                                                {showPreview && (
                                                    <a
                                                        href={getEmailAttachmentUrl(email.id, attachment.id, 'preview')}
                                                        target="_blank"
                                                        rel="noreferrer"
                                                        className="flex h-7 w-7 items-center justify-center rounded-lg text-app-muted hover:bg-app-accent/10 hover:text-app-accent transition-colors"
                                                        title="Visualizar no navegador"
                                                    >
                                                        <Eye className="h-3.5 w-3.5" />
                                                    </a>
                                                )}
                                                <a
                                                    href={getEmailAttachmentUrl(email.id, attachment.id, 'download')}
                                                    download={attachment.filename}
                                                    className="flex h-7 w-7 items-center justify-center rounded-lg text-app-muted hover:bg-app-primary/10 hover:text-app-text transition-colors"
                                                    title="Fazer download"
                                                >
                                                    <Download className="h-3.5 w-3.5" />
                                                </a>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* Body Section */}
                    <div className="text-app-text min-h-[200px]">
                        {email.body_html ? (
                            <div
                                className="rounded-lg border border-app-border/40 bg-white p-6 text-gray-900 shadow-inner overflow-x-auto"
                                dangerouslySetInnerHTML={{ __html: email.body_html }}
                            />
                        ) : (
                            <pre className="whitespace-pre-wrap rounded-lg border border-app-border/40 bg-app-primary/5 p-6 font-sans text-sm leading-relaxed text-app-text">
                                {email.body_text || 'Sem conteúdo.'}
                            </pre>
                        )}
                    </div>

                    {email.error && (
                        <div className="rounded-lg border border-rose-500/20 bg-rose-500/10 p-4 text-xs text-rose-500">
                            <span className="font-bold">Erro técnico:</span> {email.error}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default EmailDetailModal;

function formatBytes(bytes) {
    if (bytes === null || bytes === undefined) return '0 B';
    const value = Number(bytes);
    if (!Number.isFinite(value) || value <= 0) return '0 B';
    if (value < 1024) return `${value} B`;
    const units = ['KB', 'MB', 'GB'];
    let size = value / 1024;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex += 1;
    }
    return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[unitIndex]}`;
}
