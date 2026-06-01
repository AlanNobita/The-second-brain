import logging
import subprocess
import json
import os
import tempfile
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class TranscriptError(Exception):
    pass


def extract_video_id(url):
    parsed = urlparse(url)
    if parsed.hostname == "youtu.be":
        return parsed.path.strip("/")
    path = parsed.path.strip("/")
    for prefix in ("embed/", "shorts/", "v/"):
        if path.startswith(prefix):
            return path[len(prefix):]
    qs = parse_qs(parsed.query)
    return qs.get("v", [None])[0]


def extract_channel_id(url):
    path = urlparse(url).path.strip("/")
    if path.startswith("@"):
        return path
    parts = path.split("/")
    if len(parts) >= 2:
        return parts[-1]
    return path


def fetch_transcript(video_url):
    video_id = extract_video_id(video_url)
    if not video_id:
        raise TranscriptError(f"Could not extract video ID from {video_url}")

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join(segment["text"] for segment in transcript_list)
    except Exception as e:
        logger.debug("youtube-transcript-api failed for %s: %s", video_url, e)

    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".srt", delete=False, prefix=f"yt_{video_id}_")
        tmp_path = tmp.name
        tmp.close()
        subprocess.run(
            ["yt-dlp", "--skip-download", "--write-auto-sub", "--sub-lang", "en",
             "--convert-subs", "srt", "-o", tmp_path.replace(".srt", ""), video_url],
            capture_output=True, text=True, timeout=60
        )
        srt_path = tmp_path.replace(".srt", ".en.srt")
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        if os.path.exists(srt_path):
            with open(srt_path, "r") as f:
                raw = f.read()
            os.unlink(srt_path)
            return _strip_srt(raw)
    except Exception as e:
        logger.debug("yt-dlp failed for %s: %s", video_url, e)

    raise TranscriptError(f"No captions available for {video_url}")


def _strip_srt(srt_text):
    import re as _re
    lines = srt_text.split("\n")
    text_lines = []
    for line in lines:
        line = line.strip()
        if line.isdigit():
            continue
        if "-->" in line:
            continue
        line = _re.sub(r"<[^>]+>", "", line).strip()
        if line:
            text_lines.append(line)
    return " ".join(text_lines)


def search_youtube(query, max_results=5):
    try:
        result = subprocess.run(
            ["yt-dlp", f"ytsearch{max_results}:{query}", "--dump-json", "--no-warnings"],
            capture_output=True, text=True, timeout=30
        )
        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            data = json.loads(line)
            videos.append({
                "video_id": data["id"],
                "title": data["title"],
                "channel": data.get("channel", "Unknown"),
                "channel_url": data.get("channel_url", ""),
                "published_at": data.get("upload_date", ""),
                "url": f"https://youtube.com/watch?v={data['id']}",
            })
        return videos[:max_results]
    except Exception as e:
        logger.warning("YouTube search failed for %s: %s", query, e)
        return []


def get_channel_videos(channel_url, max_results=5):
    try:
        result = subprocess.run(
            ["yt-dlp", "--flat-playlist", "--dump-json", "--no-warnings",
             "--playlist-end", str(max_results), channel_url],
            capture_output=True, text=True, timeout=30
        )
        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            data = json.loads(line)
            videos.append({
                "video_id": data["id"],
                "title": data["title"],
                "channel": data.get("channel", data.get("uploader", "Unknown")),
                "channel_url": channel_url,
                "published_at": data.get("upload_date", ""),
                "url": f"https://youtube.com/watch?v={data['id']}",
            })
        return videos[:max_results]
    except Exception as e:
        logger.warning("get_channel_videos failed for %s: %s", channel_url, e)
        return []
