// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;
use std::process::{Command, Child};
use std::sync::Mutex;

struct AppState {
    python_process: Mutex<Option<Child>>,
}

fn start_python_server() -> Result<Child, std::io::Error> {
    use std::process::Stdio;
    use std::net::TcpListener;
    
    // 检查端口
    if TcpListener::bind("127.0.0.1:8002").is_ok() {
        println!("Port 8002 is available, starting Python server...");
    } else {
        println!("Port 8002 already in use, assuming server is running");
        return Ok(Command::new("echo").spawn()?);
    }
    
    // 获取Resources目录
    let exe_path = std::env::current_exe()?;
    let exe_dir = exe_path.parent().unwrap();
    
    // 在.app bundle中，Resources在Contents/Resources
    let resources_dir = exe_dir.parent().unwrap().join("Resources");
    let python_bin = resources_dir.join("bin/mlx-audio-server");
    
    println!("Resources dir: {:?}", resources_dir);
    println!("Python bin: {:?}", python_bin);
    
    // 设置环境变量指向Resources中的模型
    let child = Command::new(&python_bin)
        .env("HF_HOME", resources_dir.join("models"))
        .env("TRANSFORMERS_CACHE", resources_dir.join("models"))
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .spawn()?;
    
    println!("✅ Python server started from bundle");
    Ok(child)
}

#[tauri::command]
fn get_server_url() -> String {
    "http://127.0.0.1:8002".to_string()
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // 启动Python服务器
            match start_python_server() {
                Ok(child) => {
                    app.manage(AppState {
                        python_process: Mutex::new(Some(child)),
                    });
                    println!("✅ Python server started");
                }
                Err(e) => {
                    eprintln!("❌ Failed to start Python server: {}", e);
                }
            }
            
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                // 关闭窗口时停止Python服务器
                if let Some(state) = window.try_state::<AppState>() {
                    if let Ok(mut process) = state.python_process.lock() {
                        if let Some(mut child) = process.take() {
                            let _ = child.kill();
                            println!("✅ Python server stopped");
                        }
                    }
                }
            }
        })
        .invoke_handler(tauri::generate_handler![get_server_url])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
