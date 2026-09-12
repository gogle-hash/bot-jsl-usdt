from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import requests
import telebot
from telebot import types
import threading
import time

TOKEN = "8881010834:AAEeIE20GxhG1KthPpZd1pxQ-PSKyB5MHBU"
bot = telebot.TeleBot(TOKEN)

# ID del Administrador (Javier)
ADMIN_ID = "7995284100"

# Tiempo de prueba (3 días en segundos)
TIEMPO_PRUEBA = 3 * 24 * 60 * 60

# Configuración de Supabase desde variables de Render
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

# Tasa en memoria
tasa_actual = {"usdt": 720.00, "fuente": "Actualizado por JSL"}

# ==================== BASE DE DATOS (SUPABASE) ====================


def obtener_estado_usuario(user_id):
  url = f"{SUPABASE_URL}/rest/v1/usuarios?user_id=eq.{user_id}&select=*"
  try:
    response = requests.get(url, headers=headers)
    data = response.json()
    if isinstance(data, list) and len(data) > 0:
      return data[0]
    else:
      nuevo_usuario = {
          "user_id": str(user_id),
          "registro": time.time(),
          "licencia": False,
      }
      requests.post(
          f"{SUPABASE_URL}/rest/v1/usuarios", headers=headers, json=nuevo_usuario
      )
      return nuevo_usuario
  except Exception as e:
    print("Error Supabase:", e)
    return {"user_id": str(user_id), "registro": time.time(), "licencia": False}


def cambiar_licencia_db(user_id, estado_licencia):
  url = f"{SUPABASE_URL}/rest/v1/usuarios?user_id=eq.{user_id}"
  payload = {"licencia": estado_licencia}
  try:
    response = requests.patch(url, headers=headers, json=payload)
    return response.status_code in [200, 204]
  except Exception as e:
    print("Error actualizando licencia:", e)
    return False


def obtener_todos_usuarios():
  url = f"{SUPABASE_URL}/rest/v1/usuarios?select=*"
  try:
    response = requests.get(url, headers=headers)
    data = response.json()
    if isinstance(data, list):
      return data
    return []
  except Exception as e:
    print("Error al obtener usuarios:", e)
    return []


# ==================== LÓGICA DE LICENCIAS ====================


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
      "adquiere tu **Licencia VIP**.\n\n"
      "👤 *Comunícate con la administración para activar tu acceso:*\n"
      "👉 Contacto: @TuUsuarioDeTelegram\n"
      "📞 Teléfono: +53 51420349"
  )


# ==================== INTERFAZ Y TECLADO ====================


def crear_teclado():
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  btn_precio = types.KeyboardButton("💵 Consultar USDT Real")
  btn_id = types.KeyboardButton("🆔 Mi ID / Estado")
  markup.add(btn_precio, btn_id)
  return markup


# ==================== COMANDOS DE ADMINISTRADOR ====================


@bot.message_handler(commands=["admin"])
def cmd_admin(message):
  if str(message.from_user.id) != ADMIN_ID:
    return
  texto = (
      "⚙️ *PANEL DE ADMINISTRACIÓN JSL*\n\n"
      "• `/tasa [monto]` - Cambia la tasa USDT (Ej: `/tasa 725`)\n"
      "• `/activar [user_id]` - Activa licencia a un usuario\n"
      "• `/desactivar [user_id]` - Desactiva licencia a un usuario\n"
      "• `/usuarios` - Muestra estadísticas de la base de datos"
  )
  bot.send_message(message.chat.id, texto, parse_mode="Markdown")


@bot.message_handler(commands=["tasa"])
def cmd_cambiar_tasa(message):
  if str(message.from_user.id) != ADMIN_ID:
    return
  partes = message.text.split()
  if len(partes) < 2:
    bot.reply_to(message, "❌ Uso correcto: `/tasa 725`", parse_mode="Markdown")
    return
  try:
    nueva_tasa = float(partes[1])
    tasa_actual["usdt"] = nueva_tasa
    bot.reply_to(
        message,
        f"✅ Tasa actualizada correctamente a: *{nueva_tasa} CUP*",
        parse_mode="Markdown",
    )
  except ValueError:
    bot.reply_to(message, "❌ Error: El monto debe ser un número entero o decimal.")


