# Backend API Reference

This backend is a FastAPI service mounted under `/api` (see `backend/main.py`).

## Base URL

- Local default: `http://localhost:<PORT>/api`
- Health routes: `/api/health/*`
- Auth routes: `/api/auth/*`
- Analytics routes: `/api/*`

## Authentication

Protected endpoints require:

- Header: `Authorization: Bearer <JWT_TOKEN>`

Auth roles in token:

- `website_admin`
- `client_admin`
- `user`

Role behavior:

- `website_admin`: full analytics/data access
- `client_admin`: scoped to token `clientName`
- `user`: scoped to token `userId`

---

## 1) Auth Endpoints

### POST `/api/auth/login`
Authenticate with username/password and receive JWT.

**Request body**

```json
{
  "username": "string",
  "password": "string"
}
```

**Success 200**

```json
{
  "token": "<jwt>",
  "user": {
    "id": 1,
    "username": "...",
    "role": "website_admin|client_admin|user",
    "clientName": "...",
    "userId": 123
  }
}
```

**Errors**

- `400` missing username/password
- `401` invalid credentials/inactive user
- `500` server/database error

---

### GET `/api/auth/me` (Protected)
Return current authenticated user profile.

**Success 200**

```json
{
  "user": {
    "id": 1,
    "username": "...",
    "role": "website_admin|client_admin|user",
    "clientName": "...",
    "userId": 123
  }
}
```

**Errors**

- `401` invalid/expired session token
- `500` server/database error

---

## 2) Health Endpoint

### GET `/api/health/`
Basic service + DB connectivity check.

**Success 200**

```json
{ "ok": true }
```

**Error 500**

```json
{ "ok": false, "error": "..." }
```

---

## 3) Overview Endpoint

### GET `/api/overview/` (Protected)
Dashboard overview payload.

**Success 200**

```json
{
  "kpis": { "...": "..." },
  "topPerformers": [
    { "dimension": "Channel", "label": "...", "value": 123 }
  ],
  "alerts": [
    {
      "title": "...",
      "subtitle": "...",
      "severity": "warning|critical"
    }
  ]
}
```

---

## 4) Usage Trends Endpoint

### GET `/api/usage-trends/` (Protected)
Time-series metric endpoint with summary and anomaly detection.

**Query params**

- `granularity` (optional): `day | week | month | quarter` (default `month`)
- `metric` (optional, default `uploaded_count`):
  - `uploaded_count`, `created_count`, `published_count`
  - `uploaded_duration`, `created_duration`, `published_duration`
  - `publish_conversion_rate`, `creation_rate`, `processing_efficiency`, `waste_index`

**Success 200**

```json
{
  "metric": "uploaded_count",
  "granularity": "month",
  "series": [
    { "period": "2025-01-01", "value": 100.0 }
  ],
  "summary": {
    "latestValue": 100.0,
    "latestPeriod": "2025-01-01",
    "deltaVsPreviousPct": 12.5
  },
  "anomalies": [
    {
      "period": "2025-01-01",
      "value": 100.0,
      "zScore": 2.1,
      "severity": "medium|high",
      "direction": "spike|drop"
    }
  ]
}
```

---

## 5) Trends Endpoint

### GET `/api/trends/` (Protected)
Historical trend data with filter support.

**Query params**

- `metric` (default `uploaded_count`)
- `granularity` (default `month`)
- Filter params: `company`, `channel`, `user`, `language`, `input_type`, `output_type`, `date_from`, `date_to`

---

## 6) Funnel Endpoints

### GET `/api/funnel/` (Protected)
Funnel-stage summary, breakdown, composition links, and journey rows.

**Query params**

- `dimension` (optional): filter dimension key
- `value` (optional): filter value for `dimension`
- `breakdown` (optional): `channel | input_type | language | output_type` (default `channel`)

**Success 200** returns:

- `filter`, `stageCounts`, `sankeyLinks`, `compositionLinks`
- `breakdownDimension`, `breakdown`, `journeyVideos`

---

### GET `/api/funnel/video/{video_id}` (Protected)
Video-level details for one video.

**Path params**

- `video_id` (integer)

**Success 200**

```json
{
  "video": { "...": "..." },
  "assets": [{ "...": "..." }]
}
```

---

## 7) Explorer Endpoints

### GET `/api/explorer/dimensions` (Protected)
Returns supported explorer dimensions/measures/date fields.

### GET `/api/explorer/multidim` (Protected)
Returns multi-dimensional matrix and optional time series.

**Query params**

- `dim1` (default `channel`), `dim2` (default `language`)
- `measure` (default `uploaded_videos`)
- `timeGrain` (default `none`): `none | day | week | month`
- `dateField` (default `upload_date`): `upload_date | create_date | publish_date`
- `dim1Value` (optional): filter for selected `dim1`

### GET `/api/explorer/tables` (Protected, `website_admin` only)
List DB table names.

### GET `/api/explorer/table/{table_name}` (Protected, `website_admin` only)
Fetch table columns and rows. Query param: `limit` (default 100, max 500).

### GET `/api/explorer/chart` (Protected, `website_admin` only)
Aggregate chart rows from a DB table. Params: `table`, `x`, `aggregation`, `y`.

---

## 8) Insights Endpoint

### GET `/api/insights/` (Protected)
Generated insight cards for dashboard surfaces.

**Query params**

- `surface` (default `mission-control`)
- `limit` (1-12, default 6)

**Success 200**

```json
{ "insights": [...] }
```

---

## 9) User Journey Endpoint

### GET `/api/user-journey/` (Protected)
User journey data with timeseries, platform breakdown, and engagement metrics.

**Query params**

