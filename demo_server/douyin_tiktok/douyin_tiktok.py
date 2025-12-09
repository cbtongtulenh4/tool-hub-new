import asyncio
import os 
import time
from urllib.parse import urlencode, quote
import sys
from douyin_tiktok.douyin.abogus import ABogus as AB
from douyin_tiktok.base_crawler import BaseCrawler
from douyin_tiktok.douyin.xbogus import XBogus as XB

class BogusManager:
    @classmethod
    def xb_str_2_endpoint(cls, endpoint: str, user_agent: str) -> str:
        try:
            final_endpoint = XB(user_agent).getXBogus(endpoint)
        except Exception as e:
            raise RuntimeError("生成X-Bogus失败: {0})".format(e))

        return final_endpoint[0]

    @classmethod
    def xb_model_2_endpoint(cls, base_endpoint: str, params: dict, user_agent: str) -> str:
        if not isinstance(params, dict):
            raise TypeError("参数必须是字典类型")

        param_str = "&".join([f"{k}={v}" for k, v in params.items()])

        try:
            xb_value = XB(user_agent).getXBogus(param_str)
        except Exception as e:
            raise RuntimeError("生成X-Bogus失败: {0})".format(e))

        separator = "&" if "?" in base_endpoint else "?"

        final_endpoint = f"{base_endpoint}{separator}{param_str}&X-Bogus={xb_value[1]}"

        return final_endpoint

    @classmethod
    def ab_model_2_endpoint(cls, params: dict, user_agent: str) -> str:
        if not isinstance(params, dict):
            raise TypeError("参数必须是字典类型")

        try:
            ab_value = AB().get_value(params, )
        except Exception as e:
            raise RuntimeError("生成A-Bogus失败: {0})".format(e))

        return quote(ab_value, safe='')


    @classmethod
    def model_2_endpoint(
            cls,
            base_endpoint: str,
            params: dict,
            user_agent: str,
    ) -> str:
        if not isinstance(params, dict):
            raise TypeError("参数必须是字典类型")

        param_str = "&".join([f"{k}={v}" for k, v in params.items()])

        try:
            xb_value = XB(user_agent).getXBogus(param_str)
        except Exception as e:
            raise RuntimeError("生成X-Bogus失败: {0})".format(e))

        separator = "&" if "?" in base_endpoint else "?"

        final_endpoint = f"{base_endpoint}{separator}{param_str}&X-Bogus={xb_value[1]}"

        return final_endpoint



