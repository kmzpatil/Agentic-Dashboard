"""
Isolated simulator engine.

The simulator is intentionally disconnected from the analytics database. It keeps
its own in-process data store, log stream, and quality checks so Labs can run
without mutating KPI tables.
"""

from __future__ import annotations

import copy
import hashlib
import random
import re
import string
import threading
import time
import uuid
from collections import Counter, defaultdict, deque
from datetime import date, datetime, timedelta, timezone
from typing import Any


SIM_CLIENT = "Simulated Client"
SIM_PREFIX = "SIM"
SIM_HEADLINE_PREFIX = f"{SIM_PREFIX}:"

TARGET_TABLES = [
    "clients",
    "users",
    "channels",
    "raw_videos",
    "raw_video_channel",
    "created_assets",
    "published_posts",
    "post_distribution",
]

# ---------------------------------------------------------------------------
# Column definitions with descriptions
# ---------------------------------------------------------------------------

def _col(name: str, ctype: str, *, notnull: bool = False, pk: bool = False, description: str = "") -> dict[str, Any]:
    return {"name": name, "type": ctype, "notnull": notnull, "pk": pk, "description": description}


TABLE_COLUMNS: dict[str, list[dict[str, Any]]] = {
    "clients": [
        _col("Client_Name", "text", notnull=True, pk=True, description="Unique client identifier"),
    ],
    "users": [
        _col("User_ID", "integer", notnull=True, pk=True, description="Unique user identifier"),
        _col("User_Name", "text", description="Display name"),
        _col("Team_Name", "text", description="Team assignment"),
        _col("Client_Name", "text", description="Parent client"),
    ],
    "channels": [
        _col("Channel_Name", "text", notnull=True, pk=True, description="Unique channel name"),
        _col("Client_Name", "text", description="Parent client"),
    ],
    "raw_videos": [
        # Original columns
        _col("Video_ID", "integer", notnull=True, pk=True, description="Unique video identifier"),
        _col("User_ID", "integer", description="Uploader user reference"),
        _col("Headline", "text", description="Video title/headline"),
        _col("Source_URL", "text", description="Original source URL"),
        _col("Upload_Date", "text", description="Upload date (YYYY-MM-DD)"),
        _col("Input_Type", "text", description="Content input type"),
        _col("Language", "text", description="Primary language"),
        _col("Uploaded_Duration", "integer", description="Duration in seconds"),
        # New upload metadata
        _col("File_Size_Bytes", "integer", description="Raw file size in bytes"),
        _col("File_Format", "text", description="Container format: mp4, mov, avi, mkv, webm"),
        _col("Resolution_Width", "integer", description="Pixel width"),
        _col("Resolution_Height", "integer", description="Pixel height"),
        _col("Video_Codec", "text", description="Video codec: h264, h265, vp9, av1"),
        _col("Audio_Codec", "text", description="Audio codec: aac, opus, mp3, none"),
        _col("Bitrate_Kbps", "integer", description="Total bitrate in kbps"),
        _col("Frame_Rate", "real", description="Frames per second"),
        _col("Upload_Started_At", "text", description="ISO timestamp upload began"),
        _col("Upload_Completed_At", "text", description="ISO timestamp upload finished"),
        _col("Upload_Status", "text", description="COMPLETED, FAILED, PARTIAL, TIMEOUT"),
        _col("Retry_Count", "integer", description="Number of upload retries"),
        _col("Device_Type", "text", description="Device: desktop, mobile, tablet, api"),
        _col("Geo_Location", "text", description="ISO country code"),
        _col("Network_Type", "text", description="Network: wifi, 4g, 5g, ethernet, unknown"),
        _col("Auto_Tags", "text", description="Comma-separated auto-detected tags"),
        _col("Content_Category", "text", description="Content category"),
        _col("NSFW_Score", "real", description="NSFW probability 0.0-1.0"),
        _col("Audio_Language_Detected", "text", description="Detected audio language"),
        _col("Checksum_SHA256", "text", description="File integrity SHA-256 hash"),
        _col("Is_Corrupted", "integer", description="0=intact, 1=corrupted"),
        _col("Meets_Quality_Threshold", "integer", description="0=below, 1=meets threshold"),
    ],
    "raw_video_channel": [
        _col("Video_ID", "integer", notnull=True, pk=True, description="Video reference"),
        _col("Channel_Name", "text", notnull=True, pk=True, description="Channel reference"),
    ],
    "created_assets": [
        # Original columns
        _col("Asset_ID", "integer", notnull=True, pk=True, description="Unique asset identifier"),
        _col("Video_ID", "integer", description="Source video reference"),
        _col("Output_Type", "text", description="Asset output type"),
        _col("Create_Date", "text", description="Creation date (YYYY-MM-DD)"),
        _col("Created_Duration", "integer", description="Output duration in seconds"),
        # New processing metadata
        _col("Processing_Started_At", "text", description="ISO timestamp processing began"),
        _col("Processing_Completed_At", "text", description="ISO timestamp processing ended"),
        _col("Processing_Status", "text", description="COMPLETED, FAILED, TIMEOUT, RETRYING"),
        _col("Processing_Node", "text", description="Worker node identifier"),
        _col("CPU_Time_Ms", "integer", description="CPU milliseconds consumed"),
        _col("GPU_Time_Ms", "integer", description="GPU milliseconds consumed"),
        _col("Memory_Peak_MB", "integer", description="Peak memory usage in MB"),
        _col("Output_Resolution", "text", description="Output resolution e.g. 1920x1080"),
        _col("Output_Bitrate_Kbps", "integer", description="Output bitrate in kbps"),
        _col("Quality_Score", "real", description="Automated quality rating 0.0-100.0"),
        _col("Transcription_Confidence", "real", description="ASR confidence 0.0-1.0"),
        _col("Thumbnail_Generated", "integer", description="0=no, 1=yes"),
        _col("Error_Code", "text", description="Processing error code if failed"),
        _col("Error_Message", "text", description="Human-readable error detail"),
        _col("Processing_Retry_Count", "integer", description="Number of processing retries"),
        _col("Fallback_Used", "integer", description="0=primary, 1=fallback pipeline"),
        _col("Output_File_Size_Bytes", "integer", description="Output file size in bytes"),
        _col("SLA_Met", "integer", description="0=breached, 1=met SLA target"),
    ],
    "published_posts": [
        # Original columns
        _col("Post_ID", "integer", notnull=True, pk=True, description="Unique post identifier"),
        _col("Asset_ID", "integer", description="Source asset reference"),
        _col("Publish_Date", "text", description="Publish date (YYYY-MM-DD)"),
        _col("Published_Duration", "integer", description="Time to publish in seconds"),
        # New publishing metadata
        _col("API_Request_ID", "text", description="Unique API request identifier"),
        _col("API_Response_Code", "integer", description="HTTP response code from platform"),
        _col("API_Latency_Ms", "integer", description="Round-trip API latency in ms"),
        _col("Rate_Limited", "integer", description="0=no, 1=rate-limited"),
        _col("Auth_Token_Valid", "integer", description="0=invalid, 1=valid"),
        _col("Scheduled_At", "text", description="ISO timestamp of scheduled publish"),
        _col("Actual_Publish_Time", "text", description="ISO timestamp of actual publish"),
        _col("Schedule_Drift_Seconds", "integer", description="Difference scheduled vs actual"),
        _col("Platform_Post_ID", "text", description="ID returned by the platform"),
        _col("Platform_Status", "text", description="LIVE, PENDING_REVIEW, REJECTED, REMOVED"),
        _col("Monetization_Eligible", "integer", description="0=no, 1=eligible"),
        _col("Geo_Restricted", "integer", description="0=no, 1=restricted"),
        _col("Publish_Status", "text", description="SUCCESS, FAILED, PARTIAL, SCHEDULED"),
        _col("Publish_Retry_Count", "integer", description="Number of publish retries"),
        _col("Error_Code", "text", description="Publish error code if failed"),
        _col("Error_Message", "text", description="Human-readable publish error"),
    ],
    "post_distribution": [
        # Original columns
        _col("Distribution_ID", "integer", notnull=True, pk=True, description="Unique distribution ID"),
        _col("Post_ID", "integer", description="Parent post reference"),
        _col("Channel_Name", "text", description="Distribution channel"),
        _col("Published_Platform", "text", description="Target social platform"),
        _col("Published_URL", "text", description="URL on the platform"),
        # New distribution metadata
        _col("CDN_URL", "text", description="CDN-served content URL"),
        _col("CDN_Region", "text", description="CDN edge region"),
        _col("Embed_Code_Valid", "integer", description="0=invalid, 1=valid"),
        _col("Thumbnail_URL", "text", description="Thumbnail URL for distribution"),
        _col("Thumbnail_URL_Valid", "integer", description="0=invalid, 1=valid"),
        _col("Distribution_Status", "text", description="ACTIVE, PENDING, FAILED, REMOVED"),
        _col("Distributed_At", "text", description="ISO timestamp of distribution"),
        _col("Reach_Count", "integer", description="Initial reach/impression count"),
    ],
}

