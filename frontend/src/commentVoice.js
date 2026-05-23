import { playMp3Base64 } from "./audioUnlock";

const SEEN_KEY = "kolesoblya_comment_seen";

let hideTimer = null;

function commentId(data) {
  return Number(data?.id || data?.emittedAt || 0);
}

function markSeen(id) {
  if (!id) return;
  try {
    const prev = Number(sessionStorage.getItem(SEEN_KEY) || 0);
    if (id > prev) sessionStorage.setItem(SEEN_KEY, String(id));
  } catch {
    /* ignore */
  }
}

function isSeen(id) {
  try {
    return id > 0 && id <= Number(sessionStorage.getItem(SEEN_KEY) || 0);
  } catch {
    return false;
  }
}

/** Только сокет — без HTTP при загрузке страницы. */
export function playGameComment(data, onBubble) {
  if (!data?.text) return;
  const id = commentId(data);
  if (!id || isSeen(id)) return;

  markSeen(id);
  if (hideTimer) clearTimeout(hideTimer);

  onBubble?.({
    text: data.text,
    targetPlayer: data.targetPlayer,
    voiceLabel: data.voiceLabel,
  });

  const audio = data.audioBase64
    ? playMp3Base64(data.audioBase64, data.audioMime || "audio/mpeg")
    : Promise.resolve();

  audio.finally(() => {
    hideTimer = setTimeout(() => onBubble?.(null), 2200);
  });
}
