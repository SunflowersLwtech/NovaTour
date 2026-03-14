"use client";

import React, { useEffect, useRef, useState } from "react";
import type { Activity, ItineraryData } from "@/types/voice";

interface TripMapProps {
  itinerary: ItineraryData | null;
}

type LngLat = [number, number];
type MapStatus = "loading" | "ready" | "error" | "disabled";

interface MapLibreRasterSource {
  type: "raster";
  tiles: string[];
  tileSize: number;
  attribution: string;
}

interface MapLibreRasterLayer {
  id: string;
  type: "raster";
  source: string;
  minzoom: number;
  maxzoom: number;
}

interface MapLibreLineLayer {
  id: string;
  type: "line";
  source: string;
  layout: { "line-cap": "round"; "line-join": "round" };
  paint: {
    "line-color": string;
    "line-width": number;
    "line-opacity": number;
  };
}

interface MapLibreGeoJsonFeatureCollection {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    geometry: {
      type: "LineString";
      coordinates: LngLat[];
    };
    properties: Record<string, never>;
  }>;
}

interface MapLibreBounds {
  extend(coordinates: LngLat): void;
}

interface MapLibreMap {
  addControl(control: unknown): void;
  on(event: "load", handler: () => void): void;
  addSource(
    id: string,
    source: { type: "geojson"; data: MapLibreGeoJsonFeatureCollection }
  ): void;
  addLayer(layer: MapLibreLineLayer): void;
  getLayer(id: string): unknown;
  removeLayer(id: string): void;
  getSource(id: string): unknown;
  removeSource(id: string): void;
  fitBounds(
    bounds: MapLibreBounds,
    options: { padding: number; duration: number; maxZoom: number }
  ): void;
  remove(): void;
}

interface MapLibrePopup {
  setHTML(html: string): MapLibrePopup;
}

interface MapLibreMarker {
  setLngLat(coordinates: LngLat): MapLibreMarker;
  setPopup(popup: MapLibrePopup): MapLibreMarker;
  addTo(map: MapLibreMap): MapLibreMarker;
  remove(): void;
}

interface MapLibreNamespace {
  Map: new (options: {
    container: HTMLElement;
    style: {
      version: number;
      sources: Record<string, MapLibreRasterSource>;
      layers: MapLibreRasterLayer[];
    };
    center: LngLat;
    zoom: number;
    attributionControl: boolean;
  }) => MapLibreMap;
  NavigationControl: new (options: { showCompass: boolean }) => unknown;
  Popup: new (options: { offset: number; closeButton: boolean }) => MapLibrePopup;
  Marker: new (options: { element: HTMLElement }) => MapLibreMarker;
  LngLatBounds: new () => MapLibreBounds;
}

type RouteGeometry =
  | { type: "LineString"; coordinates: LngLat[] }
  | { type: "MultiLineString"; coordinates: LngLat[][] };

interface GeoapifyRouteResponse {
  features?: Array<{
    geometry?: RouteGeometry;
  }>;
}

const MAPLIBRE_JS = "https://unpkg.com/maplibre-gl@3.6.1/dist/maplibre-gl.js";
const MAPLIBRE_CSS = "https://unpkg.com/maplibre-gl@3.6.1/dist/maplibre-gl.css";
const DAY_COLORS = [
  "#3b82f6",
  "#22c55e",
  "#f97316",
  "#ef4444",
  "#a855f7",
  "#ec4899",
  "#14b8a6",
  "#eab308",
];

const EMPTY_STATE_STYLE: React.CSSProperties = {
  width: "100%",
  height: "100%",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  backgroundColor: "#1a1a2e",
  color: "#9ca3af",
  fontSize: "14px",
  borderRadius: "8px",
  padding: "16px",
  textAlign: "center",
};

const ensureScript = (src: string) =>
  new Promise<void>((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve();
      return;
    }

    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
    document.head.appendChild(script);
  });

const ensureCss = (href: string) => {
  if (document.querySelector(`link[href="${href}"]`)) return;

  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = href;
  document.head.appendChild(link);
};

const getMapLibre = (): MapLibreNamespace | null =>
  (window as Window & { maplibregl?: MapLibreNamespace }).maplibregl ?? null;

const getCoords = (activity: Activity): { lat: number; lng: number } | null => {
  const lat = activity.latitude;
  const lng = activity.longitude;

  if (
    typeof lat === "number" &&
    typeof lng === "number" &&
    Number.isFinite(lat) &&
    Number.isFinite(lng)
  ) {
    return { lat, lng };
  }

  return null;
};

const renderEmptyState = (message: string, color = "#9ca3af") => (
  <div style={{ ...EMPTY_STATE_STYLE, color }}>{message}</div>
);

