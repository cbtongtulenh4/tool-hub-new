
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

const initialVideos: VideoItem[] = [
    {
        id: 1,
        url: "https://www.tiktok.com/@user/video/1",
        caption: "Hãy bảo vệ cảm xúc của bạn...",
        comments: 8,
        likes: "494",
        views: "9.7K",
        shares: 30,
        status: "Sẵn sàng",
    },
    {
        id: 2,
        url: "https://www.tiktok.com/@user/video/2",
        caption: "Con người khó tính nhất...",
        comments: 2,
        likes: "321",
        views: "5.2K",
        shares: 21,
        status: "Sẵn sàng",
    },
    {
        id: 3,
        url: "https://www.tiktok.com/@user/video/3",
        caption: "Tâm bất định, không làm...",
        comments: 45,
        likes: "3.4K",
        views: "37.8K",
        shares: 151,
        status: "Sẵn sàng",
    },
    {
        id: 4,
        url: "https://www.tiktok.com/@user/video/4",
        caption: "Sự tại nhân vi, mạc oán...",
        comments: 62,
        likes: "4.0K",
        views: "37.7K",
        shares: 232,
        status: "Sẵn sàng",
    },
    {
        id: 5,
        url: "https://www.tiktok.com/@user/video/5",
        caption: "Phong cảnh hữu tình...",
        comments: 7,
        likes: "141",
        views: "2.7K",
        shares: 2,
        status: "Sẵn sàng",
    },
    {
        id: 6,
        url: "https://www.tiktok.com/@user/video/6",
        caption: "Thả kiểu nhung nhớ...",
        comments: 34,
        likes: "2.6K",
        views: "56.4K",
        shares: 127,
        status: "Sẵn sàng",
    },
]

export async function POST(request: Request) {
    try {
        const response = await fetch("http://localhost:5000/api/load_list_user_videos", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: request.url }),
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

        return NextResponse.json({ videos: initialVideos })
    } catch (error) {
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 })
    }
}
