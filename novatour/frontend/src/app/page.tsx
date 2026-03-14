"use client";

import { useMemo } from "react";
import { useVoiceAgent } from "@/hooks/useVoiceAgent";
import { VoicePanel } from "@/ui/VoicePanel";
import { ChatInterface } from "@/ui/ChatInterface";
import { ItineraryWorkspace } from "@/ui/ItineraryWorkspace";
import { NovaActViewer } from "@/ui/NovaActViewer";
import { TripMap } from "@/ui/TripMap";

export default function Home() {
  const sessionId = useMemo(
    () => `session-${Date.now().toString(36)}`,
    []
  );

  const {
    isConnected,
    isListening,
    isMuted,
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
  } = useVoiceAgent(sessionId);

  return (
    <div className="flex flex-col h-screen bg-gray-950">
      {/* Top voice panel */}
      <VoicePanel
        isConnected={isConnected}
        isListening={isListening}
        isMuted={isMuted}
        lodLevel={lodLevel}
        onConnect={connect}
        onDisconnect={disconnect}
        onStartListening={startListening}
        onStopListening={stopListening}
        onSetLod={setLod}
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
        {/* Left: Chat */}
        <div className="w-1/3 min-w-[320px] border-r border-gray-700">
          <ChatInterface
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

      {/* NovaActViewer overlay */}
      <NovaActViewer bookingProgress={bookingProgress} />
    </div>
  );
}
