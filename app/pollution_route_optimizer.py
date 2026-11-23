"""Independent Intercity Pollution-Aware Route Planner Module.

Plans intercity journeys (e.g., 'Ahmedabad, Gujarat' -> 'Mumbai, Maharashtra')
across cities, districts, and states by geocoding city names, generating multiple
alternative road routes (car, motorcycle, and other provider-supported modes),
dividing each route into geographic segments, querying nearby monitoring
stations via the existing WAQI/AQI pipeline without inventing measurements, and
estimating segment-level and route-level pollution exposure with transparent
data coverage, freshness, and confidence reporting.
"""

from __future__ import annotations

import importlib
import math
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import requests

SUPPORTED_POLLUTANTS: Tuple[str, ...] = ("PM25", "PM10", "NO2", "SO2", "CO", "O3")

POLLUTANT_ALIASES: Dict[str, Tuple[str, ...]] = {
    "PM25": ("PM25", "pm25", "pm2_5", "PM2.5", "pm2.5"),
    "PM10": ("PM10", "pm10"),
    "NO2": ("NO2", "no2"),
    "SO2": ("SO2", "so2"),
    "CO": ("CO", "co"),
    "O3": ("O3", "o3"),
}

SUPPORTED_MODES: Tuple[str, ...] = ("car", "motorcycle", "walking", "cycling")
MODE_ALIASES: Dict[str, str] = {
    "car": "car",
    "driving": "car",
    "drive": "car",
    "motorcycle": "motorcycle",
    "motorbike": "motorcycle",
    "two_wheeler": "motorcycle",
    "bike": "cycling",
    "bicycle": "cycling",
    "cycling": "cycling",
    "walk": "walking",
    "walking": "walking",
}

SUPPORTED_PREFERENCES: Tuple[str, ...] = (
    "lowest_exposure",
    "fastest",
    "shortest",
    "balanced",
)

PREFERENCE_ALIASES: Dict[str, str] = {
    "lowest_exposure": "lowest_exposure",
    "lowest_estimated_exposure": "lowest_exposure",
    "lowest_estimated_pollution_exposure": "lowest_exposure",
    "fastest": "fastest",
    "fastest_route": "fastest",
    "shortest": "shortest",
    "shortest_route": "shortest",
    "balanced": "balanced",
    "balanced_route": "balanced",
}


@dataclass
class IntercityRouteConfig:
    """Configurable geocoding, routing, station search, and exposure parameters."""

    geocoding_provider: str = field(
        default_factory=lambda: os.getenv("GEOCODING_PROVIDER", "nominatim").strip().lower()
    )
    nominatim_base_url: str = field(
        default_factory=lambda: os.getenv(
            "NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org"
        ).rstrip("/")
    )
    geocoding_user_agent: str = field(
        default_factory=lambda: os.getenv(
            "GEOCODING_USER_AGENT", "EcoHealth-IntercityRoutePlanner/1.0"
        ).strip()
    )
    routing_provider: str = field(
        default_factory=lambda: os.getenv("ROUTE_PROVIDER", "osrm").strip().lower()
    )
    osrm_base_url: str = field(
        default_factory=lambda: os.getenv(
            "OSRM_BASE_URL", "https://router.project-osrm.org"
        ).rstrip("/")
    )
    graphhopper_base_url: str = field(
        default_factory=lambda: os.getenv(
            "GRAPHHOPPER_BASE_URL", "https://graphhopper.com/api/1"
        ).rstrip("/")
    )
    graphhopper_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("GRAPHHOPPER_API_KEY") or None
    )
    waqi_base_url: str = field(
        default_factory=lambda: os.getenv(
            "WAQI_BASE_URL", "https://api.waqi.info"
        ).rstrip("/")
    )
    waqi_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("WAQI_API_KEY") or os.getenv("WAQI_TOKEN") or None
    )
    request_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("ROUTE_API_TIMEOUT_SECONDS", "12.0"))
    )
    segment_length_km: float = 15.0
    max_station_distance_km: float = 35.0
    idw_power: float = 2.0
    max_fresh_hours: float = 6.0
    min_city_separation_km: float = 5.0
    # Balanced scoring weights
    balanced_exposure_weight: float = 0.50
    balanced_duration_weight: float = 0.25
    balanced_distance_weight: float = 0.25


DEFAULT_INTERCITY_CONFIG = IntercityRouteConfig()


