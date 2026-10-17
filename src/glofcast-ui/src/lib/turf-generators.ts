'use client';

/**
 * GLOFCast — Turf.js Procedural Geometry Generators
 * ====================================================
 * High-fidelity procedural generation of organic lake boundaries
 * and realistic downstream flood path (hazard cone) polygons.
 *
 * These functions replace rigid geometric shapes with fluid, natural
 * GeoJSON geometries using Turf.js spatial operations.
 */

import * as turf from '@turf/turf';
import type { Feature, Polygon, LineString, Position } from 'geojson';

// ─── Deterministic seeded PRNG ──────────────────────────────────────────────
// Ensures identical geometry on every render for the same lake coordinates.

function seededRandom(seed: number): () => number {
  let s = seed;
  return () => {
    s = (s * 16807 + 0) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. ORGANIC LAKE MASK — Fluid glacial lake boundary
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Generate an organic, fluid lake boundary polygon using Turf.js.
 *
 * Method:
 * 1. Create a base ellipse from `circle()` with many vertices
 * 2. Apply multi-frequency Perlin-like noise to each vertex radially
 * 3. Smooth the jagged boundary with `bezierSpline()` for an organic look
 *
 * @param center - [lng, lat] of the lake center
 * @param areaKm2 - Lake surface area in km²
 * @returns GeoJSON Feature<Polygon> with organic boundary
 */
export function generateOrganicLakeMask(
  center: [number, number],
  areaKm2: number
): Feature<Polygon> {
  const rng = seededRandom(Math.abs(center[0] * 10000 + center[1] * 7777));

  // Compute equivalent radius from area (A = π·r²)
  const radiusKm = Math.sqrt(Math.max(0.01, areaKm2) / Math.PI);
  // Clamp to a visually meaningful range for the map
  const effectiveRadius = Math.max(0.15, Math.min(radiusKm * 1.2, 5));

  const numVertices = 64;
  const baseCircle = turf.circle(center, effectiveRadius, {
    steps: numVertices,
    units: 'kilometers',
  });

  // Extract ring coordinates (excluding the closing point)
  const coords = baseCircle.geometry.coordinates[0].slice(0, -1);

  // Apply multi-frequency geometric noise to create organic deformation
  // Three octaves of noise at different frequencies for natural appearance
  const noisyCoords: Position[] = coords.map((coord, i) => {
    const angle = (i / numVertices) * Math.PI * 2;

    // Three noise octaves for organic feel
    const n1 = Math.sin(angle * 3 + rng() * 6.28) * 0.22; // Low freq: major lobes
    const n2 = Math.sin(angle * 7 + rng() * 6.28) * 0.10; // Med freq: indentations
    const n3 = Math.sin(angle * 13 + rng() * 6.28) * 0.04; // High freq: micro-roughness

    const deformation = 1 + n1 + n2 + n3;

    // Add slight elliptical bias (most real glacial lakes are elongated)
    const ellipticBias = 1 + 0.2 * Math.cos(angle * 2 + rng() * 3.14);

    const dx = (coord[0] - center[0]) * deformation * ellipticBias;
    const dy = (coord[1] - center[1]) * deformation;

    return [center[0] + dx, center[1] + dy];
  });

  // Close the ring
  noisyCoords.push(noisyCoords[0]);

  // Create a line from the noisy ring for bezier smoothing
  const noisyLine = turf.lineString(noisyCoords);

  // Smooth with bezierSpline for fluid organic curves
  const smoothedLine = turf.bezierSpline(noisyLine, {
    resolution: 15000, // High resolution for smooth curves
    sharpness: 0.75,
  });

  // Close the smoothed line back into a polygon
  const smoothedCoords = smoothedLine.geometry.coordinates;
  // Ensure closure
  if (
    smoothedCoords[0][0] !== smoothedCoords[smoothedCoords.length - 1][0] ||
    smoothedCoords[0][1] !== smoothedCoords[smoothedCoords.length - 1][1]
  ) {
    smoothedCoords.push(smoothedCoords[0]);
  }

  return turf.polygon([smoothedCoords], {
    type: 'lake-mask',
    area_km2: areaKm2,
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. TOPOGRAPHIC HAZARD CONE — Downstream flood path polygon
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Simulate downslope flow direction from a lake center.
 *
 * Uses a deterministic heuristic based on coordinates:
 * - In the Himalayas (lat 27-36): flow tends south toward river valleys
 * - In the Andes (lat -10 to -5): flow tends west toward coastal valleys
 * - In Iceland (lat > 60): flow tends south toward lowlands
 * - Elsewhere: derive from coordinate hash for variety
 *
 * @returns bearing in degrees (0-360) for the downstream flow vector
 */
function estimateDownslopeBearing(center: [number, number]): number {
  const [lng, lat] = center;

  // Himalayan lakes: flow generally south to southeast
  if (lat >= 27 && lat <= 37 && lng >= 70 && lng <= 100) {
    return 160 + ((lng * 7 + lat * 3) % 40) - 20; // ~140°–200°
  }
  // Andean lakes: flow west-northwest
  if (lat >= -15 && lat <= -5 && lng >= -80 && lng <= -70) {
    return 280 + ((Math.abs(lng) * 5 + Math.abs(lat) * 2) % 30) - 15;
  }
  // Iceland: flow south toward coast
  if (lat >= 60 && lng >= -25 && lng <= -10) {
    return 180 + ((lng * 3 + lat * 7) % 20) - 10;
  }
  // General: use coordinate-based hash for deterministic bearing
  const hash = Math.abs(Math.sin(lat * 12345 + lng * 67890) * 180);
  return (hash + 120) % 360; // Biased away from north (glaciers rarely flow uphill north)
}

/**
 * Generate a realistic topographic flood hazard cone polygon.
 *
 * Instead of a rigid triangular sector, this creates a natural curved
 * flow path by:
 * 1. Computing a downslope flow bearing from topographic heuristics
 * 2. Creating a curved `lineString` with valley meander simulation
 * 3. Smoothing with `bezierSpline()` for natural hydrodynamic curves
 * 4. Expanding with `buffer()` to create a pill-shaped flood corridor
 *    with a widening downstream profile
 *
 * @param center - [lng, lat] of the glacial lake center
 * @param areaKm2 - Lake area for scale calculation
 * @returns GeoJSON Feature<Polygon> representing the hazard zone
 */
export function generateHazardCone(
  center: [number, number],
  areaKm2: number
): Feature<Polygon> {
  const rng = seededRandom(Math.abs(center[0] * 9999 + center[1] * 3333));

  // Scale the flow path length based on lake area (larger lake = longer runout)
  const baseLengthKm = Math.max(2, Math.min(15, Math.sqrt(areaKm2) * 6 + 3));
  const bearing = estimateDownslopeBearing(center);

  // Generate a multi-segment curved flow path
  // Simulate valley meander with 5-7 waypoints
  const numWaypoints = 6;
  const waypoints: Position[] = [center];

  let currentPoint = turf.point(center);
  let currentBearing = bearing;

  for (let i = 1; i <= numWaypoints; i++) {
    const progress = i / numWaypoints;

    // Each segment has slight bearing deviation (valley meander)
    const meander = (rng() - 0.5) * 25; // ±12.5° meander per segment
    currentBearing += meander;

    // Segment length increases downstream (accelerating flow fan-out)
    const segmentLength = (baseLengthKm / numWaypoints) * (0.8 + progress * 0.4);

    const nextPoint = turf.destination(currentPoint, segmentLength, currentBearing, {
      units: 'kilometers',
    });

    waypoints.push(nextPoint.geometry.coordinates);
    currentPoint = nextPoint;
  }

  // Create the raw flow path line
  const rawFlowLine = turf.lineString(waypoints);

  // Smooth with bezierSpline for natural hydrodynamic curves
  const smoothedFlowLine = turf.bezierSpline(rawFlowLine, {
    resolution: 10000,
    sharpness: 0.85,
  }) as Feature<LineString>;

  // Create a widening buffer along the flow path
  // The flood fan widens as it travels downstream, so we create
  // multiple buffer segments and union them.
  const flowCoords = smoothedFlowLine.geometry.coordinates;
  const totalPoints = flowCoords.length;
  const segmentSize = Math.max(1, Math.floor(totalPoints / 5));

  // Base buffer width scales with lake area
  const baseBufferKm = Math.max(0.15, Math.min(1.5, Math.sqrt(areaKm2) * 0.4));

  const bufferSegments: Feature<Polygon>[] = [];

  for (let seg = 0; seg < 5; seg++) {
    const startIdx = seg * segmentSize;
    const endIdx = Math.min((seg + 1) * segmentSize + 1, totalPoints);

    if (endIdx - startIdx < 2) continue;

    const segmentCoords = flowCoords.slice(startIdx, endIdx);
    const segmentLine = turf.lineString(segmentCoords);

    // Buffer width increases downstream (fan-out effect)
    const widthMultiplier = 0.6 + (seg / 4) * 1.4; // 0.6x → 2.0x
    const segmentBuffer = turf.buffer(segmentLine, baseBufferKm * widthMultiplier, {
      units: 'kilometers',
      steps: 16,
    });

    if (segmentBuffer && segmentBuffer.geometry.type === 'Polygon') {
      bufferSegments.push(segmentBuffer as Feature<Polygon>);
    }
  }

  // Union all buffer segments into a single smooth polygon
  if (bufferSegments.length === 0) {
    // Fallback: buffer the entire line
    const fallback = turf.buffer(smoothedFlowLine, baseBufferKm, {
      units: 'kilometers',
      steps: 16,
    });
    return (fallback as Feature<Polygon>) || turf.polygon([[[0, 0], [0, 1], [1, 1], [0, 0]]]);
  }

  let unionedPolygon: Feature<Polygon> = bufferSegments[0];
  for (let i = 1; i < bufferSegments.length; i++) {
    try {
      const result = turf.union(
        turf.featureCollection([unionedPolygon, bufferSegments[i]])
      );
      if (result && (result.geometry.type === 'Polygon' || result.geometry.type === 'MultiPolygon')) {
        if (result.geometry.type === 'MultiPolygon') {
          // Take the largest polygon from the MultiPolygon
          const largestRing = result.geometry.coordinates.reduce((a, b) =>
            a[0].length >= b[0].length ? a : b
          );
          unionedPolygon = turf.polygon(largestRing);
        } else {
          unionedPolygon = result as Feature<Polygon>;
        }
      }
    } catch {
      // Union can fail with complex geometries; continue with what we have
      continue;
    }
  }

  // Add metadata properties
  unionedPolygon.properties = {
    type: 'hazard-cone',
    bearing: bearing,
    length_km: baseLengthKm,
    area_km2: areaKm2,
  };

  return unionedPolygon;
}

/**
 * Generate the centerline of the flood flow path for rendering
 * as a dashed line overlay.
 */
export function generateFlowCenterline(
  center: [number, number],
  areaKm2: number
): Feature<LineString> {
  const rng = seededRandom(Math.abs(center[0] * 9999 + center[1] * 3333));
  const baseLengthKm = Math.max(2, Math.min(15, Math.sqrt(areaKm2) * 6 + 3));
  const bearing = estimateDownslopeBearing(center);

  const numWaypoints = 6;
  const waypoints: Position[] = [center];

  let currentPoint = turf.point(center);
  let currentBearing = bearing;

  for (let i = 1; i <= numWaypoints; i++) {
    const progress = i / numWaypoints;
    const meander = (rng() - 0.5) * 25;
    currentBearing += meander;
    const segmentLength = (baseLengthKm / numWaypoints) * (0.8 + progress * 0.4);

    const nextPoint = turf.destination(currentPoint, segmentLength, currentBearing, {
      units: 'kilometers',
    });

    waypoints.push(nextPoint.geometry.coordinates);
    currentPoint = nextPoint;
  }

  const rawLine = turf.lineString(waypoints);
  return turf.bezierSpline(rawLine, {
    resolution: 10000,
    sharpness: 0.85,
  }) as Feature<LineString>;
}
