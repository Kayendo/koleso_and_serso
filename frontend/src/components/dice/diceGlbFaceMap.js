import * as THREE from "three";

/**
 * Привязка граней Dice.glb к числам (по UV-текстуре dice_uv_map).
 * Локальные нормали модели после центрирования в DiceGlbMesh.
 */
export const GLB_FACE_DATA = [
  { local: new THREE.Vector3(0, 1, 0), value: 4 },
  { local: new THREE.Vector3(0, -1, 0), value: 3 },
  { local: new THREE.Vector3(1, 0, 0), value: 1 },
  { local: new THREE.Vector3(-1, 0, 0), value: 6 },
  { local: new THREE.Vector3(0, 0, 1), value: 2 },
  { local: new THREE.Vector3(0, 0, -1), value: 5 },
];

const WORLD_UP = new THREE.Vector3(0, 1, 0);
const _n = new THREE.Vector3();

/** Какое значение смотрит вверх (физический результат броска). */
export function readGlbTopFace(quaternion) {
  let best = 1;
  let bestDot = -Infinity;
  for (const f of GLB_FACE_DATA) {
    _n.copy(f.local).applyQuaternion(quaternion);
    const dot = _n.dot(WORLD_UP);
    if (dot > bestDot) {
      bestDot = dot;
      best = f.value;
    }
  }
  return best;
}

/** Показать кубик с нужной гранью вверх (заморозка после броска). */
export function glbQuaternionForTopFace(value, seed = 0) {
  const face = GLB_FACE_DATA.find((f) => f.value === value) || GLB_FACE_DATA[0];
  const q = new THREE.Quaternion().setFromUnitVectors(
    face.local.clone().normalize(),
    WORLD_UP.clone()
  );
  if (seed) {
    const spin = new THREE.Quaternion().setFromAxisAngle(
      WORLD_UP,
      (seed % 8) * 0.09
    );
    q.multiply(spin);
  }
  return q;
}
