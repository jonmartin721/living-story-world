import { useLayoutEffect, useState } from "react";
import { createPortal } from "react-dom";
import type { Toast } from "../hooks/useToastQueue";

type ToastShelfProps = {
  toasts: Toast[];
  onDismiss: (id: string) => void;
};

export function ToastShelf({ toasts, onDismiss }: ToastShelfProps) {
  const [container, setContainer] = useState<Element>(document.body);
  useLayoutEffect(() => {
    const dialogs = document.querySelectorAll("dialog[open]");
    // Native modal dialogs sit above every normal stacking context.
    setContainer(dialogs[dialogs.length - 1] ?? document.body);
  });

  return createPortal(
    <div className="toast-shelf" aria-live="polite">
      {toasts.map((toast) => (
        <button
          key={toast.id}
          className={`toast toast--${toast.tone}`}
          onClick={() => onDismiss(toast.id)}
          type="button"
        >
          {toast.message}
        </button>
      ))}
    </div>,
    container,
  );
}
