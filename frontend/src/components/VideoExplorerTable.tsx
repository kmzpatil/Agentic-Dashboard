import { useMemo, useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  ChevronsUpDown,
  Download,
  Search,
  SlidersHorizontal,
} from "lucide-react";

type VideoStatus = "Published" | "Processed Only" | "Failed";

interface VideoRow {
  id: string;
  title: string;
  client: string;
  channel: string;
  dateProcessed: string;
  inputType: string;
  outputType: string;
  status: VideoStatus;
}

type SortKey =
  | "id"
  | "title"
  | "client"
  | "channel"
  | "dateProcessed"
  | "inputType"
  | "outputType"
  | "status";

const MOCK_ROWS: VideoRow[] = [
  {
    id: "a1f9c3",
    title: "Spring Product Launch Highlights",
    client: "Acme Media",
    channel: "Brand Pulse",
    dateProcessed: "2026-03-01",
    inputType: "Zoom",
    outputType: "YouTube Shorts",
    status: "Published",
  },
  {
    id: "b7d2e8",
    title: "CEO Townhall Recap",
    client: "Nova Studios",
    channel: "Inside Nova",
    dateProcessed: "2026-03-02",
    inputType: "Webinar",
    outputType: "Instagram Reels",
    status: "Processed Only",
  },
  {
    id: "c3ab41",
    title: "Customer Success Story: FinEdge",
    client: "BrightWorks",
    channel: "Stories",
    dateProcessed: "2026-03-03",
    inputType: "MP4 Upload",
    outputType: "LinkedIn Video",
    status: "Published",
  },
  {
    id: "d90f52",
    title: "Weekly Market Briefing",
    client: "Pulse Analytics",
    channel: "Market Now",
    dateProcessed: "2026-03-03",
    inputType: "Stream Capture",
    outputType: "YouTube",
    status: "Failed",
  },
  {
    id: "e4c8a0",
    title: "Hiring Day Q&A",
    client: "TalentSphere",
    channel: "Careers",
    dateProcessed: "2026-03-04",
    inputType: "Zoom",
    outputType: "TikTok",
    status: "Processed Only",
  },
  {
    id: "f6de13",
    title: "Engineering Demo: AI Cutdown",
    client: "Code Harbor",
    channel: "Build Log",
    dateProcessed: "2026-03-05",
    inputType: "Webinar",
    outputType: "YouTube Shorts",
    status: "Published",
  },
  {
    id: "0ab12f",
    title: "Investor Update Session",
    client: "Vertex Capital",
    channel: "Investor Desk",
    dateProcessed: "2026-03-06",
    inputType: "MP4 Upload",
    outputType: "LinkedIn Video",
    status: "Failed",
  },
  {
    id: "7ce44a",
    title: "Creator Spotlight Episode 12",
    client: "Studio Spark",
    channel: "Creator Hub",
    dateProcessed: "2026-03-07",
    inputType: "Stream Capture",
    outputType: "Instagram Reels",
    status: "Published",
  },
  {
    id: "9fa8bd",
    title: "Product FAQ Digest",
    client: "Acme Media",
    channel: "Help Center",
    dateProcessed: "2026-03-08",
    inputType: "Zoom",
    outputType: "YouTube Shorts",
    status: "Processed Only",
  },
];

