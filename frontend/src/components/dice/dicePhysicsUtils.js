import * as THREE from "three";

/** Локальные нормали граней куба → значение на грани */
const FACE_DATA = [
  { local: new THREE.Vector3(0, 1, 0), value: 1 },
  { local: new THREE.Vector3(0, -1, 0), value: 6 },
  { local: new THREE.Vector3(1, 0, 0), value: 2 },
  { local: new THREE.Vector3(-1, 0, 0), value: 5 },
  { local: new THREE.Vector3(0, 0, 1), value: 3 },
  { local: new THREE.Vector3(0, 0, -1), value: 4 },
];

const WORLD_UP = new THREE.Vector3(0, 1, 0);
const _n = new THREE.Vector3();

/** Какое значение смотрит вверх по кватерниону тела */
export function readTopFace(quaternion) {
  let best = 1;
  let bestDot = -Infinity;
  for (const f of FACE_DATA) {
    _n.copy(f.local).applyQuaternion(quaternion);
    const dot = _n.dot(WORLD_UP);
    if (dot > bestDot) {
      bestDot = dot;
      best = f.value;
    }
  }
  return best;
}

/** Кватернион, при котором `value` смотрит вверх (+ небольшой случайный крен) */
export function quaternionForTopFace(value, seed = 0) {
  const map = {
    1: [0, 0, 0],
    6: [Math.PI, 0, 0],
    2: [0, Math.PI / 2, 0],
    5: [0, -Math.PI / 2, 0],
    3: [-Math.PI / 2, 0, 0],
    4: [Math.PI / 2, 0, 0],
  };
  const [x, y, z] = map[value] || map[1];
  const e = new THREE.Euler(
    x + (seed % 7) * 0.02,
    y + ((seed * 3) % 5) * 0.02,
    z
  );
  return new THREE.Quaternion().setFromEuler(e);
}

export function isAtRest(linVel, angVel, threshold = 0.08) {
  return linVel.length() < threshold && angVel.length() < threshold;
}
