import types

import pytest

import mylar
from mylar import search, series_results


class Config(types.SimpleNamespace):
    """Settings for the test: anything not given reads as unset."""
    def __getattr__(self, name):
        return None


PROVIDER = {'NZBS.in': {'type': 'newznab', 'lastrun': 0, 'active': True, 'hits': 0, 'id': 1}}
HOST = ('NZBS.in', 'https://idx.example', '1', 'KEY', '#7000', '1', 1)


def feed(n):
    items = ''.join('<item><title>Absolute Batman %03d (2025) (Digital)</title>'
                    '<link>https://idx.example/get/%d</link></item>' % (i, i) for i in range(1, n + 1))
    return ('<?xml version="1.0"?><rss><channel>%s</channel></rss>' % items).encode()


@pytest.fixture
def indexer(monkeypatch):
    """A fake Newznab indexer: records each request and answers with `size` releases."""
    state = {'size': 30, 'urls': [], 'checked': []}

    class Resp:
        status_code = 200

        def __init__(self, content):
            self.content = content

        def raise_for_status(self):
            pass

    def fake_get(url, params=None, verify=None, headers=None):
        state['urls'].append(url)
        return Resp(feed(state['size']))

    monkeypatch.setattr(search.requests, 'get', fake_get)
    class Filer:
        def checker(self, entries, is_info):
            state['checked'].append(len(entries))   # every release the issue is matched against
            return 'no results'

    monkeypatch.setattr(search.search_filer, 'search_check', lambda: Filer())
    monkeypatch.setattr(search, 'verification', lambda matches, info: None)
    monkeypatch.setattr(search, 'last_run_check', lambda **kw: None)
    monkeypatch.setattr(search, 'check_the_search_delay', lambda manual=False: 0)
    monkeypatch.setattr(mylar, 'CONFIG', Config(
        SERIES_SEARCH=True, USENET_RETENTION=None, ENABLE_TORRENT_SEARCH=False, ENABLE_32P=False,
        ZERO_LEVEL=False, ZERO_LEVEL_N='none'), raising=False)
    monkeypatch.setattr(mylar, 'USER_AGENT', 'test', raising=False)
    monkeypatch.setattr(mylar, 'LOG_LEVEL', 0, raising=False)
    series_results.clear()
    yield state
    series_results.clear()


def look_for(issue, cmloopit=1):
    return search.NZB_SEARCH('Absolute Batman', issue, '2025', '2024', 'DC Comics', '2025-01-01', '2025-01-01',
                             dict(PROVIDER), 0, None, 'iss%s' % issue, None, newznab_host=HOST, RSS='no',
                             ComicID='160294', cmloopit=cmloopit)


def test_one_request_answers_every_issue_of_the_series(indexer):
    for issue in ('1', '2', '3', '9', '10'):
        look_for(issue)
    assert len(indexer['urls']) == 1
    assert 'q=absolute%20batman&' in indexer['urls'][0] and 'limit=100' in indexer['urls'][0]
    assert 'cat=7000' in indexer['urls'][0]
    assert indexer['checked'] == [30] * 5        # every issue was matched against the full answer


def test_number_formats_reuse_the_answer_too(indexer):
    for loop in (3, 2, 1):                       # '009', '09', '9'
        look_for('9', cmloopit=loop)
    assert len(indexer['urls']) == 1


def test_a_full_page_falls_back_to_searching_each_issue(indexer):
    indexer['size'] = series_results.LIMIT
    look_for('1')                                # series search, comes back full
    look_for('2')
    look_for('3')
    assert len(indexer['urls']) == 3
    assert 'limit=100' in indexer['urls'][0]
    assert 'q=absolute%20batman%202&' in indexer['urls'][1]
    assert 'q=absolute%20batman%203&' in indexer['urls'][2]


def test_switched_off_searches_each_issue(indexer):
    mylar.CONFIG.SERIES_SEARCH = False
    look_for('1')
    look_for('2')
    assert len(indexer['urls']) == 2
    assert all('limit=' not in u for u in indexer['urls'])


def test_answers_expire(indexer, monkeypatch):
    look_for('1')
    real_time = series_results.time.time
    monkeypatch.setattr(series_results.time, 'time', lambda: real_time() + series_results.TTL + 1)
    look_for('2')
    assert len(indexer['urls']) == 2


def test_count_items():
    assert series_results.count_items(feed(7)) == 7
    assert series_results.count_items('') == 0
