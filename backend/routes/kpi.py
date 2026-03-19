"""
routes/kpi.py
-------------
REST endpoints for Custom KPI feature.

  POST /api/kpi/create        Create a new KPI (formula or natural_language)
  GET  /api/kpi/list          List all saved KPIs
  GET  /api/kpi/{id}          Execute a KPI and return time-series + insights
  DELETE /api/kpi/{id}        Delete a KPI definition

All endpoints require a valid JWT (require_auth).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from backend.contracts import KPICreateRequest, KPIExecuteResponse, KPIResponse
from backend.kpi import service as kpi_service
from backend.middleware.auth import AuthContext, require_auth

logger = logging.getLogger("frammer.routes.kpi")

router = APIRouter()


# ── POST /api/kpi/create ─────────────────────────────────────────────────────

@router.post("/create", response_model=KPIResponse)
async def create_kpi(
    body: KPICreateRequest,
    auth: AuthContext = Depends(require_auth),
):
    """
    Create a new custom KPI from a formula or natural-language description.

    - **formula** mode: arithmetic expression using known metric names
      e.g. `"created_count / uploaded_count * 100"`
    - **natural_language** mode: plain English description; LLM converts to DSL
      e.g. `"percentage of clips that get published"`

    The KPI is parsed, validated, and stored. No SQL is persisted — only the
    structured DSL JSON, which is compiled to SQL at execution time.
    """
    try:
        record = kpi_service.create_kpi(
            name=body.name,
            mode=body.mode,
            expression=body.expression,
            description=body.description,
            time_granularity=body.time_granularity,
            created_by=auth.username,
        )
        return KPIResponse(
            id=record["id"],
            name=record["name"],
            description=record.get("description"),
            dsl_json=record["dsl_json"],
            created_at=record.get("created_at"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("KPI creation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"KPI creation failed: {exc}")


# ── GET /api/kpi/list ─────────────────────────────────────────────────────────

@router.get("/list")
async def list_kpis(auth: AuthContext = Depends(require_auth)):
    """
    Return all saved KPI definitions (id, name, description, dsl_json, created_at).
    Ordered newest first.
    """
    try:
        records = kpi_service.list_kpis()
        return {"kpis": records}
    except Exception as exc:
        logger.error("KPI list failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to list KPIs: {exc}")


# ── GET /api/kpi/{id} ─────────────────────────────────────────────────────────

@router.get("/{kpi_id}")
async def execute_kpi(
    kpi_id: int,
    auth: AuthContext = Depends(require_auth),
):
    """
    Execute a saved KPI and return:
    - `time_series`:  list of {period, value} rows
    - `insights`:     deterministic stats (trend, pct_change, max, min, summary)

    Results are cached in-memory per (kpi_id, dsl_json, auth_scope) so repeated
    calls within a server session are served instantly without hitting the DB.
    """
    try:
        result = kpi_service.execute_kpi(kpi_id, auth)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("KPI execution failed for id=%d: %s", kpi_id, exc)
        return JSONResponse(
            status_code=500,
            content={"error": f"KPI execution failed: {exc}"},
        )


# ── DELETE /api/kpi/{id} ──────────────────────────────────────────────────────

@router.delete("/{kpi_id}")
async def delete_kpi(
    kpi_id: int,
    auth: AuthContext = Depends(require_auth),
):
    """
    Delete a KPI definition by ID.
    """
    try:
        kpi_service.ensure_kpi_table()
        from backend.db.pool import query
        result = query(
            "DELETE FROM kpi_definitions WHERE id = $1 RETURNING id;",
            [kpi_id],
        )
        if not result.rows:
            raise HTTPException(status_code=404, detail=f"KPI id={kpi_id} not found.")
        return {"deleted": kpi_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("KPI delete failed for id=%d: %s", kpi_id, exc)
        raise HTTPException(status_code=500, detail=f"KPI delete failed: {exc}")