const statusClasses: Record<VideoStatus, string> = {
  Published:
    "bg-emerald-950/50 text-emerald-300 border border-emerald-800/60",
  "Processed Only":
    "bg-amber-950/50 text-amber-300 border border-amber-800/60",
  Failed: "bg-red-950/50 text-red-300 border border-red-800/70",
};

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function VideoExplorerTable() {
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(5);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return MOCK_ROWS;
    return MOCK_ROWS.filter(
      (row) =>
        row.title.toLowerCase().includes(q) ||
        row.id.toLowerCase().includes(q)
    );
  }, [search]);

  const sorted = useMemo(() => {
    if (!sortKey) return filtered;

    const statusOrder: Record<VideoStatus, number> = {
      Published: 0,
      "Processed Only": 1,
      Failed: 2,
    };

    return [...filtered].sort((a, b) => {
      let av: string | number = "";
      let bv: string | number = "";

      if (sortKey === "status") {
        av = statusOrder[a.status];
        bv = statusOrder[b.status];
      } else {
        av = String(a[sortKey]).toLowerCase();
        bv = String(b[sortKey]).toLowerCase();
      }

      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
  }, [filtered, sortDir, sortKey]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / rowsPerPage));
  const currentPage = Math.min(page, totalPages);

  const pagedRows = useMemo(() => {
    const start = (currentPage - 1) * rowsPerPage;
    return sorted.slice(start, start + rowsPerPage);
  }, [currentPage, rowsPerPage, sorted]);

  const pageNumbers = useMemo(() => {
    const pages = Array.from({ length: totalPages }, (_, i) => i + 1);
    if (pages.length <= 5) return pages;

    const start = Math.max(1, currentPage - 2);
    const end = Math.min(totalPages, start + 4);
    return Array.from({ length: end - start + 1 }, (_, i) => start + i);
  }, [currentPage, totalPages]);

  function onSort(col: SortKey) {
    setPage(1);
    if (sortKey === col) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(col);
    setSortDir("asc");
  }

  function exportCsv() {
    const headers = [
      "Video ID",
      "Title",
      "Client",
      "Channel",
      "Date Processed",
      "Input Type",
      "Output Type",
      "Status",
    ];

    const escaped = sorted.map((r) =>
      [
        r.id,
        r.title,
        r.client,
        r.channel,
        r.dateProcessed,
        r.inputType,
        r.outputType,
        r.status,
      ].map((v) => `"${String(v).replace(/"/g, '""')}"`)
    );

    const csv = [headers.join(","), ...escaped.map((row) => row.join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = "video-explorer.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  function SortIcon({ col }: { col: SortKey }) {
    if (sortKey !== col) return <ChevronsUpDown className="h-4 w-4 text-neutral-500" />;
    return sortDir === "asc" ? (
      <ChevronUp className="h-4 w-4 text-neutral-300" />
    ) : (
      <ChevronDown className="h-4 w-4 text-neutral-300" />
    );
  }

  return (
    <section className="w-full rounded-xl border border-neutral-800 bg-neutral-950 shadow-sm">
      <div className="flex flex-col gap-3 border-b border-neutral-800 px-4 py-4 md:flex-row md:items-center md:justify-between">
        <div className="relative w-full md:max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-500" />
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search video title or ID..."
            className="w-full rounded-md border border-neutral-700 bg-neutral-900 py-2 pl-9 pr-3 text-sm text-white outline-none transition focus:border-red-700 focus:ring-2 focus:ring-red-950"
          />
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-md border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm font-medium text-neutral-200 hover:bg-neutral-800"
          >
            <SlidersHorizontal className="h-4 w-4" />
            Filters
          </button>

          <button
            type="button"
            onClick={exportCsv}
            className="inline-flex items-center gap-2 rounded-md bg-red-700 px-3 py-2 text-sm font-medium text-white hover:bg-red-600"
          >
            <Download className="h-4 w-4" />
            Export to CSV
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[980px] w-full text-left text-sm">
          <thead className="bg-neutral-900 text-neutral-300">
            <tr>
              {[
                { key: "id", label: "Video ID" },
                { key: "title", label: "Title" },
                { key: "client", label: "Client & Channel" },
                { key: "dateProcessed", label: "Date Processed" },
                { key: "inputType", label: "Input → Output" },
                { key: "status", label: "Status" },
              ].map((col) => (
                <th key={col.key} className="px-4 py-3 font-semibold">
                  <button
                    type="button"
                    onClick={() => onSort(col.key as SortKey)}
                    className="inline-flex items-center gap-1 text-neutral-300 hover:text-white"
                  >
                    {col.label}
                    <SortIcon col={col.key as SortKey} />
                  </button>
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {pagedRows.length > 0 ? (
              pagedRows.map((row) => (
                <tr key={row.id} className="border-t border-neutral-800 transition hover:bg-neutral-900/70">
                  <td className="px-4 py-3 font-mono text-xs text-neutral-300">{row.id}</td>
                  <td className="px-4 py-3 font-medium text-white">{row.title}</td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-neutral-100">{row.client}</div>
                    <div className="text-xs text-neutral-500">{row.channel}</div>
                  </td>
                  <td className="px-4 py-3 text-neutral-300">{formatDate(row.dateProcessed)}</td>
                  <td className="px-4 py-3 text-neutral-300">
                    {row.inputType} <span className="text-neutral-500">→</span> {row.outputType}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${statusClasses[row.status]}`}>
                      {row.status}
                    </span>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-neutral-500">
                  No videos found for your current search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-3 border-t border-neutral-800 px-4 py-3 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-2 text-sm text-neutral-400">
          <span>Rows per page</span>
          <select
            value={rowsPerPage}
            onChange={(e) => {
              setRowsPerPage(Number(e.target.value));
              setPage(1);
            }}
            className="rounded-md border border-neutral-700 bg-neutral-900 px-2 py-1 text-sm text-neutral-200"
          >
            {[5, 10, 20].map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="rounded-md border border-neutral-700 bg-neutral-900 px-3 py-1.5 text-sm text-neutral-200 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Previous
          </button>

          {pageNumbers.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPage(p)}
              className={`rounded-md px-3 py-1.5 text-sm ${
                p === currentPage
                  ? "bg-red-700 text-white"
                  : "border border-neutral-700 bg-neutral-900 text-neutral-200"
              }`}
            >
              {p}
            </button>
          ))}

          <button
            type="button"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="rounded-md border border-neutral-700 bg-neutral-900 px-3 py-1.5 text-sm text-neutral-200 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}