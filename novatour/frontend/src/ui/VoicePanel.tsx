"use client";

import type { VoiceStateValue } from "@/hooks/useVoiceAgent";

const VOICE_STATE_DISPLAY: Record<
  VoiceStateValue,
  { label: string; color: string; description: string }
> = {
  idle: {
    label: "Ready",
    color: "text-slate-300",
    description: "Voice session is connected and waiting for you.",
  },
  responding: {
    label: "Speaking",
    color: "text-emerald-300",
    description: "NovaTour is actively speaking back to you.",
  },
  interrupted: {
    label: "Interrupted",
    color: "text-amber-300",
    description: "The previous response was interrupted.",
  },
  finished: {
    label: "Done",
    color: "text-sky-300",
    description: "The latest voice response has finished.",
  },
};

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

function AudioMeter({
  level,
  isActive,
  isMuted,
}: {
  level: number;
  isActive: boolean;
  isMuted: boolean;
}) {
  const barCount = 12;
  const activeBars = isActive ? Math.max(1, Math.round(level * barCount)) : 0;

  return (
    <div
      aria-hidden="true"
      className="flex h-10 items-end gap-1 rounded-xl border border-slate-800 bg-slate-950/80 px-3 py-2"
    >
      {Array.from({ length: barCount }).map((_, index) => {
        const isLit = index < activeBars;
        return (
          <div
            key={index}
            className={`w-1.5 rounded-full transition-all ${
              isLit
                ? isMuted
                  ? "bg-amber-400"
                  : "bg-cyan-400"
                : "bg-slate-800"
            }`}
            style={{ height: `${30 + ((index % 4) + 1) * 10}%` }}
          />
        );
      })}
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
  const statusInfo = !voiceEnabled
    ? {
        label: "Text mode",
        color: "text-slate-400",
        description: "Voice controls are paused until you switch back to voice mode.",
      }
    : isMuted
    ? {
        label: "Mic muted",
        color: "text-amber-300",
        description: "Microphone capture is running, but audio is not being sent.",
      }
    : isListening
    ? VOICE_STATE_DISPLAY[voiceState === "idle" ? "idle" : voiceState]
    : isConnected
    ? {
        label: "Mic off",
        color: "text-slate-300",
        description: "Voice session is connected. Open the microphone when you want to speak.",
      }
    : {
        label: "Disconnected",
        color: "text-slate-500",
        description: "Voice mode is available, but the live session is not connected yet.",
      };

  return (
    <header className="border-b border-slate-800 bg-slate-950">
      <div className="flex flex-col gap-4 px-4 py-4 lg:px-6">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-white">
                Nova<span className="text-cyan-400">Tour</span>
              </h1>
              <span className="rounded-full border border-slate-800 bg-slate-900 px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.18em] text-slate-400">
                Live travel copilot
              </span>
            </div>
            <p className="max-w-2xl text-sm text-slate-400">
              Choose how users interact first. Voice mode keeps the microphone workflow visible.
              Text mode removes that pressure and keeps the UI chat-first.
            </p>
          </div>

          <div
            className="inline-flex w-full rounded-2xl border border-slate-800 bg-slate-900 p-1 lg:w-auto"
            role="tablist"
            aria-label="Interaction mode"
          >
            {(["voice", "text"] as const).map((mode) => {
              const selected = interactionMode === mode;
              return (
                <button
                  key={mode}
                  type="button"
                  role="tab"
                  aria-selected={selected}
                  onClick={() => onSetInteractionMode(mode)}
                  className={`flex-1 rounded-xl px-4 py-2.5 text-sm font-medium transition lg:flex-none ${
                    selected
                      ? "bg-cyan-500 text-slate-950"
                      : "text-slate-300 hover:bg-slate-800"
                  }`}
                >
                  {mode === "voice" ? "Voice Mode" : "Text Mode"}
                </button>
              );
            })}
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-[1fr,1.4fr,auto]">
          <section className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">
                  Session
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <span
                    className={`h-2.5 w-2.5 rounded-full ${
                      isConnected && voiceEnabled ? "bg-emerald-400" : "bg-slate-600"
                    }`}
                    aria-hidden="true"
                  />
                  <p className="text-sm font-medium text-white">
                    {voiceEnabled
                      ? isConnected
                        ? "Voice connected"
                        : "Voice disconnected"
                      : "Text-first mode"}
                  </p>
                </div>
                <p className="mt-2 text-sm text-slate-400">
                  {voiceEnabled
                    ? "Connect the live voice session before opening the microphone."
                    : "Text mode keeps voice disconnected until the user explicitly switches back."}
                </p>
              </div>
              <button
                type="button"
                onClick={isConnected ? onDisconnect : onConnect}
                disabled={!voiceEnabled}
                className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                  !voiceEnabled
                    ? "cursor-not-allowed bg-slate-800 text-slate-500"
                    : isConnected
                    ? "bg-emerald-500 text-slate-950 hover:bg-emerald-400"
                    : "bg-slate-100 text-slate-950 hover:bg-white"
                }`}
              >
                {isConnected ? "Disconnect voice" : "Connect voice"}
              </button>
            </div>
          </section>

          <section className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">
                    Microphone
                  </p>
                  <p className={`mt-2 text-sm font-medium ${statusInfo.color}`} aria-live="polite">
                    {statusInfo.label}
                  </p>
                  <p className="mt-1 text-sm text-slate-400">{statusInfo.description}</p>
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={isListening ? onStopListening : onStartListening}
                    disabled={!voiceEnabled || !isConnected}
                    aria-pressed={isListening}
                    className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                      !voiceEnabled || !isConnected
                        ? "cursor-not-allowed bg-slate-800 text-slate-500"
                        : isListening
                        ? "bg-rose-500 text-white hover:bg-rose-400"
                        : "bg-cyan-500 text-slate-950 hover:bg-cyan-400"
                    }`}
                  >
                    {isListening ? "Close mic" : "Open mic"}
                  </button>
                  <button
                    type="button"
                    onClick={onToggleMute}
                    disabled={!voiceEnabled || !isListening}
                    aria-pressed={isMuted}
                    className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                      !voiceEnabled || !isListening
                        ? "cursor-not-allowed bg-slate-800 text-slate-500"
                        : isMuted
                        ? "bg-amber-500 text-slate-950 hover:bg-amber-400"
                        : "bg-slate-800 text-slate-200 hover:bg-slate-700"
                    }`}
                  >
                    {isMuted ? "Unmute mic" : "Mute mic"}
                  </button>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-[auto,1fr] md:items-center">
                <AudioMeter level={micLevel} isActive={voiceEnabled && isListening} isMuted={isMuted} />
                <div>
                  <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">
                    Input level
                  </p>
                  <p className="mt-1 text-sm text-slate-300">
                    {voiceEnabled && isListening
                      ? isMuted
                        ? "Microphone is open but muted."
                        : "Live microphone activity is visible here."
                      : "Open the microphone to see live input energy."}
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">
              Detail
            </p>
            <div className="mt-3 flex gap-2">
              {[1, 2, 3].map((level) => (
                <button
                  key={level}
                  type="button"
                  onClick={() => onSetLod(level)}
                  className={`h-10 w-10 rounded-xl text-sm font-semibold transition ${
                    lodLevel === level
                      ? "bg-cyan-500 text-slate-950"
                      : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                  }`}
                  aria-pressed={lodLevel === level}
                  aria-label={`Set detail level ${level}`}
                >
                  {level}
                </button>
              ))}
            </div>
            <p className="mt-3 max-w-48 text-sm text-slate-400">
              Keep responses brief at level 1 and more narrative at level 3.
            </p>
          </section>
        </div>
      </div>
    </header>
  );
}
