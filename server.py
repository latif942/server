from flask import Flask, request, Response, jsonify
import os
import yt_dlp
import requests
import tempfile

app = Flask(__name__)

# Get cookies from Environment Variable (Set this in Render Dashboard)
# If empty, yt-dlp runs without cookies (less reliable)
YOUTUBE_COOKIES = os.environ.get('YOUTUBE_COOKIES', '')

def get_audio_url(query):
    """Uses yt-dlp to search and extract the best audio URL."""
    
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio', # Prefer m4a/mp3 for compatibility
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'socket_timeout': 10,
        'retries': 3,
    }

    # Handle Cookies if provided
    cookie_file = None
    if YOUTUBE_COOKIES:
        try:
            # Write cookies to a temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(YOUTUBE_COOKIES)
                cookie_file = f.name
            ydl_opts['cookiefile'] = cookie_file
        except Exception as e:
            print(f"Error writing cookies: {e}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Search for the video
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            
            if not info or 'entries' not in info or not info['entries']:
                return None
            
            entry = info['entries'][0]
            
            # Sometimes the URL is directly in the entry, sometimes we need to re-extract
            url = entry.get('url')
            
            if not url:
                # If no direct URL, extract again using the video ID for precise format selection
                vid_id = entry.get('id')
                if vid_id:
                    direct_info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid_id}", download=False)
                    url = direct_info.get('url')
            
            return url

    except Exception as e:
        print(f"yt-dlp error: {e}")
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
    if not q:
        return jsonify({'error': 'No query provided'}), 400

    try:
        url = get_audio_url(q)
        if not url:
            return jsonify({'error': 'Video not found or extraction failed'}), 404
        
        print(f"Streaming URL obtained for: {q}")

        # Proxy the stream to Flutter
        def generate():
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Range': request.headers.get('Range', 'bytes=0-') # Support seeking
            }
            try:
                with requests.get(url, stream=True, timeout=60, headers=headers) as r:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            yield chunk
            except Exception as e:
                print(f"Proxy error: {e}")

        resp = Response(generate(), mimetype='audio/mp4')
        resp.headers['Accept-Ranges'] = 'bytes'
        resp.headers['Access-Control-Allow-Origin'] = '*' # Allow Flutter app to access
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