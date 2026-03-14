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

const WS_URL = "ws://localhost:8000/ws/voice";

export function useVoiceAgent(sessionId: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [messages, setMessages] = useState<TranscriptMessage[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCallInfo[]>([]);
  const [itinerary, setItinerary] = useState<ItineraryData | null>(null);
  const [lodLevel, setLodLevel] = useState(2);
  const [bookingProgress, setBookingProgress] = useState<BookingProgress | null>(null);
  const [isMuted, setIsMuted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const playerRef = useRef<AudioPlayer | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const msgIdRef = useRef(0);
  const isMutedRef = useRef(false);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
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

    const ws = new WebSocket(`${WS_URL}/${sessionId}`);

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
      reconnectAttemptRef.current = 0;
    };

    ws.onclose = (ev) => {
      setIsConnected(false);
      setIsListening(false);
      if (ev.code !== 1000 && reconnectAttemptRef.current < MAX_RECONNECT) {
        reconnectAttemptRef.current++;
        const delay = 1000 * reconnectAttemptRef.current;
        setError(`Reconnecting (${reconnectAttemptRef.current}/${MAX_RECONNECT})...`);
        reconnectTimeoutRef.current = setTimeout(() => connect(), delay);
      } else if (ev.code !== 1000) {
        setError("Connection lost. Please reconnect.");
      }
    };

    ws.onerror = () => {
      setError("WebSocket connection failed");
      setIsConnected(false);
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

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimeoutRef.current);
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
        if (isMutedRef.current) return;

        const input = e.inputBuffer.getChannelData(0);
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
      setIsListening(true);
    } catch (err) {
      setError(`Microphone access failed: ${err}`);
    }
  }, []);

  const stopListening = useCallback(() => {
    processorRef.current?.disconnect();
    processorRef.current = null;
    audioCtxRef.current?.close();
    audioCtxRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setIsListening(false);
  }, []);

  const sendText = useCallback(
    (text: string) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
      addMessage("user", text, true);
      wsRef.current.send(JSON.stringify({ type: "text", text }));
    },
    [addMessage]
  );

  const toggleMute = useCallback(() => {
    setIsMuted((prev) => {
      isMutedRef.current = !prev;
      return !prev;
    });
  }, []);

  const setLod = useCallback((level: number) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ type: "lod", level }));
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearTimeout(reconnectTimeoutRef.current);
      stopListening();
      playerRef.current?.close();
      disconnect();
    };
  }, [stopListening, disconnect]);

  return {
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
  };
}
