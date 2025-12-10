"use client"

import { Search, StopCircle, Settings, Loader2, Link, List } from "lucide-react"

interface Platform {
  id: string
  name: string
  icon: React.ReactNode
  color: string
  ringColor: string
}

const platforms: Platform[] = [
  {
    id: "youtube",
    name: "Youtube",
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
      </svg>
    ),
    color: "bg-red-600/20 text-red-500",
    ringColor: "ring-red-500",
  },
  {
    id: "facebook",
    name: "Facebook",
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
      </svg>
    ),
    color: "bg-blue-600/20 text-blue-500",
    ringColor: "ring-blue-500",
  },
  {
    id: "tiktok",
    name: "TikTok",
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93v6.16c0 3.18-1.32 4.89-3.5 5.35-1.76.24-3.49-.44-4.75-1.6-1.31-1.24-1.81-3.21-1.22-5.04.99-3.09 4.71-4.04 6.27-1.45.13.23.23.49.28.76.04.28.09.57.09.86v-3.8c-2.48-.09-5.21 1.66-5.59 4.54-.36 2.71 1.62 5.25 4.3 5.41 2.8.19 5.34-1.98 5.41-4.73l.03-14.78h-5.4z" />
      </svg>
    ),
    color: "bg-black/40 text-white border border-gray-700",
    ringColor: "ring-gray-500",
  },
  {
    id: "douyin",
    name: "Douyin",
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M17.5 2V8.5C17.5 13.7467 13.2467 18 8 18C2.75329 18 2 13.7467 2 8.5V2H8V8.5C8 10.433 9.567 12 11.5 12C13.433 12 15 10.433 15 8.5V2H17.5Z" fillOpacity="0.8" />
        <path d="M16 2.5C16 2.5 16.5 5 19.5 6.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
    ),
    color: "bg-black/40 text-white border border-pink-500",
    ringColor: "ring-pink-500",
  }
]

interface SidebarProps {
  selectedPlatform: string
  setSelectedPlatform: (platform: string) => void
  channelUrl: string
  setChannelUrl: (url: string) => void
  isLoading: boolean
  onStart: () => void
  onStop: () => void
  activeTab: "channel" | "url"
  urlListText: string
  setUrlListText: (text: string) => void
  onStartFromUrls: () => void
}

