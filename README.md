<div align="center">

# mt-nso

[![License](https://img.shields.io/badge/LICENSE-MIT-5C9E31?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/PYTHON-3.9+-3776AB?style=for-the-badge)](https://www.python.org/)
[![Built by](https://img.shields.io/badge/BUILT%20BY-JEAN%20GALEA-8A2BE2?style=for-the-badge)](https://github.com/jgalea)

**CLI for Malta National Statistics Office open data (IRIS SDMX API).**

</div>

```bash
pip install -e .
mt-nso list
mt-nso get cpi --start 2024 --format json
```

## Install

Works on macOS, Linux and Windows. Python 3.9+, no third-party dependencies.

```bash
pipx install git+https://github.com/jgalea/mt-nso
```

`uv tool install git+https://github.com/jgalea/mt-nso` does the same.

From a clone on macOS or Linux:

```bash
cd mt-nso
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

mt-nso list
```

On Windows, in PowerShell:

```powershell
cd mt-nso
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .

mt-nso list
```

The Windows steps haven't been tested on a real Windows machine yet; if something breaks, open an issue.

Or without installing:

```bash
PYTHONPATH=src python3 -m mt_nso list
```

On Windows: `$env:PYTHONPATH = "src"; py -m mt_nso list`.

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
