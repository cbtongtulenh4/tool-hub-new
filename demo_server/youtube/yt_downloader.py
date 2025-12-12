import os
import sys
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from yt_dlp import YoutubeDL
sys.stdout.reconfigure(encoding="utf-8")

class YouTubeDownloader:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(YouTubeDownloader, cls).__new__(cls)
        return cls._instance

    def __init__(self, channel_url=None, output_dir=".", max_threads=4, ffmpeg_path=None):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self.ffmpeg_path = ffmpeg_path
        self.channel_url = channel_url
        self.output_dir = output_dir
        self.max_threads = max_threads
        
        if self.output_dir and not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        self._initialized = True

    def _get_ffmpeg_path(self):
        """Tự động tìm ffmpeg.exe trong folder bin khi chạy source hoặc file exe đóng gói."""
        if self.ffmpeg_path:
            return self.ffmpeg_path
        ffmpeg_filename = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        
        # Đường dẫn thư mục gốc (nơi chứa exe hoặc file py)
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        # Tìm trong folder bin
        bin_path = os.path.join(base_path, 'bin', ffmpeg_filename)
        if os.path.exists(bin_path):
            return bin_path
            
        # Fallback: Tìm ở thư mục gốc nếu không thấy trong bin
        root_path = os.path.join(base_path, ffmpeg_filename)
        if os.path.exists(root_path):
            return root_path
                
        # Nếu không tìm thấy, trả về None để yt-dlp tự tìm trong PATH
        return None

    def get_extract_options(self):
        return {
            "quiet": True,
            "extract_flat": True,
            "skip_download": True,
            "ignoreerrors": True,
        }

    def get_download_options(self):
        opts = {
            "format": "bv*[height<=1080]+ba/best",
            "outtmpl": os.path.join(self.output_dir, "%(title)s [%(id)s].%(ext)s"),
            "merge_output_format": "mp4",
            "postprocessor_args": ["-c:a", "aac", "-b:a", "192k"],
            "ignoreerrors": True,
            "retries": 3,
            "quiet": True,
            "no_warnings": True,
        }
        
        ffmpeg_loc = self._get_ffmpeg_path()
        if ffmpeg_loc:
            opts["ffmpeg_location"] = ffmpeg_loc
            
        return opts

    def get_channel_videos(self):
        if not self.channel_url:
            print("Error: No channel URL provided.")
            return []

        video_urls = []
        
        def extract_from_tab(tab_url, tab_name):
            try:
                with YoutubeDL(self.get_extract_options()) as ydl:
                    info = ydl.extract_info(tab_url, download=False)
                    entries = info.get("entries", [])
                    count = 0
                    for e in entries:
                        if e and e.get("id"):
                            url = f"https://www.youtube.com/watch?v={e['id']}"
                            title = e.get("title", "No Title")
                            item = {
                                "url": url,
                                "title": title,
                                "views": e.get("view_count", 0),
                                "likes": e.get("like_count", 0),
                                "comments": e.get("comment_count", 0),
                                "shares": 0,
                                "collects": 0
                            }
                            video_urls.append(item)
                            count += 1
                    print(f"Tìm thấy {count} {tab_name}.")
            except Exception as ex:
                print(f"Lỗi khi quét {tab_name}: {ex}")

        extract_from_tab(f"{self.channel_url}/videos", "Videos")
        extract_from_tab(f"{self.channel_url}/shorts", "Shorts")
        
        return video_urls

    def download_worker(self, url: str):
        opts = self.get_download_options()
        try:
            with YoutubeDL(opts) as ydl:
                ydl.download([url])
            return f"✅ DONE: {url}"
        except Exception as e:
            return f"❌ ERROR: {url} -> {e}"

    def download_from_list(self, video_list: list[str]):
        total_videos = len(video_list)
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            future_to_video = {executor.submit(self.download_worker, vid, "./"): vid for vid in video_list}
            
            completed_count = 0
            for future in as_completed(future_to_video):
                res = future.result()
                completed_count += 1
                try:
                    print(f"[{completed_count}/{total_videos}] {res}")
                except Exception:
                    pass
                
# if __name__ == "__main__":
#     a = YouTubeDownloader(ffmpeg_path=r"C:\source_code_new\backup\video-downloader-interface\demo_server\bin\ffmpeg.exe").download_worker(url="https://youtu.be/OYUY7Ugupts?si=KXiq3lTj_pYew979")