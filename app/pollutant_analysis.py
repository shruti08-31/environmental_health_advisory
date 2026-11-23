"""Independent Pollutant Analysis Engine for Environmental Health Advisory.

Analyses available pollutant measurements (PM2.5, PM10, NO2, SO2, CO, O3) from
the existing AQI data pipeline and historical database without modifying unrelated
modules or inventing measurements, baselines, or confirmed source attributions.
"""

from __future__ import annotations

import importlib
import math
from typing import Any, Dict, List, Optional, Tuple

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

POSSIBLE_SOURCE_CATEGORIES: Tuple[str, ...] = (
    "Traffic emissions",
    "Construction and road dust",
    "Industrial activity",
    "Fuel combustion",
    "Regional or transported pollution",
)

# Relative elevation ratio (current / baseline) used only to compare against
# measured historical baselines when actual historical rows exist.
ELEVATION_RATIO_THRESHOLD: float = 1.25
HIGH_ELEVATION_RATIO_THRESHOLD: float = 1.60


def _to_float_or_none(value: Any) -> Optional[float]:
    """Convert numeric values safely; treat None, NaN, inf, or booleans as missing."""
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


def _extract_pollutants_and_meta(payload: Any) -> Tuple[Optional[str], Optional[str], Dict[str, Optional[float]], Dict[str, Any]]:
    """Extract location, timestamp, available pollutants, and any optional context fields."""
    location: Optional[str] = None
    timestamp: Optional[str] = None
    extracted: Dict[str, Optional[float]] = {p: None for p in SUPPORTED_POLLUTANTS}
    context_meta: Dict[str, Any] = {}

    if not isinstance(payload, dict):
        return location, timestamp, extracted, context_meta

    # Unwrap nested structures commonly produced by pipeline or service layers
    candidates: List[Dict[str, Any]] = [payload]
    for nested_key in ("data", "validated_aqi", "raw_aqi", "aqi_data", "result", "reading"):
        nested = payload.get(nested_key)
        if isinstance(nested, dict):
            candidates.append(nested)

    for loc_key in ("location", "city", "station"):
        for container in candidates:
            val = container.get(loc_key)
            if isinstance(val, str) and val.strip():
                location = val.strip()
                break
        if location:
            break

    for ts_key in ("timestamp", "last_updated", "updated_at", "time", "observed_at"):
        for container in candidates:
            val = container.get(ts_key)
            if isinstance(val, str) and val.strip():
                timestamp = val.strip()
                break
        if timestamp:
            break

    for ctx_key in ("land_use", "nearby_land_use", "weather", "meteorology"):
        for container in candidates:
            if ctx_key in container and container[ctx_key] is not None:
                context_meta[ctx_key] = container[ctx_key]
                break

    pollutant_dicts: List[Dict[str, Any]] = []
    for container in candidates:
        pollutants_obj = container.get("pollutants")
        if isinstance(pollutants_obj, dict):
            pollutant_dicts.append(pollutants_obj)
        iaqi_obj = container.get("iaqi")
        if isinstance(iaqi_obj, dict):
            pollutant_dicts.append(iaqi_obj)
        pollutant_dicts.append(container)

    for canonical, aliases in POLLUTANT_ALIASES.items():
        found_val: Optional[float] = None
        for p_dict in pollutant_dicts:
            for alias in aliases:
                if alias in p_dict:
                    parsed = _to_float_or_none(p_dict[alias])
                    if parsed is not None:
                        found_val = parsed
                        break
            if found_val is not None:
                break
        extracted[canonical] = found_val

    return location, timestamp, extracted, context_meta


