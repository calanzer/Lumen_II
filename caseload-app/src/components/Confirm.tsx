import { useState, type ReactNode } from "react";
import { Modal } from "./Modal";

interface ConfirmProps {
  title: string;
  body: ReactNode;
  confirmLabel: string;
  danger?: boolean;
  // When set, the user must type this exact text to enable the confirm button.
  typedConfirmation?: string;
  onConfirm: () => void | Promise<void>;
  onCancel: () => void;
}

export function Confirm({ title, body, confirmLabel, danger, typedConfirmation, onConfirm, onCancel }: ConfirmProps) {
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const ready = !typedConfirmation || typed.trim() === typedConfirmation;
  return (
    <Modal
      title={title}
      onClose={onCancel}
      actions={
        <>
          <button className="btn" onClick={onCancel}>
            Cancel
          </button>
          <button
            className={danger ? "btn btn-danger" : "btn btn-primary"}
            disabled={!ready || busy}
            onClick={async () => {
              setBusy(true);
              try {
                await onConfirm();
              } finally {
                setBusy(false);
              }
            }}
          >
            {confirmLabel}
          </button>
        </>
      }
    >
      <div>{body}</div>
      {typedConfirmation && (
        <div className="field" style={{ marginTop: 12 }}>
          <label htmlFor="typed-confirm">
            Type <strong>{typedConfirmation}</strong> to confirm
          </label>
          <input id="typed-confirm" type="text" value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" />
        </div>
      )}
    </Modal>
  );
}
