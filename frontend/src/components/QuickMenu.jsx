import { useEffect, useState } from "react";
import { apiGet } from "../api";
import { fetchGenres, genreButtonLabel } from "../genres";
import { phaseLabel } from "../phaseLabels";
import { playerName } from "../playerName";
import GenrePicker from "./GenrePicker";

const LOADING = "Загрузка...";

export default function QuickMenu({
  onOpen,
  currentUser,
  cells,
  onLogin,
  onLogout,
  hoverCell,
  turnError,
  actionLoading,
  onRollDice,
  onDurkaRoll,
  onOpenWheel,
  onOpenExtraWheel,
  onOpenRewardWheel,
  onDurkaStepForward,
  onDurkaStepBackward,
  rewardSpins = 0,
  rewardDiceRolled = false,
  onRollRewardDice,
}) {
  const [genres, setGenres] = useState([]);
  const [pickedGenreId, setPickedGenreId] = useState("");

  const adminFx = currentUser?.adminWheelEffect;
  const adminItemPending = currentUser?.adminItemGrantPending;

  useEffect(() => {
    fetchGenres(apiGet).then(setGenres);
  }, []);

  useEffect(() => {
    setPickedGenreId("");
  }, [adminFx?.itemId, adminFx?.genreId, currentUser?.position]);

  const currentCell = cells?.find((c) => c.id === currentUser?.position);
  const isBlazerd = currentCell?.companyKey === "blazerd";
  const isItemWheelCell = currentCell?.type === "trap_joy";

  const items = [
    { id: "rules", label: "Правила", icon: "📜" },
    { id: "history", label: "История игр", icon: "📋" },
    { id: "stats", label: "Статистика", icon: "📊" },
    {
      id: "login",
      label: currentUser ? "Выйти" : "Логин",
      icon: currentUser ? "🚪" : "👤",
    },
  ];

  if (currentUser?.isAdmin) {
    items.push({ id: "admin", label: "Админ-панель", icon: "⚙️" });
  }

  const phase = currentUser?.turnPhase;
  const ongoingGame = currentUser?.ongoingGame;
  const isPlayer = currentUser?.isPlayer !== false;
  const busy = !!actionLoading;

  const genreLocked = adminFx?.genreId != null;
  const needsGenrePick =
    (adminFx && !genreLocked) || (isBlazerd && !adminFx && !isItemWheelCell);

  const lockedGenreLabel =
    adminFx?.genreLabel ||
    genreButtonLabel(genres.find((g) => g.id === adminFx?.genreId));

  let turnButton = null;
  if (isPlayer && currentUser) {
    if (phase === "idle" && !currentUser.inDurka && !ongoingGame) {
      const onStart = currentUser.position === 0;
      const loading = actionLoading === "dice";
      turnButton = (
        <button
          className="btn primary full"
          onClick={onRollDice}
          disabled={busy}
        >
          {loading
            ? LOADING
            : onStart
              ? "Бросить кубик (старт)"
              : "Бросить кубик"}
        </button>
      );
    } else if (phase === "idle" && ongoingGame) {
      turnButton =
        ongoingGame.status === "pending_admin" ? (
          <p className="muted turn-hint">
            Игра «{ongoingGame.title}» ждёт назначения админом. Новый ход после
            прохождения.
          </p>
        ) : (
          <p className="muted turn-hint">
            Откройте профиль: отзыв и оценка → «Игра пройдена» или дроп
          </p>
        );
    } else if (phase === "durka_choice") {
      const loadingFwd = actionLoading === "durkaForward";
      const loadingBack = actionLoading === "durkaBack";
      turnButton = (
        <div className="durka-choice-buttons">
          <button
            className="btn primary full"
            onClick={onDurkaStepForward}
            disabled={busy}
          >
            {loadingFwd ? LOADING : "Шаг вперёд"}
          </button>
          <button
            className="btn primary full"
            onClick={onDurkaStepBackward}
            disabled={busy}
          >
            {loadingBack ? LOADING : "Шаг назад"}
          </button>
        </div>
      );
    } else if (phase === "durka") {
      const loading = actionLoading === "durka";
      turnButton = (
        <button
          className="btn primary full"
          onClick={onDurkaRoll}
          disabled={busy}
        >
          {loading ? LOADING : "Ролл в дурке"}
        </button>
      );
    } else if (phase === "wheel_ready") {
      const loading = actionLoading === "wheel";

      if (adminFx || needsGenrePick) {
        turnButton = (
          <div className="admin-wheel-turn">
            <p className="muted turn-hint">
              {adminFx
                ? `«${adminFx.name}» — выберите жанр и роллите игру`
                : "Выберите жанр и роллите игру"}
            </p>
            {!genreLocked && (
              <GenrePicker
                genres={genres}
                value={pickedGenreId}
                onChange={setPickedGenreId}
                disabled={busy}
              />
            )}
            {genreLocked && (
              <p className="muted turn-hint">Жанр: {lockedGenreLabel || "—"}</p>
            )}
            <button
              className="btn primary full"
              onClick={() => {
                const gid = genreLocked
                  ? adminFx.genreId
                  : pickedGenreId
                    ? parseInt(pickedGenreId, 10)
                    : null;
                if (!gid) return;
                onOpenWheel(gid);
              }}
              disabled={busy || (!genreLocked && !pickedGenreId)}
            >
              {loading ? LOADING : "Роллить игру"}
            </button>
          </div>
        );
      } else if (adminItemPending) {
        turnButton = (
          <p className="muted turn-hint">
            {adminItemPending.banner || adminItemPending.effectName}: предметы
            выдаст админ
          </p>
        );
      } else {
        const extras = currentUser.extraWheelSpinsRemaining ?? 0;
        turnButton = (
          <>
            {extras > 0 && (
              <button
                className="btn primary full"
                style={{ marginBottom: "0.5rem" }}
                onClick={() => onOpenExtraWheel?.()}
                disabled={busy}
              >
                {loading ? LOADING : `Колесо приколов (${extras})`}
              </button>
            )}
            <button
              className="btn primary full"
              onClick={() => onOpenWheel()}
              disabled={busy}
            >
              {loading ? LOADING : "Крутить колесо / лотерея"}
            </button>
          </>
        );
      }
    } else if (phase === "dice_choice") {
      turnButton = (
        <p className="muted turn-hint">Подтвердите выбор кубиков в окне</p>
      );
    } else if (phase === "rolling") {
      turnButton = (
        <button className="btn full" disabled>
          Дождитесь движения…
        </button>
      );
    } else if (phase === "wheel") {
      turnButton = (
        <button className="btn full" disabled>
          Колесо на экране
        </button>
      );
    } else if (phase === "reward_items") {
      if (!rewardDiceRolled) {
        const loading = actionLoading === "rewardDice";
        turnButton = (
          <button
            className="btn primary full"
            onClick={onRollRewardDice}
            disabled={busy}
          >
            {loading ? LOADING : "Призовой кубик"}
          </button>
        );
      } else {
        const loading = actionLoading === "reward";
        const n = rewardSpins;
        turnButton = (
          <button
            className="btn primary full"
            onClick={onOpenRewardWheel}
            disabled={busy || n <= 0}
          >
            {loading
              ? LOADING
              : n > 0
                ? `Призовое колесо (${n})`
                : "Призовые колёса закончились"}
          </button>
        );
      }
    } else if (phase === "playing") {
      turnButton =
        ongoingGame?.status === "pending_admin" ? (
          <p className="muted turn-hint">
            Игра «{ongoingGame.title}» ждёт назначения админом. Новый ход после
            прохождения.
          </p>
        ) : (
          <p className="muted turn-hint">
            Откройте профиль: отзыв и оценка → «Игра пройдена» или дроп
          </p>
        );
    }
  }

  return (
    <aside className="sidebar left">
      <h2>Быстрый доступ</h2>
      <p className="sidebar-time">
        {new Date().toLocaleTimeString("ru-RU")} MSK
      </p>
      <nav className="quick-menu">
        {items.map((it) => (
          <button
            key={it.id}
            className="quick-btn"
            onClick={() => {
              if (it.id === "login") {
                currentUser ? onLogout() : onLogin();
              } else {
                onOpen(it.id);
              }
            }}
          >
            <span>{it.icon}</span> {it.label}
          </button>
        ))}
      </nav>

      <div className="cell-info-panel">
        <h3>Клетка</h3>
        {hoverCell ? (
          <>
            <p className="cell-info-title">{hoverCell.name}</p>
            <p className="cell-info-genre">
              {hoverCell.genreLabel || hoverCell.type}
            </p>
          </>
        ) : (
          <p className="muted">Наведите курсор на клетку поля</p>
        )}
      </div>

      {isPlayer && currentUser && (
        <div className="turn-panel">
          <p>
            Вы: <strong>{playerName(currentUser)}</strong>
          </p>
          {phase && (
            <p className="muted phase-label">{phaseLabel(phase)}</p>
          )}
          {turnError && <p className="error">{turnError}</p>}
          {turnButton}
        </div>
      )}
    </aside>
  );
}
