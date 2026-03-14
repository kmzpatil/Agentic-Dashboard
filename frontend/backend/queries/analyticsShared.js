const METRIC_SQL = {
  uploaded_count: `
    SELECT date_trunc($1, to_date("Upload_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS value
    FROM raw_videos
    GROUP BY 1
    ORDER BY 1;
  `,
  created_count: `
    SELECT date_trunc($1, to_date("Create_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS value
    FROM created_assets
    GROUP BY 1
    ORDER BY 1;
  `,
  published_count: `
    SELECT date_trunc($1, to_date("Publish_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS value
    FROM published_posts
    GROUP BY 1
    ORDER BY 1;
  `,
  uploaded_duration: `
    SELECT date_trunc($1, to_date("Upload_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM("Uploaded_Duration"), 0)::float8 AS value
    FROM raw_videos
    GROUP BY 1
    ORDER BY 1;
  `,
  created_duration: `
    SELECT date_trunc($1, to_date("Create_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM("Created_Duration"), 0)::float8 AS value
    FROM created_assets
    GROUP BY 1
    ORDER BY 1;
  `,
  published_duration: `
    SELECT date_trunc($1, to_date("Publish_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM("Published_Duration"), 0)::float8 AS value
    FROM published_posts
    GROUP BY 1
    ORDER BY 1;
  `,
  publish_conversion_rate: `
    WITH created AS (
      SELECT date_trunc($1, to_date("Create_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS created_count
      FROM created_assets
      GROUP BY 1
    ),
    published AS (
      SELECT date_trunc($1, to_date("Publish_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS published_count
      FROM published_posts
      GROUP BY 1
    )
    SELECT c.period,
      CASE WHEN c.created_count = 0 THEN 0 ELSE (COALESCE(p.published_count, 0) / c.created_count) * 100 END AS value
    FROM created c
    LEFT JOIN published p ON p.period = c.period
    ORDER BY c.period;
  `,
  creation_rate: `
    WITH uploaded AS (
      SELECT date_trunc($1, to_date("Upload_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS uploaded_count
      FROM raw_videos
      GROUP BY 1
    ),
    created AS (
      SELECT date_trunc($1, to_date("Create_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS created_count
      FROM created_assets
      GROUP BY 1
    )
    SELECT u.period,
      CASE WHEN u.uploaded_count = 0 THEN 0 ELSE (COALESCE(c.created_count, 0) / u.uploaded_count) * 100 END AS value
    FROM uploaded u
    LEFT JOIN created c ON c.period = u.period
    ORDER BY u.period;
  `,
  processing_efficiency: `
    WITH created AS (
      SELECT date_trunc($1, to_date("Create_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM("Created_Duration"), 0)::float8 AS created_duration
      FROM created_assets
      GROUP BY 1
    ),
    published AS (
      SELECT date_trunc($1, to_date("Publish_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM("Published_Duration"), 0)::float8 AS published_duration
      FROM published_posts
      GROUP BY 1
    )
    SELECT c.period,
      CASE WHEN c.created_duration = 0 THEN 0 ELSE (COALESCE(p.published_duration, 0) / c.created_duration) * 100 END AS value
    FROM created c
    LEFT JOIN published p ON p.period = c.period
    ORDER BY c.period;
  `,
  waste_index: `
    WITH created AS (
      SELECT date_trunc($1, to_date("Create_Date", 'YYYY-MM-DD'))::date AS period,
      COALESCE(AVG("Created_Duration"), 0)::float8 AS avg_created_duration
      FROM created_assets
      GROUP BY 1
    ),
    published AS (
      SELECT date_trunc($1, to_date("Publish_Date", 'YYYY-MM-DD'))::date AS period,
      COALESCE(AVG("Published_Duration"), 0)::float8 AS avg_published_duration
      FROM published_posts
      GROUP BY 1
    )
    SELECT c.period, (c.avg_created_duration - COALESCE(p.avg_published_duration, 0))::float8 AS value
    FROM created c
    LEFT JOIN published p ON p.period = c.period
    ORDER BY c.period;
  `,
};

