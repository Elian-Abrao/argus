import { Link } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import SectionCard from '../components/SectionCard';

function NotFoundPage() {
  return (
    <>
      <PageHeader
        title="Pagina nao encontrada"
        subtitle="A rota solicitada nao existe no dashboard operacional."
      />
      <SectionCard>
        <div className="space-y-3 text-sm text-app-muted">
          <p>Verifique o endereco ou retorne para a visao principal.</p>
          <Link
            to="/"
            className="inline-flex rounded-xl border border-app-border bg-app-primary px-4 py-2 font-semibold text-[#4b2a75] transition hover:bg-app-accent hover:text-white"
          >
            Voltar para visao geral
          </Link>
        </div>
      </SectionCard>
    </>
  );
}

export default NotFoundPage;
