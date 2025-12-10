import asyncio
import os
import re
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, make_response
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

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)


# Create media_download folder if it doesn't exist
DOWNLOAD_FOLDER = Path("media_download")
DOWNLOAD_FOLDER.mkdir(exist_ok=True)
FFMPEG_PATH = "./bin/ffmpeg.exe"

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

        if platform == "youtube":
            YouTubeDownloader(url, DOWNLOAD_FOLDER, 0, FFMPEG_PATH).download_worker(url)
            return {
                "url": url,
                "status": "success",
                "filename": "",
                "title": "",
                "duration": ""
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

@app.route('/api/load_list_user_videos', methods=['POST'])
def load_list_user_videos():
    try:
        data = request.get_json()
        user_url = data.get('url', '')
        
        if not user_url:
            return jsonify({"error": "Không có URL kênh nào được cung cấp"}), 400

        group_urls = classify_urls([user_url])
        group = group_urls[0]
        temp = group[0]
        items = []
        if temp['type'] == 'channel':
            if temp['platform'] == "tiktok" or temp['platform'] == "douyin":
                scraper = DouyinTiktokScraper(
                    douyin_cookie="ttwid=1%7CBD3GjtVoizObrVlBxAjnS7sw4iCYET8Lz1fvFRBcb9s%7C1765099018%7C95911db5fe6d88cce9fe58f586b9661d9b49ef041146760b0b429fa65f17d6ec; enter_pc_once=1; UIFID_TEMP=47253ff694b1a3f0276ef6188afc260853569160d1a9e22d73502760654854795f67336c30a5aae0d9f9a5b736035302ccbfc714f928c82e905e34a16ee3f93c8073d4df545db26c9c24e738aab9e4c9; hevc_supported=true; xgplayer_user_id=579737460722; fpk1=U2FsdGVkX1+iy1hukcoNKPtmFQaulDXO5OBUUU5d2bXfv6UTj6ScmMPReVi35gq0E6CZk7YpE/oh7gu0yHG5Sg==; fpk2=bfe921b394bf10c8d08c5999edfccc8d; bd_ticket_guard_client_web_domain=2; bd_ticket_guard_client_data_v2=eyJyZWVfcHVibGljX2tleSI6IkJNNktiK2dYeFVNd0ZnS241T0x0WDd3Y0RQUzMxM3FhWDJnZE5iUzE1aUYwQUxaKzIwZWlrRDF4S3NaWVIwWW11S0NrUk1VU0hjSUFpTzdzSjhVckthYz0iLCJ0c19zaWduIjoidHMuMi4zYmU4ZTEyODY2ZDk4YmUyMTFlMjA0YjNjYjRlNTZiNGJkNTcxZGRjYjBkNGQwMWJhMGQ3ZjJhNjZiMmFjZDNkYzRmYmU4N2QyMzE5Y2YwNTMxODYyNGNlZGExNDkxMWNhNDA2ZGVkYmViZWRkYjJlMzBmY2U4ZDRmYTAyNTc1ZCIsInJlcV9jb250ZW50Ijoic2VjX3RzIiwicmVxX3NpZ24iOiJOUkE4QUl4Z1VWVStVYTEramgzRjFCZDQxYXF0SGdvaE9aSjRwZ2xXWmZFPSIsInNlY190cyI6IiNKdkxKbDVZUUt3a0twUnhZMGZqYUxVM1ZpZno1NGlTSEVvTnNTbk1EeHJaVEJIYjQ2MGJaQU5lQU5ZblMifQ%3D%3D; odin_tt=c7fffa135a0bcb84e7c1b799548dc538ffe2246fb6cca1ac434740885c1e282236bfa726561fc60bbfedc961f0188694b7afa80b6620cde73f8371a5fa5b28ce; UIFID=47253ff694b1a3f0276ef6188afc260853569160d1a9e22d735027606548547974ba1127f039352ad446e71a171a006b21c539738d2a3709b3b9723b06104ed0bdf417c279822f556089112aa631f76a7632dc748fc624b4f55e9a67d308865f0a85c5d0324db726dda27479b40b790e4b5711316ab73bcb910b5460cfdc6b2e62cb296eca3f738248662417e389e671e17f9fd3faee6758a00d5e57d69eb746; IsDouyinActive=true; home_can_add_dy_2_desktop=%220%22; dy_swidth=1920; dy_sheight=1080; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A1920%2C%5C%22screen_height%5C%22%3A1080%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A16%2C%5C%22device_memory%5C%22%3A0%2C%5C%22downlink%5C%22%3A%5C%22%5C%22%2C%5C%22effective_type%5C%22%3A%5C%22%5C%22%2C%5C%22round_trip_time%5C%22%3A0%7D%22; strategyABtestKey=%221765099012.711%22; s_v_web_id=verify_miqbhvc2_Lhxa2v2g_Kqe2_43SZ_90a4_RWMbrdkSQjeJ; is_dash_user=1; passport_csrf_token=660815ecff8b7c91e613a68307e9718b; passport_csrf_token_default=660815ecff8b7c91e613a68307e9718b; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Atrue%2C%22volume%22%3A0.6%7D; __security_mc_1_s_sdk_crypt_sdk=8b8b24d8-47bb-9077; stream_player_status_params=%22%7B%5C%22is_auto_play%5C%22%3A0%2C%5C%22is_full_screen%5C%22%3A0%2C%5C%22is_full_webscreen%5C%22%3A1%2C%5C%22is_mute%5C%22%3A1%2C%5C%22is_speed%5C%22%3A1%2C%5C%22is_visible%5C%22%3A0%7D%22; download_guide=%223%2F20251204%2F0%22; passport_mfa_token=CjafkCFrvWfl2eRWAsHEsft666gjDyorY0gTGwqOCt3dUrHI6%2BOpOSm3BogZfBU1GUAfauLwROQaSgo8AAAAAAAAAAAAAE%2FKv4fk7D884Id%2FXHU5oDF%2B3RJImLOAr0xFXXHDUkorS%2BwS3yLMu8ZvFpUV12nbZSw1EPOmgw4Y9rHRbCACIgEDTyS9Ag%3D%3D; d_ticket=a5e10219eb2a9ec9f3e8817cab8a3ff42be43; passport_assist_user=CkDkVuuz2G13H3cfC4ro1r7cghW9eeH3c6M3Y_WfY5eEkhFd4_3_eKGlbbb7PVs7_gvbrbCjyspJ7Tol6EoMOPAZGkoKPAAAAAAAAAAAAABPypXRi27gDOEqS3wa75CIOEGN5mUCRmJaVG8B-BpI234Gg1t6aKHB0zCrdcPlwhhkbRDcpYMOGImv1lQgASIBAx0y3bU%3D; n_mh=hUgTZD6li-owxWv0c9ucMJOYC9hjLhbRWR6AsBtoJb4; passport_auth_status=3749f688e926568ddbcd8f7d0d720d99%2C; passport_auth_status_ss=3749f688e926568ddbcd8f7d0d720d99%2C; sid_guard=3f44b6fbcf985a339fe3d39a1eaa7c19%7C1764864200%7C5184000%7CMon%2C+02-Feb-2026+16%3A03%3A20+GMT; uid_tt=a314143430a5288f866168d2f63c74b6; uid_tt_ss=a314143430a5288f866168d2f63c74b6; sid_tt=3f44b6fbcf985a339fe3d39a1eaa7c19; sessionid=3f44b6fbcf985a339fe3d39a1eaa7c19; sessionid_ss=3f44b6fbcf985a339fe3d39a1eaa7c19; session_tlb_tag=sttt%7C16%7CP0S2-8-YWjOf49OaHqp8Gf________-_ksP5DZn1K48-Wgua85vJaBYKUrMUnObA0iED3-Uq9sY%3D; session_tlb_tag_bk=sttt%7C16%7CP0S2-8-YWjOf49OaHqp8Gf________-_ksP5DZn1K48-Wgua85vJaBYKUrMUnObA0iED3-Uq9sY%3D; is_staff_user=false; sid_ucp_v1=1.0.0-KGMwNzBkZGRhOTk1NmQ5YTEyNzczY2MzODQ5NGNhMjFlOGI2NWVjYjIKIAjN0vCfvfUmEMjhxskGGO8xIAww___07QU4AkDxB0gEGgJscSIgM2Y0NGI2ZmJjZjk4NWEzMzlmZTNkMzlhMWVhYTdjMTk; ssid_ucp_v1=1.0.0-KGMwNzBkZGRhOTk1NmQ5YTEyNzczY2MzODQ5NGNhMjFlOGI2NWVjYjIKIAjN0vCfvfUmEMjhxskGGO8xIAww___07QU4AkDxB0gEGgJscSIgM2Y0NGI2ZmJjZjk4NWEzMzlmZTNkMzlhMWVhYTdjMTk; _bd_ticket_crypt_doamin=2; _bd_ticket_crypt_cookie=0577c5d260e5f6cc4a9b0bbb0cfce88c; __security_mc_1_s_sdk_sign_data_key_web_protect=c59d922a-45ce-9ea0; __security_mc_1_s_sdk_cert_key=aee3377c-4335-b639; __security_server_data_status=1; login_time=1764864201130; SelfTabRedDotControl=%5B%5D; FOLLOW_LIVE_POINT_INFO=%22MS4wLjABAAAAG30iru_BqzP12E8vXgcnbBoge2KOBtANJKJzUgF8YEg%2F1765126800000%2F0%2F0%2F1765099674325%22; publish_badge_show_info=%220%2C0%2C0%2C1764864228506%22; FOLLOW_NUMBER_YELLOW_POINT_INFO=%22MS4wLjABAAAAG30iru_BqzP12E8vXgcnbBoge2KOBtANJKJzUgF8YEg%2F1765126800000%2F0%2F1765099074326%2F0%22; WallpaperGuide=%7B%22showTime%22%3A1764888586759%2C%22closeTime%22%3A0%2C%22showCount%22%3A1%2C%22cursor1%22%3A14%2C%22cursor2%22%3A4%2C%22hoverTime%22%3A1764982206395%7D; __ac_nonce=0693545f10082f703a313; __ac_signature=_02B4Z6wo00f012WDvkAAAIDAIFjQ.JEnpdtlsrrAALBgp0n8lAgcQ0kqAj7BjEOzqzrpiYqL.MtNZyvWS.u3bzaPwbzt7dkqyMG1.al49--ws9iC-O51nyO0AigFxUEZyjIWiZwHLaOJ5ksebc; douyin.com; xg_device_score=7.43799004027265; device_web_cpu_core=16; device_web_memory_size=-1; architecture=amd64; biz_trace_id=c8a2597a; sdk_source_info=7e276470716a68645a606960273f276364697660272927676c715a6d6069756077273f276364697660272927666d776a68605a607d71606b766c6a6b5a7666776c7571273f275e58272927666a6b766a69605a696c6061273f27636469766027292762696a6764695a7364776c6467696076273f275e582729277672715a646971273f2763646976602729277f6b5a666475273f2763646976602729276d6a6e5a6b6a716c273f2763646976602729276c6b6f5a7f6367273f27636469766027292771273f273731323237353c3c3530333234272927676c715a75776a716a666a69273f2763646976602778; bit_env=5M0fJ5rH_UqjctpWA5inZRnxCwojrNKP5Z99PVmNnnFTe3qgK61vMIS5SUN0U8MtorcSxenMS97glf_Pj15BpfKfksiCBvttOwHr6QyUPTpVl7px5QkqGVX2EaPmCbJ9w-UgBviT07sRSUmIaLsdBt5wK1T0584zxObyRLhiAYUcHvwMg6GNRixxmlnz92houJ-tlrBQTNgGIT9urgM7vbJxEi509o6261v2e9Hr-646LfRfe0gScfXs-yumuMWX7lVT8toBO4gYrHwPGL--F4WFygETGQ6oHCT-9VJEIu8fGTmzEKsoZREeipedPsfO0wHXqpwQ1BIK0jtbTajmVljb01xRsJdWYt5aKCBEb1MLg7srZHXk9pmZW_3IdoLn7U_5IKZHDFeyQidDIbV33rN1jg6TTSBcP5q3Fz5p8zaIbxz3lXBhym0d0xNC1t_9vYMc9ZvNRptpvI_WNDWmHw%3D%3D; gulu_source_res=eyJwX2luIjoiNWI1Zjg1NGQzZDdiYzUzOGJiZTk0MDQ0NTcwYzkzNjA3YjI0MGVjYmZmODE4ZGY1ZWRmZWIxMmQwY2U2Yzg4MSJ9; passport_auth_mix_state=ypg0hmbjjtjpt8krp9p8cbupk0k5l22q; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCTTZLYitnWHhVTXdGZ0tuNU9MdFg3d2NEUFMzMTNxYVgyZ2ROYlMxNWlGMEFMWisyMGVpa0QxeEtzWllSMFltdUtDa1JNVVNIY0lBaU83c0o4VXJLYWM9IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoyfQ%3D%3D",
                    tiktok_cookie="ttwid=1%7CkO5yilXeGaNWdFUd9vniAYyowHOs1hnLOFMM98nU3oE%7C1765118143%7C48237e937dbb6681b31003f29bf733d2f0cb8cbf9177320e9c4bcbdbe644acea; tt_chain_token=4CqUZ4QcMUs9Qsa0B8AqWw==; tiktok_webapp_theme_source=auto; tiktok_webapp_theme=dark; msToken=FuTnwlyt0j3jPWErZfLSf12y4fp98aw0FrXvxGOWX1DcNWge6mYJGZWp4aJGwszamk19UAs-kuBqd-5BdsR94y4twvrEQKVjmVUOEzsgKGr_1A07MpapENr0J6886-29umSsABQVTP3XhcgujJUlQv8=; odin_tt=f8bf6f24c0e8a8f71e8814f6aa4af33addef3bc5944615835be9e0261799149a27057a94dd608d88d71ddbc3ecd3e6779129022e463ac438caf1af2f44605ea190bb193e492d4d0beb100c9cd238b960; passport_csrf_token=925357f378a22b9194b9a186e4d768ec; passport_csrf_token_default=925357f378a22b9194b9a186e4d768ec; delay_guest_mode_vid=5; tt_csrf_token=bFtcJt0m-J2JzQyez29lWbxfbxq3I9jQB52U; s_v_web_id=verify_mivtr9og_YibNzABY_GRvO_4fc3_Bjzz_QjE05qSbMGt1; multi_sids=7440878950417794103%3A060ade417db635170c34b0c2cced01e1; cmpl_token=AgQYAPOF_hfkTtK3faFc6GddDvN3-Wp-z_-QDmCjfH8; sid_guard=060ade417db635170c34b0c2cced01e1%7C1765118136%7C15552000%7CFri%2C+05-Jun-2026+14%3A35%3A36+GMT; uid_tt=9c20af74aac806a2b58aca04ec9051c5d0e8ce1c54bd25c0e4805ca972895167; uid_tt_ss=9c20af74aac806a2b58aca04ec9051c5d0e8ce1c54bd25c0e4805ca972895167; sid_tt=060ade417db635170c34b0c2cced01e1; sessionid=060ade417db635170c34b0c2cced01e1; sessionid_ss=060ade417db635170c34b0c2cced01e1; tt_session_tlb_tag=sttt%7C5%7CBgreQX22NRcMNLDCzO0B4f_________CM7VtH8TXBhsswwqSIfAZq4KBKNu1yEOkPmjYoixMWaA%3D; sid_ucp_v1=1.0.1-KGJhNGIwMjIzY2M5MTNiZTk0OThjOWQ0MWVhM2U0NGFkYmNiM2ZlZTUKIgi3iNaCtv_ToWcQuKHWyQYYswsgDDCgoI26BjgHQPQHSAQQAxoGbWFsaXZhIiAwNjBhZGU0MTdkYjYzNTE3MGMzNGIwYzJjY2VkMDFlMTJOCiCEf8NwuuOZ9YKKxuHWCa4pDgHHEBgDHKeLjwWVs73nKRIgdv9-OeVuXnTCzPZh_fB0NHhOhCRyOhbTd_819SZ0s4YYAiIGdGlrdG9r; ssid_ucp_v1=1.0.1-KGJhNGIwMjIzY2M5MTNiZTk0OThjOWQ0MWVhM2U0NGFkYmNiM2ZlZTUKIgi3iNaCtv_ToWcQuKHWyQYYswsgDDCgoI26BjgHQPQHSAQQAxoGbWFsaXZhIiAwNjBhZGU0MTdkYjYzNTE3MGMzNGIwYzJjY2VkMDFlMTJOCiCEf8NwuuOZ9YKKxuHWCa4pDgHHEBgDHKeLjwWVs73nKRIgdv9-OeVuXnTCzPZh_fB0NHhOhCRyOhbTd_819SZ0s4YYAiIGdGlrdG9r; store-idc=alisg; store-country-sign=MEIEDF06NFTWTvv4EgpaLAQgFDVG_5OSU7-6iuylH2Y6cwRXbVzsZU4i0ACaW8kDyfMEEJpsNweLnAZK-1Jb6gETR_U; store-country-code=vn; store-country-code-src=uid; tt-target-idc=alisg; tt-target-idc-sign=Oh_RqMtekTzoeohZYKd_WcBb7lUp8AASX98scnMMCLxcr4P4_kFHq6XNbWaT0FRCPiWyMGJO2au0laGs0m_-0eCtFFbIlbE1OSy4bUClHSYF5bON4KmnMk8hsVIigX2Ci4CkC2CpJC8brzA0-72aAN8AO8i8rajzDaS4MYDd-BEV235R551nYtG6kf4fN6PCCoWbyivFQD8MgaF7qt9Vwd162iuUaj91mCYtdZWSlSigleqo3KItsokMZOPTFxPt5MnkJBW7LT-ddmwLFxeGIzX2R021Q9CwSIkg_HA8mGfImk2wv9plsxBq5Zl_u3PgHSwRAyjzVLg951APkITX7o9bKAwwlvnhe3f1i1T3peXQ1hIDsYMXZzBBmvxcK5OVd0o_syfo7h_iZFQsKqm9HzMZ7b90s5gttfZEZanasBhKniyMPp0jCf7VMctF9bBEBJASvbz8cj0NltT9QF5SDIctiQv_hPA9fuyri3cYRgFXFzsxLZjIjaDZ5-7uiWSI; last_login_method=QRcode; passport_fe_beating_status=true; perf_feed_cache={%22expireTimestamp%22:1765288800000%2C%22itemIds%22:[%227580215398243552542%22%2C%227566645514549153045%22%2C%227577963420746648853%22]}; msToken=2_FfizMOPLM3Vh3eXBIQtOAcveWoHo7y7rgBQzjCaXtQGmODl2zEG--BFF5Zxdo8FeGxH7_0EzGn_LI2WdiNItfSDqVw5wNRCN1B1z0RPgUfp7NQ0qzP955gfEg-L5kX263UpoJ9VDAFOYou-Y8HEbY="
                )
                if temp['platform'] == "douyin":
                    items = asyncio.run(scraper.douyin_fetch_user_post_videos(sec_user_id=temp['sec_user_id'], max_cursor=0, count=50))  
            elif temp['platform'] == "youtube":
                items = YouTubeDownloader(temp['url'], "", 0, FFMPEG_PATH).get_channel_videos()
        else:
            return jsonify({"error": "Not match url"}), 400
        return jsonify({"items": items}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/load_info_from_videos', methods=['POST'])
def load_info_from_videos():
    try:
        data = request.get_json()
        user_url = data.get('urls', '')
        urls = [url.strip() for url in user_url.split("\n") if url.strip()]
        
        if not urls:
            return jsonify({"error": "Không có URL kênh nào được cung cấp"}), 400

        group_urls = classify_urls(urls)

        temp = group_urls[0]
        items = []
        if temp['type'] == 'channel':
            if temp['platform'] == "tiktok" or temp['platform'] == "douyin":
                scraper = DouyinTiktokScraper(
                    douyin_cookie="ttwid=1%7CBD3GjtVoizObrVlBxAjnS7sw4iCYET8Lz1fvFRBcb9s%7C1765099018%7C95911db5fe6d88cce9fe58f586b9661d9b49ef041146760b0b429fa65f17d6ec; enter_pc_once=1; UIFID_TEMP=47253ff694b1a3f0276ef6188afc260853569160d1a9e22d73502760654854795f67336c30a5aae0d9f9a5b736035302ccbfc714f928c82e905e34a16ee3f93c8073d4df545db26c9c24e738aab9e4c9; hevc_supported=true; xgplayer_user_id=579737460722; fpk1=U2FsdGVkX1+iy1hukcoNKPtmFQaulDXO5OBUUU5d2bXfv6UTj6ScmMPReVi35gq0E6CZk7YpE/oh7gu0yHG5Sg==; fpk2=bfe921b394bf10c8d08c5999edfccc8d; bd_ticket_guard_client_web_domain=2; bd_ticket_guard_client_data_v2=eyJyZWVfcHVibGljX2tleSI6IkJNNktiK2dYeFVNd0ZnS241T0x0WDd3Y0RQUzMxM3FhWDJnZE5iUzE1aUYwQUxaKzIwZWlrRDF4S3NaWVIwWW11S0NrUk1VU0hjSUFpTzdzSjhVckthYz0iLCJ0c19zaWduIjoidHMuMi4zYmU4ZTEyODY2ZDk4YmUyMTFlMjA0YjNjYjRlNTZiNGJkNTcxZGRjYjBkNGQwMWJhMGQ3ZjJhNjZiMmFjZDNkYzRmYmU4N2QyMzE5Y2YwNTMxODYyNGNlZGExNDkxMWNhNDA2ZGVkYmViZWRkYjJlMzBmY2U4ZDRmYTAyNTc1ZCIsInJlcV9jb250ZW50Ijoic2VjX3RzIiwicmVxX3NpZ24iOiJOUkE4QUl4Z1VWVStVYTEramgzRjFCZDQxYXF0SGdvaE9aSjRwZ2xXWmZFPSIsInNlY190cyI6IiNKdkxKbDVZUUt3a0twUnhZMGZqYUxVM1ZpZno1NGlTSEVvTnNTbk1EeHJaVEJIYjQ2MGJaQU5lQU5ZblMifQ%3D%3D; odin_tt=c7fffa135a0bcb84e7c1b799548dc538ffe2246fb6cca1ac434740885c1e282236bfa726561fc60bbfedc961f0188694b7afa80b6620cde73f8371a5fa5b28ce; UIFID=47253ff694b1a3f0276ef6188afc260853569160d1a9e22d735027606548547974ba1127f039352ad446e71a171a006b21c539738d2a3709b3b9723b06104ed0bdf417c279822f556089112aa631f76a7632dc748fc624b4f55e9a67d308865f0a85c5d0324db726dda27479b40b790e4b5711316ab73bcb910b5460cfdc6b2e62cb296eca3f738248662417e389e671e17f9fd3faee6758a00d5e57d69eb746; IsDouyinActive=true; home_can_add_dy_2_desktop=%220%22; dy_swidth=1920; dy_sheight=1080; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A1920%2C%5C%22screen_height%5C%22%3A1080%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A16%2C%5C%22device_memory%5C%22%3A0%2C%5C%22downlink%5C%22%3A%5C%22%5C%22%2C%5C%22effective_type%5C%22%3A%5C%22%5C%22%2C%5C%22round_trip_time%5C%22%3A0%7D%22; strategyABtestKey=%221765099012.711%22; s_v_web_id=verify_miqbhvc2_Lhxa2v2g_Kqe2_43SZ_90a4_RWMbrdkSQjeJ; is_dash_user=1; passport_csrf_token=660815ecff8b7c91e613a68307e9718b; passport_csrf_token_default=660815ecff8b7c91e613a68307e9718b; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Atrue%2C%22volume%22%3A0.6%7D; __security_mc_1_s_sdk_crypt_sdk=8b8b24d8-47bb-9077; stream_player_status_params=%22%7B%5C%22is_auto_play%5C%22%3A0%2C%5C%22is_full_screen%5C%22%3A0%2C%5C%22is_full_webscreen%5C%22%3A1%2C%5C%22is_mute%5C%22%3A1%2C%5C%22is_speed%5C%22%3A1%2C%5C%22is_visible%5C%22%3A0%7D%22; download_guide=%223%2F20251204%2F0%22; passport_mfa_token=CjafkCFrvWfl2eRWAsHEsft666gjDyorY0gTGwqOCt3dUrHI6%2BOpOSm3BogZfBU1GUAfauLwROQaSgo8AAAAAAAAAAAAAE%2FKv4fk7D884Id%2FXHU5oDF%2B3RJImLOAr0xFXXHDUkorS%2BwS3yLMu8ZvFpUV12nbZSw1EPOmgw4Y9rHRbCACIgEDTyS9Ag%3D%3D; d_ticket=a5e10219eb2a9ec9f3e8817cab8a3ff42be43; passport_assist_user=CkDkVuuz2G13H3cfC4ro1r7cghW9eeH3c6M3Y_WfY5eEkhFd4_3_eKGlbbb7PVs7_gvbrbCjyspJ7Tol6EoMOPAZGkoKPAAAAAAAAAAAAABPypXRi27gDOEqS3wa75CIOEGN5mUCRmJaVG8B-BpI234Gg1t6aKHB0zCrdcPlwhhkbRDcpYMOGImv1lQgASIBAx0y3bU%3D; n_mh=hUgTZD6li-owxWv0c9ucMJOYC9hjLhbRWR6AsBtoJb4; passport_auth_status=3749f688e926568ddbcd8f7d0d720d99%2C; passport_auth_status_ss=3749f688e926568ddbcd8f7d0d720d99%2C; sid_guard=3f44b6fbcf985a339fe3d39a1eaa7c19%7C1764864200%7C5184000%7CMon%2C+02-Feb-2026+16%3A03%3A20+GMT; uid_tt=a314143430a5288f866168d2f63c74b6; uid_tt_ss=a314143430a5288f866168d2f63c74b6; sid_tt=3f44b6fbcf985a339fe3d39a1eaa7c19; sessionid=3f44b6fbcf985a339fe3d39a1eaa7c19; sessionid_ss=3f44b6fbcf985a339fe3d39a1eaa7c19; session_tlb_tag=sttt%7C16%7CP0S2-8-YWjOf49OaHqp8Gf________-_ksP5DZn1K48-Wgua85vJaBYKUrMUnObA0iED3-Uq9sY%3D; session_tlb_tag_bk=sttt%7C16%7CP0S2-8-YWjOf49OaHqp8Gf________-_ksP5DZn1K48-Wgua85vJaBYKUrMUnObA0iED3-Uq9sY%3D; is_staff_user=false; sid_ucp_v1=1.0.0-KGMwNzBkZGRhOTk1NmQ5YTEyNzczY2MzODQ5NGNhMjFlOGI2NWVjYjIKIAjN0vCfvfUmEMjhxskGGO8xIAww___07QU4AkDxB0gEGgJscSIgM2Y0NGI2ZmJjZjk4NWEzMzlmZTNkMzlhMWVhYTdjMTk; ssid_ucp_v1=1.0.0-KGMwNzBkZGRhOTk1NmQ5YTEyNzczY2MzODQ5NGNhMjFlOGI2NWVjYjIKIAjN0vCfvfUmEMjhxskGGO8xIAww___07QU4AkDxB0gEGgJscSIgM2Y0NGI2ZmJjZjk4NWEzMzlmZTNkMzlhMWVhYTdjMTk; _bd_ticket_crypt_doamin=2; _bd_ticket_crypt_cookie=0577c5d260e5f6cc4a9b0bbb0cfce88c; __security_mc_1_s_sdk_sign_data_key_web_protect=c59d922a-45ce-9ea0; __security_mc_1_s_sdk_cert_key=aee3377c-4335-b639; __security_server_data_status=1; login_time=1764864201130; SelfTabRedDotControl=%5B%5D; FOLLOW_LIVE_POINT_INFO=%22MS4wLjABAAAAG30iru_BqzP12E8vXgcnbBoge2KOBtANJKJzUgF8YEg%2F1765126800000%2F0%2F0%2F1765099674325%22; publish_badge_show_info=%220%2C0%2C0%2C1764864228506%22; FOLLOW_NUMBER_YELLOW_POINT_INFO=%22MS4wLjABAAAAG30iru_BqzP12E8vXgcnbBoge2KOBtANJKJzUgF8YEg%2F1765126800000%2F0%2F1765099074326%2F0%22; WallpaperGuide=%7B%22showTime%22%3A1764888586759%2C%22closeTime%22%3A0%2C%22showCount%22%3A1%2C%22cursor1%22%3A14%2C%22cursor2%22%3A4%2C%22hoverTime%22%3A1764982206395%7D; __ac_nonce=0693545f10082f703a313; __ac_signature=_02B4Z6wo00f012WDvkAAAIDAIFjQ.JEnpdtlsrrAALBgp0n8lAgcQ0kqAj7BjEOzqzrpiYqL.MtNZyvWS.u3bzaPwbzt7dkqyMG1.al49--ws9iC-O51nyO0AigFxUEZyjIWiZwHLaOJ5ksebc; douyin.com; xg_device_score=7.43799004027265; device_web_cpu_core=16; device_web_memory_size=-1; architecture=amd64; biz_trace_id=c8a2597a; sdk_source_info=7e276470716a68645a606960273f276364697660272927676c715a6d6069756077273f276364697660272927666d776a68605a607d71606b766c6a6b5a7666776c7571273f275e58272927666a6b766a69605a696c6061273f27636469766027292762696a6764695a7364776c6467696076273f275e582729277672715a646971273f2763646976602729277f6b5a666475273f2763646976602729276d6a6e5a6b6a716c273f2763646976602729276c6b6f5a7f6367273f27636469766027292771273f273731323237353c3c3530333234272927676c715a75776a716a666a69273f2763646976602778; bit_env=5M0fJ5rH_UqjctpWA5inZRnxCwojrNKP5Z99PVmNnnFTe3qgK61vMIS5SUN0U8MtorcSxenMS97glf_Pj15BpfKfksiCBvttOwHr6QyUPTpVl7px5QkqGVX2EaPmCbJ9w-UgBviT07sRSUmIaLsdBt5wK1T0584zxObyRLhiAYUcHvwMg6GNRixxmlnz92houJ-tlrBQTNgGIT9urgM7vbJxEi509o6261v2e9Hr-646LfRfe0gScfXs-yumuMWX7lVT8toBO4gYrHwPGL--F4WFygETGQ6oHCT-9VJEIu8fGTmzEKsoZREeipedPsfO0wHXqpwQ1BIK0jtbTajmVljb01xRsJdWYt5aKCBEb1MLg7srZHXk9pmZW_3IdoLn7U_5IKZHDFeyQidDIbV33rN1jg6TTSBcP5q3Fz5p8zaIbxz3lXBhym0d0xNC1t_9vYMc9ZvNRptpvI_WNDWmHw%3D%3D; gulu_source_res=eyJwX2luIjoiNWI1Zjg1NGQzZDdiYzUzOGJiZTk0MDQ0NTcwYzkzNjA3YjI0MGVjYmZmODE4ZGY1ZWRmZWIxMmQwY2U2Yzg4MSJ9; passport_auth_mix_state=ypg0hmbjjtjpt8krp9p8cbupk0k5l22q; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCTTZLYitnWHhVTXdGZ0tuNU9MdFg3d2NEUFMzMTNxYVgyZ2ROYlMxNWlGMEFMWisyMGVpa0QxeEtzWllSMFltdUtDa1JNVVNIY0lBaU83c0o4VXJLYWM9IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoyfQ%3D%3D",
                    tiktok_cookie="ttwid=1%7CkO5yilXeGaNWdFUd9vniAYyowHOs1hnLOFMM98nU3oE%7C1765118143%7C48237e937dbb6681b31003f29bf733d2f0cb8cbf9177320e9c4bcbdbe644acea; tt_chain_token=4CqUZ4QcMUs9Qsa0B8AqWw==; tiktok_webapp_theme_source=auto; tiktok_webapp_theme=dark; msToken=FuTnwlyt0j3jPWErZfLSf12y4fp98aw0FrXvxGOWX1DcNWge6mYJGZWp4aJGwszamk19UAs-kuBqd-5BdsR94y4twvrEQKVjmVUOEzsgKGr_1A07MpapENr0J6886-29umSsABQVTP3XhcgujJUlQv8=; odin_tt=f8bf6f24c0e8a8f71e8814f6aa4af33addef3bc5944615835be9e0261799149a27057a94dd608d88d71ddbc3ecd3e6779129022e463ac438caf1af2f44605ea190bb193e492d4d0beb100c9cd238b960; passport_csrf_token=925357f378a22b9194b9a186e4d768ec; passport_csrf_token_default=925357f378a22b9194b9a186e4d768ec; delay_guest_mode_vid=5; tt_csrf_token=bFtcJt0m-J2JzQyez29lWbxfbxq3I9jQB52U; s_v_web_id=verify_mivtr9og_YibNzABY_GRvO_4fc3_Bjzz_QjE05qSbMGt1; multi_sids=7440878950417794103%3A060ade417db635170c34b0c2cced01e1; cmpl_token=AgQYAPOF_hfkTtK3faFc6GddDvN3-Wp-z_-QDmCjfH8; sid_guard=060ade417db635170c34b0c2cced01e1%7C1765118136%7C15552000%7CFri%2C+05-Jun-2026+14%3A35%3A36+GMT; uid_tt=9c20af74aac806a2b58aca04ec9051c5d0e8ce1c54bd25c0e4805ca972895167; uid_tt_ss=9c20af74aac806a2b58aca04ec9051c5d0e8ce1c54bd25c0e4805ca972895167; sid_tt=060ade417db635170c34b0c2cced01e1; sessionid=060ade417db635170c34b0c2cced01e1; sessionid_ss=060ade417db635170c34b0c2cced01e1; tt_session_tlb_tag=sttt%7C5%7CBgreQX22NRcMNLDCzO0B4f_________CM7VtH8TXBhsswwqSIfAZq4KBKNu1yEOkPmjYoixMWaA%3D; sid_ucp_v1=1.0.1-KGJhNGIwMjIzY2M5MTNiZTk0OThjOWQ0MWVhM2U0NGFkYmNiM2ZlZTUKIgi3iNaCtv_ToWcQuKHWyQYYswsgDDCgoI26BjgHQPQHSAQQAxoGbWFsaXZhIiAwNjBhZGU0MTdkYjYzNTE3MGMzNGIwYzJjY2VkMDFlMTJOCiCEf8NwuuOZ9YKKxuHWCa4pDgHHEBgDHKeLjwWVs73nKRIgdv9-OeVuXnTCzPZh_fB0NHhOhCRyOhbTd_819SZ0s4YYAiIGdGlrdG9r; ssid_ucp_v1=1.0.1-KGJhNGIwMjIzY2M5MTNiZTk0OThjOWQ0MWVhM2U0NGFkYmNiM2ZlZTUKIgi3iNaCtv_ToWcQuKHWyQYYswsgDDCgoI26BjgHQPQHSAQQAxoGbWFsaXZhIiAwNjBhZGU0MTdkYjYzNTE3MGMzNGIwYzJjY2VkMDFlMTJOCiCEf8NwuuOZ9YKKxuHWCa4pDgHHEBgDHKeLjwWVs73nKRIgdv9-OeVuXnTCzPZh_fB0NHhOhCRyOhbTd_819SZ0s4YYAiIGdGlrdG9r; store-idc=alisg; store-country-sign=MEIEDF06NFTWTvv4EgpaLAQgFDVG_5OSU7-6iuylH2Y6cwRXbVzsZU4i0ACaW8kDyfMEEJpsNweLnAZK-1Jb6gETR_U; store-country-code=vn; store-country-code-src=uid; tt-target-idc=alisg; tt-target-idc-sign=Oh_RqMtekTzoeohZYKd_WcBb7lUp8AASX98scnMMCLxcr4P4_kFHq6XNbWaT0FRCPiWyMGJO2au0laGs0m_-0eCtFFbIlbE1OSy4bUClHSYF5bON4KmnMk8hsVIigX2Ci4CkC2CpJC8brzA0-72aAN8AO8i8rajzDaS4MYDd-BEV235R551nYtG6kf4fN6PCCoWbyivFQD8MgaF7qt9Vwd162iuUaj91mCYtdZWSlSigleqo3KItsokMZOPTFxPt5MnkJBW7LT-ddmwLFxeGIzX2R021Q9CwSIkg_HA8mGfImk2wv9plsxBq5Zl_u3PgHSwRAyjzVLg951APkITX7o9bKAwwlvnhe3f1i1T3peXQ1hIDsYMXZzBBmvxcK5OVd0o_syfo7h_iZFQsKqm9HzMZ7b90s5gttfZEZanasBhKniyMPp0jCf7VMctF9bBEBJASvbz8cj0NltT9QF5SDIctiQv_hPA9fuyri3cYRgFXFzsxLZjIjaDZ5-7uiWSI; last_login_method=QRcode; passport_fe_beating_status=true; perf_feed_cache={%22expireTimestamp%22:1765288800000%2C%22itemIds%22:[%227580215398243552542%22%2C%227566645514549153045%22%2C%227577963420746648853%22]}; msToken=2_FfizMOPLM3Vh3eXBIQtOAcveWoHo7y7rgBQzjCaXtQGmODl2zEG--BFF5Zxdo8FeGxH7_0EzGn_LI2WdiNItfSDqVw5wNRCN1B1z0RPgUfp7NQ0qzP955gfEg-L5kX263UpoJ9VDAFOYou-Y8HEbY="
                )
                if temp['platform'] == "douyin":
                    items = asyncio.run(scraper.douyin_fetch_user_post_videos(sec_user_id=temp['sec_user_id'], max_cursor=0, count=50))  
            elif temp['platform'] == "youtube":
                items = YouTubeDownloader(temp['url'], "", 0, FFMPEG_PATH).get_channel_videos()
        else:
            return jsonify({"error": "Not match url"}), 400
        return jsonify({"items": items}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/load_list_user_videos/stop', methods=['POST', 'OPTIONS'])
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)

