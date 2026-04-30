from flask import Flask, request, Response, jsonify
from pytubefix import Search, YouTube
import os
import requests

app = Flask(__name__)

def get_audio_url(query):
    s = Search(query)
    for result in s.results[:5]:
        try:
            yt = YouTube(result.watch_url)
            stream = yt.streams.filter(only_audio=True).order_by('abr').last()
            if stream:
                return stream.url
        except Exception as e:
            print(f"Skipping {result.watch_url}: {e}")
            continue
    raise Exception("No playable stream found")

@app.route('/stream')
def stream():
    q = request.args.get('q', '')
    if not q:
        return jsonify({'error': 'no query'}), 400
    try:
        url = get_audio_url(q)
        def generate():
            with requests.get(url, stream=True, timeout=30) as r:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
        return Response(generate(), mimetype='audio/mp4')
    except Exception as e:
        import traceback
        print(traceback.format_exc())  # ← add this
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    return 'ok'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)