import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { apiGet, apiPatch, apiPost, apiUpload, downloadApiFile } from "../api";
import { EVENT_NAME, EVENT_TAGLINE } from "../branding";
import { playerName } from "../playerName";
import InventoryModal from "./InventoryModal";
import TurnHistoryModal from "./TurnHistoryModal";
import PagedListFooter, { usePagedSlice } from "./PagedListFooter";
import CasinoPoints from "../ui/CasinoPoints";
import VipChip from "../ui/VipChip";
import VipCrest from "../ui/VipCrest";

function historyStatus(g) {
  if (g.status === "completed") return { label: "ПРОШЁЛ", cls: "completed" };
  if (g.status === "dropped") return { label: "ДРОПНУЛ", cls: "dropped" };
  return { label: "ИГРАЕТ", cls: "playing" };
}

export function RulesModal({ html, onClose }) {
  return (
    <Modal title={`Правила ${EVENT_NAME}`} onClose={onClose} casino>
      <div className="rules-content" dangerouslySetInnerHTML={{ __html: html }} />
    </Modal>
  );
}

export function HistoryModal({ items, onClose }) {
  return (
    <Modal title="История игр" onClose={onClose} wide casino>
      <div className="history-list history-list--casino">
        {items.map((g) => {
          const status = historyStatus(g);
          return (
            <article key={g.id} className="history-card history-card--casino">
              <div className="badges history-card__badges">
                <span className="badge purple">
                  {g.displayName || g.username}
                </span>
                <span
                  className={`badge ${
                    g.status === "completed"
                      ? "green"
                      : g.status === "dropped"
                        ? "red"
                        : "gray"
                  }`}
                >
                  {status.label}
                </span>
                {g.isDurka && <span className="badge orange">Дурка</span>}
              </div>
              <h4 className="history-card__title">{g.title}</h4>
              <p className="history-card__meta muted">
                {g.cellName} · кубик {g.diceRoll ?? "—"}
                {g.pointsEarned != null && (
                  <>
                    {" · "}
                    <CasinoPoints value={g.pointsEarned} />
                  </>
                )}
              </p>
              {g.review && (
                <p className="history-card__review">{g.review}</p>
              )}
            </article>
          );
        })}
      </div>
    </Modal>
  );
}

export function StatsModal({ rows, onClose }) {
  return (
    <Modal title="Статистика" onClose={onClose} wide casino>
      <table className="stats-table">
        <thead>
          <tr>
            <th>Игрок</th>
            <th>Очки</th>
            <th>Игры</th>
            <th>Дроп</th>
            <th>Очки с игр</th>
            <th>Круги</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.username}>
              <td>{r.displayName || r.username}</td>
              <td className="green">{r.points}</td>
              <td>{r.gamesCompleted}</td>
              <td>{r.gamesDropped}</td>
              <td>{r.pointsFromGames}</td>
              <td>{r.laps}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Modal>
  );
}