const DIMENSION_MAP = {
  channel:            'rvc."Channel_Name"',
  language:           'rv."Language"',
  input_type:         'rv."Input_Type"',
  output_type:        'ca."Output_Type"',
  user:               'u."User_Name"',
  client:             'COALESCE(ch."Client_Name", u."Client_Name")',
  published_platform: 'pd."Published_Platform"',
};

const MEASURE_MAP = {
  uploaded_videos:  'COUNT(DISTINCT rv."Video_ID")::float8',
  created_assets:   'COUNT(DISTINCT ca."Asset_ID")::float8',
  published_posts:  'COUNT(DISTINCT pp."Post_ID")::float8',
};

const DATE_FIELD_MAP = {
  upload_date:  "to_date(rv.\"Upload_Date\", 'YYYY-MM-DD')",
  create_date:  "to_date(ca.\"Create_Date\", 'YYYY-MM-DD')",
  publish_date: "to_date(pp.\"Publish_Date\", 'YYYY-MM-DD')",
};

const ANALYTICS_BASE_FROM = `
  FROM raw_videos rv
  LEFT JOIN raw_video_channel rvc ON rvc."Video_ID" = rv."Video_ID"
  LEFT JOIN channels ch ON ch."Channel_Name" = rvc."Channel_Name"
  LEFT JOIN users u ON u."User_ID" = rv."User_ID"
  LEFT JOIN created_assets ca ON ca."Video_ID" = rv."Video_ID"
  LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
  LEFT JOIN post_distribution pd ON pd."Post_ID" = pp."Post_ID"
`;

function getTrendInsights(points) {
  if (points.length < 3) {
    return [];
  }

  const values = points.map((p) => Number(p.value || 0));
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((acc, v) => acc + (v - mean) ** 2, 0) / values.length;
  const std = Math.sqrt(variance);

  return points
    .map((p) => {
      const value = Number(p.value || 0);
      const z = std === 0 ? 0 : (value - mean) / std;
      return { period: p.period, value, z };
    })
    .filter((p) => Math.abs(p.z) >= 1.5)
    .sort((a, b) => Math.abs(b.z) - Math.abs(a.z))
    .slice(0, 8)
    .map((p) => ({
      period:    p.period,
      value:     Number(p.value.toFixed(2)),
      zScore:    Number(p.z.toFixed(2)),
      severity:  Math.abs(p.z) >= 2.5 ? 'high' : 'medium',
      direction: p.z > 0 ? 'spike' : 'drop',
    }));
}

function buildWhereClause(predicates) {
  if (!predicates.length) {
    return '';
  }
  return `WHERE ${predicates.join(' AND ')}`;
}

/**
 * Build RBAC-scoped join + predicate fragments.
 * website_admin → no filter (sees everything)
 * client_admin  → scoped to their client
 * user          → scoped to their User_ID
 */
function buildAccessFilter(auth, startIndex = 1, videoAlias = 'rv') {
  if (!auth || auth.role === 'website_admin') {
    return { join: '', predicates: [], params: [], nextIndex: startIndex };
  }

  if (auth.role === 'client_admin') {
    return {
      join: `
        LEFT JOIN users u_scope ON u_scope."User_ID" = ${videoAlias}."User_ID"
        LEFT JOIN raw_video_channel rvc_scope ON rvc_scope."Video_ID" = ${videoAlias}."Video_ID"
        LEFT JOIN channels ch_scope ON ch_scope."Channel_Name" = rvc_scope."Channel_Name"
      `,
      predicates: [`COALESCE(ch_scope."Client_Name", u_scope."Client_Name") = $${startIndex}`],
      params:     [auth.clientName],
      nextIndex:  startIndex + 1,
    };
  }

  if (auth.role === 'user') {
    return {
      join:       '',
      predicates: [`${videoAlias}."User_ID" = $${startIndex}`],
      params:     [auth.userId],
      nextIndex:  startIndex + 1,
    };
  }

  return { join: '', predicates: [], params: [], nextIndex: startIndex };
}

