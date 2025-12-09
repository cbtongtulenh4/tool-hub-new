"use client"

import { useState } from "react"
import { Download } from "lucide-react"

export function Header() {
  const [language, setLanguage] = useState("vi")

  return (
    <header className="flex items-center justify-between px-6 py-4 relative z-20">
      <div className="flex items-center gap-3 backdrop-blur-md bg-white/5 border border-white/10 p-2 rounded-2xl shadow-lg transition-transform hover:scale-[1.02]">
        <div className="w-10 h-10 bg-gradient-to-br from-cyan-400 to-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-cyan-500/30">
          <Download className="w-6 h-6 text-white" />
        </div>
        <div className="pr-2">
          <h1 className="text-lg font-bold bg-gradient-to-r from-white via-cyan-200 to-cyan-400 bg-clip-text text-transparent">MediaDownloader</h1>
          <p className="text-[10px] text-gray-400 font-medium tracking-wider uppercase">Multi-Platform Downloader</p>
        </div>
      </div>

      {/* Language Switcher */}
      <div className="flex items-center gap-1 backdrop-blur-md bg-white/5 border border-white/10 p-1.5 rounded-xl shadow-lg">
        <button
          onClick={() => setLanguage("vi")}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all duration-300 ${language === "vi" ? "bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-md" : "text-gray-400 hover:text-white hover:bg-white/5"
            }`}
        >
          VN
        </button>
        <button
          onClick={() => setLanguage("en")}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all duration-300 ${language === "en" ? "bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-md" : "text-gray-400 hover:text-white hover:bg-white/5"
            }`}
        >
          EN
        </button>
      </div>
    </header>
  )
}