export function LoginModal({ accountData, onClose, onSuccess }) {
  const players = accountData?.players || [];
  const [mode, setMode] = useState("player");
  const [username, setUsername] = useState(players[0]?.username || "");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (mode === "player" && players.length && !username) {
      setUsername(players[0].username);
    }
    if (mode === "admin") {
      setUsername(accountData?.adminUsername || "admin");
    }
  }, [accountData, mode, players, username]);

  const submit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setErr("");
    setSubmitting(true);
    try {
      const data = await apiPost("/auth/login", { username, password });
      onSuccess(data.user);
      onClose();
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal title="Вход в зал" onClose={onClose} casino>
      <div className="login-casino-card">
        <VipCrest subtitle="MEMBERS ONLY · CONCIERGE ACCESS" />
        <VipChip label="VIP LOUNGE" pulse className="login-vip-chip" />
        <p className="login-casino-logo">{EVENT_NAME}</p>
        <p className="login-casino-tagline muted">{EVENT_TAGLINE}</p>
        <p className="login-casino-whisper">High limit · Private tables · No riff-raff</p>
      </div>
      <form onSubmit={submit} className="login-form">
        <div className="login-tabs">
          <button
            type="button"
            className={mode === "player" ? "active" : ""}
            onClick={() => setMode("player")}
          >
            Игрок
          </button>
          <button
            type="button"
            className={mode === "admin" ? "active" : ""}
            onClick={() => setMode("admin")}
          >
            Админ
          </button>
        </div>
        {mode === "player" ? (
          <>
            <label className="field-label">Участник</label>
            <select
              className="input select-styled"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            >
              {players.map((a) => (
                <option key={a.username} value={a.username}>
                  {a.username}
                </option>
              ))}
            </select>
          </>
        ) : (
          <>
            <label className="field-label">Логин админа</label>
            <input className="input" value={username} readOnly />
          </>
        )}
        <label className="field-label">Пароль</label>
        <input
          className="input"
          type="password"
          placeholder="Пароль"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {err && <p className="error">{err}</p>}
        <button
          type="submit"
          className="btn primary full"
          disabled={submitting}
        >
          {submitting ? "Загрузка..." : "Войти"}
        </button>
      </form>
    </Modal>
  );
}

