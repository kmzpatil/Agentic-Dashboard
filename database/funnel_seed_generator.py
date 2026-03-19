from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


BASE_UPLOADS = 4453
BASE_CREATED = 14916
BASE_PUBLISHED = 111

CLIENT_CHANNEL_MAP = {
    "Client 1": list("ABCDEFGHIJKLMNOPQR"),
    "Client 2": [f"C2_Channel_{i}" for i in range(1, 13)],
    "Client 3": [f"C3_Channel_{i}" for i in range(1, 16)],
    "Client 4": [f"C4_Channel_{i}" for i in range(1, 11)],
}
CLIENTS = list(CLIENT_CHANNEL_MAP.keys())

TEAMS = [
    "Unknown", "Team Name_a8d7", "Video Ops Beta", "News Desk Beta",
    "Social Media Squad", "QA Ninjas", "Frammer Studio",
    "Delta Creators", "Delta Publishers",
]

BASE_USERS = [
    "Chandan", "QA-Purushottam", "vikas.s@moolya.com", "Sandeep Belaki", "Nitesh",
    "Abhishek", "Auto Upload", "Subhesh", "Trivendra",
    "Dheeraj Pareek(QA theveritycorp.com)", "vinay singh", "Neha",
    "Subhash (moolya)", "Adarsh (Frammer)", "Anamika Singh", "AB",
    "Divyanshu Dutta Roy", "Ashween", "Vaibhav", "Alok Rai", "sukhleen", "Shadab",
    "Abhishek Sri", "QA-Bhargavi", "Deepika Uniyal (QA testaing.com)",
    "Prithviraj", "Rakesh (devops@frammer.com)", "Harish", "QA-Ankith ",
    "Ravi Pratap Rai", "QA-Aniket", "Kallol Pratim", "Ritwik", "Richa",
    "deleteme@frammer.com", "Kawaljit Singh Bedi", "Safdar", "Arun J", "QA-Amit",
    "Test User", "Arijit Chatterjee", "swathi.bharadwaj@moolya.com", "parakh",
    "Dheerendra Kumar", "Sumit (Frammer)",
]
MOCK_USERS = [f"Mock_User_{i}@example.com" for i in range(1, 101)]
ALL_USERS = BASE_USERS + MOCK_USERS

INPUT_TYPES = [
    "interview", "news bulletin", "special reports",
    "speech", "debate", "press conference",
    "discussion-show", "podcast", "sports show",
    "drama", "in-brief",
]
INPUT_WEIGHTS = [
    0.29, 0.23, 0.17, 0.13, 0.09, 0.06,
    0.015, 0.005, 0.005, 0.002, 0.003,
]

LANGUAGES = ["en", "hi", "mix", "es", "ar", "mr"]
BASE_LANG_WEIGHTS = [2647 / 4453, 1792 / 4453, 11 / 4453, 1 / 4453, 1 / 4453, 1 / 4453]

PLATFORMS = ["Facebook", "Instagram", "Linkedin", "Reels", "Shorts", "X", "Youtube", "Threads"]
OUTPUT_TYPES = ["Full package", "Key moments", "My Key moments", "Summary", "Chapters"]

START_DATE = datetime(2025, 3, 1)
END_DATE = datetime(2026, 2, 28)


def _build_client_targets() -> dict[str, dict[str, int]]:
    targets = {
        "Client 1": {
            "uploads": BASE_UPLOADS,
            "created": BASE_CREATED,
            "published": BASE_PUBLISHED,
        }
    }
    for i in range(2, 5):
        client = f"Client {i}"
        variance = random.uniform(-0.10, 0.10)
        targets[client] = {
            "uploads": int(BASE_UPLOADS * (1 + variance)),
            "created": int(BASE_CREATED * (1 + variance)),
            "published": int(BASE_PUBLISHED * (1 + variance)),
        }
    return targets


