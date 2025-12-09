"use client"

import { useState } from "react"
import { Header } from "./downloader/header"
import { Sidebar } from "./downloader/sidebar"
import { VideoResults } from "./downloader/video-results"
import { DownloadOptions } from "./downloader/download-options"

interface VideoItem {
  id: number
  url: string
  caption: string
  comments: number
  likes: string
  views: string
  shares: number
  status: string
}



export function VideoDownloader() {
  const [activeTab, setActiveTab] = useState<"channel" | "url">("channel")
  const [selectedPlatform, setSelectedPlatform] = useState("tiktok")
  const [channelUrl, setChannelUrl] = useState("https://www.tiktok.com/@sinhnovas")
  const [selectedVideos, setSelectedVideos] = useState<number[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isDataFetched, setIsDataFetched] = useState(false)
  const [videos, setVideos] = useState<VideoItem[]>([])
  const [isDownloading, setIsDownloading] = useState(false)
  const [currentDownloadingIds, setCurrentDownloadingIds] = useState<number[]>([])
  const [downloadedCount, setDownloadedCount] = useState(0)
  const [totalDownloadCount, setTotalDownloadCount] = useState(0)
  const [urlListText, setUrlListText] = useState("")
  const [concurrentDownloads, setConcurrentDownloads] = useState(5)

  const handleStartFetch = async () => {
    setIsLoading(true)
    try {
      const response = await fetch("http://localhost:5000/api/videos/list", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: channelUrl }),
      })

      if (response.ok) {
        const data = await response.json()
        setVideos(data.videos)
        setIsDataFetched(true)
      } else {
        console.error("Failed to fetch videos")
      }
    } catch (error) {
      console.error("Error fetching videos:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleStartFetchFromUrls = async () => {
    if (!urlListText.trim()) return
    setIsLoading(true)
    try {
      const response = await fetch("http://localhost:5000/api/load_info_from_videos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ urls: urlListText }),
      })

      if (response.ok) {
        const data = await response.json()
        setVideos(data.videos)
        setIsDataFetched(true)
      } else {
        console.error("Failed to fetch videos from URLs")
      }
    } catch (error) {
      console.error("Error fetching videos:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleStopFetch = async () => {
    try {
      await fetch("http://localhost:5000/api/load_list_user_videos/stop", { method: "POST" })
    } catch (error) {
      console.error("Error stopping fetch:", error)
    }

    setIsLoading(false)
    setIsDataFetched(false)
    setSelectedVideos([])
    setVideos([])
    setIsDownloading(false)
    setCurrentDownloadingIds([])
    setDownloadedCount(0)
    setTotalDownloadCount(0)
  }

  const handleStartDownload = async () => {
    if (selectedVideos.length === 0) return

    setIsDownloading(true)
    setTotalDownloadCount(selectedVideos.length)
    setDownloadedCount(0)

    const queue = [...selectedVideos]
    let completed = 0

    const downloadVideo = async (videoId: number): Promise<void> => {
      setCurrentDownloadingIds((prev) => [...prev, videoId])

      setVideos((prev) => prev.map((v) => (v.id === videoId ? { ...v, status: "Đang tải..." } : v)))
      await new Promise((resolve) => setTimeout(resolve, 300))

      const totalTime = 2000 + Math.random() * 3000
      const steps = 5
      const stepTime = totalTime / steps

      for (let i = 1; i <= steps; i++) {
        const progress = Math.floor((i / steps) * 100)
        setVideos((prev) => prev.map((v) => (v.id === videoId ? { ...v, status: `Tải ${progress}%` } : v)))
        await new Promise((resolve) => setTimeout(resolve, stepTime))
      }

      setVideos((prev) => prev.map((v) => (v.id === videoId ? { ...v, status: "Hoàn thành ✓" } : v)))
      setCurrentDownloadingIds((prev) => prev.filter((id) => id !== videoId))
      completed++
      setDownloadedCount(completed)
    }

    while (queue.length > 0) {
      const batch = queue.splice(0, concurrentDownloads)
      await Promise.all(batch.map((videoId) => downloadVideo(videoId)))
    }

    setIsDownloading(false)
    setCurrentDownloadingIds([])
  }

  const handleStopDownload = () => {
    setIsDownloading(false)
    setCurrentDownloadingIds([])
    setVideos((prev) =>
      prev.map((v) => (v.status.includes("Đang") || v.status.includes("Tải") ? { ...v, status: "Đã dừng" } : v)),
    )
  }

  return (
    <div className="h-screen bg-gradient-to-br from-[#0f0c29] via-[#302b63] to-[#24243e] text-white flex flex-col overflow-hidden font-sans selection:bg-cyan-500/30">
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none mix-blend-overlay" style={{ backgroundImage: "url('/noise.png')" }} />
      <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-b from-transparent via-cyan-900/5 to-purple-900/10 pointer-events-none" />

      <Header />

      <div className="flex-1 px-4 py-3 flex flex-col overflow-hidden relative z-10">
        <div className="flex gap-2 mb-4 shrink-0">
          <button
            onClick={() => setActiveTab("channel")}
            className={`relative overflow-hidden px-6 py-2.5 rounded-xl font-medium transition-all duration-300 transform hover:scale-105 active:scale-95 ${activeTab === "channel"
              ? "bg-gradient-to-r from-orange-500 to-red-500 text-white shadow-lg shadow-orange-500/30 ring-1 ring-orange-400/50"
              : "bg-white/5 hover:bg-white/10 text-gray-400 backdrop-blur-sm border border-white/5"
              }`}
          >
            <span className="relative z-10">Get video theo Kênh</span>
            {activeTab === "channel" && (
              <div className="absolute inset-0 bg-white/20 animate-pulse-glow" />
            )}
          </button>
          <button
            onClick={() => setActiveTab("url")}
            className={`relative overflow-hidden px-6 py-2.5 rounded-xl font-medium transition-all duration-300 transform hover:scale-105 active:scale-95 ${activeTab === "url"
              ? "bg-gradient-to-r from-orange-500 to-red-500 text-white shadow-lg shadow-orange-500/30 ring-1 ring-orange-400/50"
              : "bg-white/5 hover:bg-white/10 text-gray-400 backdrop-blur-sm border border-white/5"
              }`}
          >
            <span className="relative z-10">Tải theo Danh sách URL</span>
            {activeTab === "url" && (
              <div className="absolute inset-0 bg-white/20 animate-pulse-glow" />
            )}
          </button>
        </div>

        <div className="flex gap-4 flex-1 min-h-0">
          <Sidebar
            selectedPlatform={selectedPlatform}
            setSelectedPlatform={setSelectedPlatform}
            channelUrl={channelUrl}
            setChannelUrl={setChannelUrl}
            isLoading={isLoading}
            onStart={handleStartFetch}
            onStop={handleStopFetch}
            activeTab={activeTab}
            urlListText={urlListText}
            setUrlListText={setUrlListText}
            onStartFromUrls={handleStartFetchFromUrls}
          />

          <div className="flex-1 flex flex-col gap-4 min-h-0">
            <VideoResults
              videos={videos}
              selectedVideos={selectedVideos}
              setSelectedVideos={setSelectedVideos}
              isLoading={isLoading}
              isDataFetched={isDataFetched}
              isDownloading={isDownloading}
              currentDownloadingIds={currentDownloadingIds}
              downloadedCount={downloadedCount}
              totalDownloadCount={totalDownloadCount}
            />
            <DownloadOptions
              isDataFetched={isDataFetched}
              selectedCount={selectedVideos.length}
              isDownloading={isDownloading}
              onStartDownload={handleStartDownload}
              onStopDownload={handleStopDownload}
              downloadedCount={downloadedCount}
              totalDownloadCount={totalDownloadCount}
              concurrentDownloads={concurrentDownloads}
              setConcurrentDownloads={setConcurrentDownloads}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
