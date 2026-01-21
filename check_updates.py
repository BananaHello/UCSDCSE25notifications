#!/usr/bin/env python3
"""
GitHub Pages Change Tracker
Monitors https://ucsd-cse25.github.io/schedule/ for changes and sends Discord notifications.
"""

import hashlib
import os
import sys
import requests
from pathlib import Path


TARGET_URL = "https://ucsd-cse25.github.io/schedule/"
HASH_FILE = "last_hash.txt"


def fetch_page_content(url):
    """Fetch the full HTML content of the target URL."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching page: {e}", file=sys.stderr)
        sys.exit(1)


def compute_hash(content):
    """Compute SHA256 hash of the content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def read_previous_hash(hash_file):
    """Read the previous hash from file. Returns None if file doesn't exist."""
    hash_path = Path(hash_file)
    if hash_path.exists():
        return hash_path.read_text().strip()
    return None


def save_hash(hash_file, hash_value):
    """Save the hash to file."""
    Path(hash_file).write_text(hash_value)


def send_discord_notification(webhook_url, message):
    """Send a notification to Discord via webhook."""
    try:
        payload = {"content": message}
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        print("Discord notification sent successfully")
    except requests.RequestException as e:
        print(f"Error sending Discord notification: {e}", file=sys.stderr)
        # Don't exit - we still want to save the hash


def main():
    # Get Discord webhook URL from environment variable
    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
    if not discord_webhook:
        print("Error: DISCORD_WEBHOOK_URL environment variable not set", file=sys.stderr)
        sys.exit(1)

    # Fetch current page content
    print(f"Fetching content from {TARGET_URL}...")
    content = fetch_page_content(TARGET_URL)

    # Compute hash
    current_hash = compute_hash(content)
    print(f"Current hash: {current_hash}")

    # Read previous hash
    previous_hash = read_previous_hash(HASH_FILE)

    if previous_hash is None:
        # First run
        print("No previous hash found - this is the first run")
        save_hash(HASH_FILE, current_hash)
        message = f"🎉 Schedule monitoring started! Tracking changes at {TARGET_URL}"
        send_discord_notification(discord_webhook, message)
    elif current_hash != previous_hash:
        # Content changed
        print("Content has changed!")
        save_hash(HASH_FILE, current_hash)
        message = f"📢 Schedule page updated! Check it out: {TARGET_URL}"
        send_discord_notification(discord_webhook, message)
    else:
        # No change
        print("No changes detected")
        message = f"✅ Schedule checked - no changes detected at {TARGET_URL}"
        send_discord_notification(discord_webhook, message)


if __name__ == "__main__":
    main()
