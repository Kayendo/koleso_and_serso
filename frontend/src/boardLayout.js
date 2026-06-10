/** Сетка 11×11 как на макете: углы крупнее, без зазоров. */

const CORNER_FR = 1.55;
const MID_FR = 1;
const MID_COUNT = 9;
const GRID_TOTAL_FR = CORNER_FR * 2 + MID_FR * MID_COUNT;

function axisCenterFrac(index) {
  if (index <= 1) return CORNER_FR / 2;
  if (index >= 11) return CORNER_FR + MID_FR * MID_COUNT + CORNER_FR / 2;
  return CORNER_FR + (index - 2) * MID_FR + MID_FR / 2;
}

/** Центр клетки в % от размера поля (для сквозной анимации). */
export function cellCenterPercent(cellId) {
  const pos = cellGridPosition(cellId);
  return {
    left: (axisCenterFrac(pos.col) / GRID_TOTAL_FR) * 100,
    top: (axisCenterFrac(pos.row) / GRID_TOTAL_FR) * 100,
  };
}

export function cellGridPosition(index) {
  if (index === 0) return { row: 11, col: 1, corner: true };
  if (index >= 1 && index <= 9)
    return { row: 11, col: index + 1, edge: "bottom" };
  if (index === 10) return { row: 11, col: 11, corner: true };
  if (index >= 11 && index <= 19)
    return { row: 21 - index, col: 11, edge: "right" };
  if (index === 20) return { row: 1, col: 11, corner: true };
  if (index >= 21 && index <= 29)
    return { row: 1, col: 31 - index, edge: "top" };
  if (index === 30) return { row: 1, col: 1, corner: true };
  if (index >= 31 && index <= 39)
    return { row: index - 29, col: 1, edge: "left" };
  return { row: 6, col: 6 };
}

/** Единичный вектор дуги внутрь поля (не наружу с края). */
export function inwardArcUnit(cellId) {
  const pos = cellGridPosition(cellId);
  if (pos.edge === "right") return { x: -1, y: 0 };
  if (pos.edge === "left") return { x: 1, y: 0 };
  if (pos.edge === "bottom") return { x: 0, y: -1 };
  if (pos.edge === "top") return { x: 0, y: 1 };
  const x = pos.col <= 1 ? 1 : pos.col >= 11 ? -1 : 0;
  const y = pos.row <= 1 ? 1 : pos.row >= 11 ? -1 : 0;
  return { x: x || -0.7, y: y || -0.7 };
}

export function tokenAnchorClass(cellId) {
  const pos = cellGridPosition(cellId);
  if (pos.edge) return `anchor-${pos.edge}`;
  return "anchor-corner";
}

/** Единичный вектор движения между соседними клетками (в координатах сетки). */
export function travelVector(fromId, toId) {
  const a = cellGridPosition(fromId);
  const b = cellGridPosition(toId);
  let dx = Math.sign(b.col - a.col);
  let dy = Math.sign(b.row - a.row);
  if (dx === 0 && dy === 0) {
    dx = 1;
  }
  return { dx, dy };
}

/**
 * Доля меньшей стороны клетки (через container query) — одинаково на всех ориентациях.
 */
export function tokenSizeFraction(count) {
  if (count <= 1) return 0.48;
  if (count === 2) return 0.36;
  if (count === 3) return 0.28;
  if (count === 4) return 0.23;
  if (count === 5) return 0.19;
  return 0.16;
}

export const COLOR_MAP = {
  orange: "#e67e22",
  pink: "#e84393",
  red: "#c0392b",
  blue: "#2980b9",
  yellow: "#f1c40f",
  gray: "#7f8c8d",
  cyan: "#00cec9",
  green: "#27ae60",
  start: "#2ecc71",
  durka: "#95a5a6",
  lottery: "#f39c12",
  trallalero: "#9b59b6",
  trap: "#bdc3c7",
  question: "#74b9ff",
};

export function cellColor(cell) {
  if (cell.type === "start") return COLOR_MAP.start;
  if (cell.type === "durka") return COLOR_MAP.durka;
  if (cell.type === "lottery") return COLOR_MAP.lottery;
  if (cell.type === "trallalero") return COLOR_MAP.trallalero;
  if (cell.type === "question") return COLOR_MAP.question;
  if (cell.type === "trap_joy") return COLOR_MAP.trap;
  return COLOR_MAP[cell.colorGroup] || "#636e72";
}

/** Картинка клетки: компании — logos/, особые — cells/ по типу. */
const SPECIAL_CELL_STEMS = {
  start: "/cells/start",
  lottery: "/cells/lottery",
  durka: "/cells/durka",
  trallalero: "/cells/trallalero",
  question: "/cells/question",
  trap_joy: "/cells/trap_joy",
};

const IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"];

function cellImageStem(cell) {
  if (!cell) return null;
  if (cell.companyKey) return `/logos/${cell.companyKey}`;
  return SPECIAL_CELL_STEMS[cell.type] || null;
}

/** Все варианты пути (jpg → png → webp) для fallback при onError. */
export function cellImageCandidates(cell) {
  const stem = cellImageStem(cell);
  if (!stem) return [];
  return IMAGE_EXTENSIONS.map((ext) => `${stem}${ext}`);
}

export function cellImageUrl(cell) {
  const candidates = cellImageCandidates(cell);
  return candidates[0] || null;
}

/** Картинка из cells/ (углы, ?, подлянка) — на всю клетку. */
export function isSpecialCellArt(cell) {
  if (!cell?.companyKey && cell?.type) {
    return cell.type in SPECIAL_CELL_STEMS;
  }
  return false;
}

/** @deprecated используйте cellImageUrl */
export function logoUrl(cell) {
  return cellImageUrl(cell);
}
