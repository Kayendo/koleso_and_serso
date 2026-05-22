import { useEffect, useState } from "react";

const PAGE = 5;

export function usePagedSlice(items, pageSize = PAGE) {
  const list = items || [];
  const [shown, setShown] = useState(pageSize);

  useEffect(() => {
    setShown(pageSize);
  }, [list, pageSize]);

  const visible = list.slice(0, shown);
  const hasMore = shown < list.length;
  const loadMore = () =>
    setShown((n) => Math.min(n + pageSize, list.length));

  return { visible, hasMore, loadMore, total: list.length, shown };
}

export default function PagedListFooter({
  hasMore,
  onLoadMore,
  shown,
  total,
}) {
  if (!total) return null;
  return (
    <div className="paged-list-footer">
      <span className="muted">
        Показано {Math.min(shown, total)} из {total}
      </span>
      {hasMore && (
        <button type="button" className="btn" onClick={onLoadMore}>
          Показать ещё
        </button>
      )}
    </div>
  );
}
