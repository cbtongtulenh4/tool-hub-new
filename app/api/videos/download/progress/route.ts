import { NextRequest } from "next/server"

export async function GET(request: NextRequest) {
    const { searchParams } = new URL(request.url)
    const downloadId = searchParams.get('id')

    if (!downloadId) {
        return new Response(
            JSON.stringify({ error: 'Missing download_id' }),
            {
                status: 400,
                headers: { 'Content-Type': 'application/json' }
            }
        )
    }

    try {
        // Proxy SSE from Flask
        const response = await fetch(
            `http://localhost:5000/api/download_progress/${downloadId}`,
            {
                headers: {
                    'Accept': 'text/event-stream',
                },
            }
        )

        if (!response.ok) {
            return new Response(
                JSON.stringify({ error: 'Failed to connect to download stream' }),
                {
                    status: response.status,
                    headers: { 'Content-Type': 'application/json' }
                }
            )
        }

        // Return SSE stream
        return new Response(response.body, {
            headers: {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            },
        })
    } catch (error) {
        console.error('Error proxying SSE:', error)
        return new Response(
            JSON.stringify({ error: 'Internal server error' }),
            {
                status: 500,
                headers: { 'Content-Type': 'application/json' }
            }
        )
    }
}
