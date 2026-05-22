import PagedListFooter, { usePagedSlice } from "./PagedListFooter";

export default function TurnHistoryModal({ history, onClose }) {
  const { visible, hasMore, loadMore, shown, total } = usePagedSlice(history);

  return (
    <div className="overlay" onClick={onClose}>
      <div
        className="modal-panel wide"
        onClick={(e) => e.stopPropagation()}
      >
        <header>
          <h2>История ходов</h2>
          <button type="button" className="close" onClick={onClose}>
            ×
          </button>
        </header>
        <div className="modal-body">
          <ul className="turn-log-list turn-log-list-tall">
            {visible.length ? (
              visible.map((t) => (
                <li key={t.id} className="turn-log-entry">
                  <strong>{t.summary}</strong>
                  {t.points != null && t.points > 0 && (
                    <span className="turn-points"> · +{t.points} очк.</span>
                  )}
                  {t.dice && <span className="muted"> · кубик {t.dice}</span>}
                  {t.cell && <span className="muted"> · {t.cell}</span>}
                  {t.factors?.length > 0 && (
                    <ul className="turn-factors">
                      {t.factors.map((f, i) => (
                        <li key={i}>{f}</li>
                      ))}
                    </ul>
                  )}
                </li>
              ))
            ) : (
              <li className="muted">Пока нет записей</li>
            )}
          </ul>
          <PagedListFooter
            hasMore={hasMore}
            onLoadMore={loadMore}
            shown={shown}
            total={total}
          />
        </div>
      </div>
    </div>
  );
}
