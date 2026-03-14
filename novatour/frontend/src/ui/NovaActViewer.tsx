"use client";

import Image, { type ImageLoaderProps } from "next/image";
import { useState } from "react";

interface BookingProgress {
  step: string;
  screenshot?: string;
  status: "searching" | "found" | "booking" | "complete" | "error";
}

interface NovaActViewerProps {
  bookingProgress: BookingProgress | null;
  onCancel?: () => void;
}

const passthroughImageLoader = ({ src }: ImageLoaderProps) => src;

export function NovaActViewer({
  bookingProgress,
  onCancel,
}: NovaActViewerProps) {
  const [expanded, setExpanded] = useState(true);

  if (!bookingProgress) return null;

  return (
    <div className="fixed bottom-4 right-4 w-96 bg-gray-800 rounded-lg border border-gray-600 shadow-2xl overflow-hidden z-50">
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-2 bg-gray-700 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              bookingProgress.status === "complete"
                ? "bg-green-400"
                : bookingProgress.status === "error"
                ? "bg-red-400"
                : "bg-yellow-400 animate-pulse"
            }`}
          />
          <span className="text-sm font-medium text-white">
            Nova Act — Booking
          </span>
        </div>
        <div className="flex items-center gap-2">
          {bookingProgress.status !== "complete" &&
            bookingProgress.status !== "error" &&
            onCancel && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onCancel();
                }}
                className="text-xs text-red-400 hover:text-red-300"
              >
                Cancel
              </button>
            )}
          <span className="text-gray-400 text-xs">
            {expanded ? "▼" : "▲"}
          </span>
        </div>
      </div>

      {/* Content */}
      {expanded && (
        <div className="p-4">
          {/* Screenshot */}
          {bookingProgress.screenshot && (
            <div className="mb-3 rounded overflow-hidden border border-gray-600">
              <Image
                loader={passthroughImageLoader}
                src={bookingProgress.screenshot}
                alt="Booking progress"
                width={1200}
                height={675}
                className="w-full h-auto"
                unoptimized
              />
            </div>
          )}

          {/* Status */}
          <p className="text-sm text-gray-300">{bookingProgress.step}</p>

          {/* Progress bar */}
          <div className="mt-3 h-1 bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                bookingProgress.status === "complete"
                  ? "w-full bg-green-500"
                  : bookingProgress.status === "error"
                  ? "w-full bg-red-500"
                  : "w-2/3 bg-blue-500 animate-pulse"
              }`}
            />
          </div>
        </div>
      )}
    </div>
  );
}
