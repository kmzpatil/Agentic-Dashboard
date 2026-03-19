/**
 * Shared filter utilities used by Trends and Metrics tabs.
 */

export function parseIsoDate(value) {
  if (!value) return null;
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return null;
  return new Date(Date.UTC(year, month - 1, day));
}

export function enumerateDates(startIso, endIso) {
  const start = parseIsoDate(startIso);
  const end = parseIsoDate(endIso);
  if (!start || !end || start > end) return [];

  const dates = [];
  const cursor = new Date(start);
  while (cursor <= end) {
    dates.push(cursor.toISOString().slice(0, 10));
    cursor.setUTCDate(cursor.getUTCDate() + 1);
    if (dates.length > 5000) break;
  }
  return dates;
}

export function buildFilterParams(filters) {
  const params = new URLSearchParams();

  const appendMulti = (key, value) => {
    if (Array.isArray(value)) {
      value.forEach((v) => {
        if (v !== "All") params.append(key, v);
      });
    } else if (value && value !== "All") {
      params.append(key, value);
    }
  };

  appendMulti("company", filters.company);
  appendMulti("channel", filters.channel);
  appendMulti("user", filters.user);
  appendMulti("language", filters.language);
  appendMulti("input_type", filters.inputType);
  appendMulti("output_type", filters.outputType);

  if (filters.dateFrom) params.set("date_from", filters.dateFrom);
  if (filters.dateTo) params.set("date_to", filters.dateTo);
  return params.toString();
}

export function toOptionList(values = []) {
  return values.map((value) => ({ value, label: value }));
}
