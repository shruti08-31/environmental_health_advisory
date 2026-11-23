"""Pre-FastAPI Central Application Service Layer.

Integrates existing core and feature modules under `app/` without introducing
FastAPI, a dashboard, or new ML/DL models.
"""

from __future__ import annotations

import importlib
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ServiceResponse:
    """Uniform response structure across all eight central service functions."""

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
    """Lazy, fault-isolated loader for existing modules in the repository."""

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
            raise RuntimeError(f"Failed importing '{module_path}': {exc}") from exc

    def status(self) -> Dict[str, Any]:
        return {
            "loaded": sorted(self._loaded.keys()),
            "failed": dict(self._errors),
        }


class EnvironmentalAdvisoryService:
    """Central orchestration layer for all 8 pre-FastAPI operations."""

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
            except Exception:
                pass

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

        try:
            db_mod = self.registry.get("history_db")
            if hasattr(db_mod, "create_history_table") and callable(db_mod.create_history_table):
                db_mod.create_history_table()
                init_invoked = True
        except Exception as exc:
            init_error = str(exc)

        try:
            alert_mod = self.registry.get("alert_engine")
            if hasattr(alert_mod, "initialize_alert_tables") and callable(alert_mod.initialize_alert_tables):
                alert_mod.initialize_alert_tables()
                init_invoked = True
        except Exception as exc:
            init_error = f"{init_error}; {exc}" if init_error else str(exc)

        try:
            dq_mod = self.registry.get("data_quality")
            if hasattr(dq_mod, "create_monitoring_table") and callable(dq_mod.create_monitoring_table):
                dq_mod.create_monitoring_table()
                init_invoked = True
        except Exception as exc:
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