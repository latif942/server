from flask import Flask, request, Response, jsonify
import yt_dlp
import os
import requests

app = Flask(__name__)

CLIENTS = ['tv_embedded', 'ios', 'android', 'web']

def get_audio_url(query):
    for client in CLIENTS:
        try:
            opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'noplaylist': True,
                'nocheckcertificate': True,
                'extractor_args': {
                    'youtube': {
                        'player_client': [client],
                    }
                }
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                entries = info.get('entries') or [info]
                if not entries:
                    continue
                url = entries[0].get('url')
                if url:
                    print(f"Success with client: {client}")
                    return url
        except Exception as e:
            print(f"Client {client} failed: {e}")
            continue
    raise Exception("All clients failed")

@app.route('/stream')
def stream():
    q = request.args.get('q', '')
    if not q:
        return jsonify({'error': 'no query'}), 400
    try:
        url = get_audio_url(q)
        def generate():
            headers = {'User-Agent': 'Mozilla/5.0'}
            with requests.get(url, headers=headers, stream=True) as r:
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