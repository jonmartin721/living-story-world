import type { Toast } from "../hooks/useToastQueue";

type ToastShelfProps = {
  toasts: Toast[];
  onDismiss: (id: string) => void;
};

export function ToastShelf({ toasts, onDismiss }: ToastShelfProps) {
  return (
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
    </div>
  );
}
