"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  BookingProgress,
  ItineraryData,
  ToolCallInfo,
  TranscriptMessage,
  VoiceEvent,
} from "@/types/voice";
import {
  AudioPlayer,
  base64ToPcm,
  float32ToInt16,
  pcmToBase64,
  resample,
} from "@/utils/audio";

function getBackendUrls() {
  const apiOriginFromEnv = process.env.NEXT_PUBLIC_API_BASE_URL;
  const wsOriginFromEnv = process.env.NEXT_PUBLIC_WS_BASE_URL;
  let defaultApiOrigin = "http://localhost:8000";
  let defaultWsOrigin = "ws://localhost:8000";

  if (typeof window !== "undefined") {
    const host = window.location.hostname || "localhost";
    const apiProtocol = window.location.protocol === "https:" ? "https" : "http";
    const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
    defaultApiOrigin = `${apiProtocol}://${host}:8000`;
    defaultWsOrigin = `${wsProtocol}://${host}:8000`;
  }

  return {
    apiUrl: `${(apiOriginFromEnv || defaultApiOrigin).replace(/\/$/, "")}/api`,
    wsUrl: `${(wsOriginFromEnv || defaultWsOrigin).replace(/\/$/, "")}/ws/voice`,
  };
}

export type VoiceStateValue = "idle" | "responding" | "interrupted" | "finished";

