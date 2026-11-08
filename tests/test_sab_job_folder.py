import types

import pytest

import mylar
from mylar import sabnzbd


NZBINFO = {'nzo_id': 'nzo_1', 'issueid': '111', 'comicid': '222',
           'download_info': {'provider': 'NZBS.in', 'id': 'abc'}}


def history_client(monkeypatch, storage, **config):
    """A SABnzbd client whose history call returns one completed job stored at `storage`."""
    cfg = dict(SAB_HOST='http://sab:8080', SAB_APIKEY='k', SAB_CATEGORY='comics', SAB_VERSION='5.1.3',
               SAB_REMOVE_COMPLETED=False, SAB_REMOVE_FAILED=False, SAB_TO_MYLAR=False,
               SAB_DIRECTORY=None, SAB_MOVING_DELAY=0)
    cfg.update(config)
    monkeypatch.setattr(mylar, 'CONFIG', types.SimpleNamespace(**cfg), raising=False)
    monkeypatch.setattr(mylar, 'LOG_LEVEL', 0, raising=False)

    class Resp:
        def json(self):
            return {'history': {'slots': [{'nzo_id': 'nzo_1', 'status': 'Completed', 'script': None,
                                           'storage': str(storage), 'nzb_name': 'job.nzb'}]}}

    monkeypatch.setattr(sabnzbd.requests, 'get', lambda url, params=None, verify=None: Resp())
    return sabnzbd.SABnzbd(params={})


def test_job_folder_is_handed_over_as_the_folder(monkeypatch, tmp_path):
    job = tmp_path / 'ComicShop' / 'Absolute.Batman.009.2025.Digital'
    job.mkdir(parents=True)
    (job / 'yay.rar').write_bytes(b'x')

    found = history_client(monkeypatch, job).historycheck(dict(NZBINFO))

    assert found['status'] is True
    assert found['location'] == str(job)
    assert found['name'] == 'Absolute.Batman.009.2025.Digital'
    assert found['issueid'] == '111' and found['failed'] is False


def test_single_file_is_handed_over_with_its_folder(monkeypatch, tmp_path):
    f = tmp_path / 'Absolute Batman 009 (2025).cbz'
    f.write_bytes(b'x')

    found = history_client(monkeypatch, f).historycheck(dict(NZBINFO))

    assert found['status'] is True
    assert found['location'] == str(tmp_path)
    assert found['name'] == f.name


def test_missing_path_is_still_file_not_found(monkeypatch, tmp_path):
    found = history_client(monkeypatch, tmp_path / 'gone').historycheck(dict(NZBINFO))
    assert found == {'status': 'file not found', 'failed': False}
