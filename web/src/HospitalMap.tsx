import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FeatureCollection, MultiPolygon, Polygon, Position } from "geojson";
import {
  LngLatBounds,
  Map as MapLibreMap,
  Popup,
  type ExpressionSpecification,
  type GeoJSONSource,
  type LayerSpecification,
  type MapLayerMouseEvent,
  setWorkerUrl,
} from "maplibre-gl";
// maplibre-gl resolves its worker relative to its own module, which breaks once
// Vite pre-bundles it; point it at a Vite-managed copy of the worker instead.
import maplibreWorkerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import Accordion from "react-bootstrap/Accordion";
import CloseButton from "react-bootstrap/CloseButton";
import Modal from "react-bootstrap/Modal";

import positronLayers from "./data/positron_style.json";

setWorkerUrl(maplibreWorkerUrl);

// Assets in public/ are served relative to the app's base path.
const assetUrl = (path: string) =>
  new URL(import.meta.env.BASE_URL, window.location.href).href + path;

// Contiguous United States
const US_BOUNDS: [[number, number], [number, number]] = [
  [-124.8, 24.4], // southwest
  [-66.9, 49.4], // northeast
];

interface RegionProperties {
  osm_id: number;
  name: string;
  operator: string; // "UNKNOWN" when the hospital has no operator tag
  color: string;
}

type Regions = FeatureCollection<Polygon | MultiPolygon, RegionProperties>;

// Hospitals without an operator are highlighted individually (by osm_id, since
// names repeat across the country); everything else by its whole network.
type Selection = { key: "osm_id"; value: number } | { key: "operator"; value: string };

function selectionFor(properties: RegionProperties): Selection {
  return properties.operator === "UNKNOWN"
    ? { key: "osm_id", value: properties.osm_id }
    : { key: "operator", value: properties.operator };
}

const sameSelection = (a: Selection | null, b: Selection | null) =>
  a?.key === b?.key && a?.value === b?.value;

// While something is highlighted, regions with the "highlight" feature-state stay
// opaque and everything else is dimmed. Toggling the paint property only when a
// highlight starts/ends (and flipping feature-state otherwise) avoids re-evaluating
// the layer's paint on every mouse move.
const HIGHLIGHT_OPACITY: ExpressionSpecification = [
  "case",
  ["boolean", ["feature-state", "highlight"], false],
  0.5,
  0.1,
];
const DEFAULT_OPACITY = 0.5;

function fitSelection(map: MapLibreMap, regions: Regions, selection: Selection) {
  const bounds = new LngLatBounds();
  const extend = (coords: Position[]) =>
    coords.forEach(([lng, lat]) => bounds.extend([lng, lat]));

  for (const { geometry, properties } of regions.features) {
    if (properties[selection.key] !== selection.value) continue;
    const polygons =
      geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
    polygons.forEach((rings) => extend(rings[0]));
  }

  if (!bounds.isEmpty()) {
    map.fitBounds(bounds, { padding: 40 });
  }
}

// Built with DOM nodes (not HTML strings) since names come from OSM data.
function popupContent(rows: [label: string, value: string][]) {
  const container = document.createElement("div");
  for (const [label, value] of rows) {
    const labelEl = document.createElement("p");
    labelEl.textContent = label;
    const valueEl = document.createElement("p");
    valueEl.appendChild(document.createElement("b")).textContent = value;
    container.append(labelEl, valueEl);
  }
  return container;
}

function InfoModal({ show, onHide }: { show: boolean; onHide: () => void }) {
  return (
    <Modal show={show} onHide={onHide}>
      <Modal.Header closeButton>
        <Modal.Title>About</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <p>
          This project uses OpenStreetMap data to find all the hospitals in the United States
          and calculates a{" "}
          <a href="https://en.wikipedia.org/wiki/Voronoi_diagram" target="_blank" rel="noreferrer">
            voronoi diagram
          </a>{" "}
          to show the region that is closest to each hospital, representing a hospital's
          "territory".
        </p>
        <p>Regions are color-coded by the hospital network that runs the hospital.</p>
        <p>This shows which areas have more competition between hospital networks.</p>
        <p>
          For example, we can see the large swath of Southwest Virginia and East Tennessee
          which is operated by Ballad Health, which was recently featured in an{" "}
          <a
            href="https://kffhealthnews.org/news/article/ballad-health-er-wait-times-copa-monopoly-appalachia-hospitals/"
            target="_blank"
            rel="noreferrer"
          >
            article about increased ER wait times
          </a>
          .
        </p>
      </Modal.Body>
    </Modal>
  );
}

