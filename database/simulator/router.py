"""Simulator API router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from .engine import SimulatorEngine

router = APIRouter()

engine: SimulatorEngine | None = None
engine_error: str | None = None


def _get_engine() -> SimulatorEngine:
    global engine, engine_error
    if engine is not None:
        return engine

    try:
        engine = SimulatorEngine()
        engine.seed(count=10)
        engine.start(ops_per_batch=5, interval=2.0)
        engine_error = None
        return engine
    except Exception as exc:
        engine_error = str(exc)
        raise HTTPException(status_code=503, detail=f"Simulator unavailable: {exc}") from exc


@router.get("/status")
def get_status():
    return _get_engine().get_state()


@router.post("/start")
def start_simulation(
    ops_per_batch: int = Query(5, ge=1, le=50),
    interval: float = Query(2.0, ge=0.5, le=30.0),
):
    active_engine = _get_engine()
    active_engine.start(ops_per_batch=ops_per_batch, interval=interval)
    return {"message": "Simulation started", **active_engine.get_state()}


@router.post("/stop")
def stop_simulation():
    active_engine = _get_engine()
    active_engine.stop()
    return {"message": "Simulation stopped", **active_engine.get_state()}


@router.post("/reset")
def reset_simulation():
    active_engine = _get_engine()
    active_engine.reset()
    active_engine.seed(count=10)
    return {"message": "Simulation reset and re-seeded", **active_engine.get_state()}


@router.get("/tables")
def list_tables():
    return _get_engine().get_tables()


@router.get("/tables/{table_name}")
def get_table_data(
    table_name: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return _get_engine().get_table_rows(table_name, limit=limit, offset=offset)


@router.get("/logs")
def get_logs(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    table: str | None = Query(None),
):
    return _get_engine().get_logs(limit=limit, offset=offset, status_filter=status, table_filter=table)


@router.get("/quality")
def get_quality():
    return _get_engine().get_quality_report()


@router.get("/metrics/timeseries")
def get_timeseries():
    return _get_engine().get_timeseries_metrics()
