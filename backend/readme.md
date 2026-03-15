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

**Errors**

- `401` missing/invalid token
- `500` server/database error

---

## 4) Usage Trends Endpoint

### GET `/api/usage-trends/` (Protected)
Time-series metric endpoint with summary and anomaly detection.

**Query params**

- `granularity` (optional): `day | week | month | quarter` (default `month`)
- `metric` (optional, default `uploaded_count`):
  - `uploaded_count`
  - `created_count`
  - `published_count`
  - `uploaded_duration`
  - `created_duration`
  - `published_duration`
  - `publish_conversion_rate`
  - `creation_rate`
  - `processing_efficiency`
  - `waste_index`

Invalid values fall back to defaults.

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

**Errors**

- `401` missing/invalid token
- `500` server/database error

---

## 5) Funnel Endpoints

### GET `/api/funnel/` (Protected)
Funnel-stage summary, breakdown, composition links, and journey rows.

**Query params**

- `dimension` (optional): filter dimension key
- `value` (optional): filter value for `dimension`
- `breakdown` (optional): `channel | input_type | language | output_type` (default `channel`)

Invalid `breakdown` falls back to `channel`.

**Success 200** returns:

- `filter`
- `stageCounts`
- `sankeyLinks`
- `compositionLinks`
- `breakdownDimension`
- `breakdown`
- `journeyVideos`

**Errors**

- `401` missing/invalid token
- `500` server/database error

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

**Errors**

- `401` missing/invalid token
- `404` video not found or not accessible in scope
- `500` server/database error

---

## 6) Explorer Endpoints

### GET `/api/explorer/dimensions` (Protected)
Returns supported explorer dimensions/measures/date fields.

**Success 200**

```json
{
  "dimensions": [{ "key": "channel", "label": "Channel" }],
  "measures": [{ "key": "uploaded_videos", "label": "..." }],
  "dateFields": [{ "key": "upload_date", "label": "Upload Date" }]
}
```

---

### GET `/api/explorer/multidim` (Protected)
Returns multi-dimensional matrix and optional time series.

**Query params**

- `dim1` (default `channel`)
- `dim2` (default `language`)
- `measure` (default `uploaded_videos`)
- `timeGrain` (default `none`): `none | day | week | month`
- `dateField` (default `upload_date`): `upload_date | create_date | publish_date`
- `dim1Value` (optional): filter for selected `dim1`

Invalid values fall back to defaults.

**Success 200** returns:

- `dim1`, `dim2`, `measure`, `timeGrain`, `dateField`, `dim1Value`
- `matrixRows`
- `dim1Values`
- `dim2Values`
- `timeSeriesRows`

**Errors**

- `401` missing/invalid token
- `500` server/database error

---

### GET `/api/explorer/tables` (Protected, `website_admin` only)
List DB table names.

**Success 200**

```json
{ "tables": ["raw_videos", "created_assets"] }
```

**Errors**

- `401` missing/invalid token
- `403` forbidden for non-admin roles
- `500` server/database error

---

### GET `/api/explorer/table/{table_name}` (Protected, `website_admin` only)
Fetch table columns and rows.

**Path params**

- `table_name` (string)

**Query params**

- `limit` (optional, default `100`, max `500`)

**Success 200**

```json
{
  "table": "raw_videos",
  "columns": ["Video_ID", "Upload_Date"],
  "rows": [{ "Video_ID": 1, "Upload_Date": "2025-01-01" }]
}
```

**Errors**

- `401` missing/invalid token
- `403` forbidden for non-admin roles
- `404` table not found
- `500` server/database error

---

### GET `/api/explorer/chart` (Protected, `website_admin` only)
Aggregate chart rows from a DB table.

**Query params**

- `table` (required)
- `x` (required): x-axis/grouping column
- `aggregation` (optional): `count` (default) or `sum`
- `y` (required only when `aggregation=sum`)

**Success 200**

```json
{ "rows": [{ "x": "...", "value": 123 }] }
```

**Errors**

- `400` missing required params or invalid columns
- `401` missing/invalid token
- `403` forbidden for non-admin roles
- `404` invalid table
- `500` server/database error

---

## Notes

- Most analytics endpoints are role-scoped by token claims.
- Authentication failures from middleware return FastAPI standard `detail` messages.
- Route prefixes are configured in `backend/main.py` and `backend/routes/api.py`.
