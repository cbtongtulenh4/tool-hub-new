import { NextResponse } from "next/server"

export async function POST(request: Request) {
    try {
        // Forward request to Python backend
        const response = await fetch("http://localhost:5000/api/choose-directory", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
        })

        if (!response.ok) {
            return NextResponse.json(
                { error: "Failed to open directory chooser" },
                { status: response.status }
            )
        }

        const data = await response.json()
        return NextResponse.json(data)
    } catch (error) {
        console.error("Error choosing directory:", error)
        return NextResponse.json(
            { error: "Internal Server Error" },
            { status: 500 }
        )
    }
}
