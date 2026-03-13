const express = require('express');

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

function createApiRouter(pool) {
  const router = express.Router();

  router.get('/health', async (_req, res) => {
    try {
      await pool.query('SELECT 1');
      res.json({ ok: true });
    } catch (error) {
      res.status(500).json({ ok: false, error: error.message });
    }
  });

  router.get('/overview', async (_req, res) => {
    try {
      const [kpiResult, channelResult, userResult, inputResult, outputResult, langResult, alertResult] = await Promise.all([
        pool.query(`
        WITH uploaded AS (
          SELECT COUNT(*)::int AS count, COALESCE(SUM("Uploaded_Duration"), 0)::float8 AS duration
          FROM raw_videos
        ),
        processed AS (
          SELECT COUNT(DISTINCT "Video_ID")::int AS count
          FROM created_assets
        ),
        created AS (
          SELECT COUNT(*)::int AS count, COALESCE(SUM("Created_Duration"), 0)::float8 AS duration, COALESCE(AVG("Created_Duration"), 0)::float8 AS avg_duration
          FROM created_assets
        ),
        published AS (
          SELECT COUNT(*)::int AS count, COALESCE(SUM("Published_Duration"), 0)::float8 AS duration, COALESCE(AVG("Published_Duration"), 0)::float8 AS avg_duration
          FROM published_posts
        )
        SELECT
          u.count AS uploaded_count,
          u.duration AS uploaded_duration,
          p.count AS processed_count,
          c.count AS created_count,
          c.duration AS created_duration,
          pb.count AS published_count,
          pb.duration AS published_duration,
          CASE WHEN c.count = 0 THEN 0 ELSE (pb.count::float8 / c.count) * 100 END AS publish_conversion_rate,
          CASE WHEN c.duration = 0 THEN 0 ELSE (pb.duration / c.duration) * 100 END AS processing_efficiency,
          CASE WHEN u.count = 0 THEN 0 ELSE (c.count::float8 / u.count) * 100 END AS creation_rate,
          (c.avg_duration - pb.avg_duration) AS waste_index
        FROM uploaded u, processed p, created c, published pb;
      `),
        pool.query(`
        SELECT rvc."Channel_Name" AS label,
               COUNT(DISTINCT ca."Asset_ID")::int AS created_count,
               COUNT(DISTINCT pp."Post_ID")::int AS published_count,
               CASE WHEN COUNT(DISTINCT ca."Asset_ID") = 0 THEN 0
                 ELSE (COUNT(DISTINCT pp."Post_ID")::float8 / COUNT(DISTINCT ca."Asset_ID")) * 100 END AS conversion
        FROM raw_video_channel rvc
        LEFT JOIN created_assets ca ON rvc."Video_ID" = ca."Video_ID"
        LEFT JOIN published_posts pp ON ca."Asset_ID" = pp."Asset_ID"
        GROUP BY rvc."Channel_Name"
        HAVING COUNT(DISTINCT ca."Asset_ID") > 5
        ORDER BY conversion DESC, published_count DESC
        LIMIT 1;
      `),
        pool.query(`
        SELECT u."User_Name" AS label,
               COUNT(DISTINCT ca."Asset_ID")::int AS created_count,
               COUNT(DISTINCT pp."Post_ID")::int AS published_count,
               CASE WHEN COUNT(DISTINCT ca."Asset_ID") = 0 THEN 0
                 ELSE (COUNT(DISTINCT pp."Post_ID")::float8 / COUNT(DISTINCT ca."Asset_ID")) * 100 END AS conversion
        FROM users u
        JOIN raw_videos rv ON rv."User_ID" = u."User_ID"
        LEFT JOIN created_assets ca ON rv."Video_ID" = ca."Video_ID"
        LEFT JOIN published_posts pp ON ca."Asset_ID" = pp."Asset_ID"
        GROUP BY u."User_Name"
        HAVING COUNT(DISTINCT ca."Asset_ID") > 5
        ORDER BY conversion DESC, published_count DESC
        LIMIT 1;
      `),
        pool.query(`
        SELECT rv."Input_Type" AS label,
               COUNT(DISTINCT ca."Asset_ID")::int AS created_count,
               COUNT(DISTINCT pp."Post_ID")::int AS published_count,
               CASE WHEN COUNT(DISTINCT ca."Asset_ID") = 0 THEN 0
                 ELSE (COUNT(DISTINCT pp."Post_ID")::float8 / COUNT(DISTINCT ca."Asset_ID")) * 100 END AS conversion
        FROM raw_videos rv
        LEFT JOIN created_assets ca ON rv."Video_ID" = ca."Video_ID"
        LEFT JOIN published_posts pp ON ca."Asset_ID" = pp."Asset_ID"
        GROUP BY rv."Input_Type"
        HAVING COUNT(DISTINCT ca."Asset_ID") > 5
        ORDER BY conversion DESC, published_count DESC
        LIMIT 1;
      `),
        pool.query(`
        SELECT ca."Output_Type" AS label,
               COUNT(DISTINCT ca."Asset_ID")::int AS created_count,
               COUNT(DISTINCT pp."Post_ID")::int AS published_count,
               CASE WHEN COUNT(DISTINCT ca."Asset_ID") = 0 THEN 0
                 ELSE (COUNT(DISTINCT pp."Post_ID")::float8 / COUNT(DISTINCT ca."Asset_ID")) * 100 END AS conversion
        FROM created_assets ca
        LEFT JOIN published_posts pp ON ca."Asset_ID" = pp."Asset_ID"
        GROUP BY ca."Output_Type"
        HAVING COUNT(DISTINCT ca."Asset_ID") > 5
        ORDER BY conversion DESC, published_count DESC
        LIMIT 1;
      `),
        pool.query(`
        SELECT rv."Language" AS label,
               COUNT(DISTINCT ca."Asset_ID")::int AS created_count,
               COUNT(DISTINCT pp."Post_ID")::int AS published_count,
               CASE WHEN COUNT(DISTINCT ca."Asset_ID") = 0 THEN 0
                 ELSE (COUNT(DISTINCT pp."Post_ID")::float8 / COUNT(DISTINCT ca."Asset_ID")) * 100 END AS conversion
        FROM raw_videos rv
        LEFT JOIN created_assets ca ON rv."Video_ID" = ca."Video_ID"
        LEFT JOIN published_posts pp ON ca."Asset_ID" = pp."Asset_ID"
        GROUP BY rv."Language"
        HAVING COUNT(DISTINCT ca."Asset_ID") > 5
        ORDER BY conversion DESC, published_count DESC
        LIMIT 1;
      `),
        pool.query(`
        SELECT rvc."Channel_Name" AS channel_name,
               COUNT(DISTINCT ca."Asset_ID")::int AS created_count,
               COUNT(DISTINCT pp."Post_ID")::int AS published_count,
               CASE WHEN COUNT(DISTINCT ca."Asset_ID") = 0 THEN 0
                 ELSE (COUNT(DISTINCT pp."Post_ID")::float8 / COUNT(DISTINCT ca."Asset_ID")) * 100 END AS conversion
        FROM raw_video_channel rvc
        LEFT JOIN created_assets ca ON rvc."Video_ID" = ca."Video_ID"
        LEFT JOIN published_posts pp ON ca."Asset_ID" = pp."Asset_ID"
        GROUP BY rvc."Channel_Name"
        HAVING COUNT(DISTINCT ca."Asset_ID") > 5
        ORDER BY conversion ASC, created_count DESC
        LIMIT 5;
      `),
      ]);

      const kpis = kpiResult.rows[0];

      const topPerformers = [
        { dimension: 'Channel', ...(channelResult.rows[0] || {}) },
        { dimension: 'User', ...(userResult.rows[0] || {}) },
        { dimension: 'Input Type', ...(inputResult.rows[0] || {}) },
        { dimension: 'Output Type', ...(outputResult.rows[0] || {}) },
        { dimension: 'Language', ...(langResult.rows[0] || {}) },
      ].filter((item) => item.label);

      const alerts = alertResult.rows.map((row) => ({
        title: `${row.channel_name}: ${Number(row.conversion).toFixed(2)}% conversion`,
        subtitle: `${row.created_count} created, ${row.published_count} published`,
        severity: Number(row.conversion) < 0.5 ? 'critical' : 'warning',
      }));

      res.json({ kpis, topPerformers, alerts });
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  });

  router.get('/usage-trends', async (req, res) => {
    const granularity = ['day', 'week', 'month', 'quarter'].includes(req.query.granularity)
      ? req.query.granularity
      : 'month';

    const metric = Object.prototype.hasOwnProperty.call(METRIC_SQL, req.query.metric)
      ? req.query.metric
      : 'uploaded_count';

    try {
      const { rows } = await pool.query(METRIC_SQL[metric], [granularity]);
      const points = rows.map((r) => ({
        period: r.period,
        value: Number(r.value || 0),
      }));

      const latest = points[points.length - 1] || null;
      const previous = points[points.length - 2] || null;
      const deltaPct = latest && previous && previous.value !== 0
        ? ((latest.value - previous.value) / previous.value) * 100
        : null;

      res.json({
        metric,
        granularity,
        series: points,
        summary: {
          latestValue: latest ? Number(latest.value.toFixed(2)) : 0,
          latestPeriod: latest?.period || null,
          deltaVsPreviousPct: deltaPct === null ? null : Number(deltaPct.toFixed(2)),
        },
        anomalies: getTrendInsights(points),
      });
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  });

  router.get('/funnel', async (req, res) => {
    const dimension = req.query.dimension;
    const value = req.query.value;
    const breakdownDimension = ['channel', 'input_type', 'language', 'output_type'].includes(req.query.breakdown)
      ? req.query.breakdown
      : 'channel';

    const filter = buildFunnelFilter(dimension, value, 1);

    try {
      const funnelSql = `
      WITH filtered_videos AS (
        SELECT DISTINCT rv."Video_ID"
        FROM raw_videos rv
        ${filter.join}
        ${filter.where}
      ),
      processed AS (
        SELECT DISTINCT ca."Video_ID"
        FROM created_assets ca
        JOIN filtered_videos fv ON fv."Video_ID" = ca."Video_ID"
      ),
      created AS (
        SELECT ca."Asset_ID"
        FROM created_assets ca
        JOIN filtered_videos fv ON fv."Video_ID" = ca."Video_ID"
      ),
      published AS (
        SELECT pp."Post_ID"
        FROM published_posts pp
        JOIN created c ON c."Asset_ID" = pp."Asset_ID"
      )
      SELECT
        (SELECT COUNT(*)::int FROM filtered_videos) AS uploaded_count,
        (SELECT COUNT(*)::int FROM processed) AS processed_count,
        (SELECT COUNT(*)::int FROM created) AS created_count,
        (SELECT COUNT(*)::int FROM published) AS published_count;
    `;

      const stageCounts = (await pool.query(funnelSql, filter.params)).rows[0];

      const breakdownExprMap = {
        channel: 'rvc."Channel_Name"',
        input_type: 'rv."Input_Type"',
        language: 'rv."Language"',
        output_type: 'ca."Output_Type"',
      };

      const breakdownSql = `
      WITH filtered_videos AS (
        SELECT DISTINCT rv."Video_ID"
        FROM raw_videos rv
        ${filter.join}
        ${filter.where}
      )
      SELECT ${breakdownExprMap[breakdownDimension]} AS label,
        COUNT(DISTINCT rv."Video_ID")::int AS uploaded_count,
        COUNT(DISTINCT ca."Asset_ID")::int AS created_count,
        COUNT(DISTINCT pp."Post_ID")::int AS published_count,
        CASE WHEN COUNT(DISTINCT ca."Asset_ID") = 0 THEN 0
          ELSE (COUNT(DISTINCT pp."Post_ID")::float8 / COUNT(DISTINCT ca."Asset_ID")) * 100 END AS conversion
      FROM filtered_videos fv
      JOIN raw_videos rv ON rv."Video_ID" = fv."Video_ID"
      LEFT JOIN raw_video_channel rvc ON rvc."Video_ID" = rv."Video_ID"
      LEFT JOIN created_assets ca ON ca."Video_ID" = rv."Video_ID"
      LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
      GROUP BY 1
      ORDER BY conversion DESC, uploaded_count DESC
      LIMIT 30;
    `;

      const breakdown = (await pool.query(breakdownSql, filter.params)).rows.map((row) => ({
        ...row,
        conversion: Number(Number(row.conversion || 0).toFixed(2)),
      }));

      const compositionSql = `
      WITH filtered_videos AS (
        SELECT DISTINCT rv."Video_ID"
        FROM raw_videos rv
        ${filter.join}
        ${filter.where}
      ),
      input_data AS (
        SELECT rv."Input_Type" AS input_type, COUNT(DISTINCT rv."Video_ID")::int AS uploaded_count
        FROM filtered_videos fv
        JOIN raw_videos rv ON rv."Video_ID" = fv."Video_ID"
        GROUP BY rv."Input_Type"
      ),
      input_output AS (
        SELECT rv."Input_Type" AS input_type,
               ca."Output_Type" AS output_type,
               COUNT(ca."Asset_ID")::int AS created_count
        FROM filtered_videos fv
        JOIN raw_videos rv ON rv."Video_ID" = fv."Video_ID"
        JOIN created_assets ca ON ca."Video_ID" = rv."Video_ID"
        GROUP BY rv."Input_Type", ca."Output_Type"
      ),
      output_publish AS (
        SELECT ca."Output_Type" AS output_type,
               SUM(CASE WHEN pp."Post_ID" IS NOT NULL THEN 1 ELSE 0 END)::int AS published_count,
               SUM(CASE WHEN pp."Post_ID" IS NULL THEN 1 ELSE 0 END)::int AS unpublished_count
        FROM filtered_videos fv
        JOIN created_assets ca ON ca."Video_ID" = fv."Video_ID"
        LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
        GROUP BY ca."Output_Type"
      )
      SELECT 'uploaded_to_input' AS edge_type,
             'Uploaded' AS edge_from,
             ('Input: ' || COALESCE(input_type, 'Unknown')) AS edge_to,
             uploaded_count::float8 AS flow
      FROM input_data
      UNION ALL
      SELECT 'input_to_output',
             ('Input: ' || COALESCE(input_type, 'Unknown')),
             ('Output: ' || COALESCE(output_type, 'Unknown')),
             created_count::float8
      FROM input_output
      UNION ALL
      SELECT 'output_to_published',
             ('Output: ' || COALESCE(output_type, 'Unknown')),
             'Published',
             published_count::float8
      FROM output_publish
      UNION ALL
      SELECT 'output_to_unpublished',
             ('Output: ' || COALESCE(output_type, 'Unknown')),
             'Not Published',
             unpublished_count::float8
      FROM output_publish;
    `;

      const compositionEdgesRaw = (await pool.query(compositionSql, filter.params)).rows;
      const compositionLinks = compositionEdgesRaw
        .filter((row) => Number(row.flow) > 0)
        .sort((a, b) => Number(b.flow) - Number(a.flow))
        .slice(0, 120)
        .map((row) => ({
          from: row.edge_from,
          to: row.edge_to,
          flow: Number(row.flow),
          edgeType: row.edge_type,
        }));

      const journeySql = `
      WITH filtered_videos AS (
        SELECT DISTINCT rv."Video_ID"
        FROM raw_videos rv
        ${filter.join}
        ${filter.where}
      )
      SELECT rv."Video_ID" AS video_id,
             rv."Headline" AS headline,
             rv."Input_Type" AS input_type,
             rv."Language" AS language,
             rv."Upload_Date" AS upload_date,
             COUNT(DISTINCT rvc."Channel_Name")::int AS channel_count,
             COUNT(DISTINCT ca."Asset_ID")::int AS created_assets,
             COUNT(DISTINCT pp."Post_ID")::int AS published_posts,
             CASE WHEN COUNT(DISTINCT ca."Asset_ID") = 0 THEN 0
               ELSE (COUNT(DISTINCT pp."Post_ID")::float8 / COUNT(DISTINCT ca."Asset_ID")) * 100 END AS conversion
      FROM filtered_videos fv
      JOIN raw_videos rv ON rv."Video_ID" = fv."Video_ID"
      LEFT JOIN raw_video_channel rvc ON rvc."Video_ID" = rv."Video_ID"
      LEFT JOIN created_assets ca ON ca."Video_ID" = rv."Video_ID"
      LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
      GROUP BY rv."Video_ID", rv."Headline", rv."Input_Type", rv."Language", rv."Upload_Date"
      ORDER BY created_assets DESC, published_posts DESC, rv."Video_ID" DESC
      LIMIT 100;
    `;

      const journeyRows = (await pool.query(journeySql, filter.params)).rows;

      const mixRows = (await pool.query(`
      WITH filtered_videos AS (
        SELECT DISTINCT rv."Video_ID"
        FROM raw_videos rv
        ${filter.join}
        ${filter.where}
      )
      SELECT rv."Video_ID" AS video_id,
             COALESCE(ca."Output_Type", 'Unknown') AS output_type,
             COUNT(ca."Asset_ID")::int AS created_count,
             COUNT(pp."Post_ID")::int AS published_count
      FROM filtered_videos fv
      JOIN raw_videos rv ON rv."Video_ID" = fv."Video_ID"
      LEFT JOIN created_assets ca ON ca."Video_ID" = rv."Video_ID"
      LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
      GROUP BY rv."Video_ID", COALESCE(ca."Output_Type", 'Unknown')
      ORDER BY rv."Video_ID";
    `, filter.params)).rows;

      const mixByVideo = new Map();
      mixRows.forEach((row) => {
        const key = Number(row.video_id);
        if (!mixByVideo.has(key)) {
          mixByVideo.set(key, []);
        }
        mixByVideo.get(key).push(`${row.output_type}: ${row.published_count}/${row.created_count}`);
      });

      const journeyVideos = journeyRows.map((row) => ({
        ...row,
        conversion: Number(Number(row.conversion || 0).toFixed(2)),
        output_mix: (mixByVideo.get(Number(row.video_id)) || []).slice(0, 4),
      }));

      res.json({
        filter: { dimension: dimension || null, value: value || null },
        stageCounts,
        sankeyLinks: [
          { from: 'Uploaded', to: 'Processed', flow: Number(stageCounts.processed_count) },
          { from: 'Processed', to: 'Created', flow: Number(stageCounts.created_count) },
          { from: 'Created', to: 'Published', flow: Number(stageCounts.published_count) },
        ],
        compositionLinks,
        breakdownDimension,
        breakdown,
        journeyVideos,
      });
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  });

  router.get('/funnel/video/:videoId', async (req, res) => {
    const videoId = Number(req.params.videoId);
    if (Number.isNaN(videoId)) {
      return res.status(400).json({ error: 'Invalid video id' });
    }

    try {
      const headerResult = await pool.query(`
      SELECT rv."Video_ID" AS video_id,
             rv."Headline" AS headline,
             rv."Input_Type" AS input_type,
             rv."Language" AS language,
             rv."Upload_Date" AS upload_date,
             rv."Uploaded_Duration" AS uploaded_duration,
             ARRAY_REMOVE(ARRAY_AGG(DISTINCT rvc."Channel_Name"), NULL) AS channels
      FROM raw_videos rv
      LEFT JOIN raw_video_channel rvc ON rvc."Video_ID" = rv."Video_ID"
      WHERE rv."Video_ID" = $1
      GROUP BY rv."Video_ID", rv."Headline", rv."Input_Type", rv."Language", rv."Upload_Date", rv."Uploaded_Duration";
    `, [videoId]);

      if (headerResult.rowCount === 0) {
        return res.status(404).json({ error: 'Video not found' });
      }

      const assetsResult = await pool.query(`
      SELECT ca."Asset_ID" AS asset_id,
             ca."Output_Type" AS output_type,
             ca."Create_Date" AS create_date,
             ca."Created_Duration" AS created_duration,
             pp."Post_ID" AS post_id,
             pp."Publish_Date" AS publish_date,
             pp."Published_Duration" AS published_duration,
             ARRAY_REMOVE(ARRAY_AGG(DISTINCT pd."Published_Platform"), NULL) AS platforms
      FROM created_assets ca
      LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
      LEFT JOIN post_distribution pd ON pd."Post_ID" = pp."Post_ID"
      WHERE ca."Video_ID" = $1
      GROUP BY ca."Asset_ID", ca."Output_Type", ca."Create_Date", ca."Created_Duration", pp."Post_ID", pp."Publish_Date", pp."Published_Duration"
      ORDER BY ca."Asset_ID";
    `, [videoId]);

      return res.json({
        video: headerResult.rows[0],
        assets: assetsResult.rows,
      });
    } catch (error) {
      return res.status(500).json({ error: error.message });
    }
  });

  router.get('/explorer/dimensions', async (_req, res) => {
    res.json({
      dimensions: [
        { key: 'channel', label: 'Channel' },
        { key: 'language', label: 'Language' },
        { key: 'input_type', label: 'Input Type' },
        { key: 'output_type', label: 'Output Type' },
        { key: 'user', label: 'User' },
        { key: 'client', label: 'Client' },
        { key: 'published_platform', label: 'Published Platform' },
      ],
      measures: [
        { key: 'uploaded_videos', label: 'Uploaded Videos (distinct)' },
        { key: 'created_assets', label: 'Created Assets (distinct)' },
        { key: 'published_posts', label: 'Published Posts (distinct)' },
      ],
      dateFields: [
        { key: 'upload_date', label: 'Upload Date' },
        { key: 'create_date', label: 'Create Date' },
        { key: 'publish_date', label: 'Publish Date' },
      ],
    });
  });

  router.get('/explorer/multidim', async (req, res) => {
    const dim1 = DIMENSION_MAP[req.query.dim1] ? req.query.dim1 : 'channel';
    const dim2 = DIMENSION_MAP[req.query.dim2] ? req.query.dim2 : 'language';
    const measure = MEASURE_MAP[req.query.measure] ? req.query.measure : 'uploaded_videos';
    const timeGrain = ['none', 'day', 'week', 'month'].includes(req.query.timeGrain) ? req.query.timeGrain : 'none';
    const dateField = DATE_FIELD_MAP[req.query.dateField] ? req.query.dateField : 'upload_date';
    const dim1Value = req.query.dim1Value || '';

    const dim1Expr = DIMENSION_MAP[dim1];
    const dim2Expr = DIMENSION_MAP[dim2];
    const measureExpr = MEASURE_MAP[measure];
    const dateExpr = DATE_FIELD_MAP[dateField];

    try {
      const matrixParams = [];
      const matrixWhere = [];

      if (dim1Value) {
        matrixParams.push(dim1Value);
        matrixWhere.push(`${dim1Expr}::text = $${matrixParams.length}`);
      }

      const matrixSql = `
      SELECT COALESCE(${dim1Expr}::text, 'Unknown') AS dim1,
             COALESCE(${dim2Expr}::text, 'Unknown') AS dim2,
             ${measureExpr} AS value
      ${ANALYTICS_BASE_FROM}
      ${matrixWhere.length ? `WHERE ${matrixWhere.join(' AND ')}` : ''}
      GROUP BY 1, 2
      ORDER BY value DESC
      LIMIT 600;
    `;

      const matrixRows = (await pool.query(matrixSql, matrixParams)).rows.map((row) => ({
        dim1: row.dim1,
        dim2: row.dim2,
        value: Number(row.value || 0),
      }));

      const dim1Values = [...new Set(matrixRows.map((row) => row.dim1))].slice(0, 60);
      const dim2Values = [...new Set(matrixRows.map((row) => row.dim2))].slice(0, 30);

      let timeSeriesRows = [];
      if (timeGrain !== 'none') {
        const tsParams = [timeGrain];
        const tsWhere = [`${dateExpr} IS NOT NULL`];

        if (dim1Value) {
          tsParams.push(dim1Value);
          tsWhere.push(`${dim1Expr}::text = $${tsParams.length}`);
        }

        const tsSql = `
        SELECT date_trunc($1, ${dateExpr})::date AS period,
               COALESCE(${dim2Expr}::text, 'Unknown') AS dim2,
               ${measureExpr} AS value
        ${ANALYTICS_BASE_FROM}
        WHERE ${tsWhere.join(' AND ')}
        GROUP BY 1, 2
        ORDER BY 1, 2;
      `;

        timeSeriesRows = (await pool.query(tsSql, tsParams)).rows.map((row) => ({
          period: row.period,
          dim2: row.dim2,
          value: Number(row.value || 0),
        }));
      }

      return res.json({
        dim1,
        dim2,
        measure,
        timeGrain,
        dateField,
        dim1Value: dim1Value || null,
        matrixRows,
        dim1Values,
        dim2Values,
        timeSeriesRows,
      });
    } catch (error) {
      return res.status(500).json({ error: error.message });
    }
  });

  router.get('/explorer/tables', async (_req, res) => {
    try {
      const { rows } = await pool.query(`
      SELECT tablename
      FROM pg_tables
      WHERE schemaname = 'public'
      ORDER BY tablename;
    `);

      res.json({ tables: rows.map((r) => r.tablename) });
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  });

  router.get('/explorer/table/:tableName', async (req, res) => {
    const tableName = req.params.tableName;
    const limit = Math.min(Number(req.query.limit || 100), 500);

    try {
      const tableCheck = await pool.query(
        'SELECT tablename FROM pg_tables WHERE schemaname = \'public\' AND tablename = $1',
        [tableName],
      );

      if (tableCheck.rowCount === 0) {
        return res.status(404).json({ error: 'Table not found' });
      }

      const columnsResult = await pool.query(
        'SELECT column_name FROM information_schema.columns WHERE table_schema=\'public\' AND table_name=$1 ORDER BY ordinal_position',
        [tableName],
      );

      const quotedTableName = `"${tableName.replace(/"/g, '""')}"`;
      const dataResult = await pool.query(`SELECT * FROM ${quotedTableName} LIMIT ${limit}`);

      return res.json({
        table: tableName,
        columns: columnsResult.rows.map((r) => r.column_name),
        rows: dataResult.rows,
      });
    } catch (error) {
      return res.status(500).json({ error: error.message });
    }
  });

  router.get('/explorer/chart', async (req, res) => {
    const { table, x, y, aggregation = 'count' } = req.query;

    if (!table || !x) {
      return res.status(400).json({ error: 'table and x are required' });
    }

    try {
      const tableCheck = await pool.query(
        'SELECT tablename FROM pg_tables WHERE schemaname=\'public\' AND tablename=$1',
        [table],
      );

      if (tableCheck.rowCount === 0) {
        return res.status(404).json({ error: 'Invalid table' });
      }

      const columnsResult = await pool.query(
        'SELECT column_name FROM information_schema.columns WHERE table_schema=\'public\' AND table_name=$1',
        [table],
      );

      const validColumns = new Set(columnsResult.rows.map((r) => r.column_name));

      if (!validColumns.has(x)) {
        return res.status(400).json({ error: 'Invalid x column' });
      }

      if (aggregation === 'sum') {
        if (!y || !validColumns.has(y)) {
          return res.status(400).json({ error: 'Valid numeric y column required for sum aggregation' });
        }

        const sql = `
        SELECT "${x.replace(/"/g, '""')}"::text AS label,
               COALESCE(SUM("${y.replace(/"/g, '""')}"), 0)::float8 AS value
        FROM "${table.replace(/"/g, '""')}"
        GROUP BY 1
        ORDER BY value DESC
        LIMIT 30;
      `;
        const result = await pool.query(sql);
        return res.json({ rows: result.rows });
      }

      const sql = `
      SELECT "${x.replace(/"/g, '""')}"::text AS label,
             COUNT(*)::float8 AS value
      FROM "${table.replace(/"/g, '""')}"
      GROUP BY 1
      ORDER BY value DESC
      LIMIT 30;
    `;

      const result = await pool.query(sql);
      return res.json({ rows: result.rows });
    } catch (error) {
      return res.status(500).json({ error: error.message });
    }
  });

  return router;
}

module.exports = {
  createApiRouter,
};