def _to_float_or_none(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, dict):
        for k in ("v", "value", "val", "aqi", "concentration"):
            if k in value:
                return _to_float_or_none(value[k])
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return num if math.isfinite(num) else None


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
            dt = None  # type: ignore[assignment]
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(s, fmt)
                    break
                except ValueError:
                    continue
            if dt is None:
                return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _freshness_weight(ts_dt: Optional[datetime], max_fresh_hours: float) -> Tuple[float, str]:
    """Return freshness weight in [0.4, 1.0] and human-readable freshness label."""
    if ts_dt is None:
        return 0.65, "timestamp_unknown"
    age_hours = max(0.0, (datetime.now(timezone.utc) - ts_dt).total_seconds() / 3600.0)
    if age_hours <= max_fresh_hours:
        return 1.0, f"fresh ({age_hours:.1f}h old)"
    if age_hours <= max_fresh_hours * 4.0:
        return 0.75, f"aging ({age_hours:.1f}h old)"
    return 0.45, f"stale ({age_hours:.1f}h old)"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two WGS84 coordinates in kilometres."""
    r_earth = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    return 2.0 * r_earth * math.asin(min(1.0, math.sqrt(a)))


def validate_coordinates(lat: Any, lon: Any, label: str = "coordinate") -> Tuple[float, float]:
    if isinstance(lat, bool) or isinstance(lon, bool):
        raise ValueError(f"Invalid {label}: booleans are not valid coordinates.")
    lat_f = _to_float_or_none(lat)
    lon_f = _to_float_or_none(lon)
    if lat_f is None or lon_f is None:
        raise ValueError(f"Invalid {label}: latitude and longitude must be finite numbers.")
    if not (-90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0):
        raise ValueError(f"Invalid {label} ({lat_f}, {lon_f}): out of WGS84 bounds.")
    return (lat_f, lon_f)


def _normalize_mode(mode: str) -> str:
    key = (mode or "car").strip().lower().replace("-", "_").replace(" ", "_")
    norm = MODE_ALIASES.get(key)
    if not norm:
        raise ValueError(f"Unsupported transport mode '{mode}'. Supported: {SUPPORTED_MODES}.")
    return norm


def _normalize_preference(preference: str) -> str:
    key = (preference or "balanced").strip().lower().replace("-", "_").replace(" ", "_")
    norm = PREFERENCE_ALIASES.get(key)
    if not norm:
        raise ValueError(f"Unsupported preference '{preference}'. Supported: {SUPPORTED_PREFERENCES}.")
    return norm


def _extract_highways_and_cities(
    waypoints: Sequence[str],
    nearby_station_names: Optional[Sequence[str]] = None,
) -> Tuple[List[str], List[str]]:
    """Separate highway identifiers/names (e.g., NH 48, NE 1) from city/locality names."""
    highways: List[str] = []
    cities: List[str] = []

    for item in waypoints:
        if not isinstance(item, str) or not item.strip():
            continue
        text = item.strip()
        upper = text.upper()
        is_highway = (
            upper.startswith(("NH", "SH", "NE", "AH", "EXPRESSWAY", "HIGHWAY"))
            or "HIGHWAY" in upper
            or "EXPRESSWAY" in upper
            or any(token.startswith(("NH-", "NH", "SH-", "NE-")) for token in upper.split())
        )
        if is_highway:
            if text not in highways:
                highways.append(text)
        else:
            if text not in cities:
                cities.append(text)

    for st_name in nearby_station_names or []:
        if isinstance(st_name, str) and st_name.strip() and st_name.strip() not in cities:
            cities.append(st_name.strip())

    return highways, cities


def _load_app_config_values(config: IntercityRouteConfig) -> IntercityRouteConfig:
    """Reuse existing app.config settings when available without mutating global state."""
    try:
        cfg_mod = importlib.import_module("app.config")
        if not config.waqi_api_key:
            for attr in ("WAQI_API_KEY", "WAQI_TOKEN"):
                val = getattr(cfg_mod, attr, None)
                if isinstance(val, str) and val.strip():
                    config.waqi_api_key = val.strip()
                    break
    except Exception:
        pass
    return config


def geocode_city(
    city_name: str,
    *,
    known_cities: Optional[Dict[str, Dict[str, Any]]] = None,
    config: IntercityRouteConfig = DEFAULT_INTERCITY_CONFIG,
) -> Dict[str, Any]:
    """Convert a city/district/state query (e.g., 'Ahmedabad, Gujarat') into coordinates.

    Checks caller-supplied `known_cities` first, then queries OpenStreetMap Nominatim
    (or GraphHopper Geocode if configured) without inventing coordinates.
    """
    if not isinstance(city_name, str) or not city_name.strip():
        raise ValueError("City name must be a non-empty string.")
    query = city_name.strip()

    if isinstance(known_cities, dict):
        for k, meta in known_cities.items():
            if k.strip().lower() == query.lower() and isinstance(meta, dict):
                lat, lon = validate_coordinates(meta.get("lat"), meta.get("lon"), f"city '{query}'")
                return {
                    "query": query,
                    "display_name": str(meta.get("display_name") or query),
                    "lat": lat,
                    "lon": lon,
                    "state": meta.get("state"),
                    "district": meta.get("district"),
                    "country": meta.get("country"),
                    "provider": "supplied_registry",
                }

    prov = (config.geocoding_provider or "nominatim").strip().lower()
    if prov == "graphhopper":
        if not config.graphhopper_api_key:
            raise ValueError("GRAPHHOPPER_API_KEY is required when GEOCODING_PROVIDER=graphhopper.")
        url = f"{config.graphhopper_base_url}/geocode"
        params = {"q": query, "limit": 1, "key": config.graphhopper_api_key}
        try:
            resp = requests.get(url, params=params, timeout=config.request_timeout_seconds)
            resp.raise_for_status()
            hits = (resp.json() or {}).get("hits") or []
            if not hits:
                raise LookupError(f"Geocoding returned no results for '{query}'.")
            hit = hits[0]
            pt = hit.get("point") or {}
            lat, lon = validate_coordinates(pt.get("lat"), pt.get("lng"), query)
            return {
                "query": query,
                "display_name": str(hit.get("name") or query),
                "lat": lat,
                "lon": lon,
                "state": hit.get("state"),
                "district": hit.get("county"),
                "country": hit.get("country"),
                "provider": "graphhopper_geocode",
            }
        except requests.Timeout as exc:
            raise TimeoutError(f"Geocoding timed out for '{query}'.") from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"Geocoding request failed for '{query}': {exc}") from exc

    # Default: OpenStreetMap Nominatim
    url = f"{config.nominatim_base_url}/search"
    params = {"q": query, "format": "jsonv2", "addressdetails": 1, "limit": 1}
    headers = {"User-Agent": config.geocoding_user_agent}
    try:
        resp = requests.get(
            url, params=params, headers=headers, timeout=config.request_timeout_seconds
        )
        resp.raise_for_status()
        results = resp.json()
        if not isinstance(results, list) or not results:
            raise LookupError(f"OpenStreetMap Nominatim could not geocode '{query}'.")
        top = results[0]
        lat, lon = validate_coordinates(top.get("lat"), top.get("lon"), query)
        addr = top.get("address") or {}
        return {
            "query": query,
            "display_name": str(top.get("display_name") or query),
            "lat": lat,
            "lon": lon,
            "state": addr.get("state"),
            "district": addr.get("state_district") or addr.get("county"),
            "country": addr.get("country"),
            "provider": "osm_nominatim",
        }
    except requests.Timeout as exc:
        raise TimeoutError(f"Nominatim geocoding timed out for '{query}'.") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"Nominatim geocoding failed for '{query}': {exc}") from exc


def _validate_intercity_endpoints(
    source_geo: Dict[str, Any],
    dest_geo: Dict[str, Any],
    min_separation_km: float,
) -> float:
    """Ensure source and destination represent distinct intercity endpoints."""
    src_name = str(source_geo.get("query") or source_geo.get("display_name") or "").strip().lower()
    dst_name = str(dest_geo.get("query") or dest_geo.get("display_name") or "").strip().lower()
    if src_name and dst_name and src_name == dst_name:
        raise ValueError("Source city and destination city must be different.")

    dist_km = haversine_km(
        float(source_geo["lat"]),
        float(source_geo["lon"]),
        float(dest_geo["lat"]),
        float(dest_geo["lon"]),
    )
    if dist_km < min_separation_km:
        raise ValueError(
            f"Source and destination are only {dist_km:.2f} km apart; intercity routing requires distinct cities (>= {min_separation_km} km)."
        )
    return round(dist_km, 2)


def _fetch_osrm_intercity_routes(
    source_geo: Dict[str, Any],
    dest_geo: Dict[str, Any],
    mode: str,
    config: IntercityRouteConfig,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Query OSRM for multiple intercity road routes."""
    warnings: List[str] = []
    if mode == "motorcycle":
        # Public OSRM exposes 'driving' (car) profile; note motorcycle approximation transparently
        profile_candidates = ["motorcycle", "driving", "car"]
        warnings.append(
            "OSRM road profile used for motorcycle routing; dedicated motorcycle-only lane restrictions depend on routing server profile."
        )
    elif mode == "car":
        profile_candidates = ["driving", "car"]
    elif mode == "cycling":
        profile_candidates = ["cycling", "bike"]
    else:
        profile_candidates = ["walking", "foot"]

    coords_path = f"{source_geo['lon']},{source_geo['lat']};{dest_geo['lon']},{dest_geo['lat']}"
    last_err: Optional[Exception] = None

    for profile in profile_candidates:
        url = f"{config.osrm_base_url}/route/v1/{profile}/{coords_path}"
        params = {
            "alternatives": "true",
            "steps": "true",
            "overview": "full",
            "geometries": "geojson",
        }
        try:
            resp = requests.get(url, params=params, timeout=config.request_timeout_seconds)
            if resp.status_code == 400:
                last_err = RuntimeError(f"OSRM profile '{profile}' unavailable.")
                continue
            resp.raise_for_status()
            payload = resp.json()
            if payload.get("code") != "Ok":
                last_err = RuntimeError(f"OSRM status: {payload.get('code')}")
                continue

            raw_routes = payload.get("routes") or []
            if not raw_routes:
                raise RuntimeError("Routing service returned no routes between these cities.")

            routes: List[Dict[str, Any]] = []
            for idx, r in enumerate(raw_routes):
                raw_coords = (r.get("geometry") or {}).get("coordinates") or []
                latlon = [
                    (float(pt[1]), float(pt[0]))
                    for pt in raw_coords
                    if isinstance(pt, (list, tuple)) and len(pt) >= 2
                ]
                waypoints: List[str] = []
                for leg in r.get("legs") or []:
                    summary = leg.get("summary")
                    if isinstance(summary, str) and summary.strip():
                        waypoints.append(summary.strip())
                    for step in leg.get("steps") or []:
                        ref = step.get("ref")
                        road_name = step.get("name")
                        label = ""
                        if isinstance(ref, str) and ref.strip() and isinstance(road_name, str) and road_name.strip():
                            label = f"{ref.strip()} ({road_name.strip()})"
                        elif isinstance(ref, str) and ref.strip():
                            label = ref.strip()
                        elif isinstance(road_name, str) and road_name.strip():
                            label = road_name.strip()
                        if label and label not in waypoints and len(waypoints) < 12:
                            waypoints.append(label)

                routes.append(
                    {
                        "route_id": f"intercity_route_{idx + 1}",
                        "route_label": f"Route {idx + 1}" + (f" via {waypoints[0]}" if waypoints else ""),
                        "provider": "osrm",
                        "profile_used": profile,
                        "transport_mode": mode,
                        "waypoints": waypoints,
                        "distance_km": round(float(r.get("distance", 0.0)) / 1000.0, 2),
                        "duration_minutes": round(float(r.get("duration", 0.0)) / 60.0, 1),
                        "geometry": {
                            "type": "LineString",
                            "coordinates_latlon": latlon,
                            "coordinates_lonlat": [[c[1], c[0]] for c in latlon],
                        },
                    }
                )
            return routes, warnings
        except requests.Timeout as exc:
            raise TimeoutError(f"OSRM routing timed out after {config.request_timeout_seconds}s.") from exc
        except requests.RequestException as exc:
            last_err = exc

    raise RuntimeError(f"Failed to generate intercity routes via OSRM: {last_err}") from last_err


