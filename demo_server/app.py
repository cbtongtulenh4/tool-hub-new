import asyncio
import sys
import os
import re
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, make_response, stream_with_context, Response
import httpx
from fsmvid import FSMVIDDown
import webbrowser
import subprocess
import threading
import aiofiles
import requests
import uuid
from douyin_tiktok.douyin_tiktok import DouyinTiktokScraper
from youtube import YouTubeDownloader
from flask_cors import CORS
from queue import Queue
import json
import time
import random
from datetime import datetime


app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)


# Create media_download folder if it doesn't exist
DOWNLOAD_FOLDER = Path("media_download")
DOWNLOAD_FOLDER.mkdir(exist_ok=True)
FFMPEG_PATH = os.path.join(sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__)), "bin", "ffmpeg.exe")

# Global state for download tracking
download_tasks = {}  # {download_id: {status, videos, progress}}
download_queues = {}  # {download_id: Queue for SSE events}
playlist_session = []
download_stopped = threading.Event()
download_stopped.set()

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to remove invalid characters."""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = filename.strip('. ')
    if len(filename) > 200:
        filename = filename[:200]
    return filename or "video"

def classify_urls(urls: list) -> list:
    result_groups = [] 
    video_group = [] 

    for url in urls:
        # ---- TikTok ----
        if 'tiktok.com' in url:
            if url.split("/")[-1].startswith("@"):
                result_groups.append([
                    {'url': url, 'platform': 'tiktok', 'type': 'channel'}
                ])
            else:
                url = url.split("?")[0]
                video_group.append(
                    {'url': url, 'platform': 'tiktok', 'type': 'video'}
                )

        # ---- Douyin (China TikTok) ----
        elif 'douyin.com' in url:
            if "/user/" in url:
                result_groups.append([
                    {'url': url, 'platform': 'douyin', 'type': 'channel', 'sec_user_id': url.split("?")[0].split("/")[-1]}
                ])
            else:
                video_group.append(
                    {'url': url, 'platform': 'douyin', 'type': 'video'}
                )

        # ---- YouTube ----
        elif 'youtube.com' in url or 'youtu.be' in url:
            if "/channel/" in url:
                result_groups.append([
                    {'url': url, 'platform': 'youtube', 'type': 'channel'}
                ])
            elif url.split("/")[-1].startswith("@"):
                result_groups.append([
                    {'url': url, 'platform': 'youtube', 'type': 'channel'}
                ])
            else:
                video_group.append(
                    {'url': url, 'platform': 'youtube', 'type': 'video'}
                )

        # ---- Facebook ----
        elif 'facebook.com' in url:
            video_group.append(
                {'url': url, 'platform': 'facebook', 'type': 'video'}
            )
        else:
            video_group.append(
                {'url': url, 'platform': None, 'type': 'video'}
            )
    if video_group:
        result_groups.insert(0, video_group)

    return result_groups


async def download_single_video(item, index: int) -> dict:
    """Download a single video from URL."""
    try:
        resp_cancel = {
            "url": item['url'],
            "status": "Cancelled",
            "message": "cancel download"
        }
        if download_stopped.is_set():
            return resp_cancel
        url = item['url']
        platform = item['platform']
        if not platform:
            return {
                "url": url,
                "status": "error",
                "message": "not support this platform"
            }

        if platform == "youtube":
            # Wrap sync YouTube downloader in async to prevent blocking
            if download_stopped.is_set():
                return resp_cancel
            downloader = YouTubeDownloader(url, item['save_path'], 0, ffmpeg_path=FFMPEG_PATH)
            await asyncio.to_thread(downloader.download_worker, url)
            return {
                "url": url,
                "status": "success",
                "filename": "",
                "title": "",
                "duration": ""
            }
        fsmvid = FSMVIDDown()
        result = await fsmvid.download(platform, url)
        
        if not result or result.get("status", "") != "success" or result.get("cnt", 0) == 0:
            return {
                "url": url,
                "status": "error",
                "message": "not support this platform"
            }
        
        cnt = result.get("cnt", 0)
        medias = result.get("medias", [])
        
        if download_stopped.is_set():
            return resp_cancel

        if not medias:
            return {
                "url": url,
                "status": "error",
                "message": "Không tìm thấy media để download"
            }
        video_id = result.get("id", uuid.uuid4())
        title = result.get("title", "video")
        if cnt == 1:
            video_media = medias[0]
            video_url = video_media.get("url")
            type = video_media.get("type", "")
            
            if not video_url:
                return {
                    "url": url,
                    "status": "error",
                    "message": "Không tìm thấy URL video"
                }
            if type == "image":
                extension = video_media.get("extension", "jpg")
                filename = f"{sanitize_filename(video_id)}.{extension}"
                filepath = Path(item['save_path']) / filename
                async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
                    async with client.stream("GET", video_url) as response:
                        response.raise_for_status()
                        with open(filepath, "wb") as f:
                            async for chunk in response.aiter_bytes(chunk_size=1024*1024): 
                                f.write(chunk)
                return {
                    "url": url,
                    "status": "success",
                    "filename": filename,
                    "title": title
                }
            ext = video_media.get("ext", "mp4")
            filename = f"{sanitize_filename(video_id)}.{ext}"
            filepath = Path(item['save_path']) / filename
            async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
                async with client.stream("GET", video_url) as response:
                    response.raise_for_status()

                    async with aiofiles.open(filepath, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=4 * 1024 * 1024):  # 4MB
                            await f.write(chunk)
            return {
                "url": url,
                "status": "success",
                "filename": filename,
                "title": title,
            }

        elif cnt == 2:
            video_media = medias[0]
            
            video_url = video_media.get("url")
            ext = video_media.get("ext", "mp4")
            filename = f"{sanitize_filename(video_id)}.{ext}"
            filepath = Path(item['save_path']) / filename
            async with httpx.AsyncClient(timeout=None, follow_redirects=True, http2=True) as client:
                async with client.stream("GET", video_url) as response:
                    response.raise_for_status()

                    async with aiofiles.open(filepath, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=4 * 1024 * 1024):  # 4MB
                            await f.write(chunk)
            audio_media = medias[1]
            audio_url = audio_media.get("url")
            audio_ext = audio_media.get("ext", "mp3")
            audio_filename = f"{sanitize_filename(video_id)}.{audio_ext}"
            audio_filepath = Path(item['save_path']) / audio_filename
            async with httpx.AsyncClient(timeout=None, follow_redirects=True, http2=True) as client:
                async with client.stream("GET", audio_url) as response:
                    response.raise_for_status()

                    async with aiofiles.open(audio_filepath, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=4 * 1024 * 1024):  # 4MB
                            await f.write(chunk)


            return {
                "url": url,
                "status": "success",
                "filename": filename,
                "title": title,
                "duration": ""
            }
    except Exception as e:
        return {
            "url": url,
            "status": "error",
            "message": str(e)
        }

async def download_multiple_videos(download_id: str, items: list, concurrent_downloads: int) -> list:
    """Download multiple videos in parallel with concurrency limit."""
    
    # Tạo semaphore để giới hạn concurrent downloads
    semaphore = asyncio.Semaphore(concurrent_downloads)
    
    async def download_with_limit(item, idx):
        """Wrapper function that respects semaphore limit"""
        async with semaphore:  # Chỉ cho phép N tasks vào đây cùng lúc
            try:
                result = await download_single_video(item, idx)
                
                # Update progress
                download_tasks[download_id]['completed'] += 1
                download_tasks[download_id]['videos'][item['url']] = result
                
                print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] [PROGRESS] Video {download_tasks[download_id]['completed']}/{download_tasks[download_id]['total']}: {item['url']} - {result['status']}")
                
                emit_progress(download_id, {
                    'type': 'progress',
                    'url': item['url'],
                    'status': result['status'],
                    'message': result.get('message', ''),
                    'filename': result.get('filename', ''),
                    'completed': download_tasks[download_id]['completed'],
                    'total': download_tasks[download_id]['total']
                })
                
                return result
            except Exception as e:
                return {
                    'url': item.get('url', ''),
                    'status': 'error',
                    'message': str(e)
                }
    
    tasks = [download_with_limit(item, i) for i, item in enumerate(items)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    download_tasks[download_id]['status'] = 'completed'
    emit_progress(download_id, {
        'type': 'completed',
        'total': download_tasks[download_id]['total'],
        'completed': download_tasks[download_id]['completed']
    })
    
    return list(results)


@app.route('/api/choose-directory', methods=['GET', 'POST', 'OPTIONS'])
def choose_directory():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        return response

    try:
        cmd = [
            sys.executable, 
            "-c", 
            "import tkinter as tk; from tkinter import filedialog; root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True); print(filedialog.askdirectory()); root.destroy()"
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        selected_path = result.stdout.strip()
        
        if not selected_path:
            response = jsonify({"path": None})
        else:
            response = jsonify({"path": selected_path})
            
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        print(f"Error choosing directory: {e}")
        response = jsonify({"error": str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500


@app.route('/api/load_videos_by_user', methods=['POST'])
def load_videos_by_user():
    def load_video_data():
        global playlist_session
        playlist_session = {}
        data = request.get_json()
        user_url = data.get('channel_url', '')
    
        if not user_url:
            error_message = {
            	"error": True,
            	"message": "Empty input",
            	"status": 400
            }
            yield json.dumps(error_message, ensure_ascii=False) + "\n"
            return

        group_urls = classify_urls([user_url])
        group = group_urls[0]
        temp = group[0]
        items = []
        if temp['type'] == 'channel':
            if temp['platform'] == "tiktok" or temp['platform'] == "douyin":
                scraper = DouyinTiktokScraper()
                if temp['platform'] == "douyin":
                    items = asyncio.run(scraper.douyin_fetch_user_post_videos(sec_user_id=temp['sec_user_id'], max_cursor=0, count=50))  
            elif temp['platform'] == "youtube":
                items = YouTubeDownloader(temp['url'], "", 0, FFMPEG_PATH).get_channel_videos()
        i = 1
        temp1 = []
        check_duplicate = []
        for item in items:
            url = item['url']
            if url in check_duplicate:
                continue
            check_duplicate.append(url)
            video_data = {
                "id": i,
                "url": item['url'],
                "caption": item['title'],
                "comments": item['comments'],
                "likes": item['likes'],
                "views": item['views'],
                "collects": item['collects'],
                "shares": item['shares'],
                "status": "Sẵn sàng",
            }
            temp1.append(video_data)
            video_data['platform'] = temp['platform']
            video_data['type'] = 'video'
            playlist_session[url] = video_data  # Store each video in session
            
            if i % 20 == 0:
                delay = max(0.1, random.gauss(1, 0.5))
                time.sleep(delay)
                yield json.dumps(temp1, ensure_ascii=False) + "\n"
                temp1 = []
            i += 1
        if temp1:
            yield json.dumps(temp1, ensure_ascii=False) + "\n"

    return Response(stream_with_context(load_video_data()), mimetype="application/x-ndjson")

@app.route('/api/load_videos_by_list', methods=['POST'])
def load_videos_by_list():
    def load_video_data():
        global playlist_session
        playlist_session = {}  # Reset session for new request
        
        data = request.get_json()
        text_urls = data.get('urls', '')
    
        if not text_urls:
            error_message = {
            	"error": True,
            	"message": "Empty input",
            	"status": 400
            }
            yield json.dumps(error_message, ensure_ascii=False) + "\n"
            return
        urls = [url for url in text_urls.split('\n') if url.strip()]
        groups = classify_urls(urls)
        i = 1
        temp = []
        check_duplicate = []
        for group in groups:
            for item in group:
                url = item['url']
                if url in check_duplicate:
                    continue
                check_duplicate.append(url)
                video_data = {
                    "id": i,
                    "url": url,
                    "caption": "",
                    "comments": 0,
                    "likes": 0,
                    "views": 0,
                    "collects": 0,
                    "shares": 0,
                    "status": "Sẵn sàng" if item['platform'] else "Error",
                }
                temp.append(video_data)
                video_data['platform'] = item['platform']
                video_data['type'] = item['type']
                playlist_session[url] = video_data  # Store each video in session
                
                if i % 20 == 0:
                    yield json.dumps(temp, ensure_ascii=False) + "\n"
                    temp = []
                i += 1
            if temp:
                yield json.dumps(temp, ensure_ascii=False) + "\n"
    
    return Response(stream_with_context(load_video_data()), mimetype="application/x-ndjson")

@app.route('/api/download_videos', methods=['POST'])
def download_videos():
    """Start download and return download_id"""
    global playlist_session
    try:
        data = request.get_json()
        video_urls = data.get('video_urls', [])
        save_path = data.get('save_path', str(DOWNLOAD_FOLDER))
        quality = data.get('quality', 'Cao nhất')
        concurrent_downloads = data.get('concurrent_downloads', 5)

        if not video_urls:
            return jsonify({'error': 'No video URLs provided'}), 400
        
        items=[]
        for i, url in enumerate(video_urls, 1):
            item = playlist_session[url]
            item['save_path'] = save_path
            item['quality'] = quality
            items.append(item)

        download_id = str(uuid.uuid4())
        
        download_queues[download_id] = Queue()
        
        download_tasks[download_id] = {
            'status': 'started',
            'total': len(video_urls),
            'completed': 0,
            'videos': {}
        }
        thread = threading.Thread(
            target=run_async_downloads,
            args=(download_id, items, concurrent_downloads)
        )
        thread.daemon = True
        thread.start()

        
        return jsonify({
            'download_id': download_id,
            'status': 'started',
            'total': len(video_urls)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def emit_progress(download_id, data):
    """Emit progress event to SSE queue"""
    if download_id in download_queues:
        download_queues[download_id].put(data)

def run_async_downloads(download_id, items, concurrent_downloads):
    """Wrapper to run async downloads in background thread"""
    download_stopped.clear()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        emit_progress(download_id, {
            'type': 'started',
            'total': len(items)
        })
        loop.run_until_complete(
            download_multiple_videos(download_id, items, concurrent_downloads)
        )
    except Exception as e:
        print(f"Error in run_async_downloads: {e}")
        emit_progress(download_id, {
            'type': 'error',
            'error': str(e)
        })
    finally:
        loop.close()
        download_stopped.set()

@app.route('/api/download_progress/<download_id>', methods=['GET'])
def download_progress(download_id):
    """Stream download progress via Server-Sent Events"""
    def generate():
        if download_id not in download_queues:
            yield f"data: {json.dumps({'error': 'Invalid download_id'})}\n\n"
            return
        
        queue = download_queues[download_id]
        
        while True:
            try:
                event = queue.get(timeout=30)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event.get('type') in ['completed', 'error']:
                    if download_id in download_queues:
                        del download_queues[download_id]
                    break
            except:
                yield f": keepalive\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Access-Control-Allow-Origin': '*'
        }
    )

@app.route('/api/download/stop', methods=['POST'])
def api_download_stop():
    """Handle stop download request from frontend."""
    try:
        print("Waiting for downloads to stop...")
        download_stopped.wait()
        print("Downloads stopped.")
        response = jsonify({'message': 'Stop command received'})
        return response
    except Exception as e:
        print(f"Error in api_download_stop: {e}")
        response = jsonify({'error': str(e)})
        return response, 500

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Shutdown the server."""
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        os._exit(0)
    func()
    return 'Server shutting down...'

if __name__ == '__main__':
    app.run(debug=True, port=5000)

