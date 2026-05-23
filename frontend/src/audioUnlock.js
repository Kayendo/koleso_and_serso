/**
 * Озвучка через Web Audio — чаще играет при свёрнутой вкладке, если контекст разблокирован кликом.
 */

let audioCtx = null;
let unlocked = false;

export function unlockAudio() {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    if (!audioCtx) audioCtx = new Ctx();
    if (audioCtx.state === "suspended") audioCtx.resume();
    if (!unlocked) {
      const buf = audioCtx.createBuffer(1, 1, 22050);
      const src = audioCtx.createBufferSource();
      src.buffer = buf;
      src.connect(audioCtx.destination);
      src.start(0);
      unlocked = true;
    }
  } catch {
    /* ignore */
  }
}

function b64ToArrayBuffer(b64) {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

export function playMp3Base64(b64, mime = "audio/mpeg") {
  return new Promise((resolve) => {
    if (!b64) {
      resolve();
      return;
    }

    unlockAudio();

    if (audioCtx && mime.includes("mpeg")) {
      audioCtx
        .decodeAudioData(b64ToArrayBuffer(b64))
        .then((buffer) => {
          const src = audioCtx.createBufferSource();
          src.buffer = buffer;
          src.connect(audioCtx.destination);
          src.onended = () => resolve();
          src.start(0);
        })
        .catch(() => playHtmlAudio(b64, mime).then(resolve));
      return;
    }

    playHtmlAudio(b64, mime).then(resolve);
  });
}

function playHtmlAudio(b64, mime) {
  return new Promise((resolve) => {
    const audio = new Audio(`data:${mime};base64,${b64}`);
    audio.onended = () => resolve();
    audio.onerror = () => resolve();
    audio.play().catch(() => resolve());
  });
}

if (typeof document !== "undefined") {
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") unlockAudio();
  });
}
