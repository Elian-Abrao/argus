"""Seed a reusable demo dataset for the Argus dashboard."""

from __future__ import annotations

import os
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from remote_api import models  # noqa: E402
from remote_api.database import ensure_database_schema, session_scope  # noqa: E402


DEMO_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "argus-demo-seed-v1")


def demo_uuid(name: str) -> uuid.UUID:
    return uuid.uuid5(DEMO_NAMESPACE, name)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def upsert(session, model, entity_id: uuid.UUID, **fields):
    obj = session.get(model, entity_id)
    if obj is None:
        obj = model(id=entity_id, **fields)
        session.add(obj)
    else:
        for key, value in fields.items():
            setattr(obj, key, value)
    session.flush()
    return obj


def evenly_spaced_times(start: datetime, end: datetime, count: int) -> list[datetime]:
    if count <= 1:
        return [start]
    total_seconds = max(1.0, (end - start).total_seconds())
    return [
        start + timedelta(seconds=(total_seconds * index) / (count - 1))
        for index in range(count)
    ]


@dataclass(frozen=True)
class RunSeed:
    name: str
    instance_key: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    pid: int
    user_name: str
    config_version: str
    origin: str
    summary: str


def build_logs(run: RunSeed, automation_code: str, client_name: str) -> list[dict]:
    if run.status == "completed":
        events = [
            ("INFO", "Execucao iniciada", "main"),
            ("INFO", "Carregando parametros da automacao", "main>bootstrap"),
            ("INFO", f"Cliente alvo: {client_name}", "main>bootstrap"),
            ("INFO", f"Iniciando robo {automation_code}", "main>orchestrate"),
            ("INFO", "Coletando dados de origem", "main>extract"),
            ("INFO", "Validando consistencia do lote", "main>validate"),
            ("INFO", "Persistindo alteracoes no sistema destino", "main>persist"),
            ("SUCCESS", run.summary, "main"),
        ]
    elif run.status == "failed":
        events = [
            ("INFO", "Execucao iniciada", "main"),
            ("INFO", "Carregando parametros da automacao", "main>bootstrap"),
            ("INFO", f"Cliente alvo: {client_name}", "main>bootstrap"),
            ("INFO", "Autenticando no portal do fornecedor", "main>extract"),
            ("WARNING", "Portal respondeu com lentidao acima do esperado", "main>extract"),
            ("ERROR", run.summary, "main>validate"),
            ("INFO", "Encerrando fluxo com falha controlada", "main"),
        ]
    else:
        events = [
            ("INFO", "Execucao iniciada", "main"),
            ("INFO", "Carregando parametros da automacao", "main>bootstrap"),
            ("INFO", f"Cliente alvo: {client_name}", "main>bootstrap"),
            ("INFO", "Conectando ao sistema remoto", "main>extract"),
            ("INFO", "Processando lote atual", "main>extract"),
            ("INFO", run.summary, "main>persist"),
        ]

    target_end = run.finished_at or utc_now()
    return [
        {
            "sequence": index + 1,
            "ts": ts,
            "level": level,
            "logger_name": "argus.demo",
            "message": message,
            "context": {
                "call_chain": chain,
                "automation_code": automation_code,
                "source": "demo-seed",
            },
            "extra": {
                "client_name": client_name,
                "run_name": run.name,
            },
        }
        for index, ((level, message, chain), ts) in enumerate(
            zip(events, evenly_spaced_times(run.started_at, target_end, len(events))),
        )
    ]


