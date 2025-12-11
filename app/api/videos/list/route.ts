
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

    const body = await request.json();
    const response = await fetch("http://localhost:5000/api/load_videos_by_list", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    })

    if (!response.body) {
        return NextResponse.json({ error: "Backend does not support streaming" }, { status: 500 })
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    return new Response(
        new ReadableStream({
            async start(controller) {
                try {
                    while (true) {
                        const { done, value } = await reader.read()
                        if (done) break
                        controller.enqueue(value) // không decode/encode lại
                    }
                    controller.close()
                } catch (err) {
                    controller.error(err)
                } finally {
                    reader.releaseLock()
                }
            }
        }),
        {
            headers: {
                "Content-Type": "text/plain", // hoặc "text/event-stream"
            }
        }
    )
}
