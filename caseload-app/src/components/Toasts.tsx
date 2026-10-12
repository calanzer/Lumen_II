import { useSyncExternalStore } from "react";

interface Toast {
  id: number;
  message: string;
  undo?: () => void | Promise<void>;
}

let toasts: Toast[] = [];
let nextId = 1;
const subs = new Set<() => void>();
const emit = () => subs.forEach((f) => f());

function dismiss(id: number) {
  toasts = toasts.filter((t) => t.id !== id);
  emit();
}

export function toast(message: string, undo?: Toast["undo"]) {
  const id = nextId++;
  toasts = [...toasts, { id, message, undo }];
  emit();
  setTimeout(() => dismiss(id), undo ? 10_000 : 5_000);
}

export function Toasts() {
  const list = useSyncExternalStore(
    (f) => {
      subs.add(f);
      return () => subs.delete(f);
    },
    () => toasts,
  );
  return (
    <div className="toasts" role="status" aria-live="polite">
      {list.map((t) => (
        <div key={t.id} className="toast">
          <span>{t.message}</span>
          {t.undo && (
            <button
              className="btn-link"
              onClick={async () => {
                dismiss(t.id);
                await t.undo?.();
              }}
            >
              Undo
            </button>
          )}
          <button className="btn-link" aria-label="Dismiss" onClick={() => dismiss(t.id)}>
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}