def seed_demo_data() -> dict[str, int]:
    now = utc_now()

    client_rows = [
        {
            "key": "client-acme",
            "name": "Acme Foods",
            "external_code": "ACME",
            "contact_email": "operacoes@acmefoods.example",
        },
        {
            "key": "client-blue",
            "name": "Blue Logistics",
            "external_code": "BLUE",
            "contact_email": "rpa@bluelogistics.example",
        },
    ]

    host_rows = [
        {
            "key": "host-sp01",
            "hostname": "bot-sp01",
            "display_name": "Sao Paulo - Producao",
            "ip_address": "10.20.1.21",
            "root_folder": r"C:\Bots\Fiscal\sp01",
            "environment": "production",
            "tags": {"region": "sp", "criticality": "high"},
            "last_agent_ping": now - timedelta(minutes=2),
        },
        {
            "key": "host-rj01",
            "hostname": "bot-rj01",
            "display_name": "Rio - Financeiro",
            "ip_address": "10.20.2.15",
            "root_folder": r"C:\Bots\Financeiro\rj01",
            "environment": "production",
            "tags": {"region": "rj", "criticality": "medium"},
            "last_agent_ping": now - timedelta(minutes=7),
        },
        {
            "key": "host-hml01",
            "hostname": "bot-hml01",
            "display_name": "Homologacao",
            "ip_address": "10.30.9.10",
            "root_folder": r"C:\Bots\HML\geral",
            "environment": "staging",
            "tags": {"region": "sp", "criticality": "low"},
            "last_agent_ping": now - timedelta(hours=3),
        },
    ]

    automation_rows = [
        {
            "key": "automation-nfse",
            "code": "DEMO-NFSE",
            "name": "Emissao de NFSe",
            "description": "Emite notas fiscais de servico e envia comprovantes.",
            "owner_team": "Fiscal",
        },
        {
            "key": "automation-conciliacao",
            "code": "DEMO-CONCILIACAO",
            "name": "Conciliacao Bancaria",
            "description": "Concilia extratos e baixa pendencias financeiras.",
            "owner_team": "Financeiro",
        },
        {
            "key": "automation-cobranca",
            "code": "DEMO-COBRANCA",
            "name": "Cobranca de Inadimplentes",
            "description": "Gera lotes de cobranca e notifica clientes em atraso.",
            "owner_team": "Cobranca",
        },
    ]

    instance_rows = [
        {
            "key": "instance-acme-nfse",
            "automation_key": "automation-nfse",
            "client_key": "client-acme",
            "host_key": "host-sp01",
            "deployment_tag": "prod-acme",
            "config_signature": "nfse-v2026.03",
            "script": "main.py",
            "default_args": ["--ambiente=producao"],
            "available_args": [
                {"name": "competencia", "label": "Competencia", "type": "named", "required": True},
                {"name": "reprocessar", "label": "Reprocessar", "type": "flag", "required": False},
            ],
            "first_seen_at": now - timedelta(days=30),
            "last_seen_at": now - timedelta(minutes=5),
            "attributes": {"segment": "fiscal", "source": "demo-seed"},
        },
        {
            "key": "instance-blue-conciliacao",
            "automation_key": "automation-conciliacao",
            "client_key": "client-blue",
            "host_key": "host-rj01",
            "deployment_tag": "prod-blue",
            "config_signature": "conciliacao-v2026.03",
            "script": "main.py",
            "default_args": ["--conta-principal"],
            "available_args": [
                {"name": "periodo", "label": "Periodo", "type": "named", "required": True},
            ],
            "first_seen_at": now - timedelta(days=22),
            "last_seen_at": now - timedelta(minutes=12),
            "attributes": {"segment": "financeiro", "source": "demo-seed"},
        },
        {
            "key": "instance-blue-cobranca",
            "automation_key": "automation-cobranca",
            "client_key": "client-blue",
            "host_key": "host-rj01",
            "deployment_tag": "prod-blue",
            "config_signature": "cobranca-v2026.03",
            "script": "main.py",
            "default_args": ["--canal=email"],
            "available_args": [
                {"name": "dias_atraso", "label": "Dias de atraso", "type": "named", "required": True},
                {"name": "dry_run", "label": "Dry run", "type": "flag", "required": False},
            ],
            "first_seen_at": now - timedelta(days=18),
            "last_seen_at": now - timedelta(hours=1),
            "attributes": {"segment": "cobranca", "source": "demo-seed"},
        },
        {
            "key": "instance-hml-nfse",
            "automation_key": "automation-nfse",
            "client_key": "client-blue",
            "host_key": "host-hml01",
            "deployment_tag": "hml-blue",
            "config_signature": "nfse-hml-v2026.03",
            "script": "main.py",
            "default_args": ["--ambiente=hml"],
            "available_args": [
                {"name": "competencia", "label": "Competencia", "type": "named", "required": True},
            ],
            "first_seen_at": now - timedelta(days=12),
            "last_seen_at": now - timedelta(days=1),
            "attributes": {"segment": "fiscal-hml", "source": "demo-seed"},
        },
    ]

    runs = [
        RunSeed("nfse-acme-old-success", "instance-acme-nfse", "completed", now - timedelta(days=6, hours=4, minutes=15), now - timedelta(days=6, hours=3, minutes=57), 2201, "svc.fiscal", "2026.03.1", "schedule", "Notas emitidas e comprovantes enviados."),
        RunSeed("conciliacao-blue-success", "instance-blue-conciliacao", "completed", now - timedelta(days=4, hours=2, minutes=40), now - timedelta(days=4, hours=2, minutes=5), 3811, "svc.financeiro", "2026.03.2", "schedule", "Conciliacao finalizada sem divergencias."),
        RunSeed("cobranca-blue-failed", "instance-blue-cobranca", "failed", now - timedelta(days=3, hours=5, minutes=10), now - timedelta(days=3, hours=4, minutes=48), 4102, "svc.cobranca", "2026.03.2", "manual", "Falha ao validar lote de clientes com atraso acima de 90 dias."),
        RunSeed("nfse-hml-success", "instance-hml-nfse", "completed", now - timedelta(days=2, hours=6, minutes=5), now - timedelta(days=2, hours=5, minutes=48), 1920, "svc.hml", "2026.03.2", "manual", "Homologacao concluida com massa de testes validada."),
        RunSeed("nfse-acme-today-success", "instance-acme-nfse", "completed", now - timedelta(hours=6, minutes=15), now - timedelta(hours=5, minutes=52), 5210, "svc.fiscal", "2026.03.3", "schedule", "Lote de NFSe concluido e enviado ao cliente."),
        RunSeed("conciliacao-blue-today-failed", "instance-blue-conciliacao", "failed", now - timedelta(hours=4, minutes=22), now - timedelta(hours=4, minutes=2), 6344, "svc.financeiro", "2026.03.3", "schedule", "API do banco retornou saldo inconsistente para a conta principal."),
        RunSeed("cobranca-blue-open", "instance-blue-cobranca", "running", now - timedelta(hours=2, minutes=10), None, 7712, "svc.cobranca", "2026.03.4", "manual", "Processando ultima faixa de clientes em atraso."),
        RunSeed("cobranca-blue-overlap-success", "instance-blue-cobranca", "completed", now - timedelta(hours=1, minutes=20), now - timedelta(minutes=58), 7719, "svc.cobranca", "2026.03.4", "manual", "Lote emergencial processado com sucesso."),
        RunSeed("nfse-acme-late-success", "instance-acme-nfse", "completed", now - timedelta(minutes=48), now - timedelta(minutes=26), 8450, "svc.fiscal", "2026.03.4", "manual", "Reprocessamento concluido e cliente notificado."),
    ]

    with session_scope() as session:
        ensure_database_schema()

        clients = {}
        for row in client_rows:
            clients[row["key"]] = upsert(
                session,
                models.Client,
                demo_uuid(row["key"]),
                name=row["name"],
                external_code=row["external_code"],
                contact_email=row["contact_email"],
                created_at=now - timedelta(days=90),
                updated_at=now,
            )

        hosts = {}
        for row in host_rows:
            hosts[row["key"]] = upsert(
                session,
                models.Host,
                demo_uuid(row["key"]),
                hostname=row["hostname"],
                display_name=row["display_name"],
                ip_address=row["ip_address"],
                root_folder=row["root_folder"],
                environment=row["environment"],
                tags=row["tags"],
                last_agent_ping=row["last_agent_ping"],
                created_at=now - timedelta(days=60),
                updated_at=now,
            )

        automations = {}
        for row in automation_rows:
            automations[row["key"]] = upsert(
                session,
                models.Automation,
                demo_uuid(row["key"]),
                code=row["code"],
                name=row["name"],
                description=row["description"],
                owner_team=row["owner_team"],
                created_at=now - timedelta(days=120),
                updated_at=now,
            )

        instances = {}
        for row in instance_rows:
            instances[row["key"]] = upsert(
                session,
                models.AutomationInstance,
                demo_uuid(row["key"]),
                automation_id=automations[row["automation_key"]].id,
                client_id=clients[row["client_key"]].id,
                host_id=hosts[row["host_key"]].id,
                deployment_tag=row["deployment_tag"],
                config_signature=row["config_signature"],
                script=row["script"],
                default_args=row["default_args"],
                available_args=row["available_args"],
                first_seen_at=row["first_seen_at"],
                last_seen_at=row["last_seen_at"],
                attributes=row["attributes"],
            )

        run_models = {}
        for run in runs:
            instance = instances[run.instance_key]
            host = session.get(models.Host, instance.host_id)
            client = session.get(models.Client, instance.client_id)
            automation = session.get(models.Automation, instance.automation_id)
            run_model = upsert(
                session,
                models.Run,
                demo_uuid(run.name),
                automation_instance_id=instance.id,
                started_at=run.started_at,
                finished_at=run.finished_at,
                status=run.status,
                pid=run.pid,
                user_name=run.user_name,
                server_mode=False,
                host_ip=host.ip_address if host else None,
                root_folder=host.root_folder if host else None,
                config_version=run.config_version,
                attributes={"origin": run.origin, "email_retention_days": 14, "summary": run.summary, "seed": True},
            )
            run_models[run.name] = run_model

            session.query(models.LogEntry).filter(models.LogEntry.run_id == run_model.id).delete()
            session.query(models.RunSnapshot).filter(models.RunSnapshot.run_id == run_model.id).delete()
            session.query(models.EmailEvent).filter(models.EmailEvent.run_id == run_model.id).delete()

            for entry in build_logs(
                run,
                automation.code if automation else "DEMO",
                client.name if client else "Sem cliente",
            ):
                session.add(
                    models.LogEntry(
                        run_id=run_model.id,
                        sequence=entry["sequence"],
                        ts=entry["ts"],
                        level=entry["level"],
                        logger_name=entry["logger_name"],
                        message=entry["message"],
                        context=entry["context"],
                        extra=entry["extra"],
                        created_at=entry["ts"],
                    )
                )

            snapshot_ts = (run.finished_at or now) - timedelta(minutes=1)
            session.add(
                models.RunSnapshot(
                    run_id=run_model.id,
                    snapshot_type="summary",
                    taken_at=snapshot_ts,
                    payload={"status": run.status, "origin": run.origin, "notes": run.summary},
                )
            )
            session.add(
                models.RunSnapshot(
                    run_id=run_model.id,
                    snapshot_type="resources",
                    taken_at=snapshot_ts,
                    payload={
                        "cpu_percent": 18 if run.status == "completed" else 42,
                        "memory_mb": 420 if run.status == "completed" else 610,
                        "io_wait_percent": 3 if run.status == "completed" else 11,
                    },
                )
            )

        email_specs = [
            {
                "key": "email-nfse-ok",
                "run_name": "nfse-acme-today-success",
                "subject": "NFSe emitida com sucesso",
                "body_text": "O lote de notas fiscais foi concluido e o comprovante ja esta disponivel.",
                "recipients": ["fiscal@acmefoods.example"],
                "status": "enviado",
                "error": None,
            },
            {
                "key": "email-conciliacao-falha",
                "run_name": "conciliacao-blue-today-failed",
                "subject": "Falha na conciliacao bancaria",
                "body_text": "A conciliacao falhou por saldo inconsistente na conta principal.",
                "recipients": ["financeiro@bluelogistics.example"],
                "status": "erro",
                "error": "Saldo inconsistente retornado pela API do banco.",
            },
            {
                "key": "email-cobranca-ok",
                "run_name": "cobranca-blue-overlap-success",
                "subject": "Lote emergencial de cobranca processado",
                "body_text": "O lote emergencial foi concluido e os clientes foram notificados por email.",
                "recipients": ["cobranca@bluelogistics.example"],
                "status": "enviado",
                "error": None,
            },
        ]

        for email in email_specs:
            run_model = run_models[email["run_name"]]
            sent_at = (run_model.finished_at or now) - timedelta(minutes=2)
            session.add(
                models.EmailEvent(
                    id=demo_uuid(email["key"]),
                    run_id=run_model.id,
                    subject=email["subject"],
                    body_text=email["body_text"],
                    body_html=None,
                    recipients=email["recipients"],
                    bcc_recipients=[],
                    source_paths=[],
                    status=email["status"],
                    error=email["error"],
                    retention_days=14,
                    sent_at=sent_at,
                    expires_at=sent_at + timedelta(days=14),
                    created_at=sent_at,
                )
            )

        today_dom = now.astimezone(timezone.utc).day
        schedules = [
            {
                "key": "schedule-nfse-daily",
                "instance_key": "instance-acme-nfse",
                "script": "main.py",
                "args": ["--competencia=03/2026"],
                "recurrence_type": "daily",
                "recurrence_config": {"time": "08:30"},
                "execution_mode": "parallel",
                "timezone": "America/Sao_Paulo",
                "enabled": True,
            },
            {
                "key": "schedule-conciliacao-weekdays",
                "instance_key": "instance-blue-conciliacao",
                "script": "main.py",
                "args": ["--periodo=ontem"],
                "recurrence_type": "weekdays",
                "recurrence_config": {"time": "10:15"},
                "execution_mode": "sequential",
                "timezone": "America/Sao_Paulo",
                "enabled": True,
            },
            {
                "key": "schedule-cobranca-monthly",
                "instance_key": "instance-blue-cobranca",
                "script": "main.py",
                "args": ["--dias_atraso=15"],
                "recurrence_type": "monthly",
                "recurrence_config": {"time": "16:00", "day_of_month": today_dom, "business_day": True},
                "execution_mode": "parallel",
                "timezone": "America/Sao_Paulo",
                "enabled": True,
            },
        ]

        for item in schedules:
            upsert(
                session,
                models.ScheduledJob,
                demo_uuid(item["key"]),
                automation_instance_id=instances[item["instance_key"]].id,
                script=item["script"],
                args=item["args"],
                recurrence_type=item["recurrence_type"],
                recurrence_config=item["recurrence_config"],
                execution_mode=item["execution_mode"],
                enabled=item["enabled"],
                timezone=item["timezone"],
                created_at=now - timedelta(days=7),
                updated_at=now,
            )

        commands = [
            {
                "key": "command-cobranca-running",
                "instance_key": "instance-blue-cobranca",
                "host_key": "host-rj01",
                "status": "running",
                "run_name": "cobranca-blue-open",
                "script": "main.py",
                "args": ["--dias_atraso=15"],
                "working_dir": r"C:\Bots\Financeiro\rj01",
                "execution_mode": "parallel",
                "created_by": "admin@example.com",
                "created_at": now - timedelta(hours=2, minutes=12),
                "acked_at": now - timedelta(hours=2, minutes=10),
                "started_at": now - timedelta(hours=2, minutes=9),
                "finished_at": None,
                "result_message": None,
            },
            {
                "key": "command-cobranca-completed",
                "instance_key": "instance-blue-cobranca",
                "host_key": "host-rj01",
                "status": "completed",
                "run_name": "cobranca-blue-overlap-success",
                "script": "main.py",
                "args": ["--dias_atraso=7", "--prioridade=alta"],
                "working_dir": r"C:\Bots\Financeiro\rj01",
                "execution_mode": "parallel",
                "created_by": "scheduler",
                "created_at": now - timedelta(hours=1, minutes=25),
                "acked_at": now - timedelta(hours=1, minutes=23),
                "started_at": now - timedelta(hours=1, minutes=20),
                "finished_at": now - timedelta(minutes=58),
                "result_message": "Lote emergencial concluido.",
            },
            {
                "key": "command-conciliacao-failed",
                "instance_key": "instance-blue-conciliacao",
                "host_key": "host-rj01",
                "status": "failed",
                "run_name": "conciliacao-blue-today-failed",
                "script": "main.py",
                "args": ["--periodo=hoje"],
                "working_dir": r"C:\Bots\Financeiro\rj01",
                "execution_mode": "sequential",
                "created_by": "scheduler",
                "created_at": now - timedelta(hours=4, minutes=25),
                "acked_at": now - timedelta(hours=4, minutes=23),
                "started_at": now - timedelta(hours=4, minutes=22),
                "finished_at": now - timedelta(hours=4, minutes=2),
                "result_message": "Banco retornou saldo inconsistente.",
            },
            {
                "key": "command-nfse-pending",
                "instance_key": "instance-acme-nfse",
                "host_key": "host-sp01",
                "status": "pending",
                "run_name": None,
                "script": "main.py",
                "args": ["--competencia=04/2026"],
                "working_dir": r"C:\Bots\Fiscal\sp01",
                "execution_mode": "parallel",
                "created_by": "admin@example.com",
                "created_at": now - timedelta(minutes=12),
                "acked_at": None,
                "started_at": None,
                "finished_at": None,
                "result_message": None,
            },
        ]

        for item in commands:
            upsert(
                session,
                models.Command,
                demo_uuid(item["key"]),
                host_id=hosts[item["host_key"]].id,
                automation_instance_id=instances[item["instance_key"]].id,
                scheduled_job_id=None,
                script=item["script"],
                args=item["args"],
                working_dir=item["working_dir"],
                execution_mode=item["execution_mode"],
                status=item["status"],
                run_id=run_models[item["run_name"]].id if item["run_name"] else None,
                created_by=item["created_by"],
                created_at=item["created_at"],
                acked_at=item["acked_at"],
                started_at=item["started_at"],
                finished_at=item["finished_at"],
                result_message=item["result_message"],
            )

        return {
            "clients": session.query(models.Client).filter(models.Client.id.in_([demo_uuid(row["key"]) for row in client_rows])).count(),
            "hosts": session.query(models.Host).filter(models.Host.id.in_([demo_uuid(row["key"]) for row in host_rows])).count(),
            "automations": session.query(models.Automation).filter(models.Automation.id.in_([demo_uuid(row["key"]) for row in automation_rows])).count(),
            "instances": session.query(models.AutomationInstance).filter(models.AutomationInstance.id.in_([demo_uuid(row["key"]) for row in instance_rows])).count(),
            "runs": session.query(models.Run).filter(models.Run.id.in_([demo_uuid(run.name) for run in runs])).count(),
            "logs": session.query(models.LogEntry).join(models.Run).filter(models.Run.id.in_([demo_uuid(run.name) for run in runs])).count(),
            "emails": session.query(models.EmailEvent).filter(models.EmailEvent.id.in_([demo_uuid(item["key"]) for item in email_specs])).count(),
            "schedules": session.query(models.ScheduledJob).filter(models.ScheduledJob.id.in_([demo_uuid(item["key"]) for item in schedules])).count(),
            "commands": session.query(models.Command).filter(models.Command.id.in_([demo_uuid(item["key"]) for item in commands])).count(),
        }


def main() -> None:
    print("Garantindo schema base...")
    ensure_database_schema()
    summary = seed_demo_data()
    print("Carga demo aplicada com sucesso:")
    for key, value in summary.items():
        print(f"  {key:<11}: {value}")


if __name__ == "__main__":
    main()
