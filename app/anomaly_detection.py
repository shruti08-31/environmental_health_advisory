"""Independent Anomaly Detection & Event Investigation Module.

Detects unusual changes and investigates potential pollution events across
historical and current pollutant readings (PM25, PM10, NO2, SO2, CO, O3) using
rolling median, IQR, z-score/MAD deviation, and optional Isolation Forest when
sample size is sufficient. Anomalies are strictly indicative and never proof of
a confirmed pollution incident.
"""

from __future__ import annotations

import importlib
import json
import math
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

SUPPORTED_POLLUTANTS: Tuple[str, ...] = ("PM25", "PM10", "NO2", "SO2", "CO", "O3")

POLLUTANT_ALIASES: Dict[str, Tuple[str, ...]] = {
    "PM25": ("PM25", "pm25", "pm2_5", "PM2.5", "pm2.5"),
    "PM10": ("PM10", "pm10"),
    "NO2": ("NO2", "no2"),
    "SO2": ("SO2", "so2"),
    "CO": ("CO", "co"),
    "O3": ("O3", "o3"),
}

POLLUTANT_UNITS: Dict[str, str] = {
    "PM25": "µg/m³",
    "PM10": "µg/m³",
    "NO2": "ppb",
    "SO2": "ppb",
    "CO": "ppm",
    "O3": "ppb",
}

EVENT_CLASSIFICATIONS: Tuple[str, ...] = (
    "Sudden pollution spike",
    "Sustained elevated pollution",
    "Unusual pollutant combination",
    "Localised anomaly",
    "Widespread anomaly",
    "Insufficient data",
)


@dataclass
class AnomalyConfig:
    """Configurable thresholds and data-sufficiency rules."""

    min_historical_samples: int = 6
    min_isolation_forest_samples: int = 24
    rolling_window: int = 6
    iqr_multiplier: float = 1.5
    zscore_threshold: float = 2.5
    sudden_change_ratio: float = 0.50
    sustained_min_consecutive: int = 3
    max_stale_hours: float = 6.0
    localised_ratio_threshold: float = 1.50
    widespread_ratio_threshold: float = 1.25
    isolation_forest_contamination: float = 0.10


DEFAULT_CONFIG = AnomalyConfig()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float_or_none(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, dict):
        for key in ("value", "v", "val", "concentration", "aqi"):
            if key in value:
                return _to_float_or_none(value[key])
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(num):
        return None
    return num


def _parse_timestamp_or_none(raw: Any) -> Optional[datetime]:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        dt = raw
    elif isinstance(raw, str) and raw.strip():
        s = raw.strip()
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(s, fmt)
                    break
                except ValueError:
                    dt = None  # type: ignore[assignment]
            if dt is None:
                return None
    else:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _extract_record_fields(record: Any) -> Tuple[Optional[str], Optional[datetime], Optional[str], Dict[str, Optional[float]], Dict[str, Any]]:
    location: Optional[str] = None
    ts_dt: Optional[datetime] = None
    ts_raw: Optional[str] = None
    pollutants: Dict[str, Optional[float]] = {p: None for p in SUPPORTED_POLLUTANTS}
    context: Dict[str, Any] = {}

    if not isinstance(record, dict):
        return location, ts_dt, ts_raw, pollutants, context

    containers: List[Dict[str, Any]] = [record]
    for nested_key in ("data", "validated_aqi", "raw_aqi", "aqi_data", "reading", "result"):
        nested = record.get(nested_key)
        if isinstance(nested, dict):
            containers.append(nested)

    for loc_key in ("location", "city", "station"):
        for c in containers:
            val = c.get(loc_key)
            if isinstance(val, str) and val.strip():
                location = val.strip()
                break
        if location:
            break

    for ts_key in ("timestamp", "last_updated", "updated_at", "time", "observed_at", "recorded_at"):
        for c in containers:
            val = c.get(ts_key)
            if val is not None:
                parsed = _parse_timestamp_or_none(val)
                if parsed is not None:
                    ts_dt = parsed
                    ts_raw = val if isinstance(val, str) else parsed.isoformat()
                    break
        if ts_dt is not None:
            break

    for ctx_key in ("weather", "meteorology", "context", "land_use"):
        for c in containers:
            if ctx_key in c and c[ctx_key] is not None:
                context[ctx_key] = c[ctx_key]
                break

    pol_dicts: List[Dict[str, Any]] = []
    for c in containers:
        if isinstance(c.get("pollutants"), dict):
            pol_dicts.append(c["pollutants"])
        if isinstance(c.get("iaqi"), dict):
            pol_dicts.append(c["iaqi"])
        pol_dicts.append(c)

    for canonical, aliases in POLLUTANT_ALIASES.items():
        val_found: Optional[float] = None
        for d in pol_dicts:
            for alias in aliases:
                if alias in d:
                    parsed = _to_float_or_none(d[alias])
                    if parsed is not None:
                        val_found = parsed
                        break
            if val_found is not None:
                break
        pollutants[canonical] = val_found

    return location, ts_dt, ts_raw, pollutants, context


