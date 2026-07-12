"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

const MAP_STYLE = "https://tiles.openfreemap.org/styles/positron";

/**
 * Click-to-place location input for the custom property form.
 * Coordinates are a model input the user supplies, not an API output.
 */
export function LocationPicker({
  value,
  onChange,
}: {
  value: { latitude: number; longitude: number } | null;
  onChange: (v: { latitude: number; longitude: number }) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const onChangeRef = useRef(onChange);

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const map = new maplibregl.Map({
      container,
      style: MAP_STYLE,
      center: [-3.7038, 40.4168],
      zoom: 10.5,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }));
    mapRef.current = map;

    map.on("click", (e) => {
      onChangeRef.current({
        latitude: Number(e.lngLat.lat.toFixed(6)),
        longitude: Number(e.lngLat.lng.toFixed(6)),
      });
    });

    return () => {
      markerRef.current = null;
      mapRef.current = null;
      map.remove();
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (!value) {
      markerRef.current?.remove();
      markerRef.current = null;
      return;
    }
    if (!markerRef.current) {
      const el = document.createElement("div");
      el.style.cssText =
        "width:20px;height:20px;border-radius:9999px;background:#14594a;border:3px solid #ffffff;box-shadow:0 2px 8px rgb(26 36 33/.35)";
      markerRef.current = new maplibregl.Marker({ element: el })
        .setLngLat([value.longitude, value.latitude])
        .addTo(map);
    } else {
      markerRef.current.setLngLat([value.longitude, value.latitude]);
    }
  }, [value]);

  return (
    <div className="space-y-1.5">
      <div
        ref={containerRef}
        className="h-[220px] w-full overflow-hidden rounded-lg border border-input"
        role="application"
        aria-label="Click the map to set the property location"
      />
      <p className="text-xs text-muted-foreground">
        {value
          ? `Location set: ${value.latitude.toFixed(5)}, ${value.longitude.toFixed(5)}`
          : "Click the map to place the property. Location is required."}
      </p>
    </div>
  );
}
