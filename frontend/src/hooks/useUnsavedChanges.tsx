import { useEffect, useState } from "react";
import { Dialog } from "../components/Dialog";

export function useUnsavedChanges(dirty: boolean, onClose: () => void) {
  const [confirming, setConfirming] = useState(false);
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  const close = () => (dirty ? setConfirming(true) : onClose());
  const confirmation = confirming && (
    <Dialog title="Leave without saving?" onClose={() => setConfirming(false)}>
      <p>Your changes have not been saved.</p>
      <div className="editor__actions">
        <button
          type="button"
          className="button"
          onClick={() => setConfirming(false)}
        >
          Keep editing
        </button>
        <button
          type="button"
          className="button button--ghost"
          onClick={onClose}
        >
          Discard changes
        </button>
      </div>
    </Dialog>
  );
  return { close, confirmation };
}