export function useVoiceAgent(sessionId: string) {
  const backendUrlsRef = useRef(getBackendUrls());
  const connectRef = useRef<() => void>(() => {});
  const [isConnected, setIsConnected] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [messages, setMessages] = useState<TranscriptMessage[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCallInfo[]>([]);
  const [itinerary, setItinerary] = useState<ItineraryData | null>(null);
  const [lodLevel, setLodLevel] = useState(2);
  const [bookingProgress, setBookingProgress] = useState<BookingProgress | null>(null);
  const [voiceState, setVoiceState] = useState<VoiceStateValue>("idle");
  const [isMuted, setIsMuted] = useState(false);
  const [micLevel, setMicLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const playerRef = useRef<AudioPlayer | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const msgIdRef = useRef(0);
  const isMutedRef = useRef(false);
  const lastLevelUpdateAtRef = useRef(0);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const MAX_RECONNECT = 3;

  const addMessage = useCallback(
    (role: "user" | "assistant", text: string, is_final: boolean) => {
      const id = `msg-${msgIdRef.current++}`;
      setMessages((prev) => {
        // Update last message of same role if not final
        const last = prev[prev.length - 1];
        if (last && last.role === role && !last.is_final) {
          return [...prev.slice(0, -1), { ...last, text, is_final }];
        }
        return [...prev, { id, role, text, timestamp: Date.now(), is_final }];
      });
    },
    []
  );

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${backendUrlsRef.current.wsUrl}/${sessionId}`);

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
      reconnectAttemptRef.current = 0;
    };

    ws.onclose = (ev) => {
      setIsConnected(false);
      setIsListening(false);
      setMicLevel(0);
      if (ev.code !== 1000 && reconnectAttemptRef.current < MAX_RECONNECT) {
        reconnectAttemptRef.current++;
        const delay = 1000 * reconnectAttemptRef.current;
        setError(`Reconnecting (${reconnectAttemptRef.current}/${MAX_RECONNECT})...`);
        reconnectTimeoutRef.current = setTimeout(() => connectRef.current(), delay);
      } else if (ev.code !== 1000) {
        setError("Connection lost. Please reconnect.");
      }
    };

    ws.onerror = () => {
      setError("WebSocket connection failed");
      setIsConnected(false);
      setMicLevel(0);
    };

    ws.onmessage = (event) => {
      const data: VoiceEvent = JSON.parse(event.data);

      switch (data.type) {
        case "audio":
          if (data.data && playerRef.current) {
            const pcm = base64ToPcm(data.data);
            playerRef.current.play(pcm);
          }
          break;

        case "transcript":
          if (data.text) {
            addMessage(data.role || "assistant", data.text, data.is_final ?? true);
          }
          break;

        case "tool_call":
          setToolCalls((prev) => [
            ...prev.filter((t) => t.name !== data.name || t.status === "complete"),
            {
              name: data.name || "unknown",
              status: (data.status as "calling" | "complete") || "calling",
              input: data.input,
              result: data.result,
              timestamp: Date.now(),
            },
          ]);
          break;

        case "itinerary":
          if (data.data) {
            setItinerary(data.data as unknown as ItineraryData);
          }
          break;

        case "interruption":
          playerRef.current?.clearBuffer();
          break;

        case "booking_progress":
          setBookingProgress({
            step: data.step || "",
            screenshot: data.screenshot,
            status: (data.status as BookingProgress["status"]) || "searching",
          });
          break;

        case "voice_state":
          if (data.state) setVoiceState(data.state as VoiceStateValue);
          break;

        case "lod_change":
          if (data.level) setLodLevel(data.level);
          break;

        case "error":
          setError(data.message || "Unknown error");
          break;
      }
    };

    wsRef.current = ws;
  }, [sessionId, addMessage]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    reconnectAttemptRef.current = 0;
    wsRef.current?.close();
    wsRef.current = null;
    setIsConnected(false);
  }, []);

  const startListening = useCallback(async () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    try {
      // Init audio player for playback
      if (!playerRef.current) {
        playerRef.current = new AudioPlayer();
        await playerRef.current.init();
      }

      // Capture microphone
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      streamRef.current = stream;

      // Create audio processing pipeline
      const ctx = new AudioContext();
      audioCtxRef.current = ctx;
      const source = ctx.createMediaStreamSource(stream);
      const processor = ctx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

        const input = e.inputBuffer.getChannelData(0);
        const now = performance.now();
        if (now - lastLevelUpdateAtRef.current >= 80) {
          let sumSquares = 0;
          for (let i = 0; i < input.length; i++) {
            sumSquares += input[i] * input[i];
          }
          const rms = Math.sqrt(sumSquares / input.length);
          const nextLevel = isMutedRef.current ? 0 : Math.min(1, rms * 8);
          lastLevelUpdateAtRef.current = now;
          setMicLevel(nextLevel);
        }
        if (isMutedRef.current) return;

        // Resample from browser rate to 16kHz
        const resampled = resample(input, ctx.sampleRate, 16000);
        const pcm = float32ToInt16(resampled);
        const b64 = pcmToBase64(pcm);

        wsRef.current.send(
          JSON.stringify({ type: "audio", data: b64 })
        );
      };

      source.connect(processor);
      processor.connect(ctx.destination);
      setMicLevel(0);
      setIsListening(true);
    } catch (err) {
      setError(`Microphone access failed: ${err}`);
      setMicLevel(0);
    }
  }, []);

  const stopListening = useCallback(() => {
    processorRef.current?.disconnect();
    processorRef.current = null;
    audioCtxRef.current?.close();
    audioCtxRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setMicLevel(0);
    setIsListening(false);
  }, []);

  const sendText = useCallback(
    (text: string) => {
      addMessage("user", text, true);

      // Text chat is more reliable through the REST fallback than the live voice socket.
      fetch(`${backendUrlsRef.current.apiUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: sessionId }),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.reply) addMessage("assistant", data.reply, true);
        })
        .catch(() => {
          setError("Failed to send message. Please check your connection.");
        });
    },
    [addMessage, sessionId]
  );

  const toggleMute = useCallback(() => {
    setIsMuted((prev) => {
      isMutedRef.current = !prev;
      if (!prev) setMicLevel(0);
      return !prev;
    });
  }, []);

  const setLod = useCallback((level: number) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ type: "lod", level }));
  }, []);

  const cancelBooking = useCallback(() => {
    setBookingProgress(null);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      stopListening();
      playerRef.current?.close();
      disconnect();
    };
  }, [stopListening, disconnect]);

  return {
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
  };
}
