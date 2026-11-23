"""Central Application Service Layer.

Integrates existing core and feature modules under `app/` along with
`pollutant_analysis`, `anomaly_detection`, and `pollution_route_optimizer`
using `ServiceResponse` and `ModuleRegistry` without introducing FastAPI or
modifying unrelated modules.
"""

from __future__ import annotations

import importlib
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

logger = logging.getLogger("environmental_health_advisory.service_layer")


@dataclass
class ServiceResponse:
    """Uniform response structure across central service functions."""

    success: bool
    feature: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "feature": self.feature,
            "data": self.data,
            "error": self.error,
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **self.metadata,
            },
        }


class ModuleRegistry:
    """Lazy, fault-isolated loader for existing and newly integrated modules."""

    MODULE_PATHS: Dict[str, str] = {
        "config": "app.config",
        "exceptions": "app.exceptions",
        "models": "app.models",
        "waqi_client": "app.waqi_client",
        "validator": "app.validator",
        "severity_engine": "app.severity_engine",
        "severity_rules": "app.severity_rules",
        "health_guidance": "app.health_guidance",
        "aqi_pipeline": "app.aqi_pipeline",
        "knowledge_base": "app.rag.knowledge_base",
        "retriever": "app.rag.retriever",
        "intent_router": "app.intent_router",
        "llm_generator": "app.llm_generator",
        "history_db": "app.history.database",
        "history_analytics": "app.history.analytics",
        "location_comparison": "app.comparison.location_comparison",
        "alert_engine": "app.alerts.alert_engine",
        "activity_advisor": "app.activity_advisor",
        "data_quality": "app.monitoring.data_quality",
        "pollutant_analysis": "app.pollutant_analysis",
        "anomaly_detection": "app.anomaly_detection",
        "pollution_route_optimizer": "app.pollution_route_optimizer",
    }

    def __init__(self) -> None:
        self._loaded: Dict[str, Any] = {}
        self._errors: Dict[str, str] = {}

    def get(self, key: str) -> Any:
        if key in self._loaded:
            return self._loaded[key]
        if key in self._errors:
            raise RuntimeError(f"Module '{key}' previously failed to load: {self._errors[key]}")

        module_path = self.MODULE_PATHS.get(key)
        if not module_path:
            raise KeyError(f"Unknown module key: '{key}'")

        try:
            mod = importlib.import_module(module_path)
            self._loaded[key] = mod
            return mod
        except Exception as exc:
            self._errors[key] = str(exc)
            logger.error("Failed importing '%s': %s", module_path, exc)
            raise RuntimeError(f"Failed importing '{module_path}': {exc}") from exc

    def status(self) -> Dict[str, Any]:
        return {
            "loaded": sorted(self._loaded.keys()),
            "failed": dict(self._errors),
        }


