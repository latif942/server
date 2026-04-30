from flask import Flask, request, Response, jsonify
import os
import subprocess
import json
import tempfile
import yt_dlp

app = Flask(__name__)

# Get cookies from environment variable (set in Render Dashboard)
# If not set, yt-dlp will run without cookies (less reliable)
COOKIES_ENV = os.environ.get('YOUTUBE_COOKIES', '')

def get_video_info(query):
    """Searches YouTube and returns the best audio URL using yt-dlp."""
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False, # We need the actual URL
        'socket_timeout': 10,
    }

    # If cookies are provided, write them to a temp file
    if COOKIES_ENV:
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(COOKIES_ENV)
                cookie_file = f.name
            ydl_opts['cookiefile'] = cookie_file
        except Exception as e:
            print(f"Cookie error: {e}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Search for the video
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if not info or 'entries' not in info or not info['entries']:
                return None
            
            entry = info['entries'][0]
            url = entry.get('url') or entry.get('webpage_url')
            
            # If we got a direct URL, return it
            if url:
                return url
            
            # If not, we might need to re-extract with the specific ID
            vid_id = entry.get('id')
            if vid_id:
                info_direct = ydl.extract_info(f"https://www.youtube.com/watch?v={vid_id}", download=False)
                return info_direct.get('url')
                
    except Exception as e:
        print(f"yt-dlp error: {e}")
        return None
    finally:
        # Clean up temp cookie file if created
        if COOKIES_ENV and 'cookie_file' in locals():
            try:
                os.unlink(cookie_file)
            except:
                pass

@app.route('/stream')
def stream():
    q = request.args.get('q', '')
    if not q:
        return jsonify({'error': 'No query provided'}), 400

    try:
        url = get_video_info(q)
        if not url:
            return jsonify({'error': 'Video not found or extraction failed'}), 404
        
        print(f"Streaming: {url[:50]}...")

        # Proxy the stream to avoid CORS/IP issues
        def generate():
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Range': request.headers.get('Range', 'bytes=0-')
            }
            import requests
            with requests.get(url, stream=True, timeout=60, headers=headers) as r:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk

        resp = Response(generate(), mimetype='audio/mp4')
        resp.headers['Accept-Ranges'] = 'bytes'
        return resp

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    return 'ok'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)