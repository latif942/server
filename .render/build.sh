#!/bin/bash
set -e

# Install Python dependencies
pip install -r requirements.txt

# Install yt-dlp binary
echo "Installing yt-dlp..."
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /opt/render/.local/bin/yt-dlp
chmod +x /opt/render/.local/bin/yt-dlp

# Ensure it's in PATH
export PATH="/opt/render/.local/bin:$PATH"
echo "yt-dlp installed successfully."