import { useEffect, useRef, useState } from "react";
import { loadYouTubeIframeApi } from "./youtubeIframeApi";

/** Фоновое видео с YouTube; при ошибке — /background.jpg */
export const BACKGROUND_VIDEO_ID = "f7wMFLY-Pf4";
export const BACKGROUND_VIDEO_START = 279;
const FALLBACK_TIMEOUT_MS = 12000;
const STATIC_BG = "/background.jpg";

function preloadStaticBackground() {
  const img = new Image();
  img.src = STATIC_BG;
}

export default function SceneBackground() {
  const playerHostRef = useRef(null);
  const playerRef = useRef(null);
  const videoReadyRef = useRef(false);
  const [videoActive, setVideoActive] = useState(false);
  const [useFallback, setUseFallback] = useState(false);

  useEffect(() => {
    preloadStaticBackground();
  }, []);

  useEffect(() => {
    if (useFallback) {
      document.body.classList.add("has-custom-bg");
      return undefined;
    }
    if (videoActive) {
      document.body.classList.remove("has-custom-bg");
    }
    return undefined;
  }, [useFallback, videoActive]);

  useEffect(() => {
    if (useFallback) return undefined;

    let cancelled = false;
    let fallbackTimer = null;

    const activateFallback = () => {
      if (cancelled || videoReadyRef.current) return;
      setUseFallback(true);
      setVideoActive(false);
    };

    fallbackTimer = setTimeout(activateFallback, FALLBACK_TIMEOUT_MS);

    loadYouTubeIframeApi()
      .then((YT) => {
        if (cancelled || !playerHostRef.current) return;

        const player = new YT.Player(playerHostRef.current, {
          videoId: BACKGROUND_VIDEO_ID,
          width: "100%",
          height: "100%",
          playerVars: {
            autoplay: 1,
            mute: 1,
            controls: 0,
            disablekb: 1,
            fs: 0,
            iv_load_policy: 3,
            modestbranding: 1,
            playsinline: 1,
            rel: 0,
            loop: 1,
            playlist: BACKGROUND_VIDEO_ID,
            start: BACKGROUND_VIDEO_START,
            origin: window.location.origin,
          },
          events: {
            onReady: (event) => {
              if (cancelled) return;
              videoReadyRef.current = true;
              clearTimeout(fallbackTimer);
              event.target.mute();
              event.target.seekTo(BACKGROUND_VIDEO_START, true);
              event.target.playVideo();
              setVideoActive(true);
            },
            onError: () => {
              activateFallback();
            },
            onStateChange: (event) => {
              if (event.data === YT.PlayerState.ENDED) {
                event.target.seekTo(BACKGROUND_VIDEO_START, true);
                event.target.playVideo();
              }
            },
          },
        });

        playerRef.current = player;
      })
      .catch(() => {
        activateFallback();
      });

    return () => {
      cancelled = true;
      clearTimeout(fallbackTimer);
      videoReadyRef.current = false;
      const player = playerRef.current;
      playerRef.current = null;
      if (player?.destroy) {
        try {
          player.destroy();
        } catch {
          /* player already torn down */
        }
      }
    };
  }, [useFallback]);

  const showVideo = !useFallback;

  return (
    <div
      className={`scene-bg${videoActive ? " scene-bg--video" : ""}${useFallback ? " scene-bg--fallback" : ""}`}
      aria-hidden="true"
    >
      {showVideo && (
        <div className="scene-bg__video-wrap">
          <div ref={playerHostRef} className="scene-bg__video-host" />
          <div className="scene-bg__video-scrim" />
        </div>
      )}
      <div className="scene-bg__mesh" />
      <div className="scene-bg__orb scene-bg__orb--gold" />
      <div className="scene-bg__orb scene-bg__orb--emerald" />
      <div className="scene-bg__orb scene-bg__orb--violet" />
      <div className="scene-bg__sparkles" />
      <div className="scene-bg__chips">
        {["♠", "♦", "♣", "♥", "◆", "✦"].map((sym, i) => (
          <span key={i} className="scene-bg__chip" style={{ "--i": i }}>
            {sym}
          </span>
        ))}
      </div>
      <div className="scene-bg__grain" />
      <div className="scene-bg__vignette" />
      <div className="scene-bg__gold-rail scene-bg__gold-rail--top" />
      <div className="scene-bg__gold-rail scene-bg__gold-rail--bottom" />
    </div>
  );
}