def _fetch_graphhopper_intercity_routes(
    source_geo: Dict[str, Any],
    dest_geo: Dict[str, Any],
    mode: str,
    config: IntercityRouteConfig,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Query GraphHopper for alternative intercity routes (car, motorcycle, bike, foot)."""
    if not config.graphhopper_api_key:
        raise ValueError("GRAPHHOPPER_API_KEY is not set in environment variables.")

    gh_profile_map = {
        "car": "car",
        "motorcycle": "motorcycle",
        "cycling": "bike",
        "walking": "foot",
    }
    profile = gh_profile_map[mode]
    url = f"{config.graphhopper_base_url}/route"
    params: List[Tuple[str, Any]] = [
        ("point", f"{source_geo['lat']},{source_geo['lon']}"),
        ("point", f"{dest_geo['lat']},{dest_geo['lon']}"),
        ("profile", profile),
        ("alternative_route.max_paths", 3),
        ("points_encoded", "false"),
        ("key", config.graphhopper_api_key),
    ]
    try:
        resp = requests.get(url, params=params, timeout=config.request_timeout_seconds)
        resp.raise_for_status()
        paths = (resp.json() or {}).get("paths") or []
        if not paths:
            raise RuntimeError("GraphHopper returned zero intercity routes.")

        routes: List[Dict[str, Any]] = []
        for idx, p in enumerate(paths):
            pts = (p.get("points") or {}).get("coordinates") or []
            latlon = [
                (float(pt[1]), float(pt[0]))
                for pt in pts
                if isinstance(pt, (list, tuple)) and len(pt) >= 2
            ]
            waypoints: List[str] = []
            for instr in p.get("instructions") or []:
                street = instr.get("street_name")
                if isinstance(street, str) and street.strip() and street.strip() not in waypoints and len(waypoints) < 8:
                    waypoints.append(street.strip())

            routes.append(
                {
                    "route_id": f"intercity_route_{idx + 1}",
                    "route_label": f"Route {idx + 1}" + (f" via {waypoints[0]}" if waypoints else ""),
                    "provider": "graphhopper",
                    "profile_used": profile,
                    "transport_mode": mode,
                    "waypoints": waypoints,
                    "distance_km": round(float(p.get("distance", 0.0)) / 1000.0, 2),
                    "duration_minutes": round(float(p.get("time", 0.0)) / 60000.0, 1),
                    "geometry": {
                        "type": "LineString",
                        "coordinates_latlon": latlon,
                        "coordinates_lonlat": [[c[1], c[0]] for c in latlon],
                    },
                }
            )
        return routes, []
    except requests.Timeout as exc:
        raise TimeoutError(f"GraphHopper routing timed out after {config.request_timeout_seconds}s.") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"GraphHopper routing failed: {exc}") from exc


def generate_intercity_routes(
    source_city: str,
    destination_city: str,
    *,
    mode: str = "car",
    known_cities: Optional[Dict[str, Dict[str, Any]]] = None,
    provider_routes: Optional[Sequence[Dict[str, Any]]] = None,
    config: IntercityRouteConfig = DEFAULT_INTERCITY_CONFIG,
) -> Dict[str, Any]:
    """Geocode source/destination cities, verify they differ, and generate alternative road routes."""
    norm_mode = _normalize_mode(mode)
    src_geo = geocode_city(source_city, known_cities=known_cities, config=config)
    dst_geo = geocode_city(destination_city, known_cities=known_cities, config=config)
    straight_km = _validate_intercity_endpoints(src_geo, dst_geo, config.min_city_separation_km)

    warnings: List[str] = []
    if provider_routes is not None:
        routes: List[Dict[str, Any]] = []
        for idx, r in enumerate(provider_routes):
            if not isinstance(r, dict):
                continue
            geom = r.get("geometry") or {}
            raw_pts = geom.get("coordinates_latlon") or r.get("coordinates_latlon") or []
            latlon = [
                validate_coordinates(pt[0], pt[1], "route point")
                for pt in raw_pts
                if isinstance(pt, (list, tuple)) and len(pt) >= 2
            ]
            if not latlon:
                latlon = [(src_geo["lat"], src_geo["lon"]), (dst_geo["lat"], dst_geo["lon"])]
            dist_km = _to_float_or_none(r.get("distance_km"))
            if dist_km is None:
                dist_km = sum(
                    haversine_km(latlon[i][0], latlon[i][1], latlon[i + 1][0], latlon[i + 1][1])
                    for i in range(len(latlon) - 1)
                )
            dur_min = _to_float_or_none(r.get("duration_minutes"))
            if dur_min is None:
                speed = {"car": 60.0, "motorcycle": 55.0, "cycling": 18.0, "walking": 5.0}[norm_mode]
                dur_min = (dist_km / speed) * 60.0

            routes.append(
                {
                    "route_id": str(r.get("route_id") or f"intercity_route_{idx + 1}"),
                    "route_label": str(r.get("route_label") or f"Route {idx + 1}"),
                    "provider": str(r.get("provider") or "supplied"),
                    "profile_used": norm_mode,
                    "transport_mode": norm_mode,
                    "waypoints": list(r.get("waypoints") or []),
                    "distance_km": round(float(dist_km), 2),
                    "duration_minutes": round(float(dur_min), 1),
                    "geometry": {
                        "type": "LineString",
                        "coordinates_latlon": latlon,
                        "coordinates_lonlat": [[c[1], c[0]] for c in latlon],
                    },
                }
            )
        if not routes:
            raise ValueError("No valid intercity routes supplied.")
    else:
        prov = (config.routing_provider or "osrm").strip().lower()
        if prov == "graphhopper":
            routes, warnings = _fetch_graphhopper_intercity_routes(src_geo, dst_geo, norm_mode, config)
        elif prov == "osrm":
            routes, warnings = _fetch_osrm_intercity_routes(src_geo, dst_geo, norm_mode, config)
        else:
            raise ValueError(f"Unsupported routing provider '{config.routing_provider}'.")

    if len(routes) == 1:
        warnings.append("Routing provider returned only 1 route; no alternative corridor was available.")

    return {
        "source_city": src_geo,
        "destination_city": dst_geo,
        "straight_line_distance_km": straight_km,
        "transport_mode": norm_mode,
        "route_count": len(routes),
        "routes": routes,
        "warnings": warnings,
    }


def divide_route_into_segments(
    route: Dict[str, Any],
    *,
    segment_length_km: float = 15.0,
) -> List[Dict[str, Any]]:
    """Split an intercity route polyline into geographic segments of ~segment_length_km."""
    geom = route.get("geometry") or {}
    coords: List[Tuple[float, float]] = [
        (float(pt[0]), float(pt[1]))
        for pt in (geom.get("coordinates_latlon") or [])
        if isinstance(pt, (list, tuple)) and len(pt) >= 2
    ]
    if len(coords) < 2:
        return []

    total_dist = float(route.get("distance_km") or 0.0)
    total_dur = float(route.get("duration_minutes") or 0.0)
    target_km = max(1.0, float(segment_length_km))

    # Densify polyline at target_km intervals so long highway legs are properly subdivided
    waypoints: List[Tuple[float, float]] = [coords[0]]
    accum = 0.0
    for i in range(len(coords) - 1):
        lat1, lon1 = coords[i]
        lat2, lon2 = coords[i + 1]
        leg_km = haversine_km(lat1, lon1, lat2, lon2)
        if leg_km <= 1e-9:
            continue
        rem = leg_km
        clat, clon = lat1, lon1
        while accum + rem >= target_km:
            need = target_km - accum
            frac = need / rem
            clat = clat + frac * (lat2 - clat)
            clon = clon + frac * (lon2 - clon)
            waypoints.append((clat, clon))
            rem = haversine_km(clat, clon, lat2, lon2)
            accum = 0.0
            if rem <= 1e-9:
                break
        accum += rem
    if waypoints[-1] != coords[-1]:
        waypoints.append(coords[-1])

    raw_lengths = [
        haversine_km(waypoints[i][0], waypoints[i][1], waypoints[i + 1][0], waypoints[i + 1][1])
        for i in range(len(waypoints) - 1)
    ]
    geom_sum = sum(raw_lengths) or 1.0
    scale_dist = (total_dist / geom_sum) if total_dist > 0 else 1.0

    segments: List[Dict[str, Any]] = []
    for idx in range(len(waypoints) - 1):
        lat_a, lon_a = waypoints[idx]
        lat_b, lon_b = waypoints[idx + 1]
        seg_km = round(raw_lengths[idx] * scale_dist, 2)
        dur_share = (
            round(total_dur * (seg_km / total_dist), 2)
            if total_dist > 0 and total_dur > 0
            else round((seg_km / 55.0) * 60.0, 2)
        )
        segments.append(
            {
                "segment_id": f"{route.get('route_id', 'route')}_seg_{idx + 1}",
                "segment_index": idx + 1,
                "start": {"lat": round(lat_a, 5), "lon": round(lon_a, 5)},
                "end": {"lat": round(lat_b, 5), "lon": round(lon_b, 5)},
                "midpoint": {
                    "lat": round((lat_a + lat_b) / 2.0, 5),
                    "lon": round((lon_a + lon_b) / 2.0, 5),
                },
                "length_km": seg_km,
                "estimated_duration_minutes": dur_share,
            }
        )
    return segments


def _normalize_station_record(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse real station coordinates, AQI, and individual pollutant measurements."""
    if not isinstance(raw, dict):
        return None
    lat = _to_float_or_none(raw.get("lat") if "lat" in raw else raw.get("latitude"))
    lon = _to_float_or_none(raw.get("lon") if "lon" in raw else raw.get("longitude"))
    if lat is None or lon is None:
        geo = raw.get("geo")
        if isinstance(geo, (list, tuple)) and len(geo) >= 2:
            lat = _to_float_or_none(geo[0])
            lon = _to_float_or_none(geo[1])
    if lat is None or lon is None or not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None

    pollutants: Dict[str, Optional[float]] = {p: None for p in SUPPORTED_POLLUTANTS}
    containers = [raw]
    if isinstance(raw.get("pollutants"), dict):
        containers.insert(0, raw["pollutants"])
    if isinstance(raw.get("iaqi"), dict):
        containers.insert(0, raw["iaqi"])

    for pol, aliases in POLLUTANT_ALIASES.items():
        for c in containers:
            for alias in aliases:
                if alias in c:
                    val = _to_float_or_none(c[alias])
                    if val is not None:
                        pollutants[pol] = val
                        break
            if pollutants[pol] is not None:
                break

    aqi_val = _to_float_or_none(raw.get("aqi") if "aqi" in raw else raw.get("overall_aqi"))
    if aqi_val is None and all(v is None for v in pollutants.values()):
        return None

    ts_raw = raw.get("timestamp") or raw.get("last_updated") or raw.get("time")
    ts_dt = _parse_timestamp_or_none(ts_raw)
    name = (
        raw.get("station")
        or raw.get("station_name")
        or raw.get("name")
        or raw.get("location")
        or f"Station ({lat:.3f}, {lon:.3f})"
    )
    return {
        "station_name": str(name),
        "lat": lat,
        "lon": lon,
        "aqi": aqi_val,
        "pollutants": pollutants,
        "timestamp": ts_raw,
        "ts_dt": ts_dt,
    }


def _fetch_waqi_bounds_stations(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    config: IntercityRouteConfig,
) -> List[Dict[str, Any]]:
    """Query WAQI map/bounds feed along the intercity corridor when WAQI_API_KEY is configured."""
    cfg = _load_app_config_values(config)
    if not cfg.waqi_api_key:
        return []
    url = f"{cfg.waqi_base_url}/map/bounds/"
    params = {
        "latlng": f"{min_lat},{min_lon},{max_lat},{max_lon}",
        "token": cfg.waqi_api_key,
    }
    try:
        resp = requests.get(url, params=params, timeout=cfg.request_timeout_seconds)
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("status") != "ok":
            return []
        stations: List[Dict[str, Any]] = []
        for item in payload.get("data") or []:
            if not isinstance(item, dict):
                continue
            station_meta = item.get("station") or {}
            parsed = _normalize_station_record(
                {
                    "station_name": station_meta.get("name"),
                    "lat": item.get("lat"),
                    "lon": item.get("lon"),
                    "aqi": item.get("aqi"),
                    "timestamp": station_meta.get("time"),
                }
            )
            if parsed is not None:
                stations.append(parsed)
        return stations
    except Exception:
        return []


def find_nearby_aqi_stations(
    segment: Dict[str, Any],
    stations: Sequence[Dict[str, Any]],
    *,
    max_distance_km: float = 35.0,
) -> List[Dict[str, Any]]:
    """Find monitoring stations within max_distance_km of a route segment midpoint."""
    mid = segment.get("midpoint") or {}
    m_lat = _to_float_or_none(mid.get("lat"))
    m_lon = _to_float_or_none(mid.get("lon"))
    if m_lat is None or m_lon is None:
        return []

    nearby: List[Dict[str, Any]] = []
    for st in stations:
        norm = st if "station_name" in st and "ts_dt" in st else _normalize_station_record(st)
        if norm is None:
            continue
        dist_km = haversine_km(m_lat, m_lon, norm["lat"], norm["lon"])
        if dist_km <= max_distance_km:
            entry = dict(norm)
            entry["distance_km"] = round(dist_km, 2)
            nearby.append(entry)

    nearby.sort(key=lambda x: float(x["distance_km"]))
    return nearby


def retrieve_segment_pollution_data(
    segment: Dict[str, Any],
    stations: Sequence[Dict[str, Any]],
    *,
    config: IntercityRouteConfig = DEFAULT_INTERCITY_CONFIG,
) -> Dict[str, Any]:
    """Associate available station observations with a route segment via IDW interpolation.

    Clearly distinguishes measured station values, IDW-interpolated estimates,
    and missing pollutant species without treating missing values as zero.
    """
    nearby = find_nearby_aqi_stations(
        segment, stations, max_distance_km=config.max_station_distance_km
    )
    if not nearby:
        return {
            "segment_id": segment.get("segment_id"),
            "has_adequate_coverage": False,
            "nearby_station_count": 0,
            "nearest_station_km": None,
            "nearest_station_name": None,
            "data_source_type": "missing_data",
            "freshness_status": "no_station_data",
            "freshness_weight": 0.0,
            "estimated_aqi": None,
            "estimated_pollutants": {p: None for p in SUPPORTED_POLLUTANTS},
            "measured_stations": [],
            "limitation": f"No monitoring station within {config.max_station_distance_km} km of this segment.",
        }

    nearest = nearby[0]
    nearest_km = float(nearest["distance_km"])

    # Compute distance + freshness weights
    weights: List[float] = []
    fresh_weights: List[float] = []
    fresh_labels: List[str] = []
    for st in nearby:
        fw, flabel = _freshness_weight(st.get("ts_dt"), config.max_fresh_hours)
        dist_w = 1.0 / (max(float(st["distance_km"]), 0.25) ** config.idw_power)
        weights.append(dist_w * fw)
        fresh_weights.append(fw)
        fresh_labels.append(flabel)

    def _weighted_estimate(values_and_weights: List[Tuple[float, float]]) -> Optional[float]:
        if not values_and_weights:
            return None
        w_sum = sum(w for _, w in values_and_weights)
        if w_sum <= 0:
            return None
        return round(sum(v * w for v, w in values_and_weights) / w_sum, 2)

    aqi_pairs = [
        (float(st["aqi"]), w)
        for st, w in zip(nearby, weights)
        if st.get("aqi") is not None
    ]
    est_aqi = _weighted_estimate(aqi_pairs)

    est_pollutants: Dict[str, Optional[float]] = {}
    for pol in SUPPORTED_POLLUTANTS:
        pairs = [
            (float(st["pollutants"][pol]), w)
            for st, w in zip(nearby, weights)
            if isinstance(st.get("pollutants"), dict) and st["pollutants"].get(pol) is not None
        ]
        est_pollutants[pol] = _weighted_estimate(pairs)

    source_type = (
        "near_station_reading"
        if nearest_km <= 1.0
        else "interpolated_idw_estimate"
    )

    return {
        "segment_id": segment.get("segment_id"),
        "has_adequate_coverage": True,
        "nearby_station_count": len(nearby),
        "nearest_station_km": nearest_km,
        "nearest_station_name": nearest["station_name"],
        "data_source_type": source_type,
        "freshness_status": fresh_labels[0],
        "freshness_weight": round(float(np.mean(fresh_weights)), 3),
        "estimated_aqi": est_aqi,
        "estimated_pollutants": est_pollutants,
        "measured_stations": [
            {
                "station_name": st["station_name"],
                "distance_km": st["distance_km"],
                "aqi": st["aqi"],
                "pollutants": {
                    k: v for k, v in (st.get("pollutants") or {}).items() if v is not None
                },
                "timestamp": st.get("timestamp"),
            }
            for st in nearby[:3]
        ],
        "limitation": None,
    }


def estimate_segment_exposure(
    segment: Dict[str, Any],
    segment_pollution: Dict[str, Any],
    *,
    config: IntercityRouteConfig = DEFAULT_INTERCITY_CONFIG,
) -> Dict[str, Any]:
    """Estimate pollution exposure for a single segment using concentration, length, duration, proximity, and freshness."""
    seg_km = float(segment.get("length_km") or 0.0)
    seg_min = float(segment.get("estimated_duration_minutes") or 0.0)
    hours = max(seg_min / 60.0, 0.01)

    if not segment_pollution.get("has_adequate_coverage"):
        return {
            **segment,
            "pollution": segment_pollution,
            "estimated_segment_exposure": None,
            "exposure_band": "insufficient_data",
            "is_interpolated": False,
        }

    est_aqi = _to_float_or_none(segment_pollution.get("estimated_aqi"))
    pols = segment_pollution.get("estimated_pollutants") or {}
    pm25 = _to_float_or_none(pols.get("PM25"))
    pm10 = _to_float_or_none(pols.get("PM10"))

    # Use available concentration index without inventing missing species
    if est_aqi is not None:
        intensity = est_aqi
    elif pm25 is not None:
        intensity = pm25 * 1.5
    elif pm10 is not None:
        intensity = pm10 * 0.9
    else:
        available_vals = [float(v) for v in pols.values() if _to_float_or_none(v) is not None]
        intensity = float(np.mean(available_vals)) if available_vals else None

    if intensity is None:
        return {
            **segment,
            "pollution": segment_pollution,
            "estimated_segment_exposure": None,
            "exposure_band": "insufficient_data",
            "is_interpolated": True,
        }

    # Combine concentration intensity with travel duration (hours) and distance weighting
    # Adjusted gently by proximity confidence so distant stations are not over-trusted
    nearest_km = float(segment_pollution.get("nearest_station_km") or config.max_station_distance_km)
    proximity_factor = max(0.75, 1.0 - 0.25 * min(1.0, nearest_km / config.max_station_distance_km))
    raw_exposure = intensity * hours * (1.0 + seg_km / 100.0) * proximity_factor
    est_exp = round(raw_exposure, 2)

    if intensity >= 150:
        band = "high"
    elif intensity >= 80:
        band = "moderate"
    else:
        band = "low"

    return {
        **segment,
        "pollution": segment_pollution,
        "estimated_segment_exposure": est_exp,
        "concentration_index_used": round(intensity, 2),
        "exposure_band": band,
        "is_interpolated": segment_pollution.get("data_source_type") != "near_station_reading",
    }


def calculate_total_route_exposure(
    route: Dict[str, Any],
    stations: Sequence[Dict[str, Any]],
    *,
    config: IntercityRouteConfig = DEFAULT_INTERCITY_CONFIG,
) -> Dict[str, Any]:
    """Aggregate segment-level exposure, pollutant breakdown, coverage %, freshness, and confidence."""
    segments = divide_route_into_segments(route, segment_length_km=config.segment_length_km)
    if not segments:
        return {
            "route_id": route.get("route_id"),
            "estimated_exposure_score": None,
            "pollutant_breakdown": {p: None for p in SUPPORTED_POLLUTANTS},
            "high_exposure_segments": [],
            "low_exposure_segments": [],
            "data_coverage_percentage": 0.0,
            "data_freshness": "unavailable",
            "confidence_level": "low",
            "segments": [],
            "limitations": ["Route geometry had insufficient waypoints for segment exposure analysis."],
        }

    evaluated_segments: List[Dict[str, Any]] = []
    covered_km = 0.0
    total_km = sum(float(s.get("length_km") or 0.0) for s in segments) or 1.0
    exp_sum = 0.0
    covered_seg_count = 0
    freshness_weights: List[float] = []
    freshness_labels: List[str] = []
    pol_series: Dict[str, List[float]] = {p: [] for p in SUPPORTED_POLLUTANTS}

    for seg in segments:
        pol_info = retrieve_segment_pollution_data(seg, stations, config=config)
        seg_est = estimate_segment_exposure(seg, pol_info, config=config)
        evaluated_segments.append(seg_est)

        if seg_est.get("estimated_segment_exposure") is not None:
            covered_seg_count += 1
            covered_km += float(seg.get("length_km") or 0.0)
            exp_sum += float(seg_est["estimated_segment_exposure"])
            freshness_weights.append(float(pol_info.get("freshness_weight") or 0.65))
            freshness_labels.append(str(pol_info.get("freshness_status") or "unknown"))
            est_pols = pol_info.get("estimated_pollutants") or {}
            for p in SUPPORTED_POLLUTANTS:
                v = _to_float_or_none(est_pols.get(p))
                if v is not None:
                    pol_series[p].append(v)

    coverage_pct = round((covered_km / total_km) * 100.0, 1)
    pollutant_breakdown = {
        p: (round(float(np.mean(pol_series[p])), 2) if pol_series[p] else None)
        for p in SUPPORTED_POLLUTANTS
    }

    high_segments = [
        {
            "segment_id": s["segment_id"],
            "midpoint": s["midpoint"],
            "length_km": s["length_km"],
            "estimated_segment_exposure": s["estimated_segment_exposure"],
            "nearest_station": (s.get("pollution") or {}).get("nearest_station_name"),
        }
        for s in evaluated_segments
        if s.get("exposure_band") == "high"
    ]
    low_segments = [
        {
            "segment_id": s["segment_id"],
            "midpoint": s["midpoint"],
            "length_km": s["length_km"],
            "estimated_segment_exposure": s["estimated_segment_exposure"],
            "nearest_station": (s.get("pollution") or {}).get("nearest_station_name"),
        }
        for s in evaluated_segments
        if s.get("exposure_band") == "low"
    ]

    limitations: List[str] = [
        "Values along highway segments are spatially interpolated (IDW) from nearby monitoring stations, not direct road-level sensor measurements.",
        "A lower estimated AQI/exposure route does not guarantee overall road safety or personal medical safety.",
    ]

    if covered_seg_count == 0:
        return {
            "route_id": route.get("route_id"),
            "estimated_exposure_score": None,
            "pollutant_breakdown": pollutant_breakdown,
            "high_exposure_segments": [],
            "low_exposure_segments": [],
            "data_coverage_percentage": 0.0,
            "data_freshness": "no_station_data",
            "confidence_level": "low",
            "segments": evaluated_segments,
            "limitations": [
                f"No monitoring stations found within {config.max_station_distance_km} km along any segment of this route."
            ] + limitations,
        }

    # Scale total exposure proportionally if partial coverage exists without inventing readings
    coverage_fraction = max(0.1, covered_km / total_km)
    normalized_total_exposure = round(exp_sum / coverage_fraction, 2)

    if coverage_pct < 100.0:
        limitations.insert(
            0,
            f"Partial spatial coverage ({coverage_pct}% of route distance within {config.max_station_distance_km} km of a station); uncovered segments are excluded rather than treated as zero.",
        )

    avg_fresh_w = float(np.mean(freshness_weights)) if freshness_weights else 0.5
    if coverage_pct >= 75.0 and avg_fresh_w >= 0.85:
        confidence = "moderate"
    else:
        confidence = "low"

    return {
        "route_id": route.get("route_id"),
        "estimated_exposure_score": normalized_total_exposure,
        "pollutant_breakdown": pollutant_breakdown,
        "high_exposure_segments": high_segments,
        "low_exposure_segments": low_segments,
        "data_coverage_percentage": coverage_pct,
        "data_freshness": freshness_labels[0] if freshness_labels else "unknown",
        "confidence_level": confidence,
        "segments": evaluated_segments,
        "limitations": limitations,
    }


def _collect_corridor_stations(
    routes: Sequence[Dict[str, Any]],
    source_geo: Dict[str, Any],
    dest_geo: Dict[str, Any],
    *,
    station_records: Optional[Sequence[Dict[str, Any]]] = None,
    config: IntercityRouteConfig = DEFAULT_INTERCITY_CONFIG,
) -> List[Dict[str, Any]]:
    """Gather all valid monitoring stations along the intercity corridor."""
    normalized: List[Dict[str, Any]] = []
    if station_records is not None:
        for rec in station_records:
            parsed = _normalize_station_record(rec)
            if parsed is not None:
                normalized.append(parsed)
        return normalized

    # Compute bounding box across all route coordinates + source/destination
    lats = [float(source_geo["lat"]), float(dest_geo["lat"])]
    lons = [float(source_geo["lon"]), float(dest_geo["lon"])]
    for r in routes:
        for pt in (r.get("geometry") or {}).get("coordinates_latlon") or []:
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                lats.append(float(pt[0]))
                lons.append(float(pt[1]))

    pad_deg = 0.45
    bounds_stations = _fetch_waqi_bounds_stations(
        min(lats) - pad_deg,
        min(lons) - pad_deg,
        max(lats) + pad_deg,
        max(lons) + pad_deg,
        config,
    )
    normalized.extend(bounds_stations)

    # Also query existing pipeline for source and destination cities
    try:
        pipe_mod = importlib.import_module("app.aqi_pipeline")
        get_aqi_fn = getattr(pipe_mod, "get_aqi_data", None)
        if callable(get_aqi_fn):
            for geo_obj in (source_geo, dest_geo):
                city_q = str(geo_obj.get("query") or "")
                if not city_q:
                    continue
                res = get_aqi_fn(city_q)
                if isinstance(res, dict):
                    merged = dict(res)
                    merged.setdefault("lat", geo_obj["lat"])
                    merged.setdefault("lon", geo_obj["lon"])
                    parsed = _normalize_station_record(merged)
                    if parsed is not None:
                        normalized.append(parsed)
    except Exception:
        pass

    return normalized


def compare_intercity_routes(
    routes: Sequence[Dict[str, Any]],
    stations: Sequence[Dict[str, Any]],
    *,
    preference: str = "balanced",
    config: IntercityRouteConfig = DEFAULT_INTERCITY_CONFIG,
) -> Dict[str, Any]:
    """Compare alternative intercity routes across exposure, distance, duration, and coverage."""
    pref = _normalize_preference(preference)
    route_list = list(routes or [])
    if not route_list:
        raise ValueError("No intercity routes available to compare.")

    enriched: List[Dict[str, Any]] = []
    for r in route_list:
        exp_summary = calculate_total_route_exposure(r, stations, config=config)
        item = dict(r)
        item["exposure_analysis"] = exp_summary
        matched_station_cities = [
            (seg.get("pollution") or {}).get("nearest_station_name")
            for seg in (exp_summary.get("segments") or [])
            if (seg.get("pollution") or {}).get("nearest_station_name")
        ]
        highways, cities_along = _extract_highways_and_cities(
            item.get("waypoints") or [],
            matched_station_cities,
        )
        item["highways"] = highways
        item["cities_along_route"] = cities_along
        enriched.append(item)

    dists = [float(r["distance_km"]) for r in enriched]
    durs = [float(r["duration_minutes"]) for r in enriched]
    exps = [
        float(r["exposure_analysis"]["estimated_exposure_score"])
        for r in enriched
        if _to_float_or_none((r.get("exposure_analysis") or {}).get("estimated_exposure_score")) is not None
    ]

    def _norm(val: float, lo: float, hi: float) -> float:
        return 0.0 if hi <= lo else max(0.0, min(1.0, (val - lo) / (hi - lo)))

    table_rows: List[Dict[str, Any]] = []
    for item in enriched:
        d_norm = _norm(float(item["distance_km"]), min(dists), max(dists))
        t_norm = _norm(float(item["duration_minutes"]), min(durs), max(durs))
        raw_exp = _to_float_or_none((item.get("exposure_analysis") or {}).get("estimated_exposure_score"))
        e_norm = _norm(raw_exp, min(exps), max(exps)) if (raw_exp is not None and exps) else None

        if pref == "fastest":
            cost = t_norm
        elif pref == "shortest":
            cost = d_norm
        elif pref == "lowest_exposure":
            cost = (0.85 * e_norm + 0.15 * t_norm) if e_norm is not None else (0.5 * t_norm + 0.5 * d_norm)
        else:
            if e_norm is not None:
                w_sum = (
                    config.balanced_exposure_weight
                    + config.balanced_duration_weight
                    + config.balanced_distance_weight
                )
                cost = (
                    config.balanced_exposure_weight * e_norm
                    + config.balanced_duration_weight * t_norm
                    + config.balanced_distance_weight * d_norm
                ) / w_sum
            else:
                cost = 0.5 * t_norm + 0.5 * d_norm

        score = round(max(0.0, min(100.0, (1.0 - cost) * 100.0)), 2)
        item["preference_score"] = score
        item["exposure_included_in_score"] = e_norm is not None

        ea = item["exposure_analysis"]
        table_rows.append(
            {
                "route_id": item["route_id"],
                "route_label": item.get("route_label"),
                "distance_km": item["distance_km"],
                "duration_minutes": item["duration_minutes"],
                "estimated_exposure_score": ea.get("estimated_exposure_score"),
                "data_coverage_percentage": ea.get("data_coverage_percentage"),
                "data_freshness": ea.get("data_freshness"),
                "confidence_level": ea.get("confidence_level"),
                "preference_score": score,
            }
        )

    df_summary = pd.DataFrame(table_rows)
    return {
        "preference": pref,
        "routes": enriched,
        "comparison_table": df_summary.to_dict(orient="records"),
    }


def recommend_intercity_route(
    source_city: str,
    destination_city: str,
    *,
    mode: str = "car",
    preference: str = "balanced",
    known_cities: Optional[Dict[str, Dict[str, Any]]] = None,
    provider_routes: Optional[Sequence[Dict[str, Any]]] = None,
    station_records: Optional[Sequence[Dict[str, Any]]] = None,
    config: IntercityRouteConfig = DEFAULT_INTERCITY_CONFIG,
) -> Dict[str, Any]:
    """End-to-end intercity pollution-aware route recommendation with trade-off analysis."""
    pref = _normalize_preference(preference)
    generated = generate_intercity_routes(
        source_city,
        destination_city,
        mode=mode,
        known_cities=known_cities,
        provider_routes=provider_routes,
        config=config,
    )
    stations = _collect_corridor_stations(
        generated["routes"],
        generated["source_city"],
        generated["destination_city"],
        station_records=station_records,
        config=config,
    )
    compared = compare_intercity_routes(
        generated["routes"],
        stations,
        preference=pref,
        config=config,
    )

    ranked = sorted(
        compared["routes"],
        key=lambda r: float(r.get("preference_score", 0.0)),
        reverse=True,
    )
    best = ranked[0]
    best_ea = best.get("exposure_analysis") or {}

    # Identify trade-offs relative to fastest and shortest alternatives
    fastest_rt = min(ranked, key=lambda r: float(r["duration_minutes"]))
    shortest_rt = min(ranked, key=lambda r: float(r["distance_km"]))
    trade_offs: List[str] = []
    if best["route_id"] != fastest_rt["route_id"]:
        extra_min = round(float(best["duration_minutes"]) - float(fastest_rt["duration_minutes"]), 1)
        trade_offs.append(
            f"Adds +{extra_min} min compared to fastest route ({fastest_rt['route_id']})."
        )
    if best["route_id"] != shortest_rt["route_id"]:
        extra_km = round(float(best["distance_km"]) - float(shortest_rt["distance_km"]), 2)
        trade_offs.append(
            f"Adds +{extra_km} km compared to shortest route ({shortest_rt['route_id']})."
        )
    if not trade_offs:
        trade_offs.append("Selected route matches the fastest and shortest available option.")

    limitations: List[str] = list(generated.get("warnings") or [])
    limitations.extend(best_ea.get("limitations") or [])
    if not best.get("exposure_included_in_score") and pref in ("lowest_exposure", "balanced"):
        limitations.append(
            f"Preference '{pref}' fell back to distance/duration scoring because corridor station coverage was insufficient."
        )

    exp_val = best_ea.get("estimated_exposure_score")
    exp_phrase = (
        f"estimated exposure score {exp_val} (coverage {best_ea.get('data_coverage_percentage')}%, confidence: {best_ea.get('confidence_level')})"
        if exp_val is not None
        else "insufficient corridor monitoring coverage for numeric exposure estimate"
    )
    explanation = (
        f"Recommended {best.get('route_label') or best['route_id']} from {generated['source_city']['query']} "
        f"to {generated['destination_city']['query']} ({generated['transport_mode']}, preference: '{pref}', "
        f"score: {best['preference_score']}/100): {best['distance_km']} km, ~{best['duration_minutes']} min, "
        f"{exp_phrase}. Note: exposure values are IDW estimates from nearby stations, not direct road readings or safety guarantees."
    )

    return {
        "source_city": generated["source_city"],
        "destination_city": generated["destination_city"],
        "straight_line_distance_km": generated["straight_line_distance_km"],
        "transport_mode": generated["transport_mode"],
        "preference": pref,
        "corridor_stations_count": len(stations),
        "alternative_routes": ranked,
        "comparison_table": compared["comparison_table"],
        "recommended_route": best,
        "recommendation_explanation": explanation,
        "trade_offs": trade_offs,
        "data_limitations": limitations,
    }