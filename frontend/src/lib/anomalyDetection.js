/**
 * Client-side anomaly detection using Z-score analysis.
 * Ported from backend/queries/analytics_shared.py get_trend_insights().
 */

export function detectAnomalies(
  points,
  { valueKey = "value", periodKey = "period", threshold = 1.5 } = {},
) {
  if (points.length < 3) return [];

  const values = points.map((p) => Number(p[valueKey] || 0));
  const mean = values.reduce((s, v) => s + v, 0) / values.length;
  const variance =
    values.reduce((s, v) => s + (v - mean) ** 2, 0) / values.length;
  const std = Math.sqrt(variance);
  if (std === 0) return [];

  return points
    .map((p) => {
      const value = Number(p[valueKey] || 0);
      const z = (value - mean) / std;
      return { period: p[periodKey], value, zScore: z };
    })
    .filter((p) => Math.abs(p.zScore) >= threshold)
    .sort((a, b) => Math.abs(b.zScore) - Math.abs(a.zScore))
    .slice(0, 8)
    .map((p) => ({
      ...p,
      zScore: Math.round(p.zScore * 100) / 100,
      value: Math.round(p.value * 100) / 100,
      severity: Math.abs(p.zScore) >= 2.5 ? "high" : "medium",
      direction: p.zScore > 0 ? "spike" : "drop",
    }));
}
