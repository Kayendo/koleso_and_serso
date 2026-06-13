import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { apiPost } from "../api";
import { getCachedItemImage, loadItemImage } from "../itemArt";
import ItemIcon from "./ItemIcon";
import VipChip from "../ui/VipChip";
import { WheelPhysicsSim } from "./wheel/wheelPhysics";

const SIZE = 540;

const SEGMENT_COLORS = [
  ["#8b1a1a", "#c0392b"],
  ["#1a4a7a", "#2980b9"],
  ["#4a2a6a", "#8e44ad"],
  ["#8a6010", "#d4a017"],
  ["#0d5a4a", "#16a085"],
  ["#8a4010", "#e67e22"],
  ["#1a5a30", "#27ae60"],
  ["#1a2030", "#34495e"],
  ["#6a2010", "#c0392b"],
  ["#0a4a40", "#1abc9c"],
  ["#5a3080", "#9b59b6"],
  ["#6a5010", "#e8c468"],
];

function normalizeGames(games, wheelItems, itemWheel) {
  if (itemWheel && wheelItems?.length) {
    return wheelItems.map((i) => ({
      title: i.name || i.wheelLabel || "Предмет",
      itemId: i.id,
      flavor: i.flavor,
      description: i.description,
      polarity: i.polarity,
      durationTurns: i.durationTurns,
    }));
  }
  if (!games?.length) return [];
  if (typeof games[0] === "string") {
    return games.map((title) => ({
      title,
      hltbUrl: searchHltbUrl(title),
    }));
  }
  return games.map((g) => ({
    title: g.title || g.name || String(g),
    hltbUrl: g.hltbUrl || searchHltbUrl(g.title || g.name || ""),
  }));
}

function gamesSignature(games) {
  return (games || [])
    .map((g) => (typeof g === "string" ? g : g?.title || ""))
    .join("\x1e");
}

function searchHltbUrl(title) {
  return `https://howlongtobeat.com/?q=${encodeURIComponent(title)}`;
}

const LOADING = "Загрузка...";

function mergeHltbLinks(items, links) {
  if (!links?.length) return items;
  return items.map((item, i) => ({
    ...item,
    hltbUrl: links[i] || item.hltbUrl,
  }));
}

