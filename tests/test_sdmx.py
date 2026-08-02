"""Unit tests for SDMX flattening (no network)."""

from mt_nso.sdmx import flatten_sdmx_json


def test_flatten_basic():
    payload = {
        "data": {
            "dataSets": [
                {
                    "structure": 0,
                    "series": {
                        "0:0": {
                            "attributes": [],
                            "observations": {
                                "0": ["71.1"],
                                "1": ["72.0"],
                            },
                        }
                    },
                }
            ],
            "structures": [
                {
                    "name": "Employment Rate",
                    "dimensions": {
                        "series": [
                            {
                                "id": "SEX",
                                "values": [{"id": "T", "name": "Total"}],
                            },
                            {
                                "id": "AGE",
                                "values": [{"id": "Y20-64", "name": "20-64"}],
                            },
                        ],
                        "observation": [
                            {
                                "id": "TIME_PERIOD",
                                "values": [
                                    {"id": "2020"},
                                    {"id": "2021"},
                                ],
                            }
                        ],
                    },
                    "attributes": {"series": [], "observation": []},
                }
            ],
        }
    }
    rows = flatten_sdmx_json(payload)
    assert len(rows) == 2
    assert rows[0]["dataflow"] == "Employment Rate"
    assert rows[0]["SEX"] == "Total"
    assert rows[0]["AGE"] == "20-64"
    assert rows[0]["TIME_PERIOD"] == "2020"
    assert rows[0]["value"] == 71.1
    assert rows[1]["TIME_PERIOD"] == "2021"
    assert rows[1]["value"] == 72.0


def test_empty_payload():
    assert flatten_sdmx_json({}) == []
    assert flatten_sdmx_json({"data": {}}) == []
