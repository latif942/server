from flask import Flask, request, Response, jsonify
import os
import requests
import urllib.parse

app = Flask(__name__)

PIPED_INSTANCES = [
    'https://pipedapi.kavin.rocks',
    'https://pipedapi.adminforge.de',
    'https://pipedapi.darkness.services',
    'https://piped-api.garudalinux.org',
    'https://pipedapi.in.projectsegfau.lt',
]

def search_piped(query):
    for base in PIPED_INSTANCES:
        try:
            res = requests.get(
                f'{base}/search',
                params={'q': query, 'filter': 'music_songs'},
                timeout=6
            )
            if res.status_code != 200:
                continue
            items = res.json().get('items', [])
            for item in items:
                url = item.get('url', '')
                if 'watch?v=' in url:
                    vid = url.split('watch?v=')[-1].split('&')[0]
                    print(f"Found video {vid} via {base}")
                    return vid, base
        except Exception as e:
            print(f"Search failed on {base}: {e}")
    return None, None

def get_stream_url(video_id, base):
    for instance in [base] + PIPED_INSTANCES:
        try:
            res = requests.get(f'{instance}/streams/{video_id}', timeout=6)
            if res.status_code != 200:
                continue
            data = res.json()
            streams = [s for s in data.get('audioStreams', []) 
                      if s.get('url') and 'mime_type' in s or 'mimeType' in s]
            if not streams:
                streams = data.get('audioStreams', [])
            if streams:
                streams.sort(key=lambda x: x.get('bitrate', 0), reverse=True)
                url = streams[0].get('url')
                if url:
                    print(f"Got stream from {instance}")
                    return url
        except Exception as e:
            print(f"Stream failed on {instance}: {e}")
    return None

@app.route('/stream')
def stream():
    q = request.args.get('q', '')
    if not q:
        return jsonify({'error': 'no query'}), 400
    try:
        video_id, base = search_piped(q)
        if not video_id:
            return jsonify({'error': 'no video found'}), 404
        
        url = get_stream_url(video_id, base)
        if not url:
            return jsonify({'error': 'no stream found'}), 404

        def generate():
            with requests.get(url, stream=True, timeout=60,
                headers={'User-Agent': 'Mozilla/5.0'}) as r:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk

        return Response(generate(), mimetype='audio/mp4')
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