export const TripMap: React.FC<TripMapProps> = ({ itinerary }) => {
  const apiKey = process.env.NEXT_PUBLIC_GEOAPIFY_API_KEY;
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markersRef = useRef<MapLibreMarker[]>([]);
  const routeLayerIds = useRef<string[]>([]);
  const [mapStatus, setMapStatus] = useState<MapStatus>(() =>
    apiKey ? "loading" : "disabled"
  );
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => {
    let cancelled = false;

    if (!apiKey) {
      console.warn("TripMap: NEXT_PUBLIC_GEOAPIFY_API_KEY is not set");
      return;
    }

    ensureCss(MAPLIBRE_CSS);

    const init = async () => {
      try {
        await ensureScript(MAPLIBRE_JS);
      } catch (error) {
        console.error("TripMap: Failed to load MapLibre GL JS", error);
        if (!cancelled) setMapStatus("error");
        return;
      }

      if (cancelled || !containerRef.current) return;

      const maplibregl = getMapLibre();
      if (!maplibregl) {
        if (!cancelled) setMapStatus("error");
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
              attribution:
                '&copy; <a href="https://www.geoapify.com/">Geoapify</a>',
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
        if (cancelled) return;
        setMapReady(true);
        setMapStatus("ready");
      });

      mapRef.current = map;
    };

    init();

    return () => {
      cancelled = true;
      markersRef.current.forEach((marker) => {
        try {
          marker.remove();
        } catch {
          // noop
        }
      });
      markersRef.current = [];

      try {
        mapRef.current?.remove();
      } catch {
        // noop
      }
      mapRef.current = null;
    };
  }, [apiKey]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;

    const maplibregl = getMapLibre();
    if (!maplibregl) return;

    const controller = new AbortController();

    markersRef.current.forEach((marker) => {
      try {
        marker.remove();
      } catch {
        // noop
      }
    });
    markersRef.current = [];

    routeLayerIds.current.forEach((id) => {
      if (!map.getLayer(id)) return;
      try {
        map.removeLayer(id);
      } catch {
        // noop
      }
    });
    routeLayerIds.current = [];

    if (map.getSource("trip-route")) {
      try {
        map.removeSource("trip-route");
      } catch {
        // noop
      }
    }

    if (!itinerary) {
      return () => {
        controller.abort();
      };
    }

    const allCoordActivities: Array<{
      activity: Activity;
      coords: { lat: number; lng: number };
      dayIndex: number;
    }> = [];

    itinerary.itinerary.forEach((dayPlan, dayIndex) => {
      dayPlan.activities.forEach((activity) => {
        const coords = getCoords(activity);
        if (!coords) return;
        allCoordActivities.push({ activity, coords, dayIndex });
      });
    });

    if (allCoordActivities.length === 0) {
      return () => {
        controller.abort();
      };
    }

    allCoordActivities.forEach(({ activity, coords, dayIndex }) => {
      const markerElement = document.createElement("div");
      markerElement.style.width = "16px";
      markerElement.style.height = "16px";
      markerElement.style.borderRadius = "50%";
      markerElement.style.backgroundColor =
        DAY_COLORS[dayIndex % DAY_COLORS.length];
      markerElement.style.border = "2.5px solid #ffffff";
      markerElement.style.boxShadow = "0 2px 6px rgba(0,0,0,0.4)";
      markerElement.style.cursor = "pointer";

      const popup = new maplibregl.Popup({ offset: 12, closeButton: false })
        .setHTML(
          `<div style="font-size:13px;color:#1f2937;padding:2px 4px;">` +
            `<strong>${activity.activity}</strong>` +
            (activity.time
              ? `<br/><span style="color:#6b7280;">${activity.time}</span>`
              : "") +
            `</div>`
        );

      const marker = new maplibregl.Marker({ element: markerElement })
        .setLngLat([coords.lng, coords.lat])
        .setPopup(popup)
        .addTo(map);

      markersRef.current.push(marker);
    });

    const bounds = new maplibregl.LngLatBounds();
    allCoordActivities.forEach(({ coords }) => {
      bounds.extend([coords.lng, coords.lat]);
    });

    try {
      map.fitBounds(bounds, { padding: 50, duration: 500, maxZoom: 15 });
    } catch {
      // noop
    }

    if (allCoordActivities.length >= 2 && apiKey) {
      const waypoints = allCoordActivities
        .map(({ coords }) => `${coords.lat},${coords.lng}`)
        .join("|");
      const routeUrl = `https://api.geoapify.com/v1/routing?waypoints=${waypoints}&mode=drive&apiKey=${apiKey}`;

      fetch(routeUrl, { signal: controller.signal })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`Routing API error: ${response.status}`);
          }
          return response.json() as Promise<GeoapifyRouteResponse>;
        })
        .then((data) => {
          const geometry = data.features?.[0]?.geometry;
          if (!geometry || !mapRef.current) return;

          const lineCoords =
            geometry.type === "LineString"
              ? geometry.coordinates
              : geometry.coordinates.flat();

          if (lineCoords.length === 0) return;

          const geojson: MapLibreGeoJsonFeatureCollection = {
            type: "FeatureCollection",
            features: [
              {
                type: "Feature",
                geometry: {
                  type: "LineString",
                  coordinates: lineCoords,
                },
                properties: {},
              },
            ],
          };

          map.addSource("trip-route", { type: "geojson", data: geojson });
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
        .catch((error: unknown) => {
          if (error instanceof Error && error.name === "AbortError") return;
          console.warn("TripMap: Failed to fetch route", error);
        });
    }

    return () => {
      controller.abort();
    };
  }, [apiKey, itinerary, mapReady]);

  if (!itinerary) {
    return renderEmptyState("No itinerary to display on map", "#6b7280");
  }

  if (mapStatus === "disabled") {
    return renderEmptyState(
      "Map unavailable. Set NEXT_PUBLIC_GEOAPIFY_API_KEY to enable routing.",
      "#6b7280"
    );
  }

  if (mapStatus === "error") {
    return renderEmptyState("Map failed to load.");
  }

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      {mapStatus === "loading" && (
        <div
          style={{
            ...EMPTY_STATE_STYLE,
            position: "absolute",
            inset: 0,
            zIndex: 10,
            color: "#9ca3af",
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
