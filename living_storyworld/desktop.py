"""Desktop application launcher using PyWebView."""

import threading
import time
import sys
import socket
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
        "living_storyworld.webapp:app",
        host="127.0.0.1",
        port=port,
        log_level="warning"
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

    # Start FastAPI server in background
    server = start_server(port)
    print(f"Server started on http://127.0.0.1:{port}")

    url = f"http://127.0.0.1:{port}"

    # Create and start the webview window
    try:
        webview.create_window(
            "Living Storyworld",
            url,
            width=1280,
            height=800,
            resizable=True,
            min_size=(800, 600)
        )
        webview.start()
    except Exception as e:
        print(f"ERROR: Failed to start webview: {e}")
        print("\nTrying to open in browser instead...")
        import webbrowser
        webbrowser.open(url)
        print(f"Server running at {url}")
        print("Press Ctrl+C to stop")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    finally:
        # Cleanup
        if hasattr(server, 'should_exit'):
            server.should_exit = True

    sys.exit(0)


if __name__ == "__main__":
    launch_desktop()