export function ProfileModal({
  profile,
  games,
  inventory,
  players,
  cells,
  currentUser,
  onClose,
  onRefresh,
  onGameCompleted,
  onUserSync,
}) {
  const isOwner = currentUser?.id === profile?.id;
  const [showInventory, setShowInventory] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [turnHistory, setTurnHistory] = useState([]);
  const active = games.find((g) => g.status === "active");
  const pendingAdmin = games.find((g) => g.status === "pending_admin");
  const currentGame = active || pendingAdmin;
  const [review, setReview] = useState(active?.review || "");
  const [rating, setRating] = useState(
    active?.rating != null ? String(active.rating) : ""
  );
  const [tick, setTick] = useState(0);
  const [busy, setBusy] = useState(null);
  const [editingName, setEditingName] = useState(false);
  const [nameDraft, setNameDraft] = useState(playerName(profile));
  const gamesPaged = usePagedSlice(games);

  useEffect(() => {
    setNameDraft(playerName(profile));
    setEditingName(false);
  }, [profile?.id, profile?.displayName, profile?.username]);

  useEffect(() => {
    setReview(active?.review || "");
    setRating(active?.rating != null ? String(active.rating) : "");
  }, [active?.id, active?.review, active?.rating]);

  useEffect(() => {
    if (!active?.timerRunning) return undefined;
    const id = setInterval(() => setTick((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, [active?.timerRunning, active?.id]);

  const uploadAvatar = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("avatar", file);
    await apiUpload("/avatar", fd);
    onRefresh();
  };

  const runBusy = async (key, fn) => {
    if (busy) return;
    setBusy(key);
    try {
      await fn();
    } catch (ex) {
      alert(ex.message);
    } finally {
      setBusy(null);
    }
  };

  const toggleTimer = async () => {
    if (!active || active.status !== "active") return;
    await runBusy("timer", async () => {
      await apiPost(`/games/${active.id}/timer`, {});
      onRefresh();
    });
  };

  const saveReview = async () => {
    if (!active) return;
    const ratingNum = parseRating(rating);
    if (ratingNum == null) return;
    await runBusy("review", async () => {
      await apiPost(`/games/${active.id}/review`, { review, rating: ratingNum });
      onRefresh();
    });
  };

  const ratingNum = parseRating(rating);
  const canComplete =
    review.trim().length > 0 && ratingNum != null && ratingNum >= 1 && ratingNum <= 10;

  const complete = async () => {
    if (!active || !canComplete || busy) return;
    await runBusy("complete", async () => {
      const data = await apiPost(`/games/${active.id}/complete`, {
        review,
        rating: ratingNum,
      });
      await onRefresh?.();
      onGameCompleted?.(data);
      onClose();
    });
  };

  const drop = async () => {
    if (!active || busy) return;
    await runBusy("drop", async () => {
      await apiPost(`/games/${active.id}/drop`, {});
      onRefresh();
    });
  };

  const saveUsername = async () => {
    const next = nameDraft.trim();
    if (!next || next === playerName(profile)) {
      setEditingName(false);
      setNameDraft(playerName(profile));
      return;
    }
    await runBusy("rename", async () => {
      const data = await apiPatch("/me/display-name", { displayName: next });
      if (data.user) onUserSync?.(data.user);
      await onRefresh?.();
      setEditingName(false);
    });
  };

  const downloadGamesXlsx = async () => {
    if (!profile?.id) return;
    const safeName = playerName(profile).replace(/[^\w\u0400-\u04FF.\- ]+/gu, "_");
    await runBusy("xlsx", async () => {
      await downloadApiFile(
        `/players/${profile.id}/games.xlsx`,
        `${safeName}_games.xlsx`
      );
    });
  };

  const liveSeconds = active
    ? formatPlaySeconds(active.playSeconds, active.timerRunning, active.timerStartedAt)
    : null;

  const gameplayTags = (tags) => {
    if (!tags?.length) return null;
    return (
      <ul className="gameplay-tags">
        {tags.map((t, i) => (
          <li key={i} className="gameplay-tag">
            {typeof t === "string" ? t : t.label || t.name}
          </li>
        ))}
      </ul>
    );
  };

  return (
    <Modal title={playerName(profile)} onClose={onClose} wide casino>
      <div className="profile-casino">
      <div className="profile-hero-card">
        <div className="profile-avatar-wrap">
          <img src={profile?.avatarUrl} alt="" className="avatar-lg avatar-lg--vip" />
          <span className="profile-vip-badge">VIP</span>
          <span className="profile-high-roller">HIGH ROLLER</span>
        </div>
        <div>
          {isOwner && editingName ? (
            <div className="rename-row">
              <input
                className="input"
                value={nameDraft}
                maxLength={24}
                onChange={(e) => setNameDraft(e.target.value)}
                placeholder="Новое имя"
              />
              <div className="btn-row">
                <button
                  className="btn primary"
                  type="button"
                  disabled={!!busy || !nameDraft.trim()}
                  onClick={saveUsername}
                >
                  {busy === "rename" ? "Сохранение..." : "Сохранить"}
                </button>
                <button
                  className="btn"
                  type="button"
                  disabled={!!busy}
                  onClick={() => {
                    setEditingName(false);
                    setNameDraft(playerName(profile));
                  }}
                >
                  Отмена
                </button>
              </div>
            </div>
          ) : (
            <div className="profile-name-row">
              <h3 className="profile-username">{playerName(profile)}</h3>
              {isOwner && (
                <button
                  className="btn btn-sm"
                  type="button"
                  disabled={!!busy}
                  onClick={() => {
                    setNameDraft(playerName(profile));
                    setEditingName(true);
                  }}
                >
                  Сменить имя
                </button>
              )}
            </div>
          )}
          <div className="profile-stats-row">
            <div className="profile-stat-chip">
              <strong>{profile?.points ?? 0}</strong>
              <span>Очки</span>
            </div>
            <div className="profile-stat-chip">
              <strong>{profile?.completedCount ?? 0}</strong>
              <span>Пройдено</span>
            </div>
            <div className="profile-stat-chip">
              <strong>{profile?.droppedCount ?? 0}</strong>
              <span>Дроп</span>
            </div>
          </div>
          {isOwner && (
            <label className="btn btn-sm" style={{ marginTop: 10, display: "inline-block" }}>
              Сменить аватар
              <input type="file" hidden accept="image/*" onChange={uploadAvatar} />
            </label>
          )}
          <div className="profile-toolbar">
            <button
              className="btn"
              type="button"
              onClick={() => setShowInventory(true)}
            >
              Инвентарь
            </button>
            <button
              className="btn"
              type="button"
              onClick={async () => {
                const data = await apiGet(
                  `/players/${profile.id}/turn-history`
                );
                setTurnHistory(data.turnHistory || []);
                setShowHistory(true);
              }}
            >
              История ходов
            </button>
          </div>
        </div>
      </div>
      </div>
      {(inventory?.buffs?.length > 0 || inventory?.debuffs?.length > 0) && (
        <div className="profile-effects">
          <h4 className="profile-effects-title">Активные эффекты</h4>
          <div className="profile-effects-grid">
            {inventory.buffs.map((b) => (
              <span key={`b-${b.id}`} className="effect-pill buff">
                {b.displayLine || b.name}
              </span>
            ))}
            {inventory.debuffs.map((d) => (
              <span key={`d-${d.id}`} className="effect-pill debuff">
                {d.displayLine || d.name}
              </span>
            ))}
          </div>
        </div>
      )}
      {showHistory && (
        <TurnHistoryModal
          history={turnHistory}
          onClose={() => setShowHistory(false)}
        />
      )}
      {showInventory && (
        <InventoryModal
          inventory={inventory}
          players={players}
          cells={cells}
          playerPosition={profile?.position}
          currentUserId={currentUser?.id}
          turnPhase={currentUser?.turnPhase}
          isOwner={isOwner}
          onClose={() => setShowInventory(false)}
          onRefresh={onRefresh}
          onUserSync={onUserSync}
        />
      )}
      <div className="profile-games-head">
        <h3>Игры</h3>
        <button
          className="btn"
          type="button"
          disabled={!!busy || !games?.length}
          onClick={downloadGamesXlsx}
        >
          {busy === "xlsx" ? "Скачивание..." : "Скачать XLSX"}
        </button>
      </div>
      <ul className="game-feed">
        {gamesPaged.visible.map((g) => {
          const statusBadge =
            g.status === "active"
              ? { cls: "green", label: "В игре" }
              : g.status === "completed"
                ? { cls: "purple", label: "Прошёл" }
                : g.status === "dropped"
                  ? { cls: "red", label: "Дроп" }
                  : g.status === "pending_admin"
                    ? { cls: "orange", label: "Ждёт админа" }
                    : { cls: "gray", label: g.status };
          return (
            <li key={g.id} className="game-card game-card--casino">
              <div className="game-card-inner">
                <div className="game-card-head">
                  <span className={`badge ${statusBadge.cls}`}>{statusBadge.label}</span>
                  {g.isDurka && <span className="badge red">Дурка</span>}
                </div>
                <h4 className="game-card-title">{g.title}</h4>
                <p className="game-card-meta muted">
                  {g.cellName} · {g.genreLabel} · кубик {g.diceRoll ?? "—"}
                </p>
                {gameplayTags(g.gameplayTags)}
                {g.status !== "pending_admin" && (
                  <p className="game-card-stats">
                    HLTB: {g.hltbHours ?? "—"} ч · Время:{" "}
                    {formatPlaySeconds(g.playSeconds, g.timerRunning, g.timerStartedAt)}
                    {g.pointsEarned != null ? (
                      <>
                        {" · "}
                        <CasinoPoints value={g.pointsEarned} />
                      </>
                    ) : (
                      " · очки позже"
                    )}
                  </p>
                )}
                {g.review && g.status !== "pending_admin" && g.rating != null && (
                  <p className="game-card-review">
                    <span className="game-card-rating">{g.rating}/10</span> — {g.review}
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ul>
      <PagedListFooter
        hasMore={gamesPaged.hasMore}
        onLoadMore={gamesPaged.loadMore}
        shown={gamesPaged.shown}
        total={gamesPaged.total}
      />
      {isOwner && pendingAdmin && !active && (
        <div className="active-game-panel pending-admin-panel">
          <h4 className="active-game-title">Ожидает админа: {pendingAdmin.title}</h4>
          <p className="muted">
            Выпало на колесе — админ назначит финальную игру. После активации
            можно играть, писать отзыв и завершать прохождение.
          </p>
          <p className="muted">
            {pendingAdmin.cellName} · {pendingAdmin.genreLabel} · кубик{" "}
            {pendingAdmin.diceRoll}
          </p>
        </div>
      )}
      {isOwner && active && (
        <div className="active-game-panel active-game-panel--casino">
          <h4 className="active-game-title">Текущая: {active.title}</h4>
          {active.gameplayTags?.length > 0 && (
            <div className="active-game-tags">{gameplayTags(active.gameplayTags)}</div>
          )}
          <p className="timer-display">
            Таймер: <strong>{liveSeconds}</strong>
            {active.timerRunning ? " (идёт)" : ""}
          </p>
          <textarea
            className="input"
            rows={3}
            placeholder="Отзыв"
            value={review}
            onChange={(e) => setReview(e.target.value)}
          />
          <label className="field-label rating-label">Оценка 1–10</label>
          <input
            type="number"
            className="input rating-input"
            min={1}
            max={10}
            step={1}
            placeholder="1–10"
            value={rating}
            onChange={(e) => setRating(e.target.value)}
          />
          <div className="btn-row">
            <button
              className="btn"
              onClick={toggleTimer}
              disabled={!!busy}
            >
              {busy === "timer"
                ? "Загрузка..."
                : active.timerRunning
                  ? "Пауза"
                  : "Старт"}{" "}
              таймер
            </button>
            <button
              className="btn"
              onClick={saveReview}
              disabled={!!busy}
            >
              {busy === "review" ? "Загрузка..." : "Сохранить отзыв"}
            </button>
            <button
              className="btn primary"
              onClick={complete}
              disabled={!canComplete || !!busy}
            >
              {busy === "complete" ? "Загрузка..." : "Игра пройдена"}
            </button>
            <button
              className="btn danger"
              onClick={drop}
              disabled={!!busy}
            >
              {busy === "drop" ? "Загрузка..." : "Дроп игры"}
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
}

function Modal({ title, children, onClose, wide, casino = false }) {
  return (
    <motion.div
      className={`overlay${casino ? " overlay--casino" : ""}`}
      onClick={onClose}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
    >
      <motion.div
        className={`modal-panel ${wide ? "wide" : ""}${casino ? " modal-panel--casino" : ""}`}
        onClick={(e) => e.stopPropagation()}
        initial={{ opacity: 0, y: 28, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 16, scale: 0.98 }}
        transition={{ duration: 0.38, ease: [0.16, 1, 0.3, 1] }}
      >
        <header className={casino ? "modal-header--casino" : ""}>
          <div className="modal-header__title-group">
            {casino && (
              <VipChip label="VIP" variant="platinum" className="modal-header__chip" />
            )}
            <h2>{title}</h2>
          </div>
          <button type="button" className="close" onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        </header>
        <div className="modal-body">{children}</div>
      </motion.div>
    </motion.div>
  );
}

function parseRating(value) {
  if (value === "" || value == null) return null;
  const n = Number(value);
  if (!Number.isFinite(n) || n < 1 || n > 10) return null;
  return Math.round(n);
}

function parseUtcMs(iso) {
  if (!iso) return NaN;
  let s = String(iso).trim();
  if (!s.endsWith("Z") && !/[+-]\d{2}:\d{2}$/.test(s)) {
    s = `${s}Z`;
  }
  return new Date(s).getTime();
}

function formatPlaySeconds(baseSec, running, startedAtIso) {
  let s = Math.max(0, Math.floor(Number(baseSec) || 0));
  if (running && startedAtIso) {
    const started = parseUtcMs(startedAtIso);
    if (!Number.isNaN(started)) {
      s += Math.max(0, Math.floor((Date.now() - started) / 1000));
    }
  }
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return `${h} ч ${m} м ${sec} с`;
}
