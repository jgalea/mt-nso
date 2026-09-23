"""Command-line interface for mt-nso."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from typing import Any, Iterable, Sequence, TextIO

from mt_nso import __version__
from mt_nso.client import DEFAULT_BASE, Dataflow, NSOClient, NSOError
from mt_nso.sdmx import flatten_sdmx_json


def main(argv: Sequence[str] | None = None) -> int:
    # A Windows console or pipe may not be UTF-8; print what it can rather than crash.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    try:
        return _main(argv)
    except BrokenPipeError:
        # e.g. `mt-nso get gdp | head`
        try:
            sys.stdout.close()
        except Exception:
            pass
        return 0


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mt-nso",
        description="Malta NSO open data CLI (IRIS SDMX API)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE,
        help=f"API base URL (default: {DEFAULT_BASE})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=90.0,
        help="HTTP timeout in seconds (default: 90)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List available dataflows")
    p_list.add_argument("-q", "--query", help="Filter by id or name substring")
    p_list.add_argument(
        "--format",
        choices=("table", "json", "ids"),
        default="table",
        dest="fmt",
    )

    p_search = sub.add_parser("search", help="Search dataflows by keyword")
    p_search.add_argument("query", help="Substring matched against id and name")
    p_search.add_argument(
        "--format",
        choices=("table", "json", "ids"),
        default="table",
        dest="fmt",
    )

    p_show = sub.add_parser("show", help="Show metadata for one dataflow")
    p_show.add_argument("dataflow", help="Dataflow id (e.g. DF_CPI or DF_SOCSTAT_EMPRATE_ANNUAL)")
    p_show.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        dest="fmt",
    )

    p_get = sub.add_parser("get", help="Download and flatten a dataflow")
    p_get.add_argument("dataflow", help="Dataflow id")
    p_get.add_argument("--version", help="Pin a dataflow version (default: from catalog)")
    p_get.add_argument("--start", dest="start_period", help="Start period (e.g. 2020 or 2020-01)")
    p_get.add_argument("--end", dest="end_period", help="End period")
    p_get.add_argument(
        "--format",
        choices=("table", "json", "csv", "raw"),
        default="table",
        dest="fmt",
    )
    p_get.add_argument("-o", "--output", help="Write to file instead of stdout")
    p_get.add_argument("--limit", type=int, help="Max rows to print (table/json only)")

    p_alias = sub.add_parser("aliases", help="Show common short aliases")
    p_alias.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        dest="fmt",
    )

    args = parser.parse_args(argv)
    client = NSOClient(base_url=args.base_url, timeout=args.timeout)

    try:
        if args.command == "list":
            return cmd_list(client, query=args.query, fmt=args.fmt)
        if args.command == "search":
            return cmd_list(client, query=args.query, fmt=args.fmt)
        if args.command == "show":
            return cmd_show(client, args.dataflow, fmt=args.fmt)
        if args.command == "get":
            return cmd_get(
                client,
                dataflow_id=args.dataflow,
                version=args.version,
                start_period=args.start_period,
                end_period=args.end_period,
                fmt=args.fmt,
                output=args.output,
                limit=args.limit,
            )
        if args.command == "aliases":
            return cmd_aliases(fmt=args.fmt)
    except NSOError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130

    parser.error(f"unknown command: {args.command}")
    return 2


# Common short names -> dataflow ids
ALIASES: dict[str, str] = {
    "cpi": "DF_CPI",
    "hicp": "DF_CPI",
    "rpi": "DF_RETAIL_PRICE_INDEX_MONTHLY",
    "population": "DF_TOT_POP_BY_REG_DIST_LOC",
    "pop": "DF_TOT_POP_BY_REG_DIST_LOC",
    "employment": "DF_SOCSTAT_EMPRATE_ANNUAL",
    "emp": "DF_SOCSTAT_EMPRATE_ANNUAL",
    "gdp": "DF_NA_NAMA10GDP",
    "gdp-q": "DF_NA_NAMQ10GDP",
    "tourism": "DF_DEPARTING_TOURISTS",
    "waste": "DF_EAF_WASTE_GEN",
    "debt": "DF_GOV_DEBT_ANNUAL",
}


def resolve_dataflow_id(raw: str) -> str:
    key = raw.strip()
    return ALIASES.get(key.lower(), key)


def cmd_list(client: NSOClient, query: str | None, fmt: str) -> int:
    flows = client.list_dataflows()
    if query:
        q = query.lower()
        flows = [f for f in flows if q in f.id.lower() or q in f.name.lower()]
    if fmt == "json":
        print(json.dumps([_flow_dict(f) for f in flows], indent=2, ensure_ascii=False))
    elif fmt == "ids":
        for f in flows:
            print(f.id)
    else:
        _print_flow_table(flows)
    return 0


def cmd_show(client: NSOClient, dataflow: str, fmt: str) -> int:
    dataflow_id = resolve_dataflow_id(dataflow)
    flows = client.list_dataflows()
    match = next((f for f in flows if f.id.lower() == dataflow_id.lower()), None)
    if not match:
        # partial match
        matches = [f for f in flows if dataflow_id.lower() in f.id.lower()]
        if len(matches) == 1:
            match = matches[0]
        elif matches:
            print(f"error: ambiguous dataflow {dataflow_id!r}; matches:", file=sys.stderr)
            for f in matches:
                print(f"  {f.id}", file=sys.stderr)
            return 1
        else:
            print(f"error: dataflow not found: {dataflow_id}", file=sys.stderr)
            return 1

    if fmt == "json":
        print(json.dumps(_flow_dict(match), indent=2, ensure_ascii=False))
    else:
        print(f"id:       {match.id}")
        print(f"name:     {match.name}")
        print(f"version:  {match.version}")
        print(f"agency:   {match.agency}")
        print(f"ref:      {match.ref}")
        alias = next((k for k, v in ALIASES.items() if v == match.id), None)
        if alias:
            print(f"alias:    {alias}")
    return 0


def cmd_get(
    client: NSOClient,
    *,
    dataflow_id: str,
    version: str | None,
    start_period: str | None,
    end_period: str | None,
    fmt: str,
    output: str | None,
    limit: int | None,
) -> int:
    dataflow_id = resolve_dataflow_id(dataflow_id)

    if version is None:
        try:
            flows = client.list_dataflows()
            match = next((f for f in flows if f.id.lower() == dataflow_id.lower()), None)
            if match:
                dataflow_id = match.id
                version = match.version
        except NSOError:
            pass

    payload = client.get_data_json(
        dataflow_id,
        version=version,
        start_period=start_period,
        end_period=end_period,
    )

    out: TextIO
    close = False
    if output:
        out = open(output, "w", encoding="utf-8", newline="")
        close = True
    else:
        out = sys.stdout

    try:
        if fmt == "raw":
            json.dump(payload, out, indent=2, ensure_ascii=False)
            out.write("\n")
            return 0

        rows = flatten_sdmx_json(payload)
        if limit is not None:
            rows = rows[:limit]

        if fmt == "json":
            json.dump(rows, out, indent=2, ensure_ascii=False)
            out.write("\n")
        elif fmt == "csv":
            _write_csv(rows, out)
        else:
            _print_rows_table(rows, out)
            if not output:
                print(f"\n# {len(rows)} rows", file=sys.stderr)
        return 0
    finally:
        if close:
            out.close()
            print(f"wrote {output}", file=sys.stderr)


def cmd_aliases(fmt: str) -> int:
    items = [{"alias": k, "dataflow": v} for k, v in sorted(ALIASES.items())]
    if fmt == "json":
        print(json.dumps(items, indent=2))
    else:
        print(f"{'ALIAS':<12} DATAFLOW")
        print(f"{'-----':<12} --------")
        for item in items:
            print(f"{item['alias']:<12} {item['dataflow']}")
    return 0


def _flow_dict(f: Dataflow) -> dict[str, str]:
    return {
        "id": f.id,
        "name": f.name,
        "version": f.version,
        "agency": f.agency,
        "ref": f.ref,
    }


def _print_flow_table(flows: Iterable[Dataflow]) -> None:
    rows = list(flows)
    if not rows:
        print("No dataflows matched.")
        return
    id_w = max(len(f.id) for f in rows)
    id_w = max(id_w, 2)
    print(f"{'ID':<{id_w}}  VER   NAME")
    print(f"{'--':<{id_w}}  ---   ----")
    for f in rows:
        print(f"{f.id:<{id_w}}  {f.version:<5} {f.name}")
    print(f"\n# {len(rows)} dataflows", file=sys.stderr)


def _write_csv(rows: list[dict[str, Any]], out: TextIO) -> None:
    if not rows:
        return
    # stable column order: common keys first
    keys: list[str] = []
    for row in rows:
        for k in row:
            if k not in keys:
                keys.append(k)
    writer = csv.DictWriter(out, fieldnames=keys, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)


def _print_rows_table(rows: list[dict[str, Any]], out: TextIO) -> None:
    if not rows:
        print("No observations.", file=out)
        return

    # Prefer a compact column set for terminal reading
    preferred = [
        "TIME_PERIOD",
        "value",
        "FREQ",
        "dataflow",
    ]
    # plus a few dimension columns that vary
    skip = {"dataflow"}
    dim_keys = [
        k
        for k in rows[0]
        if k not in preferred and not k.endswith("_id") and k not in skip
    ]
    cols = [c for c in preferred if c in rows[0]]
    # keep table readable: max ~6 dim columns
    cols.extend(dim_keys[:6])

    widths = {c: len(c) for c in cols}
    rendered: list[dict[str, str]] = []
    for row in rows:
        r = {c: _cell(row.get(c)) for c in cols}
        rendered.append(r)
        for c in cols:
            widths[c] = max(widths[c], len(r[c]))

    # cap wide columns
    for c in cols:
        widths[c] = min(widths[c], 40)

    header = "  ".join(c.ljust(widths[c]) for c in cols)
    print(header, file=out)
    print("  ".join("-" * widths[c] for c in cols), file=out)
    for r in rendered:
        print("  ".join(r[c][: widths[c]].ljust(widths[c]) for c in cols), file=out)


def _cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
