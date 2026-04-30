import logging
import sys
import os
import json
import tempfile
import subprocess
import requests
from flask import Flask, request, Response, jsonify

# Configure Logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Get cookies from Environment Variable (Set 'YOUTUBE_COOKIES' in Render Dashboard)
COOKIES = os.environ.get('YOUTUBE_COOKIES', '')

def get_audio_url(query):
    """
    Uses yt-dlp CLI to search YouTube and extract the best audio URL.
    """
    logger.info(f"🔍 Searching for: {query}")
    
    # Base command
    cmd = [
        'yt-dlp',
        '-f', 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio', # Prefer m4a/mp3
        '--dump-json',          # Output JSON instead of downloading
        '--no-playlist',        # Only get the first video
        '--socket-timeout', '15',
        '--extractor-retries', '3',
        f'ytsearch1:{query}'    # Search query
    ]

    cookie_file = None
    if COOKIES:
        try:
            # Write cookies to a temp file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(COOKIES)
                cookie_file = f.name
            cmd.extend(['--cookies', cookie_file])
            logger.debug("🍪 Using cookies for extraction")
        except Exception as e:
            logger.error(f"❌ Failed to write cookie file: {e}")

    try:
        # Run yt-dlp
        logger.debug(f"⚙️ Running command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=45
        )

        # Check for errors
        if result.returncode != 0:
            logger.error(f"❌ yt-dlp failed (Code {result.returncode})")
            logger.error(f"stderr: {result.stderr[:500]}") # Log first 500 chars of error
            return None

        # Parse JSON output
        data = json.loads(result.stdout.strip())
        
        # Handle search results vs direct video
        url = None
        if 'entries' in data and data['entries']:
            url = data['entries'][0].get('url')
            logger.info(f"✅ Found Video ID: {data['entries'][0].get('id')}")
        else:
            url = data.get('url')
            logger.info(f"✅ Found Direct Video ID: {data.get('id')}")

        if not url:
            logger.error("❌ No URL found in yt-dlp output")
            return None
            
        logger.debug(f"🔗 Extracted URL: {url[:60]}...")
        return url

    except subprocess.TimeoutExpired:
        logger.error("⏰ yt-dlp timed out")
        return None
    except json.JSONDecodeError:
        logger.error("📄 Failed to parse yt-dlp JSON output")
        logger.error(f"stdout: {result.stdout[:500]}")
        return None
    except Exception as e:
        logger.error(f"💥 Unexpected error in get_audio_url: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
    finally:
        # Clean up temp cookie file
        if cookie_file and os.path.exists(cookie_file):
            try:
                os.unlink(cookie_file)
            except:
                pass

@app.route('/stream')
def stream():
    q = request.args.get('q', '')
    logger.info(f"📥 Request received: /stream?q={q}")
    
    if not q:
        return jsonify({'error': 'Missing query parameter'}), 400

    try:
        # 1. Get Audio URL
        url = get_audio_url(q)
        if not url:
            return jsonify({'error': 'Failed to extract audio URL'}), 404
        
        # 2. Proxy the Stream
        # Capture headers BEFORE generator to avoid context errors
        range_hdr = request.headers.get('Range', 'bytes=0-')
        
        def generate():
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Range': range_hdr
                }
                logger.debug(f"⬆️ Starting proxy stream to YouTube...")
                with requests.get(url, stream=True, timeout=90, headers=headers) as r:
                    logger.debug(f"⬆️ YouTube Status: {r.status_code}")
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            yield chunk
            except Exception as e:
                logger.error(f"💥 Proxy stream error: {e}")
        
        resp = Response(generate(), mimetype='audio/mp4')
        resp.headers['Accept-Ranges'] = 'bytes'
        resp.headers['Access-Control-Allow-Origin'] = '*'
        logger.info("🎵 Streaming response sent")
        return resp

    except Exception as e:
        logger.error(f"💥 Unhandled /stream error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/health')
def health():
    return 'ok'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🚀 Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port)