import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../api";
import { playerName } from "../playerName";
import { PHASE_OPTIONS } from "../phaseLabels";

async function adminPatch(path, body) {
  const r = await fetch(`/api/admin${path}`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || "Ошибка");
  return data;
}

async function adminPost(path, body) {
  const r = await fetch(`/api/admin${path}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || "Ошибка");
  return data;
}

export default function AdminPanel({ onClose }) {
  const [players, setPlayers] = useState([]);
  const [items, setItems] = useState([]);
  const [board, setBoard] = useState([]);
  const [selected, setSelected] = useState(null);
  const [games, setGames] = useState([]);
  const [userForm, setUserForm] = useState({});
  const [gameForm, setGameForm] = useState(null);
  const [msg, setMsg] = useState("");
  const [grantItemId, setGrantItemId] = useState("1");
  const [grantQty, setGrantQty] = useState("1");
  const [statusItemId, setStatusItemId] = useState("3");
  const [statusTurns, setStatusTurns] = useState("2");
  const [customPolarity, setCustomPolarity] = useState("debuff");
  const [customLabel, setCustomLabel] = useState("");
  const [customKey, setCustomKey] = useState("dice_penalty_next");
  const [customVal, setCustomVal] = useState("1");
  const [moveCell, setMoveCell] = useState("0");
  const [playerInv, setPlayerInv] = useState({ items: [], buffs: [], debuffs: [] });

  const loadPlayerInventory = async (playerId) => {
    const inv = await apiGet(`/admin/users/${playerId}/inventory`);
    setPlayerInv(inv);
    return inv;
  };

  const load = async () => {
    const list = await apiGet("/admin/players");
    setPlayers(list);
  };

  useEffect(() => {
    load();
    apiGet("/admin/items").then(setItems).catch(() => {});
    apiGet("/admin/board").then(setBoard).catch(() => {});
  }, []);

  const pickPlayer = async (p) => {
    setSelected(p);
    setUserForm({ ...p });
    setMoveCell(String(p.position ?? 0));
    const data = await apiGet(`/players/${p.id}`);
    setGames(data.games);
    const active = (data.games || []).find((g) => g.status === "active");
    setGameForm(active ? { ...active } : null);
    await loadPlayerInventory(p.id);
  };

  const refreshPlayer = async () => {
    if (!selected) return;
    await pickPlayer(selected);
    load();
  };

  const saveUser = async () => {
    await adminPatch(`/users/${selected.id}`, userForm);
    setMsg("Игрок сохранён");
    load();
  };

  const movePlayer = async () => {
    const res = await adminPost(`/users/${selected.id}/move`, {
      cellId: parseInt(moveCell, 10),
    });
    setMsg(`Перемещён на ${res.cell?.name || moveCell}`);
    setUserForm((f) => ({ ...f, position: res.user.position }));
    load();
  };

  const grantItem = async () => {
    await adminPost(`/users/${selected.id}/grant-item`, {
      itemId: parseInt(grantItemId, 10),
      quantity: parseInt(grantQty, 10) || 1,
    });
    setMsg("Предмет выдан");
    refreshPlayer();
  };

  const applyStatusFromItem = async () => {
    await adminPost(`/users/${selected.id}/apply-status`, {
      itemId: parseInt(statusItemId, 10),
      turns: parseInt(statusTurns, 10) || 1,
    });
    setMsg("Статус навешен");
    refreshPlayer();
  };

  const applyCustomStatus = async () => {
    await adminPost(`/users/${selected.id}/apply-status`, {
      polarity: customPolarity,
      label: customLabel || customKey,
      effectKey: customKey,
      effectValue: customVal,
      turns: parseInt(statusTurns, 10) || 1,
    });
    setMsg("Кастомный эффект навешен");
    refreshPlayer();
  };

  const clearBuffs = async () => {
    await adminPost(`/users/${selected.id}/clear-status`, {
      polarity: "buff",
    });
    setMsg("Баффы сняты");
    refreshPlayer();
  };

  const clearDebuffs = async () => {
    await adminPost(`/users/${selected.id}/clear-status`, {
      polarity: "debuff",
    });
    setMsg("Дебаффы сняты");
    refreshPlayer();
  };

  const removeItem = async (itemId) => {
    await adminPost(`/users/${selected.id}/remove-item`, { itemId });
    setMsg("Предмет удалён");
    refreshPlayer();
  };

  const removeModifier = async (modifierId) => {
    await adminPost(`/users/${selected.id}/clear-status`, { modifierId });
    setMsg("Эффект снят");
    refreshPlayer();
  };

  const pickGame = (g) => setGameForm({ ...g });

  const saveGame = async () => {
    await adminPatch(`/games/${gameForm.id}`, gameForm);
    setMsg("Игра сохранена");
    const data = await apiGet(`/players/${selected.id}`);
    setGames(data.games);
  };

  const reloadData = async () => {
    try {
      const res = await adminPost("/reload-data", {});
      setMsg(
        `data/ перечитана: предметов ${res.items}, GIF в пуле ${res.gifPoolSize}. ${res.note || ""}`
      );
      apiGet("/admin/items").then(setItems).catch(() => {});
    } catch (ex) {
      setMsg(ex.message);
    }
  };

  return (
    <div className="overlay overlay--casino" onClick={onClose}>
      <div
        className="modal-panel wide admin-panel modal-panel--casino"
        onClick={(e) => e.stopPropagation()}
      >
        <header>
          <h2>Админ-панель</h2>
          <button type="button" className="btn btn-sm" onClick={reloadData}>
            Перечитать data/
          </button>
          <button type="button" className="close" onClick={onClose}>
            ×
          </button>
        </header>
        <div className="modal-body admin-body">
          {msg && <p className="success-msg">{msg}</p>}
          <div className="admin-columns">
            <div>
              <h3>Игроки</h3>
              <ul className="admin-player-list">
                {players.map((p) => (
                  <li key={p.id}>
                    <button
                      type="button"
                      className={selected?.id === p.id ? "active" : ""}
                      onClick={() => pickPlayer(p)}
                    >
                      {playerName(p)} ({p.points}⚡) · кл.{p.position}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
            {selected && (
              <div className="admin-editor">
                <h3>{playerName(selected)}</h3>
                <p className="muted">Логин: {selected.username}</p>

                <div className="admin-block">
                  <h4>Перемещение</h4>
                  <select
                    className="input select-styled"
                    value={moveCell}
                    onChange={(e) => setMoveCell(e.target.value)}
                  >
                    {board.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.id}: {c.name} ({c.type})
                      </option>
                    ))}
                  </select>
                  <button type="button" className="btn primary" onClick={movePlayer}>
                    Переместить на клетку
                  </button>
                </div>

                <div className="admin-block">
                  <h4>Инвентарь и эффекты</h4>
                  <p className="muted admin-inv-hint">
                    Точечное снятие предметов и активных баффов/дебаффов.
                  </p>
                  <div className="admin-inv-section">
                    <h5>Предметы</h5>
                    {playerInv.items?.length ? (
                      <ul className="admin-inv-list">
                        {playerInv.items.map((it) => (
                          <li key={it.itemId} className="admin-inv-row">
                            <span>
                              #{it.itemId} {it.name}
                              {it.charges != null ? ` · ${it.charges} зар.` : ""}
                              {it.isTrap ? " · ловушка" : ""}
                            </span>
                            <button
                              type="button"
                              className="btn btn-sm danger"
                              onClick={() => removeItem(it.itemId)}
                            >
                              Удалить
                            </button>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="muted">Пусто</p>
                    )}
                  </div>
                  <div className="admin-inv-section">
                    <h5>Баффы</h5>
                    {playerInv.buffs?.length ? (
                      <ul className="admin-inv-list">
                        {playerInv.buffs.map((b) => (
                          <li key={b.id} className="admin-inv-row">
                            <span>{b.displayLine || b.name}</span>
                            <button
                              type="button"
                              className="btn btn-sm danger"
                              onClick={() => removeModifier(b.id)}
                            >
                              Снять
                            </button>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="muted">Нет</p>
                    )}
                  </div>
                  <div className="admin-inv-section">
                    <h5>Дебаффы</h5>
                    {playerInv.debuffs?.length ? (
                      <ul className="admin-inv-list">
                        {playerInv.debuffs.map((b) => (
                          <li key={b.id} className="admin-inv-row">
                            <span>{b.displayLine || b.name}</span>
                            <button
                              type="button"
                              className="btn btn-sm danger"
                              onClick={() => removeModifier(b.id)}
                            >
                              Снять
                            </button>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="muted">Нет</p>
                    )}
                  </div>
                </div>

                <div className="admin-block">
                  <h4>Выдать предмет</h4>
                  <select
                    className="input select-styled"
                    value={grantItemId}
                    onChange={(e) => setGrantItemId(e.target.value)}
                  >
                    {items.map((it) => (
                      <option key={it.id} value={it.id}>
                        #{it.id} {it.name}
                      </option>
                    ))}
                  </select>
                  <input
                    className="input"
                    type="number"
                    min={1}
                    value={grantQty}
                    onChange={(e) => setGrantQty(e.target.value)}
                    placeholder="кол-во / заряды"
                  />
                  <button type="button" className="btn" onClick={grantItem}>
                    Выдать
                  </button>
                </div>

                <div className="admin-block">
                  <h4>Бафф / дебафф из каталога</h4>
                  <select
                    className="input select-styled"
                    value={statusItemId}
                    onChange={(e) => setStatusItemId(e.target.value)}
                  >
                    {items.map((it) => (
                      <option key={it.id} value={it.id}>
                        #{it.id} {it.name} ({it.polarity})
                      </option>
                    ))}
                  </select>
                  <input
                    className="input"
                    type="number"
                    min={1}
                    value={statusTurns}
                    onChange={(e) => setStatusTurns(e.target.value)}
                    placeholder="ходов"
                  />
                  <button type="button" className="btn" onClick={applyStatusFromItem}>
                    Навесить
                  </button>
                </div>

                <div className="admin-block">
                  <h4>Свой эффект</h4>
                  <select
                    className="input select-styled"
                    value={customPolarity}
                    onChange={(e) => setCustomPolarity(e.target.value)}
                  >
                    <option value="buff">Бафф</option>
                    <option value="debuff">Дебафф</option>
                  </select>
                  <input
                    className="input"
                    placeholder="Название"
                    value={customLabel}
                    onChange={(e) => setCustomLabel(e.target.value)}
                  />
                  <input
                    className="input"
                    placeholder="effectKey"
                    value={customKey}
                    onChange={(e) => setCustomKey(e.target.value)}
                  />
                  <input
                    className="input"
                    placeholder="effectValue"
                    value={customVal}
                    onChange={(e) => setCustomVal(e.target.value)}
                  />
                  <button type="button" className="btn" onClick={applyCustomStatus}>
                    Навесить свой
                  </button>
                  <div className="btn-row">
                    <button type="button" className="btn" onClick={clearBuffs}>
                      Снять все баффы
                    </button>
                    <button type="button" className="btn" onClick={clearDebuffs}>
                      Снять все дебаффы
                    </button>
                  </div>
                </div>

                <div className="admin-fields">
                  {[
                    ["points", "Очки"],
                    ["position", "Позиция"],
                    ["completedCount", "Пройдено"],
                    ["droppedCount", "Дроп"],
                    ["laps", "Круги"],
                  ].map(([key, label]) => (
                    <label key={key}>
                      {label}
                      <input
                        className="input"
                        value={
                          userForm[key] ??
                          userForm[key.replace(/[A-Z]/g, (m) => `_${m.toLowerCase()}`)] ??
                          ""
                        }
                        onChange={(e) =>
                          setUserForm({
                            ...userForm,
                            [key]: e.target.value,
                          })
                        }
                      />
                    </label>
                  ))}
                  <label>
                    Фаза хода
                    <select
                      className="input select-styled"
                      value={userForm.turnPhase ?? "idle"}
                      onChange={(e) =>
                        setUserForm({ ...userForm, turnPhase: e.target.value })
                      }
                    >
                      {PHASE_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={!!userForm.inDurka || !!userForm.in_durka}
                      onChange={(e) =>
                        setUserForm({
                          ...userForm,
                          inDurka: e.target.checked,
                          in_durka: e.target.checked,
                        })
                      }
                    />{" "}
                    В дурке
                  </label>
                </div>
                <button type="button" className="btn primary" onClick={saveUser}>
                  Сохранить игрока
                </button>

                <h4>Игры</h4>
                <ul className="admin-game-list">
                  {games.map((g) => (
                    <li key={g.id}>
                      <button
                        type="button"
                        className={
                          gameForm?.id === g.id
                            ? "active"
                            : g.status === "active"
                              ? "active-game"
                              : g.status === "pending_admin"
                                ? "pending-admin-game"
                                : ""
                        }
                        onClick={() => pickGame(g)}
                      >
                        {g.title} [{g.status}]
                        {g.status === "active" ? " · текущая" : ""}
                        {g.status === "pending_admin" ? " · назначит админ" : ""}
                      </button>
                    </li>
                  ))}
                </ul>
                {gameForm && (
                  <div className="admin-game-form">
                    <h4>
                      {gameForm.status === "active"
                        ? "Текущая игра"
                        : "Редактирование игры"}
                    </h4>
                    {[
                      ["title", "Название"],
                      ["status", "Статус"],
                      ["cell_name", "Клетка"],
                      ["dice_roll", "Кубик"],
                      ["review", "Отзыв"],
                      ["rating", "Оценка"],
                      ["points_earned", "Очки за игру"],
                      ["play_seconds", "Секунд в игре"],
                    ].map(([key, label]) => (
                      <label key={key}>
                        {label}
                        <input
                          className="input"
                          value={gameForm[key] ?? ""}
                          onChange={(e) =>
                            setGameForm({
                              ...gameForm,
                              [key]: e.target.value,
                            })
                          }
                        />
                      </label>
                    ))}
                    <label>
                      HLTB (часы, вручную если не подтянулось)
                      <input
                        className="input"
                        type="number"
                        step="0.1"
                        min="0"
                        placeholder="например 12.5"
                        value={gameForm.hltb_hours ?? ""}
                        onChange={(e) =>
                          setGameForm({
                            ...gameForm,
                            hltb_hours:
                              e.target.value === ""
                                ? null
                                : parseFloat(e.target.value),
                          })
                        }
                      />
                    </label>
                    <label>
                      Время судьи (часы)
                      <input
                        className="input"
                        type="number"
                        step="0.1"
                        min="0"
                        value={gameForm.judge_hours ?? ""}
                        onChange={(e) =>
                          setGameForm({
                            ...gameForm,
                            judge_hours:
                              e.target.value === ""
                                ? null
                                : parseFloat(e.target.value),
                          })
                        }
                      />
                    </label>
                    <button
                      type="button"
                      className="btn primary"
                      onClick={saveGame}
                    >
                      Сохранить игру
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
