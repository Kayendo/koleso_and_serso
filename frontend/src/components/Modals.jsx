import { useEffect, useState } from "react";
import { apiGet, apiPost, apiUpload } from "../api";
import InventoryModal from "./InventoryModal";
import TurnHistoryModal from "./TurnHistoryModal";
import PagedListFooter, { usePagedSlice } from "./PagedListFooter";

export function RulesModal({ html, onClose }) {
  return (
    <Modal title="Правила Игрополиуса" onClose={onClose}>
      <div className="rules-content" dangerouslySetInnerHTML={{ __html: html }} />
    </Modal>
  );
}

export function HistoryModal({ items, onClose }) {
  return (
    <Modal title="История игр" onClose={onClose} wide>
      <div className="history-list">
        {items.map((g) => (
          <article key={g.id} className="history-card">
            <div className="badges">
              <span className="badge purple">{g.username}</span>
              <span
                className={`badge ${g.status === "completed" ? "green" : g.status === "dropped" ? "red" : "gray"}`}
              >
                {g.status === "completed"
                  ? "Прошёл"
                  : g.status === "dropped"
                    ? "Дропнул"
                    : "Играет"}
              </span>
              {g.isDurka && <span className="badge red">Дурка</span>}
            </div>
            <h4>{g.title}</h4>
            <p className="muted">
              {g.cellName} · кубик {g.diceRoll}
              {g.pointsEarned != null ? ` · +${g.pointsEarned}⚡` : ""}
            </p>
            {g.review && <p>{g.review}</p>}
          </article>
        ))}
      </div>
    </Modal>
  );
}

export function StatsModal({ rows, onClose }) {
  return (
    <Modal title="Статистика" onClose={onClose} wide>
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
              <td>{r.username}</td>
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
    <Modal title="Логин в Игрополиус" onClose={onClose}>
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
              className="input"
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
        <p className="muted login-hint">
          Аккаунты заданы в <code>backend/accounts.py</code>
        </p>
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
}) {
  const isOwner = currentUser?.id === profile?.id;
  const [showInventory, setShowInventory] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [turnHistory, setTurnHistory] = useState([]);
  const active = games.find((g) => g.status === "active");
  const [review, setReview] = useState(active?.review || "");
  const [rating, setRating] = useState(
    active?.rating != null ? String(active.rating) : ""
  );
  const [tick, setTick] = useState(0);
  const [busy, setBusy] = useState(null);
  const gamesPaged = usePagedSlice(games);

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
    <Modal title={profile?.username} onClose={onClose} wide>
      <div className="profile-head">
        <img src={profile?.avatarUrl} alt="" className="avatar-lg" />
        {isOwner && (
          <label className="btn">
            Сменить аватар
            <input type="file" hidden accept="image/*" onChange={uploadAvatar} />
          </label>
        )}
        <div>
          <p>Очки: {profile?.points}⚡</p>
          <p>
            Пройдено {profile?.completedCount} · Дроп {profile?.droppedCount}
          </p>
          <div className="btn-row profile-actions">
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
      {(inventory?.buffs?.length > 0 || inventory?.debuffs?.length > 0) && (
        <div className="profile-effects">
          <h4 className="profile-effects-title">Активные эффекты</h4>
          <div className="profile-effects-grid">
            {inventory.buffs.map((b) => (
              <span key={`b-${b.id}`} className="effect-pill buff">
                {b.gameplayHint || b.name}
              </span>
            ))}
            {inventory.debuffs.map((d) => (
              <span key={`d-${d.id}`} className="effect-pill debuff">
                {d.gameplayHint || d.name}
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
          isOwner={isOwner}
          onClose={() => setShowInventory(false)}
          onRefresh={onRefresh}
        />
      )}
      <h3>Игры</h3>
      <ul className="game-feed">
        {gamesPaged.visible.map((g) => (
          <li key={g.id} className="game-card">
            <div className="game-card-head">
              <span>{g.status}</span>
              {g.isDurka && <span className="badge red">дурка</span>}
            </div>
            <h4>{g.title}</h4>
            <p className="muted">
              {g.cellName} · {g.genreLabel} · кубик {g.diceRoll}
            </p>
            {gameplayTags(g.gameplayTags)}
            <p>
              HLTB: {g.hltbHours ?? "—"} ч · Время:{" "}
              {formatPlaySeconds(g.playSeconds, g.timerRunning, g.timerStartedAt)}
              {g.pointsEarned != null
                ? ` · +${g.pointsEarned}⚡`
                : " · очки позже"}
            </p>
            {g.review && (
              <p>
                {g.rating}/10 — {g.review}
              </p>
            )}
          </li>
        ))}
      </ul>
      <PagedListFooter
        hasMore={gamesPaged.hasMore}
        onLoadMore={gamesPaged.loadMore}
        shown={gamesPaged.shown}
        total={gamesPaged.total}
      />
      {isOwner && active && (
        <div className="active-game-panel">
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

function Modal({ title, children, onClose, wide }) {
  return (
    <div className="overlay" onClick={onClose}>
      <div
        className={`modal-panel ${wide ? "wide" : ""}`}
        onClick={(e) => e.stopPropagation()}
      >
        <header>
          <h2>{title}</h2>
          <button className="close" onClick={onClose}>
            ×
          </button>
        </header>
        <div className="modal-body">{children}</div>
      </div>
    </div>
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
