"use client"

import type React from "react"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Check, Pencil, Upload, FileAudio, Loader2 } from "lucide-react"

export default function SurveyAssistant() {
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [languageFile, setLanguageFile] = useState<File | null>(null)
  const [questionFile, setQuestionFile] = useState<File | null>(null)
  const [transcriptionMode, setTranscriptionMode] = useState<"local" | "online">("local")
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [isMatching, setIsMatching] = useState(false)
  const [isDragging, setIsDragging] = useState(false)

  const handleAudioDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file && (file.type.includes("audio") || file.name.match(/\.(mp3|wav|ogg)$/i))) {
      setAudioFile(file)
    }
  }

  const handleAudioSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setAudioFile(file)
    }
  }

  const handleTranscribe = async () => {
    if (!audioFile) return
    setIsTranscribing(true)
    // Simulate transcription process
    await new Promise((resolve) => setTimeout(resolve, 2000))
    setIsTranscribing(false)
  }

  const handleMatch = async () => {
    if (!languageFile || !questionFile) return
    setIsMatching(true)
    // Simulate matching process
    await new Promise((resolve) => setTimeout(resolve, 2000))
    setIsMatching(false)
  }

  return (
    <div className="container mx-auto px-4 py-8 md:py-16 max-w-7xl">
      <div className="flex gap-6 items-center justify-center">
        <aside className="hidden lg:flex lg:flex-col lg:justify-center lg:w-[280px]">
          <div className="backdrop-blur-md bg-white/40 rounded-3xl p-6 border border-white/60 shadow-lg">
            <h3 className="text-sm font-semibold text-foreground/80 mb-4 tracking-wide uppercase">使用指南</h3>
            <div className="space-y-4">
              <StepItem number={1} title="上传音频" description="点击或拖拽音频文件" />
              <StepItem number={2} title="选择模式" description="本地转写或在线转写" />
              <StepItem number={3} title="开始转文字" description="等待完成后查看结果" />
              <StepItem number={4} title="格式化文本" description="自动整理为采访对话" />
              <StepItem number={5} title="下载结果" description="导出生成的文本" />
            </div>
          </div>
        </aside>

        <Card className="backdrop-blur-xl bg-white/70 shadow-2xl border-white/50 overflow-hidden lg:max-w-3xl flex-shrink-0">
          <div className="p-8 md:p-12">
            {/* Header */}
            <div className="text-center mb-8">
              <div className="inline-flex items-center gap-3 mb-4">
                <Pencil className="w-8 h-8 text-foreground/70" />
                <h1 className="text-4xl md:text-5xl font-semibold tracking-tight text-balance">问卷调查AI小助手</h1>
              </div>
            </div>

            {/* Status Badge */}
            <div className="mb-8">
              <div className="flex items-center gap-2 px-5 py-4 bg-success/10 rounded-2xl border border-success/20">
                <div className="w-5 h-5 rounded-full bg-success flex items-center justify-center flex-shrink-0">
                  <Check className="w-3 h-3 text-white" strokeWidth={3} />
                </div>
                <p className="text-sm font-medium text-foreground">
                  本地服务已连接 <span className="text-muted-foreground ml-1">(离线转写模式)</span>
                </p>
              </div>
            </div>

            {/* Audio Upload Area */}
            <div
              className={`mb-8 relative rounded-3xl border-2 border-dashed transition-all ${
                isDragging ? "border-primary bg-primary/5" : "border-border bg-secondary/30"
              }`}
              onDragOver={(e) => {
                e.preventDefault()
                setIsDragging(true)
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleAudioDrop}
            >
              <input
                type="file"
                id="audio-upload"
                className="hidden"
                accept=".mp3,.wav,.ogg,audio/*"
                onChange={handleAudioSelect}
              />
              <label
                htmlFor="audio-upload"
                className="flex flex-col items-center justify-center py-16 px-6 cursor-pointer"
              >
                <div className="mb-6">
                  <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-100 to-indigo-100 flex items-center justify-center shadow-lg">
                    {audioFile ? (
                      <FileAudio className="w-10 h-10 text-primary" />
                    ) : (
                      <Upload className="w-10 h-10 text-primary" />
                    )}
                  </div>
                </div>
                <p className="text-lg font-medium text-foreground mb-2 text-center">
                  {audioFile ? audioFile.name : "点击或拖拽音频文件到这里"}
                </p>
                <p className="text-sm text-muted-foreground text-center">支持 MP3、WAV、OGG 等格式</p>
              </label>
            </div>

            {/* Transcription Mode Toggle */}
            <div className="flex items-center justify-between mb-6">
              <span className="text-sm font-medium text-foreground">转写模式：</span>
              <div className="inline-flex rounded-xl bg-secondary p-1 shadow-inner">
                <button
                  onClick={() => setTranscriptionMode("local")}
                  className={`px-6 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    transcriptionMode === "local"
                      ? "bg-primary text-primary-foreground shadow-md"
                      : "text-foreground/70 hover:text-foreground"
                  }`}
                >
                  本地转写
                </button>
                <button
                  onClick={() => setTranscriptionMode("online")}
                  className={`px-6 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    transcriptionMode === "online"
                      ? "bg-primary text-primary-foreground shadow-md"
                      : "text-foreground/70 hover:text-foreground"
                  }`}
                >
                  在线转写
                </button>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="grid grid-cols-2 gap-4 mb-12">
              <Button
                size="lg"
                onClick={handleTranscribe}
                disabled={!audioFile || isTranscribing}
                className="h-14 rounded-2xl bg-primary hover:bg-primary/90 text-primary-foreground font-medium shadow-lg hover:shadow-xl transition-all"
              >
                {isTranscribing ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    转写中...
                  </>
                ) : (
                  "开始转文字"
                )}
              </Button>
              <Button
                size="lg"
                variant="outline"
                onClick={() => setAudioFile(null)}
                className="h-14 rounded-2xl font-medium bg-white/50 hover:bg-white/80 border-border/50 transition-all"
              >
                清空
              </Button>
            </div>

            {/* AI Matching Section */}
            <div className="pt-8 border-t border-border/50">
              <h2 className="text-2xl font-semibold mb-3 tracking-tight">AI智能分析匹配</h2>
              <p className="text-sm text-muted-foreground mb-6 leading-relaxed">
                选择语言转化的文本文件和问题编写文件，点击开始匹配。
              </p>

              {/* File Selection */}
              <div className="grid md:grid-cols-2 gap-4 mb-6">
                <FileSelector
                  label="选取文件"
                  placeholder="未选择文件"
                  file={languageFile}
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) setLanguageFile(file)
                  }}
                  id="language-file"
                />
                <FileSelector
                  label="选取文件"
                  placeholder="未选择文件"
                  file={questionFile}
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) setQuestionFile(file)
                  }}
                  id="question-file"
                />
              </div>

              {/* Match Action Buttons */}
              <div className="grid grid-cols-2 gap-4">
                <Button
                  size="lg"
                  onClick={handleMatch}
                  disabled={!languageFile || !questionFile || isMatching}
                  className="h-14 rounded-2xl bg-primary hover:bg-primary/90 text-primary-foreground font-medium shadow-lg hover:shadow-xl transition-all"
                >
                  {isMatching ? (
                    <>
                      <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                      匹配中...
                    </>
                  ) : (
                    "开始匹配"
                  )}
                </Button>
                <Button
                  size="lg"
                  variant="outline"
                  className="h-14 rounded-2xl font-medium bg-white/50 hover:bg-white/80 border-border/50 transition-all"
                >
                  下载结果
                </Button>
              </div>
            </div>
          </div>
        </Card>

        <aside className="hidden lg:flex lg:flex-col lg:justify-center lg:w-[280px]">
          <div className="backdrop-blur-md bg-white/40 rounded-3xl p-6 border border-white/60 shadow-lg">
            <h3 className="text-sm font-semibold text-foreground/80 mb-4 tracking-wide uppercase">AI智能匹配</h3>
            <div className="space-y-4">
              <StepItem number={1} title="选择结果文件" description="转写格式化后的 .txt" />
              <StepItem number={2} title="选择问题模板" description="问卷模板文件" />
              <StepItem number={3} title="开始匹配" description="等待模型输出完成" />
              <StepItem number={4} title="下载结果" description="保存匹配后的文本" />
            </div>
            <div className="mt-6 pt-6 border-t border-white/40">
              <p className="text-xs text-muted-foreground leading-relaxed">
              </p>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}