@bot.message_handler(commands=["activar"])
def cmd_activar_usuario(message):
  if str(message.from_user.id) != ADMIN_ID:
    return
  partes = message.text.split()
  if len(partes) < 2:
    bot.reply_to(
        message, "❌ Uso correcto: `/activar 123456789`", parse_mode="Markdown"
    )
    return
  target_id = partes[1]
  if cambiar_licencia_db(target_id, True):
    bot.reply_to(
        message,
        f"✅ Licencia *ACTIVADA* para el usuario `{target_id}`.",
        parse_mode="Markdown",
    )
    try:
      bot.send_message(
          target_id,
          "🎉 *¡LICENCIA ACTIVADA!*\n\nTu acceso vitalicio al bot JSL ha sido activado por el administrador.",
          parse_mode="Markdown",
      )
    except Exception:
      pass
  else:
    bot.reply_to(message, "❌ Error al actualizar en Supabase.")


@bot.message_handler(commands=["desactivar"])
def cmd_desactivar_usuario(message):
  if str(message.from_user.id) != ADMIN_ID:
    return
  partes = message.text.split()
  if len(partes) < 2:
    bot.reply_to(
        message,
        "❌ Uso correcto: `/desactivar 123456789`",
        parse_mode="Markdown",
    )
    return
  target_id = partes[1]
  if cambiar_licencia_db(target_id, False):
    bot.reply_to(
        message,
        f"🚫 Licencia *DESACTIVADA* para el usuario `{target_id}`.",
        parse_mode="Markdown",
    )
  else:
    bot.reply_to(message, "❌ Error al actualizar en Supabase.")


@bot.message_handler(commands=["usuarios"])
def cmd_listar_usuarios(message):
  if str(message.from_user.id) != ADMIN_ID:
    return
  lista = obtener_todos_usuarios()
  total = len(lista)
  con_licencia = sum(1 for u in lista if u.get("licencia"))

  texto = (
      f"📊 *ESTADÍSTICAS JSL*\n\n"
      f"👥 Total registrados: *{total}*\n"
      f"💎 Licencias activas: *{con_licencia}*\n"
      f"⏳ En periodo de prueba / expirados: *{total - con_licencia}*"
  )
  bot.send_message(message.chat.id, texto, parse_mode="Markdown")


# ==================== MANEJADORES DE USUARIOS ====================


@bot.message_handler(commands=["start"])
def comando_start(message):
  acceso, tipo = verificar_acceso(message.from_user.id)
  if not acceso:
    bot.send_message(message.chat.id, mensaje_bloqueo(), parse_mode="Markdown")
    return

  bot.send_message(
      message.chat.id,
      "👋 Bienvenido al Bot de USDT de JSL.\n\nElige una opción del menú de abajo:",
      reply_markup=crear_teclado(),
  )


@bot.message_handler(commands=["id"])
@bot.message_handler(func=lambda message: message.text == "🆔 Mi ID / Estado")
def consultar_id_estado(message):
  uid = message.from_user.id
  acceso, tipo = verificar_acceso(uid)

  estado_txt = "Desconocido"
  if tipo == "admin":
    estado_txt = "👑 Administrador"
  elif tipo == "licencia":
    estado_txt = "💎 Licencia VIP Activa"
  elif tipo == "prueba":
    estado_txt = "⏳ Periodo de Prueba Gratuito"
  else:
    estado_txt = "❌ Acceso Expirado"

  texto = (
      f"🆔 *TU INFORMACIÓN*\n\n"
      f"👤 Tu ID: `{uid}`\n"
      f"📌 Estado: *{estado_txt}*\n\n"
      f"_Envía tu ID al administrador cuando realices un pago para activar tu licencia._"
  )
  bot.send_message(message.chat.id, texto, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text == "💵 Consultar USDT Real"
)
def consultar_precio(message):
  acceso, tipo = verificar_acceso(message.from_user.id)
  if not acceso:
    bot.send_message(message.chat.id, mensaje_bloqueo(), parse_mode="Markdown")
    return

  texto = f"💵 *TASA USDT ACTUAL*\n\n💰 Valor: *{tasa_actual['usdt']} CUP*\n📊 Fuente: {tasa_actual['fuente']}"
  bot.send_message(message.chat.id, texto, parse_mode="Markdown")


# ==================== SERVIDOR WEB FALSO PARA RENDER ====================


class ServidorFalso(BaseHTTPRequestHandler):

  def do_GET(self):
    self.send_response(200)
    self.end_headers()
    self.wfile.write(b"Bot JSL Activo y Escuchando")


def mantener_vivo():
  puerto = int(os.environ.get("PORT", 10000))
  server = HTTPServer(("0.0.0.0", puerto), ServidorFalso)
  server.serve_forever()


if __name__ == "__main__":
  threading.Thread(target=mantener_vivo, daemon=True).start()
  print("Bot JSL iniciando con base de datos, panel admin y servidor web...")
  bot.infinity_polling()

