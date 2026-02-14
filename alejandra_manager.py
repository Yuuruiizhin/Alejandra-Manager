#!/usr/bin/env python3
"""
Alejandra Manager - Gestor de Cuentas Local
Sistema de gestión de credenciales con interfaz web moderna
"""

import os
import json
import secrets
import hashlib
import base64
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import logging

# Configuración de la aplicación
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Suprimir logs de Werkzeug y Flask en modo production
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app.logger.setLevel(logging.ERROR)

# Rutas base
USER_DOCS = Path.home() / "Documents" / "Yuuruii" / "Alejandra Manager"
CREDENTIALS_FILE = USER_DOCS / "credentials.json"
SERVICES_FILE = USER_DOCS / "services.json"
ACCOUNTS_FILE = USER_DOCS / "sacc.json"
IMG_SERVICES = USER_DOCS / "img" / "services"
IMG_ACCOUNTS = USER_DOCS / "img" / "accounts"
IMG_AVATARS = USER_DOCS / "img" / "avatars"
IMG_SRC = USER_DOCS / "img" / "src"

# Extensiones permitidas para imágenes
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'svg', 'gif'}

def init_directories():
    """Inicializa las carpetas necesarias"""
    USER_DOCS.mkdir(parents=True, exist_ok=True)
    IMG_SERVICES.mkdir(parents=True, exist_ok=True)
    IMG_ACCOUNTS.mkdir(parents=True, exist_ok=True)
    IMG_AVATARS.mkdir(parents=True, exist_ok=True)
    IMG_SRC.mkdir(parents=True, exist_ok=True)
    
    # Crear imagen default si no existe
    default_svg = IMG_SRC / "default.svg"
    if not default_svg.exists():
        default_svg.write_text('''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
  <rect width="200" height="200" fill="#2a2a2a"/>
  <circle cx="100" cy="100" r="60" fill="#444"/>
  <circle cx="100" cy="80" r="25" fill="#666"/>
  <path d="M 50 140 Q 100 120 150 140" fill="#666"/>
</svg>''')