class DouyinTiktokScraper:
    def __init__(self, douyin_cookie: str, tiktok_cookie: str):
        self.douyin_cookie = douyin_cookie
        self.tiktok_cookie = tiktok_cookie
        pass


    async def fetch_post_videos_by_username(self, url: str) -> dict:

        if "douyin.com" in url:
            return await self.fetch_post_videos_by_username_douyin(url)
        elif "tiktok.com" in url:
            return await self.fetch_post_videos_by_username_tiktok(url)
        else:
            return {
                "url": url,
                "status": "error",
            "message": "not support this platform"
        }

    async def fetch_post_videos_by_username(self, url: str) -> dict:
        if "tiktok.com" in url:
            return await self.fetch_post_videos_by_username_tiktok(url)
        elif "douyin.com" in url:
            return await self.fetch_post_videos_by_username_douyin(url)
        else:
            return {
                "url": url,
                "status": "error",
                "message": "not support this platform"
            }


    async def douyin_fetch_user_post_videos(self, sec_user_id: str, max_cursor: int, count: int=50):
        items = []
        while True:
            print("max_cursor", max_cursor)
            kwargs = {'headers': {'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36', 'Referer': 'https://www.douyin.com/', 'Cookie': self.douyin_cookie}, 'proxies': {'http://': None, 'https://': None}}
            params_dict = {'device_platform': 'webapp', 'aid': '6383', 'channel': 'channel_pc_web', 'pc_client_type': 1, 'version_code': '290100', 'version_name': '29.1.0', 'cookie_enabled': 'true', 'screen_width': 1920, 'screen_height': 1080, 'browser_language': 'zh-CN', 'browser_platform': 'Win32', 'browser_name': 'Chrome', 'browser_version': '130.0.0.0', 'browser_online': 'true', 'engine_name': 'Blink', 'engine_version': '130.0.0.0', 'os_name': 'Windows', 'os_version': '10', 'cpu_core_num': 12, 'device_memory': 8, 'platform': 'PC', 'downlink': '10', 'effective_type': '4g', 'from_user_page': '1', 'locate_query': 'false', 'need_time_list': '1', 'pc_libra_divert': 'Windows', 'publish_video_strategy_type': '2', 'round_trip_time': '0', 'show_live_replay_strategy': '1', 'time_list_query': '0', 'whale_cut_token': '', 'update_version_code': '170400', 'msToken': '', 'max_cursor': max_cursor, 'count': count, 'sec_user_id': sec_user_id}
            params_dict["msToken"] = ''
            a_bogus = BogusManager.ab_model_2_endpoint(params_dict, kwargs["headers"]["User-Agent"])
            base_crawler = BaseCrawler(proxies=kwargs["proxies"], crawler_headers=kwargs["headers"])
            async with base_crawler as crawler:
                endpoint = f"https://www.douyin.com/aweme/v1/web/aweme/post/?{urlencode(params_dict)}&a_bogus={a_bogus}"
                response = await crawler.fetch_get_json(endpoint)
            for item in response.get("aweme_list", []):
                url = "https://douyin.com/video/" + item.get("aweme_id")
                title = item.get("desc") or item.get("caption") or item.get("item_title") or ""
                stats = item.get("statistics", {})
                view = stats.get("play_count", 0)
                like = stats.get("digg_count", 0)
                comment = stats.get("comment_count", 0)
                share = stats.get("share_count", 0)
                items.append({
                    "url": url,
                    "title": title,
                    "view": view,
                    "like": like,
                    "comment": comment,
                    "share": share
                })
            max_cursor = response.get("max_cursor", 0)
            has_more = response.get("has_more", 0)
            print("has_more", has_more)
            if has_more == 0:
                break
        print(items)
        return items


    async def tiktok_fetch_user_post(self, secUid: str, cursor: int = 0, count: int = 35, coverFormat: int = 2):
        kwargs = {'headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36', 'Referer': 'https://www.tiktok.com/', 'Cookie': self.tiktok_cookie}, 'proxies': {'http://': None, 'https://': None}}
        base_crawler = BaseCrawler(proxies=kwargs["proxies"], crawler_headers=kwargs["headers"])
        async with base_crawler as crawler:
            params_dict = {'WebIdLastTime': '1714385892', 'aid': '1988', 'app_language': 'zh-Hans', 'app_name': 'tiktok_web', 'browser_language': 'zh-CN', 'browser_name': 'Mozilla', 'browser_online': 'true', 'browser_platform': 'Win32', 'browser_version': '5.0%20%28Windows%29', 'channel': 'tiktok_web', 'cookie_enabled': 'true', 'count': count, 'coverFormat': coverFormat, 'cursor': cursor, 'data_collection_enabled': 'true', 'device_id': '7380187414842836523', 'device_platform': 'web_pc', 'focus_state': 'true', 'from_page': 'user', 'history_len': '3', 'is_fullscreen': 'false', 'is_page_visible': 'true', 'language': 'zh-Hans', 'locate_item_id': '', 'needPinnedItemIds': 'true', 'odinId': '7404669909585003563', 'os': 'windows', 'post_item_list_request_type': 0, 'priority_region': 'US', 'referer': '', 'region': 'US', 'screen_height': '827', 'screen_width': '1323', 'secUid': secUid, 'tz_name': 'America%2FLos_Angeles', 'user_is_login': 'true', 'webcast_language': 'zh-Hans', 'msToken': 'cj9fOAKkW5d4yMtaIR3if2fg1JiKRIMjUYMK0Ab7haGsKYEGRTETxSTXxq6NoMGGwm4NtXZPl2Z2qx-MYkzxbwpM5dhNsxykdHpGULXoypwDonY1J5ohYk_9xrS0w6-LUloN9FcMELM4FdAlb05l05U='}

            endpoint = BogusManager.model_2_endpoint(
                "https://www.tiktok.com/api/post/item_list/", params_dict, kwargs["headers"]["User-Agent"]
            )
            endpoint = "https://www.tiktok.com/api/post/item_list/?WebIdLastTime=1763074143&aid=1988&app_language=en&app_name=tiktok_web&browser_language=en-US&browser_name=Mozilla&browser_online=true&browser_platform=Win32&browser_version=5.0 (Windows)&channel=tiktok_web&clientABVersions=70508271,72437276,73720540,74444736,74446914,74534793,74757744,74780476,74782563,74852656,74860161,74864882,74879364,74879782,74891664,74902368,74907603,74926160,74930475,74936936,74961020,74970061,74970253,74973673,74976256,74983391,74983765,74983937,74987203,74998869,75001422,75005876,75014049,75026334,75036735,75041556,75045552,75045921,75048552,75069884,75077940,75083492,70138197,70156809,70405643,71057832,71200802,71381811,71516509,71803300,71962127,72360691,72408100,72854054,72892778,73004916,73171280,73208420,73952802,73952825,73989921,74276218,74844724&cookie_enabled=true&count=16&coverFormat=0&cursor=0&data_collection_enabled=true&device_id=7572345762350155282&device_platform=web_pc&enable_cache=false&focus_state=true&from_page=user&history_len=4&is_fullscreen=false&is_page_visible=true&language=en&locate_item_id=7570179644301888784&needPinnedItemIds=true&odinId=7440878950417794103&os=windows&post_item_list_request_type=0&priority_region=VN&referer=https://www.tiktok.com/&region=VN&root_referer=https://www.tiktok.com/&screen_height=990&screen_width=1760&secUid=MS4wLjABAAAAHq-fqkM0APO8oDXRDhBOJJKEUHCrW-HegMuYG3QYOkdHVhJi1u2OQlVMTZSKtxOE&tz_name=Asia/Bangkok&user_is_login=true&verifyFp=verify_mivtr9og_YibNzABY_GRvO_4fc3_Bjzz_QjE05qSbMGt1&video_encoding=mp4&webcast_language=en&msToken=cj9fOAKkW5d4yMtaIR3if2fg1JiKRIMjUYMK0Ab7haGsKYEGRTETxSTXxq6NoMGGwm4NtXZPl2Z2qx-MYkzxbwpM5dhNsxykdHpGULXoypwDonY1J5ohYk_9xrS0w6-LUloN9FcMELM4FdAlb05l05U=&X-Bogus=DFSzsIVutrUANj4OCYh6FDrO8J0x&X-Gnarly=MwdQIuVyI9TFcB4b5/uLOx/rnkUl5JdorFrqSeAQHMlj7CuKsC0lgh3A6aOFFvJ0b/4wpbR3apv5ZDruFqCErDe6PPptjBoOxCe3LI2liX-LsUlz7S5kqGe3d9tyAgFisMh2sJWdSbu8OtfoeUY5R/RoQl/tfsy1ddPJSXsed-btAxoQF5jpZH2A8rdOz5ZP4aUwJ4PGr14YM2A-aHEAfvAZvoi72A0L3wndWtD0F4kt4PbKF0fSBWmIc1Fye3ROh0xn4NObZl7i/slY2pWuD6VnLdceCYel0b-QuVuhzGzecj5pYf/mjqz62NqT1qT/dBb="
            response = await crawler.fetch_get_json(endpoint)
        return response



