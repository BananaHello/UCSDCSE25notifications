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
import difflib
from bs4 import BeautifulSoup
import re


TARGET_URL = "https://ucsd-cse25.github.io/schedule/"
HASH_FILE = "last_hash.txt"
CONTENT_FILE = "last_content.txt"


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


def read_previous_content(content_file):
    """Read the previous content from file. Returns None if file doesn't exist."""
    content_path = Path(content_file)
    if content_path.exists():
        return content_path.read_text()
    return None


def save_content(content_file, content):
    """Save the content to file."""
    Path(content_file).write_text(content)


def extract_text_content(html):
    """Extract visible text content from HTML, preserving structure."""
    soup = BeautifulSoup(html, 'html.parser')

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Get text and clean it up
    text = soup.get_text()

    # Break into lines and remove leading/trailing space
    lines = (line.strip() for line in text.splitlines())

    # Break multi-headlines into a line each and filter out blanks
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))

    # Filter out empty lines
    text = '\n'.join(chunk for chunk in chunks if chunk)

    return text


def get_meaningful_diff(old_content, new_content, max_lines=20):
    """Generate a meaningful diff summary, focusing on visible content changes."""
    # Extract text content from HTML
    old_text = extract_text_content(old_content)
    new_text = extract_text_content(new_content)

    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    # Generate unified diff
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm='', n=0))

    if not diff:
        return "Changes detected but no clear diff available."

    # Filter out metadata lines and keep only actual changes
    meaningful_changes = []
    for line in diff[3:]:  # Skip the first 3 header lines
        if line.startswith('+') and not line.startswith('+++'):
            clean_line = line[1:].strip()
            if clean_line and len(clean_line) > 2:  # Filter out very short lines
                meaningful_changes.append(f"➕ {clean_line}")
        elif line.startswith('-') and not line.startswith('---'):
            clean_line = line[1:].strip()
            if clean_line and len(clean_line) > 2:  # Filter out very short lines
                meaningful_changes.append(f"➖ {clean_line}")

    if not meaningful_changes:
        return "Minor changes detected (likely formatting or whitespace)."

    # Limit to max_lines to avoid overwhelming Discord message
    if len(meaningful_changes) > max_lines:
        summary = '\n'.join(meaningful_changes[:max_lines])
        summary += f"\n... and {len(meaningful_changes) - max_lines} more changes"
        return summary

    return '\n'.join(meaningful_changes)


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

    # Read previous hash and content
    previous_hash = read_previous_hash(HASH_FILE)
    previous_content = read_previous_content(CONTENT_FILE)

    if previous_hash is None:
        # First run
        print("No previous hash found - this is the first run")
        save_hash(HASH_FILE, current_hash)
        save_content(CONTENT_FILE, content)
        message = f"🎉 Schedule monitoring started! Tracking changes at {TARGET_URL}"
        send_discord_notification(discord_webhook, message)
    elif current_hash != previous_hash:
        # Content changed
        print("Content has changed!")

        # Generate diff if we have previous content
        diff_summary = ""
        if previous_content:
            diff_summary = get_meaningful_diff(previous_content, content)
            print(f"Changes detected:\n{diff_summary}")

        save_hash(HASH_FILE, current_hash)
        save_content(CONTENT_FILE, content)

        # Build message with diff
        message = f"📢 Schedule page updated! Check it out: {TARGET_URL}"
        if diff_summary:
            message += f"\n\n**Changes:**\n```\n{diff_summary}\n```"

        send_discord_notification(discord_webhook, message)
    else:
        # No change
        print("No changes detected")
        message = f"✅ Schedule checked - no changes detected at {TARGET_URL}"
        send_discord_notification(discord_webhook, message)


if __name__ == "__main__":
    main()
