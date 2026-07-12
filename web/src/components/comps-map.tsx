"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { ComparablesResponse } from "@/lib/api/client";
import { eur, km } from "@/lib/format";

const MAP_STYLE = "https://tiles.openfreemap.org/styles/positron";

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function popupHtml(params: {
  title: string;
  assetId: string;
  lines: string[];
}) {
  const rows = params.lines
    .map((line) => `<p style="margin:2px 0;font-size:12px;line-height:1.5;color:#3f4a46">${escapeHtml(line)}</p>`)
    .join("");
  return `
    <div style="padding:12px 14px;min-width:210px">
      <p style="margin:0 0 2px;font-size:13px;font-weight:600">${escapeHtml(params.title)}</p>
      <p style="margin:0 0 6px;font-family:var(--font-geist-mono),monospace;font-size:11px;color:#54605b;word-break:break-all">${escapeHtml(params.assetId)}</p>
      ${rows}
    </div>`;
}

/**
 * Subject property and the five comparables from the API payload, each
 * placed at its real coordinates with its real asset_id and price.
 */
export function CompsMap({ comparables }: { comparables: ComparablesResponse }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const points: [number, number][] = [];
    const map = new maplibregl.Map({
      container,
      style: MAP_STYLE,
      center: [-3.7038, 40.4168],
      zoom: 11,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }));

    const subjectLat = comparables.subject_latitude;
    const subjectLon = comparables.subject_longitude;
    if (typeof subjectLat === "number" && typeof subjectLon === "number") {
      const el = document.createElement("div");
      el.setAttribute("aria-label", "Subject property");
      el.style.cssText =
        "width:22px;height:22px;border-radius:9999px;background:#14594a;border:3px solid #ffffff;box-shadow:0 2px 8px rgb(26 36 33/.35);cursor:pointer";
      new maplibregl.Marker({ element: el })
        .setLngLat([subjectLon, subjectLat])
        .setPopup(
          new maplibregl.Popup({ offset: 16 }).setHTML(
            popupHtml({
              title: "Subject property",
              assetId:
                typeof comparables.asset_id === "string"
                  ? comparables.asset_id
                  : "custom property",
              lines: ["The property being valued."],
            })
          )
        )
        .addTo(map);
      points.push([subjectLon, subjectLat]);
    }

    for (const comp of comparables.comps) {
      if (typeof comp.latitude !== "number" || typeof comp.longitude !== "number") {
        continue;
      }
      const el = document.createElement("div");
      el.setAttribute("aria-label", `Comparable ${comp.asset_id}`);
      el.style.cssText =
        "padding:3px 9px;border-radius:9999px;background:#ffffff;border:1.5px solid #14594a;color:#14594a;font:600 11px var(--font-geist-sans),system-ui,sans-serif;box-shadow:0 2px 6px rgb(26 36 33/.18);white-space:nowrap;cursor:pointer";
      el.textContent = eur(comp.price);
      new maplibregl.Marker({ element: el })
        .setLngLat([comp.longitude, comp.latitude])
        .setPopup(
          new maplibregl.Popup({ offset: 14 }).setHTML(
            popupHtml({
              title: `Listed at ${eur(comp.price)}`,
              assetId: comp.asset_id,
              lines: [
                `${comp.area_m2} m2, ${comp.rooms} rooms, ${comp.bathrooms} bathrooms`,
                `${comp.property_type}${comp.neighborhood_name ? `, ${comp.neighborhood_name}` : ""}`,
                `${km(comp.distance_km)} from the subject`,
              ],
            })
          )
        )
        .addTo(map);
      points.push([comp.longitude, comp.latitude]);
    }

    if (points.length > 0) {
      const bounds = points.reduce(
        (b, p) => b.extend(p),
        new maplibregl.LngLatBounds(points[0], points[0])
      );
      map.fitBounds(bounds, { padding: 70, maxZoom: 15.5, duration: 0 });
    }

    return () => {
      map.remove();
    };
  }, [comparables]);

  return (
    <div
      ref={containerRef}
      className="h-[380px] w-full overflow-hidden rounded-lg border border-border"
      role="application"
      aria-label="Map of the subject property and its comparables"
    />
  );
}