PRIMARY_KEYS: dict[str, list[str]] = {
    "clients": ["Client_Name"],
    "users": ["User_ID"],
    "channels": ["Channel_Name"],
    "raw_videos": ["Video_ID"],
    "raw_video_channel": ["Video_ID", "Channel_Name"],
    "created_assets": ["Asset_ID"],
    "published_posts": ["Post_ID"],
    "post_distribution": ["Distribution_ID"],
}

REQUIRED_COLUMNS: dict[str, list[str]] = {
    "raw_videos": ["Video_ID"],
    "users": ["User_ID"],
    "created_assets": ["Asset_ID"],
    "published_posts": ["Post_ID"],
    "post_distribution": ["Distribution_ID"],
    "channels": ["Channel_Name"],
    "raw_video_channel": ["Video_ID", "Channel_Name"],
}

FOREIGN_KEYS: list[tuple[str, str, str, str]] = [
    ("raw_videos", "User_ID", "users", "User_ID"),
    ("created_assets", "Video_ID", "raw_videos", "Video_ID"),
    ("published_posts", "Asset_ID", "created_assets", "Asset_ID"),
    ("post_distribution", "Post_ID", "published_posts", "Post_ID"),
    ("raw_video_channel", "Video_ID", "raw_videos", "Video_ID"),
    ("raw_video_channel", "Channel_Name", "channels", "Channel_Name"),
]

NON_NEGATIVE_COLUMNS: dict[str, list[str]] = {
    "raw_videos": ["Uploaded_Duration", "File_Size_Bytes", "Resolution_Width", "Resolution_Height",
                    "Bitrate_Kbps", "Frame_Rate", "Retry_Count"],
    "created_assets": ["Created_Duration", "CPU_Time_Ms", "GPU_Time_Ms", "Memory_Peak_MB",
                       "Output_Bitrate_Kbps", "Output_File_Size_Bytes", "Processing_Retry_Count"],
    "published_posts": ["Published_Duration", "API_Latency_Ms", "Publish_Retry_Count"],
    "post_distribution": ["Reach_Count"],
}

DATE_COLUMNS: dict[str, list[str]] = {
    "raw_videos": ["Upload_Date"],
    "created_assets": ["Create_Date"],
    "published_posts": ["Publish_Date"],
}

RANGE_COLUMNS: dict[str, dict[str, tuple[float, float]]] = {
    "raw_videos": {"NSFW_Score": (0.0, 1.0)},
    "created_assets": {
        "Quality_Score": (0.0, 100.0),
        "Transcription_Confidence": (0.0, 1.0),
    },
}

ENUM_COLUMNS: dict[str, dict[str, list[str]]] = {
    "raw_videos": {
        "Upload_Status": ["COMPLETED", "FAILED", "PARTIAL", "TIMEOUT"],
        "File_Format": ["mp4", "mov", "avi", "mkv", "webm"],
        "Video_Codec": ["h264", "h265", "vp9", "av1"],
        "Audio_Codec": ["aac", "opus", "mp3", "none"],
        "Device_Type": ["desktop", "mobile", "tablet", "api"],
        "Network_Type": ["wifi", "4g", "5g", "ethernet", "unknown"],
    },
    "created_assets": {
        "Processing_Status": ["COMPLETED", "FAILED", "TIMEOUT", "RETRYING"],
    },
    "published_posts": {
        "Publish_Status": ["SUCCESS", "FAILED", "PARTIAL", "SCHEDULED"],
        "Platform_Status": ["LIVE", "PENDING_REVIEW", "REJECTED", "REMOVED"],
    },
    "post_distribution": {
        "Distribution_Status": ["ACTIVE", "PENDING", "FAILED", "REMOVED"],
    },
}

URL_COLUMNS: dict[str, list[str]] = {
    "raw_videos": ["Source_URL"],
    "post_distribution": ["Published_URL", "CDN_URL", "Thumbnail_URL"],
}

# ---------------------------------------------------------------------------
# Data generation constants
# ---------------------------------------------------------------------------

FIRST_NAMES = [
    "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hank",
    "Ivy", "Jake", "Karen", "Leo", "Mona", "Nate", "Olivia", "Paul",
    "Quinn", "Rose", "Sam", "Tara", "Uma", "Vince", "Wendy", "Xander",
]
TEAM_NAMES = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"]
CHANNEL_NAMES = [
    f"{SIM_PREFIX} Tech Digest",
    f"{SIM_PREFIX} Daily Bytes",
    f"{SIM_PREFIX} News Flash",
    f"{SIM_PREFIX} Sports Hub",
    f"{SIM_PREFIX} Culture Lens",
    f"{SIM_PREFIX} Market Watch",
    f"{SIM_PREFIX} Science Now",
    f"{SIM_PREFIX} Travel Tales",
]
LANGUAGES = ["English", "Hindi", "Spanish", "French", "German", "Japanese", "Korean", "Portuguese"]
INPUT_TYPES = ["Uploaded", "Created", "Live"]
OUTPUT_TYPES = ["Video", "Reel", "Short", "Story", "Post", "Article"]
PLATFORMS = ["Facebook", "Instagram", "LinkedIn", "YouTube", "X", "Threads"]
HEADLINES = [
    f"{SIM_HEADLINE_PREFIX} Major Tech Announcement",
    f"{SIM_HEADLINE_PREFIX} AI Is Changing Everything",
    f"{SIM_HEADLINE_PREFIX} Productivity Tips",
    f"{SIM_HEADLINE_PREFIX} The Future of Remote Work",
    f"{SIM_HEADLINE_PREFIX} Surprising Results",
    f"{SIM_HEADLINE_PREFIX} Industry Trends",
    f"{SIM_HEADLINE_PREFIX} Behind the Scenes",
    f"{SIM_HEADLINE_PREFIX} What You Need to Know",
]
FILE_FORMATS = ["mp4", "mov", "avi", "mkv", "webm"]
VIDEO_CODECS = ["h264", "h265", "vp9", "av1"]
AUDIO_CODECS = ["aac", "opus", "mp3", "none"]
DEVICE_TYPES = ["desktop", "mobile", "tablet", "api"]
NETWORK_TYPES = ["wifi", "4g", "5g", "ethernet", "unknown"]
CONTENT_CATEGORIES = ["news", "sports", "entertainment", "education", "technology", "lifestyle", "politics", "business"]
GEO_LOCATIONS = ["US", "IN", "GB", "DE", "BR", "JP", "KR", "FR", "AU", "CA"]
CDN_REGIONS = ["us-east-1", "us-west-2", "eu-west-1", "ap-south-1", "ap-northeast-1"]
PROCESSING_NODES = ["worker-01", "worker-02", "worker-03", "gpu-01", "gpu-02"]
AUTO_TAGS_POOL = ["breaking", "exclusive", "trending", "live", "interview", "analysis", "opinion",
                  "update", "recap", "highlight", "behind-the-scenes", "tutorial"]
UPLOAD_STATUSES = ["COMPLETED", "FAILED", "PARTIAL", "TIMEOUT"]
PROCESSING_STATUSES = ["COMPLETED", "FAILED", "TIMEOUT", "RETRYING"]
PUBLISH_STATUSES = ["SUCCESS", "FAILED", "PARTIAL", "SCHEDULED"]
PLATFORM_STATUSES = ["LIVE", "PENDING_REVIEW", "REJECTED", "REMOVED"]
DISTRIBUTION_STATUSES = ["ACTIVE", "PENDING", "FAILED", "REMOVED"]
PROCESSING_ERROR_CODES = ["CODEC_UNSUPPORTED", "OOM", "TIMEOUT", "CORRUPT_INPUT", "RESOLUTION_EXCEEDED"]
PUBLISH_ERROR_CODES = ["AUTH_FAILED", "RATE_LIMITED", "CONTENT_REJECTED", "API_TIMEOUT", "QUOTA_EXCEEDED"]
RESOLUTIONS = [(1920, 1080), (1280, 720), (3840, 2160), (1080, 1920), (720, 1280), (854, 480)]

