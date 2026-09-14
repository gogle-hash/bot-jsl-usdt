from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import telebot
from telebot import types
import threading
import time

# ==================== CONFIGURACIÓN ====================
TOKEN = os.environ.get("TELEGRAM_TOKEN", "8881010834:AAEeIE20GxhG1KthPpZd1pxQ-PSKyB5MHBU")
bot = telebot.TeleBot(TOKEN)

# ID del Administrador (Javier)
ADMIN_ID = "7995284100"

# Tiempo de prueba (3 días en segundos)
TIEMPO_PRUEBA = 3 * 24 * 60 * 60
FILE_DB = "usuarios.json"

# ==================== BASE DE DATOS LOCAL ====================
def cargar_datos():
    if os.path.exists(FILE_DB):
        try:
            with open(FILE_DB, "r") as f:
                contenido = json.load(f)
                # Verifica el formato de los datos para evitar errores
                if isinstance(contenido, dict) and "usuarios" in contenido:
                    return contenido
                elif isinstance(contenido, dict):
                    return {"tasa": 780.00, "usuarios": contenido}
        except Exception as e:
            print("Error cargando JSON, usando datos por defecto:", e)
    return {"tasa": 780.00, "usuarios": {}}

def guardar_datos():
    try:
        with open(FILE_DB, "w") as f:
            json.dump(datos, f, indent=4)
    except Exception as e:
        print("Error guardando JSON:", e)

# Cargar la base de datos al iniciar el script
datos = cargar_datos()

def obtener_o_crear_usuario(user_id):
    uid = str(user_id)
    if uid not in datos["usuarios"]:
        datos["usuarios"][uid] = {
            "registro": time.time(),
            "licencia": False
        }
        guardar_datos()
    return datos["usuarios"][uid]

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

