from flask import Flask, request, Response, jsonify
import os
import requests
from pytube import YouTube
from pytube.exceptions import RegexMatchError, VideoUnavailable

app = Flask(__name__)

# Fallback Piped instances (keep some as backup)
PIPED_INSTANCES = [
    'https://pipedapi.kavin.rocks',
    'https://pipedapi-libre.kavin.rocks',
    'https://pipedapi.adminforge.de',
]

def search_youtube(query):
    """Searches YouTube using a simple HTML scrape or Piped to get Video ID"""
    # Try Piped first for search as it's cleaner
    for base in PIPED_INSTANCES:
        try:
            r = requests.get(f'{base}/search', params={'q': query, 'filter': 'videos'}, timeout=5)
            if r.status_code == 200:
                items = r.json().get('items', [])
                for item in items:
                    url = item.get('url', '')
                    if 'watch?v=' in url:
                        vid = url.split('watch?v=')[-1].split('&')[0]
                        return vid
        except:
            continue
    return None

def get_audio_stream_url(video_id):
    """Uses PyTube to get the audio stream URL directly from YouTube"""
    try:
        yt = YouTube(f'https://www.youtube.com/watch?v={video_id}')
        # Filter for audio only, mp4 format (compatible with just_audio)
        audio_stream = yt.streams.filter(only_audio=True, file_extension='mp4').first()
        if audio_stream:
            return audio_stream.url
    except Exception as e:
        print(f"PyTube failed: {e}")
    
    # Fallback to Piped for stream URL if PyTube fails
    for base in PIPED_INSTANCES:
        try:
            r = requests.get(f'{base}/streams/{video_id}', timeout=5)
            if r.status_code == 200:
                data = r.json()
                audio_streams = data.get('audioStreams', [])
                if audio_streams:
                    # Sort by bitrate and pick the highest
                    audio_streams.sort(key=lambda x: x.get('bitrate', 0), reverse=True)
                    return audio_streams[0]['url']
        except:
            continue
    return None

@app.route('/stream')
def stream():
    q = request.args.get('q', '')
    if not q:
        return jsonify({'error': 'No query provided'}), 400

    try:
        # 1. Search for Video ID
        video_id = search_youtube(q)
        if not video_id:
            return jsonify({'error': 'Video not found'}), 404
        
        print(f"Found Video ID: {video_id}")

        # 2. Get Audio Stream URL
        stream_url = get_audio_stream_url(video_id)
        if not stream_url:
            return jsonify({'error': 'Could not retrieve stream URL'}), 404
        
        print(f"Stream URL obtained: {stream_url[:50]}...")

        # 3. Proxy the stream to avoid CORS/Expiry issues in Flutter
        def generate():
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'audio/webm,audio/ogg,audio/wav,audio/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
                'Range': request.headers.get('Range', 'bytes=0-') # Support range requests for seeking
            }
            
            # Make request to the actual audio source
            with requests.get(stream_url, stream=True, headers=headers, timeout=60) as r:
                # Forward status code and headers
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk

        response = Response(generate(), mimetype='audio/mp4')
        # Important: Forward content-range headers if present for seeking support in just_audio
        if 'Content-Range' in r.headers:
            response.headers['Content-Range'] = r.headers['Content-Range']
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