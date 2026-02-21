#!/usr/bin/env python3
"""
Alejandra Manager - Gestor de Cuentas Local
Sistema de gestión de credenciales con interfaz web moderna
"""

# ============================================================
# IMPORTS - todas las librerías que necesitamos para que esto funcione
# ============================================================

import os           # para interactuar con el sistema operativo (aunque no lo usamos directo aquí)
import json         # para leer y escribir archivos .json (donde guardamos todo)
import secrets      # para generar tokens seguros (más seguro que random)
import hashlib      # para hacer hash de contraseñas (convertirlas en cadena irreversible)
import base64       # para encoding en base64 si llegara a necesitarse
from pathlib import Path          # manejo moderno de rutas de carpetas/archivos
from datetime import datetime     # para guardar la fecha en que se crea algo
from flask import Flask, render_template, request, jsonify, send_from_directory  # el framework web
from werkzeug.utils import secure_filename  # utilidad para limpiar nombres de archivos subidos
import logging          # para controlar qué mensajes se muestran en consola
import yrz_cipher as yrz  # nuestro módulo de encriptación personalizado


# ============================================================
# CONFIGURACIÓN INICIAL DE FLASK
# ============================================================

# Creamos la app de Flask - este objeto maneja todas las rutas y requests
app = Flask(__name__)

# secret_key se usa internamente por Flask para firmar cookies y sesiones
# secrets.token_hex(32) genera una cadena aleatoria de 64 caracteres cada vez que arranca
# OJO: esto significa que si reinicias el servidor, las sesiones anteriores se invalidan
app.secret_key = secrets.token_hex(32)

# Silenciamos los logs de Werkzeug (el servidor interno de Flask)
# En producción no queremos que imprima cada request en consola
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)       # solo mostrar errores, no info ni warnings
app.logger.setLevel(logging.ERROR)


# ============================================================
# RUTAS DE ARCHIVOS Y CARPETAS
# ============================================================

# Path.home() devuelve la carpeta del usuario actual (ej: C:/Users/nombre o /home/nombre)
# El operador / en Path no es división, es para concatenar rutas de forma segura
USER_DOCS = Path.home() / "Documents" / "Yuuruii" / "Alejandra Manager"

# Archivos JSON donde guardamos toda la data
CREDENTIALS_FILE = USER_DOCS / "credentials.json"  # usuarios y contraseñas hasheadas
SERVICES_FILE    = USER_DOCS / "services.json"      # servicios creados por cada usuario
ACCOUNTS_FILE    = USER_DOCS / "sacc.json"          # cuentas dentro de cada servicio

# Carpetas de imágenes separadas por tipo
IMG_SERVICES = USER_DOCS / "img" / "services"   # iconos de servicios
IMG_ACCOUNTS = USER_DOCS / "img" / "accounts"   # iconos e imágenes de cuentas
IMG_AVATARS  = USER_DOCS / "img" / "avatars"    # fotos de perfil de usuarios
IMG_SRC      = USER_DOCS / "img" / "src"        # imágenes del sistema (ej: default.svg)

# Set de extensiones que aceptamos para subir imágenes
# Usamos set (llaves {}) en vez de lista porque la búsqueda en set es más rápida
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'svg', 'gif'}


# ============================================================
# FUNCIONES UTILITARIAS (helpers)
# Estas funciones las usamos en muchos lugares, por eso las separamos
# ============================================================

def init_directories():
    """
    Crea todas las carpetas necesarias si no existen todavía.
    Se llama una sola vez al arrancar la app desde main.py
    """
    # mkdir con parents=True crea todas las carpetas intermedias si no existen
    # exist_ok=True evita que tire error si la carpeta ya existe
    USER_DOCS.mkdir(parents=True, exist_ok=True)
    IMG_SERVICES.mkdir(parents=True, exist_ok=True)
    IMG_ACCOUNTS.mkdir(parents=True, exist_ok=True)
    IMG_AVATARS.mkdir(parents=True, exist_ok=True)
    IMG_SRC.mkdir(parents=True, exist_ok=True)

    # Creamos un SVG genérico de perfil por defecto si no existe
    # Así siempre hay una imagen para mostrar cuando el usuario no sube ninguna
    default_svg = IMG_SRC / "default.svg"
    if not default_svg.exists():
        default_svg.write_text('''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
  <rect width="200" height="200" fill="#2a2a2a"/>
  <circle cx="100" cy="100" r="60" fill="#444"/>
  <circle cx="100" cy="80" r="25" fill="#666"/>
  <path d="M 50 140 Q 100 120 150 140" fill="#666"/>
</svg>''')


