/**
 * Status badge component.
 */
import React from 'react';
import { getStatusColor } from '../utils/format';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

export default function StatusBadge({ status, size = 'sm' }: StatusBadgeProps) {
  const sizeClasses = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-2.5 py-1';
  return (
    <span className={`inline-flex items-center rounded-full font-medium capitalize ${sizeClasses} ${getStatusColor(status)}`}>
      {status === 'in_progress' ? 'In Progress' : status.replace('_', ' ')}
    </span>
  );
}
