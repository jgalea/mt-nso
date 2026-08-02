# mt-nso

CLI for [Malta National Statistics Office](https://nso.gov.mt/) open data via the IRIS SDMX REST API.

```bash
pip install -e .
mt-nso list
mt-nso get cpi --start 2024 --format json
```

## Install

```bash
cd mt-nso
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

mt-nso list
```

Or without install:

```bash
PYTHONPATH=src python3 -m mt_nso list
```

No third-party dependencies. Python 3.9+.

## Commands

```bash
# list all dataflows (~80+)
mt-nso list
mt-nso list -q population
mt-nso list --format json

# search
mt-nso search tourism

# metadata for one series
mt-nso show DF_CPI
mt-nso show employment

# fetch observations (flattened rows)
mt-nso get DF_SOCSTAT_EMPRATE_ANNUAL
mt-nso get cpi --start 2023 --end 2025
mt-nso get gdp --format csv -o gdp.csv
mt-nso get pop --format json --limit 20

# short aliases
mt-nso aliases
```

### Aliases

| Alias | Dataflow |
|-------|----------|
| `cpi` / `hicp` | `DF_CPI` |
| `rpi` | `DF_RETAIL_PRICE_INDEX_MONTHLY` |
| `pop` / `population` | `DF_TOT_POP_BY_REG_DIST_LOC` |
| `emp` / `employment` | `DF_SOCSTAT_EMPRATE_ANNUAL` |
| `gdp` | `DF_NA_NAMA10GDP` |
| `gdp-q` | `DF_NA_NAMQ10GDP` |
| `tourism` | `DF_DEPARTING_TOURISTS` |
| `waste` | `DF_EAF_WASTE_GEN` |
| `debt` | `DF_GOV_DEBT_ANNUAL` |

## API

Talks to:

```
https://irisapi.nso.gov.mt/nsi_ws/rest/
```

- Structure: `dataflow/MT1/all/latest` (SDMX structure XML)
- Data: `data/MT1,<id>,<version>/all?format=jsondata` (SDMX-JSON)

Browser UI: [iris.nso.gov.mt](https://iris.nso.gov.mt/)

## Output formats

| Flag | Meaning |
|------|---------|
| `--format table` | Human-readable (default) |
| `--format json` | Flat observation rows (or catalog for `list`) |
| `--format csv` | CSV of flat rows (`get` only) |
| `--format raw` | Unmodified SDMX-JSON payload (`get` only) |
| `--format ids` | Dataflow ids only (`list` / `search`) |

## License

MIT
