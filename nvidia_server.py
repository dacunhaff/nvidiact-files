import requests
import subprocess
import threading
import time
import sys
import os
import json
import tempfile
import pystray
from PIL import Image, ImageDraw
from datetime import datetime

# ─── CONFIGURAÇÃO ─────────────────────────────────────────────────────────────
API_URL = "https://nvidiact-api.onrender.com"
EXE_URL = "https://github.com/dacunhaff/nvidiact-files/raw/main/KIPOCK%20FULL.exe"
EXE_NAME = "KIPOCK FULL.exe"
APP_NAME = "NVIDIA CT Server"
VERSION = "2.0"

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(__file__)

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "nvidia_server.log")

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
    except:
        pass

def check_single_instance():
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 57123))
        return sock
    except:
        return None

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"key": "", "auto_start": False}

def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        log(f"Erro ao salvar config: {e}")

running = True
config = load_config()
user_key = config.get("key", "")
status_label = "Iniciando..." if user_key else "Aguardando chave..."
status_color = "gray"
processo_ativo = None
icon_instance = None

def create_icon_image(color="green"):
    colors = {
        "green": (118, 185, 0),
        "yellow": (255, 193, 7),
        "red": (220, 53, 69),
        "gray": (108, 117, 125)
    }
    img = Image.new("RGB", (64, 64), color=(0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([8, 8, 56, 56], fill=colors.get(color, colors["gray"]))
    d.text((32, 28), "N", fill=(255, 255, 255), anchor="mm")
    return img

def update_icon_color(color):
    global icon_instance, status_color
    if icon_instance and status_color != color:
        status_color = color
        icon_instance.icon = create_icon_image(color)

def notify(title, message):
    global icon_instance
    if icon_instance:
        try:
            icon_instance.notify(message, title)
        except:
            pass

def ativar_programa():
    global status_label, processo_ativo
    try:
        log("Iniciando ativação do programa...")
        status_label = "⬇️ Baixando programa..."
        update_icon_color("yellow")
        
        resp = requests.get(EXE_URL, stream=True, timeout=60)
        resp.raise_for_status()
        
        tmp_path = os.path.join(tempfile.gettempdir(), EXE_NAME)
        
        total_size = int(resp.headers.get('content-length', 0))
        downloaded = 0
        
        with open(tmp_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
        
        log(f"Download concluído: {downloaded} bytes")
        
        status_label = "▶️ Executando programa..."
        processo_ativo = subprocess.Popen([tmp_path])
        
        status_label = "✅ Programa ativo"
        update_icon_color("green")
        notify("NVIDIA CT", "Programa ativado com sucesso!")
        log("Programa ativado com sucesso")
        
    except Exception as e:
        error_msg = str(e)[:60]
        status_label = f"❌ Erro: {error_msg}"
        update_icon_color("red")
        log(f"Erro ao ativar: {e}")
        notify("NVIDIA CT - Erro", f"Falha ao ativar: {error_msg}")

def desativar_programa():
    global status_label, processo_ativo
    try:
        log("Desativando programa...")
        
        if processo_ativo:
            processo_ativo.terminate()
            time.sleep(1)
            if processo_ativo.poll() is None:
                processo_ativo.kill()
            processo_ativo = None
        
        os.system(f'taskkill /f /im "{EXE_NAME}" >nul 2>&1')
        
        tmp_path = os.path.join(tempfile.gettempdir(), EXE_NAME)
        if os.path.exists(tmp_path):
            try:
                time.sleep(0.5)
                os.remove(tmp_path)
            except:
                pass
        
        status_label = "⛔ Programa desativado"
        update_icon_color("gray")
        notify("NVIDIA CT", "Programa desativado")
        log("Programa desativado com sucesso")
        
    except Exception as e:
        error_msg = str(e)[:60]
        status_label = f"❌ Erro ao desativar: {error_msg}"
        log(f"Erro ao desativar: {e}")

def poll_loop():
    global status_label, running
    consecutive_errors = 0
    
    while running:
        if not user_key:
            status_label = "⚠️ Chave não configurada"
            update_icon_color("yellow")
            time.sleep(5)
            continue
        
        try:
            resp = requests.post(
                f"{API_URL}/api/pc/register",
                json={"key": user_key},
                timeout=10
            )
            
            if resp.status_code == 200:
                data = resp.json()
                
                if data.get("status") == "ok":
                    status_label = "🟢 Conectado"
                    update_icon_color("green")
                    consecutive_errors = 0
                    
                    command = data.get("command")
                    if command == "ativar":
                        log("Comando recebido: ATIVAR")
                        threading.Thread(target=ativar_programa, daemon=True).start()
                    elif command == "desativar":
                        log("Comando recebido: DESATIVAR")
                        threading.Thread(target=desativar_programa, daemon=True).start()
                        
                elif data.get("status") == "invalid":
                    status_label = "❌ Chave inválida"
                    update_icon_color("red")
                    log("Chave de acesso inválida")
                    
            else:
                raise Exception(f"HTTP {resp.status_code}")
                
        except Exception as e:
            consecutive_errors += 1
            status_label = f"⚠️ Erro de conexão ({consecutive_errors})"
            update_icon_color("yellow")
            
            if consecutive_errors == 1:
                log(f"Erro ao conectar na API: {e}")
            elif consecutive_errors >= 10:
                log(f"Múltiplas falhas de conexão ({consecutive_errors})")
                consecutive_errors = 0
        
        time.sleep(5)

def on_definir_chave(icon, item):
    import tkinter as tk
    from tkinter import simpledialog
    
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    chave = simpledialog.askstring(
        "NVIDIA CT - Configurar Chave",
        "Digite sua chave de acesso:\n(Formato: XXXXXXX-XXXXXX)",
        parent=root
    )
    root.destroy()
    
    if chave:
        global user_key, config
        user_key = chave.strip().upper()
        config["key"] = user_key
        save_config(config)
        log(f"Chave configurada: {user_key}")
        notify("NVIDIA CT", "Chave configurada com sucesso!")

def on_status(icon, item):
    import tkinter as tk
    from tkinter import messagebox
    
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    info = f"""NVIDIA CT Server v{VERSION}

Chave: {user_key or 'Não configurada'}
Status: {status_label}

API: {API_URL}
Log: {LOG_FILE}
"""
    
    messagebox.showinfo("NVIDIA CT - Status", info, parent=root)
    root.destroy()

def on_forcar_ativar(icon, item):
    log("Ativação forçada manualmente")
    threading.Thread(target=ativar_programa, daemon=True).start()

def on_forcar_desativar(icon, item):
    log("Desativação forçada manualmente")
    threading.Thread(target=desativar_programa, daemon=True).start()

def on_abrir_log(icon, item):
    try:
        os.startfile(LOG_FILE)
    except:
        log("Erro ao abrir arquivo de log")

def on_sair(icon, item):
    global running
    log("Encerrando servidor...")
    desativar_programa()
    running = False
    icon.stop()

def run_tray():
    global icon_instance
    
    menu = pystray.Menu(
        pystray.MenuItem("Definir Chave", on_definir_chave),
        pystray.MenuItem(lambda text: f"Status: {status_label}", on_status),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Forçar Ativar", on_forcar_ativar),
        pystray.MenuItem("Forçar Desativar", on_forcar_desativar),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Ver Log", on_abrir_log),
        pystray.MenuItem("Sair", on_sair)
    )
    
    icon_instance = pystray.Icon(
        APP_NAME,
        create_icon_image("gray"),
        f"{APP_NAME} v{VERSION}",
        menu
    )
    
    icon_instance.run()

if __name__ == "__main__":
    lock = check_single_instance()
    if not lock:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "NVIDIA CT",
            "O servidor já está em execução!\n\nVerifique a bandeja do sistema."
        )
        root.destroy()
        sys.exit(1)
    
    log(f"=== {APP_NAME} v{VERSION} iniciado ===")
    log(f"Diretório: {BASE_DIR}")
    log(f"Chave configurada: {bool(user_key)}")
    
    if not user_key:
        import tkinter as tk
        from tkinter import simpledialog, messagebox
        
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        messagebox.showinfo(
            "NVIDIA CT - Bem-vindo",
            "Bem-vindo ao NVIDIA CT Server!\n\nPor favor, configure sua chave de acesso."
        )
        
        chave = simpledialog.askstring(
            "NVIDIA CT - Configurar Chave",
            "Digite sua chave de acesso:\n(Formato: XXXXXXX-XXXXXX)",
            parent=root
        )
        root.destroy()
        
        if chave:
            user_key = chave.strip().upper()
            config["key"] = user_key
            save_config(config)
            log(f"Primeira configuração - Chave: {user_key}")
        else:
            log("Primeira execução cancelada - sem chave")
    
    poll_thread = threading.Thread(target=poll_loop, daemon=True)
    poll_thread.start()
    log("Thread de polling iniciada")
    
    try:
        run_tray()
    except KeyboardInterrupt:
        log("Interrompido pelo usuário")
    except Exception as e:
        log(f"Erro fatal: {e}")
    finally:
        running = False
        desativar_programa()
        log(f"=== {APP_NAME} encerrado ===")
