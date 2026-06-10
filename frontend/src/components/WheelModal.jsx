import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiPost } from "../api";

const SPIN_MS = 2800;
const SIZE = 520;

const SEGMENT_COLORS = [
  "#e74c3c",
  "#3498db",
  "#9b59b6",
  "#f39c12",
  "#1abc9c",
  "#e67e22",
  "#2ecc71",
  "#34495e",
  "#d35400",
  "#16a085",
  "#c0392b",
  "#8e44ad",
];

function normalizeGames(games, wheelItems, itemWheel) {
  if (itemWheel && wheelItems?.length) {
    return wheelItems.map((i) => ({
      title: i.wheelLabel || `#${i.id} ${i.name}`,
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

  const gamesSig = useMemo(() => gamesSignature(games), [games]);
  const list = items;
  const labelsVisible = showLabels && list.length > 0;

  useEffect(() => {
    setItems(normalizeGames(games, wheelItems, itemWheel));
  }, [gamesSig, itemWheel, wheelItems]);

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
      const r = w / 2 - 8;

      ctx.clearRect(0, 0, w, h);

      if (!list.length) {
        ctx.fillStyle = "#444";
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = "#aaa";
        ctx.font = "16px Manrope, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("Нет игр", cx, cy);
        return;
      }

      const n = list.length;
      const slice = (2 * Math.PI) / n;
      const rotRad = (rotDeg * Math.PI) / 180;

      for (let i = 0; i < n; i++) {
        const start = i * slice + rotRad;
        const end = start + slice;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.arc(cx, cy, r, start, end);
        ctx.closePath();
        ctx.fillStyle = SEGMENT_COLORS[i % SEGMENT_COLORS.length];
        ctx.fill();
        ctx.strokeStyle = i === hoverIdx ? "#fff" : "#111";
        ctx.lineWidth = i === hoverIdx ? 3 : 2;
        ctx.stroke();

        if (withLabels) {
          ctx.save();
          ctx.translate(cx, cy);
          ctx.rotate(start + slice / 2);
          ctx.fillStyle = "#fff";
          ctx.font = "bold 14px Manrope, sans-serif";
          ctx.textAlign = "center";
          ctx.fillText(String(list[i].title).slice(0, 24), r * 0.62, 5);
          ctx.restore();
        }
      }

      ctx.beginPath();
      ctx.arc(cx, cy, 26, 0, Math.PI * 2);
      ctx.fillStyle = "#1a1a1a";
      ctx.fill();
    },
    [list]
  );

  useEffect(() => {
    const id = requestAnimationFrame(() => {
      drawWheel(rotation, labelsVisible);
    });
    return () => cancelAnimationFrame(id);
  }, [list, rotation, labelsVisible, drawWheel]);

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
    const r = canvas.width / 2 - 8;
    if (dist < 28 || dist > r) return -1;

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
      const slice = 360 / n;
      const targetAngle = 360 - spinCommand.targetIndex * slice - slice / 2;
      const rot = 4 * 360 + targetAngle;
      setRotation(rot);
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
    const slice = 360 / n;
    const targetAngle = 360 - spinCommand.targetIndex * slice - slice / 2;
    const extra = 4 * 360 + targetAngle;
    const start = performance.now();

    const tick = (now) => {
      const t = Math.min(1, (now - start) / SPIN_MS);
      const ease = 1 - Math.pow(1 - t, 3);
      const rot = extra * ease;
      setRotation(rot);
      drawWheel(rot, true);
      if (t < 1) {
        requestAnimationFrame(tick);
      } else {
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
      <div className="overlay overlay-spectate">
        <div className="modal-square wheel-modal lottery-modal">
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
      </div>
    );
  }

  const selectedIdx = Math.max(
    0,
    list.findIndex((g) => g.title === selected)
  );

  return (
    <div className="overlay overlay-spectate">
      <div className="modal-square wheel-modal wheel-modal-large">
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
        <div className="wheel-assembly">
          <div className="wheel-arrow-fixed" aria-hidden="true" />
          <div className="wheel-spin-layer">
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
            <strong>{tip.title}</strong>
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
                  className={`btn ${
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
                  {c.title}
                  {!shopMode && c.choiceIndex === 1 ? " (выпало)" : ""}
                  {shopMode && c.wheelIndex === neighborPick.landedIndex
                    ? " (выпало)"
                    : ""}
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
                <span>{selected || `#${selectedItemId}`}</span>
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
    </div>
  );
}