def hash_password(password: str) -> str:
    """Hash de contraseña usando SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def load_json(filepath: Path, default=None):
    """Carga archivo JSON de forma segura"""
    if default is None:
        default = {}
    if filepath.exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(filepath: Path, data):
    """Guarda datos en archivo JSON"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def allowed_file(filename):
    """Verifica si la extensión del archivo es permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_uid():
    """Genera un UID único"""
    return secrets.token_hex(16)

# ============= RUTAS DE LA API =============

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    """Verifica si existen credenciales"""
    credentials = load_json(CREDENTIALS_FILE, {})
    return jsonify({
        'exists': len(credentials) > 0,
        'users': list(credentials.keys())
    })

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Inicio de sesión"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    credentials = load_json(CREDENTIALS_FILE, {})
    
    if username in credentials:
        if credentials[username]['password'] == hash_password(password):
            return jsonify({
                'success': True,
                'uid': credentials[username]['uid'],
                'email': credentials[username].get('email', ''),
                'username': username,
                'avatar': credentials[username].get('avatar', None)
            })
    
    return jsonify({'success': False, 'error': 'Credenciales inválidas'}), 401

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Registro de nuevo usuario"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    email = data.get('email', '')
    
    credentials = load_json(CREDENTIALS_FILE, {})
    
    if username in credentials:
        return jsonify({'success': False, 'error': 'Usuario ya existe'}), 400
    
    uid = generate_uid()
    credentials[username] = {
        'password': hash_password(password),
        'uid': uid,
        'email': email,
        'created_at': datetime.now().isoformat()
    }
    
    save_json(CREDENTIALS_FILE, credentials)
    
    return jsonify({
        'success': True,
        'uid': uid,
        'username': username,
        'email': email
    })

@app.route('/api/auth/update-password', methods=['POST'])
def update_password():
    """Actualizar contraseña de usuario"""
    data = request.json
    username = data.get('username')
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    credentials = load_json(CREDENTIALS_FILE, {})
    
    if username not in credentials:
        return jsonify({'success': False, 'error': 'Usuario no existe'}), 404
    
    if credentials[username]['password'] != hash_password(old_password):
        return jsonify({'success': False, 'error': 'Contraseña actual incorrecta'}), 401
    
    credentials[username]['password'] = hash_password(new_password)
    save_json(CREDENTIALS_FILE, credentials)
    
    return jsonify({'success': True})

@app.route('/api/auth/update-email', methods=['POST'])
def update_email():
    """Actualizar email de usuario"""
    data = request.json
    username = data.get('username')
    email = data.get('email')
    
    credentials = load_json(CREDENTIALS_FILE, {})
    
    if username not in credentials:
        return jsonify({'success': False, 'error': 'Usuario no existe'}), 404
    
    credentials[username]['email'] = email
    save_json(CREDENTIALS_FILE, credentials)
    
    return jsonify({'success': True})

@app.route('/api/auth/update-avatar', methods=['POST'])
def update_avatar():
    """Actualizar avatar de usuario"""
    username = request.form.get('username')
    
    credentials = load_json(CREDENTIALS_FILE, {})
    
    if username not in credentials:
        return jsonify({'success': False, 'error': 'Usuario no existe'}), 404
    
    # Guardar avatar
    if 'avatar' in request.files:
        file = request.files['avatar']
        if file and allowed_file(file.filename):
            uid = credentials[username]['uid']
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"avatar_{uid}.{ext}"
            
            # Eliminar avatar anterior si existe
            old_avatar = credentials[username].get('avatar')
            if old_avatar:
                old_file = USER_DOCS / "img" / old_avatar
                if old_file.exists():
                    old_file.unlink()
            
            # Guardar nuevo avatar
            file.save(IMG_AVATARS / filename)
            credentials[username]['avatar'] = f"avatars/{filename}"
            save_json(CREDENTIALS_FILE, credentials)
            
            return jsonify({
                'success': True,
                'avatar_path': f"avatars/{filename}"
            })
    
    return jsonify({'success': False, 'error': 'No se proporcionó imagen'}), 400

@app.route('/api/services', methods=['GET'])
def get_services():
    """Obtiene todos los servicios de un usuario"""
    uid = request.args.get('uid')
    services = load_json(SERVICES_FILE, {})
    
    user_services = {k: v for k, v in services.items() if v.get('uid') == uid}
    
    return jsonify(user_services)

@app.route('/api/services', methods=['POST'])
def create_service():
    """Crea un nuevo servicio"""
    uid = request.form.get('uid')
    name = request.form.get('name')
    
    if not uid or not name:
        return jsonify({'success': False, 'error': 'Datos incompletos'}), 400
    
    services = load_json(SERVICES_FILE, {})
    service_id = f"{uid}_{secrets.token_hex(8)}"
    
    # Manejo de la imagen del servicio
    icon_path = None
    if 'icon' in request.files:
        file = request.files['icon']
        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{service_id}.{ext}"
            file.save(IMG_SERVICES / filename)
            icon_path = f"services/{filename}"
    
    services[service_id] = {
        'name': name,
        'uid': uid,
        'icon': icon_path,
        'created_at': datetime.now().isoformat()
    }
    
    save_json(SERVICES_FILE, services)
    
    return jsonify({
        'success': True,
        'service_id': service_id,
        'service': services[service_id]
    })

@app.route('/api/services/<service_id>', methods=['DELETE'])
def delete_service(service_id):
    """Elimina un servicio"""
    services = load_json(SERVICES_FILE, {})
    
    if service_id not in services:
        return jsonify({'success': False, 'error': 'Servicio no encontrado'}), 404
    
    # Eliminar imagen del servicio
    if services[service_id].get('icon'):
        icon_file = USER_DOCS / "img" / services[service_id]['icon']
        if icon_file.exists():
            icon_file.unlink()
    
    # Eliminar cuentas asociadas
    accounts = load_json(ACCOUNTS_FILE, {})
    accounts_to_delete = [k for k, v in accounts.items() if v.get('service_id') == service_id]
    
    for acc_id in accounts_to_delete:
        # Eliminar imágenes de la cuenta
        acc_dir = IMG_ACCOUNTS / accounts[acc_id]['uid']
        if acc_dir.exists():
            for img_file in acc_dir.glob(f"{service_id}_*"):
                img_file.unlink()
        del accounts[acc_id]
    
    save_json(ACCOUNTS_FILE, accounts)
    del services[service_id]
    save_json(SERVICES_FILE, services)
    
    return jsonify({'success': True})

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """Obtiene cuentas filtradas por servicio y usuario"""
    service_id = request.args.get('service_id')
    uid = request.args.get('uid')
    
    accounts = load_json(ACCOUNTS_FILE, {})
    
    filtered = {
        k: v for k, v in accounts.items() 
        if v.get('service_id') == service_id and v.get('uid') == uid
    }
    
    return jsonify(filtered)

@app.route('/api/accounts', methods=['POST'])
def create_account():
    """Crea una nueva cuenta"""
    uid = request.form.get('uid')
    service_id = request.form.get('service_id')
    name = request.form.get('name', '')
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    email = request.form.get('email', '')
    inicio_servicio = request.form.get('inicio_servicio') == 'true'
    
    if not uid or not service_id:
        return jsonify({'success': False, 'error': 'Datos incompletos'}), 400
    
    if not username and not email:
        return jsonify({'success': False, 'error': 'Debe proporcionar usuario o email'}), 400
    
    if not inicio_servicio and not password:
        return jsonify({'success': False, 'error': 'Debe proporcionar contraseña'}), 400
    
    accounts = load_json(ACCOUNTS_FILE, {})
    account_id = f"{uid}_{secrets.token_hex(8)}"
    
    # Directorio de imágenes de la cuenta
    acc_img_dir = IMG_ACCOUNTS / uid
    acc_img_dir.mkdir(parents=True, exist_ok=True)
    
    # Icono de la cuenta
    icon_path = None
    if 'icon' in request.files:
        file = request.files['icon']
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{account_id}_icon.{ext}"
            file.save(acc_img_dir / filename)
            icon_path = f"accounts/{uid}/{filename}"
    
    # Imágenes adicionales
    images = []
    for i, key in enumerate(request.files.keys()):
        if key.startswith('image_'):
            file = request.files[key]
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{service_id}_{i}.{ext}"
                file.save(acc_img_dir / filename)
                images.append(f"accounts/{uid}/{filename}")
    
    # Nombre por defecto
    display_name = name if name else (username if username else email)
    
    accounts[account_id] = {
        'uid': uid,
        'service_id': service_id,
        'name': display_name,
        'username': username,
        'password': password,
        'email': email,
        'inicio_servicio': inicio_servicio,
        'icon': icon_path,
        'images': images,
        'created_at': datetime.now().isoformat()
    }
    
    save_json(ACCOUNTS_FILE, accounts)
    
    return jsonify({
        'success': True,
        'account_id': account_id,
        'account': accounts[account_id]
    })

@app.route('/api/accounts/<account_id>', methods=['PUT'])
def update_account(account_id):
    """Actualiza una cuenta existente"""
    accounts = load_json(ACCOUNTS_FILE, {})
    
    if account_id not in accounts:
        return jsonify({'success': False, 'error': 'Cuenta no encontrada'}), 404
    
    # Actualizar campos
    if 'username' in request.form:
        accounts[account_id]['username'] = request.form['username']
    if 'password' in request.form:
        accounts[account_id]['password'] = request.form['password']
    if 'email' in request.form:
        accounts[account_id]['email'] = request.form['email']
    
    save_json(ACCOUNTS_FILE, accounts)
    
    return jsonify({'success': True, 'account': accounts[account_id]})

@app.route('/api/accounts/<account_id>', methods=['DELETE'])
def delete_account(account_id):
    """Elimina una cuenta"""
    accounts = load_json(ACCOUNTS_FILE, {})
    
    if account_id not in accounts:
        return jsonify({'success': False, 'error': 'Cuenta no encontrada'}), 404
    
    # Eliminar imágenes
    uid = accounts[account_id]['uid']
    acc_dir = IMG_ACCOUNTS / uid
    
    if accounts[account_id].get('icon'):
        icon_file = USER_DOCS / "img" / accounts[account_id]['icon']
        if icon_file.exists():
            icon_file.unlink()
    
    for img_path in accounts[account_id].get('images', []):
        img_file = USER_DOCS / "img" / img_path
        if img_file.exists():
            img_file.unlink()
    
    del accounts[account_id]
    save_json(ACCOUNTS_FILE, accounts)
    
    return jsonify({'success': True})

@app.route('/api/accounts/count', methods=['GET'])
def count_accounts():
    """Cuenta las cuentas de un usuario"""
    uid = request.args.get('uid')
    accounts = load_json(ACCOUNTS_FILE, {})
    
    count = sum(1 for v in accounts.values() if v.get('uid') == uid)
    
    return jsonify({'count': count})

@app.route('/img/<path:filename>')
def serve_image(filename):
    """Sirve imágenes"""
    return send_from_directory(USER_DOCS / "img", filename)

if __name__ == '__main__':
    # Este archivo ahora es importado por main.py
    # Para ejecutar directamente, corre: python main.py
    print("⚠️  Usa 'python main.py' para iniciar la aplicación")
    print("   O compila con: pyinstaller alejandra_manager.spec")

