const express = require('express');

function createOverviewRouter(pool) {
  const router = express.Router();

  router.get('/', async (_req, res) => {
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

  return router;
}

module.exports = {
  createOverviewRouter,
};