def _fetch_from_pipeline(location: str) -> Dict[str, Any]:
    """Retrieve AQI data from the existing pipeline or WAQI client without modifying them."""
    pipeline_mod = importlib.import_module("app.aqi_pipeline")
    if hasattr(pipeline_mod, "get_aqi_data") and callable(pipeline_mod.get_aqi_data):
        raw = pipeline_mod.get_aqi_data(location)
        if hasattr(pipeline_mod, "validate_aqi_data") and callable(pipeline_mod.validate_aqi_data):
            try:
                validated = pipeline_mod.validate_aqi_data(raw)
                return {
                    "location": location,
                    "raw_aqi": raw,
                    "validated_aqi": validated,
                }
            except Exception:
                return {"location": location, "raw_aqi": raw}
        return {"location": location, "aqi_data": raw}

    waqi_mod = importlib.import_module("app.waqi_client")
    if hasattr(waqi_mod, "get_aqi_data") and callable(waqi_mod.get_aqi_data):
        return {"location": location, "raw_aqi": waqi_mod.get_aqi_data(location)}

    raise RuntimeError("No callable get_aqi_data found in app.aqi_pipeline or app.waqi_client.")


def _fetch_historical_records(location: Optional[str]) -> List[Dict[str, Any]]:
    """Retrieve historical AQI records from app.history.database if available."""
    if not location:
        return []
    try:
        db_mod = importlib.import_module("app.history.database")
        get_hist_fn = getattr(db_mod, "get_aqi_history", None)
        if not callable(get_hist_fn):
            return []
        rows = get_hist_fn(location=location)
        if isinstance(rows, pd.DataFrame):
            records = rows.to_dict(orient="records")
            return [r for r in records if isinstance(r, dict)]
        if isinstance(rows, list):
            return [r for r in rows if isinstance(r, dict)]
        return []
    except Exception:
        return []


