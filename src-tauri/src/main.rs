// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;
use std::process::{Command, Child};
use std::sync::Mutex;

struct AppState {
    server_process: Mutex<Option<Child>>,
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // Start the Python backend server
            let server = if cfg!(target_os = "windows") {
                Command::new("python")
                    .args(["-m", "living_storyworld.cli", "web", "--no-browser"])
                    .spawn()
                    .expect("Failed to start server")
            } else {
                Command::new("python3")
                    .args(["-m", "living_storyworld.cli", "web", "--no-browser"])
                    .spawn()
                    .expect("Failed to start server")
            };

            app.manage(AppState {
                server_process: Mutex::new(Some(server)),
            });

            // Give the server time to start
            std::thread::sleep(std::time::Duration::from_secs(2));

            Ok(())
        })
        .on_window_event(|_window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                // Kill the server when window closes
                // This will be handled by Drop trait
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