/**
 * RBAC-aware version of METRIC_SQL: wraps the query in scoped CTEs so the
 * metric is computed only over the videos/assets visible to this user.
 */
function getMetricQuery(metric, accessFilter) {
  const scopedVideosWhere = buildWhereClause(accessFilter.predicates);
  const scopedVideosCte = `
    WITH scoped_videos AS (
      SELECT DISTINCT rv."Video_ID", rv."User_ID", rv."Upload_Date", rv."Uploaded_Duration"
      FROM raw_videos rv
      ${accessFilter.join}
      ${scopedVideosWhere}
    ),
    scoped_assets AS (
      SELECT ca.*
      FROM created_assets ca
      JOIN scoped_videos sv ON sv."Video_ID" = ca."Video_ID"
    ),
    scoped_posts AS (
      SELECT pp.*
      FROM published_posts pp
      JOIN scoped_assets sa ON sa."Asset_ID" = pp."Asset_ID"
    )
  `;

  const metricSql = {
    uploaded_count: `${scopedVideosCte}
      SELECT date_trunc($1, to_date(sv."Upload_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS value
      FROM scoped_videos sv GROUP BY 1 ORDER BY 1;
    `,
    created_count: `${scopedVideosCte}
      SELECT date_trunc($1, to_date(sa."Create_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS value
      FROM scoped_assets sa GROUP BY 1 ORDER BY 1;
    `,
    published_count: `${scopedVideosCte}
      SELECT date_trunc($1, to_date(sp."Publish_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS value
      FROM scoped_posts sp GROUP BY 1 ORDER BY 1;
    `,
    uploaded_duration: `${scopedVideosCte}
      SELECT date_trunc($1, to_date(sv."Upload_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM(sv."Uploaded_Duration"), 0)::float8 AS value
      FROM scoped_videos sv GROUP BY 1 ORDER BY 1;
    `,
    created_duration: `${scopedVideosCte}
      SELECT date_trunc($1, to_date(sa."Create_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM(sa."Created_Duration"), 0)::float8 AS value
      FROM scoped_assets sa GROUP BY 1 ORDER BY 1;
    `,
    published_duration: `${scopedVideosCte}
      SELECT date_trunc($1, to_date(sp."Publish_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM(sp."Published_Duration"), 0)::float8 AS value
      FROM scoped_posts sp GROUP BY 1 ORDER BY 1;
    `,
    publish_conversion_rate: `${scopedVideosCte}
      , created AS (
        SELECT date_trunc($1, to_date(sa."Create_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS created_count
        FROM scoped_assets sa GROUP BY 1
      ),
      published AS (
        SELECT date_trunc($1, to_date(sp."Publish_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS published_count
        FROM scoped_posts sp GROUP BY 1
      )
      SELECT c.period,
        CASE WHEN c.created_count = 0 THEN 0 ELSE (COALESCE(p.published_count, 0) / c.created_count) * 100 END AS value
      FROM created c LEFT JOIN published p ON p.period = c.period ORDER BY c.period;
    `,
    creation_rate: `${scopedVideosCte}
      , uploaded AS (
        SELECT date_trunc($1, to_date(sv."Upload_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS uploaded_count
        FROM scoped_videos sv GROUP BY 1
      ),
      created AS (
        SELECT date_trunc($1, to_date(sa."Create_Date", 'YYYY-MM-DD'))::date AS period, COUNT(*)::float8 AS created_count
        FROM scoped_assets sa GROUP BY 1
      )
      SELECT u.period,
        CASE WHEN u.uploaded_count = 0 THEN 0 ELSE (COALESCE(c.created_count, 0) / u.uploaded_count) * 100 END AS value
      FROM uploaded u LEFT JOIN created c ON c.period = u.period ORDER BY u.period;
    `,
    processing_efficiency: `${scopedVideosCte}
      , created AS (
        SELECT date_trunc($1, to_date(sa."Create_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM(sa."Created_Duration"), 0)::float8 AS created_duration
        FROM scoped_assets sa GROUP BY 1
      ),
      published AS (
        SELECT date_trunc($1, to_date(sp."Publish_Date", 'YYYY-MM-DD'))::date AS period, COALESCE(SUM(sp."Published_Duration"), 0)::float8 AS published_duration
        FROM scoped_posts sp GROUP BY 1
      )
      SELECT c.period,
        CASE WHEN c.created_duration = 0 THEN 0 ELSE (COALESCE(p.published_duration, 0) / c.created_duration) * 100 END AS value
      FROM created c LEFT JOIN published p ON p.period = c.period ORDER BY c.period;
    `,
    waste_index: `${scopedVideosCte}
      , created AS (
        SELECT date_trunc($1, to_date(sa."Create_Date", 'YYYY-MM-DD'))::date AS period,
        COALESCE(AVG(sa."Created_Duration"), 0)::float8 AS avg_created_duration
        FROM scoped_assets sa GROUP BY 1
      ),
      published AS (
        SELECT date_trunc($1, to_date(sp."Publish_Date", 'YYYY-MM-DD'))::date AS period,
        COALESCE(AVG(sp."Published_Duration"), 0)::float8 AS avg_published_duration
        FROM scoped_posts sp GROUP BY 1
      )
      SELECT c.period, (c.avg_created_duration - COALESCE(p.avg_published_duration, 0))::float8 AS value
      FROM created c LEFT JOIN published p ON p.period = c.period ORDER BY c.period;
    `,
  };

  return metricSql[metric] || metricSql.uploaded_count;
}

