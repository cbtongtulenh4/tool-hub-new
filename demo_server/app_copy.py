import asyncio
import os
import re
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
import httpx
from fsmvid import FSMVIDDown
import webbrowser
import subprocess
import threading
import aiofiles
import requests
import uuid

app = Flask(__name__, static_folder='static')

# Create media_download folder if it doesn't exist
DOWNLOAD_FOLDER = Path("media_download")
DOWNLOAD_FOLDER.mkdir(exist_ok=True)

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to remove invalid characters."""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    return filename or "video"


def detect_platform(url: str) -> str:
    """Auto-detect platform from URL."""
    url_lower = url.lower()
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'tiktok.com' in url_lower:
        return 'tiktok'
    elif 'douyin.com' in url_lower:
        return 'douyin'
    elif 'facebook.com' in url_lower or 'fb.com' in url_lower:
        return 'facebook'
    else:
        return 'sax'  # Default to youtube

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
            if url.split("/")[-1].startswith("@"):
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
        url = item['url']
        platform = item['platform']
        if not platform:
            return {
                "url": url,
                "status": "error",
                "message": "not support this platform"
            }

        # Get video info from fsmvid
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
        
        if not medias:
            return {
                "url": url,
                "status": "error",
                "message": "Không tìm thấy media để download"
            }
        
        # Generate filename
        video_id = result.get("id", uuid.uuid4())
        title = result.get("title", "video")

        # Case 1: cnt == 1, video already has audio
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
                filepath = DOWNLOAD_FOLDER / filename
                # Download the image
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
            filepath = DOWNLOAD_FOLDER / filename
            # Download the video
            # async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
            #     async with client.stream("GET", video_url) as response:
            #         response.raise_for_status()
            #         with open(filepath, "wb") as f:
            #             async for chunk in response.aiter_bytes(chunk_size=1024*1024): 
            #                 f.write(chunk)
            async with httpx.AsyncClient(timeout=None, follow_redirects=True, http2=True) as client:
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
                # "size": len(response.content)
            }
        
        elif cnt == 2:
            video_media = medias[0]
            
            video_url = video_media.get("url")
            ext = video_media.get("ext", "mp4")
            filename = f"{sanitize_filename(video_id)}.{ext}"
            filepath = DOWNLOAD_FOLDER / filename
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
            audio_filepath = DOWNLOAD_FOLDER / audio_filename
            async with httpx.AsyncClient(timeout=None, follow_redirects=True, http2=True) as client:
                async with client.stream("GET", audio_url) as response:
                    response.raise_for_status()

                    async with aiofiles.open(audio_filepath, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=4 * 1024 * 1024):  # 4MB
                            await f.write(chunk)


            return {
                "url": url,
                "status": "error",
                "message": "something went wrong"
            }
    except Exception as e:
        return {
            "url": url,
            "status": "error",
            "message": str(e)
        }

def load_list_video_from_channel(channel_url: str) -> list:
    return []    

async def download_multiple_videos(items: list) -> list:
    """Download multiple videos in parallel."""
    tasks = [download_single_video(item, i) for i, item in enumerate(items)]
    results = await asyncio.gather(*tasks)
    return list(results)


@app.route('/')
def index():
    """Serve the main page."""
    return send_from_directory('static', 'index.html')



@app.route('/load_list_user_videos', methods=['POST'])
def load_list_user_videos():
    try:
        data = request.get_json()
        user_url = data.get('url', '')
        
        if not user_url:
            return jsonify({"error": "Không có URL kênh nào được cung cấp"}), 400


        
        
        return jsonify({"videos": load_list_video_from_channel(user_url)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/download', methods=['POST'])
def download():
    """Handle download request."""
    try:
        data = request.get_json()
        urls = data.get('urls', [])

        
        if not urls:
            return jsonify({"error": "Không có URL nào được cung cấp"}), 400
        
        urls = [url.strip() for url in urls if url.strip()]
        
        if not urls:
            return jsonify({"error": "Tất cả URLs đều rỗng"}), 400
        
        group_urls = classify_urls(urls)

        error_count_total = 0
        for group in group_urls:
            temp = group[0]
            if temp['type'] == 'channel':
                if temp['platform'] == "tiktok":
                    error_count_total += 1
                    continue
                    try:
                        resp = requests.get("https://api.douyin.wtf/api/tiktok/web/get_sec_user_id?url=https://www.tiktok.com/@hoangthachthao_")
                        secUid = resp.json()['data']
                    except Exception as e:
                        print(e)
                        continue
                elif temp['platform'] == "douyin":
                    urls = load_list_video_from_channel_douyin(temp['sec_user_id'])
                else:
                    error_count_total += 1
                    continue
                
            else:
                urls = group

            # Run async download
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(download_multiple_videos(urls))
            loop.close()
            
            # Count successes and failures
            success_count = sum(1 for r in results if r['status'] == 'success')
            error_count = len(results) - success_count

        return jsonify({
            "status": "completed",
            "total": len(results),
            "success": success_count,
            "errors": error_count_total + error_count,
            "results": results
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/videos/list', methods=['POST', 'OPTIONS'])
def api_videos_list():
    """Handle video list requests from frontend."""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.get_json()
        request_type = data.get('type', 'channel')
        urls = data.get('urls', [])
        query = data.get('query', '')
        platform = data.get('platform', 'tiktok')
        
        # Simulate processing delay
        import time
        import random
        time.sleep(1.5)
        
        if request_type == 'url' and urls:
            # Generate videos from URL list
            videos = []
            for idx, url in enumerate(urls):
                videos.append({
                    'id': idx + 1,
                    'url': url.strip(),
                    'caption': f'Video từ URL #{idx + 1}',
                    'comments': random.randint(0, 500),
                    'likes': f'{random.uniform(0.1, 20):.1f}K',
                    'views': f'{random.uniform(1, 100):.1f}K',
                    'shares': random.randint(0, 300),
                    'status': 'Sẵn sàng'
                })
            response = jsonify({'videos': videos})
        else:
            # Return default video list for channel
            default_videos = [
                {
                    'id': 1,
                    'url': 'https://www.tiktok.com/@user/video/1',
                    'caption': 'Hãy bảo vệ cảm xúc của bạn...',
                    'comments': 8,
                    'likes': '494',
                    'views': '9.7K',
                    'shares': 30,
                    'status': 'Sẵn sàng'
                },
                {
                    'id': 2,
                    'url': 'https://www.tiktok.com/@user/video/2',
                    'caption': 'Con người khó tính nhất...',
                    'comments': 2,
                    'likes': '321',
                    'views': '5.2K',
                    'shares': 21,
                    'status': 'Sẵn sàng'
                },
                {
                    'id': 3,
                    'url': 'https://www.tiktok.com/@user/video/3',
                    'caption': 'Tâm bất định, không làm...',
                    'comments': 45,
                    'likes': '3.4K',
                    'views': '37.8K',
                    'shares': 151,
                    'status': 'Sẵn sàng'
                }
            ]
            response = jsonify({'videos': default_videos})
        
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        print(f"Error in api_videos_list: {e}")
        response = jsonify({'error': str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500


@app.route('/api/videos/stop', methods=['POST', 'OPTIONS'])
def api_videos_stop():
    """Handle stop request from frontend."""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        # Simulate processing
        import time
        time.sleep(0.5)
        
        response = jsonify({'message': 'Stop command received'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        print(f"Error in api_videos_stop: {e}")
        response = jsonify({'error': str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500


@app.route('/choose-directory', methods=['GET', 'POST', 'OPTIONS'])
def choose_directory():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        return response

    try:
        # PowerShell command to open a Folder Browser Dialog
        ps_command = """
        Add-Type -AssemblyName System.Windows.Forms
        $f = New-Object System.Windows.Forms.FolderBrowserDialog
        $f.Description = "Chọn thư mục lưu video"
        $f.ShowNewFolderButton = $true
        if ($f.ShowDialog() -eq 'OK') {
            $f.SelectedPath
        } else {
            Write-Output "CANCELLED"
        }
        """
        
        # Execute PowerShell command
        result = subprocess.run(
            ["powershell", "-Command", ps_command], 
            capture_output=True, 
            text=True, 
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        selected_path = result.stdout.strip()
        
        if not selected_path or selected_path == "CANCELLED":
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

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Shutdown the server."""
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        # If running with other server or pyinstaller
        os._exit(0)
    func()
    return 'Server shutting down...'


