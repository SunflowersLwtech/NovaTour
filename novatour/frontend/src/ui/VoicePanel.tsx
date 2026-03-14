"use client";

interface VoicePanelProps {
  isConnected: boolean;
  isListening: boolean;
  lodLevel: number;
  onConnect: () => void;
  onDisconnect: () => void;
  onStartListening: () => void;
  onStopListening: () => void;
  onSetLod: (level: number) => void;
}

export function VoicePanel({
  isConnected,
  isListening,
  lodLevel,
  onConnect,
  onDisconnect,
  onStartListening,
  onStopListening,
  onSetLod,
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

      {/* Status */}
      <span className="text-sm text-gray-400">
        {isListening ? "Listening..." : isConnected ? "Ready" : "Disconnected"}
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