export default function HospitalMap() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [regions, setRegions] = useState<Regions | null>(null);
  const [showInfoModal, setShowInfoModal] = useState(false);
  const [showWipBanner, setShowWipBanner] = useState(true);

  // Load the (large) voronoi regions once; they feed both the map and the legend.
  useEffect(() => {
    const controller = new AbortController();
    fetch(assetUrl("data/regions.json"), { signal: controller.signal })
      .then((res) => res.json() as Promise<Regions>)
      .then(setRegions)
      .catch((err) => {
        if (err.name !== "AbortError") console.error("Failed to load regions", err);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!mapContainer.current) return;

    const map = new MapLibreMap({
      container: mapContainer.current,
      style: {
        version: 8,
        glyphs: assetUrl("glyphs/{fontstack}/{range}.pbf"),
        sources: {
          openmaptiles: {
            type: "vector",
            url: "https://planet-tiles.wcedmisten.dev/planet-2024-09-06.json",
            maxzoom: 14,
          },
          hospitals: {
            type: "geojson",
            data: assetUrl("data/hospitals_layer.json"),
          },
          // filled in once regions.json has loaded
          voronoi: {
            type: "geojson",
            data: { type: "FeatureCollection", features: [] },
            promoteId: "osm_id",
          },
        },
        layers: positronLayers as LayerSpecification[],
      },
      bounds: US_BOUNDS,
      minZoom: 2,
    });
    mapRef.current = map;
    let removed = false;

    // The style's hospital layers reference this icon by name.
    map.loadImage(assetUrl("hospital-solid.png")).then((image) => {
      // StrictMode/HMR may have torn the map down before the image loaded.
      if (removed) return;
      if (!map.hasImage("hospitalMarker")) map.addImage("hospitalMarker", image.data);
    });

    map.on("mouseenter", "voronoi", () => {
      map.getCanvas().style.cursor = "pointer";
    });

    return () => {
      removed = true;
      map.remove();
      mapRef.current = null;
    };
  }, []);

  const operatorIds = useMemo(() => {
    const index = new Map<string, number[]>();
    for (const { properties } of regions?.features ?? []) {
      const ids = index.get(properties.operator);
      if (ids) ids.push(properties.osm_id);
      else index.set(properties.operator, [properties.osm_id]);
    }
    return index;
  }, [regions]);

  const highlighted = useRef<Selection | null>(null);

  const setHighlight = useCallback(
    (map: MapLibreMap, selection: Selection | null) => {
      const previous = highlighted.current;
      if (sameSelection(previous, selection)) return;

      const idsFor = ({ key, value }: Selection) =>
        key === "osm_id" ? [value] : (operatorIds.get(value) ?? []);
      const setState = (selection: Selection, highlight: boolean) => {
        for (const id of idsFor(selection)) {
          map.setFeatureState({ source: "voronoi", id }, { highlight });
        }
      };

      if (previous) setState(previous, false);
      if (selection) setState(selection, true);
      if (!previous !== !selection) {
        map.setPaintProperty(
          "voronoi",
          "fill-opacity",
          selection ? HIGHLIGHT_OPACITY : DEFAULT_OPACITY,
        );
      }
      highlighted.current = selection;
    },
    [operatorIds],
  );

  const focus = useCallback(
    (map: MapLibreMap, regions: Regions, selection: Selection) => {
      setHighlight(map, selection);
      fitSelection(map, regions, selection);
    },
    [setHighlight],
  );

  // Push regions into the map and wire up hover/click once both exist.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !regions) return;

    const setData = () => (map.getSource("voronoi") as GeoJSONSource).setData(regions);
    if (map.isStyleLoaded()) setData();
    else map.once("load", setData);

    const onClick = (e: MapLayerMouseEvent) => {
      const properties = e.features?.[0]?.properties as RegionProperties | undefined;
      if (!properties) return;

      new Popup()
        .setLngLat(e.lngLat)
        .setDOMContent(
          popupContent([
            ["🏥 Hospital Name:", properties.name],
            ["🔗 Network:", properties.operator],
          ]),
        )
        .addTo(map);

      focus(map, regions, selectionFor(properties));
    };

    const onMouseMove = (e: MapLayerMouseEvent) => {
      const properties = e.features?.[0]?.properties as RegionProperties | undefined;
      if (properties) setHighlight(map, selectionFor(properties));
    };
    const onMouseLeave = () => {
      map.getCanvas().style.cursor = "";
      setHighlight(map, null);
    };

    map.on("click", "voronoi", onClick);
    map.on("mousemove", "voronoi", onMouseMove);
    map.on("mouseleave", "voronoi", onMouseLeave);
    return () => {
      map.off("click", "voronoi", onClick);
      map.off("mousemove", "voronoi", onMouseMove);
      map.off("mouseleave", "voronoi", onMouseLeave);
    };
  }, [regions, focus, setHighlight]);

  // Operators sorted by number of hospitals, largest networks first.
  const operators = useMemo(() => {
    const byOperator = new Map<string, { color: string; count: number }>();
    for (const { properties } of regions?.features ?? []) {
      if (properties.operator === "UNKNOWN") continue;
      const entry = byOperator.get(properties.operator);
      if (entry) entry.count++;
      else byOperator.set(properties.operator, { color: properties.color, count: 1 });
    }
    return [...byOperator].sort((a, b) => b[1].count - a[1].count || a[0].localeCompare(b[0]));
  }, [regions]);

  return (
    <main className="map-wrap">
      {showWipBanner && (
        <div className="wip-banner" role="status">
          <span>⚠️ Work in progress: this data is undergoing further validation.</span>
          <CloseButton aria-label="Dismiss" onClick={() => setShowWipBanner(false)} />
        </div>
      )}
      <InfoModal show={showInfoModal} onHide={() => setShowInfoModal(false)} />
      <div ref={mapContainer} className="map" />
      <div id="state-legend" className="legend">
        <Accordion>
          <Accordion.Item eventKey="0">
            <Accordion.Header>US Hospital Territory Map</Accordion.Header>
            <Accordion.Body>
              <p style={{ cursor: "pointer" }} onClick={() => setShowInfoModal(true)}>
                About ⓘ
              </p>
              <p>Hospital Operators (click to focus)</p>
              {!regions && <p>Loading…</p>}
              <div className="legend-group">
                {operators.map(([operator, { color, count }]) => (
                  <div
                    key={operator}
                    className="legend-element"
                    onClick={() =>
                      mapRef.current &&
                      regions &&
                      focus(mapRef.current, regions, { key: "operator", value: operator })
                    }
                  >
                    <span className="legend-color" style={{ backgroundColor: color }} />
                    {operator} ({count})
                  </div>
                ))}
              </div>
            </Accordion.Body>
          </Accordion.Item>
        </Accordion>
      </div>
    </main>
  );
}
