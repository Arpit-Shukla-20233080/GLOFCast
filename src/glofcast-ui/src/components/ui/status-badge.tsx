'use client';

import React from 'react';

interface StatusBadgeProps {
  status: 'online' | 'offline' | 'warning' | 'critical';
  label: string;
  size?: 'sm' | 'md';
}

export function StatusBadge({ status, label, size = 'sm' }: StatusBadgeProps) {
  const statusColors = {
    online: 'bg-green-400',
    offline: 'bg-gray-400',
    warning: 'bg-amber-400',
    critical: 'bg-red-400',
  };
  const textColor = {
    online: 'text-green-400',
    offline: 'text-gray-400',
    warning: 'text-amber-400',
    critical: 'text-red-400',
  };

  const sizeClasses = size === 'sm' ? 'px-2 py-1 text-xs' : 'px-3 py-1.5 text-sm';
  const dotSize = size === 'sm' ? 'h-1.5 w-1.5' : 'h-2 w-2';

  return (
    <div className={`inline-flex items-center gap-2 rounded-full backdrop-blur-sm bg-white/5 border border-white/10 ${sizeClasses}`}>
      <span className="relative flex h-2 w-2 items-center justify-center">
        <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${statusColors[status]}`}></span>
        <span className={`relative inline-flex rounded-full ${dotSize} ${statusColors[status]}`}></span>
      </span>
      <span className={`font-medium ${textColor[status]}`}>{label}</span>
    </div>
  );
}
