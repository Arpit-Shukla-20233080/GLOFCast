'use client';

import { motion } from 'framer-motion';
import { Activity, Thermometer, TrendingUp, TrendingDown, Loader2 } from 'lucide-react';
import { useState, useMemo, useEffect } from 'react';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
  ReferenceLine,
} from 'recharts';
import { generateVelocityData, generateTemperatureData } from '@/lib/mock-data';
import type { GlacialLake, TimeSeriesPoint } from '@/lib/mock-data';
import { fetchVelocityPrediction, fetchTemperaturePrediction } from '@/lib/api';
import { ChartSkeleton } from '@/components/ui/loading-skeleton';

interface RightPanelProps {
  lake: GlacialLake;
  backendOnline?: boolean;
}

type TimeRange = '7d' | '30d' | '90d';

const timeRangeMap: Record<TimeRange, number> = {
  '7d': 7,
  '30d': 30,
  '90d': 90,
};

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number; name: string; color: string }>; label?: string }) {
  if (!active || !payload?.length) return null;

  return (
    <div className="glass rounded-lg p-3 min-w-[160px]">
      <p className="text-xs text-slate-400 mb-1.5">{label}</p>
      {payload.map((entry, idx) => (
        <p key={idx} className="text-sm font-mono font-medium" style={{ color: entry.color }}>
          {entry.value.toFixed(2)} {entry.name === 'velocity' ? 'm/yr' : '°C'}
        </p>
      ))}
    </div>
  );
}

