'use client';

import { motion } from 'framer-motion';
import { ShieldAlert, Zap, Thermometer, Eye, AlertTriangle, Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { GlacialLake } from '@/lib/mock-data';
import { fetchCoordinateTelemetry } from '@/lib/api';
import type { SubModelScores } from '@/lib/api';

interface RiskPanelProps {
  lake: GlacialLake;
  backendOnline?: boolean;
}

function getRiskColorHex(score: number): string {
  if (score >= 0.7) return '#ef4444';
  if (score >= 0.4) return '#f59e0b';
  return '#22c55e';
}

function getRiskLabel(score: number): string {
  if (score >= 0.8) return 'IMMINENT RISK';
  if (score >= 0.7) return 'HIGH RISK';
  if (score >= 0.4) return 'ELEVATED';
  return 'STABLE';
}

export function RiskPanel({ lake, backendOnline = false }: RiskPanelProps) {
  const [displayScore, setDisplayScore] = useState(0);
  const [liveScores, setLiveScores] = useState<SubModelScores | null>(null);
  const [alertTriggered, setAlertTriggered] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Use live fusion score if available, otherwise use mock riskScore
  const targetScore = liveScores ? liveScores.fusion : lake.riskScore;
  const color = getRiskColorHex(targetScore);
  const label = getRiskLabel(targetScore);
  const isCritical = targetScore >= 0.7;

  // ── Fetch live HydroFusion fusion scores from backend ──────────────────────
  useEffect(() => {
    if (!backendOnline) return;

    setIsLoading(true);
    fetchCoordinateTelemetry(lake.lat, lake.lng, 30)
      .then((data) => {
        setLiveScores(data.risk_scores);
        setAlertTriggered(data.alert_triggered);
      })
      .catch(() => {
        // Fall back to mock scores
        setLiveScores(null);
      })
      .finally(() => setIsLoading(false));
  }, [backendOnline, lake.lat, lake.lng]);

  // Animate the score counting up
  useEffect(() => {
    setDisplayScore(0);
    const duration = 1500;
    const steps = 60;
    const increment = targetScore / steps;
    let current = 0;
    let step = 0;

    const timer = setInterval(() => {
      step++;
      current = Math.min(targetScore, increment * step);
      setDisplayScore(current);
      if (step >= steps) clearInterval(timer);
    }, duration / steps);

    return () => clearInterval(timer);
  }, [targetScore]);

  // SVG circular gauge
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (displayScore * circumference);

  // Sub-model score display values
  const cryoformerScore = liveScores ? liveScores.cryoformer : targetScore * 0.9;
  const thermoseqScore = liveScores ? liveScores.thermoseq : Math.min(1, targetScore * 1.05);
  const morphologicalScore = liveScores ? liveScores.morphological : targetScore * 0.85;

  return (
    <motion.div
      initial={{ y: -80, opacity: 0, scale: 0.9 }}
      animate={{ y: 0, opacity: 1, scale: 1 }}
      exit={{ y: -80, opacity: 0, scale: 0.9 }}
      transition={{ type: 'spring', damping: 25, stiffness: 300, delay: 0.1 }}
      className="absolute top-20 left-1/2 -translate-x-1/2 z-40"
    >
      <div className={`glass rounded-2xl p-5 ${isCritical ? 'risk-pulse-critical' : ''}`}>
        {/* Alert banner when hydrodynamic routing is triggered */}
        {alertTriggered && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            className="mb-3 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center gap-2"
          >
            <AlertTriangle size={14} className="text-red-400 flex-shrink-0" />
            <span className="text-[11px] text-red-300 font-medium">
              ⚠ ALERT: Risk score ≥ 0.85 — Hydrodynamic routing payload generated (r.avaflow)
            </span>
          </motion.div>
        )}

        <div className="flex items-center gap-6">
          {/* Circular gauge */}
          <div className="relative w-32 h-32 flex-shrink-0">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
              {/* Background track */}
              <circle
                cx="60"
                cy="60"
                r={radius}
                fill="none"
                stroke="rgba(255,255,255,0.06)"
                strokeWidth="8"
              />
              {/* Progress arc */}
              <circle
                cx="60"
                cy="60"
                r={radius}
                fill="none"
                stroke={color}
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                style={{ transition: 'stroke-dashoffset 0.1s ease-out' }}
              />
              {/* Glow effect */}
              <circle
                cx="60"
                cy="60"
                r={radius}
                fill="none"
                stroke={color}
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                opacity="0.3"
                filter="blur(6px)"
                style={{ transition: 'stroke-dashoffset 0.1s ease-out' }}
              />
            </svg>
            {/* Score text in center */}
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              {isLoading ? (
                <Loader2 size={24} className="animate-spin" style={{ color }} />
              ) : (
                <>
                  <span className="text-3xl font-bold font-mono" style={{ color }}>
                    {displayScore.toFixed(2)}
                  </span>
                  <span className="text-[10px] text-slate-500 uppercase tracking-widest">/ 1.00</span>
                </>
              )}
            </div>
          </div>

          {/* Risk details */}
          <div className="space-y-3">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <ShieldAlert size={16} style={{ color }} />
                <span
                  className="text-sm font-bold uppercase tracking-wider"
                  style={{ color }}
                >
                  {label}
                </span>
                {liveScores && (
                  <span className="flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                    <span className="h-1 w-1 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="text-[8px] text-emerald-400 font-bold uppercase">Live</span>
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400">
                {liveScores ? 'HydroFusion Fusion Score' : 'AI Fusion Risk Score'} for {lake.name}
              </p>
            </div>

            {/* Sub-model breakdown */}
            <div className="space-y-1.5">
              {/* CryoFormer */}
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-1.5">
                  <Zap size={10} className="text-sky-400" />
                  <span className="text-[11px] text-slate-400">CryoFormer</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-16 h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.min(100, cryoformerScore * 100)}%` }}
                      transition={{ delay: 0.5, duration: 1 }}
                      className="h-full bg-sky-400 rounded-full"
                    />
                  </div>
                  <span className="text-[11px] font-mono text-slate-400">
                    {cryoformerScore.toFixed(2)}
                  </span>
                </div>
              </div>
              {/* ThermoSeq */}
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-1.5">
                  <Thermometer size={10} className="text-amber-400" />
                  <span className="text-[11px] text-slate-400">ThermoSeq</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-16 h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.min(100, thermoseqScore * 100)}%` }}
                      transition={{ delay: 0.7, duration: 1 }}
                      className="h-full bg-amber-400 rounded-full"
                    />
                  </div>
                  <span className="text-[11px] font-mono text-slate-400">
                    {Math.min(1, thermoseqScore).toFixed(2)}
                  </span>
                </div>
              </div>
              {/* HydroFusion (Morphological + Fusion) */}
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-1.5">
                  <Eye size={10} className="text-teal-400" />
                  <span className="text-[11px] text-slate-400">HydroFusion</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-16 h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.min(100, targetScore * 100)}%` }}
                      transition={{ delay: 0.9, duration: 1 }}
                      className="h-full bg-teal-400 rounded-full"
                    />
                  </div>
                  <span className="text-[11px] font-mono text-slate-400">
                    {targetScore.toFixed(2)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