# ---------------------------------------------------------------------------
# Error injection defaults
# ---------------------------------------------------------------------------

DEFAULT_ERROR_RATES: dict[str, float] = {
    # Upload errors
    "null_fields": 0.05,
    "invalid_format": 0.03,
    "corrupted_file": 0.02,
    "failed_upload": 0.04,
    "future_date": 0.02,
    "negative_value": 0.02,
    "duplicate_checksum": 0.03,
    # Processing errors
    "processing_failure": 0.05,
    "sla_breach": 0.08,
    "low_quality": 0.06,
    "no_thumbnail": 0.04,
    "temporal_inversion": 0.02,
    # Publishing errors
    "publish_failure": 0.04,
    "rate_limited": 0.06,
    "content_rejected": 0.03,
    "high_latency": 0.05,
    "schedule_drift": 0.07,
    "auth_failure": 0.02,
    # Distribution errors
    "invalid_url": 0.03,
    "invalid_embed": 0.04,
    "orphan_records": 0.02,
}

MAX_LOG_ENTRIES = 10_000

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _random_date(start_year: int = 2024, end_year: int = 2026) -> str:
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    delta = (end - start).days
    day = start + timedelta(days=random.randint(0, delta))
    return day.isoformat()


def _random_url(prefix: str = "video") -> str:
    slug = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"https://example.com/{prefix}/{slug}"


def _random_string(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_letters, k=length))


def _random_sha256() -> str:
    return hashlib.sha256(uuid.uuid4().bytes).hexdigest()


def _random_iso_timestamp(base_date: str | None = None, offset_seconds: int = 0) -> str:
    if base_date:
        try:
            dt = datetime.strptime(base_date, "%Y-%m-%d")
        except ValueError:
            dt = datetime.now(timezone.utc)
    else:
        dt = datetime.now(timezone.utc)
    dt = dt.replace(
        hour=random.randint(0, 23),
        minute=random.randint(0, 59),
        second=random.randint(0, 59),
        tzinfo=timezone.utc,
    )
    dt += timedelta(seconds=offset_seconds)
    return dt.isoformat()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _roll(rate: float) -> bool:
    return random.random() < rate


URL_RE = re.compile(r"^https?://")


