from flask import Flask, request, Response, jsonify
import os
import requests

# Initialize Flask correctly
app = Flask(__name__)

PIPED_INSTANCES = [
    'https://pipedapi.kavin.rocks',
    'https://pipedapi-libre.kavin.rocks',
    'https://pipedapi.adminforge.de',
    'https://api.piped.yt',
    'https://pipedapi.darkness.services',
    'https://pipedapi.leptons.xyz',
    'https://piped-api.privacy.com.de',
    'https://pipedapi.owo.si',
    'https://pipedapi.ducks.party',
    'https://api.piped.private.coffee',
    'https://pipedapi.reallyaweso.me',
]

def search_video(query):
    """Searches for a video ID using Piped instances."""
    for base in PIPED_INSTANCES:
        try:
            # Use a shorter timeout for search to fail fast
            r = requests.get(f'{base}/search', params={'q': query, 'filter': 'videos'}, timeout=5)
            if r.status_code != 200: 
                continue
            
            data = r.json()
            items = data.get('items', [])
            
            for item in items:
                url = item.get('url', '')
                if 'watch?v=' in url:
                    vid = url.split('watch?v=')[-1].split('&')[0]
                    print(f"[SEARCH] Found {vid} via {base}")
                    return vid, base
        except Exception as e:
            # Silently fail to next instance
            continue
    return None, None

def get_stream_url(video_id):
    """Gets the direct audio stream URL using Piped instances."""
    for base in PIPED_INSTANCES:
        try:
            r = requests.get(f'{base}/streams/{video_id}', timeout=5)
            if r.status_code != 200: 
                continue
            
            data = r.json()
            streams = data.get('audioStreams', [])
            
            # Filter valid streams
            valid_streams = [s for s in streams if s.get('url')]
            if not valid_streams: 
                continue
            
            # Sort by bitrate (highest first)
            valid_streams.sort(key=lambda x: x.get('bitrate', 0), reverse=True)
            best_stream = valid_streams[0]
            url = best_stream['url']
            
            print(f"[STREAM] Got stream URL from {base}")
            return url
        except Exception as e:
            continue
    return None

@app.route('/stream')
def stream():
    q = request.args.get('q', '')
    if not q:
        return jsonify({'error': 'No query parameter provided'}), 400

    try:
        # 1. Search for Video ID
        vid, search_base = search_video(q)
        if not vid:
            return jsonify({'error': 'Video not found'}), 404
        
        # 2. Get Stream URL
        stream_url = get_stream_url(vid)
        if not stream_url:
            return jsonify({'error': 'Could not retrieve stream URL'}), 404
        
        # 3. Proxy the stream to Flutter
        def generate():
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'audio/mp4, audio/webm, audio/ogg, audio/*;q=0.9, */*;q=0.8',
                'Range': request.headers.get('Range', 'bytes=0-')
            }
            
            try:
                with requests.get(stream_url, stream=True, timeout=60, headers=headers) as r:
                    # Yield chunks
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            yield chunk
            except Exception as e:
                print(f"[PROXY ERROR] {e}")
                return

        response = Response(generate(), mimetype='audio/mp4')
        response.headers['Accept-Ranges'] = 'bytes'
        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    return 'OK'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)