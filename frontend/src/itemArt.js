/** Картинки предметов: frontend/public/items/<id>.{jpg,png,webp} */

const IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"];

const imageCache = new Map();

export function itemImageCandidates(itemId) {
  const id = Number(itemId);
  if (!id) return [];
  const stem = `/items/${id}`;
  return IMAGE_EXTENSIONS.map((ext) => `${stem}${ext}`);
}

export function itemImageUrl(itemId) {
  return itemImageCandidates(itemId)[0] || null;
}

export function getCachedItemImage(itemId) {
  const cached = imageCache.get(Number(itemId));
  return cached || null;
}

/** Подгрузка первого существующего варианта; null если файла нет. */
export function loadItemImage(itemId) {
  const id = Number(itemId);
  if (!id) return Promise.resolve(null);
  if (imageCache.has(id)) {
    return Promise.resolve(imageCache.get(id));
  }

  const candidates = itemImageCandidates(id);

  return new Promise((resolve) => {
    let index = 0;

    const tryNext = () => {
      if (index >= candidates.length) {
        imageCache.set(id, null);
        resolve(null);
        return;
      }

      const img = new Image();
      img.onload = () => {
        imageCache.set(id, img);
        resolve(img);
      };
      img.onerror = () => {
        index += 1;
        tryNext();
      };
      img.src = candidates[index];
    };

    tryNext();
  });
}
