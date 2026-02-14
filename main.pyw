#!/usr/bin/env python3
"""
Launcher GUI minimalista para Alejandra Manager
Solo pide puerto y abre el gestor
"""

import os
import sys
import threading
import webbrowser
import time
from pathlib import Path
from PIL import Image

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import customtkinter as ctk
except ImportError:
    os.system("pip install customtkinter")
    import customtkinter as ctk

try:
    import pystray
except ImportError:
    os.system("pip install pystray")
    import pystray

from alejandra_manager import app, init_directories

# Tema dark
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class LauncherSimple:
    def __init__(self, root):
        self.root = root
        self.root.title("Alejandra Manager")
        self.root.geometry("400x250")
        self.root.iconbitmap(Path(__file__).parent / "static" / "img" / "aml.ico")
        self.root.resizable(False, False)
        self.root.configure(fg_color="#1a1a1a")
        
        # Estado
        self.server_running = False
        self.server_thread = None
        self.port = 5000
        self.tray_icon = None
        
        # Protocolo para cerrar a bandeja
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Interfaz minimalista"""
        
        # Título
        title = ctk.CTkLabel(
            self.root,
            text="⚡ ALEJANDRA MANAGER",
            font=("Arial", 18, "bold"),
            text_color="#e0e0e0"
        )
        title.pack(pady=20)
        
        # Puerto
        port_label = ctk.CTkLabel(
            self.root,
            text="Puerto:",
            font=("Arial", 12),
            text_color="#e0e0e0"
        )
        port_label.pack(pady=(10, 5))
        
        self.port_entry = ctk.CTkEntry(
            self.root,
            placeholder_text="5000",
            font=("Arial", 14),
            fg_color="#2d2d2d",
            border_color="#444444",
            border_width=1,
            text_color="#e0e0e0",
            width=200,
            height=35
        )
        self.port_entry.pack(pady=5)
        self.port_entry.insert(0, "5000")
        
        # Botón Continuar
        btn_continuar = ctk.CTkButton(
            self.root,
            text="▶️  CONTINUAR",
            font=("Arial", 13, "bold"),
            fg_color="#2ecc71",
            hover_color="#27ae60",
            text_color="white",
            height=40,
            corner_radius=8,
            command=self.start_server
        )
        btn_continuar.pack(pady=20)
    
    def start_server(self):
        """Inicia el servidor y abre el navegador"""
        try:
            # Validar puerto
            try:
                self.port = int(self.port_entry.get())
                if self.port < 1024 or self.port > 65535:
                    print("❌ Puerto inválido (1024-65535)")
                    return
            except ValueError:
                print("❌ El puerto debe ser un número")
                return
            
            print(f"⏳ Inicializando en puerto {self.port}...")
            init_directories()
            
            # Minimizar a bandeja
            self.minimize_to_tray()
            
            # Iniciar servidor
            self.server_thread = threading.Thread(
                target=self.run_flask,
                daemon=True
            )
            self.server_thread.start()
            
            self.server_running = True
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def run_flask(self):
        """Ejecuta Flask"""
        try:
            time.sleep(1)
            print(f"✅ Servidor iniciado en http://localhost:{self.port}")
            
            # Abrir navegador
            webbrowser.open(f'http://localhost:{self.port}')
            
            # Ejecutar Flask sin mostrar consola
            app.run(
                debug=False,
                port=self.port,
                use_reloader=False,
                threaded=True,
                host='127.0.0.1'
            )
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def minimize_to_tray(self):
        """Minimiza a la bandeja del sistema"""
        try:
            icon_path = Path(__file__).parent / "static" / "img" / "aml.png"
            
            if icon_path.exists():
                image = Image.open(icon_path)
                image.thumbnail((64, 64))
                
                menu = pystray.Menu(
                    pystray.MenuItem(
                        f"Ejecutando en puerto {self.port}",
                        lambda: None,
                        enabled=False
                    ),
                    pystray.MenuItem("Abrir", self.open_app),
                    pystray.MenuItem("-", lambda: None),
                    pystray.MenuItem("Cerrar", self.close_app)
                )
                
                self.tray_icon = pystray.Icon(
                    "Alejandra Manager",
                    image,
                    "Alejandra Manager",
                    menu
                )
                
                self.root.withdraw()
                threading.Thread(target=self.tray_icon.run, daemon=True).start()
            
        except Exception as e:
            print(f"⚠️  Error en bandeja: {e}")
    
    def open_app(self, icon=None, item=None):
        """Abre el navegador"""
        try:
            webbrowser.open(f'http://localhost:{self.port}')
        except:
            pass
    
    def close_app(self, icon=None, item=None):
        """Cierra la app"""
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()
        sys.exit(0)

def main():
    root = ctk.CTk()
    gui = LauncherSimple(root)
    root.mainloop()

if __name__ == '__main__':
    main()