function buildFunnelFilter(dimension, value, startIndex = 1, auth = null) {
  const accessFilter = buildAccessFilter(auth, startIndex, 'rv');
  const params = [...accessFilter.params];
  const predicates = [...accessFilter.predicates];
  const joinParts = [];

  if (accessFilter.join) {
    joinParts.push(accessFilter.join);
  }

  let nextIndex = accessFilter.nextIndex;

  if (dimension && value) {
    if (dimension === 'channel') {
      joinParts.push('LEFT JOIN raw_video_channel rvc_filter ON rv."Video_ID" = rvc_filter."Video_ID"');
      predicates.push(`rvc_filter."Channel_Name" = $${nextIndex}`);
      params.push(value);
      nextIndex += 1;
    }
    if (dimension === 'input_type') {
      predicates.push(`rv."Input_Type" = $${nextIndex}`);
      params.push(value);
      nextIndex += 1;
    }
    if (dimension === 'language') {
      predicates.push(`rv."Language" = $${nextIndex}`);
      params.push(value);
      nextIndex += 1;
    }
    if (dimension === 'user') {
      joinParts.push('LEFT JOIN users u_filter ON rv."User_ID" = u_filter."User_ID"');
      predicates.push(`u_filter."User_Name" = $${nextIndex}`);
      params.push(value);
      nextIndex += 1;
    }
    if (dimension === 'output_type') {
      joinParts.push('LEFT JOIN created_assets ca_filter ON ca_filter."Video_ID" = rv."Video_ID"');
      predicates.push(`ca_filter."Output_Type" = $${nextIndex}`);
      params.push(value);
      nextIndex += 1;
    }
  }

  return {
    join:      joinParts.join('\n'),
    where:     buildWhereClause(predicates),
    params,
    nextIndex,
  };
}

module.exports = {
  METRIC_SQL,
  DIMENSION_MAP,
  MEASURE_MAP,
  DATE_FIELD_MAP,
  ANALYTICS_BASE_FROM,
  getTrendInsights,
  buildAccessFilter,
  buildWhereClause,
  getMetricQuery,
  buildFunnelFilter,
};