def load_list_video_from_channel_douyin(sec_user_id: str) -> list:
    rs = []
    try:
        resp = requests.get(f"https://api.douyin.wtf/api/douyin/web/fetch_user_post_videos?sec_user_id={sec_user_id}&max_cursor=0&count=100")
        resp.raise_for_status()
        datas = resp.json()['data']
        for aweme in datas['aweme_list']:
            rs.append({'url': f"https://www.douyin.com/video/{aweme['aweme_id']}", 'platform': 'douyin', 'type': 'video'})
    except Exception as e:
        print(e)
    return rs

# def check_url_is_channel(urls: list) -> bool:
#     channel_urls = []
#     for url in urls:
#         url_lower = url.lower()
#         if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
#             return 'youtube'
#         elif 'tiktok.com' in url_lower:
#             return 'tiktok'
#         elif 'douyin.com' in url_lower:
#             return 'douyin'
#         elif 'facebook.com' in url_lower or 'fb.com' in url_lower:
#             return 'facebook'
#         else:
#             return 'sax'

def open_browser():
    """Open browser after a short delay to ensure server is ready."""
    import time
    time.sleep(1.5)  # Wait for server to start
    webbrowser.open('http://localhost:5000')


if __name__ == '__main__':
    # if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    #     threading.Thread(target=open_browser, daemon=True).start()
    app.run(debug=True, port=5000)