def _build_client_rate_map(client_targets: dict[str, dict[str, int]]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for client, targets in client_targets.items():
        out[client] = {
            "upload_to_created": targets["created"] / max(targets["uploads"], 1),
        }
    return out


def _build_client_lang_map() -> dict[str, list[float]]:
    lang_map = {"Client 1": BASE_LANG_WEIGHTS}
    for client in ["Client 2", "Client 3", "Client 4"]:
        varied_weights = [weight * (1 + random.uniform(-0.10, 0.10)) for weight in BASE_LANG_WEIGHTS]
        total_weight = sum(varied_weights)
        lang_map[client] = [weight / total_weight for weight in varied_weights]
    return lang_map


def _date_str(value: datetime) -> str:
    return value.strftime("%Y-%m-%d")


def generate_users() -> pd.DataFrame:
    rows = []
    for index, user_name in enumerate(ALL_USERS, start=1):
        client_name = CLIENTS[(index - 1) % len(CLIENTS)]
        rows.append(
            {
                "User_ID": index,
                "User_Name": user_name,
                "Team_Name": random.choice(TEAMS),
                "Client_Name": client_name,
            }
        )
    return pd.DataFrame(rows)


def generate_clients() -> pd.DataFrame:
    return pd.DataFrame([{"Client_Name": client} for client in CLIENTS])


def generate_channels() -> pd.DataFrame:
    rows = []
    for client, channels in CLIENT_CHANNEL_MAP.items():
        for channel_name in channels:
            rows.append({"Channel_Name": channel_name, "Client_Name": client})
    return pd.DataFrame(rows)


def _duration_based_asset_count(uploaded_duration: int, base_rate: float) -> int:
    reference_duration = 600
    duration_factor = uploaded_duration / reference_duration
    lam = base_rate * duration_factor
    n_assets = np.random.poisson(lam)
    return min(max(1, int(n_assets)), 20)


def generate_raw_videos(
    users_df: pd.DataFrame,
    client_targets: dict[str, dict[str, int]],
    client_lang_map: dict[str, list[float]],
) -> pd.DataFrame:
    rows = []
    video_id = 1

    users_by_client = {
        client: users_df[users_df["Client_Name"] == client].copy()
        for client in CLIENTS
    }

    for client, targets in client_targets.items():
        user_pool = users_by_client[client]
        for _ in range(targets["uploads"]):
            user = user_pool.sample(1).iloc[0]
            upload_date = START_DATE + timedelta(days=random.randint(0, (END_DATE - START_DATE).days))

            if client == "Client 3":
                input_type = random.choice(["podcast", "interview"])
                duration = random.randint(1800, 3600)
            elif client == "Client 4":
                input_type = random.choice(["press conference", "speech"])
                duration = random.randint(3600, 10800)
            else:
                input_type = str(np.random.choice(INPUT_TYPES, p=INPUT_WEIGHTS))
                duration = max(60, int(np.random.normal(600, 250)))

            rows.append(
                {
                    "Video_ID": video_id,
                    "Client_Name": client,
                    "Headline": f"Headline_{video_id}",
                    "Source_URL": f"https://objectstorage/video/{video_id}",
                    "User_ID": int(user["User_ID"]),
                    "Upload_Date": _date_str(upload_date),
                    "Input_Type": input_type,
                    "Language": str(np.random.choice(LANGUAGES, p=client_lang_map[client])),
                    "Uploaded_Duration": int(duration),
                }
            )
            video_id += 1

    return pd.DataFrame(rows)


def generate_raw_video_channel(videos_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, video in videos_df.iterrows():
        available_channels = CLIENT_CHANNEL_MAP[video["Client_Name"]]
        channel_count = min(random.randint(1, 3), len(available_channels))
        selected_channels = random.sample(available_channels, channel_count)
        for channel_name in selected_channels:
            rows.append({"Video_ID": int(video["Video_ID"]), "Channel_Name": channel_name})
    return pd.DataFrame(rows)


def generate_created_assets(
    videos_df: pd.DataFrame,
    client_targets: dict[str, dict[str, int]],
    client_rate_map: dict[str, dict[str, float]],
) -> pd.DataFrame:
    rows: list[dict] = []

    for client, group in videos_df.groupby("Client_Name"):
        client_target = client_targets[client]["created"]
        base_rate = client_rate_map[client]["upload_to_created"]
        client_rows: list[dict] = []

        for _, video in group.iterrows():
            asset_count = _duration_based_asset_count(int(video["Uploaded_Duration"]), base_rate)
            for _ in range(asset_count):
                create_date = datetime.strptime(video["Upload_Date"], "%Y-%m-%d") + timedelta(days=random.randint(0, 2))
                client_rows.append(
                    {
                        "Video_ID": int(video["Video_ID"]),
                        "Output_Type": random.choice(OUTPUT_TYPES),
                        "Create_Date": _date_str(create_date),
                        "Created_Duration": int(int(video["Uploaded_Duration"]) * random.uniform(0.3, 0.6)),
                    }
                )

        client_df = pd.DataFrame(client_rows)
        if len(client_df) > client_target:
            client_df = client_df.sample(client_target)
        elif len(client_df) < client_target and not client_df.empty:
            diff = client_target - len(client_df)
            extra = client_df.sample(diff, replace=True).copy()
            client_df = pd.concat([client_df, extra], ignore_index=True)

        rows.extend(client_df.to_dict("records"))

    final_df = pd.DataFrame(rows).sample(frac=1).reset_index(drop=True)
    final_df.insert(0, "Asset_ID", range(1, len(final_df) + 1))
    return final_df


def generate_published_posts(
    assets_df: pd.DataFrame,
    videos_df: pd.DataFrame,
    client_targets: dict[str, dict[str, int]],
) -> pd.DataFrame:
    merged = assets_df.merge(videos_df[["Video_ID", "Client_Name"]], on="Video_ID", how="left")
    rows: list[dict] = []

    for client, group in merged.groupby("Client_Name"):
        client_target = client_targets[client]["published"]
        actual_target = min(client_target, len(group))
        selected = group.sample(actual_target)

        for _, asset in selected.iterrows():
            publish_date = datetime.strptime(asset["Create_Date"], "%Y-%m-%d") + timedelta(days=random.randint(0, 3))
            rows.append(
                {
                    "Asset_ID": int(asset["Asset_ID"]),
                    "Publish_Date": _date_str(publish_date),
                    "Published_Duration": int(int(asset["Created_Duration"]) * random.uniform(0.4, 0.8)),
                }
            )

    final_df = pd.DataFrame(rows).sample(frac=1).reset_index(drop=True)
    final_df.insert(0, "Post_ID", range(1, len(final_df) + 1))
    return final_df


def generate_post_distribution(posts_df: pd.DataFrame, assets_df: pd.DataFrame, videos_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    asset_video_map = dict(zip(assets_df["Asset_ID"], assets_df["Video_ID"]))
    video_client_map = dict(zip(videos_df["Video_ID"], videos_df["Client_Name"]))

    for _, post in posts_df.iterrows():
        video_id = int(asset_video_map[int(post["Asset_ID"])])
        client_name = str(video_client_map[video_id])
        available_channels = CLIENT_CHANNEL_MAP[client_name]
        assigned_channel = random.choice(available_channels)

        if client_name == "Client 3":
            platform_pool = ["X", "Threads", "Youtube"]
        elif client_name == "Client 4":
            platform_pool = ["Linkedin", "Youtube", "Facebook"]
        else:
            platform_pool = PLATFORMS

        platform_count = min(random.randint(1, 3), len(platform_pool))
        platforms = random.sample(platform_pool, platform_count)
        for platform in platforms:
            rows.append(
                {
                    "Post_ID": int(post["Post_ID"]),
                    "Channel_Name": assigned_channel,
                    "Published_Platform": platform,
                    "Published_URL": f"https://{platform.lower()}.com/p/{int(post['Post_ID'])}",
                }
            )

    return pd.DataFrame(rows)


def generate_funnel_seed_tables(seed: int = 42) -> dict[str, pd.DataFrame]:
    random.seed(seed)
    np.random.seed(seed)

    client_targets = _build_client_targets()
    client_rate_map = _build_client_rate_map(client_targets)
    client_lang_map = _build_client_lang_map()

    users = generate_users()
    clients = generate_clients()
    channels = generate_channels()
    raw_videos = generate_raw_videos(users, client_targets, client_lang_map)
    raw_video_channel = generate_raw_video_channel(raw_videos)
    created_assets = generate_created_assets(raw_videos, client_targets, client_rate_map)
    published_posts = generate_published_posts(created_assets, raw_videos, client_targets)
    post_distribution = generate_post_distribution(published_posts, created_assets, raw_videos)

    raw_videos = raw_videos.drop(columns=["Client_Name"])

    return {
        "users": users,
        "clients": clients,
        "channels": channels,
        "raw_videos": raw_videos,
        "raw_video_channel": raw_video_channel,
        "created_assets": created_assets,
        "published_posts": published_posts,
        "post_distribution": post_distribution,
    }


def write_seed_csvs(output_dir: Path, seed: int = 42) -> dict[str, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    tables = generate_funnel_seed_tables(seed=seed)

    counts: dict[str, int] = {}
    for table_name, dataframe in tables.items():
        dataframe.to_csv(output_dir / f"{table_name}.csv", index=False)
        counts[table_name] = len(dataframe)
    return counts


def main() -> None:
    output_dir = Path.cwd()
    counts = write_seed_csvs(output_dir)
    print("Generated funnel seed CSV files:")
    for table_name, row_count in counts.items():
        print(f"- {table_name}: {row_count} rows")


if __name__ == "__main__":
    main()