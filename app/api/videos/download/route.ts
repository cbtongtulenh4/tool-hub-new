import { NextResponse } from "next/server"

interface DownloadRequest {
    video_urls: string[]
    save_path: string
    quality: string
    video_format: string
    audio_format: string
    video_enabled: boolean
    audio_enabled: boolean
    concurrent_downloads: number
}

export async function POST(request: Request) {
    try {
        const body: DownloadRequest = await request.json()

        // Forward request to Python backend
        const response = await fetch("http://localhost:5000/api/download_videos", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        })

        if (!response.ok) {
            return NextResponse.json(
                { error: "Failed to start download" },
                { status: response.status }
            )
        }

        const data = await response.json()
        return NextResponse.json(data)
    } catch (error) {
        console.error("Error starting download:", error)
        return NextResponse.json(
            { error: "Internal Server Error" },
            { status: 500 }
        )
    }
}
