import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../api";
import { fetchGenres } from "../genres";
import { playerName } from "../playerName";
import GenrePicker from "./GenrePicker";
import ItemIcon from "./ItemIcon";
import VipChip from "../ui/VipChip";

const LOADING = "Загрузка...";
const GENRE_PICK_ITEMS = new Set([15]);
const LAW_ITEMS = new Set([40, 41]);
const WHEEL_READY_ONLY = new Set([15, 24, 25, 40, 41]);

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
          {selected.flavor && (
            <p className="inv-flavor">{selected.flavor}</p>
          )}
          {selected.gameplayHint && selected.gameplayHint !== selected.name && (
            <p className="inv-gameplay-hint">{selected.gameplayHint}</p>
          )}
          {selected.durationLabel && (
            <p className="muted">{selected.durationLabel}</p>
          )}
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
  turnPhase,
  isOwner,
  onClose,
  onRefresh,
  onUserSync,
}) {
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState(null);
  const [targetName, setTargetName] = useState("");
  const [partnerName, setPartnerName] = useState("");
  const [repairTargetId, setRepairTargetId] = useState("");
  const [chocolateGenreId, setChocolateGenreId] = useState("");
  const [genres, setGenres] = useState([]);
  const [explosivesAlert, setExplosivesAlert] = useState(null);

  useEffect(() => {
    fetchGenres(apiGet).then(setGenres);
  }, []);

  const postUse = async (body) => {
    const data = await apiPost("/inventory/use", body);
    if (data.explosivesRoll) {
      const title =
        data.explosivesMessage ||
        (data.explosivesRoll === "survived" ? "ВЫ УЦЕЛЕЛИ" : "ВЫ ВЗОРВАЛИСЬ");
      const detail =
        data.explosivesRoll === "survived"
          ? "Эффект предмета сработал. Заряд предмета и взрывчатки списаны."
          : "Эффект предмета не сработал. Заряд предмета и взрывчатки всё равно списаны.";
      setExplosivesAlert({ title, detail, ok: data.explosivesRoll === "survived" });
    }
    if (data.user) onUserSync?.(data.user);
    await onRefresh?.();
    setSelected(null);
    return data;
  };

  const useSelected = async (extra = {}) => {
    if (!selected || busy) return;
    const item = selected;

    const partner =
      item.itemId === 11
        ? (players || []).find(
            (p) =>
              p.id !== currentUserId &&
              playerName(p).toLowerCase() === partnerName.trim().toLowerCase()
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
      if (WHEEL_READY_ONLY.has(item.itemId) && turnPhase !== "wheel_ready") {
        alert(
          "Используйте после броска кубика, перед открытием колеса"
        );
        return;
      }
      if (GENRE_PICK_ITEMS.has(item.itemId) && !chocolateGenreId) {
        alert("Выберите категорию игр");
        return;
      }
      await postUse({
        itemId: item.itemId,
        targetUsername: targetName.trim() || undefined,
        partnerUsername: item.itemId === 11 ? partner.username : undefined,
        partnerUserId: item.itemId === 11 ? partner.id : undefined,
        targetItemId:
          item.itemId === 9 ? parseInt(repairTargetId, 10) : undefined,
        genreId: GENRE_PICK_ITEMS.has(item.itemId)
          ? parseInt(chocolateGenreId, 10)
          : undefined,
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
    setChocolateGenreId("");
    setSelected((prev) =>
      prev?.itemId === item.itemId && prev?.isTrap === item.isTrap ? null : item
    );
  };

  return (
    <>
      {explosivesAlert && (
        <div className="overlay overlay-spectate overlay--casino explosives-overlay">
          <div
            className={`modal-square explosives-modal modal-panel--casino ${
              explosivesAlert.ok ? "explosives-survived" : "explosives-boom"
            }`}
          >
            <h2>{explosivesAlert.title}</h2>
            <p>{explosivesAlert.detail}</p>
            <button
              type="button"
              className="btn primary"
              onClick={() => setExplosivesAlert(null)}
            >
              Понятно
            </button>
          </div>
        </div>
      )}
    <div className="overlay overlay--casino" onClick={onClose}>
      <div
        className="modal-panel wide inventory-panel modal-panel--casino"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="modal-header--casino inventory-header--vip">
          <div className="modal-header__title-group modal-header__title-group--stack">
            <div className="modal-header__title-row">
              <VipChip label="VAULT" variant="platinum" pulse className="modal-header__chip" />
              <h2>Сейф предметов</h2>
            </div>
            <p className="inventory-vip-sub">PRIVATE VAULT · INSURED LOOT</p>
          </div>
          <button type="button" className="close" onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        </header>
        <div className="modal-body inventory-body">
          <div className="inventory-casino-layout">
          <div className="inventory-felt-panel">
          <section className="inv-section">
            <h3 className="inv-section-title">Баффы</h3>
            <StatusRow entries={inventory?.buffs || []} polarity="buff" />
          </section>

          <section className="inv-section">
            <h3 className="inv-section-title">Дебаффы</h3>
            <StatusRow entries={inventory?.debuffs || []} polarity="debuff" />
          </section>
          </div>

          <div className="inventory-items-panel">
          <section className="inv-section">
            <h3 className="inv-section-title">Предметы</h3>
            <p className="muted inv-hint">
              Выберите предмет и нажмите «Использовать».
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
                        quantity={it.quantity}
                        charges={it.charges}
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
              <div className="inv-detail-head">
                <ItemIcon
                  itemId={selected.itemId}
                  title={selected.name}
                  large
                />
                <h4>
                  {selected.name}
                  {selected.isTrap ? " (ловушка)" : ""}
                </h4>
              </div>
              {selected.flavor && (
                <p className="inv-flavor">{selected.flavor}</p>
              )}
              <p className="inv-mechanics">{selected.description || "—"}</p>
              <p className="muted">В наличии: {selected.quantity ?? 1}</p>
              {selected.charges != null &&
                (selected.chargesPerUnit > 1 ||
                  selected.charges !== (selected.quantity ?? 1)) && (
                  <p className="muted">
                    Осталось использований: {selected.charges}
                  </p>
                )}

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
                          {it.name} (×{it.quantity})
                        </button>
                      ))}
                  </div>
                </>
              )}

              {isOwner && selected && GENRE_PICK_ITEMS.has(selected.itemId) && (
                <>
                  {turnPhase !== "wheel_ready" ? (
                    <p className="muted inv-hint">
                      Доступно только после броска кубика, перед колесом игр.
                    </p>
                  ) : (
                    <>
                      <label className="field-label">Жанр</label>
                      <GenrePicker
                        genres={genres}
                        value={chocolateGenreId}
                        onChange={setChocolateGenreId}
                        disabled={busy}
                        layout="grid"
                      />
                    </>
                  )}
                </>
              )}

              {isOwner && selected && LAW_ITEMS.has(selected.itemId) && (
                <p className="muted inv-hint">
                  После использования выберите категорию слева в панели хода и
                  роллите игру.
                </p>
              )}

              {isOwner && selected && [24, 25].includes(selected.itemId) && (
                <p className="muted inv-hint">
                  После использования откройте колесо приколов на этой клетке.
                </p>
              )}

              {isOwner && selected.itemId !== 11 && (
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
                              onClick={() => setTargetName(playerName(p))}
                            >
                              {playerName(p)}
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
                          onClick={() => setPartnerName(playerName(p))}
                        >
                          {playerName(p)}
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

            </section>
          )}
          </div>
          </div>
        </div>
      </div>
    </div>
    </>
  );
}
