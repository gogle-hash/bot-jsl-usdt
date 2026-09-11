import telebot
from telebot import types
import os
import json
import time

TOKEN = "8881010834:AAEeIE20GxhG1KthPpZd1pxQ-PSKyB5MHBU"
bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 7995284100
ARCHIVO_DB = "usuarios.json"
TIEMPO_PRUEBA = 3 * 24 * 60 * 60 

tasa_actual = {
    "usdt": 720.00,
    "fuente": "Actualizado por JSL"
}

def cargar_db():
    if not os.path.exists(ARCHIVO_DB):
        return {}
    try:
        with open(ARCHIVO_DB, "r") as f:
            return json.load(f)
    except:
        return {}

def guardar_db(db):
    with open(ARCHIVO_DB, "w") as f:
        json.dump(db, f, indent=4)

def obtener_estado_usuario(user_id):
    db = cargar_db()
    uid_str = str(user_id)
    if uid_str not in db:
        db[uid_str] = {
            "registro": time.time(),
            "licencia": False
        }
        guardar_db(db)
    return db[uid_str]

def verificar_acceso(user_id):
    if user_id == ADMIN_ID:
        return True, "admin"
    estado = obtener_estado_usuario(user_id)
    if estado["licencia"]:
        return True, "licencia"
    tiempo_usado = time.time() - estado["registro"]
    if tiempo_usado < TIEMPO_PRUEBA:
        return True, "prueba"
    return False, "expirado"

def mensaje_bloqueo():
    return (
        "⛔ *TIEMPO DE PRUEBA AGOTADO* ⛔\n\n"
        "Tus 3 días de acceso gratuito al sistema JSL han finalizado.\n\n"
        "Para seguir consultando la tasa en tiempo real sin interrupciones, "
        "necesitas adquirir una **Licencia de Pago Único (Vitalicia)**.\n\n"
        "📲 *Comunícate por WhatsApp para realizar tu pago y activar tu acceso:*\n"
        "👉 https://wa.me/5351420349"
    )

def crear_teclado():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_precio = types.KeyboardButton("💱 Consultar USDT Real")
    markup.add(btn_precio)
    return markup

@bot.message_handler(commands=['start', 'ayuda'])
def enviar_bienvenida(message):
    acceso, tipo = verificar_acceso(message.chat.id)
    if not acceso:
        bot.send_message(message.chat.id, mensaje_bloqueo(), parse_mode="Markdown")
        return
    estado = obtener_estado_usuario(message.chat.id)
    texto = "¡Hola! Bot JSL de Monitoreo USDT activo.\n\n"
    if tipo == "prueba":
        tiempo_restante = TIEMPO_PRUEBA - (time.time() - estado["registro"])
        dias_restantes = int(tiempo_restante // (24 * 3600))
        texto += f"⚠️ *Estás en tu período de prueba.* Te quedan {dias_restantes} días gratis.\n\n"
    elif tipo == "licencia":
        texto += "✅ *Tu licencia JSL está activa (Pago Único).* Gracias por tu confianza.\n\n"
    texto += "Toca el botón de abajo para consultar la cotización actual del mercado."
    bot.send_message(message.chat.id, texto, reply_markup=crear_teclado(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text in ["💱 Consultar USDT Real", "/precio"])
def ver_precio(message):
    acceso, tipo = verificar_acceso(message.chat.id)
    if not acceso:
        bot.send_message(message.chat.id, mensaje_bloqueo(), parse_mode="Markdown")
        return
    respuesta = (
        f"📊 *Monitoreo USDT Real (Cuba)*\n\n"
        f"🟢 *USDT (Base):* `{tasa_actual['usdt']:.2f} CUP`\n"
        f"📡 *Estado:* Dinámico en tiempo real"
    )
    bot.send_message(message.chat.id, respuesta, parse_mode="Markdown", reply_markup=crear_teclado())

@bot.message_handler(commands=['set'])
def actualizar_tasa(message):
    global tasa_actual
    if message.from_user.id != ADMIN_ID:
        return
    try:
        partes = message.text.split()
        if len(partes) < 2:
            bot.reply_to(message, "⚠️ Uso correcto: `/set 725`", parse_mode="Markdown")
            return
        nuevo_valor = float(partes[1])
        tasa_actual["usdt"] = nuevo_valor
        bot.reply_to(message, f"✅ ¡Tasa actualizada! Nuevo precio USDT: *{nuevo_valor:.2f} CUP*", parse_mode="Markdown")
    except ValueError:
        bot.reply_to(message, "⚠️ Error: Pon un número válido.")

@bot.message_handler(commands=['licencia'])
def otorgar_licencia(message):
    if message.from_user.id != ADMIN_ID:
        return
    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "⚠️ Uso correcto: `/licencia ID_DEL_USUARIO`\nEjemplo: `/licencia 123456789`")
        return
    user_id_obj = partes[1]
    db = cargar_db()
    if user_id_obj not in db:
        bot.reply_to(message, "❌ Ese ID no está registrado en la base de datos del bot.")
        return
    db[user_id_obj]["licencia"] = True
    guardar_db(db)
    bot.reply_to(message, f"✅ Licencia vitalicia otorgada al usuario ID: `{user_id_obj}`")
    try:
        bot.send_message(user_id_obj, "🎉 *¡FELICIDADES!* 🎉\nTu licencia de pago único ha sido activada por la administración. Ya tienes acceso vitalicio al sistema JSL.", parse_mode="Markdown")
    except:
        pass

@bot.message_handler(commands=['stats'])
def ver_estadisticas(message):
    if message.from_user.id != ADMIN_ID:
        return
    db = cargar_db()
    total = len(db)
    con_licencia = sum(1 for data in db.values() if data["licencia"])
    en_prueba = total - con_licencia
    bot.reply_to(message, f"📈 *Estadísticas de JSL Negocios*\n\n👥 Usuarios totales: *{total}*\n✅ Con Licencia Pagada: *{con_licencia}*\n⏳ En periodo de prueba: *{en_prueba}*", parse_mode="Markdown")

@bot.message_handler(commands=['alerta'])
def enviar_alerta(message):
    if message.from_user.id != ADMIN_ID:
        return
    texto_alerta = message.text.replace("/alerta", "").strip()
    if not texto_alerta:
        bot.reply_to(message, "⚠️ Falta el mensaje.", parse_mode="Markdown")
        return
    db = cargar_db()
    enviados = 0
    bot.reply_to(message, "⏳ Enviando alerta masiva...")
    for uid in db.keys():
        try:
            bot.send_message(uid, f"🔔 *Notificación Oficial JSL*\n\n{texto_alerta}", parse_mode="Markdown")
            enviados += 1
        except:
            pass
    bot.reply_to(message, f"✅ ¡Alerta enviada a {enviados} usuarios!")

print("Bot JSL PRO (Con WhatsApp y Licencias) iniciado...")
bot.infinity_polling()