# ==================== RESTAURACIÓN DE BACKUP ====================
@bot.message_handler(content_types=['document'])
def restaurar_respaldo(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    
    if message.document.file_name == "usuarios.json":
        try:
            bot.reply_to(message, "⏳ Restaurando sistema...")
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            with open(FILE_DB, 'wb') as new_file:
                new_file.write(downloaded_file)
            
            global datos
            datos = cargar_datos()
            
            bot.reply_to(message, f"✅ *¡Sistema Restaurado!*\n\n• Tasa fijada en: *{datos.get('tasa', 720.0)} CUP*\n• Base de datos de clientes actualizada.", parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"❌ Error al restaurar: {e}")

# ==================== COMANDOS DE ADMINISTRADOR ====================
@bot.message_handler(commands=["admin"])
def cmd_admin(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    texto = (
        "⚙️ *PANEL DE ADMINISTRACIÓN JSL*\n\n"
        "• `/tasa [monto]` - Fija la tasa USDT\n"
        "• `/activar [id]` - Activa acceso VIP\n"
        "• `/desactivar [id]` - Quita acceso VIP\n"
        "• `/usuarios` - Ver estadísticas\n"
        "• `/notificar [texto]` - Enviar anuncio\n"
        "• `/respaldo` - Descargar base de datos"
    )
    bot.send_message(message.chat.id, texto, parse_mode="Markdown")

@bot.message_handler(commands=["tasa"])
def cmd_cambiar_tasa(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, f"❌ Uso: `/tasa 725`\nLa tasa guardada actualmente es: *{datos.get('tasa', 720.0)} CUP*", parse_mode="Markdown")
        return
    try:
        nueva_tasa = float(partes[1])
        datos["tasa"] = nueva_tasa
        guardar_datos()
        bot.reply_to(message, f"✅ Tasa actualizada permanentemente a: *{nueva_tasa} CUP*", parse_mode="Markdown")
    except ValueError:
        bot.reply_to(message, "❌ Error: Escribe un número válido.")

@bot.message_handler(commands=["respaldo"])
def cmd_respaldo(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    guardar_datos()
    if os.path.exists(FILE_DB):
        with open(FILE_DB, "rb") as f:
            bot.send_document(message.chat.id, f, caption=f"📦 *Copia de Seguridad*\nTasa: {datos.get('tasa', 720.0)} CUP\nUsuarios: {len(datos['usuarios'])}")

@bot.message_handler(commands=["notificar"])
def cmd_notificar(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    
    texto_enviar = message.text.replace("/notificar", "").strip()
    if not texto_enviar:
        bot.reply_to(message, "❌ Uso correcto:\n`/notificar Hola a todos!`")
        return
        
    bot.reply_to(message, "⏳ Enviando mensajes...")
    enviados, fallidos = 0, 0
    
    for uid in list(datos["usuarios"].keys()):
        if str(uid) != ADMIN_ID:
            try:
                bot.send_message(uid, f"📢 *ANUNCIO JSL*\n\n{texto_enviar}", parse_mode="Markdown")
                enviados += 1
                time.sleep(0.1) # Pausa para evitar bloqueo por spam de Telegram
            except Exception:
                fallidos += 1
                
    bot.reply_to(message, f"✅ Finalizado.\nEnviados: *{enviados}*\nBloqueados/Borrados: *{fallidos}*", parse_mode="Markdown")

@bot.message_handler(commands=["activar"])
def cmd_activar_usuario(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    partes = message.text.split()
    if len(partes) < 2:
        return bot.reply_to(message, "❌ Uso: `/activar 123456789`", parse_mode="Markdown")
    
    target_id = partes[1]
    usr = obtener_o_crear_usuario(target_id)
    usr["licencia"] = True
    guardar_datos()
    
    bot.reply_to(message, f"✅ Licencia VIP *ACTIVADA* para `{target_id}`.", parse_mode="Markdown")
    try:
        bot.send_message(target_id, "🎉 *¡LICENCIA ACTIVADA!*\n\nTu acceso VIP ha sido habilitado sin límite de tiempo.", parse_mode="Markdown")
    except:
        pass

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
    guardar_datos()
    bot.reply_to(message, f"🚫 Licencia *DESACTIVADA* para `{target_id}`.", parse_mode="Markdown")

@bot.message_handler(commands=["usuarios"])
def cmd_listar_usuarios(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    total = len(datos["usuarios"])
    con_licencia = sum(1 for u in datos["usuarios"].values() if u.get("licencia"))
    texto = (f"📊 *ESTADÍSTICAS DEL SISTEMA*\n\n"
             f"👥 Total Registrados: *{total}*\n"
             f"💎 Usuarios VIP: *{con_licencia}*\n"
             f"⏳ Pruebas/Expirados: *{total - con_licencia}*\n"
             f"💵 Tasa configurada: *{datos.get('tasa', 720.0)} CUP*")
    bot.send_message(message.chat.id, texto, parse_mode="Markdown")

# ==================== COMANDOS DE CLIENTES ====================
@bot.message_handler(commands=["start"])
def comando_start(message):
    acceso, tipo = verificar_acceso(message.from_user.id)
    if not acceso:
        bot.send_message(message.chat.id, mensaje_bloqueo(), parse_mode="Markdown")
        return
    bot.send_message(
        message.chat.id,
        "👋 Bienvenido a *JSL - USDT Bot*.\n\nElige una opción en el menú inferior:",
        parse_mode="Markdown",
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
    
    bot.send_message(message.chat.id, f"🆔 *TU PERFIL*\n\n👤 Tu ID: `{uid}`\n📌 Estado: *{estado_txt}*", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "💵 Consultar USDT Real")
def consultar_precio(message):
    acceso, tipo = verificar_acceso(message.from_user.id)
    if not acceso:
        bot.send_message(message.chat.id, mensaje_bloqueo(), parse_mode="Markdown")
        return
    
    tasa = datos.get("tasa", 780.00)
    bot.send_message(message.chat.id, f"💵 *TASA EN TIEMPO REAL*\n\n💰 Valor actual: *{tasa} CUP*\n📊 Fuente: Actualizado por la administración JSL", parse_mode="Markdown")

# ==================== SERVIDOR WEB PARA EVITAR QUE RENDER APAGUE EL BOT ====================
class ServidorPing(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot JSL Activo (GET OK)")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

    def log_message(self, format, *args):
        pass # Ignora el spam de los logs de los pings para que tu consola esté limpia

def iniciar_servidor():
    puerto = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", puerto), ServidorPing)
    server.serve_forever()

if __name__ == "__main__":
    # Arrancamos el servidor web en un hilo secundario
    threading.Thread(target=iniciar_servidor, daemon=True).start()
    print("Bot JSL iniciando y esperando conexiones...")
    
    # Notificación al administrador cuando el bot arranca
    try:
        bot.send_message(ADMIN_ID, f"🟢 *Servidor Iniciado/Reiniciado*\n\nTasa cargada en memoria: *{datos.get('tasa', 720.0)} CUP*\n(Si Render reseteó los datos, reenvíame el último archivo usuarios.json)", parse_mode="Markdown")
    except Exception:
        pass
    
    # Bucle infinito resistente a desconexiones
    bot.infinity_polling(timeout=60, long_polling_timeout=60)

