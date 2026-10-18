'use client';

/**
 * GLOFCast — Glacier Map Component (Deliverable 1)
 * ====================================================
 * High-fidelity geospatial command center built with Leaflet + Turf.js.
 *
 * Features:
 *  1. Esri World Imagery satellite base layer (dark mode aesthetic)
 *  2. Organic lake mask polygons via Turf.js bezierSpline
 *  3. Topographic hazard cone (curved flood path) via Turf.js buffer
 *  4. Marker clustering with risk-colored glowing dots
 *  5. Click-anywhere custom analysis with procedural geometry
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MapPin, Layers, ZoomIn, ZoomOut, Crosshair, Eye, EyeOff } from 'lucide-react';
import type { GlacialLake } from '@/lib/mock-data';
import { createDynamicLake } from '@/lib/mock-data';
import dynamic from 'next/dynamic';

// ─── Risk color utilities ───────────────────────────────────────────────────

function getRiskColor(riskLevel: string): string {
  switch (riskLevel) {
    case 'critical': return '#ef4444';
    case 'high': return '#f59e0b';
    case 'medium': return '#38bdf8';
    case 'low': return '#22c55e';
    default: return '#94a3b8';
  }
}

function getRiskGlow(riskLevel: string): string {
  switch (riskLevel) {
    case 'critical': return '0 0 20px rgba(239, 68, 68, 0.6), 0 0 40px rgba(239, 68, 68, 0.2)';
    case 'high': return '0 0 15px rgba(245, 158, 11, 0.5), 0 0 30px rgba(245, 158, 11, 0.15)';
    case 'medium': return '0 0 10px rgba(56, 189, 248, 0.4)';
    case 'low': return '0 0 8px rgba(34, 197, 94, 0.3)';
    default: return 'none';
  }
}

function getRiskLabel(riskLevel: string): string {
  switch (riskLevel) {
    case 'critical': return 'CRITICAL';
    case 'high': return 'HIGH';
    case 'medium': return 'MEDIUM';
    case 'low': return 'LOW';
    default: return 'N/A';
  }
}

function worstRisk(levels: string[]): string {
  const order = ['critical', 'high', 'medium', 'low'];
  for (const level of order) {
    if (levels.includes(level)) return level;
  }
  return 'low';
}

function getMarkerSize(zoom: number): number {
  if (zoom >= 12) return 22;
  if (zoom >= 10) return 18;
  if (zoom >= 8) return 14;
  if (zoom >= 6) return 12;
  return 10;
}

function shouldShowLabel(zoom: number): boolean {
  return zoom >= 9;
}

// ─── Main component interfaces ──────────────────────────────────────────────

interface GlacierMapProps {
  lakes: GlacialLake[];
  selectedLake: GlacialLake | null;
  onSelectLake: (lake: GlacialLake) => void;
}

// ─── Map Implementation ─────────────────────────────────────────────────────

function MapImplementation({ lakes, selectedLake, onSelectLake }: GlacierMapProps) {
  const mapRef = useRef<L.Map | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const markersLayerRef = useRef<any>(null);
  const geoLayerRef = useRef<L.LayerGroup | null>(null); // For Turf.js overlays
  const [mapReady, setMapReady] = useState(false);
  const [currentZoom, setCurrentZoom] = useState(4);
  const [lakeCount, setLakeCount] = useState(0);
  const [clusteringEnabled, setClusteringEnabled] = useState(false);
  const [overlaysVisible, setOverlaysVisible] = useState(true);
  const [L, setL] = useState<typeof import('leaflet') | null>(null);
  const [turfModule, setTurfModule] = useState<typeof import('@/lib/turf-generators') | null>(null);

  // Dynamic import of leaflet and turf generators
  useEffect(() => {
    Promise.all([
      import('leaflet'),
      import('@/lib/turf-generators'),
    ]).then(([leaflet, turfGen]) => {
      setL(leaflet);
      setTurfModule(turfGen);
    });
  }, []);

  // Initialize the map
  useEffect(() => {
    if (!L || mapRef.current) return;

    delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: '',
      iconUrl: '',
      shadowUrl: '',
    });

    const map = L.map('glacier-map', {
      center: [33, 78],
      zoom: 4,
      minZoom: 2,
      maxZoom: 18,
      zoomControl: false,
      attributionControl: true,
      maxBoundsViscosity: 1.0,
    });

    map.getContainer().style.background = '#0a0f1e';

    // ── Esri World Imagery satellite tile layer ──────────────────────────
    L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      {
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP',
        maxZoom: 19,
      }
    ).addTo(map);

    // Semi-transparent label overlay for satellite readability
    L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
      {
        maxZoom: 19,
        opacity: 0.45,
      }
    ).addTo(map);

    // GeoJSON overlay layer group for Turf.js geometries
    const geoLayer = L.layerGroup().addTo(map);
    geoLayerRef.current = geoLayer;

    // MarkerCluster setup
    (async () => {
      try {
        await import('leaflet.markercluster');
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const LGlobal = L as any;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const MCG = LGlobal.MarkerClusterGroup || LGlobal.markerClusterGroup || (window as any).L?.MarkerClusterGroup;

        if (MCG) {
          const clusterGroup = new MCG({
            maxClusterRadius: 50,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false,
            zoomToBoundsOnClick: true,
            disableClusteringAtZoom: 12,
            animate: true,
            animateAddingMarkers: false,
            spiderfyDistanceMultiplier: 1.5,
            chunkedLoading: true,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            iconCreateFunction: (cluster: any) => {
              const childMarkers = cluster.getAllChildMarkers();
              const count = cluster.getChildCount();
              const riskLevels = childMarkers.map(
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                (m: any) => m._lakeData?.riskLevel || 'low'
              );
              const worst = worstRisk(riskLevels);
              const color = getRiskColor(worst);

              let size = 40;
              let fontSize = 13;
              if (count >= 100) { size = 60; fontSize = 15; }
              else if (count >= 50) { size = 52; fontSize = 14; }
              else if (count >= 10) { size = 44; fontSize = 13; }

              return L.divIcon({
                html: `
                  <div class="cluster-marker" style="
                    width: ${size}px;
                    height: ${size}px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 50%;
                    background: radial-gradient(circle at 35% 35%, ${color}dd, ${color}88);
                    border: 2px solid rgba(255,255,255,0.25);
                    box-shadow: 0 0 ${size * 0.6}px ${color}66, 0 0 ${size * 0.3}px ${color}33, inset 0 1px 1px rgba(255,255,255,0.15);
                    color: #fff;
                    font-size: ${fontSize}px;
                    font-weight: 700;
                    font-family: 'Inter', system-ui, sans-serif;
                    text-shadow: 0 1px 3px rgba(0,0,0,0.6);
                    cursor: pointer;
                    transition: transform 0.2s ease, box-shadow 0.2s ease;
                  ">
                    ${count}
                  </div>
                `,
                className: 'glofcast-cluster-icon',
                iconSize: L.point(size, size),
                iconAnchor: L.point(size / 2, size / 2),
              });
            },
          });
          map.addLayer(clusterGroup);
          markersLayerRef.current = clusterGroup;
          setClusteringEnabled(true);
        } else {
          throw new Error('MarkerClusterGroup constructor not found');
        }
      } catch (err) {
        console.warn('[GLOFCast] MarkerCluster fallback:', err);
        const fallbackLayer = L.layerGroup().addTo(map);
        markersLayerRef.current = fallbackLayer;
        setClusteringEnabled(false);
      }
    })();

    // Track zoom
    map.on('zoomend', () => {
      setCurrentZoom(map.getZoom());
    });

    // Click to analyze custom location
    let dynamicMarker: L.Marker | null = null;
    map.on('click', (e: L.LeafletMouseEvent) => {
      const { lat, lng } = e.latlng;

      if (dynamicMarker) {
        map.removeLayer(dynamicMarker);
      }

      const pinIcon = L.divIcon({
        className: 'custom-marker',
        html: `
          <div class="custom-pin-wrapper">
            <div class="custom-pin-dot"></div>
            <div class="custom-pin-ring"></div>
            <div class="custom-pin-label">📍 Custom Analysis</div>
          </div>
        `,
        iconSize: [26, 26],
        iconAnchor: [13, 13],
      });

      dynamicMarker = L.marker([lat, lng], { icon: pinIcon }).addTo(map);
      const dynamicLake = createDynamicLake(lat, lng);
      onSelectLake(dynamicLake);
    });

    mapRef.current = map;
    setCurrentZoom(map.getZoom());
    setMapReady(true);

    return () => {
      map.remove();
      mapRef.current = null;
      markersLayerRef.current = null;
      geoLayerRef.current = null;
    };
  }, [L, onSelectLake]);

  // ── Sync lake markers ─────────────────────────────────────────────────
  useEffect(() => {
    if (!L || !markersLayerRef.current || !mapRef.current) return;

    const zoom = mapRef.current.getZoom();
    const layer = markersLayerRef.current;
    layer.clearLayers();

    const markerSize = getMarkerSize(zoom);
    const showLabels = shouldShowLabel(zoom);

    lakes.forEach((lake) => {
      const color = getRiskColor(lake.riskLevel);
      const glow = getRiskGlow(lake.riskLevel);
      const pulseClass = lake.riskLevel === 'critical' ? 'risk-pulse-critical' : '';
      const riskLabel = getRiskLabel(lake.riskLevel);

      const labelHtml = showLabels
        ? `<div class="lake-marker-label">${lake.name}</div>`
        : '';

      const icon = L.divIcon({
        className: 'custom-marker',
        html: `
          <div class="lake-marker-wrapper" data-risk="${lake.riskLevel}">
            <div class="lake-marker-dot ${pulseClass}" style="
              width: ${markerSize}px;
              height: ${markerSize}px;
              background: radial-gradient(circle at 35% 35%, ${color}, ${color}bb);
              border: 2px solid rgba(255,255,255,0.7);
              border-radius: 50%;
              box-shadow: ${glow};
              cursor: pointer;
              transition: transform 0.15s ease;
            "></div>
            ${labelHtml}
          </div>
        `,
        iconSize: [markerSize, markerSize],
        iconAnchor: [markerSize / 2, markerSize / 2],
      });

      const marker = L.marker([lake.lat, lake.lng], { icon });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (marker as any)._lakeData = lake;

      const tooltipContent = `
        <div class="lake-tooltip">
          <div class="lake-tooltip-header">
            <span class="lake-tooltip-risk-badge" style="background: ${color}; box-shadow: 0 0 8px ${color}66;">${riskLabel}</span>
            <span class="lake-tooltip-name">${lake.name}</span>
          </div>
          <div class="lake-tooltip-meta">
            <span>📍 ${lake.region || 'Unknown'}</span>
            <span>⛰️ ${lake.elevation.toLocaleString()}m</span>
          </div>
          <div class="lake-tooltip-meta">
            <span>💧 ${(lake.areaKm2 ?? lake.area)?.toFixed(3)} km²</span>
            <span>⚠️ Risk: ${(lake.riskScore * 100).toFixed(0)}%</span>
          </div>
          <div class="lake-tooltip-footer">Click to analyze</div>
        </div>
      `;

      marker.bindTooltip(tooltipContent, {
        direction: 'top',
        offset: L.point(0, -(markerSize / 2 + 4)),
        className: 'glofcast-tooltip',
        opacity: 1,
      });

      marker.on('click', () => {
        onSelectLake(lake);
      });

      layer.addLayer(marker);
    });

    setLakeCount(lakes.length);
  }, [L, lakes, currentZoom, onSelectLake]);

  // ── Render Turf.js procedural overlays for selected lake ───────────────
  useEffect(() => {
    if (!L || !mapRef.current || !geoLayerRef.current || !turfModule) return;

    const geoLayer = geoLayerRef.current;
    geoLayer.clearLayers();

    if (!selectedLake || !overlaysVisible) return;

    const center: [number, number] = [selectedLake.lng, selectedLake.lat];
    const areaKm2 = selectedLake.areaKm2 ?? selectedLake.area;

    try {
      // 1. Generate and render organic lake mask
      const lakeMask = turfModule.generateOrganicLakeMask(center, areaKm2);

      L.geoJSON(lakeMask, {
        style: {
          color: '#00e5ff',
          weight: 2.5,
          opacity: 0.9,
          fillColor: '#00e5ff',
          fillOpacity: 0.12,
          dashArray: '',
          className: 'lake-mask-glow',
        },
      }).addTo(geoLayer);

      // Inner glow ring (slightly smaller)
      L.geoJSON(lakeMask, {
        style: {
          color: '#00e5ff',
          weight: 0.8,
          opacity: 0.4,
          fillColor: '#00bcd4',
          fillOpacity: 0.06,
          dashArray: '4 2',
        },
      }).addTo(geoLayer);

      // 2. Generate and render hazard cone (flood path)
      const hazardCone = turfModule.generateHazardCone(center, areaKm2);

      L.geoJSON(hazardCone, {
        style: {
          color: '#ff1744',
          weight: 2,
          opacity: 0.8,
          fillColor: '#ff1744',
          fillOpacity: 0.15,
          dashArray: '8 4 2 4',
          className: 'hazard-cone-glow',
        },
      }).addTo(geoLayer);

      // Inner hazard gradient (semi-transparent red fill)
      L.geoJSON(hazardCone, {
        style: {
          color: 'transparent',
          weight: 0,
          fillColor: '#ff5252',
          fillOpacity: 0.08,
        },
      }).addTo(geoLayer);

      // 3. Flow centerline (dashed white line)
      const flowLine = turfModule.generateFlowCenterline(center, areaKm2);

      L.geoJSON(flowLine, {
        style: {
          color: '#ffffff',
          weight: 1.5,
          opacity: 0.35,
          dashArray: '6 6',
        },
      }).addTo(geoLayer);

      // Flow direction arrow markers along the centerline
      const flowCoords = flowLine.geometry.coordinates;
      const arrowStep = Math.max(1, Math.floor(flowCoords.length / 6));

      for (let i = arrowStep; i < flowCoords.length - 1; i += arrowStep) {
        const coord = flowCoords[i];
        const arrowIcon = L.divIcon({
          className: '',
          html: `<div style="
            color: rgba(255, 23, 68, 0.6);
            font-size: 10px;
            text-shadow: 0 0 6px rgba(255, 23, 68, 0.4);
            pointer-events: none;
          ">▼</div>`,
          iconSize: [12, 12],
          iconAnchor: [6, 6],
        });
        L.marker([coord[1], coord[0]], { icon: arrowIcon, interactive: false }).addTo(geoLayer);
      }

    } catch (err) {
      console.warn('[GLOFCast] Turf overlay generation error:', err);
    }
  }, [L, selectedLake, turfModule, overlaysVisible]);

  // Fly to selected lake
  useEffect(() => {
    if (!mapRef.current || !selectedLake) return;
    mapRef.current.flyTo([selectedLake.lat, selectedLake.lng], 10, {
      duration: 2,
    });
  }, [selectedLake]);

  // Map controls
  const handleZoomIn = useCallback(() => {
    mapRef.current?.zoomIn();
  }, []);

  const handleZoomOut = useCallback(() => {
    mapRef.current?.zoomOut();
  }, []);

  const handleResetView = useCallback(() => {
    mapRef.current?.flyTo([33, 78], 4, { duration: 1.5 });
  }, []);

  const toggleOverlays = useCallback(() => {
    setOverlaysVisible((prev) => !prev);
  }, []);

  return (
    <>
      <link
        rel="stylesheet"
        href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
        crossOrigin=""
      />
      <link
        rel="stylesheet"
        href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css"
        crossOrigin=""
      />
      <link
        rel="stylesheet"
        href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css"
        crossOrigin=""
      />
      <div id="glacier-map" className="absolute inset-0 z-0" style={{ width: '100%', height: '100%', background: '#0a0f1e' }} />

      {/* Map controls — bottom left */}
      <AnimatePresence>
        {mapReady && (
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3, duration: 0.4 }}
            className="absolute bottom-24 left-5 z-20 flex flex-col gap-1.5"
          >
            <button className="map-control-btn" onClick={handleZoomIn} title="Zoom In">
              <ZoomIn size={16} />
            </button>
            <button className="map-control-btn" onClick={handleZoomOut} title="Zoom Out">
              <ZoomOut size={16} />
            </button>
            <div className="w-full h-px bg-white/10 my-0.5" />
            <button className="map-control-btn" onClick={handleResetView} title="Reset View">
              <Crosshair size={16} />
            </button>
            <button className="map-control-btn" onClick={toggleOverlays} title="Toggle GIS Overlays">
              {overlaysVisible ? <Eye size={16} /> : <EyeOff size={16} />}
            </button>
            <button className="map-control-btn" title="Layers">
              <Layers size={16} />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Lake count + zoom status */}
      <AnimatePresence>
        {mapReady && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.4 }}
            className="absolute bottom-5 left-5 z-20"
          >
            <div className="glass rounded-lg px-3 py-2 flex items-center gap-3 text-xs">
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-slate-400">{lakeCount} lakes</span>
              </div>
              <div className="w-px h-3 bg-white/10" />
              <span className="text-slate-500">Zoom {currentZoom}</span>
              {clusteringEnabled && (
                <>
                  <div className="w-px h-3 bg-white/10" />
                  <span className="text-sky-400/60 text-[10px]">Clustered</span>
                </>
              )}
              {overlaysVisible && selectedLake && (
                <>
                  <div className="w-px h-3 bg-white/10" />
                  <span className="text-cyan-400/60 text-[10px]">GIS Active</span>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* GIS overlay legend — shown when overlays are active for selected lake */}
      <AnimatePresence>
        {mapReady && selectedLake && overlaysVisible && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ delay: 0.2, duration: 0.3 }}
            className="absolute bottom-20 right-5 z-20"
          >
            <div className="glass rounded-xl px-4 py-3">
              <div className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold mb-2">Procedural GIS Overlays</div>
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-1 rounded-full" style={{ background: '#00e5ff', boxShadow: '0 0 6px #00e5ff' }} />
                  <span className="text-[11px] text-cyan-300">Lake Boundary (Turf.js)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-1 rounded-full" style={{ background: '#ff1744', boxShadow: '0 0 6px #ff1744' }} />
                  <span className="text-[11px] text-red-300">Hazard Cone (Flow Path)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-0.5 rounded-full border-t border-dashed border-white/40" />
                  <span className="text-[11px] text-slate-400">Flow Centerline</span>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Risk legend — bottom right (no lake selected) */}
      <AnimatePresence>
        {mapReady && !selectedLake && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ delay: 0.4, duration: 0.4 }}
            className="absolute bottom-5 right-5 z-20"
          >
            <div className="glass rounded-xl px-4 py-3">
              <div className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold mb-2">Risk Level</div>
              <div className="flex flex-col gap-1.5">
                {[
                  { label: 'Critical', color: '#ef4444' },
                  { label: 'High', color: '#f59e0b' },
                  { label: 'Medium', color: '#38bdf8' },
                  { label: 'Low', color: '#22c55e' },
                ].map(({ label, color }) => (
                  <div key={label} className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ background: color, boxShadow: `0 0 6px ${color}66` }} />
                    <span className="text-[11px] text-slate-400">{label}</span>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Instruction overlay */}
      <AnimatePresence>
        {!selectedLake && mapReady && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="absolute bottom-5 left-1/2 -translate-x-1/2 z-20"
          >
            <div className="glass rounded-full px-6 py-3 flex items-center gap-3">
              <MapPin size={16} className="text-sky-400" />
              <span className="text-sm text-slate-300">
                Click anywhere on the map or select a lake marker to view risk analysis
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

// Dynamic import wrapper to prevent SSR
const GlacierMap = dynamic(() => Promise.resolve(MapImplementation), {
  ssr: false,
  loading: () => (
    <div className="absolute inset-0 bg-slate-950 flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 rounded-full border-2 border-sky-400/30 border-t-sky-400 animate-spin" />
        <span className="text-slate-400 text-sm">Loading map...</span>
      </div>
    </div>
  ),
});

export default GlacierMap;
export { getRiskColor };
