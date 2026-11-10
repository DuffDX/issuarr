import types

import pytest

import mylar
from mylar import search, webserve


def config(monkeypatch, **kw):
    monkeypatch.setattr(mylar, 'CONFIG', types.SimpleNamespace(**kw), raising=False)
    monkeypatch.setattr(mylar, 'LOG_LEVEL', 0, raising=False)


@pytest.mark.parametrize('wait, manual, expected', [
    (0, False, 0),
    (15, False, 15),
    (90, False, 90),
    (90, True, 30),      # a search you start by hand never waits longer than 30 seconds
    (5, True, 5),
])
def test_wait_in_seconds(monkeypatch, wait, manual, expected):
    config(monkeypatch, SEARCH_WAIT=wait, SEARCH_DELAY=3)
    assert search.check_the_search_delay(manual) == expected


def test_unset_seconds_falls_back_to_the_old_minutes(monkeypatch):
    config(monkeypatch, SEARCH_WAIT=-1, SEARCH_DELAY=3)
    assert search.check_the_search_delay(False) == 180


def test_settings_page_shows_seconds(monkeypatch):
    config(monkeypatch, SEARCH_WAIT=-1, SEARCH_DELAY=3)
    assert webserve.search_wait_seconds() == 180
    config(monkeypatch, SEARCH_WAIT=0, SEARCH_DELAY=3)
    assert webserve.search_wait_seconds() == 0
    config(monkeypatch, SEARCH_WAIT=20, SEARCH_DELAY=3)
    assert webserve.search_wait_seconds() == 20
