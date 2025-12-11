"use client"

import { useEffect, useRef, useState, useMemo } from "react"
import { CheckSquare, Loader2, Filter, X, Eye, Heart, MessageCircle, Share2, Search } from "lucide-react"

interface VideoItem {
  id: number
  url: string
  caption: string
  comments: number
  likes: string
  collects: string
  shares: number
  status: string
}

interface VideoResultsProps {
  videos: VideoItem[]
  selectedVideos: number[]
  setSelectedVideos: (videos: number[]) => void
  isLoading: boolean
  isDataFetched: boolean
  isDownloading: boolean
  currentDownloadingIds: number[]
  downloadedCount: number
  totalDownloadCount: number
}

// Helper to parse metric strings like "1.2K", "1M" or numbers to raw numbers
const parseMetric = (value: string | number): number => {
  if (typeof value === 'number') return value
  if (!value) return 0

  const clean = value.toString().replace(/,/g, '').toUpperCase()
  const multiplier = clean.endsWith('K') ? 1000 :
    clean.endsWith('M') ? 1000000 :
      clean.endsWith('B') ? 1000000000 : 1

  const num = parseFloat(clean)
  return isNaN(num) ? 0 : num * multiplier
}

export function VideoResults({
  videos,
  selectedVideos,
  setSelectedVideos,
  isLoading,
  isDataFetched,
  isDownloading,
  currentDownloadingIds,
  downloadedCount,
  totalDownloadCount,
}: VideoResultsProps) {
  const tableRef = useRef<HTMLDivElement>(null)
  const rowRefs = useRef<{ [key: number]: HTMLTableRowElement | null }>({})
  const [showFilter, setShowFilter] = useState(false)
  const [filters, setFilters] = useState({
    collects: "",
    likes: "",
    comments: "",
    shares: "",
  })
  const isVideoError = (status: string) => { return status?.includes("Error") || status?.includes("Failed"); }

  // Filter logic
  const filteredVideos = useMemo(() => {
    return videos.filter(video => {
      const collects = parseMetric(video.collects)
      const likes = parseMetric(video.likes)
      const comments = parseMetric(video.comments)
      const shares = parseMetric(video.shares)

      const minCollects = filters.collects ? parseMetric(filters.collects) : 0
      const minLikes = filters.likes ? parseMetric(filters.likes) : 0
      const minComments = filters.comments ? parseMetric(filters.comments) : 0
      const minShares = filters.shares ? parseMetric(filters.shares) : 0

      return (
        collects >= minCollects &&
        likes >= minLikes &&
        comments >= minComments &&
        shares >= minShares
      )
    })
  }, [videos, filters])

  // Auto-scroll to latest video when new data arrives
  useEffect(() => {
    if (!isLoading && videos.length > 0) {
      const lastVideoId = videos[videos.length - 1].id
      const lastRow = rowRefs.current[lastVideoId]
      if (lastRow && tableRef.current) {
        lastRow.scrollIntoView({
          behavior: "smooth",
          block: "end",
        })
      }
    }
  }, [videos.length, isLoading])

  useEffect(() => {
    if (isDownloading && currentDownloadingIds.length > 0) {
      const firstDownloadingId = currentDownloadingIds[0]
      const currentRow = rowRefs.current[firstDownloadingId]
      if (currentRow && tableRef.current) {
        currentRow.scrollIntoView({
          behavior: "smooth",
          block: "center",
        })
      }
    }
  }, [currentDownloadingIds, isDownloading])

  const toggleVideo = (id: number) => {
    const video = videos.find(v => v.id === id);
    if (video && isVideoError(video.status)) return;
    if (selectedVideos.includes(id)) {
      setSelectedVideos(selectedVideos.filter((v) => v !== id))
    } else {
      setSelectedVideos([...selectedVideos, id])
    }
  }

  const toggleAll = () => {
    // Only toggle visible/filtered videos
    const visibleIds = filteredVideos.filter(v => !isVideoError(v.status)).map(v => v.id);
    const allVisibleSelected = visibleIds.every(id => selectedVideos.includes(id))

    if (allVisibleSelected) {
      // Unselect only the visible ones
      setSelectedVideos(selectedVideos.filter(id => !visibleIds.includes(id)))
    } else {
      // Add unselected visible ones to selection
      const newSelected = [...selectedVideos]
      visibleIds.forEach(id => {
        if (!newSelected.includes(id)) newSelected.push(id)
      })
      setSelectedVideos(newSelected)
    }
  }

  const getStatusColor = (status: string) => {
    if (status.includes("Đang") || status.includes("Tải")) return "text-yellow-400 animate-pulse"
    if (status.includes("Hoàn thành")) return "text-green-400"
    if (status.includes("Đã dừng")) return "text-red-400"
    return "text-gray-400"
  }

  const isVideoDownloading = (videoId: number) => currentDownloadingIds.includes(videoId)

  // Calculate stats for footer
  const visibleSelectedCount = filteredVideos.filter(v => selectedVideos.includes(v.id)).length

  return (
    <div className="bg-white/5 backdrop-blur-md border border-white/10 rounded-xl overflow-hidden transition-all duration-500 flex-1 flex flex-col min-h-0 shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/10 shrink-0 bg-white/5">
        <div className="flex items-center gap-2">
          <div className="w-8 h-5 bg-gradient-to-r from-red-500 to-orange-500 rounded flex items-center justify-center shadow-lg shadow-orange-500/20">
            <span className="text-[10px] font-bold text-white">PLAY</span>
          </div>
          <span className="font-medium bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">Kết quả video</span>
          {isDownloading && (
            <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 animate-pulse">
              Đang tải: {downloadedCount}/{totalDownloadCount}
            </span>
          )}
        </div>
        <button
          onClick={() => setShowFilter(!showFilter)}
          className={`cursor-pointer flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs transition-all duration-300 border ${showFilter
            ? "bg-cyan-500/20 text-cyan-400 border-cyan-500/50"
            : "bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white border-white/5 hover:border-white/20"
            }`}
        >
          {showFilter ? <X className="w-3.5 h-3.5" /> : <Filter className="w-3.5 h-3.5" />}
          Filter
        </button>
      </div>

      {/* Filter Panel */}
      {showFilter && (
        <div className="px-4 py-3 border-b border-white/10 bg-white/5 grid grid-cols-2 md:grid-cols-4 gap-3 animate-in slide-in-from-top-2">
          <div className="relative group">
            <div className="absolute inset-y-0 left-2 flex items-center pointer-events-none">
              <Eye className="w-3.5 h-3.5 text-blue-400" />
            </div>
            <input
              type="text"
              placeholder="Min Collects"
              value={filters.collects}
              onChange={(e) => setFilters(prev => ({ ...prev, collects: e.target.value }))}
              className="w-full bg-black/20 border border-white/10 rounded-lg py-1.5 pl-8 pr-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500/50 focus:bg-black/40 transition-all font-mono"
            />
          </div>
          <div className="relative group">
            <div className="absolute inset-y-0 left-2 flex items-center pointer-events-none">
              <Heart className="w-3.5 h-3.5 text-pink-400" />
            </div>
            <input
              type="text"
              placeholder="Min Likes"
              value={filters.likes}
              onChange={(e) => setFilters(prev => ({ ...prev, likes: e.target.value }))}
              className="w-full bg-black/20 border border-white/10 rounded-lg py-1.5 pl-8 pr-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-pink-500/50 focus:bg-black/40 transition-all font-mono"
            />
          </div>
          <div className="relative group">
            <div className="absolute inset-y-0 left-2 flex items-center pointer-events-none">
              <MessageCircle className="w-3.5 h-3.5 text-gray-400" />
            </div>
            <input
              type="text"
              placeholder="Min Comments"
              value={filters.comments}
              onChange={(e) => setFilters(prev => ({ ...prev, comments: e.target.value }))}
              className="w-full bg-black/20 border border-white/10 rounded-lg py-1.5 pl-8 pr-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-gray-500/50 focus:bg-black/40 transition-all font-mono"
            />
          </div>
          <div className="relative group">
            <div className="absolute inset-y-0 left-2 flex items-center pointer-events-none">
              <Share2 className="w-3.5 h-3.5 text-green-400" />
            </div>
            <input
              type="text"
              placeholder="Min Shares"
              value={filters.shares}
              onChange={(e) => setFilters(prev => ({ ...prev, shares: e.target.value }))}
              className="w-full bg-black/20 border border-white/10 rounded-lg py-1.5 pl-8 pr-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-green-500/50 focus:bg-black/40 transition-all font-mono"
            />
          </div>
        </div>
      )}

      <div ref={tableRef} className="flex-1 overflow-y-auto overflow-x-auto custom-scrollbar min-h-0 scroll-smooth">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 animate-pulse">
            <Loader2 className="w-12 h-12 text-cyan-400 animate-spin mb-4" />
            <p className="text-gray-400 font-light tracking-wide">Đang tải danh sách video...</p>
            <div className="mt-4 flex gap-2">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce"
                  style={{ animationDelay: `${i * 150}ms` }}
                />
              ))}
            </div>
          </div>
        ) : !isDataFetched ? (
          <div className="flex flex-col items-center justify-center py-20 text-gray-500">
            <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mb-4">
              <Loader2 className="w-10 h-10 opacity-30" />
            </div>
            <p className="text-lg font-medium text-gray-400">Chưa có dữ liệu</p>
            <p className="text-xs mt-2 opacity-60">Nhấn "Lấy danh sách video" để bắt đầu</p>
          </div>
        ) : filteredVideos.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-gray-500">
            <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mb-3">
              <Search className="w-8 h-8 opacity-40" />
            </div>
            <p className="text-sm font-medium text-gray-400">Không tìm thấy video nào</p>
            <p className="text-xs mt-1 opacity-60">Thử điều chỉnh bộ lọc của bạn</p>
            <button
              onClick={() => setFilters({ collects: "", likes: "", comments: "", shares: "" })}
              className="mt-3 px-3 py-1 bg-white/10 hover:bg-white/20 rounded text-xs text-white transition-colors"
            >
              Xóa bộ lọc
            </button>
          </div>
        ) : (
          <table className="w-full text-sm border-collapse">
            <thead className="sticky top-0 bg-[#151525]/90 backdrop-blur-md z-10 shadow-sm">
              <tr className="text-gray-400 text-left text-xs uppercase tracking-wider">
                <th className="px-4 py-3 w-12 font-medium">STT</th>
                <th className="px-4 py-3 w-12 font-medium text-center">#</th>
                <th className="px-4 py-3 font-medium max-w-[200px]">URL</th>
                <th className="px-4 py-3 font-medium">Caption</th>
                <th className="px-4 py-3 font-medium text-center">Cmt</th>
                <th className="px-4 py-3 font-medium text-center">Like</th>
                <th className="px-4 py-3 font-medium text-center">Collect</th>
                <th className="px-4 py-3 font-medium text-center">Share</th>
                <th className="px-4 py-3 font-medium text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {filteredVideos.map((video, index) => (
                <tr
                  key={video.id}
                  ref={(el) => {
                    rowRefs.current[video.id] = el
                  }}
                  className={`group transition-all duration-300 animate-slide-in ${isVideoError(video.status) ? "bg-gray-900/50 text-gray-500 opacity-60" : isVideoDownloading(video.id) ? "bg-cyan-500/10" : "hover:bg-white/5"
                    }`}
                  style={{ animationDelay: `${index * 30}ms` }}
                >
                  <td className="px-4 py-3 text-gray-500 font-mono text-xs">{video.id}</td>
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={() => toggleVideo(video.id)}
                      disabled={isDownloading || isVideoError(video.status)}
                      className={`cursor-pointer w-5 h-5 rounded border flex items-center justify-center transition-all duration-300 transform group-hover:scale-110 disabled:opacity-50 mx-auto ${isVideoError(video.status) ? "bg-red-500/20 border-red-500/50 cursor-not-allowed" : selectedVideos.includes(video.id)
                        ? "bg-cyan-500 border-cyan-500 shadow-lg shadow-cyan-500/30"
                        : "border-gray-600 bg-transparent group-hover:border-cyan-400 text-transparent hover:text-cyan-400/50"
                        }`}
                    >
                      <span className={`text-xs ${selectedVideos.includes(video.id) ? "text-white scale-100" : "scale-0"} transition-transform duration-200`}>✓</span>
                    </button>
                  </td>
                  <td className="px-4 py-3 max-w-[200px]">
                    <a
                      href={video.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      title={video.url}
                      className="text-cyan-400 hover:text-cyan-300 truncate block transition-colors duration-300 text-xs font-mono bg-cyan-500/10 px-2 py-1 rounded border border-cyan-500/20"
                    >
                      {video.url}
                    </a>
                  </td>
                  <td className="px-4 py-3 text-gray-300 truncate max-w-[250px] font-light">
                    {video.caption}
                  </td>
                  <td className="px-4 py-3 text-center text-gray-400 text-xs">
                    {video.comments}
                  </td>
                  <td className="px-4 py-3 text-center text-pink-400 text-xs font-medium">
                    {video.likes}
                  </td>
                  <td className="px-4 py-3 text-center text-blue-400 text-xs">
                    {video.collects}
                  </td>
                  <td className="px-4 py-3 text-center text-green-400 text-xs">
                    {video.shares}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${isVideoError(video.status) ? "bg-red-500/20 text-red-400 border-red-500/30" : (video.status || "").includes("Hoàn thành") ? "bg-green-500/10 text-green-400 border-green-500/20" :
                      (video.status || "").includes("Đang") ? "bg-yellow-500/10 text-yellow-400 border-yellow-500/20 animate-pulse" :
                        (video.status || "").includes("Đã dừng") ? "bg-red-500/10 text-red-400 border-red-500/20" :
                          "bg-gray-500/10 text-gray-400 border-gray-500/20"
                      }`}>
                      {video.status || "Sẵn sàng"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-4 py-2 border-t border-white/10 shrink-0 bg-white/5 text-xs">
        <div className="flex items-center gap-2 text-gray-400">
          {showFilter && (filters.collects || filters.likes || filters.comments || filters.shares) ? (
            <span>Đang lọc: <span className="text-white font-medium">{filteredVideos.length}</span> / {videos.length} video</span>
          ) : (
            <span>Tổng: <span className="text-white font-medium">{videos.length}</span> video</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={toggleAll}
            disabled={!isDataFetched || isDownloading || filteredVideos.length === 0}
            className="cursor-pointer flex items-center gap-2 text-gray-400 hover:text-cyan-400 transition-all duration-300 disabled:opacity-50 hover:bg-white/5 px-2 py-1 rounded-lg"
          >
            <CheckSquare className="w-4 h-4" />
            <span>{visibleSelectedCount === filteredVideos.length && filteredVideos.length > 0 ? "Bỏ chọn" : "Chọn tất cả"}</span>
            <span className="ml-1 px-1.5 py-0.5 bg-white/10 rounded-md text-white">{visibleSelectedCount}</span>
          </button>
        </div>
      </div>
    </div>
  )
}