def hash_password(password: str) -> str:
    """
    Convierte una contraseña en texto plano a un hash SHA-256.

    El hash es un proceso de una sola vía: puedes convertir "hola123" -> "abc...xyz"
    pero NO puedes convertir "abc...xyz" -> "hola123" de vuelta.
    Por eso nunca guardamos la contraseña real, solo el hash.
    Cuando el usuario hace login, hasheamos lo que escribe y comparamos hashes.
    """
    # .encode() convierte el string a bytes (SHA-256 trabaja con bytes, no strings)
    # .hexdigest() devuelve el resultado como string hexadecimal (más fácil de guardar)
    return hashlib.sha256(password.encode()).hexdigest()


def load_json(filepath: Path, default=None):
    """
    Lee un archivo JSON y devuelve su contenido como diccionario Python.
    Si el archivo no existe o está corrupto, devuelve el valor 'default'.

    Esto es útil porque así nunca crashea la app si falta un archivo.
    """
    # Si no pasaron default, usamos un dict vacío
    if default is None:
        default = {}

    # Solo intentamos leer si el archivo realmente existe
    if filepath.exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)  # convierte el JSON a dict de Python
        except:
            # Si el JSON está mal formateado o hay error de lectura,
            # devolvemos el default en vez de crashear toda la app
            return default

    # Si el archivo no existe, devolvemos el default
    return default


def save_json(filepath: Path, data):
    """
    Guarda un diccionario Python como archivo JSON en disco.

    indent=2 hace que el JSON sea legible (con sangría de 2 espacios)
    ensure_ascii=False permite guardar caracteres especiales como ñ, á, etc.
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def allowed_file(filename):
    """
    Verifica que el archivo subido tenga una extensión permitida.

    Ejemplo: "foto.jpg" -> True   /   "virus.exe" -> False

    rsplit('.', 1) divide por el último punto, ej: "foto.min.js" -> ["foto.min", "js"]
    El [1] toma solo la extensión y .lower() la convierte a minúsculas para comparar
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def decrypt_account(account: dict) -> dict:
    """
    Desencripta todos los campos sensibles de una cuenta antes de enviarlos al frontend.

    IMPORTANTE: Los datos en disco siempre están encriptados con yrz.encrypt().
    Antes de devolver datos al frontend (al navegador), debemos desencriptarlos
    con yrz.decrypt() para que el usuario vea texto legible, no datos cifrados.

    La regla es:
        - Guardar en disco    -> siempre encriptado    (yrz.encrypt)
        - Devolver al cliente -> siempre desencriptado (yrz.decrypt) <- esto hace esta función

    Retorna una COPIA del dict con los campos desencriptados.
    No modifica el dict original para no contaminar los datos en memoria.
    """
    # Estos son los campos que guardamos encriptados en el JSON
    encrypted_fields = ['name', 'username', 'password', 'email', 'inicio_servicio', 'icon']

    # .copy() hace una copia superficial del dict para no modificar el original
    decrypted = account.copy()

    for field in encrypted_fields:
        # .get(field, '') devuelve '' si el campo no existe, evita KeyError
        val = account.get(field, '')

        # Solo intentamos desencriptar si el campo tiene valor (no está vacío)
        if val:
            try:
                decrypted[field] = yrz.decrypt(val)
            except Exception:
                # Si algo falla (por ejemplo, un valor que no estaba encriptado
                # o datos corruptos), dejamos el valor tal cual para no crashear
                decrypted[field] = val

    return decrypted


def generate_uid():
    """
    Genera un identificador único para cada usuario.

    secrets.token_hex(16) crea una cadena hexadecimal aleatoria de 32 caracteres.
    La probabilidad de colisión (que dos usuarios tengan el mismo uid) es prácticamente cero.
    """
    return secrets.token_hex(16)


# ============================================================
# RUTAS DE LA API
# Cada @app.route define un endpoint que el frontend puede llamar
# methods=['GET'] = solo recibe peticiones GET
# methods=['POST'] = solo recibe peticiones POST, etc.
# ============================================================

@app.route('/')
def index():
    """
    Ruta raíz - sirve la página principal HTML.
    render_template busca el archivo en la carpeta /templates/
    """
    return render_template('index.html')


