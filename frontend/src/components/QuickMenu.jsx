import { phaseLabel } from "../phaseLabels";

const LOADING = "Загрузка...";

export default function QuickMenu({
  onOpen,
  currentUser,
  onLogin,
  onLogout,
  hoverCell,
  turnError,
  actionLoading,
  onRollDice,
  onDurkaRoll,
  onOpenWheel,
  onOpenRewardWheel,
  rewardSpins = 0,
  rewardDiceRolled = false,
  onRollRewardDice,
}) {
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
  const isPlayer = currentUser?.isPlayer !== false;
  const busy = !!actionLoading;

  let turnButton = null;
  if (isPlayer && currentUser) {
    if (phase === "idle" && !currentUser.inDurka) {
      const loading = actionLoading === "dice";
      turnButton = (
        <button
          className="btn primary full"
          onClick={onRollDice}
          disabled={busy}
        >
          {loading ? LOADING : "Бросить кубик"}
        </button>
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
      turnButton = (
        <button
          className="btn primary full"
          onClick={onOpenWheel}
          disabled={busy}
        >
          {loading ? LOADING : "Крутить колесо / лотерея"}
        </button>
      );
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
      turnButton = (
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
            Вы: <strong>{currentUser.username}</strong>
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