if __name__ == "__main__":
    scraper = DouyinTiktokScraper(
        douyin_cookie="ttwid=1%7CBD3GjtVoizObrVlBxAjnS7sw4iCYET8Lz1fvFRBcb9s%7C1765099018%7C95911db5fe6d88cce9fe58f586b9661d9b49ef041146760b0b429fa65f17d6ec; enter_pc_once=1; UIFID_TEMP=47253ff694b1a3f0276ef6188afc260853569160d1a9e22d73502760654854795f67336c30a5aae0d9f9a5b736035302ccbfc714f928c82e905e34a16ee3f93c8073d4df545db26c9c24e738aab9e4c9; hevc_supported=true; xgplayer_user_id=579737460722; fpk1=U2FsdGVkX1+iy1hukcoNKPtmFQaulDXO5OBUUU5d2bXfv6UTj6ScmMPReVi35gq0E6CZk7YpE/oh7gu0yHG5Sg==; fpk2=bfe921b394bf10c8d08c5999edfccc8d; bd_ticket_guard_client_web_domain=2; bd_ticket_guard_client_data_v2=eyJyZWVfcHVibGljX2tleSI6IkJNNktiK2dYeFVNd0ZnS241T0x0WDd3Y0RQUzMxM3FhWDJnZE5iUzE1aUYwQUxaKzIwZWlrRDF4S3NaWVIwWW11S0NrUk1VU0hjSUFpTzdzSjhVckthYz0iLCJ0c19zaWduIjoidHMuMi4zYmU4ZTEyODY2ZDk4YmUyMTFlMjA0YjNjYjRlNTZiNGJkNTcxZGRjYjBkNGQwMWJhMGQ3ZjJhNjZiMmFjZDNkYzRmYmU4N2QyMzE5Y2YwNTMxODYyNGNlZGExNDkxMWNhNDA2ZGVkYmViZWRkYjJlMzBmY2U4ZDRmYTAyNTc1ZCIsInJlcV9jb250ZW50Ijoic2VjX3RzIiwicmVxX3NpZ24iOiJOUkE4QUl4Z1VWVStVYTEramgzRjFCZDQxYXF0SGdvaE9aSjRwZ2xXWmZFPSIsInNlY190cyI6IiNKdkxKbDVZUUt3a0twUnhZMGZqYUxVM1ZpZno1NGlTSEVvTnNTbk1EeHJaVEJIYjQ2MGJaQU5lQU5ZblMifQ%3D%3D; odin_tt=c7fffa135a0bcb84e7c1b799548dc538ffe2246fb6cca1ac434740885c1e282236bfa726561fc60bbfedc961f0188694b7afa80b6620cde73f8371a5fa5b28ce; UIFID=47253ff694b1a3f0276ef6188afc260853569160d1a9e22d735027606548547974ba1127f039352ad446e71a171a006b21c539738d2a3709b3b9723b06104ed0bdf417c279822f556089112aa631f76a7632dc748fc624b4f55e9a67d308865f0a85c5d0324db726dda27479b40b790e4b5711316ab73bcb910b5460cfdc6b2e62cb296eca3f738248662417e389e671e17f9fd3faee6758a00d5e57d69eb746; IsDouyinActive=true; home_can_add_dy_2_desktop=%220%22; dy_swidth=1920; dy_sheight=1080; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A1920%2C%5C%22screen_height%5C%22%3A1080%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A16%2C%5C%22device_memory%5C%22%3A0%2C%5C%22downlink%5C%22%3A%5C%22%5C%22%2C%5C%22effective_type%5C%22%3A%5C%22%5C%22%2C%5C%22round_trip_time%5C%22%3A0%7D%22; strategyABtestKey=%221765099012.711%22; s_v_web_id=verify_miqbhvc2_Lhxa2v2g_Kqe2_43SZ_90a4_RWMbrdkSQjeJ; is_dash_user=1; passport_csrf_token=660815ecff8b7c91e613a68307e9718b; passport_csrf_token_default=660815ecff8b7c91e613a68307e9718b; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Atrue%2C%22volume%22%3A0.6%7D; __security_mc_1_s_sdk_crypt_sdk=8b8b24d8-47bb-9077; stream_player_status_params=%22%7B%5C%22is_auto_play%5C%22%3A0%2C%5C%22is_full_screen%5C%22%3A0%2C%5C%22is_full_webscreen%5C%22%3A1%2C%5C%22is_mute%5C%22%3A1%2C%5C%22is_speed%5C%22%3A1%2C%5C%22is_visible%5C%22%3A0%7D%22; download_guide=%223%2F20251204%2F0%22; passport_mfa_token=CjafkCFrvWfl2eRWAsHEsft666gjDyorY0gTGwqOCt3dUrHI6%2BOpOSm3BogZfBU1GUAfauLwROQaSgo8AAAAAAAAAAAAAE%2FKv4fk7D884Id%2FXHU5oDF%2B3RJImLOAr0xFXXHDUkorS%2BwS3yLMu8ZvFpUV12nbZSw1EPOmgw4Y9rHRbCACIgEDTyS9Ag%3D%3D; d_ticket=a5e10219eb2a9ec9f3e8817cab8a3ff42be43; passport_assist_user=CkDkVuuz2G13H3cfC4ro1r7cghW9eeH3c6M3Y_WfY5eEkhFd4_3_eKGlbbb7PVs7_gvbrbCjyspJ7Tol6EoMOPAZGkoKPAAAAAAAAAAAAABPypXRi27gDOEqS3wa75CIOEGN5mUCRmJaVG8B-BpI234Gg1t6aKHB0zCrdcPlwhhkbRDcpYMOGImv1lQgASIBAx0y3bU%3D; n_mh=hUgTZD6li-owxWv0c9ucMJOYC9hjLhbRWR6AsBtoJb4; passport_auth_status=3749f688e926568ddbcd8f7d0d720d99%2C; passport_auth_status_ss=3749f688e926568ddbcd8f7d0d720d99%2C; sid_guard=3f44b6fbcf985a339fe3d39a1eaa7c19%7C1764864200%7C5184000%7CMon%2C+02-Feb-2026+16%3A03%3A20+GMT; uid_tt=a314143430a5288f866168d2f63c74b6; uid_tt_ss=a314143430a5288f866168d2f63c74b6; sid_tt=3f44b6fbcf985a339fe3d39a1eaa7c19; sessionid=3f44b6fbcf985a339fe3d39a1eaa7c19; sessionid_ss=3f44b6fbcf985a339fe3d39a1eaa7c19; session_tlb_tag=sttt%7C16%7CP0S2-8-YWjOf49OaHqp8Gf________-_ksP5DZn1K48-Wgua85vJaBYKUrMUnObA0iED3-Uq9sY%3D; session_tlb_tag_bk=sttt%7C16%7CP0S2-8-YWjOf49OaHqp8Gf________-_ksP5DZn1K48-Wgua85vJaBYKUrMUnObA0iED3-Uq9sY%3D; is_staff_user=false; sid_ucp_v1=1.0.0-KGMwNzBkZGRhOTk1NmQ5YTEyNzczY2MzODQ5NGNhMjFlOGI2NWVjYjIKIAjN0vCfvfUmEMjhxskGGO8xIAww___07QU4AkDxB0gEGgJscSIgM2Y0NGI2ZmJjZjk4NWEzMzlmZTNkMzlhMWVhYTdjMTk; ssid_ucp_v1=1.0.0-KGMwNzBkZGRhOTk1NmQ5YTEyNzczY2MzODQ5NGNhMjFlOGI2NWVjYjIKIAjN0vCfvfUmEMjhxskGGO8xIAww___07QU4AkDxB0gEGgJscSIgM2Y0NGI2ZmJjZjk4NWEzMzlmZTNkMzlhMWVhYTdjMTk; _bd_ticket_crypt_doamin=2; _bd_ticket_crypt_cookie=0577c5d260e5f6cc4a9b0bbb0cfce88c; __security_mc_1_s_sdk_sign_data_key_web_protect=c59d922a-45ce-9ea0; __security_mc_1_s_sdk_cert_key=aee3377c-4335-b639; __security_server_data_status=1; login_time=1764864201130; SelfTabRedDotControl=%5B%5D; FOLLOW_LIVE_POINT_INFO=%22MS4wLjABAAAAG30iru_BqzP12E8vXgcnbBoge2KOBtANJKJzUgF8YEg%2F1765126800000%2F0%2F0%2F1765099674325%22; publish_badge_show_info=%220%2C0%2C0%2C1764864228506%22; FOLLOW_NUMBER_YELLOW_POINT_INFO=%22MS4wLjABAAAAG30iru_BqzP12E8vXgcnbBoge2KOBtANJKJzUgF8YEg%2F1765126800000%2F0%2F1765099074326%2F0%22; WallpaperGuide=%7B%22showTime%22%3A1764888586759%2C%22closeTime%22%3A0%2C%22showCount%22%3A1%2C%22cursor1%22%3A14%2C%22cursor2%22%3A4%2C%22hoverTime%22%3A1764982206395%7D; __ac_nonce=0693545f10082f703a313; __ac_signature=_02B4Z6wo00f012WDvkAAAIDAIFjQ.JEnpdtlsrrAALBgp0n8lAgcQ0kqAj7BjEOzqzrpiYqL.MtNZyvWS.u3bzaPwbzt7dkqyMG1.al49--ws9iC-O51nyO0AigFxUEZyjIWiZwHLaOJ5ksebc; douyin.com; xg_device_score=7.43799004027265; device_web_cpu_core=16; device_web_memory_size=-1; architecture=amd64; biz_trace_id=c8a2597a; sdk_source_info=7e276470716a68645a606960273f276364697660272927676c715a6d6069756077273f276364697660272927666d776a68605a607d71606b766c6a6b5a7666776c7571273f275e58272927666a6b766a69605a696c6061273f27636469766027292762696a6764695a7364776c6467696076273f275e582729277672715a646971273f2763646976602729277f6b5a666475273f2763646976602729276d6a6e5a6b6a716c273f2763646976602729276c6b6f5a7f6367273f27636469766027292771273f273731323237353c3c3530333234272927676c715a75776a716a666a69273f2763646976602778; bit_env=5M0fJ5rH_UqjctpWA5inZRnxCwojrNKP5Z99PVmNnnFTe3qgK61vMIS5SUN0U8MtorcSxenMS97glf_Pj15BpfKfksiCBvttOwHr6QyUPTpVl7px5QkqGVX2EaPmCbJ9w-UgBviT07sRSUmIaLsdBt5wK1T0584zxObyRLhiAYUcHvwMg6GNRixxmlnz92houJ-tlrBQTNgGIT9urgM7vbJxEi509o6261v2e9Hr-646LfRfe0gScfXs-yumuMWX7lVT8toBO4gYrHwPGL--F4WFygETGQ6oHCT-9VJEIu8fGTmzEKsoZREeipedPsfO0wHXqpwQ1BIK0jtbTajmVljb01xRsJdWYt5aKCBEb1MLg7srZHXk9pmZW_3IdoLn7U_5IKZHDFeyQidDIbV33rN1jg6TTSBcP5q3Fz5p8zaIbxz3lXBhym0d0xNC1t_9vYMc9ZvNRptpvI_WNDWmHw%3D%3D; gulu_source_res=eyJwX2luIjoiNWI1Zjg1NGQzZDdiYzUzOGJiZTk0MDQ0NTcwYzkzNjA3YjI0MGVjYmZmODE4ZGY1ZWRmZWIxMmQwY2U2Yzg4MSJ9; passport_auth_mix_state=ypg0hmbjjtjpt8krp9p8cbupk0k5l22q; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCTTZLYitnWHhVTXdGZ0tuNU9MdFg3d2NEUFMzMTNxYVgyZ2ROYlMxNWlGMEFMWisyMGVpa0QxeEtzWllSMFltdUtDa1JNVVNIY0lBaU83c0o4VXJLYWM9IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoyfQ%3D%3D",
        tiktok_cookie="ttwid=1%7CkO5yilXeGaNWdFUd9vniAYyowHOs1hnLOFMM98nU3oE%7C1765118143%7C48237e937dbb6681b31003f29bf733d2f0cb8cbf9177320e9c4bcbdbe644acea; tt_chain_token=4CqUZ4QcMUs9Qsa0B8AqWw==; tiktok_webapp_theme_source=auto; tiktok_webapp_theme=dark; msToken=FuTnwlyt0j3jPWErZfLSf12y4fp98aw0FrXvxGOWX1DcNWge6mYJGZWp4aJGwszamk19UAs-kuBqd-5BdsR94y4twvrEQKVjmVUOEzsgKGr_1A07MpapENr0J6886-29umSsABQVTP3XhcgujJUlQv8=; odin_tt=f8bf6f24c0e8a8f71e8814f6aa4af33addef3bc5944615835be9e0261799149a27057a94dd608d88d71ddbc3ecd3e6779129022e463ac438caf1af2f44605ea190bb193e492d4d0beb100c9cd238b960; passport_csrf_token=925357f378a22b9194b9a186e4d768ec; passport_csrf_token_default=925357f378a22b9194b9a186e4d768ec; delay_guest_mode_vid=5; tt_csrf_token=bFtcJt0m-J2JzQyez29lWbxfbxq3I9jQB52U; s_v_web_id=verify_mivtr9og_YibNzABY_GRvO_4fc3_Bjzz_QjE05qSbMGt1; multi_sids=7440878950417794103%3A060ade417db635170c34b0c2cced01e1; cmpl_token=AgQYAPOF_hfkTtK3faFc6GddDvN3-Wp-z_-QDmCjfH8; sid_guard=060ade417db635170c34b0c2cced01e1%7C1765118136%7C15552000%7CFri%2C+05-Jun-2026+14%3A35%3A36+GMT; uid_tt=9c20af74aac806a2b58aca04ec9051c5d0e8ce1c54bd25c0e4805ca972895167; uid_tt_ss=9c20af74aac806a2b58aca04ec9051c5d0e8ce1c54bd25c0e4805ca972895167; sid_tt=060ade417db635170c34b0c2cced01e1; sessionid=060ade417db635170c34b0c2cced01e1; sessionid_ss=060ade417db635170c34b0c2cced01e1; tt_session_tlb_tag=sttt%7C5%7CBgreQX22NRcMNLDCzO0B4f_________CM7VtH8TXBhsswwqSIfAZq4KBKNu1yEOkPmjYoixMWaA%3D; sid_ucp_v1=1.0.1-KGJhNGIwMjIzY2M5MTNiZTk0OThjOWQ0MWVhM2U0NGFkYmNiM2ZlZTUKIgi3iNaCtv_ToWcQuKHWyQYYswsgDDCgoI26BjgHQPQHSAQQAxoGbWFsaXZhIiAwNjBhZGU0MTdkYjYzNTE3MGMzNGIwYzJjY2VkMDFlMTJOCiCEf8NwuuOZ9YKKxuHWCa4pDgHHEBgDHKeLjwWVs73nKRIgdv9-OeVuXnTCzPZh_fB0NHhOhCRyOhbTd_819SZ0s4YYAiIGdGlrdG9r; ssid_ucp_v1=1.0.1-KGJhNGIwMjIzY2M5MTNiZTk0OThjOWQ0MWVhM2U0NGFkYmNiM2ZlZTUKIgi3iNaCtv_ToWcQuKHWyQYYswsgDDCgoI26BjgHQPQHSAQQAxoGbWFsaXZhIiAwNjBhZGU0MTdkYjYzNTE3MGMzNGIwYzJjY2VkMDFlMTJOCiCEf8NwuuOZ9YKKxuHWCa4pDgHHEBgDHKeLjwWVs73nKRIgdv9-OeVuXnTCzPZh_fB0NHhOhCRyOhbTd_819SZ0s4YYAiIGdGlrdG9r; store-idc=alisg; store-country-sign=MEIEDF06NFTWTvv4EgpaLAQgFDVG_5OSU7-6iuylH2Y6cwRXbVzsZU4i0ACaW8kDyfMEEJpsNweLnAZK-1Jb6gETR_U; store-country-code=vn; store-country-code-src=uid; tt-target-idc=alisg; tt-target-idc-sign=Oh_RqMtekTzoeohZYKd_WcBb7lUp8AASX98scnMMCLxcr4P4_kFHq6XNbWaT0FRCPiWyMGJO2au0laGs0m_-0eCtFFbIlbE1OSy4bUClHSYF5bON4KmnMk8hsVIigX2Ci4CkC2CpJC8brzA0-72aAN8AO8i8rajzDaS4MYDd-BEV235R551nYtG6kf4fN6PCCoWbyivFQD8MgaF7qt9Vwd162iuUaj91mCYtdZWSlSigleqo3KItsokMZOPTFxPt5MnkJBW7LT-ddmwLFxeGIzX2R021Q9CwSIkg_HA8mGfImk2wv9plsxBq5Zl_u3PgHSwRAyjzVLg951APkITX7o9bKAwwlvnhe3f1i1T3peXQ1hIDsYMXZzBBmvxcK5OVd0o_syfo7h_iZFQsKqm9HzMZ7b90s5gttfZEZanasBhKniyMPp0jCf7VMctF9bBEBJASvbz8cj0NltT9QF5SDIctiQv_hPA9fuyri3cYRgFXFzsxLZjIjaDZ5-7uiWSI; last_login_method=QRcode; passport_fe_beating_status=true; perf_feed_cache={%22expireTimestamp%22:1765288800000%2C%22itemIds%22:[%227580215398243552542%22%2C%227566645514549153045%22%2C%227577963420746648853%22]}; msToken=2_FfizMOPLM3Vh3eXBIQtOAcveWoHo7y7rgBQzjCaXtQGmODl2zEG--BFF5Zxdo8FeGxH7_0EzGn_LI2WdiNItfSDqVw5wNRCN1B1z0RPgUfp7NQ0qzP955gfEg-L5kX263UpoJ9VDAFOYou-Y8HEbY="
    )
    asyncio.run(scraper.douyin_fetch_user_post_videos(sec_user_id="MS4wLjABAAAAtGiTBx3XQ2ZwMmMB4uvKsEEtf0XvLvJty_Po0yOKgK0", max_cursor=0, count=50))  
    # asyncio.run(scraper.tiktok_fetch_user_post(secUid="MS4wLjABAAAAQVGqi8nNZgWX8kTRRgEijcZBaRBNcqNuPxToy_mJXniYK97Kpdk0rdeP3JUV0F8q", cursor=0, count=10))    

