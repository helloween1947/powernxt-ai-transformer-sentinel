const ease = [0.22, 1, 0.36, 1];
export const motionTiming = {
  micro: { duration: 0.2, ease },
  view: { duration: 0.24, ease },
  spatial: { duration: 0.36, ease },
  exit: { duration: 0.16, ease: [0.4, 0, 1, 1] },
  cursor: { duration: 0.12, ease },
};
export const inspectionEntry = reduced => reduced ? { opacity: 1, y: 0 } : { opacity: 0, y: 8 };
export function cameraResetProgress(elapsed, duration = 0.36) {
  const t = Math.max(0, Math.min(1, elapsed / duration));
  return t * t * (3 - 2 * t);
}