export default function WheelModal({
  sessionId,
  actorUsername,
  games,
  wheelItems,
  itemWheel,
  blazerdGenreLabel,
  lottery,
  canInteract,
  spinCommand,
  hltbItems,
  actionLoading,
  onConfirm,
  onRequestSpin,
  rewardSpinsRemaining,
  rewardSpinIndex,
  wheelType,
  turnError,
  extraWheelSpinsRemaining,
  voteLabels,
  onDismiss,
}) {
  const [rotation, setRotation] = useState(0);
  const [flapperDeg, setFlapperDeg] = useState(0);
  const simRef = useRef(null);
  const [selected, setSelected] = useState(null);
  const [selectedItemId, setSelectedItemId] = useState(null);
  const [tip, setTip] = useState(null);
  const [genrePick, setGenrePick] = useState(null);
  const [spinning, setSpinning] = useState(false);
  const [done, setDone] = useState(false);
  const [neighborPick, setNeighborPick] = useState(null);
  const [neighborChoiceIndex, setNeighborChoiceIndex] = useState(null);
  const [shopSelections, setShopSelections] = useState([]);
  const [alreadyPlayed, setAlreadyPlayed] = useState(false);
  const shopMode = neighborPick?.mode;
  const [showLabels, setShowLabels] = useState(false);
  const [items, setItems] = useState(() =>
    normalizeGames(games, wheelItems, itemWheel)
  );
  const canvasRef = useRef(null);
  const lastSpinKeyRef = useRef(null);
  const [itemArtTick, setItemArtTick] = useState(0);

  const gamesSig = useMemo(() => gamesSignature(games), [games]);
  const list = items;
  const labelsVisible = showLabels && list.length > 0;

  useEffect(() => {
    setItems(normalizeGames(games, wheelItems, itemWheel));
  }, [gamesSig, itemWheel, wheelItems]);

  useEffect(() => {
    if (!itemWheel || !items.length) return undefined;
    let cancelled = false;
    const ids = items.map((it) => it.itemId).filter(Boolean);
    Promise.all(ids.map((id) => loadItemImage(id))).then(() => {
      if (!cancelled) setItemArtTick((t) => t + 1);
    });
    return () => {
      cancelled = true;
    };
  }, [itemWheel, items]);

  useEffect(() => {
    if (!hltbItems?.length) return;
    setItems((prev) => {
      const byTitle = Object.fromEntries(
        hltbItems.map((x) => [x.title, x.hltbUrl])
      );
      return prev.map((item) => ({
        ...item,
        hltbUrl: byTitle[item.title] || item.hltbUrl,
      }));
    });
  }, [hltbItems]);

  useEffect(() => {
    if (itemWheel || !list.length) return;
    let cancelled = false;
    apiPost("/hltb/links", { titles: list.map((g) => g.title), quick: true })
      .then((data) => {
        if (!cancelled) {
          setItems((prev) => mergeHltbLinks(prev, data.links));
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [sessionId, gamesSig, itemWheel]);

  useEffect(() => {
    lastSpinKeyRef.current = null;
    setDone(false);
    setShowLabels(false);
    setSelected(null);
    setSelectedItemId(null);
    setTip(null);
    setRotation(0);
    setSpinning(false);
    setNeighborPick(null);
    setNeighborChoiceIndex(null);
  }, [sessionId]);

  const urlForIndex = (idx) =>
    list[idx]?.hltbUrl || searchHltbUrl(list[idx]?.title || "");

  const drawWheel = useCallback(
    (rotDeg, withLabels, hoverIdx = -1) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      const w = canvas.width;
      const h = canvas.height;
      const cx = w / 2;
      const cy = h / 2;
      const rOuter = w / 2 - 6;
      const rInner = rOuter - 14;

      ctx.clearRect(0, 0, w, h);

      // Внешнее золотое кольцо
      const ringGrad = ctx.createRadialGradient(cx, cy, rInner, cx, cy, rOuter + 4);
      ringGrad.addColorStop(0, "#3d2e10");
      ringGrad.addColorStop(0.5, "#e8c468");
      ringGrad.addColorStop(1, "#6a5018");
      ctx.beginPath();
      ctx.arc(cx, cy, rOuter + 4, 0, Math.PI * 2);
      ctx.fillStyle = ringGrad;
      ctx.fill();

      if (!list.length) {
        ctx.beginPath();
        ctx.arc(cx, cy, rInner, 0, Math.PI * 2);
        ctx.fillStyle = "#1a1520";
        ctx.fill();
        ctx.fillStyle = "#c9a84c";
        ctx.font = "600 16px Outfit, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("Нет секторов", cx, cy);
        return;
      }

      const n = list.length;
      const slice = (2 * Math.PI) / n;
      const rotRad = (rotDeg * Math.PI) / 180;

      for (let i = 0; i < n; i++) {
        const start = i * slice + rotRad;
        const end = start + slice;
        const mid = start + slice / 2;
        const [c0, c1] = SEGMENT_COLORS[i % SEGMENT_COLORS.length];
        const segGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, rInner);
        segGrad.addColorStop(0, c1);
        segGrad.addColorStop(1, c0);

        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.arc(cx, cy, rInner, start, end);
        ctx.closePath();
        ctx.fillStyle = segGrad;
        ctx.fill();

        if (i === hoverIdx) {
          ctx.fillStyle = "rgba(255, 255, 255, 0.18)";
          ctx.fill();
        }

        ctx.strokeStyle = "rgba(0, 0, 0, 0.55)";
        ctx.lineWidth = 2;
        ctx.stroke();

        // Штифт между секторами
        const pegR = rInner - 4;
        const px = cx + Math.cos(start) * pegR;
        const py = cy + Math.sin(start) * pegR;
        ctx.beginPath();
        ctx.arc(px, py, 4, 0, Math.PI * 2);
        ctx.fillStyle = "#f5d98a";
        ctx.fill();
        ctx.strokeStyle = "#3d2e10";
        ctx.lineWidth = 1;
        ctx.stroke();

        if (withLabels) {
          ctx.save();
          ctx.translate(cx, cy);
          ctx.rotate(mid);
          const labelR = rInner * 0.64;
          const itemId = list[i].itemId;
          const icon = itemWheel && itemId ? getCachedItemImage(itemId) : null;

          if (icon) {
            const iconSize = Math.min(34, slice * rInner * 0.42);
            ctx.shadowColor = "rgba(0,0,0,0.75)";
            ctx.shadowBlur = 5;
            ctx.drawImage(
              icon,
              labelR - iconSize / 2,
              -iconSize - 4,
              iconSize,
              iconSize
            );
            ctx.shadowBlur = 0;
            const shortName = String(list[i].title || "").slice(0, 14);
            if (shortName) {
              ctx.fillStyle = "#fff";
              ctx.font = "bold 10px Outfit, system-ui, sans-serif";
              ctx.textAlign = "center";
              ctx.shadowColor = "rgba(0,0,0,0.8)";
              ctx.shadowBlur = 3;
              ctx.fillText(shortName, labelR, 10);
              ctx.shadowBlur = 0;
            }
          } else {
            ctx.fillStyle = "#fff";
            ctx.font = "bold 13px Outfit, system-ui, sans-serif";
            ctx.textAlign = "center";
            ctx.shadowColor = "rgba(0,0,0,0.8)";
            ctx.shadowBlur = 4;
            const title = String(list[i].title).slice(0, 22);
            ctx.fillText(title, labelR, 5);
            ctx.shadowBlur = 0;
          }
          ctx.restore();
        }
      }

      // Огни по ободу
      for (let i = 0; i < 24; i++) {
        const a = (i / 24) * Math.PI * 2 + rotRad * 0.02;
        const lx = cx + Math.cos(a) * (rOuter - 2);
        const ly = cy + Math.sin(a) * (rOuter - 2);
        ctx.beginPath();
        ctx.arc(lx, ly, i % 2 === 0 ? 3.5 : 2.5, 0, Math.PI * 2);
        ctx.fillStyle = i % 2 === 0 ? "#fff8e0" : "#e8c468";
        ctx.fill();
      }

      // Центральная ступица
      const hubGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, 38);
      hubGrad.addColorStop(0, "#f5d98a");
      hubGrad.addColorStop(0.4, "#a88438");
      hubGrad.addColorStop(1, "#1a1208");
      ctx.beginPath();
      ctx.arc(cx, cy, 38, 0, Math.PI * 2);
      ctx.fillStyle = hubGrad;
      ctx.fill();
      ctx.strokeStyle = "#f5d98a";
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(cx, cy, 14, 0, Math.PI * 2);
      ctx.fillStyle = "#0a0806";
      ctx.fill();
      ctx.shadowColor = "rgba(245, 217, 138, 0.85)";
      ctx.shadowBlur = 12;
      ctx.fillStyle = "#f5d98a";
      ctx.font = "bold 11px Outfit, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("VIP", cx, cy);
      ctx.shadowBlur = 0;
    },
    [list, itemWheel]
  );

  useEffect(() => {
    const id = requestAnimationFrame(() => {
      drawWheel(rotation, labelsVisible);
    });
    return () => cancelAnimationFrame(id);
  }, [list, rotation, labelsVisible, itemArtTick, drawWheel]);

  const hitTestSegment = (clientX, clientY) => {
    const canvas = canvasRef.current;
    if (!canvas || !list.length || !labelsVisible) return -1;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const x = (clientX - rect.left) * scaleX - cx;
    const y = (clientY - rect.top) * scaleY - cy;
    const dist = Math.hypot(x, y);
    const r = canvas.width / 2 - 20;
    if (dist < 40 || dist > r) return -1;

    let angleDeg = (Math.atan2(y, x) * 180) / Math.PI;
    angleDeg = ((angleDeg - rotation) % 360 + 360) % 360;
    const sliceDeg = 360 / list.length;
    return Math.floor(angleDeg / sliceDeg) % list.length;
  };

  const openHltb = (idx) => {
    if (idx < 0 || !list[idx]) return;
    window.open(urlForIndex(idx), "_blank", "noopener,noreferrer");
  };

  const showItemTip = (idx) => {
    if (idx < 0 || !list[idx]) return;
    const it = list[idx];
    setTip({
      itemId: it.itemId,
      title: it.title,
      flavor: it.flavor,
      description: it.description || "—",
      duration: it.durationTurns,
      polarity: it.polarity,
    });
  };

  const handleCanvasClick = (e) => {
    if (!labelsVisible) return;
    const idx = hitTestSegment(e.clientX, e.clientY);
    if (idx >= 0) {
      if (itemWheel) showItemTip(idx);
      else openHltb(idx);
    }
  };

  const handleCanvasMove = (e) => {
    if (!labelsVisible) return;
    const idx = hitTestSegment(e.clientX, e.clientY);
    if (canvasRef.current) {
      canvasRef.current.style.cursor = idx >= 0 ? "pointer" : "default";
    }
    drawWheel(rotation, true, idx);
  };

  useEffect(() => {
    if (!spinCommand) return;
    if (spinCommand.sessionId != null && spinCommand.sessionId !== sessionId) {
      return;
    }

    if (spinCommand.recovered) {
      const spun = normalizeGames(
        spinCommand.wheel?.length ? spinCommand.wheel : games,
        spinCommand.wheelItems || wheelItems,
        itemWheel || spinCommand.wheelType === "item"
      );
      if (spun.length) setItems(spun);
      const active = spun.length ? spun : list;
      if (!active.length) return;

      const n = active.length;
      const sim = new WheelPhysicsSim(n);
      sim.snapTo(spinCommand.targetIndex, 3);
      simRef.current = sim;
      const rot = sim.getRotationDeg();
      setRotation(rot);
      setFlapperDeg(0);
      setShowLabels(true);
      setSpinning(false);
      setDone(true);
      lastSpinKeyRef.current = `${sessionId}-${spinCommand.targetIndex}-${n}-recovered`;
      if (spinCommand.crownPick?.choices?.length) {
        setNeighborPick(spinCommand.crownPick);
        setSelected(null);
        setSelectedItemId(null);
        setNeighborChoiceIndex(null);
      } else if (spinCommand.shopPick?.choices?.length) {
        setNeighborPick(spinCommand.shopPick);
        setSelected(null);
        setSelectedItemId(null);
        setNeighborChoiceIndex(null);
        setShopSelections([]);
      } else {
        const pick = active[spinCommand.targetIndex] || active[0];
        setNeighborPick(null);
        setSelected(pick?.title || "");
        setSelectedItemId(
          spinCommand.selectedItemId ?? pick?.itemId ?? null
        );
        setAlreadyPlayed(!!spinCommand.duplicateGame);
      }
      drawWheel(rot, true);
      return;
    }

    const pickTag = spinCommand.crownPick
      ? "crown"
      : spinCommand.shopPick
        ? "shop"
        : "plain";
    const spinKey = `${sessionId}-${spinCommand.targetIndex}-${(spinCommand.wheel || []).length}-${pickTag}`;
    if (lastSpinKeyRef.current === spinKey) return;
    lastSpinKeyRef.current = spinKey;

    const spun = normalizeGames(
      spinCommand.wheel?.length ? spinCommand.wheel : games,
      spinCommand.wheelItems || wheelItems,
      itemWheel || spinCommand.wheelType === "item"
    );
    if (spun.length) setItems(spun);
    const active = spun.length ? spun : list;
    if (!active.length) return;

    setSpinning(true);
    setShowLabels(true);
    setDone(false);
    setAlreadyPlayed(false);

    const n = active.length;
    const isItemWheel = itemWheel || spinCommand.wheelType === "item";
    const sim = new WheelPhysicsSim(n);
    sim.startSpin(
      spinCommand.targetIndex,
      isItemWheel ? 3 : 12,
      isItemWheel ? null : 58 + Math.random() * 4
    );
    simRef.current = sim;
    let last = performance.now();

    const tick = (now) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      const running = sim.step(dt);
      const rot = sim.getRotationDeg();
      setRotation(rot);
      setFlapperDeg(sim.getFlapperDeg());
      drawWheel(rot, true);
      if (running) {
        requestAnimationFrame(tick);
      } else {
        sim.angle = sim._targetAngle;
        const rotFinal = sim.getRotationDeg();
        setRotation(rotFinal);
        drawWheel(rotFinal, true);

        if (spinCommand.crownPick?.choices?.length) {
          setNeighborPick(spinCommand.crownPick);
          setSelected(null);
          setSelectedItemId(null);
          setNeighborChoiceIndex(null);
        } else if (spinCommand.shopPick?.choices?.length) {
          setNeighborPick(spinCommand.shopPick);
          setSelected(null);
          setSelectedItemId(null);
          setNeighborChoiceIndex(null);
          setShopSelections([]);
        } else {
          const pick = active[spinCommand.targetIndex] || active[0];
          setNeighborPick(null);
          const title =
            spinCommand.selectedItemName ||
            pick?.title ||
            "";
          setSelected(title);
          setSelectedItemId(
            spinCommand.selectedItemId ?? pick?.itemId ?? null
          );
          setAlreadyPlayed(!!spinCommand.duplicateGame);
        }
        setDone(true);
        setSpinning(false);
      }
    };
    requestAnimationFrame(tick);
  }, [spinCommand, sessionId, games, wheelItems, itemWheel, list, drawWheel]);

  const busy = !!actionLoading;
  const spinLoading = actionLoading === "spin";
  const confirmLoading = actionLoading === "confirm";
  const handleSpinClick = () => {
    if (!canInteract || spinning || !list.length || busy) return;
    onRequestSpin?.();
  };

  if (lottery) {
    return (
      <motion.div
        className="overlay overlay-spectate overlay--casino"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <div className="modal-square wheel-modal lottery-modal modal-panel--casino">
          <div className="wheel-vip-banner">
            <VipChip label="JACKPOT" variant="ruby" pulse />
            <span className="wheel-vip-banner__sub">777 HIGH LIMIT · WHALE LOTTERY</span>
          </div>
          <p className="spectate-actor">{actorUsername} — лотерея</p>
          <h3>777 Лотерея</h3>
          <p>
            Откройте{" "}
            <a
              href="https://gamegauntlets.com/"
              target="_blank"
              rel="noreferrer"
            >
              Game Gauntlet
            </a>{" "}
            и введите выпавшую игру:
          </p>
          {canInteract ? (
            <>
              <input
                id="lottery-title"
                className="input"
                placeholder="Название игры со Steam"
              />
              <button
                className="btn primary"
                disabled={busy}
                onClick={() => {
                  const el = document.getElementById("lottery-title");
                  const title = (el?.value ?? "").trim();
                  if (!title || busy) return;
                  onConfirm({
                    selectedGame: title,
                    lotteryUrl: "https://gamegauntlets.com/",
                  });
                }}
              >
                {confirmLoading ? LOADING : "Записать игру"}
              </button>
            </>
          ) : (
            <p className="muted">Ждём ввода игрока…</p>
          )}
        </div>
      </motion.div>
    );
  }

  const selectedIdx = Math.max(
    0,
    list.findIndex((g) => g.title === selected)
  );

  return (
    <motion.div
      className="overlay overlay-spectate overlay--casino"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <div className="modal-square wheel-modal wheel-modal-large wheel-casino-chamber">
        <div className="wheel-vip-banner">
          <VipChip label="HIGH LIMIT" variant="platinum" pulse />
          <span className="wheel-vip-banner__sub">PRIVATE WHEEL · CONCIERGE SPIN</span>
        </div>
        <div className="wheel-casino-lights" aria-hidden="true">
          {Array.from({ length: 16 }, (_, i) => (
            <span key={i} className="wheel-casino-bulb" style={{ "--i": i }} />
          ))}
        </div>
        {canInteract && onDismiss && !spinning && !done && (
          <button
            type="button"
            className="wheel-dismiss-btn close"
            title="Закрыть колесо"
            onClick={onDismiss}
          >
            ×
          </button>
        )}
        <p className="spectate-actor">
          {actorUsername}{" "}
          {blazerdGenreLabel ? `— Blazerd: ${blazerdGenreLabel}` : ""}{" "}
          {spinning
            ? "крутит колесо"
            : done
              ? "выпало"
              : wheelType === "reward_item"
                ? `— награда · колесо ${rewardSpinIndex || 1}${
                    rewardSpinsRemaining != null
                      ? ` (осталось ${rewardSpinsRemaining})`
                      : ""
                  }`
                : itemWheel
                  ? "— колесо предметов"
                  : "— колесо игр"}
        </p>
        {turnError && <p className="error wheel-error">{turnError}</p>}
        {voteLabels?.length > 0 && (
          <div className="wheel-vote-banners">
            {voteLabels.map((label) => (
              <span key={label} className="wheel-vote-banner">
                {label}
              </span>
            ))}
          </div>
        )}
        {itemWheel && Number(extraWheelSpinsRemaining) > 0 && (
          <p className="wheel-spins-counter">
            Доп. прокруты колеса: <strong>{extraWheelSpinsRemaining}</strong>
          </p>
        )}
        <div className="wheel-assembly wheel-assembly--casino">
          <div
            className="wheel-flapper"
            style={{
              transform: `translateY(-50%) rotate(${flapperDeg}deg)`,
            }}
            aria-hidden="true"
          >
            <div className="wheel-flapper__arm" />
            <div className="wheel-flapper__paddle" />
          </div>
          <div className="wheel-spin-layer wheel-spin-layer--casino">
            <canvas
              ref={canvasRef}
              width={SIZE}
              height={SIZE}
              className={labelsVisible ? "wheel-canvas-clickable" : ""}
              onClick={handleCanvasClick}
              onMouseMove={handleCanvasMove}
              onMouseLeave={() => drawWheel(rotation, labelsVisible)}
            />
          </div>
        </div>
        {!done && canInteract && (
          <button
            className="btn primary"
            onClick={handleSpinClick}
            disabled={spinning || !list.length || busy}
          >
            {spinning
              ? "Крутится…"
              : spinLoading
                ? LOADING
                : "Крутить колесо"}
          </button>
        )}
        {!done && !canInteract && (
          <p className="muted">Ожидаем действия игрока…</p>
        )}
        {tip && itemWheel && (
          <div className="inv-tooltip wheel-item-tip">
            <div className="wheel-item-tip__head">
              {tip.itemId != null && (
                <ItemIcon itemId={tip.itemId} title={tip.title} large />
              )}
              <strong>{tip.title}</strong>
            </div>
            {tip.flavor && <p className="inv-flavor">{tip.flavor}</p>}
            <p className="inv-mechanics">{tip.description}</p>
          </div>
        )}
        {done && neighborPick?.choices?.length && (
          <>
            <p className="muted wheel-crown-hint">
              {shopMode === "chat"
                ? "По магазинам с чатом: чат голосует между пятью секторами (выпало + 4 соседа)."
                : shopMode === "leprechaun"
                  ? "По магазинам с Лепреконом: выберите ровно 2 сектора из пяти."
                  : "Корона колесного короля: выберите выпавшую игру или соседнюю"}
            </p>
            {shopMode && neighborPick.landedTitle && (
              <p className="wheel-result muted">
                Недоступно: <strong>{neighborPick.landedTitle}</strong>
              </p>
            )}
            <div className="crown-pick-row">
              {neighborPick.choices.map((c) => (
                <button
                  key={c.choiceIndex}
                  type="button"
                  className={`btn crown-pick-btn ${
                    shopMode === "leprechaun"
                      ? shopSelections.includes(c.choiceIndex)
                        ? "primary"
                        : ""
                      : neighborChoiceIndex === c.choiceIndex
                        ? "primary"
                        : ""
                  }`}
                  onClick={() => {
                    if (shopMode === "leprechaun") {
                      setShopSelections((prev) => {
                        if (prev.includes(c.choiceIndex)) {
                          return prev.filter((x) => x !== c.choiceIndex);
                        }
                        if (prev.length >= 2) return prev;
                        return [...prev, c.choiceIndex];
                      });
                      return;
                    }
                    setNeighborChoiceIndex(c.choiceIndex);
                    setSelected(c.title);
                    if (itemWheel && c.itemId != null) {
                      setSelectedItemId(c.itemId);
                    }
                  }}
                >
                  {itemWheel && c.itemId != null && (
                    <ItemIcon itemId={c.itemId} title={c.title} />
                  )}
                  <span>
                    {c.title}
                    {!shopMode && c.choiceIndex === 1 ? " (выпало)" : ""}
                    {shopMode && c.wheelIndex === neighborPick.landedIndex
                      ? " (выпало)"
                      : ""}
                  </span>
                </button>
              ))}
            </div>
            {selected && (
              <p className="wheel-result">
                Выбрано:{" "}
                {itemWheel ? (
                  <span>{selected}</span>
                ) : (
                  <a
                    href={searchHltbUrl(selected)}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {selected}
                  </a>
                )}
              </p>
            )}
            {canInteract && (
              <button
                className="btn primary"
                disabled={
                  busy ||
                  (shopMode === "leprechaun"
                    ? shopSelections.length !== 2
                    : shopMode === "chat"
                      ? false
                      : neighborChoiceIndex == null)
                }
                onClick={() => {
                  if (busy) return;
                  if (shopMode === "leprechaun" && shopSelections.length !== 2) return;
                  if (!shopMode && neighborChoiceIndex == null) return;
                  if (itemWheel) {
                    if (shopMode) {
                      onConfirm({
                        wheelType: wheelType || "item",
                        targetIndex: spinCommand?.targetIndex,
                        shopChoiceIndexes:
                          shopMode === "leprechaun" ? shopSelections : undefined,
                      });
                    } else {
                      onConfirm({
                        wheelType: wheelType || "item",
                        selectedItemId:
                          selectedItemId ?? spinCommand?.selectedItemId,
                        targetIndex: spinCommand?.targetIndex,
                      });
                    }
                  } else {
                    onConfirm({
                      selectedGame: selected,
                      genreId: genrePick,
                      crownChoiceIndex: neighborChoiceIndex,
                    });
                  }
                }}
              >
                {confirmLoading
                  ? LOADING
                  : shopMode === "chat"
                    ? "Чат голосует"
                    : "Принять"}
              </button>
            )}
          </>
        )}
        {done &&
          !itemWheel &&
          alreadyPlayed &&
          !neighborPick?.choices?.length && (
          <>
            <p className="wheel-result wheel-already-played">Уже выпадало</p>
            {selected && (
              <p className="muted">
                {selected}
              </p>
            )}
            {canInteract && (
              <button
                className="btn primary"
                disabled={busy || spinning}
                onClick={() => {
                  if (busy || spinning) return;
                  setDone(false);
                  setAlreadyPlayed(false);
                  setSelected(null);
                  onRequestSpin?.();
                }}
              >
                {spinLoading ? LOADING : "Рерол"}
              </button>
            )}
          </>
        )}
        {done &&
          (selected ||
            selectedItemId != null ||
            spinCommand?.selectedItemId != null ||
            Number.isInteger(spinCommand?.targetIndex)) &&
          !neighborPick?.choices?.length &&
          !(alreadyPlayed && !itemWheel) && (
          <>
            <p className="wheel-result">
              Выпало:{" "}
              {itemWheel ? (
                <span>
                  {selected ||
                    list.find((g) => g.itemId === selectedItemId)?.title ||
                    "Предмет"}
                </span>
              ) : (
                <a
                  href={urlForIndex(selectedIdx)}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {selected}
                </a>
              )}
            </p>
            {canInteract && (
              <button
                className="btn primary"
                disabled={busy}
                onClick={() => {
                  if (busy) return;
                  if (itemWheel) {
                    onConfirm({
                      wheelType: wheelType || "item",
                      selectedItemId:
                        selectedItemId ?? spinCommand?.selectedItemId,
                      targetIndex:
                        spinCommand?.targetIndex ??
                        (selectedIdx >= 0 ? selectedIdx : 0),
                    });
                  } else {
                    onConfirm({
                      selectedGame: selected,
                      genreId: genrePick,
                    });
                  }
                }}
              >
                {confirmLoading ? LOADING : "Принять"}
              </button>
            )}
          </>
        )}
      </div>
    </motion.div>
  );
}
