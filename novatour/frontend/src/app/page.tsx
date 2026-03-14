"use client";

import { useMemo } from "react";
import { useVoiceAgent } from "@/hooks/useVoiceAgent";
import { VoicePanel } from "@/ui/VoicePanel";
import { ChatInterface } from "@/ui/ChatInterface";
import { ItineraryWorkspace } from "@/ui/ItineraryWorkspace";

export default function Home() {
  const sessionId = useMemo(
    () => `session-${Date.now().toString(36)}`,
    []
  );

  const {
    isConnected,
    isListening,
    messages,
    toolCalls,
    itinerary,
    lodLevel,
    error,
    connect,
    disconnect,
    startListening,
    stopListening,
    sendText,
    setLod,
  } = useVoiceAgent(sessionId);

  return (
    <div className="flex flex-col h-screen bg-gray-950">
      {/* Top voice panel */}
      <VoicePanel
        isConnected={isConnected}
        isListening={isListening}
        lodLevel={lodLevel}
        onConnect={connect}
        onDisconnect={disconnect}
        onStartListening={startListening}
        onStopListening={stopListening}
        onSetLod={setLod}
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

        {/* Right: Map placeholder */}
        <div className="w-1/3 min-w-[300px] bg-gray-900 flex flex-col">
          <div className="px-4 py-3 border-b border-gray-700">
            <h2 className="text-sm font-semibold text-gray-300">Map</h2>
          </div>
          <div className="flex-1 flex items-center justify-center text-gray-600">
            <div className="text-center">
              <svg
                className="w-16 h-16 mx-auto mb-3 opacity-30"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <path d="M20.5 3l-.16.03L15 5.1 9 3 3.36 4.9c-.21.07-.36.25-.36.48V20.5c0 .28.22.5.5.5l.16-.03L9 18.9l6 2.1 5.64-1.9c.21-.07.36-.25.36-.48V3.5c0-.28-.22-.5-.5-.5zM15 19l-6-2.11V5l6 2.11V19z" />
              </svg>
              <p className="text-sm">Map view</p>
              <p className="text-xs mt-1 opacity-60">
                Plan a trip to see locations
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
