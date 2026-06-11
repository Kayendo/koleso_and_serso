import { Suspense, useEffect, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Physics, RigidBody, CuboidCollider } from "@react-three/rapier";
import { Text } from "@react-three/drei";
import * as THREE from "three";
import { EVENT_NAME } from "../../branding";
import DiceGlbMesh, { DICE_SIZE } from "./DiceGlbMesh";
import { glbQuaternionForTopFace, readGlbTopFace } from "./diceGlbFaceMap";
import { isAtRest } from "./dicePhysicsUtils";

const FELT_TEXTURE_CANDIDATES = ["/dice/felt.jpg", "/dice/felt.png"];
let feltTextureCache = null;
let feltTexturePromise = null;

const TABLE_W = 7.2;
const TABLE_D = 4.8;
const WALL_H = 1.4;
const RAIL_H = 0.14;
const RAIL_W = 0.1;

function loadFeltTexture() {
  if (feltTextureCache) return Promise.resolve(feltTextureCache);
  if (feltTexturePromise) return feltTexturePromise;
  feltTexturePromise = new Promise((resolve) => {
    const loader = new THREE.TextureLoader();
    const tryLoad = (i) => {
      if (i >= FELT_TEXTURE_CANDIDATES.length) {
        resolve(null);
        return;
      }
      loader.load(
        FELT_TEXTURE_CANDIDATES[i],
        (tex) => {
          tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
          tex.repeat.set(1.4, 1.4);
          tex.colorSpace = THREE.SRGBColorSpace;
          feltTextureCache = tex;
          resolve(tex);
        },
        undefined,
        () => tryLoad(i + 1)
      );
    };
    tryLoad(0);
  });
  return feltTexturePromise;
}

function useFeltTexture() {
  const [map, setMap] = useState(feltTextureCache);
  useEffect(() => {
    if (feltTextureCache) return undefined;
    let cancelled = false;
    loadFeltTexture().then((tex) => {
      if (!cancelled && tex) setMap(tex);
    });
    return () => {
      cancelled = true;
    };
  }, []);
  return map;
}

function cryptoFloat() {
  const buf = new Uint32Array(1);
  crypto.getRandomValues(buf);
  return buf[0] / 0xffffffff;
}

function randomImpulse() {
  return {
    lx: (cryptoFloat() - 0.5) * 1.1,
    ly: -2.2 - cryptoFloat() * 1.4,
    lz: (cryptoFloat() - 0.5) * 1.1,
    ax: (cryptoFloat() - 0.5) * 22,
    ay: (cryptoFloat() - 0.5) * 22,
    az: (cryptoFloat() - 0.5) * 22,
  };
}

function DieMesh() {
  return <DiceGlbMesh />;
}

function PhysicsDie({ index, spawnX, onSettled, allSettled }) {
  const ref = useRef(null);
  const settled = useRef(false);
  const settleFrames = useRef(0);
  const impulse = useRef(randomImpulse()).current;
  const [spawned, setSpawned] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setSpawned(true), index * 120);
    return () => clearTimeout(t);
  }, [index]);

  useFrame(() => {
    const body = ref.current;
    if (!body || settled.current || allSettled.current) return;

    const lv = body.linvel();
    const av = body.angvel();
    const lin = new THREE.Vector3(lv.x, lv.y, lv.z);
    const ang = new THREE.Vector3(av.x, av.y, av.z);

    if (isAtRest(lin, ang, 0.1)) {
      settleFrames.current += 1;
    } else {
      settleFrames.current = 0;
    }

    if (settleFrames.current < 10) return;

    const rot = body.rotation();
    const q = new THREE.Quaternion(rot.x, rot.y, rot.z, rot.w);
    const value = readGlbTopFace(q);

    body.setLinvel({ x: 0, y: 0, z: 0 }, true);
    body.setAngvel({ x: 0, y: 0, z: 0 }, true);

    settled.current = true;
    onSettled(index, value);
  });

  if (!spawned) return null;

  return (
    <RigidBody
      ref={ref}
      colliders="cuboid"
      restitution={0.38}
      friction={0.9}
      linearDamping={0.18}
      angularDamping={0.24}
      position={[spawnX, 3.4 + index * 0.3, -0.15 + index * 0.2]}
      linearVelocity={[impulse.lx, impulse.ly, impulse.lz]}
      angularVelocity={[impulse.ax, impulse.ay, impulse.az]}
    >
      <DieMesh />
    </RigidBody>
  );
}

function TableRails() {
  const wood = { color: "#4a3218", roughness: 0.65, metalness: 0.05 };
  const hw = TABLE_W / 2;
  const hd = TABLE_D / 2;
  const y = RAIL_H / 2 + 0.02;

  return (
    <>
      <mesh position={[0, y, -hd - RAIL_W / 2]}>
        <boxGeometry args={[TABLE_W + RAIL_W * 2, RAIL_H, RAIL_W]} />
        <meshStandardMaterial {...wood} />
      </mesh>
      <mesh position={[0, y, hd + RAIL_W / 2]}>
        <boxGeometry args={[TABLE_W + RAIL_W * 2, RAIL_H, RAIL_W]} />
        <meshStandardMaterial {...wood} />
      </mesh>
      <mesh position={[-hw - RAIL_W / 2, y, 0]}>
        <boxGeometry args={[RAIL_W, RAIL_H, TABLE_D]} />
        <meshStandardMaterial {...wood} />
      </mesh>
      <mesh position={[hw + RAIL_W / 2, y, 0]}>
        <boxGeometry args={[RAIL_W, RAIL_H, TABLE_D]} />
        <meshStandardMaterial {...wood} />
      </mesh>
    </>
  );
}

