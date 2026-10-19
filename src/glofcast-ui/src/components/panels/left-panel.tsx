'use client';

import { motion } from 'framer-motion';
import { Satellite, Eye, EyeOff, MapPin, Mountain, Droplets, Clock, Cpu } from 'lucide-react';
import { useState } from 'react';
import type { GlacialLake } from '@/lib/mock-data';
import { StatusBadge } from '@/components/ui/status-badge';

interface LeftPanelProps {
  lake: GlacialLake;
  onClose: () => void;
}

export function LeftPanel({ lake, onClose }: LeftPanelProps) {
  const [showMask, setShowMask] = useState(false);

  return (
    <motion.div
      initial={{ x: -400, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: -400, opacity: 0 }}
      transition={{ type: 'spring', damping: 30, stiffness: 300 }}
      className="absolute top-20 left-4 z-30 w-80 panel-scroll"
    >
      <div className="glass rounded-2xl overflow-hidden">
        {/* Satellite imagery placeholder */}
        <div className="relative h-48 bg-gradient-to-br from-slate-800 via-slate-700 to-slate-900 overflow-hidden">
          {/* Simulated satellite view */}
          <div className="absolute inset-0 opacity-60">
            <div className="absolute inset-0" style={{
              background: `
                radial-gradient(ellipse at 45% 50%, rgba(56, 189, 248, 0.15) 0%, transparent 60%),
                radial-gradient(ellipse at 55% 45%, rgba(45, 212, 191, 0.1) 0%, transparent 50%),
                linear-gradient(180deg, rgba(15, 23, 42, 0.3) 0%, rgba(15, 23, 42, 0.8) 100%)
              `
            }} />
            {/* Lake body */}
            <svg className="absolute inset-0 w-full h-full" viewBox="0 0 320 192">
              <ellipse cx="160" cy="96" rx="60" ry="35" fill="rgba(56, 189, 248, 0.25)" stroke="rgba(56, 189, 248, 0.4)" strokeWidth="1" />
              {showMask && (
                <>
                  <ellipse cx="160" cy="96" rx="70" ry="42" fill="none" stroke="#ef4444" strokeWidth="2" strokeDasharray="4 4" opacity="0.8" />
                  <ellipse cx="160" cy="96" rx="60" ry="35" fill="rgba(239, 68, 68, 0.15)" stroke="#ef4444" strokeWidth="1.5" />
                  <text x="165" y="145" fill="#ef4444" fontSize="10" fontWeight="600" opacity="0.9">Expansion Zone</text>
                </>
              )}
            </svg>
          </div>

          {/* Labels */}
          <div className="absolute top-3 left-3 flex items-center gap-2">
            <Satellite size={14} className="text-sky-400" />
            <span className="text-xs text-sky-300 font-medium">Sentinel-2 Optical</span>
          </div>

          {/* Mask toggle */}
          <button
            onClick={() => setShowMask(!showMask)}
            className="absolute top-3 right-3 glass-light rounded-lg px-3 py-1.5 flex items-center gap-2 text-xs font-medium hover:bg-white/10 transition-colors"
          >
            {showMask ? <EyeOff size={12} /> : <Eye size={12} />}
            <span>{showMask ? 'Hide' : 'Show'} Mask</span>
          </button>

          <div className="absolute bottom-3 left-3 right-3 flex justify-between items-end">
            <span className="text-[10px] text-slate-400">HydroFusion Segmentation</span>
            <span className="text-[10px] text-slate-500">Last pass: 2h ago</span>
          </div>
        </div>

        {/* Lake info */}
        <div className="p-5 space-y-4">
          <div>
            <h3 className="text-lg font-bold text-white">{lake.name}</h3>
            <p className="text-sm text-slate-400">{lake.region}, {lake.country}</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="glass-light rounded-xl p-3">
              <div className="flex items-center gap-2 mb-1">
                <MapPin size={12} className="text-sky-400" />
                <span className="text-[10px] text-slate-500 uppercase tracking-wider">Coordinates</span>
              </div>
              <p className="text-sm text-white font-mono">
                {lake.lat.toFixed(3)}°, {lake.lng.toFixed(3)}°
              </p>
            </div>
            <div className="glass-light rounded-xl p-3">
              <div className="flex items-center gap-2 mb-1">
                <Mountain size={12} className="text-teal-400" />
                <span className="text-[10px] text-slate-500 uppercase tracking-wider">Elevation</span>
              </div>
              <p className="text-sm text-white font-mono">{lake.elevation.toLocaleString()}m</p>
            </div>
            <div className="glass-light rounded-xl p-3">
              <div className="flex items-center gap-2 mb-1">
                <Droplets size={12} className="text-blue-400" />
                <span className="text-[10px] text-slate-500 uppercase tracking-wider">Lake Area</span>
              </div>
              <p className="text-sm text-white font-mono">{lake.area} km²</p>
            </div>
            <div className="glass-light rounded-xl p-3">
              <div className="flex items-center gap-2 mb-1">
                <Clock size={12} className="text-amber-400" />
                <span className="text-[10px] text-slate-500 uppercase tracking-wider">Updated</span>
              </div>
              <p className="text-sm text-white font-mono">2h ago</p>
            </div>
          </div>

          {/* Model status */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Cpu size={14} className="text-slate-400" />
              <span className="text-xs text-slate-400 uppercase tracking-wider font-medium">Model Status</span>
            </div>
            <div className="space-y-2">
              <StatusBadge
                status={lake.modelStatus.cryoformer ? 'online' : 'offline'}
                label="CryoFormer — Ice Velocity"
              />
              <StatusBadge
                status={lake.modelStatus.thermoseq ? 'online' : 'offline'}
                label="ThermoSeq — Climate Model"
              />
              <StatusBadge
                status={lake.modelStatus.hydrofusion ? 'online' : 'offline'}
                label="HydroFusion — Risk Fusion"
              />
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-full py-2.5 rounded-xl text-sm font-medium text-slate-400 hover:text-white hover:bg-white/5 transition-all border border-white/5"
          >
            Close Panel
          </button>
        </div>
      </div>
    </motion.div>
  );
}
