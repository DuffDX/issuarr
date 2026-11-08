import types

import pytest
import requests

import mylar
from mylar import helpers


@pytest.fixture
def blocklist(monkeypatch):
    def setup(timer=900):
        monkeypatch.setattr(mylar, 'CONFIG', types.SimpleNamespace(BLOCKLIST_TIMER=timer), raising=False)
        monkeypatch.setattr(mylar, 'PROVIDER_BLOCKLIST', [], raising=False)
        monkeypatch.setattr(mylar, 'LOG_LEVEL', 0, raising=False)
        return mylar.PROVIDER_BLOCKLIST
    return setup


def http_error(code, headers=None):
    resp = requests.models.Response()
    resp.status_code = code
    resp.headers.update(headers or {})
    return requests.exceptions.HTTPError('%s error for url: https://idx/api?t=search&apikey=SECRET' % code, response=resp)


def test_rejected_api_key_does_not_pause(blocklist):
    bl = blocklist()
    assert helpers.provider_request_failed('NZBS.in (newznab)', http_error(401)) == 'auth'
    assert helpers.provider_request_failed('NZBS.in (newznab)', http_error(403)) == 'auth'
    assert bl == []


def test_server_error_pauses_for_the_set_time(blocklist):
    bl = blocklist(timer=300)
    assert helpers.provider_request_failed('NZBS.in (newznab)', http_error(503)) == 'down'
    assert len(bl) == 1 and bl[0]['reason'] == 'Unavailable (HTTP 503)'
    assert helpers.block_provider_check('NZBS.in') is True


def test_connection_failure_pauses(blocklist):
    bl = blocklist()
    assert helpers.provider_request_failed('NZBS.in (newznab)', requests.exceptions.ConnectionError('refused')) == 'down'
    assert len(bl) == 1


def test_zero_turns_pausing_off(blocklist):
    bl = blocklist(timer=0)
    helpers.provider_request_failed('NZBS.in (newznab)', http_error(503))
    helpers.provider_request_failed('NZBS.in (newznab)', requests.exceptions.ConnectionError('refused'))
    assert bl == []


def test_rate_limit_always_pauses_and_honours_retry_after(blocklist):
    bl = blocklist(timer=0)
    assert helpers.provider_request_failed('NZBS.in (newznab)', http_error(429, {'Retry-After': '120'})) == 'rate'
    assert len(bl) == 1
    assert 100 < bl[0]['resume'] - helpers.time.time() <= 120


def test_api_limit_pauses_even_when_pausing_is_off(blocklist):
    bl = blocklist(timer=0)
    helpers.disable_provider('NZBS.in (newznab)', 'API Limit reached', provider_asked=True)
    assert len(bl) == 1


def test_other_client_errors_do_not_pause_and_hide_the_key(blocklist, monkeypatch):
    bl = blocklist()
    logged = []
    monkeypatch.setattr(helpers.logger, 'warn', lambda msg, *a, **k: logged.append(msg))
    assert helpers.provider_request_failed('NZBS.in (newznab)', http_error(400)) == 'other'
    assert bl == []
    assert 'SECRET' not in logged[0] and 'apikey=xxx' in logged[0]