- `granularity` (default `week`)
- Filter params: `company`, `channel`, `user`, `language`, `input_type`, `output_type`, `date_from`, `date_to`

**Success 200** returns:

- `summary` — uploaded, created, published, distributions, views, interactions
- `timeseries` — data at specified granularity
- `platformBreakdown`, `outputTypeBreakdown`
- `recentJourneys`, `kpiDefinitions`

---

## 10) Advanced KPIs Endpoint

### GET `/api/advanced-kpis/{kpi_id}` (Protected)
Get computed data for a specific advanced KPI.

**Supported KPI IDs**:

`publish_conversion`, `processing_efficiency`, `upload_failure_rate`, `creation_rate`, `multidimensional_waste`, `publish_dependency_index`, `point_biserial`, `ctas`, `rei`, `roi`, `waste_index`, `interaction_lift`, `cross_dimension_entropy`, `dfs`, `month_by_month_use_rate`

---

## 11) Custom KPI Endpoints

### POST `/api/kpi/create` (Protected)
Create a custom KPI from formula or natural language.

**Request body**

```json
{
  "name": "string",
  "mode": "formula|natural_language",
  "expression": "string",
  "description": "string (optional)",
  "time_granularity": "day|week|month|quarter (optional)"
}
```

### GET `/api/kpi/list` (Protected)
List all saved KPI definitions.

### GET `/api/kpi/{kpi_id}` (Protected)
Execute a KPI and return time-series data with insights.

### DELETE `/api/kpi/{kpi_id}` (Protected)
Delete a KPI definition.

---

## 12) Data Quality Endpoints

### GET `/api/data-quality/` (Protected)
Data quality overview with scores, issues, and heatmap.

**Success 200** returns:

- `overall_score`, `table_scores`
- `orphan_links`, `heatmap`, `dead_ends`, `suspicious_users`

### GET `/api/data-quality/issues` (Protected)
Paginated list of data quality issues.

**Query params**

- `table` (optional): filter by table name
- `check_type` (optional): filter by check type
- `limit` (default 50), `offset` (default 0)

---

## 13) Wrapped Endpoint

### GET `/api/wrapped/` (Protected)
Aggregated KPI data for period summary ("Year Wrapped").

**Success 200** returns:

- Pipeline counts (uploaded, created, published)
- Entropy and personality scores
- Best month performance
- Top channels/users (client_admin), REI scores (user role)

---

## 14) Publish Predictor Endpoints

### GET `/api/publish-predictor/options` (Protected)
Available model options (clients, channels, types, durations).

### POST `/api/publish-predictor/predict` (Protected)
Predict publish probability with SHAP feature importance.

**Request body**

```json
{
  "client": "string",
  "channel": "string",
  "input_type": "string",
  "language": "string",
  "output_type": "string",
  "durations": { "...": 0 }
}
```

### POST `/api/publish-predictor/retrain` (Protected, `website_admin` only)
Retrain the RandomForest prediction model.

---

## 15) Chat Endpoints

### POST `/api/chat` (Protected)
Send a message to ATLAS.

**Request body**

```json
{
  "message": "string",
  "filters": {},
  "conversation_id": "string (optional)",
  "mode": "string (optional)"
}
```

### POST `/api/chat/stream` (Protected)
Streaming SSE endpoint for progressive agent events.

Same request body as `/api/chat`.

---

## 16) Conversation Endpoints

### GET `/api/conversations` (Protected)
List all saved conversations for the authenticated user.

### GET `/api/conversations/{conversation_id}` (Protected)
Retrieve a specific conversation with messages.

### DELETE `/api/conversations/{conversation_id}` (Protected)
Delete a conversation.

---

## 17) Filter Endpoints

### GET `/api/v1/filters/date-range` (Protected)
Get earliest and latest dates in the dataset.

### GET `/api/v1/filters/options/company` (Protected)
Get all company/client names.

### GET `/api/v1/filters/options/channel` (Protected)
Get available channels. Query param: `company` (optional).

### GET `/api/v1/filters/options/user` (Protected)
Get available users. Query params: `company`, `channel` (optional).

### GET `/api/v1/filters/options/language` (Protected)
Get available languages. Query param: `company` (optional).

### GET `/api/v1/filters/options/input-type` (Protected)
Get available input types. Query param: `company` (optional).

### GET `/api/v1/filters/options/output-type` (Protected)
Get available output types. Query param: `company` (optional).

### GET `/api/v1/filters/options` (Protected)
Get all filter options in a single request.

### GET `/api/v1/filters/validate` (Protected)
Validate a filter combination returns data.

---

## 18) Labs Endpoints

### GET `/api/labs/forecast/client-chronos` (Protected)
Forecast metrics for a specific client using ChronoS.

**Query params**: `client_name` (required), `metric`, `granularity`, `prediction_length` (1-90)

### GET `/api/labs/forecast/all-clients` (Protected)
Forecast metrics for all clients.

**Query params**: `metric`, `granularity`, `prediction_length` (1-90)

---

## 19) Simulator Endpoints (Labs)

Mounted under `/api/labs/simulator/` and `/api/simulator/`.

- `GET /status` — Simulator status
- `POST /start` — Start simulator
- `POST /stop` — Stop simulator
- `POST /reset` — Reset simulator state
- `GET /tables` — List simulator tables
- `GET /logs` — Operation logs
- `GET /quality` — Quality check results
- `GET /metrics/timeseries` — Timeseries metrics

---

## Notes

- Most analytics endpoints are role-scoped by token claims.
- Authentication failures from middleware return FastAPI standard `detail` messages.
- Route prefixes are configured in `backend/main.py` and `backend/routes/api.py`.
