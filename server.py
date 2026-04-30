from flask import Flask, request, Response, jsonify
import os, requests, subprocess, json, tempfile

app = Flask(__name__)
COOKIES = os.environ.get('YOUTUBE_COOKIES', '')

def get_audio_url(query):
    cmd = [
        'yt-dlp',
        '-f', 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio',
        '--dump-json',
        '--no-playlist',
        '--socket-timeout', '10',
        f'ytsearch1:{query}'
    ]
    if COOKIES:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(COOKIES)
            cookie_file = f.name
        cmd.extend(['--cookies', cookie_file])
    else:
        cookie_file = None
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"yt-dlp error: {result.stderr}")
            return None
        data = json.loads(result.stdout.strip())
        # Handle both single video and search results
        if 'entries' in data and data['entries']:
            url = data['entries'][0].get('url')
        else:
            url = data.get('url')
        return url
    except Exception as e:
        print(f"subprocess error: {e}")
        return None
    finally:
        if cookie_file and os.path.exists(cookie_file):
            os.unlink(cookie_file)

@app.route('/stream')
def stream():
    q = request.args.get('q', '')
    if not q:
        return jsonify({'error': 'no query'}), 400
    try:
        url = get_audio_url(q)
        if not url:
            return jsonify({'error': 'extraction failed'}), 404
        
        # FIX: Capture headers BEFORE the generator
        range_header = request.headers.get('Range', 'bytes=0-')
        
        def gen():
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Range': range_header  # Use the captured value
            }
            with requests.get(url, stream=True, timeout=60, headers=headers) as r:
                for chunk in r.iter_content(8192):
                    if chunk:
                        yield chunk
        resp = Response(gen(), mimetype='audio/mp4')
        resp.headers['Accept-Ranges'] = 'bytes'
        return resp
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    return 'ok'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)