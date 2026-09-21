import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

window.scrollTo = vi.fn();

// Use the browser's storage, even on Node versions that expose their own global.
const browserWindow = (
  globalThis as typeof globalThis & { jsdom: { window: Window } }
).jsdom.window;
Object.defineProperty(window, "localStorage", {
  configurable: true,
  get: () => browserWindow.localStorage,
});

// jsdom does not implement the native dialog lifecycle.
HTMLDialogElement.prototype.showModal = function () {
  this.setAttribute("open", "");
};
HTMLDialogElement.prototype.close = function () {
  this.removeAttribute("open");
};
