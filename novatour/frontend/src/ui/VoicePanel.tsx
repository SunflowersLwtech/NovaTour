"use client";

import type { VoiceStateValue } from "@/hooks/useVoiceAgent";

interface VoicePanelProps {
  interactionMode: "voice" | "text";
  isConnected: boolean;
  isListening: boolean;
  isMuted: boolean;
  micLevel: number;
  voiceState: VoiceStateValue;
  lodLevel: number;
  onConnect: () => void;
  onDisconnect: () => void;
  onStartListening: () => void;
  onStopListening: () => void;
  onSetLod: (level: number) => void;
  onSetInteractionMode: (mode: "voice" | "text") => void;
  onToggleMute: () => void;
}

function MiniMeter({
  level,
  active,
  muted,
}: {
  level: number;
  active: boolean;
  muted: boolean;
}) {
  const bars = 6;
  const lit = active ? Math.max(1, Math.round(level * bars)) : 0;

  return (
    <div className="flex items-end gap-[3px] h-5" aria-hidden="true">
      {Array.from({ length: bars }).map((_, i) => (
        <div
          key={i}
          className={`w-[3px] rounded-full transition-all duration-75 ${
            i < lit ? (muted ? "bg-warn" : "bg-accent") : "bg-subtle"
          }`}
          style={{ height: `${40 + ((i % 3) + 1) * 20}%` }}
        />
      ))}
    </div>
  );
}

export function VoicePanel({
  interactionMode,
  isConnected,
  isListening,
  isMuted,
  micLevel,
  voiceState,
  lodLevel,
  onConnect,
  onDisconnect,
  onStartListening,
  onStopListening,
  onSetLod,
  onSetInteractionMode,
  onToggleMute,
}: VoicePanelProps) {
  const voiceEnabled = interactionMode === "voice";

  // Status indicator
  let statusColor = "bg-dim";
  let statusLabel = "Text mode";

  if (voiceEnabled) {
    if (isMuted) {
      statusColor = "bg-warn";
      statusLabel = "Muted";
    } else if (isListening) {
      if (voiceState === "responding") {
        statusColor = "bg-ok";
        statusLabel = "Speaking";
      } else if (voiceState === "interrupted") {
        statusColor = "bg-warn";
        statusLabel = "Interrupted";
      } else {
        statusColor = "bg-ok";
        statusLabel = "Listening";
      }
    } else if (isConnected) {
      statusColor = "bg-secondary";
      statusLabel = "Connected";
    } else {
      statusColor = "bg-dim";
      statusLabel = "Disconnected";
    }
  }

  return (
    <header className="flex items-center gap-3 px-4 h-14 border-b border-subtle bg-surface shrink-0">
      {/* Brand */}
      <h1 className="text-lg font-extrabold tracking-tight shrink-0">
        Nova<span className="text-accent">Tour</span>
      </h1>

      <div className="w-px h-5 bg-subtle shrink-0" />

      {/* Mode toggle */}
      <div className="flex rounded-lg bg-deep p-0.5 gap-0.5 shrink-0">
        {(["text", "voice"] as const).map((mode) => (
          <button
            key={mode}
            type="button"
            onClick={() => onSetInteractionMode(mode)}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
              interactionMode === mode
                ? "bg-accent text-deep"
                : "text-secondary hover:text-primary"
            }`}
          >
            {mode === "voice" ? "Voice" : "Text"}
          </button>
        ))}
      </div>

      {/* Voice controls — only in voice mode */}
      {voiceEnabled && (
        <>
          <div className="w-px h-5 bg-subtle shrink-0" />

          <button
            type="button"
            onClick={isConnected ? onDisconnect : onConnect}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all shrink-0 ${
              isConnected
                ? "bg-ok/15 text-ok hover:bg-ok/25"
                : "bg-elevated text-secondary hover:text-primary hover:bg-raised"
            }`}
          >
            {isConnected ? "Connected" : "Connect"}
          </button>

          {isConnected && (
            <>
              <button
                type="button"
                onClick={isListening ? onStopListening : onStartListening}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all shrink-0 ${
                  isListening
                    ? "bg-err/15 text-err hover:bg-err/25"
                    : "bg-elevated text-secondary hover:text-primary hover:bg-raised"
                }`}
              >
                {isListening ? "Stop mic" : "Open mic"}
              </button>

              {isListening && (
                <>
                  <button
                    type="button"
                    onClick={onToggleMute}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all shrink-0 ${
                      isMuted
                        ? "bg-warn/15 text-warn hover:bg-warn/25"
                        : "bg-elevated text-secondary hover:text-primary hover:bg-raised"
                    }`}
                  >
                    {isMuted ? "Unmute" : "Mute"}
                  </button>

                  <MiniMeter
                    level={micLevel}
                    active={!isMuted}
                    muted={isMuted}
                  />
                </>
              )}
            </>
          )}
        </>
      )}

      {/* Spacer */}
      <div className="flex-1 min-w-0" />

      {/* LOD selector */}
      <div className="flex gap-1 shrink-0">
        {[1, 2, 3].map((level) => (
          <button
            key={level}
            type="button"
            onClick={() => onSetLod(level)}
            className={`w-7 h-7 rounded-md text-xs font-bold transition-all ${
              lodLevel === level
                ? "bg-accent text-deep"
                : "bg-elevated text-dim hover:text-secondary hover:bg-raised"
            }`}
            aria-label={`Detail level ${level}`}
          >
            {level}
          </button>
        ))}
      </div>

      <div className="w-px h-5 bg-subtle shrink-0" />

      {/* Status */}
      <div className="flex items-center gap-2 shrink-0">
        <div
          className={`w-2 h-2 rounded-full ${statusColor} ${
            isListening && !isMuted ? "pulse-dot" : ""
          }`}
        />
        <span className="text-xs font-medium text-secondary">
          {statusLabel}
        </span>
      </div>
    </header>
  );
}
