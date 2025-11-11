"""Desktop application launcher using PyWebView."""

import threading
import time
import sys
import uvicorn
import webview


class Server(uvicorn.Server):
    """Custom uvicorn server that runs in a thread."""

    def install_signal_handlers(self):
        pass


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
    time.sleep(2)

    return server


def launch_desktop(port: int = 8001):
    """Launch the desktop application with PyWebView."""
    print("Starting Living Storyworld...")

    # Start FastAPI server in background
    server = start_server(port)

    url = f"http://127.0.0.1:{port}"

    # Create and start the webview window
    webview.create_window(
        "Living Storyworld",
        url,
        width=1280,
        height=800,
        resizable=True,
        min_size=(800, 600)
    )

    try:
        webview.start()
    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup
        if hasattr(server, 'should_exit'):
            server.should_exit = True

    sys.exit(0)


if __name__ == "__main__":
    launch_desktop()
