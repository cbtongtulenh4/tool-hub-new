"use client"

import { useState } from "react"
import { Folder, Download, StopCircle, FileText, ChevronDown, ChevronUp } from "lucide-react"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select"

interface DownloadOptionsProps {
  isDataFetched: boolean
  selectedCount: number
  isDownloading: boolean
  onStartDownload: (options: DownloadSettings) => void
  onStopDownload: () => void
  downloadedCount: number
  totalDownloadCount: number
  concurrentDownloads: number
  setConcurrentDownloads: (value: number) => void
}

export interface DownloadSettings {
  savePath: string
  quality: string
  videoFormat: string
  audioFormat: string
  videoEnabled: boolean
  audioEnabled: boolean
  concurrentDownloads: number
}

export function DownloadOptions({
  isDataFetched,
  selectedCount,
  isDownloading,
  onStartDownload,
  onStopDownload,
  downloadedCount,
  totalDownloadCount,
  concurrentDownloads,
  setConcurrentDownloads,
}: DownloadOptionsProps) {
  const [savePath, setSavePath] = useState("D:/Videos/Downloader")
  const [isChoosingPath, setIsChoosingPath] = useState(false)
  const [videoEnabled, setVideoEnabled] = useState(true)
  const [audioEnabled, setAudioEnabled] = useState(true)
  const [videoFormat, setVideoFormat] = useState("MP4")
  const [audioFormat, setAudioFormat] = useState("MP3")
  const [quality, setQuality] = useState("Cao nhất")
  const [isCollapsed, setIsCollapsed] = useState(false)

  const handleChoosePath = async () => {
    if (isChoosingPath) return
    setIsChoosingPath(true)
    try {
      const response = await fetch("/api/choose-directory", { method: "POST" })
      if (response.ok) {
        const data = await response.json()
        if (data.path) {
          setSavePath(data.path)
        }
      }
    } catch (error) {
      console.error("Error choosing path:", error)
    } finally {
      setIsChoosingPath(false)
    }
  }

  return (
    <div
      className={`bg-white/5 backdrop-blur-md border border-white/10 rounded-xl p-2 transition-all duration-500 shrink-0 shadow-lg ${isDataFetched ? "opacity-100 translate-y-0" : "opacity-60 grayscale"
        }`}
    >

      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-[#2a2a4a] rounded-t-xl transition-all duration-300"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <Download className="w-5 h-5 text-gray-400" />
          <span className="font-medium">Tùy chọn tải xuống</span>
        </div>
        <div className="flex items-center gap-3">
          {isCollapsed && (
            <div className="flex items-center gap-3 text-sm text-gray-400 animate-fade-in">
              <span className="bg-[#1a1a2e] px-2 py-1 rounded">{quality}</span>
              <span className="bg-[#1a1a2e] px-2 py-1 rounded">{videoFormat}</span>
              <span className="bg-[#1a1a2e] px-2 py-1 rounded">x{concurrentDownloads}</span>
            </div>
          )}
          <button
            className={`p-1 rounded-lg hover:bg-[#3a3a5a] transition-all duration-300 ${isCollapsed ? "" : "rotate-180"}`}
          >
            <ChevronUp className="w-5 h-5 text-gray-400" />
          </button>
        </div>
      </div>
      {/* <div className="flex items-center gap-2 mb-2">
        <Download className="w-5 h-5 text-cyan-400" />
        <span className="font-medium bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">Tùy chọn tải xuống</span>
      </div> */}

      <div
        className={`grid transition-all duration-500 ease-in-out ${isCollapsed ? "grid-rows-[0fr] opacity-0" : "grid-rows-[1fr] opacity-100"
          }`}
      >
        <div className="overflow-hidden">
          <div className="px-4 pb-4"></div>

          <div className="grid grid-cols-3 gap-4 mb-2">
            {/* Save Path */}
            <div className="animate-fade-in group" style={{ animationDelay: "100ms" }}>
              <label className="text-xs text-gray-400 mb-2 block uppercase tracking-wider font-medium group-hover:text-cyan-400 transition-colors">Đường dẫn lưu</label>
              <div className="flex gap-2 relative">
                <input
                  type="text"
                  value={savePath}
                  readOnly
                  className="flex-1 bg-black/20 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:ring-1 focus:ring-cyan-500/50 transition-all duration-300 font-mono text-xs"
                />
                <button
                  onClick={handleChoosePath}
                  disabled={isChoosingPath}
                  className="cursor-pointer bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white px-3 py-2 rounded-lg transition-all duration-300 border border-white/5 hover:border-white/20 active:scale-95 disabled:opacity-50 disabled:cursor-wait"
                >
                  <Folder className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Quality */}
            <div className="animate-fade-in group" style={{ animationDelay: "200ms" }}>
              <label className="text-xs text-gray-400 mb-2 block uppercase tracking-wider font-medium group-hover:text-cyan-400 transition-colors">Chất lượng</label>
              <div className="relative">
                <Select value={quality} onValueChange={setQuality}>
                  <SelectTrigger className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white appearance-none cursor-pointer transition-all duration-300 focus:ring-1 focus:ring-cyan-500/50 hover:bg-black/30">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1a1a2e] border border-white/10 rounded-lg shadow-lg">
                    <SelectItem value="Cao nhất" className="cursor-pointer hover:bg-white/10 py-2 px-3 rounded">Cao nhat</SelectItem>
                    <SelectItem value="1080p" className="cursor-pointer hover:bg-white/10 py-2 px-3 rounded">1080p</SelectItem>
                    <SelectItem value="720p" className="cursor-pointer hover:bg-white/10 py-2 px-3 rounded">720p</SelectItem>
                    <SelectItem value="480p" className="cursor-pointer hover:bg-white/10 py-2 px-3 rounded">480p</SelectItem>
                  </SelectContent>
                </Select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none group-hover:text-cyan-400 transition-colors" />
              </div>
            </div>

            {/* Concurrent Downloads */}
            <div className="animate-fade-in group" style={{ animationDelay: "300ms" }}>
              <label className="text-xs text-gray-400 mb-2 block uppercase tracking-wider font-medium group-hover:text-cyan-400 transition-colors">Tải đồng thời</label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  value={concurrentDownloads}
                  onChange={(e) => setConcurrentDownloads(Math.max(1, Math.min(10, Number.parseInt(e.target.value) || 1)))}
                  min={1}
                  max={10}
                  className="flex-1 bg-black/20 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:ring-1 focus:ring-cyan-500/50 transition-all duration-300 text-center font-bold"
                />
                <div className="flex flex-col gap-0.5">
                  <button
                    onClick={() => setConcurrentDownloads(Math.min(10, concurrentDownloads + 1))}
                    className="bg-white/5 hover:bg-cyan-500/20 hover:text-cyan-400 p-0.5 rounded transition-all duration-300 active:scale-90"
                  >
                    <ChevronUp className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => setConcurrentDownloads(Math.max(1, concurrentDownloads - 1))}
                    className="bg-white/5 hover:bg-cyan-500/20 hover:text-cyan-400 p-0.5 rounded transition-all duration-300 active:scale-90"
                  >
                    <ChevronDown className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Video/Audio Toggles */}
          <div className="grid grid-cols-2 gap-4 mb-2">
            {/* Video Toggle */}
            <div className="flex items-center gap-4 animate-fade-in p-3 rounded-xl bg-black/10 border border-white/5 transition-colors hover:bg-black/20 group" style={{ animationDelay: "400ms" }}>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setVideoEnabled(!videoEnabled)}
                  className={`cursor-pointer w-10 h-6 rounded-full transition-all duration-300 relative ${videoEnabled ? "bg-gradient-to-r from-cyan-500 to-blue-500 shadow-lg shadow-cyan-500/30" : "bg-gray-700"
                    }`}
                >
                  <div
                    className={`w-4 h-4 bg-white rounded-full transition-all duration-300 shadow-md absolute top-1 left-1 ${videoEnabled ? "translate-x-4" : "translate-x-0"
                      }`}
                  />
                </button>
                <span className={`text-sm font-medium transition-colors ${videoEnabled ? "text-white" : "text-gray-500"}`}>Video</span>
              </div>
              <div className="relative flex-1">
                <Select value={videoFormat} onValueChange={setVideoFormat} disabled={!videoEnabled}>
                  <SelectTrigger className={`w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white appearance-none cursor-pointer transition-all duration-300 focus:ring-1 focus:ring-cyan-500/50 hover:bg-black/30 ${!videoEnabled ? 'opacity-30 cursor-not-allowed' : ''}`}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1a1a2e] border border-white/10 rounded-lg shadow-lg">
                    <SelectItem value="MP4" className="cursor-pointer hover:bg-white/10 py-2 px-3 rounded">MP4</SelectItem>
                    <SelectItem value="MKV" className="cursor-pointer hover:bg-white/10 py-2 px-3 rounded">MKV</SelectItem>
                    <SelectItem value="AVI" className="cursor-pointer hover:bg-white/10 py-2 px-3 rounded">AVI</SelectItem>
                    <SelectItem value="WEBM" className="cursor-pointer hover:bg-white/10 py-2 px-3 rounded">WEBM</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Audio Toggle */}
            <div className="flex items-center gap-4 animate-fade-in p-3 rounded-xl bg-black/10 border border-white/5 transition-colors hover:bg-black/20 group" style={{ animationDelay: "500ms" }}>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setAudioEnabled(!audioEnabled)}
                  className={`cursor-pointer w-10 h-6 rounded-full transition-all duration-300 relative ${audioEnabled ? "bg-gradient-to-r from-cyan-500 to-blue-500 shadow-lg shadow-cyan-500/30" : "bg-gray-700"
                    }`}
                >
                  <div
                    className={`w-4 h-4 bg-white rounded-full transition-all duration-300 shadow-md absolute top-1 left-1 ${audioEnabled ? "translate-x-4" : "translate-x-0"
                      }`}
                  />
                </button>
                <span className={`text-sm font-medium transition-colors ${audioEnabled ? "text-white" : "text-gray-500"}`}>Audio</span>
              </div>
              <div className="relative flex-1">
                <Select value={audioFormat} onValueChange={setAudioFormat} disabled={!audioEnabled}>
                  <SelectTrigger className={`w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white appearance-none cursor-pointer transition-all duration-300 focus:ring-1 focus:ring-cyan-500/50 hover:bg-black/30 ${!audioEnabled ? 'opacity-30 cursor-not-allowed' : ''}`}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1a1a2e] border border-white/10 rounded-lg shadow-lg">
                    <SelectItem value="MP3" className="cursor-pointer hover:bg-white/10 py-2 px-3 rounded">MP3</SelectItem>
                    <SelectItem value="AAC" className="cursor-pointer hover:bg-white/10 py-2 px-3 rounded">AAC</SelectItem>
                    <SelectItem value="WAV" className="cursor-pointer hover:bg-white/10 py-2 px-3 rounded">WAV</SelectItem>
                    <SelectItem value="FLAC" className="cursor-pointer hover:bg-white/10 py-2 px-3 rounded">FLAC</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}

      {/* <div className="flex items-center justify-between animate-fade-in pt-1" style={{ animationDelay: "600ms" }}> */}
      <div
        className={`flex items-center justify-between p-4 border-t border-[#3a3a5a] ${isCollapsed ? "rounded-b-xl" : ""}`}
      >

        <button className="cursor-pointer flex items-center gap-2 text-gray-400 hover:text-cyan-400 transition-all duration-300 hover:scale-105 active:scale-95 text-xs font-medium uppercase tracking-wide group">
          <div className="p-1.5 rounded-lg bg-white/5 group-hover:bg-cyan-500/10 transition-colors">
            <FileText className="w-4 h-4" />
          </div>
          Xem file kết quả
        </button>

        <div className="flex items-center gap-3">
          {isDownloading ? (
            <div className="flex items-center gap-3 px-5 py-2.5 rounded-xl bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 shadow-lg shadow-yellow-500/5">
              <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
              <span className="font-medium text-sm">
                Đang xử lý {downloadedCount}/{totalDownloadCount}
              </span>
            </div>
          ) : (
            <button
              onClick={() => onStartDownload({
                savePath,
                quality,
                videoFormat,
                audioFormat,
                videoEnabled,
                audioEnabled,
                concurrentDownloads
              })}
              disabled={!isDataFetched || selectedCount === 0}
              className="cursor-pointer relative overflow-hidden group flex items-center gap-2 bg-gradient-to-r from-cyan-600 to-blue-600 disabled:from-gray-700 disabled:to-gray-800 text-white px-6 py-2.5 rounded-xl transition-all duration-300 hover:shadow-lg hover:shadow-cyan-500/20 active:scale-95 disabled:active:scale-100 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div className="absolute inset-0 bg-white/20 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
              <Download className="w-4 h-4" />
              <span className="font-bold text-sm">Tải đã chọn ({selectedCount})</span>
            </button>
          )}
          <button
            disabled={true}//{!isDownloading}
            onClick={onStopDownload}
            className="cursor-pointer flex items-center gap-2 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 px-4 py-2.5 rounded-xl transition-all duration-300 hover:shadow-lg hover:shadow-red-500/10 active:scale-95"
          >
            <StopCircle className="w-4 h-4" />
            <span className="font-medium text-sm">Dừng</span>
          </button>
        </div>
      </div>
    </div>
  )
}
