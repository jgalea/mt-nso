"""Flatten SDMX-JSON data messages into row records."""

from __future__ import annotations

from typing import Any


def flatten_sdmx_json(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert an SDMX-JSON data message into a list of flat observation rows."""
    data = payload.get("data") or {}
    datasets = data.get("dataSets") or []
    structures = data.get("structures") or []
    if not datasets or not structures:
        return []

    struct = structures[datasets[0].get("structure", 0)]
    series_dims = (struct.get("dimensions") or {}).get("series") or []
    obs_dims = (struct.get("dimensions") or {}).get("observation") or []
    series_attrs = (struct.get("attributes") or {}).get("series") or []
    obs_attrs = (struct.get("attributes") or {}).get("observation") or []

    flow_name = struct.get("name") or struct.get("names", {}).get("en") or ""
    rows: list[dict[str, Any]] = []

    for series_key, series in (datasets[0].get("series") or {}).items():
        series_labels = _decode_key(series_key, series_dims)
        series_attr_vals = _decode_attrs(series.get("attributes") or [], series_attrs)

        for obs_idx, values in (series.get("observations") or {}).items():
            if not values:
                continue
            row: dict[str, Any] = {}
            if flow_name:
                row["dataflow"] = flow_name
            row.update(series_labels)
            row.update(_decode_obs_index(obs_idx, obs_dims))
            row["value"] = _coerce_number(values[0])
            # observation attributes start after the value at index 0
            if len(values) > 1 and obs_attrs:
                for i, attr_def in enumerate(obs_attrs):
                    if i + 1 >= len(values):
                        break
                    label = _attr_label(attr_def, values[i + 1])
                    if label is not None:
                        row[attr_def.get("id") or f"attr_{i}"] = label
            row.update(series_attr_vals)
            rows.append(row)

    return rows


def _decode_key(key: str, dims: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not key or not dims:
        return out
    parts = key.split(":")
    for i, part in enumerate(parts):
        if i >= len(dims):
            break
        dim = dims[i]
        dim_id = dim.get("id") or f"dim_{i}"
        try:
            idx = int(part)
        except ValueError:
            out[dim_id] = part
            continue
        values = dim.get("values") or []
        if 0 <= idx < len(values):
            val = values[idx]
            out[dim_id] = val.get("name") or val.get("id") or idx
            raw_id = val.get("id")
            if raw_id and raw_id != out[dim_id]:
                out[f"{dim_id}_id"] = raw_id
        else:
            out[dim_id] = idx
    return out


def _decode_obs_index(obs_idx: str, obs_dims: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not obs_dims:
        out["TIME_PERIOD"] = obs_idx
        return out
    # Single observation dimension (usually TIME_PERIOD) is an integer index
    try:
        idx = int(obs_idx)
    except ValueError:
        # multi-dim observation keys use colon separators
        return _decode_key(obs_idx, obs_dims)

    dim = obs_dims[0]
    dim_id = dim.get("id") or "TIME_PERIOD"
    values = dim.get("values") or []
    if 0 <= idx < len(values):
        val = values[idx]
        out[dim_id] = val.get("id") or val.get("name") or idx
    else:
        out[dim_id] = idx
    return out


def _decode_attrs(attr_values: list[Any], attr_defs: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for i, attr_def in enumerate(attr_defs):
        if i >= len(attr_values):
            break
        label = _attr_label(attr_def, attr_values[i])
        if label is not None:
            out[attr_def.get("id") or f"attr_{i}"] = label
    return out


def _attr_label(attr_def: dict[str, Any], raw: Any) -> Any:
    if raw is None:
        return None
    values = attr_def.get("values") or []
    try:
        idx = int(raw)
    except (TypeError, ValueError):
        return raw
    if 0 <= idx < len(values):
        val = values[idx]
        return val.get("name") or val.get("id") or idx
    return raw


def _coerce_number(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    s = str(value).strip()
    if not s:
        return None
    try:
        if "." in s or "e" in s.lower():
            return float(s)
        return int(s)
    except ValueError:
        return value
