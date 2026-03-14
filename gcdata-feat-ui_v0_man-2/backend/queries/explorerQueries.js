const TABLES_QUERY = `
  SELECT tablename
  FROM pg_tables
  WHERE schemaname = 'public'
  ORDER BY tablename;
`;

const TABLE_EXISTS_QUERY = 'SELECT tablename FROM pg_tables WHERE schemaname = \'public\' AND tablename = $1';
const TABLE_COLUMNS_QUERY = 'SELECT column_name FROM information_schema.columns WHERE table_schema=\'public\' AND table_name=$1 ORDER BY ordinal_position';

function getMatrixQuery(dim1Expr, dim2Expr, measureExpr, scopeJoin, matrixWhereClause) {
  return `
    SELECT COALESCE(${dim1Expr}::text, 'Unknown') AS dim1,
           COALESCE(${dim2Expr}::text, 'Unknown') AS dim2,
           ${measureExpr} AS value
    FROM raw_videos rv
    ${scopeJoin}
    LEFT JOIN raw_video_channel rvc ON rvc."Video_ID" = rv."Video_ID"
    LEFT JOIN channels ch ON ch."Channel_Name" = rvc."Channel_Name"
    LEFT JOIN users u ON u."User_ID" = rv."User_ID"
    LEFT JOIN created_assets ca ON ca."Video_ID" = rv."Video_ID"
    LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
    LEFT JOIN post_distribution pd ON pd."Post_ID" = pp."Post_ID"
    ${matrixWhereClause}
    GROUP BY 1, 2
    ORDER BY value DESC
    LIMIT 600;
  `;
}

function getTimeSeriesQuery(dateExpr, dim2Expr, measureExpr, scopeJoin, tsWhereClause) {
  return `
    SELECT date_trunc($1, ${dateExpr})::date AS period,
           COALESCE(${dim2Expr}::text, 'Unknown') AS dim2,
           ${measureExpr} AS value
    FROM raw_videos rv
    ${scopeJoin}
    LEFT JOIN raw_video_channel rvc ON rvc."Video_ID" = rv."Video_ID"
    LEFT JOIN channels ch ON ch."Channel_Name" = rvc."Channel_Name"
    LEFT JOIN users u ON u."User_ID" = rv."User_ID"
    LEFT JOIN created_assets ca ON ca."Video_ID" = rv."Video_ID"
    LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
    LEFT JOIN post_distribution pd ON pd."Post_ID" = pp."Post_ID"
    WHERE ${tsWhereClause}
    GROUP BY 1, 2
    ORDER BY 1, 2;
  `;
}

function getTableDataQuery(tableName, limit) {
  const quotedTableName = `"${tableName.replace(/"/g, '""')}"`;
  return `SELECT * FROM ${quotedTableName} LIMIT ${limit}`;
}

function getSumChartQuery(table, x, y) {
  return `
    SELECT "${x.replace(/"/g, '""')}"::text AS label,
           COALESCE(SUM("${y.replace(/"/g, '""')}"), 0)::float8 AS value
    FROM "${table.replace(/"/g, '""')}"
    GROUP BY 1
    ORDER BY value DESC
    LIMIT 30;
  `;
}

function getCountChartQuery(table, x) {
  return `
    SELECT "${x.replace(/"/g, '""')}"::text AS label,
           COUNT(*)::float8 AS value
    FROM "${table.replace(/"/g, '""')}"
    GROUP BY 1
    ORDER BY value DESC
    LIMIT 30;
  `;
}

module.exports = {
  TABLES_QUERY,
  TABLE_EXISTS_QUERY,
  TABLE_COLUMNS_QUERY,
  getMatrixQuery,
  getTimeSeriesQuery,
  getTableDataQuery,
  getSumChartQuery,
  getCountChartQuery,
};
