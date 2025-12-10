
import { NextResponse } from "next/server"

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

export async function POST(request: Request) {
    try {
        const body = await request.json();
        const response = await fetch("http://localhost:5000/api/load_videos_by_list", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        })

        const data = await response.json()
        let items = data.items



        if (items && Array.isArray(items)) {
            const generatedVideos: VideoItem[] = items.map((item: any, index: number) => ({
                id: index + 1,
                url: (item.url || "").trim(),
                caption: (item.title || "").trim(),
                comments: item.comments ?? 0,
                likes: item.likes ?? "0",
                views: item.views ?? "0",
                shares: item.shares ?? 0,
                status: "Sẵn sàng",
            }))
            return NextResponse.json({ videos: generatedVideos })
        }
    } catch (error) {
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 })
    }
}
