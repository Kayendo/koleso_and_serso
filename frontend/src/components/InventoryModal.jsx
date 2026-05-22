import { useMemo, useState } from "react";
import { apiPost } from "../api";

const LOADING = "Загрузка...";
const CLOVER_TYPES = new Set(["trallalero", "lottery", "question"]);

function ItemIcon({ itemId, title, selected }) {
  return (
    <div
      className={`inv-icon ${selected ? "inv-icon-selected" : ""}`}
      title={title}
    >
      {itemId}
    </div>
  );
}

function StatusRow({ entries, polarity }) {
  const [selectedId, setSelectedId] = useState(null);
  const selected = entries.find((e) => e.id === selectedId);

  return (
    <div className="inv-status-block">
      <div className="inv-status-row">
        {entries.length ? (
          entries.map((e) => (
            <button
              key={e.id}
              type="button"
              className={`inv-status-chip ${polarity} ${
                selectedId === e.id ? "selected" : ""
              }`}
              onClick={() => setSelectedId(selectedId === e.id ? null : e.id)}
            >
              <ItemIcon
                itemId={e.itemId ?? e.id}
                title={e.name}
                selected={selectedId === e.id}
              />
            </button>
          ))
        ) : (
          <span className="muted">Нет активных эффектов</span>
        )}
      </div>
      {selected && (
        <div className="inv-detail-panel inv-detail-compact">
          <strong>{selected.name}</strong>
          <p>{selected.description || "—"}</p>
          {selected.gameplayHint && (
            <p className="inv-gameplay-hint">{selected.gameplayHint}</p>
          )}
          <p className="muted">
            {selected.durationLabel
              ? `Срок: ${selected.durationLabel}`
              : `Осталось ходов: ${
                  selected.turnsRemaining > 0 ? selected.turnsRemaining : "∞"
                }`}
          </p>
        </div>
      )}
    </div>
  );
}

