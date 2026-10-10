import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export const cn = (...values) => twMerge(clsx(values));
export function number(value, digits = 1) {
  return typeof value === 'number' && Number.isFinite(value)
    ? value.toLocaleString('en-IN', { maximumFractionDigits: digits }) : '—';
}
export function time(value, detailed = false) {
  if (!value || !Number.isFinite(Date.parse(value))) return 'Unavailable';
  return new Intl.DateTimeFormat('en-IN', {
    timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: false,
    ...(detailed ? { day: '2-digit', month: 'short', year: 'numeric' } : {}),
  }).format(new Date(value));
}
export function readPreference(key, fallback = '') {
  try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; }
}
export function savePreference(key, value) {
  try { localStorage.setItem(key, value); } catch { /* Storage may be restricted. */ }
}
