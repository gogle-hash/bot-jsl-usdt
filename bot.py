from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import telebot
from telebot import types
import threading
import time

TOKEN = os.environ.get("TELEGRAM_TOKEN", "8881010834:AAEeIE20GxhG1KthPpZd1pxQ-PSKyB5MHBU")
bot = telebot.TeleBot(TOKEN)

# ID del Administrador (Javier)
ADMIN_ID = "7995284100"

# Tiempo de prueba (3 días en segundos)
TIEMPO_PRUEBA = 3 * 24 * 60 * 60
FILE_DB = "usuarios.json"

tasa_actual = {"usdt": 720.00, "fuente": "Actualizado por JSL"}

# ==================== BASE DE DATOS LOCAL ====================

def cargar_usuarios():
    if os.path.exists(FILE_DB):
        try:
            with open(FILE_DB, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def guardar_usuarios(db):
    try:
        with open(FILE_DB, "w") as f:
            json.dump(db, f, indent=4)
    except Exception as e:
        print("Error guardando JSON:", e)

db_usuarios = cargar_usuarios()

def obtener_o_crear_usuario(user_id):
    uid = str(user_id)
    if uid not in db_usuarios:
        db_usuarios[uid] = {
            "registro": time.time(),
            "licencia": False
        }
        guardar_usuarios(db_usuarios)
    return db_usuarios[uid]

# ==================== LÓGICA DE LICENCIAS ====================

def verificar_acceso(user_id):
    uid = str(user_id)
    if uid == ADMIN_ID:
        return True, "admin"
    
    usr = obtener_o_crear_usuario(uid)
    
    if usr.get("licencia"):
        return True, "licencia"
    
    tiempo_usado = time.time() - float(usr.get("registro", time.time()))
    if tiempo_usado < TIEMPO_PRUEBA:
        return True, "prueba"
    
    return False, "expirado"

def mensaje_bloqueo():
    return (
        "⏳ *TIEMPO DE PRUEBA AGOTADO* ⏳\n\n"
        "Tus 3 días de acceso gratuito al sistema JSL han finalizado.\n\n"
        "Para seguir consultando la tasa en tiempo real sin interrupciones, "
        "adquiere tu **Licencia VIP**.\n\n"
        "👤 *Comunícate con la administración para activar tu acceso:*\n"
        "👉 Contacto: @TuUsuarioDeTelegram\n"
        "📞 Teléfono: +53 51420349"
    )

def crear_teclado():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_precio = types.KeyboardButton("💵 Consultar USDT Real")
    btn_id = types.KeyboardButton("🆔 Mi ID / Estado")
    markup.add(btn_precio, btn_id)
    return markup

# ==================== RESTAURACIÓN ====================

@bot.message_handler(content_types=['document'])
def restaurar_respaldo(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    
    if message.document.file_name == "usuarios.json":
        try:
            bot.reply_to(message, "⏳ Descargando copia de seguridad...")
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            with open(FILE_DB, 'wb') as new_file:
                new_file.write(downloaded_file)
            
            global db_usuarios
            db_usuarios = cargar_usuarios()
            
            bot.reply_to(message, "✅ *¡Base de datos restaurada!*\nTodos los clientes recuperaron su tiempo y licencias.", parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"❌ Error al restaurar: {e}")

# ==================== COMANDOS ADMIN ====================

@bot.message_handler(commands=["admin"])
def cmd_admin(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    texto = (
        "⚙️ *PANEL DE ADMINISTRACIÓN JSL*\n\n"
        "• `/tasa [monto]` - Cambia la tasa USDT\n"
        "• `/activar [user_id]` - Activa licencia VIP\n"
        "• `/desactivar [user_id]` - Desactiva licencia VIP\n"
        "• `/usuarios` - Muestra estadísticas\n"
        "• `/notificar [mensaje]` - Mensaje masivo\n"
        "• `/respaldo` - Pide el archivo de la base de datos"
    )
    bot.send_message(message.chat.id, texto, parse_mode="Markdown")

@bot.message_handler(commands=["respaldo"])
def cmd_respaldo(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    guardar_usuarios(db_usuarios)
    if os.path.exists(FILE_DB):
        with open(FILE_DB, "rb") as f:
            bot.send_document(message.chat.id, f, caption="📦 *Guarda este archivo.* Si el servidor se reinicia, reenvíamelo para restaurar todo.")

@bot.message_handler(commands=["notificar"])
def cmd_notificar(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    
    texto_enviar = message.text.replace("/notificar", "").strip()
    if not texto_enviar:
        bot.reply_to(message, "❌ Ejemplo:\n`/notificar La tasa cambió a 725 CUP!`")
        return
        
    bot.reply_to(message, "⏳ Enviando...")
    enviados, fallidos = 0, 0
    
    for uid in list(db_usuarios.keys()):
        if str(uid) != ADMIN_ID:
            try:
                bot.send_message(uid, f"📢 *NOTIFICACIÓN DE JSL*\n\n{texto_enviar}", parse_mode="Markdown")
                enviados += 1
                time.sleep(0.1)
            except Exception:
                fallidos += 1
                
    bot.reply_to(message, f"✅ Difusión: Enviados *{enviados}* | Fallidos *{fallidos}*", parse_mode="Markdown")

@bot.message_handler(commands=["tasa"])
def cmd_cambiar_tasa(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "❌ Uso: `/tasa 725`", parse_mode="Markdown")
        return
    try:
        nueva_tasa = float(partes[1])
        tasa_actual["usdt"] = nueva_tasa
        bot.reply_to(message, f"✅ Tasa actualizada a: *{nueva_tasa} CUP*", parse_mode="Markdown")
    except ValueError:
        bot.reply_to(message, "❌ Ingrese un número válido.")

@bot.message_handler(commands=["activar"])
def cmd_activar_usuario(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "❌ Uso: `/activar 123456789`", parse_mode="Markdown")
        return
    target_id = partes[1]
    usr = obtener_o_crear_usuario(target_id)
    usr["licencia"] = True
    guardar_usuarios(db_usuarios)
    
    bot.reply_to(message, f"✅ Licencia *ACTIVADA* para `{target_id}`.", parse_mode="Markdown")
    try:
        bot.send_message(target_id, "🎉 *¡LICENCIA ACTIVADA!*\n\nTu acceso VIP ha sido activado.", parse_mode="Markdown")
    except Exception:
        pass
    
    if os.path.exists(FILE_DB):
        with open(FILE_DB, "rb") as f:
            bot.send_document(ADMIN_ID, f, caption="🔄 *Respaldo de Seguridad*\n(Generado al activar un usuario)")

@bot.message_handler(commands=["desactivar"])
def cmd_desactivar_usuario(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    partes = message.text.split()
    if len(partes) < 2:
        return
    target_id = partes[1]
    usr = obtener_o_crear_usuario(target_id)
    usr["licencia"] = False
    guardar_usuarios(db_usuarios)
    bot.reply_to(message, f"🚫 Licencia *DESACTIVADA* para `{target_id}`.", parse_mode="Markdown")

@bot.message_handler(commands=["usuarios"])
def cmd_listar_usuarios(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    total = len(db_usuarios)
    con_licencia = sum(1 for u in db_usuarios.values() if u.get("licencia"))
    texto = f"📊 *ESTADÍSTICAS*\n\n👥 Registrados: *{total}*\n💎 VIP: *{con_licencia}*\n⏳ Prueba/Expirados: *{total - con_licencia}*"
    bot.send_message(message.chat.id, texto, parse_mode="Markdown")

# ==================== MANEJADORES CLIENTES ====================

@bot.message_handler(commands=["start"])
def comando_start(message):
    acceso, tipo = verificar_acceso(message.from_user.id)
    if not acceso:
        bot.send_message(message.chat.id, mensaje_bloqueo(), parse_mode="Markdown")
        return
    bot.send_message(
        message.chat.id,
        "👋 Bienvenido al Bot de USDT de JSL.\n\nElige una opción:",
        reply_markup=crear_teclado(),
    )

@bot.message_handler(commands=["id"])
@bot.message_handler(func=lambda message: message.text == "🆔 Mi ID / Estado")
def consultar_id_estado(message):
    uid = message.from_user.id
    acceso, tipo = verificar_acceso(uid)
    
    if tipo == "admin": estado_txt = "👑 Administrador"
    elif tipo == "licencia": estado_txt = "💎 VIP Activa"
    elif tipo == "prueba": estado_txt = "⏳ Periodo de Prueba"
    else: estado_txt = "❌ Acceso Expirado"
    
    bot.send_message(message.chat.id, f"🆔 *TU INFORMACIÓN*\n\n👤 Tu ID: `{uid}`\n📌 Estado: *{estado_txt}*", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "💵 Consultar USDT Real")
def consultar_precio(message):
    acceso, tipo = verificar_acceso(message.from_user.id)
    if not acceso:
        bot.send_message(message.chat.id, mensaje_bloqueo(), parse_mode="Markdown")
        return
    bot.send_message(message.chat.id, f"💵 *TASA ACTUAL*\n\n💰 Valor: *{tasa_actual['usdt']} CUP*\n📊 Fuente: {tasa_actual['fuente']}", parse_mode="Markdown")

# ==================== SERVIDOR WEB CORREGIDO (Soporte GET y HEAD) ====================

class ServidorFalso(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot JSL Activo")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def log_message(self, format, *args):
        return  # Oculta los pings continuos del log para no saturar

def mantener_vivo():
    puerto = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", puerto), ServidorFalso)
    server.serve_forever()

if __name__ == "__main__":
    threading.Thread(target=mantener_vivo, daemon=True).start()
    print("Bot JSL iniciando...")
    try:
        bot.send_message(ADMIN_ID, "⚠️ *Sistema Iniciado/Reiniciado*\n\nSi Render borró la base de datos, por favor **reenvíame el último archivo usuarios.json** para restaurar todo.", parse_mode="Markdown")
    except Exception:
        pass
    bot.infinity_polling()