export function Sidebar({
  selectedPlatform,
  setSelectedPlatform,
  channelUrl,
  setChannelUrl,
  isLoading,
  onStart,
  onStop,
  activeTab,
  urlListText,
  setUrlListText,
  onStartFromUrls,
}: SidebarProps) {
  if (activeTab === "url") {
    return (
      <div className="w-80 flex flex-col gap-4 h-full animate-slide-in">
        <div className="bg-white/5 backdrop-blur-md border border-white/10 rounded-xl p-4 flex-1 flex flex-col min-h-0 shadow-xl">
          <div className="flex items-center gap-2 mb-4 shrink-0">
            <List className="w-5 h-5 text-cyan-400" />
            <span className="font-medium bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">Danh sách URL</span>
          </div>

          <div className="flex-1 flex flex-col min-h-0 px-1">
            <p className="text-xs text-gray-400 mb-2 shrink-0">Nhập danh sách URL video (mỗi URL một dòng):</p>
            <textarea
              value={urlListText}
              onChange={(e) => setUrlListText(e.target.value)}
              placeholder={`https://www.tiktok.com/@user/video/1\nhttps://www.tiktok.com/@user/video/2\n...`}
              className="flex-1 bg-black/20 border border-white/10 rounded-lg px-3 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-cyan-500/50 transition-all duration-300 resize-none custom-scrollbar min-h-0 hover:bg-black/30"
            />

            <div className="mt-3 text-xs text-gray-500 shrink-0">
              <div className="flex items-center gap-1">
                <Link className="w-3 h-3" />
                <span>Số URL: {urlListText.split("\n").filter((url) => url.trim()).length}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="bg-white/5 backdrop-blur-md border border-white/10 rounded-xl p-4 shrink-0 shadow-lg">
          <div className="space-y-3">
            <button
              onClick={onStartFromUrls}
              disabled={isLoading || !urlListText.trim()}
              className="cursor-pointer w-full relative overflow-hidden group flex items-center justify-center gap-2 bg-gradient-to-r from-cyan-600 to-blue-600 disabled:from-gray-700 disabled:to-gray-800 text-white px-4 py-3 rounded-lg transition-all duration-300 hover:shadow-lg hover:shadow-cyan-500/20 active:scale-95 disabled:active:scale-100"
            >
              <div className="absolute inset-0 bg-white/20 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm font-medium">Đang xử lý URL...</span>
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  <span className="text-sm font-medium">Lấy danh sách video</span>
                </>
              )}
            </button>
            <button
              onClick={onStop}
              disabled={true}//{!isLoading}
              className="cursor-pointer w-full flex items-center justify-center gap-2 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 px-4 py-3 rounded-lg transition-all duration-300 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100 disabled:hover:bg-red-500/10"
            >
              <StopCircle className="w-4 h-4" />
              <span className="text-sm font-medium">Dừng get video</span>
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="w-80 flex flex-col gap-4 h-full animate-slide-in">
      {/* Settings Card */}
      <div className="bg-white/5 backdrop-blur-md border border-white/10 rounded-xl p-4 flex-1 flex flex-col min-h-0 shadow-xl">
        <div className="flex items-center gap-2 mb-4 shrink-0 px-1">
          <Settings className="w-5 h-5 text-cyan-400" />
          <span className="font-medium bg-gradient-to-r from-white to-gray-400 bg-clip-text ">Cài đặt</span>
        </div>

        <div className="flex-1 overflow-y-auto px-1 custom-scrollbar min-h-0 -mr-2 pr-2">
          <div className="grid grid-cols-2 gap-3 pb-2">
            {platforms.map((platform, index) => (
              <button
                key={platform.id}
                onClick={() => setSelectedPlatform(platform.id)}
                style={{ animationDelay: `${index * 50}ms` }}
                className={`group relative flex flex-col items-center gap-2 p-3 rounded-xl transition-all duration-300 transform hover:scale-[1.02] animate-fade-in border ${selectedPlatform === platform.id
                  ? `bg-[#3a3a5a]/80 ${platform.ringColor} border-${platform.ringColor.split('-')[1]}-500/50 shadow-lg`
                  : "bg-black/20 border-white/5 hover:bg-white/10"
                  }`}
              >
                <div
                  className={`w-10 h-10 ${platform.color} rounded-xl flex items-center justify-center transition-transform duration-300 group-hover:scale-110 shadow-inner`}
                >
                  {platform.icon}
                </div>
                <span className={`text-[10px] uppercase tracking-wider font-semibold ${selectedPlatform === platform.id ? "text-white" : "text-gray-400 group-hover:text-gray-200"}`}>{platform.name}</span>

                {selectedPlatform === platform.id && (
                  <div className="absolute inset-0 border-2 border-inherit rounded-xl opacity-50 animate-pulse" />
                )}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Channel Input */}
      <div className="bg-white/5 backdrop-blur-md border border-white/10 rounded-xl p-4 shrink-0 shadow-lg">
        <p className="text-xs font-medium text-gray-400 mb-2 uppercase tracking-wide">Danh sách kênh / page: (1)</p>
        <div className="relative group">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Link className="h-4 w-4 text-gray-500 group-focus-within:text-cyan-400 transition-colors" />
          </div>
          <input
            type="text"
            value={channelUrl}
            onChange={(e) => setChannelUrl(e.target.value)}
            className="w-full bg-black/20 border border-white/10 rounded-lg pl-9 pr-3 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all duration-300 group-hover:bg-black/30"
            placeholder="Nhập URL kênh..."
          />
        </div>

        {/* Action Buttons */}
        <div className="mt-4 space-y-3">
          <button
            onClick={onStart}
            disabled={isLoading}
            className="cursor-pointer w-full relative overflow-hidden group flex items-center justify-center gap-2 bg-gradient-to-r from-cyan-600 to-blue-600 disabled:from-gray-700 disabled:to-gray-800 text-white px-4 py-3 rounded-lg transition-all duration-300 hover:shadow-lg hover:shadow-cyan-500/20 active:scale-95 disabled:active:scale-100"
          >
            <div className="absolute inset-0 bg-white/20 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm font-medium">Đang lấy dữ liệu...</span>
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                <span className="text-sm font-medium">Lấy danh sách video</span>
              </>
            )}
          </button>
          <button
            onClick={onStop}
            disabled={true}//{!isLoading}
            className="cursor-pointer w-full flex items-center justify-center gap-2 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 px-4 py-3 rounded-lg transition-all duration-300 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100 disabled:hover:bg-red-500/10"
          >
            <StopCircle className="w-4 h-4" />
            <span className="text-sm font-medium">Dừng get video</span>
          </button>
        </div>
      </div>
    </div>
  )
}
