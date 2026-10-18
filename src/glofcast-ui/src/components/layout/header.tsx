'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Snowflake } from 'lucide-react';
import { StatusBadge } from '@/components/ui/status-badge';

interface HeaderProps {
  backendOnline?: boolean;
}

export function Header({ backendOnline = false }: HeaderProps) {
  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="fixed top-0 left-0 right-0 h-16 z-50 flex items-center justify-between px-6 backdrop-blur-xl bg-slate-900/80 border-b border-white/10"
    >
      <div className="flex items-center gap-3">
        <Snowflake className="h-6 w-6 text-sky-400" />
        <div className="flex flex-col">
          <span className="font-bold text-white text-lg leading-tight">GLOFCast</span>
          <span className="text-xs text-slate-400 font-medium">GLOF Command Center</span>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3 hidden md:flex">
          <StatusBadge status={backendOnline ? 'online' : 'offline'} label="CryoFormer" />
          <StatusBadge status={backendOnline ? 'online' : 'offline'} label="ThermoSeq" />
          <StatusBadge status={backendOnline ? 'online' : 'offline'} label="HydroFusion" />
        </div>
        
        <div className="h-6 w-px bg-white/10 hidden md:block"></div>
        
        <div className="flex items-center gap-2">
          <div
            className={`h-2 w-2 rounded-full ${
              backendOnline ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]' : 'bg-amber-400'
            }`}
          />
          <span
            className={`text-sm font-medium ${
              backendOnline ? 'text-emerald-400' : 'text-amber-400'
            }`}
          >
            {backendOnline ? 'FastAPI Gateway Live' : 'Autonomous Fallback'}
          </span>
        </div>
      </div>
    </motion.header>
  );
}
