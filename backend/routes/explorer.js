const express = require('express');
const {
  DIMENSION_MAP,
  MEASURE_MAP,
  DATE_FIELD_MAP,
  ANALYTICS_BASE_FROM,
} = require('./shared/analytics');

function createExplorerRouter(pool) {
  const router = express.Router();

  router.get('/dimensions', async (_req, res) => {
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

  router.get('/multidim', async (req, res) => {
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

  router.get('/tables', async (_req, res) => {
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

  router.get('/table/:tableName', async (req, res) => {
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

  router.get('/chart', async (req, res) => {
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
  createExplorerRouter,
};
