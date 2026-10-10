import { Quaternion, Vector3 } from 'three';

// Rotate world directions into camera space without applying position or zoom.
export function sceneAxes(camera) {
  const inverse = camera.getWorldQuaternion(new Quaternion()).invert();
  return ['X', 'Y', 'Z'].map((label, index) => {
    const direction = new Vector3().setComponent(index, 1).applyQuaternion(inverse);
    return {
      label,
      x: Math.round(direction.x * 1000) / 1000,
      y: Math.round(-direction.y * 1000) / 1000,
      depth: Math.round(direction.z * 1000) / 1000,
    };
  }).sort((a, b) => a.depth - b.depth);
}
