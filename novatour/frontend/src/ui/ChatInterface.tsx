"use client";

import { useEffect, useRef, useState } from "react";
import type { ToolCallInfo, TranscriptMessage } from "@/types/voice";

const SUGGESTIONS = [
  "Plan a 3-day trip to Tokyo",
  "What's the weather in Paris?",
  "Find flights to Bali",
  "Create a NYC itinerary",
];

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
    <div className="flex flex-col h-full bg-deep">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 ? (
          /* Empty state with welcome + suggestions */
          <div className="flex flex-col items-center justify-center h-full">
            <h2 className="text-3xl font-extrabold tracking-tight mb-1">
              Nova<span className="text-accent">Tour</span>
            </h2>
            <p className="text-secondary text-sm mb-8">
              Your AI travel companion. Ask me anything.
            </p>
            <div className="grid grid-cols-2 gap-2 max-w-sm w-full">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => onSendText(s)}
                  className="text-left px-4 py-3 rounded-xl bg-elevated border border-subtle text-sm text-secondary hover:text-primary hover:border-accent/30 hover:bg-raised transition-all"
                >
                  {s}
                </button>
              ))}
            </div>
            <p className="text-dim text-xs mt-6">
              {interactionMode === "voice"
                ? isConnected
                  ? "Voice session is connected. Speak or type below."
                  : "Connect voice above, or just type a message."
                : "Type a message below to get started."}
            </p>
          </div>
        ) : (
          /* Message list */
          <div className="space-y-3 max-w-2xl mx-auto">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                } msg-appear`}
              >
                <div
                  className={`max-w-[80%] px-4 py-2.5 text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-bubble text-bubble-text"
                      : "bg-elevated text-primary border border-subtle"
                  } ${!msg.is_final ? "opacity-60" : ""}`}
                  style={{
                    borderRadius:
                      msg.role === "user"
                        ? "16px 16px 4px 16px"
                        : "16px 16px 16px 4px",
                  }}
                >
                  <p className="whitespace-pre-wrap">{msg.text}</p>
                  {!msg.is_final && (
                    <span className="text-xs text-dim mt-1 inline-block">
                      ...
                    </span>
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
                  className="flex items-center gap-2.5 px-4 py-2.5 bg-accent/10 rounded-xl border border-accent/15 msg-appear"
                >
                  <div className="w-1.5 h-1.5 rounded-full bg-accent pulse-dot" />
                  <span className="text-xs text-accent font-medium">
                    {tc.name}
                  </span>
                </div>
              ))}

            {/* Completed tool calls */}
            {toolCalls
              .filter((t) => t.status === "complete")
              .slice(-5)
              .map((tc) => (
                <div
                  key={`${tc.name}-${tc.timestamp}`}
                  className="px-4 py-2.5 bg-ok/5 rounded-xl border border-ok/10"
                >
                  <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-ok" />
                    <span className="text-xs text-ok font-medium">
                      {tc.name}
                    </span>
                  </div>
                  {tc.result && (
                    <p className="text-xs text-dim mt-1.5 line-clamp-2">
                      {tc.result.slice(0, 200)}
                    </p>
                  )}
                </div>
              ))}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="px-6 py-4 border-t border-subtle">
        <form
          onSubmit={handleSubmit}
          className="flex gap-2 max-w-2xl mx-auto"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              interactionMode === "voice"
                ? "Type a message or speak..."
                : "Where would you like to go?"
            }
            className="flex-1 bg-elevated text-primary rounded-xl px-4 py-3 text-sm border border-subtle placeholder:text-dim focus:border-accent/50 focus:outline-none transition-colors"
          />
          <button
            type="submit"
            disabled={!input.trim()}
            className="px-5 py-3 bg-accent text-deep rounded-xl text-sm font-semibold hover:bg-accent-hover disabled:opacity-30 disabled:cursor-not-allowed transition-all"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
