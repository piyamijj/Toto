import json
import urllib.parse
import urllib.request

from toto import config


class DataSourceError(RuntimeError):
    pass


def get_json(url, params=None, headers=None):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "toto-analiz/1.0", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # ağ, HTTP veya JSON hatası
        raise DataSourceError(f"{urllib.parse.urlsplit(url).netloc} isteği başarısız: {exc}") from exc


def get_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "toto-analiz/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT * 3) as resp:
            return resp.read().decode("utf-8-sig", errors="replace")
    except Exception as exc:
        raise DataSourceError(f"İndirme başarısız ({url}): {exc}") from exc
