"use client";

import { useEffect, useRef, useState } from "react";
import type { ToolCallInfo, TranscriptMessage } from "@/types/voice";

interface ChatInterfaceProps {
  interactionMode: "voice" | "text";
  messages: TranscriptMessage[];
  toolCalls: ToolCallInfo[];
  onSendText: (text: string) => void;
  isConnected: boolean;
}

export function ChatInterface({
  interactionMode,
  messages,
  toolCalls,
  onSendText,
  isConnected,
}: ChatInterfaceProps) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, toolCalls]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    onSendText(input.trim());
    setInput("");
  };

  return (
    <div className="flex flex-col h-full bg-gray-900">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-700">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-gray-300">Chat</h2>
          <span
            className={`rounded-full px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.18em] ${
              interactionMode === "voice"
                ? "bg-cyan-500/15 text-cyan-300"
                : "bg-slate-800 text-slate-300"
            }`}
          >
            {interactionMode === "voice" ? "Voice assisted" : "Text first"}
          </span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 text-sm mt-8">
            <p>
              {interactionMode === "voice"
                ? "Voice mode is active. You can speak, or type if that is faster."
                : "Text mode is active. Type below, or switch back to voice when you want live audio."}
            </p>
            <p className="text-xs mt-1 opacity-60">
              {interactionMode === "voice"
                ? isConnected
                  ? "The live session is connected and ready."
                  : "Connect voice above if you want microphone input."
                : "Text chat works without any voice connection."}
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-lg px-4 py-2 text-sm ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-700 text-gray-100"
              } ${!msg.is_final ? "opacity-70" : ""}`}
            >
              <p className="whitespace-pre-wrap">{msg.text}</p>
              {!msg.is_final && (
                <span className="text-xs opacity-50">...</span>
              )}
            </div>
          </div>
        ))}

        {/* Active tool calls */}
        {toolCalls
          .filter((t) => t.status === "calling")
          .map((tc) => (
            <div
              key={`${tc.name}-${tc.timestamp}`}
              className="flex items-center gap-2 px-3 py-2 bg-yellow-900/30 rounded-lg border border-yellow-700/50"
            >
              <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse" />
              <span className="text-xs text-yellow-300">
                Calling {tc.name}...
              </span>
            </div>
          ))}

        {/* Completed tool calls with results */}
        {toolCalls
          .filter((t) => t.status === "complete")
          .slice(-5)
          .map((tc) => (
            <div
              key={`${tc.name}-${tc.timestamp}`}
              className="px-3 py-2 bg-green-900/20 rounded-lg border border-green-700/30"
            >
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-400 rounded-full" />
                <span className="text-xs text-green-300 font-medium">
                  {tc.name}
                </span>
              </div>
              {tc.result && (
                <p className="text-xs text-gray-400 mt-1 line-clamp-3">
                  {tc.result.slice(0, 200)}
                  {tc.result.length > 200 ? "..." : ""}
                </p>
              )}
            </div>
          ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Input — always enabled (REST fallback when disconnected) */}
      <form
        onSubmit={handleSubmit}
        className="p-3 border-t border-gray-700"
      >
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              interactionMode === "voice"
                ? isConnected
                  ? "Type a message while voice mode stays active..."
                  : "Type a message, or connect voice above..."
                : "Type a message in text mode..."
            }
            className="flex-1 bg-gray-800 text-white rounded-lg px-4 py-2 text-sm border border-gray-600 focus:border-blue-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={!input.trim()}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
