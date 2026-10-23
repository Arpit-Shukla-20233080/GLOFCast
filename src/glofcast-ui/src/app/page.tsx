'use client';

import { useState, useCallback, useEffect } from 'react';
import { AnimatePresence } from 'framer-motion';
import GlacierMap from '@/components/map/glacier-map';
import { Header } from '@/components/layout/header';
import { LeftPanel } from '@/components/panels/left-panel';
import { RightPanel } from '@/components/panels/right-panel';
import { RiskPanel } from '@/components/panels/risk-panel';
import { HistoricalValidationPanel } from '@/components/panels/historical-validation-panel';
import { GLACIAL_LAKES } from '@/lib/mock-data';
import type { GlacialLake } from '@/lib/mock-data';
import { fetchLakes, isBackendAvailable } from '@/lib/api';

export default function Home() {
  const [selectedLake, setSelectedLake] = useState<GlacialLake | null>(null);
  const [lakes, setLakes] = useState<GlacialLake[]>(GLACIAL_LAKES);
  const [backendOnline, setBackendOnline] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // ── On mount: attempt to load lakes from the FastAPI backend ──────────
  // Falls back to mock data if the backend is unreachable, ensuring the
  // UI always renders regardless of backend availability.
  useEffect(() => {
    async function loadLakes() {
      try {
        const online = await isBackendAvailable();
        setBackendOnline(online);

        if (online) {
          const response = await fetchLakes({ limit: 200 });
          if (response.lakes.length > 0) {
            setLakes(response.lakes);
          }
        }
      } catch {
        // Silently fall back to mock data
        console.warn('Backend unreachable — using mock data');
      } finally {
        setIsLoading(false);
      }
    }
    loadLakes();
  }, []);

  const handleSelectLake = useCallback((lake: GlacialLake) => {
    setSelectedLake(lake);
  }, []);

  const handleClose = useCallback(() => {
    setSelectedLake(null);
  }, []);

  return (
    <main className="relative w-screen h-screen overflow-hidden bg-slate-950">
      {/* Header — shows live/offline status based on backend connectivity */}
      <Header backendOnline={backendOnline} />

      {/* Full-screen map — renders with either live or mock lake data */}
      <GlacierMap
        lakes={lakes}
        selectedLake={selectedLake}
        onSelectLake={handleSelectLake}
      />

      {/* Panels — animate in/out when a lake is selected */}
      <AnimatePresence mode="wait">
        {selectedLake && (
          <>
            {/* Risk score — top center */}
            <RiskPanel
              key={`risk-${selectedLake.id}`}
              lake={selectedLake}
              backendOnline={backendOnline}
            />

            {/* Left panel — satellite & info */}
            <LeftPanel
              key={`left-${selectedLake.id}`}
              lake={selectedLake}
              onClose={handleClose}
            />

            {/* Right panel — charts (live data if backend online) */}
            <RightPanel
              key={`right-${selectedLake.id}`}
              lake={selectedLake}
              backendOnline={backendOnline}
            />

            {/* Historical validation panel — slides in for lakes with known GLOFs */}
            <HistoricalValidationPanel
              key={`hist-${selectedLake.id}`}
              lake={selectedLake}
            />
          </>
        )}
      </AnimatePresence>

      {/* Loading overlay during initial data fetch */}
      <AnimatePresence>
        {isLoading && (
          <div className="absolute inset-0 z-[100] bg-slate-950 flex items-center justify-center">
            <div className="flex flex-col items-center gap-4">
              <div className="w-16 h-16 rounded-full border-2 border-sky-400/30 border-t-sky-400 animate-spin" />
              <span className="text-slate-400 text-sm font-medium">Initializing GLOFCast Systems...</span>
              <span className="text-slate-500 text-xs">Loading CryoFormer · ThermoSeq · HydroFusion</span>
            </div>
          </div>
        )}
      </AnimatePresence>

      {/* Vignette overlay for depth effect */}
      <div
        className="absolute inset-0 pointer-events-none z-10"
        style={{
          background:
            'radial-gradient(ellipse at center, transparent 50%, rgba(10, 15, 30, 0.4) 100%)',
        }}
      />
    </main>
  );
}