export function RightPanel({ lake, backendOnline = false }: RightPanelProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>('30d');
  const [liveVelocityData, setLiveVelocityData] = useState<TimeSeriesPoint[] | null>(null);
  const [liveTemperatureData, setLiveTemperatureData] = useState<TimeSeriesPoint[] | null>(null);
  const [isLoadingVel, setIsLoadingVel] = useState(false);
  const [isLoadingTemp, setIsLoadingTemp] = useState(false);

  // ── Fetch live data from backend when available ─────────────────────────
  useEffect(() => {
    if (!backendOnline) return;

    const days = timeRangeMap[timeRange];

    setIsLoadingVel(true);
    setIsLoadingTemp(true);

    fetchVelocityPrediction(lake.lat, lake.lng, days)
      .then((data) => setLiveVelocityData(data))
      .catch(() => setLiveVelocityData(null))
      .finally(() => setIsLoadingVel(false));

    fetchTemperaturePrediction(lake.lat, lake.lng, days)
      .then((data) => setLiveTemperatureData(data))
      .catch(() => setLiveTemperatureData(null))
      .finally(() => setIsLoadingTemp(false));
  }, [backendOnline, lake.lat, lake.lng, timeRange]);

  // ── Use live data if available, fall back to mock ───────────────────────
  const velocityData = useMemo(() => {
    if (liveVelocityData && liveVelocityData.length > 0) return liveVelocityData;
    return generateVelocityData(timeRangeMap[timeRange]);
  }, [liveVelocityData, timeRange]);

  const temperatureData = useMemo(() => {
    if (liveTemperatureData && liveTemperatureData.length > 0) return liveTemperatureData;
    return generateTemperatureData(timeRangeMap[timeRange]);
  }, [liveTemperatureData, timeRange]);

  // Calculate stats
  const velValues = velocityData.map((d) => d.value);
  const tempValues = temperatureData.map((d) => d.value);

  const velCurrent = velValues[velValues.length - 1];
  const velAvg = velValues.reduce((a, b) => a + b, 0) / velValues.length;
  const velTrend = velCurrent - velValues[0];

  const tempCurrent = tempValues[tempValues.length - 1];
  const tempAvg = tempValues.reduce((a, b) => a + b, 0) / tempValues.length;
  const tempTrend = tempCurrent - tempValues[0];

  const isLiveData = backendOnline && liveVelocityData !== null;

  return (
    <motion.div
      initial={{ x: 400, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 400, opacity: 0 }}
      transition={{ type: 'spring', damping: 30, stiffness: 300 }}
      className="absolute top-20 right-4 z-30 w-96 panel-scroll"
    >
      <div className="glass rounded-2xl overflow-hidden">
        {/* Header with time range selector */}
        <div className="p-4 pb-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider">
              Kinematics & Climate
            </h3>
            {/* Live data indicator */}
            {isLiveData && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-[9px] text-emerald-400 font-medium uppercase">Live</span>
              </span>
            )}
          </div>
          <div className="flex gap-1 glass-light rounded-lg p-1">
            {(['7d', '30d', '90d'] as TimeRange[]).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                  timeRange === range
                    ? 'bg-sky-500/20 text-sky-400'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                {range}
              </button>
            ))}
          </div>
        </div>

        {/* CryoFormer — Ice Velocity Chart */}
        <div className="px-4 pt-2 pb-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Activity size={14} className="text-sky-400" />
              <span className="text-xs text-slate-400 font-medium">CryoFormer — Ice Velocity</span>
            </div>
            <div className="flex items-center gap-1.5">
              {isLoadingVel ? (
                <Loader2 size={12} className="text-sky-400 animate-spin" />
              ) : velTrend > 0 ? (
                <TrendingUp size={12} className="text-red-400" />
              ) : (
                <TrendingDown size={12} className="text-green-400" />
              )}
              <span className={`text-xs font-mono ${velTrend > 0 ? 'text-red-400' : 'text-green-400'}`}>
                {velTrend > 0 ? '+' : ''}{velTrend.toFixed(1)} m/yr
              </span>
            </div>
          </div>

          {/* Velocity stats */}
          <div className="grid grid-cols-3 gap-2 mb-3">
            <div className="glass-light rounded-lg p-2 text-center">
              <p className="text-[10px] text-slate-500 uppercase">Current</p>
              <p className="text-sm font-mono font-bold text-sky-400">{velCurrent.toFixed(1)}</p>
            </div>
            <div className="glass-light rounded-lg p-2 text-center">
              <p className="text-[10px] text-slate-500 uppercase">Average</p>
              <p className="text-sm font-mono font-bold text-slate-300">{velAvg.toFixed(1)}</p>
            </div>
            <div className="glass-light rounded-lg p-2 text-center">
              <p className="text-[10px] text-slate-500 uppercase">Unit</p>
              <p className="text-sm font-mono font-bold text-slate-300">m/yr</p>
            </div>
          </div>

          {/* Velocity chart */}
          {isLoadingVel ? (
            <div className="h-36"><ChartSkeleton /></div>
          ) : (
            <div className="h-36 -mx-2">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={velocityData}>
                  <defs>
                    <linearGradient id="velGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 9, fill: '#64748b' }}
                    axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                    tickLine={false}
                    interval="preserveStartEnd"
                    tickFormatter={(val) => {
                      const d = new Date(val);
                      return `${d.getMonth() + 1}/${d.getDate()}`;
                    }}
                  />
                  <YAxis
                    tick={{ fontSize: 9, fill: '#64748b' }}
                    axisLine={false}
                    tickLine={false}
                    width={35}
                    domain={['auto', 'auto']}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="value"
                    name="velocity"
                    stroke="#38bdf8"
                    strokeWidth={2}
                    fill="url(#velGradient)"
                    dot={false}
                    activeDot={{ r: 4, fill: '#38bdf8', stroke: '#0f172a', strokeWidth: 2 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="mx-4 border-t border-white/5" />

        {/* ThermoSeq — Temperature Chart */}
        <div className="px-4 pt-4 pb-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Thermometer size={14} className="text-amber-400" />
              <span className="text-xs text-slate-400 font-medium">ThermoSeq — Surface Temperature</span>
            </div>
            <div className="flex items-center gap-1.5">
              {isLoadingTemp ? (
                <Loader2 size={12} className="text-amber-400 animate-spin" />
              ) : tempTrend > 0 ? (
                <TrendingUp size={12} className="text-red-400" />
              ) : (
                <TrendingDown size={12} className="text-green-400" />
              )}
              <span className={`text-xs font-mono ${tempTrend > 0 ? 'text-red-400' : 'text-green-400'}`}>
                {tempTrend > 0 ? '+' : ''}{tempTrend.toFixed(1)}°C
              </span>
            </div>
          </div>

          {/* Temperature stats */}
          <div className="grid grid-cols-3 gap-2 mb-3">
            <div className="glass-light rounded-lg p-2 text-center">
              <p className="text-[10px] text-slate-500 uppercase">Current</p>
              <p className="text-sm font-mono font-bold text-amber-400">{tempCurrent.toFixed(1)}°</p>
            </div>
            <div className="glass-light rounded-lg p-2 text-center">
              <p className="text-[10px] text-slate-500 uppercase">Average</p>
              <p className="text-sm font-mono font-bold text-slate-300">{tempAvg.toFixed(1)}°</p>
            </div>
            <div className="glass-light rounded-lg p-2 text-center">
              <p className="text-[10px] text-slate-500 uppercase">Unit</p>
              <p className="text-sm font-mono font-bold text-slate-300">°C</p>
            </div>
          </div>

          {/* Temperature chart */}
          {isLoadingTemp ? (
            <div className="h-36"><ChartSkeleton /></div>
          ) : (
            <div className="h-36 -mx-2">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={temperatureData}>
                  <defs>
                    <linearGradient id="tempGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 9, fill: '#64748b' }}
                    axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                    tickLine={false}
                    interval="preserveStartEnd"
                    tickFormatter={(val) => {
                      const d = new Date(val);
                      return `${d.getMonth() + 1}/${d.getDate()}`;
                    }}
                  />
                  <YAxis
                    tick={{ fontSize: 9, fill: '#64748b' }}
                    axisLine={false}
                    tickLine={false}
                    width={35}
                    domain={['auto', 'auto']}
                  />
                  <ReferenceLine
                    y={0}
                    stroke="#ef4444"
                    strokeDasharray="4 4"
                    strokeOpacity={0.5}
                    label={{ value: '0°C', position: 'right', fontSize: 9, fill: '#ef4444' }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="value"
                    name="temperature"
                    stroke="#f59e0b"
                    strokeWidth={2}
                    fill="url(#tempGradient)"
                    dot={false}
                    activeDot={{ r: 4, fill: '#f59e0b', stroke: '#0f172a', strokeWidth: 2 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
