'use client';

import React from 'react';

interface LoadingSkeletonProps {
  width?: string | number;
  height?: string | number;
  className?: string;
  variant?: 'line' | 'circle' | 'rect';
}

export function LoadingSkeleton({ width, height, className = '', variant = 'rect' }: LoadingSkeletonProps) {
  const baseClasses = 'animate-pulse bg-white/10';
  
  let variantClasses = '';
  if (variant === 'line') variantClasses = 'h-4 w-full rounded';
  else if (variant === 'circle') variantClasses = 'rounded-full';
  else if (variant === 'rect') variantClasses = 'rounded-lg';

  return (
    <div
      className={`${baseClasses} ${variantClasses} ${className}`}
      style={{ width, height }}
    />
  );
}

export function ChartSkeleton() {
  return (
    <div className="p-4 rounded-xl backdrop-blur-sm bg-white/5 border border-white/10 w-full h-full flex flex-col gap-4">
      <LoadingSkeleton variant="rect" className="w-full flex-grow min-h-[200px]" />
      <div className="flex gap-2 justify-between">
        <LoadingSkeleton variant="line" className="w-1/4" />
        <LoadingSkeleton variant="line" className="w-1/4" />
        <LoadingSkeleton variant="line" className="w-1/4" />
      </div>
    </div>
  );
}

export function PanelSkeleton() {
  return (
    <div className="flex flex-col gap-3 w-full">
      <LoadingSkeleton variant="line" className="w-3/4" />
      <LoadingSkeleton variant="line" className="w-full" />
      <LoadingSkeleton variant="line" className="w-5/6" />
      <LoadingSkeleton variant="line" className="w-1/2" />
    </div>
  );
}