class EnvironmentalAdvisoryService:
    """Central orchestration layer for core, analytical, anomaly, and route operations."""

    def __init__(self, registry: Optional[ModuleRegistry] = None) -> None:
        self.registry = registry or ModuleRegistry()
        self._retriever_instance: Optional[Any] = None
        self.env_report: Dict[str, Any] = {}
        self.db_report: Dict[str, Any] = {}

    def _get_retriever(self) -> Any:
        if self._retriever_instance is not None:
            return self._retriever_instance

        ret_mod = self.registry.get("retriever")
        retriever_cls = getattr(ret_mod, "KnowledgeRetriever", None)
        if retriever_cls is None:
            raise AttributeError("KnowledgeRetriever not found in app.rag.retriever")

        retriever = retriever_cls()
        index_path = Path("rag_index/knowledge.faiss")
        metadata_path = Path("rag_index/metadata.json")
        if index_path.exists() and metadata_path.exists() and hasattr(retriever, "load_index"):
            try:
                retriever.load_index(str(index_path), str(metadata_path))
            except Exception as exc:
                logger.warning("FAISS index load skipped: %s", exc)

        self._retriever_instance = retriever
        return self._retriever_instance

    def verify_environment(self, required_vars: Optional[List[str]] = None) -> Dict[str, Any]:
        """Verify environment variables without overriding existing values."""
        env_file = Path(".env")
        loaded_from_dotenv: List[str] = []

        if env_file.exists() and env_file.is_file():
            for raw_line in env_file.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
                    loaded_from_dotenv.append(key)

        config_loaded = False
        try:
            self.registry.get("config")
            config_loaded = True
        except Exception:
            config_loaded = False

        checks = required_vars or ["WAQI_API_KEY"]
        present = {var: bool(os.environ.get(var)) for var in checks}

        self.env_report = {
            "dotenv_found": env_file.exists(),
            "loaded_from_dotenv": loaded_from_dotenv,
            "app_config_imported": config_loaded,
            "required_vars_present": present,
        }
        return self.env_report

    def verify_database(self, db_path: Optional[str] = None) -> Dict[str, Any]:
        """Verify SQLite database connectivity and ensure required tables exist."""
        resolved_path = (
            db_path
            or os.environ.get("AQI_DB_PATH")
            or os.environ.get("DATABASE_PATH")
            or "aqi_history.db"
        )

        init_invoked = False
        init_error: Optional[str] = None

        for mod_key, fn_name in (
            ("history_db", "create_history_table"),
            ("alert_engine", "initialize_alert_tables"),
            ("data_quality", "create_monitoring_table"),
        ):
            try:
                mod = self.registry.get(mod_key)
                fn = getattr(mod, fn_name, None)
                if callable(fn):
                    fn()
                    init_invoked = True
            except Exception as exc:
                logger.warning("DB init helper %s.%s failed: %s", mod_key, fn_name, exc)
                init_error = f"{init_error}; {exc}" if init_error else str(exc)

        tables: List[str] = []
        connection_ok = False
        conn_error: Optional[str] = None

        if resolved_path != ":memory:":
            parent = Path(resolved_path).parent
            if str(parent) not in ("", "."):
                parent.mkdir(parents=True, exist_ok=True)

        try:
            with sqlite3.connect(resolved_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
                tables = [row[0] for row in cursor.fetchall()]
                connection_ok = True
        except Exception as exc:
            conn_error = str(exc)
            logger.error("SQLite connection check failed for '%s': %s", resolved_path, exc)

        self.db_report = {
            "db_path": resolved_path,
            "connection_ok": connection_ok,
            "connection_error": conn_error,
            "init_function_invoked": init_invoked,
            "init_error": init_error,
            "tables": tables,
        }
        return self.db_report

    def _run_feature(self, feature_name: str, handler: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
        try:
            payload = handler()
            return ServiceResponse(
                success=True,
                feature=feature_name,
                data=payload,
            ).to_dict()
        except Exception as exc:
            logger.exception("Service feature '%s' raised %s: %s", feature_name, type(exc).__name__, exc)
            return ServiceResponse(
                success=False,
                feature=feature_name,
                error={
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            ).to_dict()

    # 1. Current AQI
    def get_current_aqi(self, location: str, persist_history: bool = False) -> Dict[str, Any]:
        def _handler() -> Dict[str, Any]:
            pipeline_mod = self.registry.get("aqi_pipeline")
            waqi_mod = self.registry.get("waqi_client")
            validator_mod = self.registry.get("validator")
            severity_mod = self.registry.get("severity_engine")

            get_aqi_fn = getattr(pipeline_mod, "get_aqi_data", None) or getattr(waqi_mod, "get_aqi_data", None)
            if not callable(get_aqi_fn):
                raise AttributeError("get_aqi_data not found in app.aqi_pipeline or app.waqi_client")
            raw_result = get_aqi_fn(location)

            val_fn = getattr(pipeline_mod, "validate_aqi_data", None) or getattr(validator_mod, "validate_aqi_data", None)
            if not callable(val_fn):
                raise AttributeError("validate_aqi_data not found")
            validation_result = val_fn(raw_result)

            sev_fn = getattr(pipeline_mod, "determine_severity", None) or getattr(severity_mod, "determine_severity", None)
            if not callable(sev_fn):
                raise AttributeError("determine_severity not found")
            severity_result = sev_fn(validation_result)

            if persist_history:
                db_mod = self.registry.get("history_db")
                save_fn = getattr(db_mod, "save_aqi_reading", None)
                if callable(save_fn):
                    try:
                        save_fn(validation_result)
                    except Exception:
                        save_fn(raw_result)

            return {
                "location": location,
                "raw_aqi": raw_result,
                "validated_aqi": validation_result,
                "severity": severity_result,
            }

        return self._run_feature("get_current_aqi", _handler)

    # 2. Health Advisory
    def get_health_advisory(
        self,
        location: str,
        user_group: str = "general",
        question: Optional[str] = None,
    ) -> Dict[str, Any]:
        def _handler() -> Dict[str, Any]:
            pipeline_mod = self.registry.get("aqi_pipeline")
            if user_group == "general" and question is None and callable(getattr(pipeline_mod, "get_aqi_advisory", None)):
                advisory = pipeline_mod.get_aqi_advisory(location)
                return {
                    "location": location,
                    "user_group": user_group,
                    "advisory": advisory,
                }

            current = self.get_current_aqi(location=location, persist_history=False)
            if not current["success"] or not current["data"]:
                raise RuntimeError(f"Could not retrieve AQI for '{location}': {current.get('error')}")

            validation_result = current["data"]["validated_aqi"]
            severity_result = current["data"]["severity"]

            guidance_mod = self.registry.get("health_guidance")
            guidance_fn = getattr(guidance_mod, "generate_health_guidance", None)
            if not callable(guidance_fn):
                raise AttributeError("generate_health_guidance not found in app.health_guidance")

            guidance = guidance_fn(validation_result, severity_result)

            llm_response = None
            if question:
                try:
                    llm_mod = self.registry.get("llm_generator")
                    if callable(getattr(llm_mod, "generate_response", None)):
                        llm_response = llm_mod.generate_response(
                            query=question,
                            intent="health_advisory",
                            aqi_result=validation_result,
                            severity_result=severity_result,
                            health_guidance=guidance,
                        )
                except Exception:
                    pass

            return {
                "location": location,
                "user_group": user_group,
                "severity": severity_result,
                "guidance": guidance,
                "llm_response": llm_response,
            }

        return self._run_feature("get_health_advisory", _handler)

    # 3. Environmental Knowledge Questions (Intent Router + FAISS RAG + LLM Generator)
    def ask_environmental_question(
        self,
        question: str,
        location: Optional[str] = None,
        top_k: int = 4,
    ) -> Dict[str, Any]:
        def _handler() -> Dict[str, Any]:
            if not question or not question.strip():
                raise ValueError("Question must not be empty.")

            router_mod = self.registry.get("intent_router")
            route_fn = getattr(router_mod, "route_intent", None)
            intent = route_fn(question) if callable(route_fn) else "environmental_knowledge"

            retriever = self._get_retriever()
            rag_context = retriever.retrieve(question, top_k=top_k)

            llm_mod = self.registry.get("llm_generator")
            llm_fn = getattr(llm_mod, "generate_response", None)
            answer = (
                llm_fn(
                    query=question,
                    intent=intent,
                    rag_context=rag_context,
                )
                if callable(llm_fn)
                else rag_context
            )

            return {
                "question": question,
                "location": location,
                "intent": intent,
                "rag_context": rag_context,
                "answer": answer,
            }

        return self._run_feature("ask_environmental_question", _handler)

    # 4. Historical AQI & Trend Analytics
    def get_aqi_history(
        self,
        location: str,
        days: int = 7,
        include_analytics: bool = True,
    ) -> Dict[str, Any]:
        def _handler() -> Dict[str, Any]:
            end_dt = datetime.now(timezone.utc)
            start_dt = end_dt - timedelta(days=days)
            start_str = start_dt.strftime("%Y-%m-%d")
            end_str = end_dt.strftime("%Y-%m-%d")

            db_mod = self.registry.get("history_db")
            hist_fn = getattr(db_mod, "get_aqi_history", None)
            if not callable(hist_fn):
                raise AttributeError("get_aqi_history not found in app.history.database")

            records = hist_fn(location=location, start_date=start_str, end_date=end_str)
            analytics = None

            if include_analytics:
                try:
                    analytics_mod = self.registry.get("history_analytics")
                    ana_fn = getattr(analytics_mod, "get_aqi_analytics", None)
                    if callable(ana_fn):
                        analytics = ana_fn(
                            location=location,
                            start_date=start_str,
                            end_date=end_str,
                            period="daily",
                        )
                except Exception:
                    pass

            return {
                "location": location,
                "days": days,
                "start_date": start_str,
                "end_date": end_str,
                "records": records,
                "analytics": analytics,
            }

        return self._run_feature("get_aqi_history", _handler)

    # 5. Multi-Location AQI Comparison
    def compare_locations(
        self,
        locations: List[str],
        tolerance_minutes: int = 15,
    ) -> Dict[str, Any]:
        def _handler() -> Dict[str, Any]:
            if not locations or len(locations) < 2:
                raise ValueError("Provide at least two locations to compare.")

            comp_mod = self.registry.get("location_comparison")
            comp_fn = getattr(comp_mod, "compare_locations", None)
            if not callable(comp_fn):
                raise AttributeError("compare_locations not found in app.comparison.location_comparison")

            comparison = comp_fn(locations, tolerance_minutes=tolerance_minutes)
            return {
                "locations": locations,
                "tolerance_minutes": tolerance_minutes,
                "comparison": comparison,
            }

        return self._run_feature("compare_locations", _handler)

    # 6. Smart AQI Alerts
    def generate_aqi_alerts(
        self,
        locations: List[str],
        threshold: Optional[int] = None,
    ) -> Dict[str, Any]:
        def _handler() -> Dict[str, Any]:
            if not locations:
                raise ValueError("Provide at least one location for alert evaluation.")

            alert_mod = self.registry.get("alert_engine")
            if callable(getattr(alert_mod, "initialize_alert_tables", None)):
                alert_mod.initialize_alert_tables()

            if threshold is not None and callable(getattr(alert_mod, "configure_default_alert_rules", None)):
                alert_mod.configure_default_alert_rules(locations, aqi_threshold=threshold)

            eval_fn = getattr(alert_mod, "evaluate_multiple_locations", None)
            if not callable(eval_fn):
                raise AttributeError("evaluate_multiple_locations not found in app.alerts.alert_engine")

            evaluations = eval_fn(locations)
            history = (
                alert_mod.get_alert_history(limit=25)
                if callable(getattr(alert_mod, "get_alert_history", None))
                else None
            )

            return {
                "locations": locations,
                "threshold": threshold,
                "evaluations": evaluations,
                "recent_alert_history": history,
            }

        return self._run_feature("generate_aqi_alerts", _handler)

    # 7. Outdoor Activity & Exposure Advisor
    def get_activity_advice(
        self,
        location: str,
        activity: str = "outdoor_exercise",
        duration_minutes: int = 60,
        sensitivity_category: str = "general",
    ) -> Dict[str, Any]:
        def _handler() -> Dict[str, Any]:
            advisor_mod = self.registry.get("activity_advisor")
            live_fn = getattr(advisor_mod, "get_live_activity_advisory", None)
            if not callable(live_fn):
                raise AttributeError("get_live_activity_advisory not found in app.activity_advisor")

            advice = live_fn(location, activity, sensitivity_category=sensitivity_category)
            return {
                "location": location,
                "activity": activity,
                "duration_minutes": duration_minutes,
                "sensitivity_category": sensitivity_category,
                "advice": advice,
            }

        return self._run_feature("get_activity_advice", _handler)

    # 8. AQI Data Quality Monitoring
    def get_data_quality_report(self, location: Optional[str] = None) -> Dict[str, Any]:
        def _handler() -> Dict[str, Any]:
            dq_mod = self.registry.get("data_quality")
            if callable(getattr(dq_mod, "create_monitoring_table", None)):
                dq_mod.create_monitoring_table()

            live_monitoring = None
            if location and callable(getattr(dq_mod, "monitor_aqi_data", None)):
                live_monitoring = dq_mod.monitor_aqi_data(location)

            stats = (
                dq_mod.get_request_statistics(location=location)
                if callable(getattr(dq_mod, "get_request_statistics", None))
                else None
            )
            history = (
                dq_mod.get_monitoring_history(location=location, limit=25)
                if callable(getattr(dq_mod, "get_monitoring_history", None))
                else None
            )

            return {
                "location": location,
                "live_monitoring": live_monitoring,
                "request_statistics": stats,
                "monitoring_history": history,
            }

        return self._run_feature("get_data_quality_report", _handler)

    # 9. Pollutant Analysis & Possible Source Insights (reuses existing AQI & history service methods)
    def analyze_pollutants_and_sources(
        self,
        location: str,
        aqi_payload: Optional[Dict[str, Any]] = None,
        historical_records: Optional[List[Dict[str, Any]]] = None,
        days: int = 7,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        def _handler() -> Dict[str, Any]:
            if not location or not location.strip():
                raise ValueError("Location must be a non-empty string.")
            loc_clean = location.strip()

            pa_mod = self.registry.get("pollutant_analysis")
            analyse_fn = getattr(pa_mod, "analyse_pollutants", None)
            report_fn = getattr(pa_mod, "generate_pollutant_report", None)
            if not callable(analyse_fn) or not callable(report_fn):
                raise AttributeError("analyse_pollutants / generate_pollutant_report not found in app.pollutant_analysis")

            resolved_payload = aqi_payload
            if resolved_payload is None:
                current_res = self.get_current_aqi(location=loc_clean, persist_history=False)
                if current_res.get("success") and isinstance(current_res.get("data"), dict):
                    resolved_payload = (
                        current_res["data"].get("validated_aqi")
                        or current_res["data"].get("raw_aqi")
                        or current_res["data"]
                    )
                else:
                    resolved_payload = {"location": loc_clean}

            if isinstance(resolved_payload, dict) and context:
                merged_payload = dict(resolved_payload)
                for k, v in context.items():
                    if v is not None and k not in merged_payload:
                        merged_payload[k] = v
                resolved_payload = merged_payload

            resolved_history = historical_records
            if resolved_history is None:
                hist_res = self.get_aqi_history(location=loc_clean, days=days, include_analytics=False)
                if hist_res.get("success") and isinstance(hist_res.get("data"), dict):
                    raw_recs = hist_res["data"].get("records")
                    resolved_history = raw_recs if isinstance(raw_recs, list) else []
                else:
                    resolved_history = []

            report = report_fn(
                aqi_payload=resolved_payload,
                location=loc_clean,
                historical_records=resolved_history,
                fetch_if_missing=False,
            )
            analysis = analyse_fn(
                aqi_payload=resolved_payload,
                location=loc_clean,
                historical_records=resolved_history,
                fetch_if_missing=False,
            )

            return {
                "location": report.get("location", loc_clean),
                "observation_timestamp": report.get("observation_timestamp"),
                "available_pollutants": report.get("available_pollutants", {}),
                "missing_pollutants": analysis.get("missing_pollutants", []),
                "dominant_pollutant": report.get("dominant_pollutant"),
                "dominant_pollutant_details": report.get("dominant_pollutant_details", {}),
                "elevated_pollutants": report.get("elevated_pollutants", []),
                "historical_comparison": report.get("historical_comparison", {}),
                "pollutant_patterns": analysis.get("pollutant_patterns", []),
                "possible_sources": report.get("possible_sources", []),
                "supporting_evidence": report.get("supporting_evidence", []),
                "confidence_level": report.get("confidence_level", "low"),
                "data_limitations": report.get("data_limitations", []),
                "summary": report.get("summary", ""),
            }

        return self._run_feature("analyze_pollutants_and_sources", _handler)

    # 10. Anomaly Detection & Event Investigation
    def detect_pollutant_anomalies(
        self,
        location: str,
        historical_records: Optional[Sequence[Dict[str, Any]]] = None,
        current_reading: Optional[Dict[str, Any]] = None,
        nearby_stations: Optional[Sequence[Dict[str, Any]]] = None,
        days: int = 7,
        config: Optional[Any] = None,
    ) -> Dict[str, Any]:
        def _handler() -> Dict[str, Any]:
            if not location or not location.strip():
                raise ValueError("Location must be a non-empty string.")
            loc_clean = location.strip()

            anom_mod = self.registry.get("anomaly_detection")
            detect_fn = getattr(anom_mod, "detect_anomalies", None)
            summary_fn = getattr(anom_mod, "generate_event_summary", None)
            if not callable(detect_fn):
                raise AttributeError("detect_anomalies not found in app.anomaly_detection")

            resolved_history: Optional[Sequence[Dict[str, Any]]] = historical_records
            if resolved_history is None:
                hist_res = self.get_aqi_history(location=loc_clean, days=days, include_analytics=False)
                if hist_res.get("success") and isinstance(hist_res.get("data"), dict):
                    recs = hist_res["data"].get("records")
                    if isinstance(recs, list):
                        resolved_history = recs

            resolved_current = current_reading
            if resolved_current is None:
                cur_res = self.get_current_aqi(location=loc_clean, persist_history=False)
                if cur_res.get("success") and isinstance(cur_res.get("data"), dict):
                    resolved_current = (
                        cur_res["data"].get("validated_aqi")
                        or cur_res["data"].get("raw_aqi")
                    )

            kwargs: Dict[str, Any] = {
                "historical_records": resolved_history,
                "current_reading": resolved_current,
                "nearby_stations": nearby_stations,
            }
            if config is not None:
                kwargs["config"] = config

            result = detect_fn(loc_clean, **kwargs)
            if callable(summary_fn) and isinstance(result, dict):
                result["event_summary"] = summary_fn(result)
            return result

        return self._run_feature("detect_pollutant_anomalies", _handler)

    def investigate_anomaly_event(
        self,
        event: Dict[str, Any],
        nearby_stations: Optional[Sequence[Dict[str, Any]]] = None,
        contextual_data: Optional[Dict[str, Any]] = None,
        investigation_status: str = "under_investigation",
        persist: bool = True,
        config: Optional[Any] = None,
    ) -> Dict[str, Any]:
        def _handler() -> Dict[str, Any]:
            if not isinstance(event, dict):
                raise ValueError("Event must be a dictionary.")

            anom_mod = self.registry.get("anomaly_detection")
            inv_fn = getattr(anom_mod, "investigate_pollution_event", None)
            save_fn = getattr(anom_mod, "save_anomaly_event", None)
            if not callable(inv_fn):
                raise AttributeError("investigate_pollution_event not found in app.anomaly_detection")

            kwargs: Dict[str, Any] = {
                "nearby_stations": nearby_stations,
                "contextual_data": contextual_data,
                "investigation_status": investigation_status,
            }
            if config is not None:
                kwargs["config"] = config

            investigated = inv_fn(event, **kwargs)
            event_id: Optional[str] = investigated.get("event_id") if isinstance(investigated, dict) else None
            persisted = False
            if persist and callable(save_fn):
                event_id = save_fn(investigated)
                persisted = True

            return {
                "event_id": event_id,
                "persisted": persisted,
                "event": investigated,
            }

        return self._run_feature("investigate_anomaly_event", _handler)

    def get_saved_anomaly_events(
        self,
        location: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        def _handler() -> Dict[str, Any]:
            anom_mod = self.registry.get("anomaly_detection")
            hist_fn = getattr(anom_mod, "get_anomaly_history", None)
            if not callable(hist_fn):
                raise AttributeError("get_anomaly_history not found in app.anomaly_detection")

            events = hist_fn(location=location, status=status, limit=limit)
            return {
                "location": location,
                "status": status,
                "count": len(events),
                "events": events,
            }

        return self._run_feature("get_saved_anomaly_events", _handler)

    # 11. Pollution-Aware Route Optimization
    def optimize_pollution_route(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        mode: str = "walking",
        preference: str = "balanced",
        provider_routes: Optional[Sequence[Dict[str, Any]]] = None,
        station_records: Optional[Sequence[Dict[str, Any]]] = None,
        location_hints: Optional[Sequence[str]] = None,
        config: Optional[Any] = None,
    ) -> Dict[str, Any]:
        def _handler() -> Dict[str, Any]:
            route_mod = self.registry.get("pollution_route_optimizer")
            rec_fn = getattr(route_mod, "recommend_best_route", None)
            if not callable(rec_fn):
                raise AttributeError("recommend_best_route not found in app.pollution_route_optimizer")

            kwargs: Dict[str, Any] = {
                "mode": mode,
                "preference": preference,
                "provider_routes": provider_routes,
                "station_records": station_records,
                "location_hints": location_hints,
            }
            if config is not None:
                kwargs["config"] = config

            return rec_fn(origin_lat, origin_lon, dest_lat, dest_lon, **kwargs)

        return self._run_feature("optimize_pollution_route", _handler)