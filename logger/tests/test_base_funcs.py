from logger import start_logger
import importlib
pause_mod = importlib.import_module('logger.extras.base_funcs.pause')
cleanup_mod = importlib.import_module('logger.extras.base_funcs.cleanup')


def _no_profiler_start(self):
    pass


def test_pause_timeout(tmp_path, monkeypatch):
    monkeypatch.setattr('logger.core.context.Profiler.start', _no_profiler_start)
    logger = start_logger('p', log_dir=str(tmp_path), console_level='CRITICAL')
    # input will raise EOFError (simulate no user input)
    monkeypatch.setattr('builtins.input', lambda msg='': (_ for _ in ()).throw(EOFError))
    resp = pause_mod.pause(logger, msg='? ', timeout=0.1)
    assert resp is None
    logger.end()


def test_cleanup_invokes_subprocess(tmp_path, monkeypatch):
    monkeypatch.setattr('logger.core.context.Profiler.start', _no_profiler_start)
    logger = start_logger('c', log_dir=str(tmp_path), console_level='CRITICAL')
    calls = []
    monkeypatch.setattr(cleanup_mod.subprocess, 'run', lambda cmd, check=False: calls.append(cmd))
    cleanup_mod.cleanup(logger)
    assert calls
    logger.end()
