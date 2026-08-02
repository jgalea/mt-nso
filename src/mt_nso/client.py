"""HTTP client for the NSO IRIS SDMX REST API."""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_BASE = "https://irisapi.nso.gov.mt/nsi_ws/rest"
DEFAULT_AGENCY = "MT1"
USER_AGENT = "mt-nso/0.1 (+https://github.com/jgalea/mt-nso)"


class NSOError(Exception):
    """Raised when the NSO API returns an error or empty response."""


@dataclass(frozen=True)
class Dataflow:
    id: str
    name: str
    version: str
    agency: str = DEFAULT_AGENCY

    @property
    def ref(self) -> str:
        return f"{self.agency},{self.id},{self.version}"


class NSOClient:
    def __init__(self, base_url: str = DEFAULT_BASE, timeout: float = 90.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._ctx = ssl.create_default_context()

    def _get(self, path: str, accept: str | None = None) -> bytes:
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {"User-Agent": USER_AGENT}
        if accept:
            headers["Accept"] = accept
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=self._ctx) as resp:
                body = resp.read()
                if resp.status == 204 or not body:
                    raise NSOError(f"No content for {url} (HTTP {resp.status})")
                return body
        except urllib.error.HTTPError as e:
            detail = e.read()[:300].decode("utf-8", errors="replace")
            raise NSOError(f"HTTP {e.code} for {url}: {detail}") from e
        except urllib.error.URLError as e:
            raise NSOError(f"Request failed for {url}: {e.reason}") from e

    def list_dataflows(self, agency: str = DEFAULT_AGENCY) -> list[Dataflow]:
        xml = self._get(f"dataflow/{agency}/all/latest").decode("utf-8")
        return parse_dataflows(xml, default_agency=agency)

    def get_data_json(
        self,
        dataflow_id: str,
        *,
        version: str | None = None,
        agency: str = DEFAULT_AGENCY,
        key: str = "all",
        start_period: str | None = None,
        end_period: str | None = None,
    ) -> dict[str, Any]:
        """Fetch a dataflow as SDMX-JSON.

        Tries agency,id,version first, then agency,id (some flows reject a pinned version).
        """
        params: list[str] = []
        if start_period:
            params.append(f"startPeriod={urllib.parse.quote(start_period)}")
        if end_period:
            params.append(f"endPeriod={urllib.parse.quote(end_period)}")
        params.append("format=jsondata")
        qs = "&".join(params)

        candidates: list[str] = []
        if version:
            candidates.append(f"data/{agency},{dataflow_id},{version}/{key}?{qs}")
        candidates.append(f"data/{agency},{dataflow_id}/{key}?{qs}")
        if not version:
            candidates.append(f"data/{agency},{dataflow_id},1.0/{key}?{qs}")
            candidates.append(f"data/{agency},{dataflow_id},1.1/{key}?{qs}")

        last_err: Exception | None = None
        for path in candidates:
            try:
                raw = self._get(path, accept="application/vnd.sdmx.data+json")
                return json.loads(raw.decode("utf-8"))
            except (NSOError, json.JSONDecodeError) as e:
                last_err = e
                continue
        raise NSOError(f"Could not load data for {dataflow_id}: {last_err}")


def parse_dataflows(xml: str, default_agency: str = DEFAULT_AGENCY) -> list[Dataflow]:
    """Parse dataflow structure XML into Dataflow records."""
    blocks = re.findall(
        r"<structure:Dataflow\b([^>]*)>(.*?)</structure:Dataflow>",
        xml,
        flags=re.S,
    )
    out: list[Dataflow] = []
    for attrs, body in blocks:
        id_m = re.search(r'\bid="([^"]+)"', attrs)
        if not id_m:
            continue
        ver_m = re.search(r'\bversion="([^"]+)"', attrs)
        agency_m = re.search(r'\bagencyID="([^"]+)"', attrs)
        name_m = re.search(
            r'<common:Name[^>]*(?:xml:lang="en")?[^>]*>([^<]+)</common:Name>',
            body,
        )
        if not name_m:
            name_m = re.search(r"<common:Name[^>]*>([^<]+)</common:Name>", body)
        out.append(
            Dataflow(
                id=id_m.group(1),
                name=(name_m.group(1).strip() if name_m else id_m.group(1)),
                version=ver_m.group(1) if ver_m else "1.0",
                agency=agency_m.group(1) if agency_m else default_agency,
            )
        )
    out.sort(key=lambda d: d.id.lower())
    return out
