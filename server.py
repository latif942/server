from flask import Flask, request, Response, jsonify
import os
import requests

app = Flask(__name__)

PIPED = [
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
    for base in PIPED:
        try:
            r = requests.get(f'{base}/search', params={'q': query, 'filter': 'videos'}, timeout=5)
            if r.status_code != 200: continue
            items = r.json().get('items', [])
            for item in items:
                url = item.get('url', '')
                if 'watch?v=' in url:
                    vid = url.split('watch?v=')[-1].split('&')[0]
                    print(f"Found {vid} via {base}")
                    return vid, base
        except Exception as e:
            print(f"{base} search failed: {e}")
    return None, None

def get_stream(video_id):
    for base in PIPED:
        try:
            r = requests.get(f'{base}/streams/{video_id}', timeout=5)
            if r.status_code != 200: continue
            streams = r.json().get('audioStreams', [])
            streams = [s for s in streams if s.get('url')]
            if not streams: continue
            streams.sort(key=lambda x: x.get('bitrate', 0), reverse=True)
            url = streams[0]['url']
            print(f"Got stream from {base}")
            return url
        except Exception as e:
            print(f"{base} stream failed: {e}")
    return None

@app.route('/stream')
def stream():
    q = request.args.get('q', '')
    if not q: return jsonify({'error': 'no query'}), 400
    try:
        vid, base = search_video(q)
        if not vid: return jsonify({'error': 'no video found'}), 404
        url = get_stream(vid)
        if not url: return jsonify({'error': 'no stream found'}), 404
        def generate():
            with requests.get(url, stream=True, timeout=60, headers={'User-Agent': 'Mozilla/5.0'}) as r:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk: yield chunk
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