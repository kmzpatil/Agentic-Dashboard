# Database Module

## Overview

The `database` folder contains all database-facing assets for GC Data:

- bootstrap and local database lifecycle scripts,
- database dumps and schema artifacts,
- a standalone API surface for table-level access,
- and an isolated simulator module for synthetic data and quality diagnostics.

## Directory Map

```text
database/
|- __init__.py
|- bootstrap_postgres.py
|- frammer_data.sql
|- frammer_database.sql
|- local_postgres.py
|- README.md
|- requirements.txt
|- reset_local_postgres.py
|- schema.sql
|- .local_postgres/
|  |- data/
|  |- socket/
|  |- postgres.log
|  |- README.md
|- simulator/
|  |- __init__.py
|  |- data_logger.py
|  |- engine.py
|  |- quality.py
|  |- router.py
|  |- test_simulator.py
|  |- README.md
|- __pycache__/
```

## Responsibilities Matrix

| Item                      | Type                | Role                                                                                                          |
| ------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------- |
| `__init__.py`             | Package marker      | Marks this folder as a Python package for module imports.                                                     |
| `bootstrap_postgres.py`   | Bootstrap script    | Migrates data from SQLite assets into PostgreSQL, recreates tables, loads rows, and applies indexes.          |
| `local_postgres.py`       | Runtime utility     | Starts, stops, inspects, and initializes a self-contained local PostgreSQL cluster under `.local_postgres/`.  |
| `reset_local_postgres.py` | Maintenance utility | Stops local PostgreSQL (if running) and deletes `.local_postgres/` for a clean reset.                         |
| `requirements.txt`        | Dependency file     | Lists Python dependencies required by the database scripts and local API tooling.                             |
| `frammer_data.sql`        | Data artifact       | PostgreSQL plain-text dump used for local restore and bootstrap of analytics and auth-related data.           |
| `frammer_database.sql`    | Data artifact       | SQLite-style SQL script containing transactional schema creation and insert statements for dataset bootstrap. |
| `schema.sql`              | Data artifact       | PostgreSQL custom-format binary dump (`PGDMP`), intended for `pg_restore` usage.                              |
| `.local_postgres/`        | Runtime folder      | Generated local cluster state, including data files, socket path, and logs.                                   |
| `simulator/`              | Feature module      | Isolated simulator package for synthetic data generation, mutation logging, and quality analysis.             |
| `__pycache__/`            | Runtime cache       | Auto-generated Python bytecode cache.                                                                         |

## Operational Guidance

1. Prefer `frammer_data.sql` for local PostgreSQL restoration.
2. Use `schema.sql` only with `pg_restore` because it is not plain SQL.
3. Treat `.local_postgres/` and `__pycache__/` as generated runtime state.
