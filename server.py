from flask import Flask, request, Response, jsonify
import os
import requests

app = Flask(__name__)

INVIDIOUS = [
    'https://invidious.jing.rocks',
    'https://yt.cdaut.de',
    'https://invidious.nerdvpn.de',
]

def search_and_get_url(query):
    for base in INVIDIOUS:
        try:
            # search
            res = requests.get(f'{base}/api/v1/search',
                params={'q': query, 'type': 'video', 'page': 1},
                timeout=8)
            if res.status_code != 200:
                continue
            results = res.json()
            if not results:
                continue
            video_id = results[0]['videoId']

            # get streams
            res2 = requests.get(f'{base}/api/v1/videos/{video_id}', timeout=8)
            if res2.status_code != 200:
                continue
            data = res2.json()
            streams = [f for f in data.get('adaptiveFormats', []) if 'audio' in f.get('type', '')]
            if not streams:
                streams = [f for f in data.get('formatStreams', [])]
            if not streams:
                continue
            url = streams[0]['url']
            print(f"Got stream from {base}")
            return url
        except Exception as e:
            print(f"{base} failed: {e}")
            continue
    raise Exception("All Invidious instances failed")

@app.route('/stream')
def stream():
    q = request.args.get('q', '')
    if not q:
        return jsonify({'error': 'no query'}), 400
    try:
        url = search_and_get_url(q)
        def generate():
            with requests.get(url, stream=True, timeout=30) as r:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
        return Response(generate(), mimetype='audio/mp4')
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    return 'ok'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)