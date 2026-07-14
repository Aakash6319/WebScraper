import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merge Tailwind CSS classes safely.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a date string for display.
 */
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return 'N/A';
  try {
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

/**
 * Format milliseconds to human-readable duration.
 */
export function formatDuration(ms: number | null | undefined): string {
  if (!ms) return '0s';
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

/**
 * Get status badge color classes.
 */
export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    running: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    waiting_captcha: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
    waiting_user_input: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
    retrying: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    completed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    cancelled: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
    timed_out: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    active: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200',
    idle: 'bg-slate-100 text-slate-800 dark:bg-slate-900 dark:text-slate-200',
    closed: 'bg-gray-100 text-gray-600',
  };
  return colors[status] || colors.pending;
}
