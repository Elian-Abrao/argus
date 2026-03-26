import logging
import json
import smtplib
import time
from types import SimpleNamespace
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


from logger import start_logger
from logger.extras.dependency import DependencyManager
from logger.extras.network import NetworkMonitor
from logger.extras import capture_prints
import requests
import logger.extras.dependency as dependency_mod
import logger.extras.network as network_mod
import logger.extras.metrics as metrics
import logger.extras.utils.timer as timer_utils
import logger.extras.monitoring as monitoring_mod
from logger.extras.remote_sink import RemoteSink, RemoteSinkSettings


def test_dependency_manager_cache(monkeypatch):
    dm = DependencyManager()

    fake_pkg = type('Dist', (), {'key': 'requests', 'version': '1.0'})
    monkeypatch.setattr(dependency_mod.pkg_resources, 'working_set', [fake_pkg], raising=False)

    t = [0.0]
    monkeypatch.setattr(dependency_mod.time, 'time', lambda: t[0])
    info1 = dm.get_environment_info()
    t[0] += 10
    info2 = dm.get_environment_info()
    assert info1 is info2
    t[0] += dm._cache_duration + 1
    info3 = dm.get_environment_info()
    assert info3 is not info1


def test_logger_log_environment(tmp_path, caplog, monkeypatch):
    logger = start_logger('env', log_dir=str(tmp_path), console_level='INFO')
    dummy_info = {
        'python': {
            'version': '3.x',
            'implementation': 'CPython',
            'compiler': '',
            'build': ('', '')
        },
        'system': {
            'os': 'Linux',
            'release': '5',
            'machine': 'x86',
            'processor': 'CPU',
            'node': 'node'
        },
        'packages': {'requests': '1.0'}
    }
    monkeypatch.setattr(logger._dep_manager, 'get_environment_info', lambda force_update=False: dummy_info)

    block = logger.log_environment(return_block=True)
    assert 'AMBIENTE' in block

    with caplog.at_level(logging.INFO):
        logger.log_environment()
    assert any('AMBIENTE' in rec.message for rec in caplog.records)
    logger.end()


def test_network_monitor_measure_latency(monkeypatch):
    nm = NetworkMonitor()

    class FakeResp:
        status_code = 200
        content = b'OK'

    t = [0.0]
    def fake_time():
        return t[0]
    monkeypatch.setattr(network_mod.time, 'time', fake_time)

    t[0] = 0
    def fake_get(url, timeout=1.0):
        t[0] = 0.05
        return FakeResp()
    monkeypatch.setattr(network_mod.requests, 'get', fake_get)
    result = nm.measure_latency('http://example.com')
    assert result['status_code'] == 200
    assert result['content_size'] == 2
    assert abs(result['latency'] - 50) < 1e-6
    metrics = nm.metrics['example.com']
    assert metrics['total_requests'] == 1
    assert metrics['total_bytes'] == 2
    assert metrics['latencies'] == [50]


def test_network_monitor_connection_error(monkeypatch):
    nm = NetworkMonitor()

    def fake_get(url, timeout=1.0):
        raise requests.exceptions.ConnectionError("fail")

    monkeypatch.setattr(network_mod.requests, 'get', fake_get)

    result = nm.measure_latency('http://example.com')
    assert result['type'] == 'ConnectionError'
    metrics = nm.metrics['example.com']
    assert metrics['total_errors'] == 1


def test_network_monitor_name_resolution_error(monkeypatch, caplog):
    nm = NetworkMonitor()

    def fake_get(url, timeout=1.0):
        raise requests.exceptions.ConnectionError(
            "HTTPSConnectionPool(host='x', port=443): Max retries exceeded with url: / (Caused by NameResolutionError('fail'))"
        )

    monkeypatch.setattr(network_mod.requests, 'get', fake_get)
    with caplog.at_level(logging.WARNING):
        result = nm.measure_latency('http://example.com')
    assert result['error'] == 'sem conectividade'
    assert 'Sem conectividade' in caplog.text

def test_network_monitor_generic_exception(monkeypatch):
    nm = NetworkMonitor()

    def fake_get(url, timeout=1.0):
        raise RuntimeError('boom')

    monkeypatch.setattr(network_mod.requests, 'get', fake_get)
    result = nm.measure_latency('http://example.com')
    assert result['type'] == 'Exception'


def test_logger_check_connectivity_and_metrics(tmp_path, caplog, monkeypatch):
    logger = start_logger('net', log_dir=str(tmp_path), console_level='INFO')

    dummy_nm = SimpleNamespace()
    dummy_nm.check_connection = lambda host='8.8.8.8', port=53, timeout=1.0: (True, 20.0)
    dummy_nm.measure_latency = lambda url, timeout=1.0: {'latency': 30.0, 'status_code': 200, 'content_size': 2}
    dummy_nm.metrics = {'example.com': {'total_requests': 1, 'total_errors': 0, 'total_bytes': 2, 'latencies': [30.0]}}
    monkeypatch.setattr(logger, '_net_monitor', dummy_nm, raising=False)

    with caplog.at_level(logging.INFO):
        logger.check_connectivity(['http://example.com'])
    assert any('example.com' in rec.message for rec in caplog.records)

    metrics = logger.get_network_metrics('example.com')
    assert metrics['average_latency'] == 30.0
    logger.end()


