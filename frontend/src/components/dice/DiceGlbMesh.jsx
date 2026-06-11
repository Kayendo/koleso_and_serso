import { useMemo } from "react";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";

export const DICE_GLB_URL = "/dice/Dice.glb";
export const DICE_SIZE = 0.55;

useGLTF.preload(DICE_GLB_URL);

let preparedDiceTemplate = null;

function prepareDiceScene(scene) {
  const root = scene.clone(true);

  root.traverse((obj) => {
    if (obj.isLight || obj.isCamera) {
      obj.visible = false;
    }
    if (obj.isMesh && obj.material) {
      const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
      mats.forEach((mat) => {
        mat.roughness = mat.roughness ?? 0.42;
        mat.metalness = mat.metalness ?? 0.06;
      });
    }
  });

  const box = new THREE.Box3().setFromObject(root);
  const center = box.getCenter(new THREE.Vector3());
  root.position.sub(center);

  const size = box.getSize(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z, 0.001);
  root.scale.setScalar(DICE_SIZE / maxDim);

  return root;
}

function cloneDiceFromTemplate(scene) {
  if (!preparedDiceTemplate) {
    preparedDiceTemplate = prepareDiceScene(scene);
  }
  return preparedDiceTemplate.clone(true);
}

/** Реалистичный кубик из Dice.glb */
export default function DiceGlbMesh({ fallback: Fallback = null }) {
  const { scene } = useGLTF(DICE_GLB_URL);
  const model = useMemo(() => cloneDiceFromTemplate(scene), [scene]);

  if (!model) {
    return Fallback ? <Fallback /> : null;
  }

  return <primitive object={model} />;
}
