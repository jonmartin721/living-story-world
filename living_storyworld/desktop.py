"""Desktop application launcher using PyWebView."""

import socket
import sys
import threading
import time

import uvicorn
import webview


class Server(uvicorn.Server):
    """Custom uvicorn server that runs in a thread."""

    def install_signal_handlers(self):
        pass


def is_server_ready(port: int, timeout: int = 10) -> bool:
    """Check if the server is ready to accept connections."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except (socket.error, ConnectionRefusedError):
            time.sleep(0.1)
    return False


def start_server(port: int = 8001):
    """Start the FastAPI server in a background thread."""
    config = uvicorn.Config(
        "living_storyworld.webapp:app", host="127.0.0.1", port=port, log_level="warning"
    )
    server = Server(config=config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server to be ready
    if not is_server_ready(port):
        print("ERROR: Server failed to start within 10 seconds")
        sys.exit(1)

    return server


def launch_desktop(port: int = 8001):
    """Launch the desktop application with PyWebView."""
    print("Starting Living Storyworld desktop app...")
    print(f"Platform: {sys.platform}")

    # Start FastAPI server in background
    try:
        server = start_server(port)
        print(f"✓ Server started on http://127.0.0.1:{port}")
    except Exception as e:
        print(f"ERROR: Failed to start server: {e}")
        if sys.platform == "win32":
            input("Press Enter to exit...")
        sys.exit(1)

    url = f"http://127.0.0.1:{port}"

    # Create and start the webview window
    try:
        print("Initializing window...")
        webview.create_window(
            "Living Storyworld",
            url,
            width=1280,
            height=1000,
            resizable=True,
            min_size=(800, 600),
        )
        print("Starting webview...")

        # Use edge on Windows, auto-detect on other platforms
        gui = "edgechromium" if sys.platform == "win32" else None
        webview.start(gui=gui)

    except Exception as e:
        print(f"ERROR: Failed to start webview: {e}")
        print(f"Error type: {type(e).__name__}")

        if sys.platform == "win32":
            # On Windows, show full traceback for debugging
            import traceback

            traceback.print_exc()

        print("\n" + "=" * 50)
        print("Fallback: Opening in browser instead...")
        if sys.platform == "linux":
            print("(Linux desktop mode requires GTK - using browser)")
        print("=" * 50)

        import webbrowser

        time.sleep(1)
        webbrowser.open(url)
        print(f"✓ Browser opened to {url}")
        print("\nServer is running. Press Ctrl+C to stop.")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
    finally:
        # Cleanup
        if hasattr(server, "should_exit"):
            server.should_exit = True

    sys.exit(0)


if __name__ == "__main__":
    launch_desktop()
