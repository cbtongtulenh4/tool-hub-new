import os
import sys
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from yt_dlp import YoutubeDL
sys.stdout.reconfigure(encoding="utf-8")
def get_extract_options():
    return {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
        "ignoreerrors": True,
        # "cookiefile": r"D:\tiktok-cookies.txt",
    }
tab_url = "https://www.douyin.com/user/MS4wLjABAAAAS8wZfJe1top4fYXXWzNUT7ddiR7_JDL3LTfRvWIAaVk"
video_urls = []
try:
    with YoutubeDL(get_extract_options()) as ydl:
        info = ydl.extract_info(tab_url, download=False)
        entries = info.get("entries", [])
        count = 0
        for e in entries:
            if not e or not e.get("id"):
                continue

            item = {
                "url": f"https://www.tiktok.com/@vie_vie_205/video/{e['id']}",
                "title": e.get("title", ""),
            }
            video_urls.append(item)
            print(item)
            count += 1
        print(f"Tìm thấy {count}")
except Exception as ex:
    print(f"Lỗi khi quét {ex}")