
import { NextResponse } from "next/server"

export async function POST(request: Request) {
    const response = await fetch("http://localhost:5000/api/download/stop", { method: "POST" })
    const data = await response.json()
    return NextResponse.json(data)
}

