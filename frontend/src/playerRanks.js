/** Звания по месту в рейтинге (5 игроков), английские теги как раньше WHALE/VIP. */

export const RANK_TITLES = [
  { label: "WHALE", hint: "House Whale" },
  { label: "HIGH ROLLER", hint: "High Roller" },
  { label: "SHARK", hint: "Card Shark" },
  { label: "REGULAR", hint: "Table Regular" },
  { label: "FLOOR CHIP", hint: "Chip picked up from the floor" },
];

export function rankTitle(placeIndex) {
  return RANK_TITLES[placeIndex]?.label ?? `${placeIndex + 1}`;
}

export function rankClass(placeIndex) {
  const n = placeIndex + 1;
  if (n >= 1 && n <= 5) return `player-rank player-rank--${n}`;
  return "player-rank";
}