def identify_dominant_pollutant(
    pollutants: Dict[str, Optional[float]],
    historical_baselines: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Identify the dominant pollutant among available measurements.

    Uses relative ratio to historical baseline when available for a pollutant,
    and otherwise compares raw measured concentrations across available pollutants.
    Missing values are excluded and never treated as zero.
    """
    available: Dict[str, float] = {}
    missing: List[str] = []

    for pol in SUPPORTED_POLLUTANTS:
        val = _to_float_or_none(pollutants.get(pol) if isinstance(pollutants, dict) else None)
        if val is None:
            missing.append(pol)
        else:
            available[pol] = val

    if not available:
        return {
            "dominant_pollutant": None,
            "selection_basis": "none",
            "measured_value": None,
            "unit": None,
            "baseline_ratio": None,
            "available_pollutants": {},
            "missing_pollutants": missing,
            "note": "No valid pollutant measurements available to determine a dominant pollutant.",
        }

    baselines = historical_baselines or {}
    ratio_candidates: Dict[str, float] = {}
    for pol, val in available.items():
        base_val = _to_float_or_none(baselines.get(pol))
        if base_val is not None and base_val > 0:
            ratio_candidates[pol] = round(val / base_val, 3)

    if ratio_candidates:
        dominant = max(
            ratio_candidates.keys(),
            key=lambda p: (ratio_candidates[p], available[p]),
        )
        basis = "historical_baseline_ratio"
        ratio_val: Optional[float] = ratio_candidates[dominant]
    else:
        dominant = max(available.keys(), key=lambda p: available[p])
        basis = "highest_measured_concentration"
        ratio_val = None

    return {
        "dominant_pollutant": dominant,
        "selection_basis": basis,
        "measured_value": available[dominant],
        "unit": POLLUTANT_UNITS.get(dominant),
        "baseline_ratio": ratio_val,
        "available_pollutants": available,
        "missing_pollutants": missing,
    }


def compare_pollutant_baseline(
    pollutants: Dict[str, Optional[float]],
    historical_records: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Compare current available pollutants against historical baseline statistics.

    Does not invent baselines or thresholds; reports 'insufficient_baseline_data'
    when no valid historical values exist for a pollutant.
    """
    records = historical_records or []
    comparisons: Dict[str, Dict[str, Any]] = {}
    baselines_for_ratio: Dict[str, float] = {}
    elevated_pollutants: List[Dict[str, Any]] = []
    insufficient_baseline_for: List[str] = []

    for pol in SUPPORTED_POLLUTANTS:
        current_val = _to_float_or_none(pollutants.get(pol) if isinstance(pollutants, dict) else None)
        hist_vals: List[float] = []
        for rec in records:
            _, _, rec_pols, _ = _extract_pollutants_and_meta(rec)
            v = _to_float_or_none(rec_pols.get(pol))
            if v is not None:
                hist_vals.append(v)

        if not hist_vals:
            insufficient_baseline_for.append(pol)
            comparisons[pol] = {
                "current_value": current_val,
                "unit": POLLUTANT_UNITS.get(pol),
                "historical_sample_count": 0,
                "baseline_mean": None,
                "baseline_median": None,
                "ratio_to_mean": None,
                "status": "insufficient_baseline_data",
            }
            continue

        arr = np.asarray(hist_vals, dtype=float)
        baseline_mean = float(np.mean(arr))
        baseline_median = float(np.median(arr))
        baselines_for_ratio[pol] = baseline_mean

        if current_val is None:
            comparisons[pol] = {
                "current_value": None,
                "unit": POLLUTANT_UNITS.get(pol),
                "historical_sample_count": int(arr.size),
                "baseline_mean": round(baseline_mean, 3),
                "baseline_median": round(baseline_median, 3),
                "ratio_to_mean": None,
                "status": "current_value_missing",
            }
            continue

        ratio = (current_val / baseline_mean) if baseline_mean > 0 else None
        if ratio is not None and ratio >= HIGH_ELEVATION_RATIO_THRESHOLD:
            status = "markedly_elevated_vs_baseline"
        elif ratio is not None and ratio >= ELEVATION_RATIO_THRESHOLD:
            status = "elevated_vs_baseline"
        else:
            status = "within_or_below_baseline"

        entry = {
            "current_value": current_val,
            "unit": POLLUTANT_UNITS.get(pol),
            "historical_sample_count": int(arr.size),
            "baseline_mean": round(baseline_mean, 3),
            "baseline_median": round(baseline_median, 3),
            "ratio_to_mean": round(ratio, 3) if ratio is not None else None,
            "status": status,
        }
        comparisons[pol] = entry

        if status in ("elevated_vs_baseline", "markedly_elevated_vs_baseline"):
            elevated_pollutants.append(
                {
                    "pollutant": pol,
                    "current_value": current_val,
                    "baseline_mean": round(baseline_mean, 3),
                    "ratio_to_mean": round(ratio, 3) if ratio is not None else None,
                    "status": status,
                }
            )

    return {
        "comparisons": comparisons,
        "elevated_pollutants": elevated_pollutants,
        "baselines_mean": baselines_for_ratio,
        "insufficient_baseline_for": insufficient_baseline_for,
    }


def _detect_pollutant_patterns(
    available: Dict[str, float],
    elevated_names: List[str],
) -> List[Dict[str, Any]]:
    """Detect notable multi-pollutant combinations from available measurements."""
    patterns: List[Dict[str, Any]] = []
    present = set(available.keys())

    if {"PM25", "PM10"}.issubset(present):
        pm25 = available["PM25"]
        pm10 = available["PM10"]
        ratio_pm25_pm10 = (pm25 / pm10) if pm10 > 0 else None
        patterns.append(
            {
                "combination": ["PM25", "PM10"],
                "measured_values": {"PM25": pm25, "PM10": pm10},
                "pm25_to_pm10_ratio": round(ratio_pm25_pm10, 3) if ratio_pm25_pm10 is not None else None,
                "elevated_in_combination": [p for p in ("PM25", "PM10") if p in elevated_names],
                "observation": "Both fine (PM2.5) and coarse (PM10) particulate measurements are present.",
            }
        )

    if {"NO2", "CO"}.issubset(present):
        patterns.append(
            {
                "combination": ["NO2", "CO"],
                "measured_values": {"NO2": available["NO2"], "CO": available["CO"]},
                "elevated_in_combination": [p for p in ("NO2", "CO") if p in elevated_names],
                "observation": "Both NO2 and CO measurements are present together.",
            }
        )

    if {"SO2", "PM25"}.issubset(present):
        patterns.append(
            {
                "combination": ["SO2", "PM25"],
                "measured_values": {"SO2": available["SO2"], "PM25": available["PM25"]},
                "elevated_in_combination": [p for p in ("SO2", "PM25") if p in elevated_names],
                "observation": "Both SO2 and PM2.5 measurements are present together.",
            }
        )

    if {"NO2", "O3"}.issubset(present):
        patterns.append(
            {
                "combination": ["NO2", "O3"],
                "measured_values": {"NO2": available["NO2"], "O3": available["O3"]},
                "elevated_in_combination": [p for p in ("NO2", "O3") if p in elevated_names],
                "observation": "Both NO2 and O3 measurements are present together.",
            }
        )

    return patterns


def identify_possible_sources(
    pollutants: Dict[str, Optional[float]],
    baseline_comparison: Optional[Dict[str, Any]] = None,
    context_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate indicative, non-confirmed contributing source hypotheses.

    Strictly distinguishes measured pollutant facts from possible explanations
    and never claims an exact or confirmed source from AQI measurements alone.
    """
    available: Dict[str, float] = {}
    for pol in SUPPORTED_POLLUTANTS:
        val = _to_float_or_none(pollutants.get(pol) if isinstance(pollutants, dict) else None)
        if val is not None:
            available[pol] = val

    comp_map = (baseline_comparison or {}).get("comparisons") or {}
    elevated_names = [
        item["pollutant"]
        for item in ((baseline_comparison or {}).get("elevated_pollutants") or [])
        if isinstance(item, dict) and item.get("pollutant")
    ]
    patterns = _detect_pollutant_patterns(available, elevated_names)

    def _is_elevated(pol: str) -> bool:
        return pol in elevated_names or comp_map.get(pol, {}).get("status") in (
            "elevated_vs_baseline",
            "markedly_elevated_vs_baseline",
        )

    hypotheses: List[Dict[str, Any]] = []

    # 1. Traffic emissions (indicative when NO2 and/or CO are present/elevated)
    if "NO2" in available or "CO" in available:
        supporting_facts: List[str] = []
        evidence_points = 0
        if "NO2" in available:
            supporting_facts.append(f"Measured NO2 = {available['NO2']} {POLLUTANT_UNITS['NO2']}")
            evidence_points += 1
            if _is_elevated("NO2"):
                supporting_facts.append("NO2 is elevated relative to its historical baseline")
                evidence_points += 1
        if "CO" in available:
            supporting_facts.append(f"Measured CO = {available['CO']} {POLLUTANT_UNITS['CO']}")
            evidence_points += 1
            if _is_elevated("CO"):
                supporting_facts.append("CO is elevated relative to its historical baseline")
                evidence_points += 1

        confidence = "moderate" if evidence_points >= 3 else "low"
        hypotheses.append(
            {
                "source_category": "Traffic emissions",
                "status_label": "indicative_only_not_confirmed",
                "confidence_level": confidence,
                "measured_evidence": supporting_facts,
                "explanation": (
                    "Indicative only: NO2 and CO are commonly associated with motor vehicle "
                    "combustion, though other combustion sources or local dispersion conditions "
                    "cannot be ruled out from pollutant readings alone."
                ),
            }
        )

    # 2. Construction and road dust (indicative when PM10 and/or PM2.5 are present)
    if "PM10" in available or "PM25" in available:
        dust_facts: List[str] = []
        dust_points = 0
        if "PM10" in available:
            dust_facts.append(f"Measured PM10 = {available['PM10']} {POLLUTANT_UNITS['PM10']}")
            dust_points += 1
            if _is_elevated("PM10"):
                dust_facts.append("PM10 is elevated relative to its historical baseline")
                dust_points += 1
        if "PM25" in available:
            dust_facts.append(f"Measured PM2.5 = {available['PM25']} {POLLUTANT_UNITS['PM25']}")
            dust_points += 1

        confidence = "moderate" if dust_points >= 3 else "low"
        hypotheses.append(
            {
                "source_category": "Construction and road dust",
                "status_label": "indicative_only_not_confirmed",
                "confidence_level": confidence,
                "measured_evidence": dust_facts,
                "explanation": (
                    "Indicative only: Coarse particulate matter (PM10) alongside fine particles "
                    "can occur with construction activity or resuspended road dust, but does not "
                    "confirm site-specific dust sources without on-site or land-use verification."
                ),
            }
        )

    # 3. Industrial activity (indicative when SO2 and/or particulate/NO2 signals appear)
    if "SO2" in available:
        ind_facts = [f"Measured SO2 = {available['SO2']} {POLLUTANT_UNITS['SO2']}"]
        ind_points = 1
        if _is_elevated("SO2"):
            ind_facts.append("SO2 is elevated relative to its historical baseline")
            ind_points += 1
        if "PM25" in available:
            ind_facts.append(f"Measured PM2.5 = {available['PM25']} {POLLUTANT_UNITS['PM25']}")
            ind_points += 1

        confidence = "moderate" if ind_points >= 2 else "low"
        hypotheses.append(
            {
                "source_category": "Industrial activity",
                "status_label": "indicative_only_not_confirmed",
                "confidence_level": confidence,
                "measured_evidence": ind_facts,
                "explanation": (
                    "Indicative only: Sulfur dioxide (SO2) and particulate matter can coincide "
                    "with industrial processes or stationary point sources, but measurements alone "
                    "do not verify industrial emission attribution."
                ),
            }
        )

    # 4. Fuel combustion (indicative when PM2.5, CO, NO2, or SO2 are present)
    combustion_pols = [p for p in ("PM25", "CO", "NO2", "SO2") if p in available]
    if combustion_pols:
        comb_facts = [f"Measured {p} = {available[p]} {POLLUTANT_UNITS[p]}" for p in combustion_pols]
        elev_comb = [p for p in combustion_pols if _is_elevated(p)]
        if elev_comb:
            comb_facts.append(f"Elevated vs. baseline in combustion-related species: {', '.join(elev_comb)}")

        confidence = "moderate" if len(elev_comb) >= 2 else "low"
        hypotheses.append(
            {
                "source_category": "Fuel combustion",
                "status_label": "indicative_only_not_confirmed",
                "confidence_level": confidence,
                "measured_evidence": comb_facts,
                "explanation": (
                    "Indicative only: Fine particulates and combustion gases can arise from biomass, "
                    "coal, oil, or gas burning across multiple sectors; pollutant data cannot "
                    "confirm the specific fuel type or facility."
                ),
            }
        )

    # 5. Regional or transported pollution (indicative when PM2.5 and/or O3 are present)
    if "PM25" in available or "O3" in available:
        reg_facts: List[str] = []
        reg_points = 0
        if "PM25" in available:
            reg_facts.append(f"Measured PM2.5 = {available['PM25']} {POLLUTANT_UNITS['PM25']}")
            reg_points += 1
            if _is_elevated("PM25"):
                reg_facts.append("PM2.5 is elevated relative to its historical baseline")
                reg_points += 1
        if "O3" in available:
            reg_facts.append(f"Measured O3 = {available['O3']} {POLLUTANT_UNITS['O3']}")
            reg_points += 1
            if _is_elevated("O3"):
                reg_facts.append("O3 is elevated relative to its historical baseline")
                reg_points += 1

        confidence = "moderate" if reg_points >= 2 else "low"
        hypotheses.append(
            {
                "source_category": "Regional or transported pollution",
                "status_label": "indicative_only_not_confirmed",
                "confidence_level": confidence,
                "measured_evidence": reg_facts,
                "explanation": (
                    "Indicative only: Fine particulate matter (PM2.5) and ozone (O3) can reflect "
                    "regional background levels or secondary photochemical formation/transport, "
                    "which requires meteorological and trajectory data to evaluate further."
                ),
            }
        )

    # Include optional context note ONLY if actual data was supplied
    context_notes: List[str] = []
    if context_meta:
        for key, val in context_meta.items():
            if val is not None:
                context_notes.append(f"Provided {key}: {val}")

    if not available:
        overall_confidence = "none"
    elif any(h["confidence_level"] == "moderate" for h in hypotheses):
        overall_confidence = "moderate"
    else:
        overall_confidence = "low"

    return {
        "disclaimer": (
            "Possible contributing sources are indicative hypotheses only and are not "
            "confirmed by AQI or pollutant measurements alone."
        ),
        "overall_confidence_level": overall_confidence,
        "pollutant_patterns": patterns,
        "possible_sources": hypotheses,
        "context_provided": context_notes,
    }


def analyse_pollutants(
    aqi_payload: Optional[Dict[str, Any]] = None,
    *,
    location: Optional[str] = None,
    historical_records: Optional[List[Dict[str, Any]]] = None,
    fetch_if_missing: bool = True,
) -> Dict[str, Any]:
    """Analyse pollutant measurements from an AQI payload or the existing pipeline.

    Args:
        aqi_payload: Optional dictionary containing AQI/pollutant readings.
        location: Optional location name used to query pipeline/history when needed.
        historical_records: Optional list of historical reading dicts for baseline comparison.
        fetch_if_missing: When True and aqi_payload is None, queries the pipeline for location.
    """
    limitations: List[str] = []
    source_payload = aqi_payload

    if source_payload is None and fetch_if_missing:
        if not location or not location.strip():
            raise ValueError("Either 'aqi_payload' or a non-empty 'location' must be provided.")
        try:
            source_payload = _fetch_from_pipeline(location.strip())
        except Exception as exc:
            limitations.append(f"Pipeline retrieval failed: {exc}")
            source_payload = {"location": location.strip()}

    parsed_loc, parsed_ts, pollutants, context_meta = _extract_pollutants_and_meta(source_payload)
    resolved_location = (location.strip() if location and location.strip() else parsed_loc) or "Unknown"

    if parsed_ts is None:
        limitations.append("Observation timestamp is missing from the AQI reading.")

    missing_pollutants = [p for p in SUPPORTED_POLLUTANTS if pollutants.get(p) is None]
    available_pollutants = {p: pollutants[p] for p in SUPPORTED_POLLUTANTS if pollutants.get(p) is not None}

    if not available_pollutants:
        limitations.append("Insufficient pollutant data: no valid pollutant concentrations were available.")
    elif missing_pollutants:
        limitations.append(
            f"Partial pollutant coverage: missing {', '.join(missing_pollutants)} "
            "(missing values are not treated as zero)."
        )

    hist_rows = historical_records
    if hist_rows is None and resolved_location != "Unknown":
        hist_rows = _fetch_historical_records(resolved_location)

    baseline_result = compare_pollutant_baseline(pollutants, historical_records=hist_rows)
    if baseline_result["insufficient_baseline_for"]:
        limitations.append(
            "No historical baseline records available for: "
            + ", ".join(baseline_result["insufficient_baseline_for"])
            + "."
        )

    if not context_meta:
        limitations.append("No nearby land-use or meteorological data provided.")

    dominant_info = identify_dominant_pollutant(
        pollutants,
        historical_baselines=baseline_result.get("baselines_mean"),
    )
    source_analysis = identify_possible_sources(
        pollutants,
        baseline_comparison=baseline_result,
        context_meta=context_meta,
    )

    insufficient_data_warning: Optional[str] = None
    if not available_pollutants:
        insufficient_data_warning = (
            "Insufficient data: no valid pollutant measurements available to perform full pollutant analysis."
        )
    elif len(available_pollutants) < 2:
        insufficient_data_warning = (
            f"Limited data warning: only {len(available_pollutants)} pollutant "
            f"({', '.join(available_pollutants.keys())}) available; multi-pollutant pattern analysis is limited."
        )

    return {
        "location": resolved_location,
        "observation_timestamp": parsed_ts,
        "available_pollutants": available_pollutants,
        "missing_pollutants": missing_pollutants,
        "dominant_pollutant": dominant_info,
        "elevated_pollutants": baseline_result["elevated_pollutants"],
        "historical_comparison": baseline_result["comparisons"],
        "pollutant_patterns": source_analysis["pollutant_patterns"],
        "possible_sources": source_analysis["possible_sources"],
        "confidence_level": source_analysis["overall_confidence_level"],
        "insufficient_data_warning": insufficient_data_warning,
        "data_limitations": limitations,
    }


def generate_pollutant_report(
    aqi_payload: Optional[Dict[str, Any]] = None,
    *,
    location: Optional[str] = None,
    historical_records: Optional[List[Dict[str, Any]]] = None,
    fetch_if_missing: bool = True,
) -> Dict[str, Any]:
    """Build a structured pollutant analysis report plus a human-readable summary."""
    try:
        analysis = analyse_pollutants(
            aqi_payload=aqi_payload,
            location=location,
            historical_records=historical_records,
            fetch_if_missing=fetch_if_missing,
        )
    except Exception as exc:
        loc_label = (location or "Unknown").strip() or "Unknown"
        warning = f"Unable to complete pollutant analysis due to error: {exc}"
        return {
            "location": loc_label,
            "observation_timestamp": None,
            "available_pollutants": {},
            "dominant_pollutant": None,
            "elevated_pollutants": [],
            "historical_comparison": {},
            "possible_sources": [],
            "supporting_evidence": [],
            "confidence_level": "none",
            "data_limitations": [warning],
            "summary": f"Pollutant analysis for {loc_label} could not be completed. {warning}",
        }

    loc = analysis["location"]
    ts = analysis["observation_timestamp"] or "not recorded"
    avail = analysis["available_pollutants"]
    dom = analysis["dominant_pollutant"] or {}
    dom_pol = dom.get("dominant_pollutant")
    elevated = analysis["elevated_pollutants"]
    sources = analysis["possible_sources"]
    limitations = analysis["data_limitations"]
    warning = analysis["insufficient_data_warning"]

    evidence_items: List[Dict[str, Any]] = []
    for src in sources:
        evidence_items.append(
            {
                "source_category": src.get("source_category"),
                "confidence_level": src.get("confidence_level"),
                "measured_evidence": src.get("measured_evidence", []),
            }
        )

    summary_parts: List[str] = [
        f"Pollutant analysis for {loc} (observed: {ts})."
    ]

    if warning:
        summary_parts.append(warning)

    if avail:
        readings_str = ", ".join(
            f"{k}: {v} {POLLUTANT_UNITS.get(k, '')}".strip() for k, v in avail.items()
        )
        summary_parts.append(f"Available measurements: {readings_str}.")

    if dom_pol:
        summary_parts.append(
            f"Dominant pollutant (indicative comparison): {dom_pol} "
            f"({dom.get('measured_value')} {dom.get('unit') or ''}, basis: {dom.get('selection_basis')})."
        )
    else:
        summary_parts.append("No dominant pollutant could be identified due to missing measurements.")

    if elevated:
        elev_str = ", ".join(
            f"{e['pollutant']} ({e['ratio_to_mean']}x baseline)" for e in elevated
        )
        summary_parts.append(f"Elevated relative to historical baseline: {elev_str}.")
    else:
        summary_parts.append("No pollutants were identified as elevated above historical baselines.")

    if sources:
        src_names = ", ".join(
            f"{s['source_category']} [indicative, {s['confidence_level']} confidence]" for s in sources
        )
        summary_parts.append(
            f"Possible contributing sources (not confirmed by AQI alone): {src_names}."
        )

    if limitations:
        summary_parts.append(f"Limitations: {'; '.join(limitations)}")

    report: Dict[str, Any] = {
        "location": loc,
        "observation_timestamp": analysis["observation_timestamp"],
        "available_pollutants": avail,
        "dominant_pollutant": dom_pol,
        "dominant_pollutant_details": dom,
        "elevated_pollutants": elevated,
        "historical_comparison": analysis["historical_comparison"],
        "pollutant_patterns": analysis["pollutant_patterns"],
        "possible_sources": sources,
        "supporting_evidence": evidence_items,
        "confidence_level": analysis["confidence_level"],
        "data_limitations": limitations,
        "summary": " ".join(summary_parts),
    }
    return report