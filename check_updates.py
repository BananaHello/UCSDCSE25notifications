#!/usr/bin/env python3
"""
GitHub Pages Change Tracker
Monitors URLs defined in links.txt for changes and sends Discord notifications.
"""

import hashlib
import json
import os
import sys
import requests
from pathlib import Path
from urllib.parse import urlparse
import difflib
from bs4 import BeautifulSoup


CONFIG_FILE = "config.json"
LINKS_FILE = "links.txt"
HASHES_DIR = "hashes"


def load_config():
    """Load config.json. Returns defaults if file is missing."""
    config_path = Path(CONFIG_FILE)
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {"enabled": True}


def load_links():
    """
    Read links.txt and return a list of (label, url) tuples.
    Supports "Label | URL" format or bare URLs. Skips blank lines and # comments.
    """
    links_path = Path(LINKS_FILE)
    if not links_path.exists():
        return []

    entries = []
    for line in links_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            label, _, url = line.partition("|")
            label = label.strip()
            url = url.strip()
        else:
            url = line
            parsed = urlparse(url)
            label = (parsed.netloc + parsed.path).rstrip("/")
        entries.append((label, url))
    return entries


def url_to_id(url):
    """Return a stable 16-char ID for a URL, used for filenames."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def fetch_page_content(url):
    """Fetch the full HTML content of the target URL."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None


def compute_hash(content):
    """Compute SHA256 hash of the content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def read_file(path):
    """Read a file and return its text, or None if it doesn't exist."""
    p = Path(path)
    return p.read_text() if p.exists() else None


def extract_text_content(html):
    """Extract visible text content from HTML, preserving structure."""
    soup = BeautifulSoup(html, "html.parser")
    for script in soup(["script", "style"]):
        script.decompose()
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return "\n".join(chunk for chunk in chunks if chunk)


def get_meaningful_diff(old_content, new_content, max_lines=20):
    """Generate a meaningful diff summary from two HTML pages."""
    old_text = extract_text_content(old_content)
    new_text = extract_text_content(new_content)

    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm="", n=0))

    if not diff:
        return "Changes detected but no clear diff available."

    meaningful_changes = []
    for line in diff[3:]:
        if line.startswith("+") and not line.startswith("+++"):
            clean_line = line[1:].strip()
            if clean_line and len(clean_line) > 2:
                meaningful_changes.append(f"➕ {clean_line}")
        elif line.startswith("-") and not line.startswith("---"):
            clean_line = line[1:].strip()
            if clean_line and len(clean_line) > 2:
                meaningful_changes.append(f"➖ {clean_line}")

    if not meaningful_changes:
        return "Minor changes detected (likely formatting or whitespace)."

    if len(meaningful_changes) > max_lines:
        summary = "\n".join(meaningful_changes[:max_lines])
        summary += f"\n... and {len(meaningful_changes) - max_lines} more changes"
        return summary

    return "\n".join(meaningful_changes)


def send_discord_notification(webhook_url, message):
    """Send a notification to Discord via webhook."""
    try:
        response = requests.post(webhook_url, json={"content": message}, timeout=10)
        response.raise_for_status()
        print("Discord notification sent successfully")
    except requests.RequestException as e:
        print(f"Error sending Discord notification: {e}", file=sys.stderr)


def check_url(label, url, discord_webhook):
    """Check a single URL for changes and send a Discord notification."""
    uid = url_to_id(url)
    hash_file = Path(HASHES_DIR) / f"{uid}_hash.txt"
    content_file = Path(HASHES_DIR) / f"{uid}_content.txt"

    print(f"Fetching [{label}] {url}...")
    content = fetch_page_content(url)
    if content is None:
        send_discord_notification(
            discord_webhook,
            f"⚠️ **{label}** could not be reached: {url}",
        )
        return

    current_hash = compute_hash(content)
    previous_hash = read_file(hash_file)
    previous_content = read_file(content_file)

    if previous_hash is None:
        print(f"  First run for [{label}]")
        Path(hash_file).write_text(current_hash)
        Path(content_file).write_text(content)
        send_discord_notification(
            discord_webhook,
            f"🎉 Now monitoring **{label}** ({url})",
        )
    elif current_hash != previous_hash:
        print(f"  Content changed for [{label}]")
        diff_summary = ""
        if previous_content:
            diff_summary = get_meaningful_diff(previous_content, content)
            print(f"  Changes:\n{diff_summary}")

        Path(hash_file).write_text(current_hash)
        Path(content_file).write_text(content)

        message = f"📢 **{label}** updated! Check it out: {url}"
        if diff_summary:
            message += f"\n\n**Changes:**\n```\n{diff_summary}\n```"
        send_discord_notification(discord_webhook, message)
    else:
        print(f"  No changes for [{label}]")
        send_discord_notification(
            discord_webhook,
            f"✅ **{label}** checked — no changes detected",
        )


def main():
    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
    if not discord_webhook:
        print("Error: DISCORD_WEBHOOK_URL environment variable not set", file=sys.stderr)
        sys.exit(1)

    config = load_config()
    if not config.get("enabled", True):
        print("Notifications are disabled (config.json: enabled=false). Exiting.")
        sys.exit(0)

    links = load_links()
    if not links:
        print(f"No URLs to monitor. Add entries to {LINKS_FILE}.", file=sys.stderr)
        sys.exit(1)

    Path(HASHES_DIR).mkdir(exist_ok=True)

    for label, url in links:
        check_url(label, url, discord_webhook)


if __name__ == "__main__":
    main()