# ----- AUTENTICACIÓN -----

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    """
    Verifica si ya existe al menos un usuario registrado.
    El frontend lo usa para saber si debe mostrar login o registro.
    """
    credentials = load_json(CREDENTIALS_FILE, {})

    return jsonify({
        'exists': len(credentials) > 0,    # True si hay usuarios, False si está vacío
        'users': list(credentials.keys())  # lista de nombres de usuario registrados
    })


@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    Verifica las credenciales de login del usuario.

    Proceso:
    1. Recibe username y password del frontend
    2. Hashea la password recibida
    3. Compara con el hash guardado en disco
    4. Si coinciden, devuelve los datos del usuario
    """
    data = request.json  # lee el body de la request como dict Python
    username = data.get('username')
    password = data.get('password')

    credentials = load_json(CREDENTIALS_FILE, {})

    # Primero verificamos que el usuario exista, luego comparamos hashes
    # Nunca comparamos passwords en texto plano, siempre hashes
    if username in credentials:
        if credentials[username]['password'] == hash_password(password):
            return jsonify({
                'success': True,
                'uid': credentials[username]['uid'],
                'email': credentials[username].get('email', ''),
                'username': username,
                'avatar': credentials[username].get('avatar', None)
            })

    # Si llegamos aquí es porque el usuario no existe o la contraseña es incorrecta
    # Devolvemos el mismo mensaje para ambos casos (seguridad: no revelar cuál falló)
    return jsonify({'success': False, 'error': 'Credenciales inválidas'}), 401


@app.route('/api/auth/register', methods=['POST'])
def register():
    """
    Registra un nuevo usuario en el sistema.

    Genera un UID único y guarda la contraseña hasheada (nunca en texto plano).
    """
    data = request.json
    username = data.get('username')
    password = data.get('password')
    email = data.get('email', '')  # email es opcional, por defecto string vacío

    credentials = load_json(CREDENTIALS_FILE, {})

    # No permitimos usuarios duplicados
    if username in credentials:
        return jsonify({'success': False, 'error': 'Usuario ya existe'}), 400

    # Generamos el uid antes de guardar para tenerlo disponible
    uid = generate_uid()

    # Guardamos el usuario - OJO: nunca guardamos la password real, solo su hash
    credentials[username] = {
        'password': hash_password(password),        # hash irreversible
        'uid': uid,
        'email': email,
        'created_at': datetime.now().isoformat()    # fecha en formato "2024-01-15T10:30:00"
    }

    save_json(CREDENTIALS_FILE, credentials)

    # En la respuesta sí devolvemos los datos (sin el hash de contraseña)
    return jsonify({
        'success': True,
        'uid': uid,
        'username': username,
        'email': email
    })


@app.route('/api/auth/update-password', methods=['POST'])
def update_password():
    """
    Permite al usuario cambiar su contraseña.
    Requiere la contraseña actual para confirmar que es él.
    """
    data = request.json
    username = data.get('username')
    old_password = data.get('old_password')
    new_password = data.get('new_password')

    credentials = load_json(CREDENTIALS_FILE, {})

    # Verificamos que el usuario exista
    if username not in credentials:
        return jsonify({'success': False, 'error': 'Usuario no existe'}), 404

    # Verificamos que la contraseña actual sea correcta antes de permitir el cambio
    if credentials[username]['password'] != hash_password(old_password):
        return jsonify({'success': False, 'error': 'Contraseña actual incorrecta'}), 401

    # Guardamos el hash de la nueva contraseña
    credentials[username]['password'] = hash_password(new_password)
    save_json(CREDENTIALS_FILE, credentials)

    return jsonify({'success': True})


@app.route('/api/auth/update-email', methods=['POST'])
def update_email():
    """
    Actualiza el email de un usuario.
    No requiere contraseña porque el email no es un dato crítico de seguridad.
    """
    data = request.json
    username = data.get('username')
    email = data.get('email')

    credentials = load_json(CREDENTIALS_FILE, {})

    if username not in credentials:
        return jsonify({'success': False, 'error': 'Usuario no existe'}), 404

    # Simplemente sobreescribimos el campo email
    credentials[username]['email'] = email
    save_json(CREDENTIALS_FILE, credentials)

    return jsonify({'success': True})


@app.route('/api/auth/update-avatar', methods=['POST'])
def update_avatar():
    """
    Actualiza la foto de perfil de un usuario.

    Usa request.form (no request.json) porque estamos subiendo un archivo,
    lo que requiere multipart/form-data en vez de application/json.
    """
    # Con archivos usamos request.form para los campos de texto
    username = request.form.get('username')

    credentials = load_json(CREDENTIALS_FILE, {})

    if username not in credentials:
        return jsonify({'success': False, 'error': 'Usuario no existe'}), 404

    # request.files contiene los archivos subidos
    if 'avatar' in request.files:
        file = request.files['avatar']

        # Verificamos que sea una extensión permitida
        if file and allowed_file(file.filename):
            uid = credentials[username]['uid']

            # Sacamos la extensión del nombre original del archivo
            # rsplit('.', 1) divide por el último punto: "foto.min.jpg" -> ["foto.min", "jpg"]
            ext = file.filename.rsplit('.', 1)[1].lower()

            # Nombramos el archivo con el uid para que sea único por usuario
            filename = f"avatar_{uid}.{ext}"

            # Borramos el avatar anterior si existía para no acumular archivos huérfanos
            old_avatar = credentials[username].get('avatar')
            if old_avatar:
                old_file = USER_DOCS / "img" / old_avatar
                if old_file.exists():
                    old_file.unlink()  # .unlink() es el equivalente de "borrar archivo" en Path

            # Guardamos el nuevo archivo en disco
            file.save(IMG_AVATARS / filename)

            # Guardamos la ruta relativa (no absoluta) en el JSON
            # así funciona aunque la app se mueva de carpeta
            credentials[username]['avatar'] = f"avatars/{filename}"
            save_json(CREDENTIALS_FILE, credentials)

            return jsonify({
                'success': True,
                'avatar_path': f"avatars/{filename}"
            })

    return jsonify({'success': False, 'error': 'No se proporcionó imagen'}), 400


# ----- SERVICIOS -----

@app.route('/api/services', methods=['GET'])
def get_services():
    """
    Devuelve todos los servicios que pertenecen al usuario (filtrados por uid).

    uid viene como query param en la URL: /api/services?uid=abc123
    """
    uid = request.args.get('uid')  # request.args = query params de la URL
    services = load_json(SERVICES_FILE, {})

    # Filtramos solo los servicios de este usuario usando dict comprehension
    # Es equivalente a un for loop que va armando un dict nuevo
    user_services = {k: v for k, v in services.items() if v.get('uid') == uid}

    return jsonify(user_services)


@app.route('/api/services', methods=['POST'])
def create_service():
    """
    Crea un nuevo servicio (ej: "Gmail", "Netflix", "GitHub").
    Los servicios son contenedores que agrupan cuentas.
    """
    uid = request.form.get('uid')
    name = request.form.get('name')

    # Validación básica: uid y name son obligatorios
    if not uid or not name:
        return jsonify({'success': False, 'error': 'Datos incompletos'}), 400

    services = load_json(SERVICES_FILE, {})

    # El ID del servicio combina uid + token aleatorio para que sea único globalmente
    service_id = f"{uid}_{secrets.token_hex(8)}"

    # El icono del servicio es opcional
    icon_path = None
    if 'icon' in request.files:
        file = request.files['icon']
        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{service_id}.{ext}"
            file.save(IMG_SERVICES / filename)
            icon_path = f"services/{filename}"  # ruta relativa para guardar en JSON

    # Guardamos el servicio - los datos de servicios NO se encriptan
    # porque el nombre del servicio no es sensible (ej: "Gmail" no es un secreto)
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
    """
    Elimina un servicio Y todas las cuentas que pertenecen a ese servicio.
    Es un delete en cascada: borramos todo lo relacionado.

    service_id viene en la URL: DELETE /api/services/abc123_xyz
    """
    services = load_json(SERVICES_FILE, {})

    if service_id not in services:
        return jsonify({'success': False, 'error': 'Servicio no encontrado'}), 404

    # Borramos el icono del servicio del disco si existe
    if services[service_id].get('icon'):
        icon_file = USER_DOCS / "img" / services[service_id]['icon']
        if icon_file.exists():
            icon_file.unlink()

    # Buscamos y borramos todas las cuentas que pertenecen a este servicio
    accounts = load_json(ACCOUNTS_FILE, {})

    # Primero hacemos una lista de los IDs a borrar (no podemos borrar mientras iteramos)
    accounts_to_delete = [k for k, v in accounts.items() if v.get('service_id') == service_id]

    for acc_id in accounts_to_delete:
        # También borramos las imágenes de esa cuenta del disco
        acc_dir = IMG_ACCOUNTS / accounts[acc_id]['uid']
        if acc_dir.exists():
            # glob busca archivos que coincidan con el patrón
            for img_file in acc_dir.glob(f"{service_id}_*"):
                img_file.unlink()
        del accounts[acc_id]

    # Guardamos los archivos JSON ya sin los datos borrados
    save_json(ACCOUNTS_FILE, accounts)
    del services[service_id]
    save_json(SERVICES_FILE, services)

    return jsonify({'success': True})


# ----- CUENTAS -----

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """
    Devuelve las cuentas de un usuario filtradas por servicio.

    AQUÍ ESTÁ EL DECRYPT: los datos en disco están encriptados,
    pero antes de enviarlos al frontend los desencriptamos con decrypt_account().
    """
    service_id = request.args.get('service_id')
    uid = request.args.get('uid')

    accounts = load_json(ACCOUNTS_FILE, {})

    # Filtramos las cuentas que pertenecen a este usuario y servicio
    # y las desencriptamos con decrypt_account() antes de devolverlas
    filtered = {
        k: decrypt_account(v) for k, v in accounts.items()
        if v.get('service_id') == service_id and v.get('uid') == uid
    }

    return jsonify(filtered)


@app.route('/api/accounts', methods=['POST'])
def create_account():
    """
    Crea una nueva cuenta dentro de un servicio.

    ENCRIPTACIÓN AL GUARDAR: todos los campos sensibles se encriptan
    con yrz.encrypt() antes de escribirlos al JSON.

    DESENCRIPTACIÓN AL RESPONDER: usamos decrypt_account() en la respuesta
    para que el frontend reciba datos legibles inmediatamente.
    """
    # Obtenemos todos los campos del formulario
    uid             = request.form.get('uid')
    service_id      = request.form.get('service_id')
    name            = request.form.get('name', '')
    username        = request.form.get('username', '')
    password        = request.form.get('password', '')
    email           = request.form.get('email', '')

    # inicio_servicio indica si esta cuenta es la del servicio en sí (sin contraseña propia)
    inicio_servicio = request.form.get('inicio_servicio') == 'true'  # convierte string a bool

    # Validaciones básicas antes de procesar nada
    if not uid or not service_id:
        return jsonify({'success': False, 'error': 'Datos incompletos'}), 400

    if not username and not email:
        return jsonify({'success': False, 'error': 'Debe proporcionar usuario o email'}), 400

    # Si no es inicio_servicio, la contraseña es obligatoria
    if not inicio_servicio and not password:
        return jsonify({'success': False, 'error': 'Debe proporcionar contraseña'}), 400

    accounts = load_json(ACCOUNTS_FILE, {})

    # ID único para esta cuenta
    account_id = f"{uid}_{secrets.token_hex(8)}"

    # Preparamos la carpeta de imágenes para este usuario
    acc_img_dir = IMG_ACCOUNTS / uid
    acc_img_dir.mkdir(parents=True, exist_ok=True)

    # Procesamos el icono de la cuenta (opcional)
    icon_path = None
    if 'icon' in request.files:
        file = request.files['icon']
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{account_id}_icon.{ext}"
            file.save(acc_img_dir / filename)
            icon_path = f"accounts/{uid}/{filename}"

    # Procesamos imágenes adicionales (capturas de pantalla, etc.)
    images = []
    for i, key in enumerate(request.files.keys()):
        if key.startswith('image_'):  # solo procesamos claves que empiecen con "image_"
            file = request.files[key]
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{service_id}_{i}.{ext}"
                file.save(acc_img_dir / filename)
                images.append(f"accounts/{uid}/{filename}")

    # Si no pusieron nombre, usamos username, y si tampoco, usamos email
    display_name = name if name else (username if username else email)

    # ============================================================
    # AQUÍ SE ENCRIPTA TODO ANTES DE GUARDAR EN DISCO
    # La condición "if campo else ''" evita encriptar strings vacíos
    # porque yrz.encrypt('') podría generar valores raros en algunos cifrados
    # ============================================================
    accounts[account_id] = {
        'uid': uid,
        'service_id': service_id,
        'name':            yrz.encrypt(display_name)         if display_name    else '',
        'username':        yrz.encrypt(username)             if username        else '',
        'password':        yrz.encrypt(password)             if password        else '',
        'email':           yrz.encrypt(email)                if email           else '',
        'inicio_servicio': yrz.encrypt(str(inicio_servicio)) if inicio_servicio else '',
        'icon':            yrz.encrypt(icon_path)            if icon_path       else '',
        'images':          images,              # las rutas de imágenes no se encriptan
        'created_at':      datetime.now().isoformat()
    }

    # Guardamos en disco (encriptado)
    save_json(ACCOUNTS_FILE, accounts)

    # Devolvemos al frontend la cuenta DESENCRIPTADA para que la muestre de inmediato
    return jsonify({
        'success': True,
        'account_id': account_id,
        'account': decrypt_account(accounts[account_id])  # <- desencriptamos antes de enviar
    })


@app.route('/api/accounts/<account_id>', methods=['PUT'])
def update_account(account_id):
    """
    Actualiza campos de una cuenta existente.

    Solo actualiza los campos que vengan en el request (no sobreescribe todo).
    Al guardar encripta, al responder desencripta.
    """
    accounts = load_json(ACCOUNTS_FILE, {})

    # Verificamos que la cuenta que quieren editar exista
    if account_id not in accounts:
        return jsonify({'success': False, 'error': 'Cuenta no encontrada'}), 404

    # Solo actualizamos los campos que llegaron en el form
    # Si un campo no llega, se queda como estaba (no lo tocamos)
    if 'username' in request.form:
        accounts[account_id]['username'] = yrz.encrypt(request.form['username'])
    if 'password' in request.form:
        accounts[account_id]['password'] = yrz.encrypt(request.form['password'])
    if 'email' in request.form:
        accounts[account_id]['email'] = yrz.encrypt(request.form['email'])

    # Guardamos los cambios en disco (encriptados)
    save_json(ACCOUNTS_FILE, accounts)

    # Respondemos con la cuenta desencriptada para que el frontend la muestre actualizada
    return jsonify({'success': True, 'account': decrypt_account(accounts[account_id])})


@app.route('/api/accounts/<account_id>', methods=['DELETE'])
def delete_account(account_id):
    """
    Elimina una cuenta y todas sus imágenes del disco.
    """
    accounts = load_json(ACCOUNTS_FILE, {})

    if account_id not in accounts:
        return jsonify({'success': False, 'error': 'Cuenta no encontrada'}), 404

    uid = accounts[account_id]['uid']
    acc_dir = IMG_ACCOUNTS / uid  # carpeta de imágenes de este usuario

    # Borramos el icono de la cuenta si existe
    if accounts[account_id].get('icon'):
        icon_file = USER_DOCS / "img" / accounts[account_id]['icon']
        if icon_file.exists():
            icon_file.unlink()  # .unlink() borra el archivo del disco

    # Borramos las imágenes adicionales
    # .get con default [] evita KeyError si la clave 'images' no existe
    for img_path in accounts[account_id].get('images', []):
        img_file = USER_DOCS / "img" / img_path
        if img_file.exists():
            img_file.unlink()

    # Borramos la cuenta del dict y guardamos
    del accounts[account_id]
    save_json(ACCOUNTS_FILE, accounts)

    return jsonify({'success': True})


@app.route('/api/accounts/count', methods=['GET'])
def count_accounts():
    """
    Devuelve el número total de cuentas que tiene un usuario.
    Útil para mostrar estadísticas en el dashboard.
    """
    uid = request.args.get('uid')
    accounts = load_json(ACCOUNTS_FILE, {})

    # Contamos cuántas cuentas tienen este uid usando una generator expression
    # Es como un for loop compacto que va sumando 1 por cada cuenta que coincide
    count = sum(1 for v in accounts.values() if v.get('uid') == uid)

    return jsonify({'count': count})


# ----- IMÁGENES -----

@app.route('/img/<path:filename>')
def serve_image(filename):
    """
    Sirve archivos de imagen desde la carpeta de imágenes del usuario.

    <path:filename> captura rutas con subdirectorios, ej: "avatars/foto.jpg"
    send_from_directory maneja los headers HTTP correctos para archivos estáticos.
    """
    return send_from_directory(USER_DOCS / "img", filename)


# ============================================================
# PUNTO DE ENTRADA
# ============================================================

if __name__ == '__main__':
    # Si corres este archivo directamente (python alejandra_manager.py),
    # te avisamos que debes usar main.py que configura todo correctamente
    print("⚠️  Usa 'python main.py' para iniciar la aplicación")
    print("   O compila con: pyinstaller alejandra_manager.spec")