def test_logger_check_connectivity_offline(tmp_path, caplog, monkeypatch):
    logger = start_logger('off', log_dir=str(tmp_path), console_level='INFO')

    dummy_nm = SimpleNamespace()
    dummy_nm.check_connection = lambda host='8.8.8.8', port=53, timeout=1.0: (False, None)
    dummy_nm.measure_latency = lambda url, timeout=1.0: {'latency': 1.0}
    monkeypatch.setattr(logger, '_net_monitor', dummy_nm, raising=False)

    with caplog.at_level(logging.INFO):
        logger.check_connectivity(['http://example.com'])

    msgs = ' '.join(rec.message for rec in caplog.records)
    assert 'Sem conexão com a internet' in msgs
    assert 'example.com' not in msgs
    logger.end()


def test_metrics_tracker_and_timer(tmp_path, caplog, monkeypatch):
    logger = start_logger('metrics', log_dir=str(tmp_path), console_level='INFO')

    t = [0.0]
    monkeypatch.setattr(metrics.time, 'time', lambda: t[0])
    monkeypatch.setattr(timer_utils.time, 'time', lambda: t[0])

    logger.reset_metrics()
    with caplog.at_level(logging.INFO):
        with logger.timer('task'):
            t[0] += 2
        logger.report_metrics()

    messages = ' '.join(r.message for r in caplog.records)
    assert 'Iniciando task' in messages
    assert 'task concluída em 2.0s' in messages
    assert 'Duração total: 2.0s' in messages
    logger.end()


def test_start_logger_calls_check_connectivity(tmp_path, monkeypatch):
    called = {'n': 0}

    def fake_check(self, urls=None, level='INFO', timeout=1.0, return_block=False):
        called['n'] += 1
        return 'X'

    monkeypatch.setattr(network_mod, 'logger_check_connectivity', fake_check)

    logger = start_logger('auto', log_dir=str(tmp_path), console_level='INFO')
    assert called['n'] == 1
    logger.end()


def test_connectivity_block_in_banners(tmp_path, caplog, monkeypatch):
    calls: list[bool] = []

    def fake_check(self, urls=None, level='INFO', timeout=1.0, return_block=False):
        calls.append(return_block)
        return 'CONNECT'

    monkeypatch.setattr(network_mod, 'logger_check_connectivity', fake_check)

    with caplog.at_level(logging.INFO):
        logger = start_logger('banner', log_dir=str(tmp_path), console_level='INFO')
        logger.end()

    assert calls == [True, True]
    messages = ' '.join(rec.message for rec in caplog.records)
    assert messages.count('CONNECT') == 2


def test_start_logger_calls_memory_snapshot(tmp_path, monkeypatch):
    called = {'n': 0}

    def fake_snapshot(self):
        called['n'] += 1

    monkeypatch.setattr(monitoring_mod, 'logger_memory_snapshot', fake_snapshot)

    logger = start_logger('mem', log_dir=str(tmp_path), console_level='INFO')
    assert called['n'] == 1
    logger.end()


def test_memory_leak_block_in_banner(tmp_path, caplog):
    logger = start_logger('leak', log_dir=str(tmp_path), console_level='INFO')
    logger._monitor.get_memory_diff = lambda: (5.0, {'Obj': 2})
    with caplog.at_level(logging.INFO):
        logger.end()

    assert any('VAZAMENTO DE MEMÓRIA' in rec.message for rec in caplog.records)

def test_memory_leak_respects_threshold(tmp_path, caplog):
    logger = start_logger('thr', log_dir=str(tmp_path), console_level='INFO')
    logger._monitor.get_memory_diff = lambda: (1.0, {'Obj': 2})
    with caplog.at_level(logging.INFO):
        logger.end()

    assert not any('VAZAMENTO DE MEMÓRIA' in r.message for r in caplog.records)


def test_memory_leak_show_all_flag(tmp_path, caplog):
    logger = start_logger(
        'all', log_dir=str(tmp_path), console_level='INFO', show_all_leaks=True
    )
    logger._monitor.get_memory_diff = lambda: (1.0, {'Obj': 1})
    with caplog.at_level(logging.INFO):
        logger.end()

    assert any('VAZAMENTO DE MEMÓRIA' in r.message for r in caplog.records)


def test_memory_leak_watch_object(tmp_path, caplog):
    logger = start_logger(
        'watch', log_dir=str(tmp_path), console_level='INFO', watch_objects=['X']
    )
    logger._monitor.get_memory_diff = lambda: (1.0, {'X': 1})
    with caplog.at_level(logging.INFO):
        logger.end()

    assert any('X:' in r.message for r in caplog.records)


