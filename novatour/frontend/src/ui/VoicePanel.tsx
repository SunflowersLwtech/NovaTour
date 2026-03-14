"use client";

interface VoicePanelProps {
  isConnected: boolean;
  isListening: boolean;
  isMuted: boolean;
  lodLevel: number;
  onConnect: () => void;
  onDisconnect: () => void;
  onStartListening: () => void;
  onStopListening: () => void;
  onSetLod: (level: number) => void;
  onToggleMute: () => void;
}

export function VoicePanel({
  isConnected,
  isListening,
  isMuted,
  lodLevel,
  onConnect,
  onDisconnect,
  onStartListening,
  onStopListening,
  onSetLod,
  onToggleMute,
}: VoicePanelProps) {
  return (
    <div className="flex items-center gap-4 px-6 py-3 bg-gray-900 border-b border-gray-700">
      {/* Logo */}
      <h1 className="text-xl font-bold text-white mr-4">
        Nova<span className="text-blue-400">Tour</span>
      </h1>

      {/* Connection */}
      <button
        onClick={isConnected ? onDisconnect : onConnect}
        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
          isConnected
            ? "bg-green-600 hover:bg-green-700 text-white"
            : "bg-gray-600 hover:bg-gray-500 text-white"
        }`}
      >
        {isConnected ? "Connected" : "Connect"}
      </button>

      {/* Mic Button */}
      <button
        onClick={isListening ? onStopListening : onStartListening}
        disabled={!isConnected}
        className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${
          isListening
            ? "bg-red-500 hover:bg-red-600 animate-pulse shadow-lg shadow-red-500/50"
            : isConnected
            ? "bg-blue-500 hover:bg-blue-600"
            : "bg-gray-600 cursor-not-allowed"
        }`}
      >
        <svg
          className="w-6 h-6 text-white"
          fill="currentColor"
          viewBox="0 0 24 24"
        >
          {isListening ? (
            <rect x="6" y="6" width="12" height="12" rx="2" />
          ) : (
            <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1 1.93c-3.94-.49-7-3.85-7-7.93h2c0 3.31 2.69 6 6 6s6-2.69 6-6h2c0 4.08-3.06 7.44-7 7.93V20h4v2H8v-2h4v-4.07z" />
          )}
        </svg>
      </button>

      {/* Mute Button */}
      <button
        onClick={onToggleMute}
        disabled={!isListening}
        className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${
          !isListening
            ? "bg-gray-700 cursor-not-allowed opacity-50"
            : isMuted
            ? "bg-yellow-600 hover:bg-yellow-700"
            : "bg-gray-600 hover:bg-gray-500"
        }`}
        title={isMuted ? "Unmute" : "Mute"}
      >
        <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
          {isMuted ? (
            <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z" />
          ) : (
            <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
          )}
        </svg>
      </button>

      {/* Status */}
      <span className="text-sm text-gray-400">
        {isMuted ? "Muted" : isListening ? "Listening..." : isConnected ? "Ready" : "Disconnected"}
      </span>

      {/* LOD Controls */}
      <div className="ml-auto flex items-center gap-2">
        <span className="text-xs text-gray-500">Detail:</span>
        {[1, 2, 3].map((level) => (
          <button
            key={level}
            onClick={() => onSetLod(level)}
            className={`w-8 h-8 rounded text-xs font-bold transition-colors ${
              lodLevel === level
                ? "bg-blue-500 text-white"
                : "bg-gray-700 text-gray-400 hover:bg-gray-600"
            }`}
          >
            {level}
          </button>
        ))}
      </div>
    </div>
  );
}
