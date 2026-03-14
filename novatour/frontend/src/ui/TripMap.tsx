"use client";

import React, { useEffect, useRef, useState } from "react";
import type { ItineraryData, Activity } from "@/types/voice";

interface TripMapProps {
  itinerary: ItineraryData | null;
}

// MapLibre CDN URLs
const MAPLIBRE_JS = "https://unpkg.com/maplibre-gl@3.6.1/dist/maplibre-gl.js";
const MAPLIBRE_CSS = "https://unpkg.com/maplibre-gl@3.6.1/dist/maplibre-gl.css";

// Day colors for markers
const DAY_COLORS = ["#3b82f6", "#22c55e", "#f97316", "#ef4444", "#a855f7", "#ec4899", "#14b8a6", "#eab308"];

const ensureScript = (src: string) =>
  new Promise<void>((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) return resolve();
    const s = document.createElement("script");
    s.src = src;
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error(`Failed to load script: ${src}`));
    document.head.appendChild(s);
  });

const ensureCss = (href: string) => {
  if (document.querySelector(`link[href="${href}"]`)) return;
  const l = document.createElement("link");
  l.rel = "stylesheet";
  l.href = href;
  document.head.appendChild(l);
};

/** Extract lat/lng from an activity that may have coordinate fields */
const getCoords = (
  activity: Activity
): { lat: number; lng: number } | null => {
  const a = activity as Activity & { lat?: number; lng?: number; latitude?: number; longitude?: number };
  const lat = a.lat ?? a.latitude;
  const lng = a.lng ?? a.longitude;
  if (typeof lat === "number" && typeof lng === "number" && Number.isFinite(lat) && Number.isFinite(lng)) {
    return { lat, lng };
  }
  return null;
};