def test_capture_prints_restores_on_exception(tmp_path):
    logger = start_logger('print', log_dir=str(tmp_path), console_level='CRITICAL', capture_prints=False)
    logger.capture_prints(False)
    import builtins
    original = builtins.print
    try:
        with capture_prints(logger):
            assert builtins.print is not original
            raise RuntimeError('boom')
    except RuntimeError:
        pass
    assert builtins.print is original
    logger.end()


def _extract_email_payload(caplog):
    for rec in caplog.records:
        if rec.message.startswith("EMAIL_CAPTURE "):
            raw = rec.message.split("EMAIL_CAPTURE ", 1)[1]
            return json.loads(raw)
    return None


def test_capture_emails_sendmail_logs_payload(tmp_path, caplog, monkeypatch):
    def fake_sendmail(self, from_addr, to_addrs, msg, *args, **kwargs):
        return {}

    monkeypatch.setattr(smtplib.SMTP, "sendmail", fake_sendmail)
    logger = start_logger(
        "mail-ok",
        log_dir=str(tmp_path),
        console_level="INFO",
        capture_prints=False,
    )

    msg = MIMEMultipart()
    msg["From"] = "smtp@treeinova.com.br"
    msg["To"] = "destinatario@treeinova.com.br"
    msg["Subject"] = "Teste de envio"
    msg.attach(MIMEText("Corpo em texto", "plain"))

    attachment = MIMEBase("application", "octet-stream")
    attachment.set_payload(b"conteudo")
    encoders.encode_base64(attachment)
    attachment.add_header("Content-Disposition", "attachment; filename=relatorio.csv")
    msg.attach(attachment)

    with caplog.at_level(logging.INFO):
        with smtplib.SMTP() as server:
            server.sendmail(
                "smtp@treeinova.com.br",
                ["destinatario@treeinova.com.br", "oculto@treeinova.com.br"],
                msg.as_string(),
            )

    payload = _extract_email_payload(caplog)
    assert payload is not None
    assert payload["assunto"] == "Teste de envio"
    assert payload["destinatarios"] == ["destinatario@treeinova.com.br"]
    assert payload["destinatarios_copia_oculta"] == ["oculto@treeinova.com.br"]
    assert payload["status"] == "enviado"
    assert "relatorio.csv" in payload["paths_arquivos"]
    assert payload["corpo"]["texto"] == "Corpo em texto"
    logger.end()


def test_capture_emails_sendmail_logs_failure(tmp_path, caplog, monkeypatch):
    def fake_sendmail(self, from_addr, to_addrs, msg, *args, **kwargs):
        raise RuntimeError("falhou no smtp")

    monkeypatch.setattr(smtplib.SMTP, "sendmail", fake_sendmail)
    logger = start_logger(
        "mail-fail",
        log_dir=str(tmp_path),
        console_level="INFO",
        capture_prints=False,
    )

    msg = MIMEMultipart()
    msg["From"] = "smtp@treeinova.com.br"
    msg["To"] = "destinatario@treeinova.com.br"
    msg["Subject"] = "Teste falha"
    msg.attach(MIMEText("Corpo", "plain"))

    with caplog.at_level(logging.INFO):
        try:
            with smtplib.SMTP() as server:
                server.sendmail(
                    "smtp@treeinova.com.br",
                    ["destinatario@treeinova.com.br"],
                    msg.as_string(),
                )
        except RuntimeError:
            pass

    payload = _extract_email_payload(caplog)
    assert payload is not None
    assert payload["status"] == "falha"
    assert "falhou no smtp" in payload["erro"]
    logger.end()


def test_remote_sink_send_email_event_is_async(monkeypatch):
    settings = RemoteSinkSettings(
        endpoint="http://logger-api.invalid/api",
        api_key=None,
        automation={"code": "TST", "name": "Teste"},
    )
    sink = RemoteSink(settings)

    monkeypatch.setattr(sink, "_wait_until_bootstrap", lambda: True)
    monkeypatch.setattr(sink, "_send_run_update", lambda status: None)

    called = {"n": 0}

    def fake_retry(url, payload):
        time.sleep(0.3)
        called["n"] += 1
        return None

    monkeypatch.setattr(sink, "_post_email_event_with_retry", fake_retry)
    sink.start()

    started = time.perf_counter()
    sink.send_email_event(
        {"subject": "Assunto", "status": "enviado"},
        attachments=[],
    )
    elapsed = time.perf_counter() - started

    assert elapsed < 0.15

    time.sleep(0.4)
    sink.finalize()
    assert called["n"] == 1


def test_remote_sink_start_does_not_block_with_slow_bootstrap(monkeypatch):
    settings = RemoteSinkSettings(
        endpoint="http://logger-api.invalid/api",
        api_key=None,
        automation={"code": "TST", "name": "Teste"},
    )
    sink = RemoteSink(settings)

    def slow_bootstrap_once():
        time.sleep(0.3)
        return False

    monkeypatch.setattr(sink, "_bootstrap_run_once", slow_bootstrap_once)

    started = time.perf_counter()
    sink.start()
    elapsed = time.perf_counter() - started

    assert elapsed < 0.15
    sink.finalize()