function StepItem({ number, title, description }: { number: number; title: string; description: string }) {
  return (
    <div className="flex gap-3 group">
      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500/20 to-indigo-500/20 flex items-center justify-center flex-shrink-0 group-hover:from-blue-500/30 group-hover:to-indigo-500/30 transition-colors">
        <span className="text-xs font-semibold text-primary">{number}</span>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground mb-0.5">{title}</p>
        <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
      </div>
    </div>
  )
}

function FileSelector({
  label,
  placeholder,
  file,
  onChange,
  id,
}: {
  label: string
  placeholder: string
  file: File | null
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  id: string
}) {
  return (
    <div>
      <input type="file" id={id} className="hidden" accept=".txt,.doc,.docx,.pdf" onChange={onChange} />
      <label
        htmlFor={id}
        className="flex items-center justify-between px-5 py-4 rounded-xl bg-secondary/50 hover:bg-secondary/80 border border-border/50 cursor-pointer transition-all group"
      >
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-foreground/60 mb-1">{label}</p>
          <p className="text-sm text-foreground truncate">{file ? file.name : placeholder}</p>
        </div>
        <div className="ml-3 w-10 h-10 rounded-lg bg-white/50 group-hover:bg-white flex items-center justify-center flex-shrink-0 transition-colors">
          <Upload className="w-5 h-5 text-muted-foreground" />
        </div>
      </label>
    </div>
  )
}
