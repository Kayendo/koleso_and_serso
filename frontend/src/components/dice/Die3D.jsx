/** CSS 3D кубик с точками 1–6 */
const PIP_GRID = {
  1: [4],
  2: [0, 8],
  3: [0, 4, 8],
  4: [0, 2, 6, 8],
  5: [0, 2, 4, 6, 8],
  6: [0, 2, 3, 5, 6, 8],
};

const FACE_VALUES = [1, 2, 3, 4, 5, 6];

/** Угол куба, при котором видна грань value */
const SHOW_ROT = {
  1: { x: 0, y: 0 },
  2: { x: 0, y: -90 },
  3: { x: -90, y: 0 },
  4: { x: 90, y: 0 },
  5: { x: 0, y: 90 },
  6: { x: 0, y: 180 },
};

function FacePips({ value }) {
  const on = new Set(PIP_GRID[value] || []);
  return (
    <div className="die3d-pips" data-value={value}>
      {Array.from({ length: 9 }, (_, i) => (
        <span key={i} className={on.has(i) ? "die3d-pip" : "die3d-pip die3d-pip--empty"} />
      ))}
    </div>
  );
}

function DieFace({ value, transform }) {
  return (
    <div className="die3d-face" style={{ transform }}>
      <FacePips value={value} />
    </div>
  );
}

const CUBE_PX = { md: 72, sm: 52 };

function faceTransforms(half) {
  return {
    1: `rotateY(0deg) translateZ(${half}px)`,
    6: `rotateY(180deg) translateZ(${half}px)`,
    2: `rotateY(90deg) translateZ(${half}px)`,
    5: `rotateY(-90deg) translateZ(${half}px)`,
    3: `rotateX(90deg) translateZ(${half}px)`,
    4: `rotateX(-90deg) translateZ(${half}px)`,
  };
}

export function rotationForValue(value) {
  const r = SHOW_ROT[value] || SHOW_ROT[1];
  return { x: r.x, y: r.y };
}

export default function Die3D({
  value = 1,
  rolling = false,
  throwDelay = 0,
  offsetX = 0,
  size = "md",
}) {
  const v = Math.min(6, Math.max(1, value || 1));
  const rot = rotationForValue(v);
  const px = CUBE_PX[size] || CUBE_PX.md;
  const transforms = faceTransforms(px / 2);
  const style = {
    "--die-tx": `${offsetX}px`,
    "--die-delay": `${throwDelay}ms`,
    transform: rolling
      ? undefined
      : `rotateX(${rot.x}deg) rotateY(${rot.y}deg)`,
  };

  return (
    <div
      className={`die3d-wrap die3d-wrap--${size} ${rolling ? "die3d-wrap--rolling" : "die3d-wrap--landed"}`}
      style={{ "--die-delay": `${throwDelay}ms`, "--die-tx": `${offsetX}px` }}
    >
      <div className="die3d-scene">
        <div className="die3d-cube" style={style}>
          {FACE_VALUES.map((fv) => (
            <DieFace key={fv} value={fv} transform={transforms[fv]} />
          ))}
        </div>
      </div>
      <div className="die3d-shadow" aria-hidden="true" />
    </div>
  );
}
