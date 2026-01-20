# UCSD CSE 25 Schedule Notifications

Monitors https://ucsd-cse25.github.io/schedule/ for changes and sends Discord notifications when updates are detected.

## Features

- Checks the schedule page every hour for changes
- Sends Discord notifications when updates are detected
- Stores content hash to track changes efficiently
- Handles first run and network errors gracefully

## Setup

### 1. Configure Discord Webhook

The Discord webhook URL is already configured in the script. If you need to change it:

1. Go to your repository's Settings → Secrets and variables → Actions
2. Create or update a secret named `DISCORD_WEBHOOK_URL`
3. Set the value to your Discord webhook URL

**Current webhook URL** (already set): `https://discord.com/api/webhooks/1463303473885085708/uEdsDl4dWE6VIU5XPaNyR7gDk-X4zkPOfMzCjZsfx1VSxerUg2TzJc-H92qkgpNBVQ7E`

### 2. Enable GitHub Actions

1. Go to your repository's Settings → Actions → General
2. Under "Workflow permissions", select "Read and write permissions"
3. Click "Save"

### 3. Push to GitHub

```bash
git add .
git commit -m "Add schedule change tracker"
git push
```

### 4. Manual Test (Optional)

You can manually trigger the workflow to test it:

1. Go to the "Actions" tab in your repository
2. Select "Check Schedule for Updates" workflow
3. Click "Run workflow"

## How It Works

1. **Python Script** (`check_updates.py`):
   - Fetches the HTML content from the target URL
   - Computes a SHA256 hash of the content
   - Compares against the previous hash stored in `last_hash.txt`
   - Sends a Discord notification if the content changed
   - Saves the new hash for future comparisons

2. **GitHub Actions Workflow** (`.github/workflows/check-schedule.yml`):
   - Runs automatically every hour (via cron schedule)
   - Can be triggered manually via workflow_dispatch
   - Installs dependencies and runs the Python script
   - Commits and pushes the updated hash file back to the repository

## Files

- `check_updates.py` - Main Python script for checking updates
- `.github/workflows/check-schedule.yml` - GitHub Actions workflow
- `requirements.txt` - Python dependencies
- `last_hash.txt` - Stores the hash of the last checked content (auto-generated)

## Customization

### Change Check Frequency

Edit the cron schedule in `.github/workflows/check-schedule.yml`:

```yaml
schedule:
  - cron: '0 * * * *'  # Every hour
  # - cron: '*/30 * * * *'  # Every 30 minutes
  # - cron: '0 */2 * * *'  # Every 2 hours
```

### Change Target URL

Edit the `TARGET_URL` variable in `check_updates.py`:

```python
TARGET_URL = "https://ucsd-cse25.github.io/schedule/"
```

## Troubleshooting

- **No notifications received**: Check that the Discord webhook URL is correctly set in GitHub Secrets
- **Workflow not running**: Verify that GitHub Actions has write permissions in repository settings
- **Network errors**: The script will log errors but won't fail the workflow; check Actions logs for details
