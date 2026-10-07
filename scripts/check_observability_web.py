"""Check a deployed Grafana subpath without credentials or private telemetry."""

import argparse
import json
import re
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import urlopen


def check(url):
    url = url.rstrip("/") + "/"
    with urlopen(url, timeout=15) as response:
        assert response.geturl() == urljoin(url, "login"), response.geturl()
        html = response.read().decode()
    asset = re.search(r'href="([^" ]*public/build/[^" ]+\.css)"', html)
    assert asset, "Grafana stylesheet missing"
    with urlopen(urljoin(url, asset[1]), timeout=15) as response:
        assert "text/css" in response.headers.get("Content-Type", "")
    with urlopen(urljoin(url, "api/health"), timeout=15) as response:
        assert json.load(response)["database"] == "ok"
    try:
        urlopen(urljoin(url, "api/search"), timeout=15)
    except HTTPError as error:
        assert error.code == 401, error.code
    else:
        raise AssertionError("Dashboard API allowed anonymous access")
    print("PASS Grafana HTTPS subpath, login, assets, health and anonymous access protection")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    check(parser.parse_args().url)
