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
  channel: 'rvc."Channel_Name"',
  language: 'rv."Language"',
  input_type: 'rv."Input_Type"',
  output_type: 'ca."Output_Type"',
  user: 'u."User_Name"',
  client: 'COALESCE(ch."Client_Name", u."Client_Name")',
  published_platform: 'pd."Published_Platform"',
};

const MEASURE_MAP = {
  uploaded_videos: 'COUNT(DISTINCT rv."Video_ID")::float8',
  created_assets: 'COUNT(DISTINCT ca."Asset_ID")::float8',
  published_posts: 'COUNT(DISTINCT pp."Post_ID")::float8',
};

const DATE_FIELD_MAP = {
  upload_date: "to_date(rv.\"Upload_Date\", 'YYYY-MM-DD')",
  create_date: "to_date(ca.\"Create_Date\", 'YYYY-MM-DD')",
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
      period: p.period,
      value: Number(p.value.toFixed(2)),
      zScore: Number(p.z.toFixed(2)),
      severity: Math.abs(p.z) >= 2.5 ? 'high' : 'medium',
      direction: p.z > 0 ? 'spike' : 'drop',
    }));
}

function buildFunnelFilter(dimension, value, startIndex = 1) {
  if (!dimension || !value) {
    return {
      join: '',
      where: '',
      params: [],
      nextIndex: startIndex,
    };
  }

  if (dimension === 'channel') {
    return {
      join: 'LEFT JOIN raw_video_channel rvc_filter ON rv."Video_ID" = rvc_filter."Video_ID"',
      where: `WHERE rvc_filter."Channel_Name" = $${startIndex}`,
      params: [value],
      nextIndex: startIndex + 1,
    };
  }

  if (dimension === 'input_type') {
    return {
      join: '',
      where: `WHERE rv."Input_Type" = $${startIndex}`,
      params: [value],
      nextIndex: startIndex + 1,
    };
  }

  if (dimension === 'language') {
    return {
      join: '',
      where: `WHERE rv."Language" = $${startIndex}`,
      params: [value],
      nextIndex: startIndex + 1,
    };
  }

  if (dimension === 'user') {
    return {
      join: 'LEFT JOIN users u_filter ON rv."User_ID" = u_filter."User_ID"',
      where: `WHERE u_filter."User_Name" = $${startIndex}`,
      params: [value],
      nextIndex: startIndex + 1,
    };
  }

  if (dimension === 'output_type') {
    return {
      join: 'LEFT JOIN created_assets ca_filter ON ca_filter."Video_ID" = rv."Video_ID"',
      where: `WHERE ca_filter."Output_Type" = $${startIndex}`,
      params: [value],
      nextIndex: startIndex + 1,
    };
  }

  return {
    join: '',
    where: '',
    params: [],
    nextIndex: startIndex,
  };
}

module.exports = {
  METRIC_SQL,
  DIMENSION_MAP,
  MEASURE_MAP,
  DATE_FIELD_MAP,
  ANALYTICS_BASE_FROM,
  getTrendInsights,
  buildFunnelFilter,
};