function FeltTableVisual() {
  const feltMap = useFeltTexture();
  return (
    <>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <planeGeometry args={[TABLE_W, TABLE_D]} />
        <meshStandardMaterial
          map={feltMap || null}
          color="#0d5c3d"
          roughness={0.92}
          metalness={0.02}
        />
      </mesh>
      <mesh position={[0, -0.2, 0]}>
        <boxGeometry args={[TABLE_W + 0.35, 0.32, TABLE_D + 0.35]} />
        <meshStandardMaterial color="#3d2810" roughness={0.7} />
      </mesh>
      <TableRails />
      <Text
        position={[0, 0.02, TABLE_D / 2 - 0.35]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.22}
        color="#c9a84c"
        anchorX="center"
        anchorY="middle"
        letterSpacing={0.06}
      >
        {EVENT_NAME}
      </Text>
    </>
  );
}

function FeltTablePhysics() {
  const hw = TABLE_W / 2;
  const hd = TABLE_D / 2;
  return (
    <>
      <RigidBody type="fixed" friction={1.15} restitution={0.12}>
        <CuboidCollider args={[hw, 0.08, hd]} position={[0, -0.08, 0]} />
      </RigidBody>
      <RigidBody type="fixed" restitution={0.08} friction={0.95}>
        <CuboidCollider args={[0.06, WALL_H, hd + 0.2]} position={[-hw - 0.06, WALL_H / 2, 0]} />
        <CuboidCollider args={[0.06, WALL_H, hd + 0.2]} position={[hw + 0.06, WALL_H / 2, 0]} />
        <CuboidCollider args={[hw + 0.2, WALL_H, 0.06]} position={[0, WALL_H / 2, -hd - 0.06]} />
        <CuboidCollider args={[hw + 0.2, WALL_H, 0.06]} position={[0, WALL_H / 2, hd + 0.06]} />
      </RigidBody>
      <FeltTableVisual />
    </>
  );
}

function FrozenDice({ finalValues }) {
  const count = finalValues.length;
  const offsets =
    count === 1 ? [0] : count === 2 ? [-0.65, 0.65] : [-1, 0, 1];

  return (
    <>
      <ambientLight intensity={0.55} />
      <directionalLight position={[4, 8, 3]} intensity={1.1} />
      <FeltTableVisual />
      {finalValues.map((v, i) => {
        const q = glbQuaternionForTopFace(v, i);
        const e = new THREE.Euler().setFromQuaternion(q);
        return (
          <group
            key={i}
            position={[offsets[i], DICE_SIZE / 2 + 0.03, -0.1 + i * 0.12]}
            rotation={[e.x, e.y, e.z]}
          >
            <DieMesh />
          </group>
        );
      })}
    </>
  );
}

function SceneContent({ diceCount, finalValues, onAllSettled, frozen }) {
  if (frozen) {
    return <FrozenDice finalValues={finalValues} />;
  }

  const settled = useRef({});
  const allSettled = useRef(false);
  const count = diceCount;

  const offsets =
    count === 1 ? [0] : count === 2 ? [-0.65, 0.65] : [-1, 0, 1];

  const handleSettled = (index, value) => {
    settled.current[index] = value;
    if (Object.keys(settled.current).length >= count && !allSettled.current) {
      allSettled.current = true;
      const values = Array.from({ length: count }, (_, i) => settled.current[i]);
      onAllSettled?.(values);
    }
  };

  return (
    <>
      <ambientLight intensity={0.55} />
      <directionalLight position={[4, 8, 3]} intensity={1.1} />
      <pointLight position={[-2, 4, 2]} intensity={0.35} color="#e8c468" />
      <Physics gravity={[0, -22, 0]} timeStep={1 / 60}>
        <FeltTablePhysics />
        {Array.from({ length: count }, (_, i) => (
          <PhysicsDie
            key={i}
            index={i}
            spawnX={offsets[i]}
            onSettled={handleSettled}
            allSettled={allSettled}
          />
        ))}
      </Physics>
    </>
  );
}

export default function PhysicsDiceScene({
  diceCount = 2,
  finalValues,
  onAllSettled,
  frozen = false,
  active = true,
  className = "",
}) {
  const count = finalValues?.length || diceCount;

  return (
    <div className={`physics-dice-canvas-wrap ${className}`.trim()}>
      <Canvas
        frameloop={active ? "always" : "demand"}
        dpr={[1, 1.5]}
        camera={{ position: [4.2, 5.2, 4.2], fov: 48, near: 0.1, far: 60 }}
        onCreated={({ camera, gl }) => {
          camera.lookAt(0, 0.05, 0);
          gl.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
        }}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      >
        <Suspense fallback={null}>
          <SceneContent
            diceCount={count}
            finalValues={finalValues}
            onAllSettled={onAllSettled}
            frozen={frozen}
          />
        </Suspense>
      </Canvas>
    </div>
  );
}
