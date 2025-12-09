
import { NextResponse } from "next/server"

export async function POST(request: Request) {
    // Simulate processing the stop command
    await new Promise((resolve) => setTimeout(resolve, 500))

    return NextResponse.json({ message: "Stop command received" })
}
