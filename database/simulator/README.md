# Simulator Module

## Overview

The `simulator` module provides a controlled environment for synthetic data operations in Labs and validation flows. It is designed to run independently from production KPI mutation paths while preserving realistic table relationships and observability.

## Module Objectives

- Generate synthetic, relationally consistent records.
- Capture operation-level logs for traceability.
- Evaluate data quality continuously through deterministic checks.
- Expose a simple API surface for simulator control and inspection.

## Responsibilities Matrix

| Item                | Type              | Role                                                                                                                                                                      |
| ------------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `__init__.py`       | Package marker    | Exposes `SimulatorEngine` as the public module export.                                                                                                                    |
| `engine.py`         | Core engine       | Maintains in-memory simulated tables, seeds test data, runs mutation cycles, tracks logs, and computes quality and timeseries outputs.                                    |
| `router.py`         | API layer         | FastAPI router providing simulator lifecycle and observability endpoints (`/status`, `/start`, `/stop`, `/reset`, `/tables`, `/logs`, `/quality`, `/metrics/timeseries`). |
| `data_logger.py`    | Logging utility   | Structured Postgres-backed logging service for mutation lifecycle and quality issue records in `_simulation_log`.                                                         |
| `quality.py`        | Validation engine | Executes quality rules: required-field checks, duplicate key checks, foreign key integrity, non-negative metrics, and date format validation.                             |
| `test_simulator.py` | Test suite        | Integration-style tests covering schema visibility, seeding behavior, mutation logging, and quality error detection flows.                                                |
| `README.md`         | Documentation     | Defines module purpose, architecture, and ownership boundaries.                                                                                                           |
| `__pycache__/`      | Runtime cache     | Auto-generated Python bytecode cache.                                                                                                                                     |

## Data Isolation and Safety

- Synthetic content uses explicit simulation markers (for example `Simulated Client` and `SIM:` headline prefixes).
- Operational metrics and quality reports are derived from simulator activity only.
- The simulator is intended for experimentation and diagnostics, not as a replacement for production ingestion pipelines.
