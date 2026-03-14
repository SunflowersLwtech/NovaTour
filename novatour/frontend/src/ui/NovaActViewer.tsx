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
    <div className="fixed bottom-4 right-4 w-96 bg-elevated rounded-xl border border-subtle shadow-2xl overflow-hidden z-50">
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-2.5 bg-surface cursor-pointer border-b border-subtle"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              bookingProgress.status === "complete"
                ? "bg-ok"
                : bookingProgress.status === "error"
                ? "bg-err"
                : "bg-warn pulse-dot"
            }`}
          />
          <span className="text-sm font-semibold text-primary">
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
                className="text-xs text-err hover:text-err/80 font-medium"
              >
                Cancel
              </button>
            )}
          <span className="text-dim text-xs">
            {expanded ? "▼" : "▲"}
          </span>
        </div>
      </div>

      {/* Content */}
      {expanded && (
        <div className="p-4">
          {bookingProgress.screenshot && (
            <div className="mb-3 rounded-lg overflow-hidden border border-subtle">
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

          <p className="text-sm text-secondary">{bookingProgress.step}</p>

          <div className="mt-3 h-1 bg-subtle rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                bookingProgress.status === "complete"
                  ? "w-full bg-ok"
                  : bookingProgress.status === "error"
                  ? "w-full bg-err"
                  : "w-2/3 bg-accent pulse-dot"
              }`}
            />
          </div>
        </div>
      )}
    </div>
  );
}
