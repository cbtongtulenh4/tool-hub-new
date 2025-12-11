"use client"

import { useState } from "react"
import { Header } from "./downloader/header"
import { Sidebar } from "./downloader/sidebar"
import { VideoResults } from "./downloader/video-results"
import { DownloadOptions } from "./downloader/download-options"
import { useToast } from '@/hooks/use-toast'
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
  const [channelUrl, setChannelUrl] = useState("")
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
  const { toast } = useToast()

  const handleStartFetch = async () => {
    // Reset state before fetching
    setVideos([]);
    setSelectedVideos([]);  // Reset checkbox selections
    setIsDataFetched(false);
    setIsLoading(true);

    try {
      const response = await fetch("/api/videos/user", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel_url: channelUrl }),
      })

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let isFirstChunk = true;

      while (true) {
        const { done, value } = await reader!.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        const items = chunk.split('\n').filter(line => line.trim());

        if (items.length > 0) {

          const newVideos = items.flatMap(item => {
            const parsed = JSON.parse(item);
            return Array.isArray(parsed) ? parsed : [parsed];
          });
          if (newVideos[0].error) {
            toast({
              title: "Loi",
              description: newVideos[0].message || "",
              variant: "destructive"
            })
            setIsLoading(false);
            continue;
          }
          setVideos(prev => [...prev, ...newVideos]);

          // Set isDataFetched to true on first chunk so table renders immediately
          if (isFirstChunk) {
            setIsLoading(false)
            setIsDataFetched(true);
            isFirstChunk = false;
          }
        }
      }
    } catch (error) {
      console.error("Error fetching videos:", error)
    }
  }

  const handleStartFetchFromUrls = async () => {
    if (!urlListText.trim()) return

    // Reset state before fetching
    setVideos([]);
    setSelectedVideos([]);  // Reset checkbox selections
    setIsDataFetched(false);
    setIsLoading(true);


    try {
      const response = await fetch("/api/videos/list", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ urls: urlListText }),
      })

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let isFirstChunk = true;

      while (true) {
        const { done, value } = await reader!.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        const items = chunk.split('\n').filter(line => line.trim());

        if (items.length > 0) {

          const newVideos = items.flatMap(item => {
            const parsed = JSON.parse(item);
            return Array.isArray(parsed) ? parsed : [parsed];
          });
          if (newVideos[0].error) {
            toast({
              title: "Loi",
              description: newVideos[0].message || "",
              variant: "destructive"
            })
            setIsLoading(false);
            continue;
          }
          setVideos(prev => [...prev, ...newVideos]);

          if (isFirstChunk) {
            setIsLoading(false)
            setIsDataFetched(true);
            isFirstChunk = false;
          }
        }
      }
    } catch (error) {
      console.error("Error fetching videos:", error)
    }
  }

  const handleStopFetch = async () => {
    try {
      await fetch("/api/videos/stop", { method: "POST" })
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

  const handleStartDownload = async (settings: {
    savePath: string
    quality: string
    videoFormat: string
    audioFormat: string
    videoEnabled: boolean
    audioEnabled: boolean
    concurrentDownloads: number
  }) => {
    if (selectedVideos.length === 0) return

    setIsDownloading(true)
    setTotalDownloadCount(selectedVideos.length)
    setDownloadedCount(0)

    // Get URLs of selected videos, excluding already completed ones
    const selectedVideoUrls = videos
      .filter(v => selectedVideos.includes(v.id))
      .filter(v => !v.status.includes('Hoàn thành'))  // Skip completed videos
      .map(v => v.url)

    // Deduplicate URLs to avoid downloading same video multiple times
    const uniqueUrls = [...new Set(selectedVideoUrls)]

    console.log('Selected video IDs:', selectedVideos)
    console.log('Selected video URLs (with duplicates):', selectedVideoUrls)
    console.log('Unique URLs to download:', uniqueUrls)
    console.log('Total videos in list:', videos.length)

    if (uniqueUrls.length === 0) {
      toast({
        title: "Không có video nào cần tải",
        description: "Tất cả videos đã chọn đều đã được tải xuống",
        variant: "default",
      })
      return
    }

    try {
      // Call the download API
      const response = await fetch("/api/videos/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_urls: uniqueUrls,  // Use deduplicated URLs
          save_path: settings.savePath,
          quality: settings.quality,
          video_format: settings.videoFormat,
          audio_format: settings.audioFormat,
          video_enabled: settings.videoEnabled,
          audio_enabled: settings.audioEnabled,
          concurrent_downloads: settings.concurrentDownloads,
        }),
      })

      if (!response.ok) {
        toast({
          title: "Lỗi",
          description: "Không thể bắt đầu tải xuống",
          variant: "destructive",
        })
        setIsDownloading(false)
        return
      }

      const data = await response.json()
      const downloadId = data.download_id

      toast({
        title: "Đã bắt đầu tải xuống",
        description: `Đang tải ${selectedVideos.length} video`,
      })

      // Update initial status
      setVideos((prev) =>
        prev.map((v) =>
          selectedVideos.includes(v.id) ? { ...v, status: "Đang tải..." } : v
        )
      )

      // Connect to SSE for progress updates
      const eventSource = new EventSource(`/api/videos/download/progress?id=${downloadId}`)

      eventSource.onmessage = (event) => {
        try {
          const progressData = JSON.parse(event.data)

          if (progressData.type === 'started') {
            console.log('Download started:', progressData)
          } else if (progressData.type === 'progress') {
            console.log('Progress update for URL:', progressData.url, 'Status:', progressData.status)
            // Update specific video status - only for selected videos with matching URL
            setVideos((prev) =>
              prev.map((v) =>
                v.url === progressData.url && selectedVideos.includes(v.id)
                  ? {
                    ...v,
                    status: progressData.status === 'success'
                      ? 'Hoàn thành ✓'
                      : `Lỗi: ${progressData.message || 'Unknown error'}`
                  }
                  : v
              )
            )
            setDownloadedCount(progressData.completed)
          } else if (progressData.type === 'completed') {
            eventSource.close()
            setIsDownloading(false)
            setCurrentDownloadingIds([])
            toast({
              title: "Hoàn thành",
              description: `Đã tải xong ${progressData.completed}/${progressData.total} video`,
            })
          } else if (progressData.type === 'error') {
            eventSource.close()
            setIsDownloading(false)
            setCurrentDownloadingIds([])
            toast({
              title: "Lỗi",
              description: progressData.error || "Có lỗi xảy ra",
              variant: "destructive",
            })
          }
        } catch (err) {
          console.error('Error parsing SSE data:', err)
        }
      }

      eventSource.onerror = (error) => {
        console.error('SSE Error:', error)
        eventSource.close()
        setIsDownloading(false)
        setCurrentDownloadingIds([])
        toast({
          title: "Lỗi kết nối",
          description: "Mất kết nối với server",
          variant: "destructive",
        })
      }

    } catch (error) {
      console.error("Error downloading videos:", error)
      toast({
        title: "Lỗi",
        description: "Có lỗi xảy ra khi tải xuống",
        variant: "destructive",
      })
      setIsDownloading(false)
      setCurrentDownloadingIds([])
    }
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
        <div className="flex gap-2 mb-2 shrink-0">
          <button
            onClick={() => setActiveTab("channel")}
            className={`cursor-pointer relative overflow-hidden px-3 py-1.5 rounded-lg font-medium transition-all duration-300 transform hover:scale-105 active:scale-95 ${activeTab === "channel"
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
            className={`cursor-pointer relative overflow-hidden px-3 py-1.5 rounded-lg font-medium transition-all duration-300 transform hover:scale-105 active:scale-95 ${activeTab === "url"
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
