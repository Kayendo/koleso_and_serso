/** Жанры для кнопок выбора (fallback, если API недоступен). */

export const FALLBACK_GENRES = [
  { id: 1, buttonLabel: "Пазлы", shortLabel: "Пазлы" },
  { id: 2, buttonLabel: "Шутеры", shortLabel: "Шутеры" },
  { id: 3, buttonLabel: "Экшены", shortLabel: "Экшены" },
  { id: 4, buttonLabel: "Приключения", shortLabel: "Приключения" },
  { id: 5, buttonLabel: "Платформеры", shortLabel: "Платформеры" },
  { id: 6, buttonLabel: "Симуляторы", shortLabel: "Симуляторы" },
  { id: 7, buttonLabel: "Хорроры", shortLabel: "Хорроры" },
  { id: 8, buttonLabel: "РПГ", shortLabel: "РПГ" },
  { id: 9, buttonLabel: "Стратегии", shortLabel: "Стратегии" },
];

export function genreButtonLabel(g) {
  if (!g) return "";
  return g.buttonLabel || g.shortLabel || g.label || "";
}

export async function fetchGenres(apiGet) {
  try {
    const list = await apiGet("/genres");
    if (Array.isArray(list) && list.length > 0) return list;
  } catch {
    /* fallback */
  }
  return FALLBACK_GENRES;
}