class _IDCounter:
    def __init__(self, start: int = 1) -> None:
        self._val = start
        self._lock = threading.Lock()

    def next(self) -> int:
        with self._lock:
            value = self._val
            self._val += 1
            return value


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class SimulatorEngine:
    def __init__(self) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = {table: [] for table in TARGET_TABLES}
        self._logs: deque[dict[str, Any]] = deque(maxlen=MAX_LOG_ENTRIES)
        self._log_id = _IDCounter(1)
        self._distribution_id = _IDCounter(1)
        self._user_id = _IDCounter(1)
        self._video_id = _IDCounter(1)
        self._asset_id = _IDCounter(1)
        self._post_id = _IDCounter(1)

        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._ops_per_batch = 5
        self._batch_interval = 2.0

        self._error_rates: dict[str, float] = dict(DEFAULT_ERROR_RATES)
        self._quality_timeseries: deque[dict[str, Any]] = deque(maxlen=120)
        self._checksums_seen: set[str] = set()

    # ── lifecycle ──────────────────────────────────────────────────────

    def start(self, ops_per_batch: int = 5, interval: float = 2.0) -> None:
        with self._lock:
            self._ops_per_batch = ops_per_batch
            self._batch_interval = interval
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def reset(self) -> None:
        was_running = self._running
        self.stop()
        self._tables = {table: [] for table in TARGET_TABLES}
        self._logs = deque(maxlen=MAX_LOG_ENTRIES)
        self._distribution_id = _IDCounter(1)
        self._user_id = _IDCounter(1)
        self._video_id = _IDCounter(1)
        self._asset_id = _IDCounter(1)
        self._post_id = _IDCounter(1)
        self._quality_timeseries.clear()
        self._checksums_seen.clear()
        if was_running:
            self.start(self._ops_per_batch, self._batch_interval)

    # ── state queries ─────────────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "tables": {table: len(rows) for table, rows in self._tables.items()},
            "log_counts": dict(Counter(log["status"] for log in self._logs)),
            "settings": {
                "ops_per_batch": self._ops_per_batch,
                "interval": self._batch_interval,
            },
        }

    def get_tables(self) -> list[dict[str, Any]]:
        return [
            {
                "name": table,
                "columns": copy.deepcopy(TABLE_COLUMNS[table]),
                "row_count": len(self._tables[table]),
            }
            for table in TARGET_TABLES
        ]

    def get_table_rows(self, table_name: str, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        if table_name not in self._tables:
            return {"error": "Table not found", "rows": [], "columns": []}
        rows = self._tables[table_name][offset: offset + limit]
        columns = [column["name"] for column in TABLE_COLUMNS[table_name]]
        return {"columns": columns, "rows": copy.deepcopy(rows), "total": len(self._tables[table_name])}

    def get_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        status_filter: str | None = None,
        table_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = list(reversed(self._logs))
        if status_filter:
            rows = [row for row in rows if row["status"] == status_filter]
        if table_filter:
            rows = [row for row in rows if row["table_name"] == table_filter]
        return copy.deepcopy(rows[offset: offset + limit])

    def get_quality_report(self) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        issues += self._check_nulls()
        issues += self._check_duplicate_pks()
        issues += self._check_referential_integrity()
        issues += self._check_non_negative()
        issues += self._check_date_formats()
        issues += self._check_ranges()
        issues += self._check_enums()
        issues += self._check_urls()
        issues += self._check_temporal_order()
        issues += self._check_business_logic()

        tables: dict[str, dict[str, Any]] = {}
        total_rows = 0
        for table_name in TARGET_TABLES:
            row_count = len(self._tables[table_name])
            total_rows += row_count
            table_issues = [issue for issue in issues if issue["table"] == table_name]
            score = 100.0 if row_count == 0 else max(0.0, 100.0 - (len(table_issues) / row_count) * 100)
            tables[table_name] = {
                "row_count": row_count,
                "issue_count": len(table_issues),
                "score": round(score, 1),
                "issues": table_issues,
            }

        overall_score = 100.0 if total_rows == 0 else max(0.0, 100.0 - (len(issues) / total_rows) * 100)
        return {
            "overall_score": round(overall_score, 1),
            "total_issues": len(issues),
            "total_rows": total_rows,
            "tables": tables,
        }

    def get_timeseries_metrics(self) -> dict[str, Any]:
        buckets: dict[str, dict[str, int]] = defaultdict(lambda: {"INSERT": 0, "UPDATE": 0, "DELETE": 0})
        for log in self._logs:
            if log["status"] != "SUCCESS":
                continue
            bucket = log["timestamp"][:16]
            if log["operation"] in {"INSERT", "UPDATE", "DELETE"}:
                buckets[bucket][log["operation"]] += 1

        labels = sorted(buckets.keys())[-60:]
        return {
            "labels": labels,
            "inserts": [buckets[label]["INSERT"] for label in labels],
            "updates": [buckets[label]["UPDATE"] for label in labels],
            "deletes": [buckets[label]["DELETE"] for label in labels],
        }

    # ── new DQA methods ───────────────────────────────────────────────

    def get_stage_quality_scores(self) -> dict[str, Any]:
        """Per-stage quality scores using weighted formulas."""
        upload_score = self._compute_upload_quality()
        processing_score = self._compute_processing_quality()
        publishing_score = self._compute_publishing_quality()
        overall = round(0.35 * upload_score + 0.35 * processing_score + 0.30 * publishing_score, 1)
        return {
            "upload": {"score": upload_score, "stage": "Upload", "table": "raw_videos",
                       "row_count": len(self._tables["raw_videos"])},
            "processing": {"score": processing_score, "stage": "Processing", "table": "created_assets",
                           "row_count": len(self._tables["created_assets"])},
            "publishing": {"score": publishing_score, "stage": "Publishing", "table": "published_posts",
                           "row_count": len(self._tables["published_posts"])},
            "overall": overall,
        }

    def get_pipeline_funnel(self) -> dict[str, Any]:
        """Pipeline counts and drop-off rates."""
        uploads = len(self._tables["raw_videos"])
        processed = len(self._tables["created_assets"])
        published = len(self._tables["published_posts"])
        distributed = len(self._tables["post_distribution"])

        def _rate(num: int, den: int) -> float:
            return round((num / den * 100) if den > 0 else 0.0, 1)

        return {
            "stages": [
                {"name": "Upload", "count": uploads, "icon": "upload"},
                {"name": "Processing", "count": processed, "icon": "cpu"},
                {"name": "Publishing", "count": published, "icon": "send"},
            ],
            "conversions": [
                {"from": "Upload", "to": "Processing", "rate": _rate(processed, uploads),
                 "drop_off": _rate(max(uploads - processed, 0), uploads)},
                {"from": "Processing", "to": "Publishing", "rate": _rate(published, processed),
                 "drop_off": _rate(max(processed - published, 0), processed)},
            ],
            "distribution_count": distributed,
            "total_uploads": uploads,
            "total_processed": processed,
            "total_published": published,
        }

    def get_error_distribution(self) -> dict[str, Any]:
        """Error counts grouped by category and error code."""
        by_code: dict[str, int] = Counter()
        by_category: dict[str, int] = Counter()
        by_stage: dict[str, int] = Counter()

        for log in self._logs:
            if log["status"] != "QUALITY_ISSUE":
                continue
            code = log.get("error_code", "UNKNOWN")
            by_code[code] += 1
            # Parse stage from code prefix
            if code.startswith("UPL_"):
                by_stage["Upload"] += 1
            elif code.startswith("PRC_"):
                by_stage["Processing"] += 1
            elif code.startswith("PUB_"):
                by_stage["Publishing"] += 1
            elif code.startswith("DST_"):
                by_stage["Distribution"] += 1
            else:
                by_stage["Other"] += 1
            # Parse category
            parts = code.split("_")
            if len(parts) >= 2:
                cat_map = {"COMP": "Completeness", "VAL": "Validity", "REF": "Referential Integrity",
                           "TIME": "Timeliness", "CON": "Consistency", "BIZ": "Business Logic"}
                by_category[cat_map.get(parts[1], "Other")] += 1
            else:
                by_category["Other"] += 1

        # Top error codes
        top_codes = [{"code": code, "count": count} for code, count in by_code.most_common(20)]

        return {
            "by_code": top_codes,
            "by_category": dict(by_category),
            "by_stage": dict(by_stage),
            "total_errors": sum(by_code.values()),
        }

    def get_stage_timeseries(self) -> dict[str, Any]:
        """Quality scores over time."""
        ts = list(self._quality_timeseries)
        return {
            "labels": [entry["timestamp"] for entry in ts],
            "upload": [entry["upload"] for entry in ts],
            "processing": [entry["processing"] for entry in ts],
            "publishing": [entry["publishing"] for entry in ts],
            "overall": [entry["overall"] for entry in ts],
        }

    def get_recent_critical_issues(self, limit: int = 10) -> list[dict[str, Any]]:
        """Most recent high-severity quality issues."""
        issues = []
        for log in reversed(self._logs):
            if log["status"] == "QUALITY_ISSUE":
                issues.append({
                    "id": log["id"],
                    "timestamp": log["timestamp"],
                    "table_name": log["table_name"],
                    "error_code": log.get("error_code", "UNKNOWN"),
                    "error_message": log.get("error_message", ""),
                    "severity": self._get_severity(log.get("error_code", "")),
                })
                if len(issues) >= limit:
                    break
        return issues

    def get_processing_latency_distribution(self) -> dict[str, Any]:
        """Histogram of processing times (CPU_Time_Ms)."""
        buckets = {"0-100ms": 0, "100-500ms": 0, "500ms-1s": 0, "1-5s": 0, "5-30s": 0, "30s+": 0}
        for row in self._tables["created_assets"]:
            cpu = row.get("CPU_Time_Ms")
            if cpu is None or not isinstance(cpu, (int, float)):
                continue
            if cpu < 100:
                buckets["0-100ms"] += 1
            elif cpu < 500:
                buckets["100-500ms"] += 1
            elif cpu < 1000:
                buckets["500ms-1s"] += 1
            elif cpu < 5000:
                buckets["1-5s"] += 1
            elif cpu < 30000:
                buckets["5-30s"] += 1
            else:
                buckets["30s+"] += 1
        return {"buckets": buckets}

    def get_schema_descriptions(self) -> list[dict[str, Any]]:
        """Full schema with column descriptions for UI."""
        result = []
        pipeline_tables = ["raw_videos", "created_assets", "published_posts", "post_distribution"]
        stage_map = {
            "raw_videos": "Upload",
            "created_assets": "Processing",
            "published_posts": "Publishing",
            "post_distribution": "Distribution",
        }
        for table in pipeline_tables:
            cols = TABLE_COLUMNS.get(table, [])
            pk_cols = PRIMARY_KEYS.get(table, [])
            fk_refs = {}
            for child_t, child_c, parent_t, parent_c in FOREIGN_KEYS:
                if child_t == table:
                    fk_refs[child_c] = f"{parent_t}.{parent_c}"
            result.append({
                "table": table,
                "stage": stage_map.get(table, ""),
                "row_count": len(self._tables[table]),
                "columns": [
                    {
                        "name": c["name"],
                        "type": c["type"],
                        "notnull": c["notnull"],
                        "pk": c["name"] in pk_cols,
                        "fk": fk_refs.get(c["name"]),
                        "description": c.get("description", ""),
                    }
                    for c in cols
                ],
            })
        return result

    def get_error_config(self) -> dict[str, float]:
        return dict(self._error_rates)

    def set_error_config(self, rates: dict[str, float]) -> None:
        for key, value in rates.items():
            if key in self._error_rates:
                self._error_rates[key] = max(0.0, min(1.0, float(value)))

    # ── seed ──────────────────────────────────────────────────────────

    def seed(self, count: int = 10) -> None:
        self._seed_clients()
        self._seed_users(count)
        self._seed_channels()
        self._seed_raw_videos(count * 2)
        self._seed_created_assets(count)
        self._seed_published_posts(count)
        self._record_quality_snapshot()

    # ── internal helpers ──────────────────────────────────────────────

    def _pk_tuple(self, table: str, row: dict[str, Any]) -> tuple[Any, ...]:
        return tuple(row.get(column) for column in PRIMARY_KEYS[table])

    def _insert_row(self, table: str, row: dict[str, Any], *, operation: str = "INSERT") -> bool:
        if any(self._pk_tuple(table, existing) == self._pk_tuple(table, row) for existing in self._tables[table]):
            return False
        log_id = self._log_pending(operation, table, row_id=self._row_id(table, row), new_values=row)
        self._tables[table].append(copy.deepcopy(row))
        self._mark_success(log_id)
        return True

    def _log_pending(
        self,
        operation: str,
        table_name: str,
        *,
        row_id: str | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> int:
        log_id = self._log_id.next()
        self._logs.append(
            {
                "id": log_id,
                "timestamp": _now(),
                "operation": operation,
                "table_name": table_name,
                "row_id": row_id,
                "old_values": copy.deepcopy(old_values),
                "new_values": copy.deepcopy(new_values),
                "status": "PENDING",
                "error_message": None,
                "error_code": error_code,
            }
        )
        return log_id

    def _log_quality_issue(self, table: str, error_code: str, message: str, details: dict[str, Any] | None = None) -> None:
        log_id = self._log_id.next()
        self._logs.append({
            "id": log_id,
            "timestamp": _now(),
            "operation": "QUALITY_CHECK",
            "table_name": table,
            "row_id": None,
            "old_values": None,
            "new_values": copy.deepcopy(details),
            "status": "QUALITY_ISSUE",
            "error_message": message,
            "error_code": error_code,
        })

    def _mark_success(self, log_id: int) -> None:
        for log in self._logs:
            if log["id"] == log_id:
                log["status"] = "SUCCESS"
                log["timestamp"] = _now()
                return

    def _mark_error(self, log_id: int, message: str) -> None:
        for log in self._logs:
            if log["id"] == log_id:
                log["status"] = "ERROR"
                log["error_message"] = message
                log["timestamp"] = _now()
                return

    def _row_id(self, table: str, row: dict[str, Any]) -> str:
        return "|".join(str(row.get(column, "")) for column in PRIMARY_KEYS[table])

    @staticmethod
    def _get_severity(error_code: str) -> str:
        if not error_code:
            return "low"
        if "_BIZ_" in error_code or "_REF_" in error_code:
            return "high"
        if "_CON_" in error_code or "_TIME_" in error_code:
            return "medium"
        return "low"

    # ── seeding methods ───────────────────────────────────────────────

    def _seed_clients(self) -> None:
        self._insert_row("clients", {"Client_Name": SIM_CLIENT})

    def _seed_users(self, count: int) -> None:
        for _ in range(count):
            self._insert_row(
                "users",
                {
                    "User_ID": self._user_id.next(),
                    "User_Name": f"{SIM_PREFIX} {random.choice(FIRST_NAMES)} {_random_string(4)}",
                    "Team_Name": random.choice(TEAM_NAMES),
                    "Client_Name": SIM_CLIENT,
                },
            )

    def _seed_channels(self) -> None:
        for channel_name in CHANNEL_NAMES:
            self._insert_row(
                "channels",
                {"Channel_Name": channel_name, "Client_Name": SIM_CLIENT},
            )

    def _seed_raw_videos(self, count: int) -> None:
        user_ids = [row["User_ID"] for row in self._tables["users"]]
        channel_names = [row["Channel_Name"] for row in self._tables["channels"]]
        if not user_ids:
            return
        for _ in range(count):
            video_id = self._video_id.next()
            upload_date = _random_date()
            upload_started = _random_iso_timestamp(upload_date)
            upload_duration_secs = random.randint(5, 600)
            checksum = _random_sha256()
            width, height = random.choice(RESOLUTIONS)

            row: dict[str, Any] = {
                "Video_ID": video_id,
                "User_ID": random.choice(user_ids),
                "Headline": random.choice(HEADLINES),
                "Source_URL": _random_url("video"),
                "Upload_Date": upload_date,
                "Input_Type": random.choice(INPUT_TYPES),
                "Language": random.choice(LANGUAGES),
                "Uploaded_Duration": random.randint(10, 7200),
                "File_Size_Bytes": random.randint(1_000_000, 5_000_000_000),
                "File_Format": random.choice(FILE_FORMATS),
                "Resolution_Width": width,
                "Resolution_Height": height,
                "Video_Codec": random.choice(VIDEO_CODECS),
                "Audio_Codec": random.choice(AUDIO_CODECS),
                "Bitrate_Kbps": random.randint(500, 50_000),
                "Frame_Rate": random.choice([23.976, 24.0, 25.0, 29.97, 30.0, 50.0, 59.94, 60.0]),
                "Upload_Started_At": upload_started,
                "Upload_Completed_At": _random_iso_timestamp(upload_date, upload_duration_secs),
                "Upload_Status": "COMPLETED",
                "Retry_Count": 0,
                "Device_Type": random.choice(DEVICE_TYPES),
                "Geo_Location": random.choice(GEO_LOCATIONS),
                "Network_Type": random.choice(NETWORK_TYPES),
                "Auto_Tags": ",".join(random.sample(AUTO_TAGS_POOL, k=random.randint(1, 4))),
                "Content_Category": random.choice(CONTENT_CATEGORIES),
                "NSFW_Score": round(random.uniform(0.0, 0.15), 4),
                "Audio_Language_Detected": random.choice(LANGUAGES),
                "Checksum_SHA256": checksum,
                "Is_Corrupted": 0,
                "Meets_Quality_Threshold": 1,
            }

            # Error injection for uploads
            self._inject_upload_errors(row)

            self._insert_row("raw_videos", row)
            self._checksums_seen.add(row.get("Checksum_SHA256", ""))

            if channel_names:
                self._insert_row(
                    "raw_video_channel",
                    {"Video_ID": video_id, "Channel_Name": random.choice(channel_names)},
                )

    def _inject_upload_errors(self, row: dict[str, Any]) -> None:
        r = self._error_rates

        if _roll(r["null_fields"]):
            field = random.choice(["Headline", "Source_URL", "File_Format", "Checksum_SHA256"])
            row[field] = None
            code_map = {"Headline": "UPL_COMP_MISSING_HEADLINE", "Source_URL": "UPL_COMP_MISSING_SOURCE_URL",
                        "File_Format": "UPL_COMP_MISSING_FORMAT", "Checksum_SHA256": "UPL_COMP_MISSING_CHECKSUM"}
            self._log_quality_issue("raw_videos", code_map[field], f"Missing {field} for Video_ID={row['Video_ID']}")

        if _roll(r["invalid_format"]):
            row["File_Format"] = random.choice(["flv", "wmv", "3gp", "dat"])
            self._log_quality_issue("raw_videos", "UPL_VAL_INVALID_FORMAT",
                                    f"Invalid format '{row['File_Format']}' for Video_ID={row['Video_ID']}")

        if _roll(r["corrupted_file"]):
            row["Is_Corrupted"] = 1
            row["Upload_Status"] = "COMPLETED"  # status mismatch
            self._log_quality_issue("raw_videos", "UPL_BIZ_CORRUPTED_FILE",
                                    f"Corrupted file for Video_ID={row['Video_ID']}")
            self._log_quality_issue("raw_videos", "UPL_CON_STATUS_MISMATCH",
                                    f"Upload_Status=COMPLETED but Is_Corrupted=1 for Video_ID={row['Video_ID']}")

        if _roll(r["failed_upload"]):
            row["Upload_Status"] = random.choice(["FAILED", "PARTIAL", "TIMEOUT"])
            row["Retry_Count"] = random.randint(1, 8)
            self._log_quality_issue("raw_videos", "UPL_COMP_PARTIAL_UPLOAD",
                                    f"Upload_Status={row['Upload_Status']} for Video_ID={row['Video_ID']}")
            if row["Retry_Count"] > 5:
                self._log_quality_issue("raw_videos", "UPL_BIZ_EXCESSIVE_RETRIES",
                                        f"Retry_Count={row['Retry_Count']} for Video_ID={row['Video_ID']}")

        if _roll(r["future_date"]):
            future = (date.today() + timedelta(days=random.randint(30, 365))).isoformat()
            row["Upload_Date"] = future
            self._log_quality_issue("raw_videos", "UPL_VAL_FUTURE_DATE",
                                    f"Future Upload_Date={future} for Video_ID={row['Video_ID']}")

        if _roll(r["negative_value"]):
            row["Uploaded_Duration"] = -random.randint(1, 1000)
            self._log_quality_issue("raw_videos", "UPL_VAL_NEGATIVE_DURATION",
                                    f"Negative duration={row['Uploaded_Duration']} for Video_ID={row['Video_ID']}")

        if _roll(r["duplicate_checksum"]) and self._checksums_seen:
            row["Checksum_SHA256"] = random.choice(list(self._checksums_seen))
            self._log_quality_issue("raw_videos", "UPL_CON_DUPLICATE_CHECKSUM",
                                    f"Duplicate checksum for Video_ID={row['Video_ID']}")

    def _seed_created_assets(self, count: int) -> None:
        video_ids = [row["Video_ID"] for row in self._tables["raw_videos"]]
        if not video_ids:
            return
        for _ in range(count):
            video_id = random.choice(video_ids)
            # Find parent video's upload date for temporal consistency
            parent_date = None
            for v in self._tables["raw_videos"]:
                if v["Video_ID"] == video_id:
                    parent_date = v.get("Upload_Date")
                    break

            create_date = _random_date()
            if parent_date:
                try:
                    pd = datetime.strptime(parent_date, "%Y-%m-%d")
                    cd = pd + timedelta(days=random.randint(0, 30))
                    create_date = cd.strftime("%Y-%m-%d")
                except ValueError:
                    pass

            proc_started = _random_iso_timestamp(create_date)
            cpu_time = random.randint(100, 60_000)
            gpu_time = random.randint(0, 30_000)
            quality = round(random.uniform(40.0, 98.0), 1)

            row: dict[str, Any] = {
                "Asset_ID": self._asset_id.next(),
                "Video_ID": video_id,
                "Output_Type": random.choice(OUTPUT_TYPES),
                "Create_Date": create_date,
                "Created_Duration": random.randint(5, 3600),
                "Processing_Started_At": proc_started,
                "Processing_Completed_At": _random_iso_timestamp(create_date, cpu_time // 1000 + random.randint(1, 60)),
                "Processing_Status": "COMPLETED",
                "Processing_Node": random.choice(PROCESSING_NODES),
                "CPU_Time_Ms": cpu_time,
                "GPU_Time_Ms": gpu_time,
                "Memory_Peak_MB": random.randint(128, 8192),
                "Output_Resolution": f"{random.choice(RESOLUTIONS)[0]}x{random.choice(RESOLUTIONS)[1]}",
                "Output_Bitrate_Kbps": random.randint(500, 20_000),
                "Quality_Score": quality,
                "Transcription_Confidence": round(random.uniform(0.5, 0.99), 3),
                "Thumbnail_Generated": 1,
                "Error_Code": None,
                "Error_Message": None,
                "Processing_Retry_Count": 0,
                "Fallback_Used": 0,
                "Output_File_Size_Bytes": random.randint(500_000, 2_000_000_000),
                "SLA_Met": 1,
            }

            self._inject_processing_errors(row)
            self._insert_row("created_assets", row)

    def _inject_processing_errors(self, row: dict[str, Any]) -> None:
        r = self._error_rates

        if _roll(r["processing_failure"]):
            error_code = random.choice(PROCESSING_ERROR_CODES)
            row["Processing_Status"] = "FAILED"
            row["Error_Code"] = error_code
            row["Error_Message"] = f"Processing failed: {error_code}"
            row["Processing_Retry_Count"] = random.randint(1, 5)
            self._log_quality_issue("created_assets", "PRC_BIZ_PROCESSING_FAILED",
                                    f"Processing failed ({error_code}) for Asset_ID={row['Asset_ID']}")
            if row["Processing_Retry_Count"] > 3:
                self._log_quality_issue("created_assets", "PRC_BIZ_EXCESSIVE_RETRIES",
                                        f"Retry_Count={row['Processing_Retry_Count']} for Asset_ID={row['Asset_ID']}")

        if _roll(r["sla_breach"]):
            row["SLA_Met"] = 0
            row["CPU_Time_Ms"] = random.randint(60_000, 300_000)
            self._log_quality_issue("created_assets", "PRC_TIME_SLA_BREACH",
                                    f"SLA breached for Asset_ID={row['Asset_ID']}, CPU_Time_Ms={row['CPU_Time_Ms']}")

        if _roll(r["low_quality"]):
            row["Quality_Score"] = round(random.uniform(0.0, 29.9), 1)
            self._log_quality_issue("created_assets", "PRC_BIZ_LOW_QUALITY",
                                    f"Quality_Score={row['Quality_Score']} for Asset_ID={row['Asset_ID']}")

        if _roll(r["no_thumbnail"]):
            row["Thumbnail_Generated"] = 0
            self._log_quality_issue("created_assets", "PRC_BIZ_NO_THUMBNAIL",
                                    f"No thumbnail for Asset_ID={row['Asset_ID']}")

        if _roll(r["temporal_inversion"]):
            # Swap start and end times
            row["Processing_Started_At"], row["Processing_Completed_At"] = (
                row["Processing_Completed_At"], row["Processing_Started_At"])
            self._log_quality_issue("created_assets", "PRC_CON_COMPLETED_BEFORE_START",
                                    f"Processing end before start for Asset_ID={row['Asset_ID']}")

        if _roll(r["null_fields"]):
            row["Output_Type"] = None
            self._log_quality_issue("created_assets", "PRC_COMP_MISSING_OUTPUT_TYPE",
                                    f"Missing Output_Type for Asset_ID={row['Asset_ID']}")

    def _seed_published_posts(self, count: int) -> None:
        asset_ids = [row["Asset_ID"] for row in self._tables["created_assets"]]
        channel_names = [row["Channel_Name"] for row in self._tables["channels"]]
        if not asset_ids:
            return
        for _ in range(count):
            asset_id = random.choice(asset_ids)
            # Find parent asset's create date
            parent_date = None
            for a in self._tables["created_assets"]:
                if a["Asset_ID"] == asset_id:
                    parent_date = a.get("Create_Date")
                    break

            publish_date = _random_date()
            if parent_date:
                try:
                    pd = datetime.strptime(parent_date, "%Y-%m-%d")
                    pub_d = pd + timedelta(days=random.randint(0, 14))
                    publish_date = pub_d.strftime("%Y-%m-%d")
                except ValueError:
                    pass

            scheduled_at = _random_iso_timestamp(publish_date, -random.randint(0, 7200))
            actual_publish = _random_iso_timestamp(publish_date, random.randint(0, 300))
            drift = random.randint(-60, 120)
            post_id = self._post_id.next()

            row: dict[str, Any] = {
                "Post_ID": post_id,
                "Asset_ID": asset_id,
                "Publish_Date": publish_date,
                "Published_Duration": random.randint(5, 1800),
                "API_Request_ID": str(uuid.uuid4()),
                "API_Response_Code": 200,
                "API_Latency_Ms": random.randint(50, 3000),
                "Rate_Limited": 0,
                "Auth_Token_Valid": 1,
                "Scheduled_At": scheduled_at,
                "Actual_Publish_Time": actual_publish,
                "Schedule_Drift_Seconds": drift,
                "Platform_Post_ID": f"plt_{_random_string(12)}",
                "Platform_Status": "LIVE",
                "Monetization_Eligible": random.choice([0, 1]),
                "Geo_Restricted": 0,
                "Publish_Status": "SUCCESS",
                "Publish_Retry_Count": 0,
                "Error_Code": None,
                "Error_Message": None,
            }

            self._inject_publishing_errors(row)
            self._insert_row("published_posts", row)

            if channel_names:
                self._seed_distribution(post_id, channel_names)

    def _inject_publishing_errors(self, row: dict[str, Any]) -> None:
        r = self._error_rates

        if _roll(r["publish_failure"]):
            row["Publish_Status"] = "FAILED"
            error_code = random.choice(PUBLISH_ERROR_CODES)
            row["Error_Code"] = error_code
            row["Error_Message"] = f"Publish failed: {error_code}"
            row["API_Response_Code"] = random.choice([400, 401, 403, 429, 500, 502, 503])
            row["Platform_Post_ID"] = None
            row["Platform_Status"] = "REJECTED"
            self._log_quality_issue("published_posts", "PUB_BIZ_PUBLISH_FAILED",
                                    f"Publish failed ({error_code}) for Post_ID={row['Post_ID']}")

        if _roll(r["rate_limited"]):
            row["Rate_Limited"] = 1
            row["API_Latency_Ms"] = random.randint(10_000, 60_000)
            self._log_quality_issue("published_posts", "PUB_BIZ_RATE_LIMITED",
                                    f"Rate limited for Post_ID={row['Post_ID']}")

        if _roll(r["content_rejected"]):
            row["Platform_Status"] = "REJECTED"
            row["Publish_Status"] = "FAILED"
            self._log_quality_issue("published_posts", "PUB_BIZ_CONTENT_REJECTED",
                                    f"Content rejected for Post_ID={row['Post_ID']}")

        if _roll(r["high_latency"]):
            row["API_Latency_Ms"] = random.randint(30_000, 120_000)
            self._log_quality_issue("published_posts", "PUB_TIME_HIGH_LATENCY",
                                    f"High latency {row['API_Latency_Ms']}ms for Post_ID={row['Post_ID']}")

        if _roll(r["schedule_drift"]):
            row["Schedule_Drift_Seconds"] = random.randint(3600, 86400)
            self._log_quality_issue("published_posts", "PUB_TIME_EXCESSIVE_DRIFT",
                                    f"Drift={row['Schedule_Drift_Seconds']}s for Post_ID={row['Post_ID']}")

        if _roll(r["auth_failure"]):
            row["Auth_Token_Valid"] = 0
            row["API_Response_Code"] = 401
            row["Publish_Status"] = "FAILED"
            row["Error_Code"] = "AUTH_FAILED"
            row["Error_Message"] = "Authentication token expired or invalid"
            self._log_quality_issue("published_posts", "PUB_BIZ_AUTH_FAILURE",
                                    f"Auth failure for Post_ID={row['Post_ID']}")

        if _roll(r["null_fields"]):
            row["API_Request_ID"] = None
            self._log_quality_issue("published_posts", "PUB_COMP_MISSING_API_REQUEST",
                                    f"Missing API_Request_ID for Post_ID={row['Post_ID']}")

        if _roll(r["future_date"]):
            future = (date.today() + timedelta(days=random.randint(60, 365))).isoformat()
            row["Publish_Date"] = future
            self._log_quality_issue("published_posts", "PUB_VAL_FUTURE_PUBLISH",
                                    f"Future Publish_Date={future} for Post_ID={row['Post_ID']}")

    def _seed_distribution(self, post_id: int, channel_names: list[str]) -> None:
        platform = random.choice(PLATFORMS)
        pub_url = _random_url("post")
        cdn_url = _random_url("cdn")
        thumb_url = _random_url("thumb")

        row: dict[str, Any] = {
            "Distribution_ID": self._distribution_id.next(),
            "Post_ID": post_id,
            "Channel_Name": random.choice(channel_names),
            "Published_Platform": platform,
            "Published_URL": pub_url,
            "CDN_URL": cdn_url,
            "CDN_Region": random.choice(CDN_REGIONS),
            "Embed_Code_Valid": 1,
            "Thumbnail_URL": thumb_url,
            "Thumbnail_URL_Valid": 1,
            "Distribution_Status": "ACTIVE",
            "Distributed_At": _now(),
            "Reach_Count": random.randint(0, 100_000),
        }

        self._inject_distribution_errors(row)
        self._insert_row("post_distribution", row)

    def _inject_distribution_errors(self, row: dict[str, Any]) -> None:
        r = self._error_rates

        if _roll(r["invalid_url"]):
            row["Published_URL"] = f"not-a-url-{_random_string(6)}"
            self._log_quality_issue("post_distribution", "DST_VAL_INVALID_URL",
                                    f"Invalid URL for Distribution_ID={row['Distribution_ID']}")

        if _roll(r["invalid_embed"]):
            row["Embed_Code_Valid"] = 0
            self._log_quality_issue("post_distribution", "DST_CON_EMBED_INVALID",
                                    f"Invalid embed code for Distribution_ID={row['Distribution_ID']}")

        if _roll(r["null_fields"]):
            target = random.choice(["Published_URL", "CDN_URL", "Published_Platform"])
            row[target] = None
            code_map = {"Published_URL": "DST_COMP_MISSING_URL", "CDN_URL": "DST_COMP_MISSING_CDN",
                        "Published_Platform": "DST_COMP_MISSING_PLATFORM"}
            self._log_quality_issue("post_distribution", code_map[target],
                                    f"Missing {target} for Distribution_ID={row['Distribution_ID']}")

        if _roll(r["negative_value"]):
            row["Reach_Count"] = -random.randint(1, 1000)
            self._log_quality_issue("post_distribution", "DST_VAL_NEGATIVE_REACH",
                                    f"Negative reach={row['Reach_Count']} for Distribution_ID={row['Distribution_ID']}")

    # ── batch loop ────────────────────────────────────────────────────

    def _loop(self) -> None:
        while self._running:
            try:
                self._run_batch()
                self._record_quality_snapshot()
            except Exception:
                pass
            time.sleep(self._batch_interval)

    def _run_batch(self) -> None:
        # Pipeline-ordered: mostly uploads, then processing, then publishing
        ops = [self._op_insert_upload, self._op_insert_process, self._op_insert_publish,
               self._op_update, self._op_delete]
        weights = [0.35, 0.30, 0.20, 0.12, 0.03]
        for _ in range(self._ops_per_batch):
            random.choices(ops, weights=weights, k=1)[0]()

    def _op_insert_upload(self) -> None:
        self._seed_raw_videos(1)

    def _op_insert_process(self) -> None:
        self._seed_created_assets(1)

    def _op_insert_publish(self) -> None:
        self._seed_published_posts(1)

    def _op_update(self) -> None:
        table = random.choice(["raw_videos", "created_assets", "users"])
        rows = self._tables[table]
        if not rows:
            return
        row = random.choice(rows)

        if table == "raw_videos":
            old_values = {"Headline": row["Headline"]}
            row["Headline"] = f"{random.choice(HEADLINES)} (Updated)"
            new_values = {"Headline": row["Headline"]}
        elif table == "created_assets":
            old_values = {"Output_Type": row["Output_Type"]}
            row["Output_Type"] = random.choice(OUTPUT_TYPES)
            new_values = {"Output_Type": row["Output_Type"]}
        else:
            old_values = {"Team_Name": row["Team_Name"]}
            row["Team_Name"] = random.choice(TEAM_NAMES)
            new_values = {"Team_Name": row["Team_Name"]}

        log_id = self._log_pending("UPDATE", table, row_id=self._row_id(table, row), old_values=old_values, new_values=new_values)
        self._mark_success(log_id)

    def _op_delete(self) -> None:
        table = random.choice(["raw_videos", "created_assets"])
        if not self._tables[table]:
            return

        row = random.choice(self._tables[table])
        log_id = self._log_pending("DELETE", table, row_id=self._row_id(table, row))

        if table == "raw_videos":
            video_id = row["Video_ID"]
            asset_ids = [asset["Asset_ID"] for asset in self._tables["created_assets"] if asset["Video_ID"] == video_id]
            post_ids = [post["Post_ID"] for post in self._tables["published_posts"] if post["Asset_ID"] in asset_ids]
            self._tables["post_distribution"] = [item for item in self._tables["post_distribution"] if item["Post_ID"] not in post_ids]
            self._tables["published_posts"] = [item for item in self._tables["published_posts"] if item["Post_ID"] not in post_ids]
            self._tables["created_assets"] = [item for item in self._tables["created_assets"] if item["Asset_ID"] not in asset_ids]
            self._tables["raw_video_channel"] = [item for item in self._tables["raw_video_channel"] if item["Video_ID"] != video_id]
            self._tables["raw_videos"] = [item for item in self._tables["raw_videos"] if item["Video_ID"] != video_id]
        else:
            asset_id = row["Asset_ID"]
            post_ids = [post["Post_ID"] for post in self._tables["published_posts"] if post["Asset_ID"] == asset_id]
            self._tables["post_distribution"] = [item for item in self._tables["post_distribution"] if item["Post_ID"] not in post_ids]
            self._tables["published_posts"] = [item for item in self._tables["published_posts"] if item["Post_ID"] not in post_ids]
            self._tables["created_assets"] = [item for item in self._tables["created_assets"] if item["Asset_ID"] != asset_id]

        self._mark_success(log_id)

    # ── quality score computation ─────────────────────────────────────

    def _safe_ratio(self, numerator: int, denominator: int) -> float:
        return numerator / denominator if denominator > 0 else 1.0

    def _compute_upload_quality(self) -> float:
        rows = self._tables["raw_videos"]
        if not rows:
            return 100.0
        n = len(rows)
        metadata_fields = ["Headline", "Source_URL", "File_Format", "Resolution_Width", "Checksum_SHA256"]
        complete = sum(1 for r in rows if all(r.get(f) is not None for f in metadata_fields))
        valid_format = sum(1 for r in rows if r.get("File_Format") in FILE_FORMATS)
        valid_codec = sum(1 for r in rows if r.get("Video_Codec") in VIDEO_CODECS)
        intact = sum(1 for r in rows if r.get("Is_Corrupted") == 0 and r.get("Checksum_SHA256"))
        success = sum(1 for r in rows if r.get("Upload_Status") == "COMPLETED")
        timely = sum(1 for r in rows if r.get("Retry_Count", 0) <= 2)

        score = (
            0.30 * self._safe_ratio(complete, n)
            + 0.20 * self._safe_ratio((valid_format + valid_codec), n * 2)
            + 0.15 * self._safe_ratio(intact, n)
            + 0.20 * self._safe_ratio(success, n)
            + 0.15 * self._safe_ratio(timely, n)
        ) * 100
        return round(max(0.0, min(100.0, score)), 1)

    def _compute_processing_quality(self) -> float:
        rows = self._tables["created_assets"]
        if not rows:
            return 100.0
        n = len(rows)
        success = sum(1 for r in rows if r.get("Processing_Status") == "COMPLETED")
        good_quality = sum(1 for r in rows if (r.get("Quality_Score") or 0) >= 50)
        sla_met = sum(1 for r in rows if r.get("SLA_Met") == 1)
        no_error = sum(1 for r in rows if r.get("Error_Code") is None)
        has_thumb = sum(1 for r in rows if r.get("Thumbnail_Generated") == 1)

        score = (
            0.30 * self._safe_ratio(success, n)
            + 0.25 * self._safe_ratio(good_quality, n)
            + 0.20 * self._safe_ratio(sla_met, n)
            + 0.15 * self._safe_ratio(no_error, n)
            + 0.10 * self._safe_ratio(has_thumb, n)
        ) * 100
        return round(max(0.0, min(100.0, score)), 1)

    def _compute_publishing_quality(self) -> float:
        posts = self._tables["published_posts"]
        dist = self._tables["post_distribution"]
        if not posts:
            return 100.0
        n = len(posts)
        api_success = sum(1 for r in posts if 200 <= (r.get("API_Response_Code") or 0) < 300)
        url_valid = sum(1 for r in dist if r.get("Published_URL") and URL_RE.match(str(r.get("Published_URL", ""))))
        url_total = max(len(dist), 1)
        schedule_ok = sum(1 for r in posts if abs(r.get("Schedule_Drift_Seconds") or 0) < 300)
        platform_live = sum(1 for r in posts if r.get("Platform_Status") == "LIVE")
        no_rate_limit = sum(1 for r in posts if r.get("Rate_Limited") == 0)

        score = (
            0.25 * self._safe_ratio(api_success, n)
            + 0.20 * self._safe_ratio(url_valid, url_total)
            + 0.20 * self._safe_ratio(schedule_ok, n)
            + 0.20 * self._safe_ratio(platform_live, n)
            + 0.15 * self._safe_ratio(no_rate_limit, n)
        ) * 100
        return round(max(0.0, min(100.0, score)), 1)

    def _record_quality_snapshot(self) -> None:
        scores = self.get_stage_quality_scores()
        self._quality_timeseries.append({
            "timestamp": _now()[:19],
            "upload": scores["upload"]["score"],
            "processing": scores["processing"]["score"],
            "publishing": scores["publishing"]["score"],
            "overall": scores["overall"],
        })

    # ── extended quality checks ───────────────────────────────────────

    def _check_nulls(self) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for table, required_columns in REQUIRED_COLUMNS.items():
            for row in self._tables[table]:
                for column in required_columns:
                    if row.get(column) is None:
                        issues.append({
                            "table": table, "check": "NULL_VIOLATION", "column": column,
                            "pk": {key: row.get(key) for key in PRIMARY_KEYS[table]},
                            "message": f"Required column '{column}' is NULL",
                        })
        return issues

    def _check_duplicate_pks(self) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for table, pk_columns in PRIMARY_KEYS.items():
            counts = Counter(tuple(row.get(column) for column in pk_columns) for row in self._tables[table])
            for values, count in counts.items():
                if count <= 1:
                    continue
                issues.append({
                    "table": table, "check": "DUPLICATE_PK", "columns": pk_columns,
                    "values": list(values), "duplicate_count": count,
                    "message": f"Duplicate PK detected for {table}",
                })
        return issues

    def _check_referential_integrity(self) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for child_table, child_column, parent_table, parent_column in FOREIGN_KEYS:
            parent_values = {row.get(parent_column) for row in self._tables[parent_table]}
            for row in self._tables[child_table]:
                value = row.get(child_column)
                if value is None or value in parent_values:
                    continue
                issues.append({
                    "table": child_table, "check": "FK_VIOLATION", "column": child_column,
                    "value": value, "references": f"{parent_table}.{parent_column}",
                    "pk": {key: row.get(key) for key in PRIMARY_KEYS[child_table]},
                    "message": f"Orphan FK: {child_table}.{child_column}={value}",
                })
        return issues

    def _check_non_negative(self) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for table, columns in NON_NEGATIVE_COLUMNS.items():
            for row in self._tables[table]:
                for column in columns:
                    value = row.get(column)
                    if value is not None and isinstance(value, (int, float)) and value < 0:
                        issues.append({
                            "table": table, "check": "NEGATIVE_VALUE", "column": column,
                            "value": value,
                            "pk": {key: row.get(key) for key in PRIMARY_KEYS[table]},
                            "message": f"Negative value in {table}.{column}",
                        })
        return issues

    def _check_date_formats(self) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for table, columns in DATE_COLUMNS.items():
            for row in self._tables[table]:
                for column in columns:
                    value = row.get(column)
                    if value is None:
                        continue
                    try:
                        datetime.strptime(str(value), "%Y-%m-%d")
                    except ValueError:
                        issues.append({
                            "table": table, "check": "INVALID_DATE", "column": column,
                            "value": value,
                            "pk": {key: row.get(key) for key in PRIMARY_KEYS[table]},
                            "message": f"Invalid date in {table}.{column}",
                        })
        return issues

    def _check_ranges(self) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for table, columns in RANGE_COLUMNS.items():
            for row in self._tables[table]:
                for column, (lo, hi) in columns.items():
                    value = row.get(column)
                    if value is None:
                        continue
                    if not isinstance(value, (int, float)):
                        continue
                    if value < lo or value > hi:
                        issues.append({
                            "table": table, "check": "OUT_OF_RANGE", "column": column,
                            "value": value, "range": [lo, hi],
                            "pk": {key: row.get(key) for key in PRIMARY_KEYS[table]},
                            "message": f"{table}.{column}={value} out of range [{lo}, {hi}]",
                        })
        return issues

    def _check_enums(self) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for table, columns in ENUM_COLUMNS.items():
            for row in self._tables[table]:
                for column, allowed in columns.items():
                    value = row.get(column)
                    if value is None:
                        continue
                    if value not in allowed:
                        issues.append({
                            "table": table, "check": "INVALID_ENUM", "column": column,
                            "value": value, "allowed": allowed,
                            "pk": {key: row.get(key) for key in PRIMARY_KEYS[table]},
                            "message": f"{table}.{column}='{value}' not in allowed values",
                        })
        return issues

    def _check_urls(self) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for table, columns in URL_COLUMNS.items():
            for row in self._tables[table]:
                for column in columns:
                    value = row.get(column)
                    if value is None:
                        continue
                    if not URL_RE.match(str(value)):
                        issues.append({
                            "table": table, "check": "INVALID_URL", "column": column,
                            "value": value,
                            "pk": {key: row.get(key) for key in PRIMARY_KEYS[table]},
                            "message": f"Invalid URL in {table}.{column}",
                        })
        return issues

    def _check_temporal_order(self) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        # Upload: started < completed
        for row in self._tables["raw_videos"]:
            s, e = row.get("Upload_Started_At"), row.get("Upload_Completed_At")
            if s and e and str(s) > str(e):
                issues.append({
                    "table": "raw_videos", "check": "TEMPORAL_INVERSION",
                    "message": f"Upload_Started_At > Upload_Completed_At for Video_ID={row.get('Video_ID')}",
                    "pk": {"Video_ID": row.get("Video_ID")},
                })
        # Processing: started < completed
        for row in self._tables["created_assets"]:
            s, e = row.get("Processing_Started_At"), row.get("Processing_Completed_At")
            if s and e and str(s) > str(e):
                issues.append({
                    "table": "created_assets", "check": "TEMPORAL_INVERSION",
                    "message": f"Processing_Started_At > Processing_Completed_At for Asset_ID={row.get('Asset_ID')}",
                    "pk": {"Asset_ID": row.get("Asset_ID")},
                })
        return issues

    def _check_business_logic(self) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        # Processing completed but has error code
        for row in self._tables["created_assets"]:
            if row.get("Processing_Status") == "COMPLETED" and row.get("Error_Code"):
                issues.append({
                    "table": "created_assets", "check": "LOGIC_VIOLATION",
                    "message": f"Processing COMPLETED but Error_Code={row.get('Error_Code')} for Asset_ID={row.get('Asset_ID')}",
                    "pk": {"Asset_ID": row.get("Asset_ID")},
                })
            if row.get("Processing_Status") == "FAILED" and not row.get("Error_Code"):
                issues.append({
                    "table": "created_assets", "check": "LOGIC_VIOLATION",
                    "message": f"Processing FAILED but no Error_Code for Asset_ID={row.get('Asset_ID')}",
                    "pk": {"Asset_ID": row.get("Asset_ID")},
                })
        # Publishing success but has error
        for row in self._tables["published_posts"]:
            if row.get("Publish_Status") == "SUCCESS" and row.get("Error_Code"):
                issues.append({
                    "table": "published_posts", "check": "LOGIC_VIOLATION",
                    "message": f"Publish SUCCESS but Error_Code={row.get('Error_Code')} for Post_ID={row.get('Post_ID')}",
                    "pk": {"Post_ID": row.get("Post_ID")},
                })
            if row.get("Auth_Token_Valid") == 0 and row.get("Publish_Status") == "SUCCESS":
                issues.append({
                    "table": "published_posts", "check": "LOGIC_VIOLATION",
                    "message": f"Auth_Token_Valid=0 but SUCCESS for Post_ID={row.get('Post_ID')}",
                    "pk": {"Post_ID": row.get("Post_ID")},
                })
        # Distribution active but no URL
        for row in self._tables["post_distribution"]:
            if row.get("Distribution_Status") == "ACTIVE" and not row.get("Published_URL"):
                issues.append({
                    "table": "post_distribution", "check": "LOGIC_VIOLATION",
                    "message": f"ACTIVE but no Published_URL for Distribution_ID={row.get('Distribution_ID')}",
                    "pk": {"Distribution_ID": row.get("Distribution_ID")},
                })
        return issues
