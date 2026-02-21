import json
import os
import sys

# ── Ruta compatible con PyInstaller (_MEIPASS) y ejecución normal ──
if hasattr(sys, "_MEIPASS"):
    # Ejecutable compilado con PyInstaller
    base_dir = sys._MEIPASS
else:
    # Script Python normal
    base_dir = os.path.dirname(os.path.abspath(__file__))

ruta = os.path.join(base_dir, "yrz_codek.json")

# ── Cargar el diccionario ──────────────────────────────────────────
with open(ruta, "r", encoding="utf-8") as f:
    data = json.load(f)

cifrado = data["cifrado"]

# Normalizar claves especiales a sus caracteres reales
if "SPACE"   in cifrado: cifrado[" "]  = cifrado.pop("SPACE")
if "TAB"     in cifrado: cifrado["\t"] = cifrado.pop("TAB")
if "NEWLINE" in cifrado: cifrado["\n"] = cifrado.pop("NEWLINE")

# Diccionario invertido para descifrar
descifrado = {v: k for k, v in cifrado.items()}


# ── Funciones ─────────────────────────────────────────────────────
def encrypt(texto):
    """Convierte cada carácter a su código de 3 símbolos."""
    resultado = ""
    for char in texto:
        if char in cifrado:
            resultado += cifrado[char]
        else:
            resultado += f"[?{char}]"   # carácter no mapeado, se preserva
    return resultado


def decrypt(texto):
    """Recorre el texto de 3 en 3 y lo convierte de vuelta al original."""
    resultado = ""
    i = 0
    while i < len(texto):
        # Carácter no mapeado entre corchetes
        if texto[i] == "[" and i + 2 < len(texto) and texto[i+1] == "?":
            fin = texto.index("]", i)
            resultado += texto[i+2:fin]
            i = fin + 1
            continue
        # Leer de 3 en 3
        triple = texto[i:i+3]
        if triple in descifrado:
            resultado += descifrado[triple]
            i += 3
        else:
            resultado += texto[i]   # carácter suelto inesperado
            i += 1
    return resultado