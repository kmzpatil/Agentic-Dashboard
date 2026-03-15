"""Simulator API router."""

from __future__ import annotations

from fastapi import APIRouter, Query

from .engine import SimulatorEngine

router = APIRouter()

engine = SimulatorEngine()
engine.seed(count=10)
engine.start(ops_per_batch=5, interval=2.0)


@router.get("/status")
def get_status():
    return engine.get_state()


@router.post("/start")
def start_simulation(
    ops_per_batch: int = Query(5, ge=1, le=50),
    interval: float = Query(2.0, ge=0.5, le=30.0),
):
    engine.start(ops_per_batch=ops_per_batch, interval=interval)
    return {"message": "Simulation started", **engine.get_state()}


@router.post("/stop")
def stop_simulation():
    engine.stop()
    return {"message": "Simulation stopped", **engine.get_state()}


@router.post("/reset")
def reset_simulation():
    engine.reset()
    engine.seed(count=10)
    return {"message": "Simulation reset and re-seeded", **engine.get_state()}


@router.get("/tables")
def list_tables():
    return engine.get_tables()


@router.get("/tables/{table_name}")
def get_table_data(
    table_name: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return engine.get_table_rows(table_name, limit=limit, offset=offset)


@router.get("/logs")
def get_logs(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    table: str | None = Query(None),
):
    return engine.get_logs(limit=limit, offset=offset, status_filter=status, table_filter=table)


@router.get("/quality")
def get_quality():
    return engine.get_quality_report()


@router.get("/metrics/timeseries")
def get_timeseries():
    return engine.get_timeseries_metrics()
