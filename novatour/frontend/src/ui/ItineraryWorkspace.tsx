"use client";

import Image, { type ImageLoaderProps } from "next/image";
import type { ItineraryData } from "@/types/voice";

interface ItineraryWorkspaceProps {
  itinerary: ItineraryData | null;
}

const passthroughImageLoader = ({ src }: ImageLoaderProps) => src;

export function ItineraryWorkspace({ itinerary }: ItineraryWorkspaceProps) {
  if (!itinerary) {
    return (
      <div className="flex flex-col h-full items-center justify-center text-dim px-8">
        <svg
          className="w-12 h-12 mb-3 opacity-20"
          fill="currentColor"
          viewBox="0 0 24 24"
        >
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm4 18H6V4h7v5h5v11z" />
        </svg>
        <p className="text-sm font-medium text-secondary">No itinerary yet</p>
        <p className="text-xs mt-1">Ask NovaTour to plan a trip</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-surface">
      {/* Header */}
      <div className="px-5 py-4 border-b border-subtle">
        <h2 className="text-base font-bold text-primary">
          {itinerary.destination}
        </h2>
        <p className="text-xs text-secondary mt-0.5">
          {itinerary.days} day{itinerary.days > 1 ? "s" : ""}
          {itinerary.mock && (
            <span className="ml-2 text-warn">(mock data)</span>
          )}
        </p>
      </div>

      {/* Day plans */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {itinerary.itinerary.map((day) => (
          <div
            key={day.day}
            className="rounded-xl border border-subtle overflow-hidden bg-elevated"
          >
            {/* Day header */}
            <div className="px-4 py-2.5 border-b border-subtle bg-accent/5">
              <h3 className="text-sm font-semibold text-accent">
                Day {day.day}: {day.theme}
              </h3>
            </div>

            {/* Activities */}
            <div className="p-3 space-y-2">
              {day.activities.map((act, i) => (
                <div key={i} className="flex items-start gap-3 text-sm">
                  <span className="text-accent font-mono text-xs mt-0.5 w-12 shrink-0">
                    {act.time}
                  </span>
                  {act.photo_url && (
                    <Image
                      loader={passthroughImageLoader}
                      src={act.photo_url}
                      alt={act.activity}
                      width={48}
                      height={48}
                      className="w-12 h-12 rounded-lg object-cover shrink-0"
                      loading="lazy"
                      unoptimized
                      onError={(event) => {
                        event.currentTarget.style.display = "none";
                      }}
                    />
                  )}
                  <div className="min-w-0">
                    <p className="text-primary text-sm">{act.activity}</p>
                    <p className="text-xs text-dim mt-0.5">
                      {act.location} · {act.duration}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Budget */}
        {itinerary.budget_estimate && (
          <div className="rounded-xl border border-subtle p-4 bg-elevated">
            <h3 className="text-sm font-semibold text-primary mb-2">Budget</h3>
            <div className="grid grid-cols-2 gap-1.5 text-sm">
              {Object.entries(itinerary.budget_estimate).map(([key, val]) => (
                <div key={key} className="flex justify-between">
                  <span className="text-dim capitalize">{key}</span>
                  <span
                    className={
                      key === "total"
                        ? "text-accent font-semibold"
                        : "text-secondary"
                    }
                  >
                    {val}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
