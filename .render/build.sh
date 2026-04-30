#!/bin/bash
set -e

# Install dependencies
pip install -r requirements.txt

# Force install yt-dlp binary to a known location
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /opt/render/.local/bin/yt-dlp
chmod +x /opt/render/.local/bin/yt-dlp

# Add to PATH so your script can find it
export PATH="/opt/render/.local/bin:$PATH"