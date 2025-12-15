import asyncio
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx
import sys
from playwright.async_api import async_playwright
# if sys.stdout is not None:
#     sys.stdout.reconfigure(encoding="utf-8")
import uuid

FSMVID_DOWNLOAD_URL = "https://fsmvid.com/api/proxy"
FSMVID_BASE_URL = "https://fsmvid.com/"

async def _get_cookies_via_playwright() -> str:
    """Launch Playwright headlessly, navigate to FSMVID base URL, and return cookies as a header string."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(FSMVID_BASE_URL)
        await page.wait_for_load_state("networkidle")
        cookies = await page.context.cookies()
        return "; ".join(f"{c['name']}={c['value']}" for c in cookies)


class FSMVIDDown:
    """Singleton class to interact with FSMVID API with optional cookie handling."""

    _instance: Optional["FSMVIDDown"] = None
    _cookie_lock: asyncio.Lock = asyncio.Lock()
    _cached_cookie: Optional[str] = None

    def __new__(cls, *args, **kwargs) -> "FSMVIDDown":
        if cls._instance is None:
            cls._instance = super(FSMVIDDown, cls).__new__(cls)
        return cls._instance

    async def download(self, platform: str, download_url: str, cookie: str | None = None) -> Dict[str, Any]:
        """Call the FSMVID API and return a simplified result.

        If the API does not return the expected schema, the raw JSON is returned
        for the caller to handle.
        """
        payload = {"platform": platform, "url": download_url}

        timeout = httpx.Timeout(15.0, connect=10.0, read=10.0)
        
        # Use provided cookie, or cached cookie, or empty string
        current_cookie = cookie if cookie is not None else self._cached_cookie
        
        headers = {
            "accept": "*/*",
            # "accept-encoding": "gzip, deflate, br, zstd", # Let httpx handle encoding
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json",
            "origin": "https://fsmvid.com",
            "priority": "u=1, i",
            "referer": "https://fsmvid.com/",
            "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Cookie": current_cookie if current_cookie is not None else ""
        }

        async with httpx.AsyncClient(http2=True, timeout=timeout, headers=headers) as client:
            # Try the request with current headers
            try:
                resp = await client.post(FSMVID_DOWNLOAD_URL, json=payload)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as e:
                # If 403, we need to refresh cookies
                if e.response.status_code == 403:
                    # Acquire lock to ensure only one process refreshes the cookie
                    async with self._cookie_lock:
                        # Check if cookie was refreshed while we were waiting for the lock
                        if self._cached_cookie != current_cookie and self._cached_cookie is not None:
                            # Use the new cached cookie
                            headers["Cookie"] = self._cached_cookie
                        else:
                            # Actually refresh the cookie
                            fresh_cookies = await _get_cookies_via_playwright()
                            self._cached_cookie = fresh_cookies
                            headers["Cookie"] = fresh_cookies
                    
                    # Retry the request with the new cookie
                    resp = await client.post(FSMVID_DOWNLOAD_URL, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                else:
                    raise
            except Exception:
                raise

        if isinstance(data, dict) and data.get("status") == "success" and "medias" in data:
            return self.select_best_streams(data, platform)

        return data

    @staticmethod
    def _parse_height(media: Dict[str, Any]) -> Optional[int]:
        """Return height (p) from 'height' field or parse from 'label' like '(1080p)'."""
        h = media.get("height")
        if isinstance(h, int):
            return h
        label = media.get("label", "") or ""
        m = re.search(r"(\d{3,4})(?=p\b)", label)
        return int(m.group(1)) if m else None

    @staticmethod
    def _bitrate(media: Dict[str, Any]) -> int:
        """Return bitrate (bit/s); if missing, return 0."""
        br = media.get("bitrate")
        try:
            return int(br) if br is not None else 0
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _ext_rank(media: Dict[str, Any]) -> int:
        """Prefer mp4 over webm when quality is equal."""
        ext = (media.get("ext") or "").lower()
        return 0 if ext == "mp4" else 1

    @staticmethod
    def _youtube_platform(medias: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Select best video/audio for a single media entry (YouTube schema)."""
        best_video: Optional[Dict[str, Any]] = None
        best_audio: Optional[Dict[str, Any]] = None
        for media in medias:
            if media.get("type") == "video":
                if best_video is None:
                    best_video = media
                else:
                    hv = FSMVIDDown._parse_height(media) or -1
                    hb = FSMVIDDown._parse_height(best_video) or -1
                    if hv > hb and hv <= 1080:
                        best_video = media
                    elif hv == hb:
                        if FSMVIDDown._ext_rank(media) < FSMVIDDown._ext_rank(best_video):
                            best_video = media
                        elif FSMVIDDown._bitrate(media) > FSMVIDDown._bitrate(best_video):
                            best_video = media
                        else:
                            fps_new = media.get("fps") or 0
                            fps_old = best_video.get("fps") or 0
                            if fps_new > fps_old:
                                best_video = media
            elif media.get("type") == "audio":
                if best_audio is None:
                    best_audio = media
                else:
                    br_new = FSMVIDDown._bitrate(media)
                    br_old = FSMVIDDown._bitrate(best_audio)
                    if br_new > br_old:
                        best_audio = media
                    elif br_new == br_old:
                        pref = {"m4a": 0, "mp4": 1, "webm": 2}
                        rank_new = pref.get((media.get("ext") or "").lower(), 99)
                        rank_old = pref.get((best_audio.get("ext") or "").lower(), 99)
                        if rank_new < rank_old:
                            best_audio = media
        return best_video, best_audio

    @staticmethod
    def _tiktok_douyin_platform(medias: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        best_video, best_audio = None, None
        best_video = medias[0]
        return best_video, best_audio

    @staticmethod
    def _facebook_platform(medias: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        best_video, best_audio = None, None
        best_video = medias[0]
        return best_video, best_audio

    @staticmethod
    def _switch_platform(media: Dict[str, Any], platform: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Dispatch to platform‑specific selection logic.

        TikTok uses the same schema as YouTube, so we reuse the YouTube helper.
        """
        match platform:
            case "youtube":
                return FSMVIDDown._youtube_platform(media)
            case "tiktok":
                # TikTok shares the same media schema as YouTube.
                return FSMVIDDown._youtube_platform(media)
            case "douyin":
                # Placeholder for future Douyin handling.
                return None, None
            case "facebook":
                # Placeholder for future Facebook handling.
                return None, None
            case _:
                # Fallback: simple ranking based on extension.
                ext = (media.get("ext") or "").lower()
                return (media if ext == "mp4" else None), None

    @staticmethod
    def select_best_streams(datas: Dict[str, Any], platform: str) -> Dict[str, Any]:
        """Select the best video and audio from the list of medias.

        - Video: larger height is better; if equal, prefer mp4, then higher bitrate, then higher fps.
        - Audio: higher bitrate is better; if equal, prefer m4a/mp4 over webm.
        """
        best_video: Optional[Dict[str, Any]] = None
        best_audio: Optional[Dict[str, Any]] = None
        medias: List[Dict[str, Any]] = datas.get("medias", []) or []

        video_id = uuid.uuid4().hex
        if platform == "tiktok" or platform == "douyin":
            best_video, best_audio = FSMVIDDown._tiktok_douyin_platform(medias)
            id = datas.get("id") or ""
            if id:
                video_id = id
        if platform == "facebook":
            best_video, best_audio = FSMVIDDown._facebook_platform(medias)
            link = datas.get("url") or ""
            if link.startswith("https://www.facebook.com/reel/"):
                video_id = link.split("https://www.facebook.com/reel/")[-1]
                video_id = video_id.split("/")[0]
                
        if platform == "youtube":
            best_video, best_audio = FSMVIDDown._youtube_platform(medias)

        picked = [x for x in (best_video, best_audio) if x is not None]
        return {
            "status": "success",
            "id": video_id,
            "title": datas.get("title"),
            "url": datas.get("url"),
            "thumbnail": datas.get("thumbnail"),
            "duration": datas.get("duration"),
            "cnt": len(picked),
            "medias": picked,
            "debug": {
                "video_height": FSMVIDDown._parse_height(best_video) if best_video else None,
                "video_bitrate": FSMVIDDown._bitrate(best_video) if best_video else None,
                "video_fps": best_video.get("fps") if best_video else None,
                "audio_bitrate": FSMVIDDown._bitrate(best_audio) if best_audio else None,
            },
        }

if __name__ == "__main__":
    fsmvid = FSMVIDDown()
    result = asyncio.run(
        fsmvid.download(
            "youtube",
            "https://youtube.com/shorts/_UqfmjFaBOQ?si=liRlBjrRBgFKV1uC",
        )
    )
    # result = asyncio.run(
    #     fsmvid.download(
    #         "douyin",
    #         "https://www.douyin.com/video/7545997115172949307",
    #     )
    # )
    print(result)
