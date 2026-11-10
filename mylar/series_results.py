#  This file is part of Mylar.
#
#  Mylar is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Mylar is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Mylar.  If not, see <http://www.gnu.org/licenses/>.

"""Search a whole series at once.

A Newznab search for just the series name returns every release of it the indexer
has, so one request can answer the search for every wanted issue of that series.
The answer is kept for a while and each issue is matched against it, instead of
sending one request (and waiting between requests) per issue and per number format.

When an indexer returns a full page (LIMIT results) the series may have more
releases than fit, so that answer is marked incomplete and issues fall back to the
usual per-issue search.
"""

import re
import threading
import time

import mylar

LIMIT = 100          # results asked for in one series search (the usual Newznab maximum)
TTL = 20 * 60        # seconds a series answer is reused

_lock = threading.Lock()
_cache = {}


def enabled():
    return bool(getattr(mylar.CONFIG, 'SERIES_SEARCH', True))


def key(provider, host, series_terms, category):
    return (str(provider).lower(), str(host).lower(), str(series_terms).lower(), str(category))


def count_items(content):
    if isinstance(content, bytes):
        content = content.decode('utf-8', 'replace')
    return len(re.findall(r'<item[\s>]', content or ''))


def get(k, now=None):
    now = time.time() if now is None else now
    with _lock:
        entry = _cache.get(k)
        if entry is None:
            return None
        if now - entry['stored'] > TTL:
            del _cache[k]
            return None
        return entry


def put(k, content, now=None):
    items = count_items(content)
    entry = {'content': content, 'items': items, 'complete': items < LIMIT,
             'stored': time.time() if now is None else now}
    with _lock:
        _cache[k] = entry
    return entry


def clear():
    with _lock:
        _cache.clear()


class CachedResponse(object):
    """Stands in for a requests response when the series answer is reused."""
    status_code = 200

    def __init__(self, content):
        self.content = content
