import os
import re
from openai import OpenAI
from openai import APIError, APITimeoutError
from flask import current_app
import requests


def debloat_and_structure(transcript, video_title, channel):
    system_prompt = """You are a note-taking AI. Extract substance from a YouTube transcript.

RULES (strict):
1. Extract ONLY content present in the transcript. No additions, inferences, or summaries.
2. Remove: greetings ("hey guys", "welcome back"), sponsor segments, channel plugs, CTAs, off-topic banter.
3. Preserve: ALL data points, arguments, examples, code, quotes, statistics, references, tools, people, timelines.
4. Organize by ## topic sections. Use natural topic shifts in the transcript as boundaries.
5. Code blocks: verbatim with ``` fences.
6. Do NOT condense. Full substance without filler.
7. Do not guess. Omit or mark [unclear] if not in transcript.
8. No imaginary content. No elaborating on what the speaker said.

Format:
## Key Concepts
- ...

## Notes
[de-bloated full context organized by topic]

## Takeaways
- ...

## References
- ..."""

    try:
        client = OpenAI(
            api_key=current_app.config["OPENROUTER_API_KEY"],
            base_url=current_app.config["OPENROUTER_BASE_URL"],
        )
        model = current_app.config.get("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Title: {video_title}\nChannel: {channel}\n\nTranscript:\n{transcript}"}
            ]
        )
        return response.choices[0].message.content
    except (APIError, APITimeoutError, requests.RequestException, KeyError, RuntimeError) as e:
        import logging
        logging.getLogger(__name__).warning("OpenRouter de-bloat failed: %s", e)
        return _fallback_debloat(transcript, video_title, channel)


def _fallback_debloat(transcript, video_title, channel):
    lines = transcript.split("\n")
    cleaned = []
    skip_phrases = [
        "hey guys", "welcome back", "don't forget to like", "like and subscribe",
        "hit that bell", "thanks to our sponsor", "check them out", "raid shadow legends",
        "before we start", "make sure to"
    ]
    for line in lines:
        lower = line.strip().lower()
        if any(phrase in lower for phrase in skip_phrases):
            continue
        cleaned.append(line)
    text = "\n".join(cleaned)
    return f"# {video_title}\n\n**Channel:** {channel}\n\n## Notes\n\n{text.strip()}\n\n## Takeaways\n\n-\n\n## References\n\n-"


def save_note_file(markdown, video_title, ingested_date, output_dir=None):
    if output_dir is None:
        output_dir = os.environ.get("OBSIDIAN_NOTES_PATH",
                                    os.path.join(os.path.dirname(__file__), "..", "..", "obsidian-ingest"))
    os.makedirs(output_dir, exist_ok=True)
    safe_title = re.sub(r'[^\w\s-]', '', video_title).strip().replace(' ', '-')[:80]
    filename = f"{ingested_date}-{safe_title}.md"
    filepath = os.path.join(output_dir, filename)
    try:
        with open(filepath, "w") as f:
            f.write(markdown)
    except OSError as e:
        raise IOError(f"Failed to write note file at {filepath}: {e}") from e
    return filepath
