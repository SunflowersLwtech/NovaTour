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
      <div className="flex flex-col h-full bg-gray-900 items-center justify-center text-gray-500">
        <svg className="w-16 h-16 mb-4 opacity-30" fill="currentColor" viewBox="0 0 24 24">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm4 18H6V4h7v5h5v11z" />
        </svg>
        <p className="text-sm">No itinerary yet</p>
        <p className="text-xs mt-1 opacity-60">
          Ask NovaTour to plan a trip!
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-gray-900">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-700">
        <h2 className="text-sm font-semibold text-gray-300">
          {itinerary.destination} — {itinerary.days} Days
        </h2>
        {itinerary.mock && (
          <span className="text-xs text-yellow-400">(Mock Data)</span>
        )}
      </div>

      {/* Day plans */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {itinerary.itinerary.map((day) => (
          <div
            key={day.day}
            className="bg-gray-800 rounded-lg overflow-hidden border border-gray-700"
          >
            {/* Day header */}
            <div className="px-4 py-2 bg-blue-900/30 border-b border-gray-700">
              <h3 className="text-sm font-semibold text-blue-300">
                Day {day.day}: {day.theme}
              </h3>
            </div>

            {/* Activities */}
            <div className="p-3 space-y-2">
              {day.activities.map((act, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 text-sm"
                >
                  <span className="text-blue-400 font-mono text-xs mt-0.5 w-12 flex-shrink-0">
                    {act.time}
                  </span>
                  {act.photo_url && (
                    <Image
                      loader={passthroughImageLoader}
                      src={act.photo_url}
                      alt={act.activity}
                      width={56}
                      height={56}
                      className="w-14 h-14 rounded object-cover flex-shrink-0"
                      loading="lazy"
                      unoptimized
                      onError={(event) => {
                        event.currentTarget.style.display = "none";
                      }}
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-gray-200">{act.activity}</p>
                    <p className="text-xs text-gray-500">
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
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <h3 className="text-sm font-semibold text-gray-300 mb-2">
              Budget Estimate
            </h3>
            <div className="grid grid-cols-2 gap-2 text-sm">
              {Object.entries(itinerary.budget_estimate).map(([key, val]) => (
                <div key={key} className="flex justify-between">
                  <span className="text-gray-400 capitalize">{key}</span>
                  <span
                    className={
                      key === "total"
                        ? "text-blue-300 font-semibold"
                        : "text-gray-300"
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