export default function InventoryModal({
  inventory,
  players,
  cells,
  playerPosition,
  currentUserId,
  isOwner,
  onClose,
  onRefresh,
}) {
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState(null);
  const [targetName, setTargetName] = useState("");
  const [partnerName, setPartnerName] = useState("");
  const [repairTargetId, setRepairTargetId] = useState("");

  const onCloverCell = useMemo(() => {
    const cell = cells?.find((c) => c.id === playerPosition);
    return cell && CLOVER_TYPES.has(cell.type);
  }, [cells, playerPosition]);

  const postUse = async (body) => {
    await apiPost("/inventory/use", body);
    await onRefresh?.();
    setSelected(null);
  };

  const useSelected = async (extra = {}) => {
    if (!selected || busy) return;
    const item = selected;

    const partner =
      item.itemId === 11
        ? (players || []).find(
            (p) =>
              p.id !== currentUserId &&
              p.username.toLowerCase() === partnerName.trim().toLowerCase()
          )
        : null;

    if (item.itemId === 11 && !partnerName.trim()) {
      alert("Введите имя партнёра для колец");
      return;
    }
    if (item.itemId === 11 && !partner) {
      alert("Игрок не найден — выберите из списка или введите точный ник");
      return;
    }
    if (item.isTrap && !targetName.trim()) {
      alert("Введите имя цели для ловушки");
      return;
    }

    setBusy(true);
    try {
      if (item.itemId === 9 && !repairTargetId) {
        alert("Выберите предмет для ремонта (не Шоколад)");
        return;
      }
      await postUse({
        itemId: item.itemId,
        targetUsername: targetName.trim() || undefined,
        partnerUsername: item.itemId === 11 ? partner.username : undefined,
        partnerUserId: item.itemId === 11 ? partner.id : undefined,
        targetItemId:
          item.itemId === 9 ? parseInt(repairTargetId, 10) : undefined,
        mode: extra.mode,
      });
      setTargetName("");
    } catch (ex) {
      alert(ex.message);
    } finally {
      setBusy(false);
    }
  };

  const selectItem = (item) => {
    setSelected((prev) =>
      prev?.itemId === item.itemId && prev?.isTrap === item.isTrap ? null : item
    );
  };

  const isClover = selected?.itemId === 13;

  return (
    <div className="overlay" onClick={onClose}>
      <div
        className="modal-panel wide inventory-panel"
        onClick={(e) => e.stopPropagation()}
      >
        <header>
          <h2>Инвентарь</h2>
          <button type="button" className="close" onClick={onClose}>
            ×
          </button>
        </header>
        <div className="modal-body inventory-body">
          <section className="inv-section">
            <h3>Баффы (влияют на прохождение)</h3>
            <StatusRow entries={inventory?.buffs || []} polarity="buff" />
          </section>

          <section className="inv-section">
            <h3>Дебаффы (влияют на прохождение)</h3>
            <StatusRow entries={inventory?.debuffs || []} polarity="debuff" />
          </section>

          <section className="inv-section">
            <h3>Предметы</h3>
            <p className="muted inv-hint">
              Нажмите на предмет, затем «Использовать» в панели ниже.
            </p>
            <div className="inv-grid">
              {(inventory?.items || []).length ? (
                inventory.items.map((it) => {
                  const isSel =
                    selected?.itemId === it.itemId &&
                    selected?.isTrap === it.isTrap;
                  return (
                    <button
                      key={`${it.itemId}-${it.isTrap}`}
                      type="button"
                      className={`inv-grid-cell ${isSel ? "selected" : ""}`}
                      onClick={() => selectItem(it)}
                    >
                      <ItemIcon
                        itemId={it.itemId}
                        title={it.name}
                        selected={isSel}
                      />
                      {it.quantity > 1 && (
                        <span className="inv-qty">×{it.quantity}</span>
                      )}
                    </button>
                  );
                })
              ) : (
                <span className="muted">Пусто</span>
              )}
            </div>
          </section>

          {selected && (
            <section className="inv-detail-panel">
              <h4>
                {selected.name}
                {selected.isTrap ? " (ловушка)" : ""}
              </h4>
              <p>{selected.description || "—"}</p>
              <p className="muted">
                Зарядов: {selected.charges ?? selected.quantity ?? 1}
              </p>

              {isOwner && selected.itemId === 9 && (
                <>
                  <label className="field-label">Починить предмет</label>
                  <div className="inv-repair-targets">
                    {(inventory?.items || [])
                      .filter((it) => it.itemId !== 9 && it.itemId !== 15)
                      .map((it) => (
                        <button
                          key={it.itemId}
                          type="button"
                          className={`btn ${
                            String(repairTargetId) === String(it.itemId)
                              ? "primary"
                              : ""
                          }`}
                          onClick={() => setRepairTargetId(String(it.itemId))}
                        >
                          #{it.itemId} {it.name} (×{it.quantity})
                        </button>
                      ))}
                  </div>
                </>
              )}

              {isOwner && !isClover && selected.itemId !== 11 && (
                <>
                  {selected.isTrap && (
                    <>
                      <label className="field-label">Имя цели</label>
                      <input
                        className="input"
                        value={targetName}
                        onChange={(e) => setTargetName(e.target.value)}
                        placeholder="ник игрока"
                      />
                      <div className="inv-trap-btns">
                        {(players || [])
                          .filter((p) => p.id !== currentUserId)
                          .map((p) => (
                            <button
                              key={p.id}
                              type="button"
                              className="btn"
                              onClick={() => setTargetName(p.username)}
                            >
                              {p.username}
                            </button>
                          ))}
                      </div>
                    </>
                  )}
                  <div className="inv-action-btns">
                    <button
                      type="button"
                      className="btn primary"
                      disabled={busy}
                      onClick={() => useSelected()}
                    >
                      {busy ? LOADING : "Использовать"}
                    </button>
                    <button
                      type="button"
                      className="btn"
                      onClick={() => setSelected(null)}
                    >
                      Снять выбор
                    </button>
                  </div>
                </>
              )}

              {isOwner && selected.itemId === 11 && (
                <>
                  <label className="field-label">Имя партнёра</label>
                  <input
                    className="input"
                    value={partnerName}
                    onChange={(e) => setPartnerName(e.target.value)}
                    placeholder="ник игрока"
                  />
                  <div className="inv-trap-btns">
                    {(players || [])
                      .filter((p) => p.id !== currentUserId)
                      .map((p) => (
                        <button
                          key={p.id}
                          type="button"
                          className="btn"
                          onClick={() => setPartnerName(p.username)}
                        >
                          {p.username}
                        </button>
                      ))}
                  </div>
                  <div className="inv-action-btns">
                    <button
                      type="button"
                      className="btn primary"
                      disabled={busy}
                      onClick={() => useSelected()}
                    >
                      {busy ? LOADING : "Связать кольца"}
                    </button>
                    <button
                      type="button"
                      className="btn"
                      onClick={() => setSelected(null)}
                    >
                      Снять выбор
                    </button>
                  </div>
                </>
              )}

              {isOwner && isClover && (
                <div className="inv-clover-actions">
                  <button
                    type="button"
                    className="btn"
                    disabled={busy}
                    onClick={() => useSelected({ mode: "block_trap" })}
                  >
                    Отбить ловушку
                  </button>
                  {onCloverCell ? (
                    <>
                      <button
                        type="button"
                        className="btn"
                        disabled={busy}
                        onClick={() => useSelected({ mode: "cell_bonus" })}
                      >
                        +2 очка (Траллалеро / Лотерея / ?)
                      </button>
                      <button
                        type="button"
                        className="btn"
                        disabled={busy}
                        onClick={() => useSelected({ mode: "cell_easy" })}
                      >
                        Лёгкая сложность
                      </button>
                    </>
                  ) : (
                    <p className="muted">
                      Бонусы клетки — только на Траллалеро, Лотерее или «?»
                    </p>
                  )}
                  <button
                    type="button"
                    className="btn"
                    onClick={() => setSelected(null)}
                  >
                    Снять выбор
                  </button>
                </div>
              )}
            </section>
          )}

        </div>
      </div>
    </div>
  );
}