export const TripMap: React.FC<TripMapProps> = ({ itinerary }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const routeLayerIds = useRef<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [mapReady, setMapReady] = useState(false);

  // Initialize map
  useEffect(() => {
    let cancelled = false;
    const apiKey = process.env.NEXT_PUBLIC_GEOAPIFY_API_KEY;
    if (!apiKey) {
      console.warn("TripMap: NEXT_PUBLIC_GEOAPIFY_API_KEY is not set");
      setLoading(false);
      return;
    }

    ensureCss(MAPLIBRE_CSS);

    const init = async () => {
      try {
        await ensureScript(MAPLIBRE_JS);
      } catch (err) {
        console.error("TripMap: Failed to load MapLibre GL JS", err);
        setLoading(false);
        return;
      }

      if (cancelled || !containerRef.current) return;

      const maplibregl = (window as any).maplibregl;
      if (!maplibregl) {
        setLoading(false);
        return;
      }

      const tileUrl = `https://maps.geoapify.com/v1/tile/dark-matter-brown-purple/{z}/{x}/{y}.png?apiKey=${apiKey}`;

      const map = new maplibregl.Map({
        container: containerRef.current,
        style: {
          version: 8,
          sources: {
            "geoapify-tiles": {
              type: "raster",
              tiles: [tileUrl],
              tileSize: 256,
              attribution: '&copy; <a href="https://www.geoapify.com/">Geoapify</a>',
            },
          },
          layers: [
            {
              id: "geoapify-layer",
              type: "raster",
              source: "geoapify-tiles",
              minzoom: 0,
              maxzoom: 20,
            },
          ],
        },
        center: [0, 20],
        zoom: 2,
        attributionControl: false,
      });

      map.addControl(new maplibregl.NavigationControl({ showCompass: false }));
      map.on("load", () => {
        if (!cancelled) {
          setMapReady(true);
          setLoading(false);
        }
      });

      mapRef.current = map;
    };

    init();

    return () => {
      cancelled = true;
      setMapReady(false);
      setLoading(false);
      markersRef.current.forEach((m) => {
        try { m.remove(); } catch { /* noop */ }
      });
      markersRef.current = [];
      try { mapRef.current?.remove(); } catch { /* noop */ }
      mapRef.current = null;
    };
  }, []);

  // Update markers and route when itinerary changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;

    const maplibregl = (window as any).maplibregl;
    if (!maplibregl) return;

    const apiKey = process.env.NEXT_PUBLIC_GEOAPIFY_API_KEY;

    // Clear old markers
    markersRef.current.forEach((m) => {
      try { m.remove(); } catch { /* noop */ }
    });
    markersRef.current = [];

    // Clear old route layers/sources
    routeLayerIds.current.forEach((id) => {
      if (map.getLayer(id)) {
        try { map.removeLayer(id); } catch { /* noop */ }
      }
    });
    routeLayerIds.current = [];
    if (map.getSource("trip-route")) {
      try { map.removeSource("trip-route"); } catch { /* noop */ }
    }

    if (!itinerary) return;

    // Collect activities with coordinates, grouped by day
    const allCoordActivities: { activity: Activity; coords: { lat: number; lng: number }; dayIndex: number }[] = [];

    itinerary.itinerary.forEach((dayPlan, dayIdx) => {
      dayPlan.activities.forEach((activity) => {
        const coords = getCoords(activity);
        if (coords) {
          allCoordActivities.push({ activity, coords, dayIndex: dayIdx });
        }
      });
    });

    if (allCoordActivities.length === 0) return;

    // Add markers
    allCoordActivities.forEach(({ activity, coords, dayIndex }) => {
      const color = DAY_COLORS[dayIndex % DAY_COLORS.length];

      // Create marker element
      const el = document.createElement("div");
      el.style.width = "16px";
      el.style.height = "16px";
      el.style.borderRadius = "50%";
      el.style.backgroundColor = color;
      el.style.border = "2.5px solid #ffffff";
      el.style.boxShadow = "0 2px 6px rgba(0,0,0,0.4)";
      el.style.cursor = "pointer";

      const popup = new maplibregl.Popup({ offset: 12, closeButton: false })
        .setHTML(
          `<div style="font-size:13px;color:#1f2937;padding:2px 4px;">` +
          `<strong>${activity.activity}</strong>` +
          (activity.time ? `<br/><span style="color:#6b7280;">${activity.time}</span>` : "") +
          `</div>`
        );

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([coords.lng, coords.lat])
        .setPopup(popup)
        .addTo(map);

      markersRef.current.push(marker);
    });

    // Fit bounds to all markers
    const bounds = new maplibregl.LngLatBounds();
    allCoordActivities.forEach(({ coords }) => {
      bounds.extend([coords.lng, coords.lat]);
    });
    try {
      map.fitBounds(bounds, { padding: 50, duration: 500, maxZoom: 15 });
    } catch { /* noop */ }

    // Fetch route polyline if 2+ waypoints and API key available
    if (allCoordActivities.length >= 2 && apiKey) {
      const waypoints = allCoordActivities
        .map(({ coords }) => `${coords.lat},${coords.lng}`)
        .join("|");

      const routeUrl = `https://api.geoapify.com/v1/routing?waypoints=${waypoints}&mode=drive&apiKey=${apiKey}`;

      const controller = new AbortController();

      fetch(routeUrl, { signal: controller.signal })
        .then((res) => {
          if (!res.ok) throw new Error(`Routing API error: ${res.status}`);
          return res.json();
        })
        .then((data) => {
          const geometry = data?.features?.[0]?.geometry;
          if (!geometry) return;

          // Flatten coordinates (may be MultiLineString)
          let lineCoords: number[][] = [];
          if (geometry.type === "LineString") {
            lineCoords = geometry.coordinates;
          } else if (geometry.type === "MultiLineString") {
            lineCoords = geometry.coordinates.flat();
          }

          if (lineCoords.length === 0) return;

          // Check map is still alive
          if (!mapRef.current) return;

          const geojson = {
            type: "FeatureCollection" as const,
            features: [
              {
                type: "Feature" as const,
                geometry: { type: "LineString" as const, coordinates: lineCoords },
                properties: {},
              },
            ],
          };

          map.addSource("trip-route", { type: "geojson", data: geojson });

          // Outline layer for contrast
          map.addLayer({
            id: "trip-route-outline",
            type: "line",
            source: "trip-route",
            layout: { "line-cap": "round", "line-join": "round" },
            paint: {
              "line-color": "#ffffff",
              "line-width": 6,
              "line-opacity": 0.4,
            },
          });
          routeLayerIds.current.push("trip-route-outline");

          // Main route line
          map.addLayer({
            id: "trip-route-line",
            type: "line",
            source: "trip-route",
            layout: { "line-cap": "round", "line-join": "round" },
            paint: {
              "line-color": "#f97316",
              "line-width": 4,
              "line-opacity": 0.9,
            },
          });
          routeLayerIds.current.push("trip-route-line");
        })
        .catch((err) => {
          if ((err as Error).name === "AbortError") return;
          console.warn("TripMap: Failed to fetch route", err);
        });

      // Cleanup abort on unmount or re-render
      return () => {
        controller.abort();
      };
    }
  }, [itinerary, mapReady]);

  if (!itinerary) {
    return (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#1a1a2e",
          color: "#6b7280",
          fontSize: "14px",
          borderRadius: "8px",
        }}
      >
        No itinerary to display on map
      </div>
    );
  }

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      {loading && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            zIndex: 10,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "#1a1a2e",
            color: "#9ca3af",
            fontSize: "14px",
            borderRadius: "8px",
          }}
        >
          Loading map...
        </div>
      )}
      <div
        ref={containerRef}
        style={{ width: "100%", height: "100%", borderRadius: "8px" }}
      />
    </div>
  );
};

export default TripMap;