def _is_stale(ts_dt: Optional[datetime], max_stale_hours: float) -> bool:
    if ts_dt is None:
        return True
    age_hours = (datetime.now(timezone.utc) - ts_dt).total_seconds() / 3600.0
    return age_hours > max_stale_hours


def _get_db_connection() -> sqlite3.Connection:
    """Reuse existing database connection conventions when available."""
    try:
        db_mod = importlib.import_module("app.history.database")
        if hasattr(db_mod, "get_connection") and callable(db_mod.get_connection):
            conn = db_mod.get_connection()
            if isinstance(conn, sqlite3.Connection):
                return conn
    except Exception:
        pass
    return sqlite3.connect("aqi_history.db")


def _ensure_anomaly_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS anomaly_events (
            event_id TEXT PRIMARY KEY,
            location TEXT NOT NULL,
            pollutant TEXT,
            event_classification TEXT NOT NULL,
            severity TEXT NOT NULL,
            investigation_status TEXT NOT NULL,
            current_value REAL,
            baseline_value REAL,
            deviation REAL,
            detection_method TEXT,
            consecutive_count INTEGER DEFAULT 1,
            detected_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )
        """
    )
    conn.commit()


def _retrieve_history_from_db(location: str, limit: int = 200) -> List[Dict[str, Any]]:
    """Retrieve historical records from existing history database or SQLite table."""
    try:
        db_mod = importlib.import_module("app.history.database")
        if hasattr(db_mod, "get_aqi_history") and callable(db_mod.get_aqi_history):
            rows = db_mod.get_aqi_history(location=location)
            if isinstance(rows, pd.DataFrame):
                return [r for r in rows.to_dict(orient="records") if isinstance(r, dict)][-limit:]
            if isinstance(rows, list):
                return [r for r in rows if isinstance(r, dict)][-limit:]
    except Exception:
        pass

    try:
        conn = _get_db_connection()
        try:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='aqi_history'"
            )
            if not cur.fetchone():
                return []
            cur = conn.execute(
                "SELECT * FROM aqi_history WHERE LOWER(location) = LOWER(?) ORDER BY rowid DESC LIMIT ?",
                (location, limit),
            )
            cols = [c[0] for c in cur.description]
            fetched = [dict(zip(cols, row)) for row in cur.fetchall()]
            fetched.reverse()
            return fetched
        finally:
            conn.close()
    except Exception:
        return []


def _consecutive_tail_count(series: pd.Series, anomalous_mask: pd.Series) -> int:
    """Count consecutive anomalous readings at the end of a series."""
    count = 0
    for idx in range(len(series) - 1, -1, -1):
        if pd.isna(series.iloc[idx]):
            continue
        if bool(anomalous_mask.iloc[idx]):
            count += 1
        else:
            break
    return count


def _run_isolation_forest_flags(
    df: pd.DataFrame,
    available_cols: List[str],
    config: AnomalyConfig,
) -> Tuple[Optional[pd.Series], Optional[str]]:
    """Run Isolation Forest only when sample size and scikit-learn availability allow."""
    valid_rows = df[available_cols].dropna()
    if len(valid_rows) < config.min_isolation_forest_samples or len(available_cols) < 1:
        return None, None

    try:
        sk_ensemble = importlib.import_module("sklearn.ensemble")
        iso_cls = getattr(sk_ensemble, "IsolationForest", None)
        if iso_cls is None:
            return None, None
        model = iso_cls(
            n_estimators=100,
            contamination=config.isolation_forest_contamination,
            random_state=42,
        )
        preds = model.fit_predict(valid_rows.to_numpy(dtype=float))
        flagged_index = valid_rows.index[preds == -1]
        mask = pd.Series(False, index=df.index)
        mask.loc[flagged_index] = True
        return mask, "isolation_forest"
    except Exception:
        return None, None


def compare_nearby_stations(
    target_location: str,
    target_pollutants: Dict[str, Optional[float]],
    nearby_readings: Optional[Sequence[Dict[str, Any]]] = None,
    config: AnomalyConfig = DEFAULT_CONFIG,
) -> Dict[str, Any]:
    """Compare target station pollutant readings with available nearby stations.

    Does not fabricate nearby station data; returns 'no_nearby_station_data'
    when no valid nearby station readings are provided.
    """
    readings = list(nearby_readings or [])
    if not readings:
        return {
            "available": False,
            "comparison_status": "no_nearby_station_data",
            "target_location": target_location,
            "stations_compared": [],
            "pollutant_comparisons": {},
            "note": "No nearby monitoring station data available.",
        }

    station_summaries: List[Dict[str, Any]] = []
    per_pollutant_ratios: Dict[str, List[float]] = {p: [] for p in SUPPORTED_POLLUTANTS}

    for rec in readings:
        st_loc, st_ts, st_ts_raw, st_pols, _ = _extract_record_fields(rec)
        label = st_loc or "Unnamed Station"
        stale = _is_stale(st_ts, config.max_stale_hours)
        valid_pols = {k: v for k, v in st_pols.items() if v is not None}

        for pol, t_val in target_pollutants.items():
            s_val = st_pols.get(pol)
            if t_val is not None and s_val is not None and s_val > 0 and not stale:
                per_pollutant_ratios[pol].append(round(t_val / s_val, 3))

        station_summaries.append(
            {
                "station": label,
                "timestamp": st_ts_raw,
                "is_stale": stale,
                "pollutants": valid_pols,
            }
        )

    pollutant_comparisons: Dict[str, Any] = {}
    max_ratio_seen: Optional[float] = None
    for pol in SUPPORTED_POLLUTANTS:
        ratios = per_pollutant_ratios[pol]
        if ratios:
            median_ratio = float(np.median(np.asarray(ratios, dtype=float)))
            if max_ratio_seen is None or median_ratio > max_ratio_seen:
                max_ratio_seen = median_ratio
            if median_ratio >= config.localised_ratio_threshold:
                pattern = "potentially_localised_higher"
            elif median_ratio >= config.widespread_ratio_threshold:
                pattern = "moderately_elevated_vs_nearby"
            else:
                pattern = "consistent_with_nearby"
            pollutant_comparisons[pol] = {
                "target_value": target_pollutants.get(pol),
                "median_target_to_nearby_ratio": round(median_ratio, 3),
                "nearby_sample_count": len(ratios),
                "pattern": pattern,
            }

    if not pollutant_comparisons:
        status = "no_comparable_fresh_nearby_pollutants"
    elif max_ratio_seen is not None and max_ratio_seen >= config.localised_ratio_threshold:
        status = "potentially_localised"
    elif max_ratio_seen is not None and max_ratio_seen >= config.widespread_ratio_threshold:
        status = "elevated_across_area_indicative"
    else:
        status = "consistent_with_nearby_stations"

    return {
        "available": True,
        "comparison_status": status,
        "target_location": target_location,
        "stations_compared": station_summaries,
        "pollutant_comparisons": pollutant_comparisons,
    }


def detect_anomalies(
    location: str,
    *,
    historical_records: Optional[Sequence[Dict[str, Any]]] = None,
    current_reading: Optional[Dict[str, Any]] = None,
    nearby_stations: Optional[Sequence[Dict[str, Any]]] = None,
    config: AnomalyConfig = DEFAULT_CONFIG,
) -> Dict[str, Any]:
    """Detect unusual pollutant changes using rolling median, IQR, z-score, and optional Isolation Forest."""
    if not location or not location.strip():
        raise ValueError("Location must be a non-empty string.")
    loc_clean = location.strip()

    raw_history = list(historical_records) if historical_records is not None else _retrieve_history_from_db(loc_clean)

    parsed_rows: List[Dict[str, Any]] = []
    data_warnings: List[str] = []

    for rec in raw_history:
        r_loc, r_ts, r_ts_raw, r_pols, r_ctx = _extract_record_fields(rec)
        parsed_rows.append(
            {
                "location": r_loc or loc_clean,
                "ts_dt": r_ts,
                "timestamp": r_ts_raw,
                "context": r_ctx,
                **r_pols,
            }
        )

    current_ctx: Dict[str, Any] = {}
    current_ts_raw: Optional[str] = None
    current_ts_dt: Optional[datetime] = None
    current_pols: Dict[str, Optional[float]] = {p: None for p in SUPPORTED_POLLUTANTS}

    if current_reading is not None:
        c_loc, c_ts, c_ts_raw, c_pols, c_ctx = _extract_record_fields(current_reading)
        current_ts_dt = c_ts
        current_ts_raw = c_ts_raw
        current_pols = c_pols
        current_ctx = c_ctx
        if _is_stale(c_ts, config.max_stale_hours):
            data_warnings.append("Current reading timestamp is missing or older than configured freshness window.")
        parsed_rows.append(
            {
                "location": c_loc or loc_clean,
                "ts_dt": c_ts,
                "timestamp": c_ts_raw,
                "context": c_ctx,
                **c_pols,
            }
        )

    if not parsed_rows:
        return {
            "location": loc_clean,
            "generated_at": _utc_now_iso(),
            "status": "insufficient_data",
            "classification": "Insufficient data",
            "warnings": ["No historical or current pollutant records available."],
            "anomalies": [],
            "unusual_combinations": [],
            "nearby_comparison": compare_nearby_stations(loc_clean, current_pols, nearby_stations, config),
        }

    df = pd.DataFrame(parsed_rows)
    if df["ts_dt"].notna().any():
        df["_sort_ts"] = df["ts_dt"].fillna(datetime.min.replace(tzinfo=timezone.utc))
        df = df.sort_values("_sort_ts").reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)

    if current_reading is None:
        last_row = df.iloc[-1]
        current_ts_dt = last_row.get("ts_dt") if isinstance(last_row.get("ts_dt"), datetime) else None
        current_ts_raw = last_row.get("timestamp")
        current_ctx = last_row.get("context") if isinstance(last_row.get("context"), dict) else {}
        current_pols = {p: _to_float_or_none(last_row.get(p)) for p in SUPPORTED_POLLUTANTS}
        if _is_stale(current_ts_dt, config.max_stale_hours):
            data_warnings.append("Latest available observation timestamp is missing or stale.")

    active_pols = [p for p in SUPPORTED_POLLUTANTS if current_pols.get(p) is not None]
    if not active_pols:
        data_warnings.append("No non-missing pollutant values in latest reading; missing values are not treated as zero.")
        return {
            "location": loc_clean,
            "generated_at": _utc_now_iso(),
            "observation_timestamp": current_ts_raw,
            "status": "insufficient_data",
            "classification": "Insufficient data",
            "warnings": data_warnings,
            "anomalies": [],
            "unusual_combinations": [],
            "nearby_comparison": compare_nearby_stations(loc_clean, current_pols, nearby_stations, config),
        }

    hist_df = df.iloc[:-1] if current_reading is not None and len(df) > 1 else df

    iso_cols = [
        p
        for p in SUPPORTED_POLLUTANTS
        if int(hist_df[p].notna().sum()) >= config.min_historical_samples
    ]
    iso_mask, iso_label = _run_isolation_forest_flags(df, iso_cols, config)

    nearby_comp = compare_nearby_stations(loc_clean, current_pols, nearby_stations, config)
    detected_events: List[Dict[str, Any]] = []
    anomalous_pol_names: List[str] = []
    sufficient_pol_count = 0

    for pol in active_pols:
        cur_val = current_pols[pol]
        assert cur_val is not None

        hist_series = hist_df[pol].dropna().astype(float)
        if len(hist_series) < config.min_historical_samples:
            data_warnings.append(
                f"{pol}: fewer than {config.min_historical_samples} valid historical samples ({len(hist_series)} found)."
            )
            continue

        sufficient_pol_count += 1
        rolling_med_series = hist_series.rolling(
            window=min(config.rolling_window, len(hist_series)), min_periods=1
        ).median()
        rolling_baseline = float(rolling_med_series.iloc[-1])

        q25 = float(np.percentile(hist_series, 25))
        q75 = float(np.percentile(hist_series, 75))
        iqr = q75 - q25
        upper_iqr = q75 + config.iqr_multiplier * iqr
        lower_iqr = q25 - config.iqr_multiplier * iqr

        mean_val = float(np.mean(hist_series))
        std_val = float(np.std(hist_series, ddof=1)) if len(hist_series) > 1 else 0.0
        has_variance = std_val > 1e-9
        z_score = ((cur_val - mean_val) / std_val) if has_variance else 0.0

        prior_non_null = float(hist_series.iloc[-1])
        pct_change_from_prev = (
            ((cur_val - prior_non_null) / prior_non_null) if prior_non_null > 0 else None
        )

        full_series = df[pol].astype(float)
        full_roll_med = full_series.rolling(
            window=min(config.rolling_window, max(1, len(full_series))), min_periods=1
        ).median()

        point_anom_mask = pd.Series(False, index=df.index)
        if iqr > 1e-9:
            point_anom_mask = point_anom_mask | (full_series > upper_iqr) | (full_series < lower_iqr)
        if has_variance:
            point_anom_mask = point_anom_mask | (
                (full_series - mean_val).abs() > config.zscore_threshold * std_val
            )
        if iso_mask is not None and pol in iso_cols:
            point_anom_mask = point_anom_mask | iso_mask

        consec_count = max(1, _consecutive_tail_count(full_series, point_anom_mask))

        is_iqr_anom = iqr > 1e-9 and (cur_val > upper_iqr or cur_val < lower_iqr)
        is_z_anom = has_variance and abs(z_score) >= config.zscore_threshold
        is_sudden_shift = (
            pct_change_from_prev is not None and abs(pct_change_from_prev) >= config.sudden_change_ratio
        )
        is_iso_anom = bool(iso_mask is not None and pol in iso_cols and iso_mask.iloc[-1])

        methods_triggered: List[str] = []
        if is_iqr_anom:
            methods_triggered.append("rolling_median_and_iqr")
        if is_z_anom:
            methods_triggered.append("statistical_deviation_zscore")
        if is_iso_anom and iso_label:
            methods_triggered.append(iso_label)
        if is_sudden_shift and not methods_triggered:
            methods_triggered.append("sudden_step_change")

        if methods_triggered:
            anomalous_pol_names.append(pol)
            deviation = round(cur_val - rolling_baseline, 3)

            if consec_count >= config.sustained_min_consecutive and cur_val > rolling_baseline:
                classification = "Sustained elevated pollution"
            elif pct_change_from_prev is not None and pct_change_from_prev >= config.sudden_change_ratio:
                classification = "Sudden pollution spike"
            elif nearby_comp.get("comparison_status") == "potentially_localised":
                classification = "Localised anomaly"
            elif nearby_comp.get("comparison_status") == "elevated_across_area_indicative":
                classification = "Widespread anomaly"
            else:
                classification = "Sudden pollution spike" if deviation >= 0 else "Unusual pollutant combination"

            elevated_ratio = (cur_val / rolling_baseline) if rolling_baseline > 0 else 1.0
            if (has_variance and abs(z_score) >= 3.5) or elevated_ratio >= 2.0:
                severity = "high"
            elif (has_variance and abs(z_score) >= config.zscore_threshold) or is_iqr_anom or elevated_ratio >= 1.5:
                severity = "moderate"
            else:
                severity = "low"

            direction_text = "above" if deviation >= 0 else "below"
            pct_text = (
                f" ({pct_change_from_prev * 100:+.1f}% vs. prior reading)"
                if pct_change_from_prev is not None
                else ""
            )
            possible_explanation = (
                f"Indicative signal only (not confirmed): {pol} is {abs(deviation):.2f} {POLLUTANT_UNITS[pol]} "
                f"{direction_text} rolling median baseline ({rolling_baseline:.2f} {POLLUTANT_UNITS[pol]}){pct_text}. "
                "Requires meteorological, dispersion, or local activity context to evaluate further."
            )

            event_id = f"ANO-{uuid.uuid4().hex[:8].upper()}"
            detected_events.append(
                {
                    "event_id": event_id,
                    "location": loc_clean,
                    "pollutant": pol,
                    "current_measurement": cur_val,
                    "unit": POLLUTANT_UNITS[pol],
                    "historical_baseline": round(rolling_baseline, 3),
                    "baseline_window_median": round(float(full_roll_med.iloc[-1]), 3),
                    "deviation": deviation,
                    "z_score": round(z_score, 3) if has_variance else None,
                    "detection_method": ", ".join(methods_triggered),
                    "detection_timestamp": current_ts_raw or _utc_now_iso(),
                    "duration_observations": consec_count,
                    "classification": classification,
                    "nearby_station_comparison": nearby_comp if nearby_comp.get("available") else None,
                    "contextual_observations": current_ctx if current_ctx else None,
                    "possible_explanation": possible_explanation,
                    "severity": severity,
                    "investigation_status": "open",
                    "disclaimer": "Anomaly detection indicates statistical deviation only and is not proof of a pollution incident.",
                }
            )

    # Identify unusual pollutant combinations only when 2+ pollutants are anomalous
    # and the combination is focused (e.g., <= 3 co-anomalous pollutants)
    unusual_combinations: List[Dict[str, Any]] = []
    if 2 <= len(anomalous_pol_names) <= 3:
        combo_event = {
            "event_id": f"ANO-{uuid.uuid4().hex[:8].upper()}",
            "location": loc_clean,
            "pollutant": "+".join(anomalous_pol_names),
            "pollutants_involved": anomalous_pol_names,
            "current_measurement": {p: current_pols[p] for p in anomalous_pol_names},
            "historical_baseline": None,
            "deviation": None,
            "detection_method": "multi_pollutant_co_deviation",
            "detection_timestamp": current_ts_raw or _utc_now_iso(),
            "duration_observations": 1,
            "classification": "Unusual pollutant combination",
            "nearby_station_comparison": nearby_comp if nearby_comp.get("available") else None,
            "contextual_observations": current_ctx if current_ctx else None,
            "possible_explanation": (
                f"Indicative signal only (not confirmed): multiple pollutants ({', '.join(anomalous_pol_names)}) "
                "show concurrent unusual deviation in the same observation window."
            ),
            "severity": "moderate",
            "investigation_status": "open",
            "disclaimer": "Co-occurring deviations do not confirm a specific emission event.",
        }
        unusual_combinations.append(combo_event)
        detected_events.append(combo_event)

    if not detected_events:
        if sufficient_pol_count == 0:
            overall_class = "Insufficient data"
            status = "insufficient_data"
        else:
            overall_class = "Normal / No Anomaly"
            status = "normal"
    else:
        status = "anomalies_detected"
        if len(unusual_combinations) > 0:
            overall_class = "Unusual pollutant combination"
        elif nearby_comp.get("comparison_status") == "potentially_localised":
            overall_class = "Localised anomaly"
        elif nearby_comp.get("comparison_status") == "elevated_across_area_indicative":
            overall_class = "Widespread anomaly"
        else:
            overall_class = detected_events[0]["classification"]

    return {
        "location": loc_clean,
        "generated_at": _utc_now_iso(),
        "observation_timestamp": current_ts_raw,
        "status": status,
        "classification": overall_class,
        "warnings": data_warnings,
        "anomalies": detected_events,
        "unusual_combinations": unusual_combinations,
        "nearby_comparison": nearby_comp,
    }


def investigate_pollution_event(
    event: Dict[str, Any],
    *,
    nearby_stations: Optional[Sequence[Dict[str, Any]]] = None,
    contextual_data: Optional[Dict[str, Any]] = None,
    investigation_status: str = "under_investigation",
    config: AnomalyConfig = DEFAULT_CONFIG,
) -> Dict[str, Any]:
    """Enrich an anomaly event with structured investigation details and status tracking."""
    if not isinstance(event, dict):
        raise ValueError("Event must be a dictionary.")

    enriched = dict(event)
    loc = enriched.get("location") or "Unknown"
    target_pols: Dict[str, Optional[float]] = {p: None for p in SUPPORTED_POLLUTANTS}
    pol_field = enriched.get("pollutant")
    if isinstance(pol_field, str) and pol_field in SUPPORTED_POLLUTANTS:
        target_pols[pol_field] = _to_float_or_none(enriched.get("current_measurement"))

    nearby_result = compare_nearby_stations(loc, target_pols, nearby_stations, config)
    if nearby_result.get("available"):
        enriched["nearby_station_comparison"] = nearby_result

    merged_ctx: Dict[str, Any] = {}
    if isinstance(enriched.get("contextual_observations"), dict):
        merged_ctx.update(enriched["contextual_observations"])
    if isinstance(contextual_data, dict) and contextual_data:
        merged_ctx.update(contextual_data)
    enriched["contextual_observations"] = merged_ctx if merged_ctx else None

    enriched["investigation_status"] = investigation_status
    enriched["investigated_at"] = _utc_now_iso()
    enriched.setdefault(
        "disclaimer",
        "Investigation findings are indicative and do not confirm a specific fire, industrial, or construction incident.",
    )
    return enriched


def save_anomaly_event(event: Dict[str, Any]) -> str:
    """Persist an anomaly event to SQLite using existing database conventions."""
    if not isinstance(event, dict):
        raise ValueError("Event must be a dictionary.")

    event_id = str(event.get("event_id") or f"ANO-{uuid.uuid4().hex[:8].upper()}")
    now_iso = _utc_now_iso()
    cur_num = _to_float_or_none(event.get("current_measurement"))
    base_num = _to_float_or_none(event.get("historical_baseline"))
    dev_num = _to_float_or_none(event.get("deviation"))
    consec = int(event.get("duration_observations") or 1)

    conn = _get_db_connection()
    try:
        _ensure_anomaly_table(conn)
        conn.execute(
            """
            INSERT OR REPLACE INTO anomaly_events (
                event_id, location, pollutant, event_classification, severity,
                investigation_status, current_value, baseline_value, deviation,
                detection_method, consecutive_count, detected_at, updated_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                str(event.get("location") or "Unknown"),
                str(event.get("pollutant") or ""),
                str(event.get("classification") or "Insufficient data"),
                str(event.get("severity") or "low"),
                str(event.get("investigation_status") or "open"),
                cur_num,
                base_num,
                dev_num,
                str(event.get("detection_method") or ""),
                consec,
                str(event.get("detection_timestamp") or now_iso),
                now_iso,
                json.dumps(event, default=str),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return event_id


def get_anomaly_history(
    location: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Retrieve persisted anomaly events with optional location and investigation status filters."""
    conn = _get_db_connection()
    try:
        _ensure_anomaly_table(conn)
        query = "SELECT payload_json FROM anomaly_events WHERE 1=1"
        params: List[Any] = []
        if location and location.strip():
            query += " AND LOWER(location) = LOWER(?)"
            params.append(location.strip())
        if status and status.strip():
            query += " AND LOWER(investigation_status) = LOWER(?)"
            params.append(status.strip())
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(int(limit))

        cur = conn.execute(query, params)
        results: List[Dict[str, Any]] = []
        for (payload_str,) in cur.fetchall():
            try:
                parsed = json.loads(payload_str)
                if isinstance(parsed, dict):
                    results.append(parsed)
            except json.JSONDecodeError:
                continue
        return results
    finally:
        conn.close()


def generate_event_summary(detection_result: Dict[str, Any]) -> str:
    """Create a concise, non-sensational human-readable summary of detected anomalies."""
    if not isinstance(detection_result, dict):
        return "No anomaly detection data available."

    loc = detection_result.get("location") or "Unknown"
    obs_ts = detection_result.get("observation_timestamp") or "timestamp unavailable"
    classification = detection_result.get("classification") or "Insufficient data"
    anomalies = detection_result.get("anomalies") or []
    warnings = detection_result.get("warnings") or []

    if not anomalies:
        warn_suffix = f" Warnings: {'; '.join(warnings)}." if warnings else ""
        return (
            f"Anomaly check for {loc} (observation: {obs_ts}): {classification}. "
            f"No anomalous pollutant deviations flagged.{warn_suffix}"
        )

    details: List[str] = []
    for item in anomalies:
        pol = item.get("pollutant")
        cur = item.get("current_measurement")
        base = item.get("historical_baseline")
        dev = item.get("deviation")
        sev = item.get("severity")
        status = item.get("investigation_status")
        dur = item.get("duration_observations", 1)
        if base is not None and dev is not None:
            details.append(
                f"{pol} at {cur} (baseline {base}, deviation {dev:+g}, {dur} obs, severity {sev}, status: {status})"
            )
        else:
            details.append(
                f"{pol} combination (severity {sev}, status: {status})"
            )

    return (
        f"Indicative anomaly summary for {loc} (observation: {obs_ts}, classification: {classification}): "
        + "; ".join(details)
        + ". Note: anomalies indicate statistical variation and do not confirm a pollution incident."
    )