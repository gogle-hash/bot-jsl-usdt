import telebot
from telebot import types
import os
import time
import requests

TOKEN = "8881010834:AAEeIE20GxhGlKthPpZd1pxQ-PSKyB5MHBU"
bot = telebot.TeleBot(TOKEN)

# Tu ID real de administrador
ADMIN_ID = "7995284100"

# 3 días calculados en segundos
TIEMPO_PRUEBA = 3 * 24 * 60 * 60

# Variables de entorno de Supabase (las lee de Render automáticamente)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

tasa_actual = {
    "usdt": 720.00,
    "fuente": "Actualizado por JSL"
}

# --- SISTEMA DE BASE DE DATOS (SUPABASE EN LA NUBE) ---
def obtener_estado_usuario(user_id):
    url = f"{SUPABASE_URL}/rest/v1/usuarios?user_id=eq.{user_id}&select=*"
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        else:
            # Si el usuario es nuevo, lo registramos
            nuevo_usuario = {
                "user_id": str(user_id),
                "registro": time.time(),
                "licencia": False
            }
            requests.post(f"{SUPABASE_URL}/rest/v1/usuarios", headers=headers, json=nuevo_usuario)
            return nuevo_usuario
    except Exception as e:
        print("Error al conectar con Supabase:", e)
        return {"user_id": str(user_id), "registro": time.time(), "licencia": False}

# --- LÓGICA DE ACCESO Y LICENCIAS ---
def verificar_acceso(user_id):
    if str(user_id) == ADMIN_ID:
        return True, "admin"

    estado = obtener_estado_usuario(user_id)

    if estado.get("licencia"):
        return True, "licencia"

    tiempo_usado = time.time() - float(estado.get("registro", time.time()))
    if tiempo_usado < TIEMPO_PRUEBA:
        return True, "prueba"

    return False, "expirado"

def mensaje_bloqueo():
    return (
        "⏳ *TIEMPO DE PRUEBA AGOTADO* ⏳\n\n"
        "Tus 3 días de acceso gratuito al sistema JSL han finalizado.\n\n"
        "Para seguir consultando la tasa en tiempo real sin interrupciones, "
        "necesitas adquirir una **Licencia de Pago Único (Vitalicia)**.\n\n"
        "👤 *Comunícate con la administración para realizar tu pago y activar tu acceso:*\n"
        "👉 @TuUsuarioDeTelegram\n"
        "📞 +53 51420349"
    )

# --- INTERFAZ Y MANEJADORES ---
def crear_teclado():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_precio = types.KeyboardButton("Consultar USDT Real")
    markup.add(btn_precio)
    return markup

@bot.message_handler(commands=['start'])
def comando_start(message):
    acceso, tipo = verificar_acceso(message.from_user.id)
    if not acceso:
        bot.send_message(message.chat.id, mensaje_bloqueo(), parse_mode="Markdown")
        return
    
    bot.send_message(
        message.chat.id, 
        "👋 Bienvenido al Bot de USDT de JSL.\n\nElige una opción del menú de abajo:", 
        reply_markup=crear_teclado()
    )

@bot.message_handler(func=lambda message: message.text == "Consultar USDT Real")
def consultar_precio(message):
    acceso, tipo = verificar_acceso(message.from_user.id)
    if not acceso:
        bot.send_message(message.chat.id, mensaje_bloqueo(), parse_mode="Markdown")
        return
    
    texto = f"💵 *TASA USDT ACTUAL*\n\n💰 Valor: {tasa_actual['usdt']} CUP\n📊 Fuente: {tasa_actual['fuente']}"
    bot.send_message(message.chat.id, texto, parse_mode="Markdown")

if __name__ == "__main__":
    print("Bot JSL iniciando con Supabase en Render...")
    bot.infinity_polling()

