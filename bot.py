	mport os
import telebot
import requests

# Tus tokens y credenciales seguras (se configuran luego en Render)
TOKEN = os.getenv("BOT_TOKEN")  # Token de tu bot de Telegram
SUPABASE_URL = os.getenv("SUPABASE_URL")  # URL de tu proyecto Supabase
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # Key anon o service_role de Supabase

bot = telebot.TeleBot(TOKEN)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


def cargar_db():
  """Carga los usuarios y licencias desde la nube de Supabase"""
  try:
    url = f"{SUPABASE_URL}/rest/v1/usuarios?select=*"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
      data = response.json()
      db = {}
      for row in data:
        db[str(row["user_id"])] = {"licencia": row["licencia"]}
      return db
  except Exception as e:
    print(f"Error cargando DB: {e}")
  return {}


def guardar_usuario_db(user_id, licencia_val):
  """Guarda o actualiza un usuario directamente en Supabase"""
  try:
    url = f"{SUPABASE_URL}/rest/v1/usuarios"
    payload = {"user_id": str(user_id), "licencia": licencia_val}
    headers_upsert = HEADERS.copy()
    headers_upsert["Prefer"] = "resolution=merge-duplicates"

    response = requests.post(url, headers=headers_upsert, json=payload)
    return response.status_code in [200, 201]
  except Exception as e:
    print(f"Error guardando DB: {e}")
    return False


# --- COMANDOS DEL BOT ---


@bot.message_handler(commands=["start"])
def send_welcome(message):
  user_id = str(message.from_user.id)
  db = cargar_db()

  # Si el usuario no existe en la base de datos, lo creamos con licencia False por defecto
  if user_id not in db:
    guardar_usuario_db(user_id, False)

  bot.reply_to(
      message,
      "¡Bienvenido al Bot JSL de monitoreo USDT! Tu usuario ha sido registrado"
      " en la base de datos segura.",
  )


@bot.message_handler(commands=["dar_licencia"])
def dar_licencia(message):
  # Comando de administrador para activar licencia a un usuario
  if str(message.from_user.id) == "TU_ID_DE_ADMIN":
    partes = message.text.split()
    if len(partes) > 1:
      id_a_activar = partes[1]
      guardar_usuario_db(id_a_activar, True)
      bot.reply_to(
          message,
          f"¡Licencia activada con éxito para el usuario {id_a_activar}!",
      )
    else:
      bot.reply_to(message, "Uso: /dar_licencia [ID_DEL_USUARIO]")
  else:
    bot.reply_to(message, "No tienes permisos para usar este comando.")


# Iniciar el bot
print("Bot JSL iniciado correctamente...")
bot.infinity_polling()

