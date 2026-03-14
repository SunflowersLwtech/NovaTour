"use client";

import { useCallback, useId, useState } from "react";
import { useVoiceAgent } from "@/hooks/useVoiceAgent";
import { VoicePanel } from "@/ui/VoicePanel";
import { ChatInterface } from "@/ui/ChatInterface";
import { ItineraryWorkspace } from "@/ui/ItineraryWorkspace";
import { NovaActViewer } from "@/ui/NovaActViewer";
import { TripMap } from "@/ui/TripMap";

export type InteractionMode = "voice" | "text";
type SideTab = "itinerary" | "map";

export default function Home() {
  const sessionId = `session-${useId().replace(/:/g, "")}`;
  const [interactionMode, setInteractionMode] =
    useState<InteractionMode>("voice");
  const [sideTab, setSideTab] = useState<SideTab>("itinerary");

  const {
    isConnected,
    isListening,
    isMuted,
    micLevel,
    voiceState,
    messages,
    toolCalls,
    itinerary,
    lodLevel,
    bookingProgress,
    error,
    connect,
    disconnect,
    startListening,
    stopListening,
    sendText,
    setLod,
    toggleMute,
    cancelBooking,
  } = useVoiceAgent(sessionId);

  const handleModeChange = useCallback(
    (nextMode: InteractionMode) => {
      setInteractionMode(nextMode);
      if (nextMode === "text") {
        stopListening();
        disconnect();
      }
    },
    [disconnect, stopListening]
  );

  const handleConnect = useCallback(() => {
    setInteractionMode("voice");
    connect();
  }, [connect]);

  const handleStartListening = useCallback(() => {
    setInteractionMode("voice");
    startListening();
  }, [startListening]);

  return (
    <div className="flex flex-col h-screen bg-deep">
      {/* Compact header toolbar */}
      <VoicePanel
        interactionMode={interactionMode}
        isConnected={isConnected}
        isListening={isListening}
        isMuted={isMuted}
        micLevel={micLevel}
        voiceState={voiceState}
        lodLevel={lodLevel}
        onConnect={handleConnect}
        onDisconnect={disconnect}
        onStartListening={handleStartListening}
        onStopListening={stopListening}
        onSetLod={setLod}
        onSetInteractionMode={handleModeChange}
        onToggleMute={toggleMute}
      />

      {/* Error banner */}
      {error && (
        <div className="px-4 py-2 text-sm bg-err/10 border-b border-err/20 text-err">
          {error}
        </div>
      )}

      {/* Main content: Chat + Side panel */}
      <div className="flex-1 flex overflow-hidden">
        {/* Chat — primary panel */}
        <div className="flex-1 min-w-[320px] border-r border-subtle">
          <ChatInterface
            interactionMode={interactionMode}
            messages={messages}
            toolCalls={toolCalls}
            onSendText={sendText}
            isConnected={isConnected}
          />
        </div>

        {/* Side panel — hidden on small screens */}
        <div className="hidden lg:flex w-[400px] flex-col bg-surface">
          {/* Tab bar */}
          <div className="flex border-b border-subtle">
            {(["itinerary", "map"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setSideTab(tab)}
                className={`flex-1 px-4 py-3 text-xs font-semibold uppercase tracking-[0.15em] transition-colors ${
                  sideTab === tab
                    ? "text-accent border-b-2 border-accent"
                    : "text-dim border-b-2 border-transparent hover:text-secondary"
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-hidden">
            {sideTab === "itinerary" ? (
              <ItineraryWorkspace itinerary={itinerary} />
            ) : (
              <TripMap itinerary={itinerary} />
            )}
          </div>
        </div>
      </div>

      {/* Booking overlay */}
      <NovaActViewer bookingProgress={bookingProgress} onCancel={cancelBooking} />
    </div>
  );
}
