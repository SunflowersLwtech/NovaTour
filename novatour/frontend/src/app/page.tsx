"use client";

import { useCallback, useId, useState } from "react";
import { useVoiceAgent } from "@/hooks/useVoiceAgent";
import { VoicePanel } from "@/ui/VoicePanel";
import { ChatInterface } from "@/ui/ChatInterface";
import { ItineraryWorkspace } from "@/ui/ItineraryWorkspace";
import { NovaActViewer } from "@/ui/NovaActViewer";
import { TripMap } from "@/ui/TripMap";

export type InteractionMode = "voice" | "text";

export default function Home() {
  const sessionId = `session-${useId().replace(/:/g, "")}`;
  const [interactionMode, setInteractionMode] = useState<InteractionMode>("voice");

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
    <div className="flex flex-col h-screen bg-gray-950">
      {/* Top voice panel */}
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
        <div className="px-4 py-2 bg-red-900/50 border-b border-red-700 text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Three-column layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Chat — always available (text fallback via REST when disconnected) */}
        <div className="w-1/3 min-w-[320px] border-r border-gray-700">
          <ChatInterface
            interactionMode={interactionMode}
            messages={messages}
            toolCalls={toolCalls}
            onSendText={sendText}
            isConnected={isConnected}
          />
        </div>

        {/* Center: Itinerary */}
        <div className="flex-1 border-r border-gray-700">
          <ItineraryWorkspace itinerary={itinerary} />
        </div>

        {/* Right: Map */}
        <div className="w-1/3 min-w-[300px] bg-gray-900 flex flex-col">
          <div className="px-4 py-3 border-b border-gray-700">
            <h2 className="text-sm font-semibold text-gray-300">Map</h2>
          </div>
          <div className="flex-1">
            <TripMap itinerary={itinerary} />
          </div>
        </div>
      </div>

      {/* NovaActViewer overlay — with cancel wired */}
      <NovaActViewer bookingProgress={bookingProgress} onCancel={cancelBooking} />
    </div>
  );
}
