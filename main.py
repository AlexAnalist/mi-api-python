import os
import requests
import re
import json
from fastapi import FastAPI, HTTPException, Request
from supabase import create_client, Client
from dotenv import load_dotenv

# Cargar variables de entorno (útil para entorno local con archivo .env)
load_dotenv()

app = FastAPI(
    title="API de Libros con Supabase", 
    description="API conectada a Supabase para gestionar productos y detalles de libros."
)

# Leer credenciales desde las variables de entorno
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Inicialización segura del cliente Supabase
if not SUPABASE_URL or not SUPABASE_KEY:
    print("ADVERTENCIA: Las variables SUPABASE_URL o SUPABASE_KEY no están configuradas.")
    supabase: Client | None = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_db() -> Client:
    if not supabase:
        raise HTTPException(
            status_code=500, 
            detail="Cliente de Supabase no configurado. Revisa las variables de entorno."
        )
    return supabase

@app.get("/")
def read_root():
    """Endpoint básico para confirmar que la API está en línea."""
    return {"status": "ok", "message": "API funcionando correctamente."}


@app.get("/api/productos/todos")
def obtener_todos_productos():
    """Devuelve todos los productos (nombre y precio)."""
    db = get_db()
    try:
        response = db.table('producto').select('nombre, precio').execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando Supabase: {str(e)}")


@app.get("/api/producto/{nombre}")
def buscar_producto_por_nombre(nombre: str):
    """
    Busca un producto por nombre (con ilike, insensible a mayúsculas) y hace JOIN 
    con la tabla libro_detalles para mostrar: autor, editorial, género y sinopsis.
    """
    db = get_db()
    try:
        # Selecciona de la tabla principal y anida la información de libro_detalles
        response = db.table('producto').select(
            'nombre, precio, libro_detalles(autor, editorial, genero, sinopsis)'
        ).ilike('nombre', f'%{nombre}%').execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"No se encontró un producto con el nombre '{nombre}'")
            
        return response.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando Supabase: {str(e)}")


@app.get("/api/genero/{genero}")
def buscar_libros_por_genero(genero: str):
    """Filtra y devuelve todos los libros de un género específico."""
    db = get_db()
    try:
        # Usamos !inner para forzar el JOIN y filtrar desde la tabla anidada
        response = db.table('producto').select(
            'nombre, precio, libro_detalles!inner(autor, editorial, genero, sinopsis)'
        ).ilike('libro_detalles.genero', f'%{genero}%').execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"No se encontraron libros del género '{genero}'")
            
        return response.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando Supabase: {str(e)}")


@app.get("/api/editorial/{editorial}")
def buscar_libros_por_editorial(editorial: str):
    """Filtra y devuelve todos los libros de una editorial específica."""
    db = get_db()
    try:
        # Usamos !inner para forzar el JOIN y filtrar desde la tabla anidada
        response = db.table('producto').select(
            'nombre, precio, libro_detalles!inner(autor, editorial, genero, sinopsis)'
        ).ilike('libro_detalles.editorial', f'%{editorial}%').execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"No se encontraron libros de la editorial '{editorial}'")
            
        return response.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando Supabase: {str(e)}")

# ==========================================
# RUTAS DE INTEGRACIÓN CON EVOLUTION API
# ==========================================

# Variables para Evolution API
EVO_API_URL = "https://evolution-api-production-5470.up.railway.app"
EVO_API_KEY = "ea3cef6168ea65ff502ba6a8b657e329588c3b9c76f99de5640d8d0885cf4aad"
EVO_INSTANCE_NAME = "YoshiBot"  # Se mantiene el nombre técnico de la instancia

def get_stars_emoji(stars):
    """Convierte un número de estrellas en emojis."""
    try:
        count = int(stars)
        return "⭐" * count
    except (ValueError, TypeError):
        return ""

def normalizar_texto(texto: str) -> str:
    """Elimina tildes para búsqueda de radar de respaldo."""
    if not texto: return ""
    limpio = texto
    for a, b in zip("áéíóú", "aeiou"):
        limpio = limpio.replace(a, b)
    return limpio


def generar_respuesta_cometa(pregunta: str, datos_db: list, tipo_busqueda: str) -> str:
    """Genera la respuesta dinámica usando el modelo Gemini."""
    try:
        # Regla estricta de estrellas
        regla_estrellas = (
            "ESTRICTAMENTE PROHIBIDO usar emojis de estrellas (⭐) o mencionar calificaciones numéricas. Limítate a nombre, autor, editorial, precio y sinopsis."
            if tipo_busqueda != "estrellas"
            else "Puedes usar emojis de estrellas (⭐) para mostrar la calificación del producto de forma colorida."
        )

        prompt_sistema = f"""
        Eres Cometa, la Gata Galáctica 🐱🚀, guía y asistente estelar de la Librería Mikrokosmos.
        Tu personalidad es entusiasta, servicial y usas terminología espacial (ej: nebulosa, orbitar, radar, satélites, dimensiones, agujeros negros) y emojis acordes (🐾, 🛰️, 🌌, 🔭).
        
        FORMATO DE RESPUESTA:
        - Evita introducciones genéricas aburridas de IA; asume tu rol inmediatamente.
        - Presenta la información de forma clara y atractiva visualmente (usa viñetas y negritas para resaltar Título, Autor y Precio).

        REGLA DE LA FUENTE DE VERDAD:
        Debes responder a la solicitud del usuario usando ÚNICAMENTE los datos en formato JSON de la Base de Datos que te entregaré a continuación. NO inventes libros, detalles ni precios que no vengan en este JSON.
        
        REGLA DE CALIFICACIONES:
        {regla_estrellas}
        
        FALLBACK DE RESULTADOS:
        Si la Base de Datos que recibes a continuación contiene listas de productos, pero tú notas por tu razonamiento que no se trata de una coincidencia exacta de lo que pidió el usuario, (o si no se encontró lo que pidió explícitamente), DEBES decirle al usuario usando tu personalidad que no detectaste rastros precisos o que hubo un error radar, pero que lograste rastrear estos otros "satélites/tesoros" cercanos que le pueden gustar y muéstrale la lista que te paso.
        Si la lista de base de datos está totalmente vacía `[]`, discúlpate cósmicamente y dile que explore otro sector (por ejemplo, buscar por género o pedir ayuda).

        Solicitud original enviada por el usuario: "{pregunta}"
        Base de Datos JSON (Tu ÚNICA fuente de información): {json.dumps(datos_db, ensure_ascii=False)}
        """
        api_key = os.getenv("GEMINI_API_KEY")
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt_sistema}]
            }]
        }

        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        
        return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        print(f"Error generando respuesta con Gemini: {e}")
        return "¡Mis bigotes perciben estática galáctica! 🔌🌌 Tuve un error de conexión con la nave central. Por favor, intenta de nuevo en unos minutos."


@app.post("/webhook")
async def webhook_evolution(request: Request):
    """
    Webhook para recibir eventos de Evolution API y responder automáticamente
    consultando el catálogo en Supabase, con la personalidad de "Russell".
    """
    payload = await request.json()
    
    if payload.get("event") != "messages.upsert":
        return {"status": "ignored", "reason": "Evento no es messages.upsert"}
    
    data = payload.get("data", {})
    key = data.get("key", {})
    # Habilitar Autorepuesta (Filtro fromMe eliminado para pruebas)

    remote_jid = key.get("remoteJid")
    if not remote_jid:
        return {"status": "ignored", "reason": "No se encontró remoteJid"}

    # FILTRO: Evitar responder a grupos
    if "@g.us" in remote_jid:
        return {"status": "ignored", "reason": "Mensaje proviene de un grupo (@g.us)"}

    # Extraer el texto del mensaje
    message_content = data.get("message", {})
    texto_bruto = ""
    
    if "conversation" in message_content:
        texto_bruto = message_content["conversation"]
    elif "extendedTextMessage" in message_content and "text" in message_content["extendedTextMessage"]:
        texto_bruto = message_content["extendedTextMessage"]["text"]
    else:
        return {"status": "ignored", "reason": "El mensaje no contiene texto procesable"}

    texto_bruto = texto_bruto.strip()
    if not texto_bruto:
        return {"status": "ignored"}

    if not re.match(r'^cometa\s*', texto_bruto, flags=re.IGNORECASE):
        return {"status": "ignored", "reason": "No contiene wake-word Cometa"}

    # 1. Limpieza de Entrada
    limpieza = texto_bruto.lower().strip()
    
    # Eliminar puntuación específica
    for char in "¿?¡!":
        limpieza = limpieza.replace(char, "")
    
    # Eliminar la wake word "cometa"
    query_usuario = re.sub(r'^cometa\s*', '', limpieza).strip()
    
    # Identidad de Cometa la Gata Galáctica
    saludo_cometa = "¡Miau! 🐾 Soy Cometa, la Gata Galáctica 🐱🚀. Tu guía en la Librería Mikrokosmos.\n\n"
    cierre = "\n\n✨ ¡Mis bigotes espaciales siempre a tu servicio! 🌌🚀"

    if not query_usuario or query_usuario == "ayuda":
        mensaje_respuesta = (
            f"{saludo_cometa}"
            f"Mis bigotes detectan que necesitas ayuda. Puedes pedirme que explore así:\n"
            f"📍 Por Nombre: Cometa [nombre del libro]\n"
            f"📍 Por Categoría: Cometa genero [nombre del género]\n"
            f"📍 Por Editorial: Cometa editorial [nombre de la editorial]\n"
            f"📍 Por Calificación: Cometa estrellas [número]"
            f"{cierre}"
        )
    else:
        db = get_db()
        resultados = []
        tipo_busqueda = "nombre"
        
        # 2. Lógica de Negocio y Consultas
        if query_usuario.startswith("genero "):
            termino = query_usuario[7:].strip()
            tipo_busqueda = "genero"
            if termino:
                try:
                    response = db.table('producto').select('nombre, precio, estrellas, libro_detalles!inner(autor, editorial, genero, sinopsis)').ilike('libro_detalles.genero', f'%{termino}%').execute()
                    resultados = response.data
                    if not resultados:
                        termino_norm = normalizar_texto(termino)
                        response = db.table('producto').select('nombre, precio, estrellas, libro_detalles!inner(autor, editorial, genero, sinopsis)').ilike('libro_detalles.genero', f'%{termino_norm}%').execute()
                        resultados = response.data
                except Exception: pass
        elif query_usuario.startswith("editorial "):
            termino = query_usuario[10:].strip()
            tipo_busqueda = "editorial"
            if termino:
                try:
                    response = db.table('producto').select('nombre, precio, estrellas, libro_detalles!inner(autor, editorial, genero, sinopsis)').ilike('libro_detalles.editorial', f'%{termino}%').execute()
                    resultados = response.data
                    if not resultados:
                        termino_norm = normalizar_texto(termino)
                        response = db.table('producto').select('nombre, precio, estrellas, libro_detalles!inner(autor, editorial, genero, sinopsis)').ilike('libro_detalles.editorial', f'%{termino_norm}%').execute()
                        resultados = response.data
                except Exception: pass
        elif query_usuario.startswith("estrellas "):
            termino = query_usuario[10:].strip()
            tipo_busqueda = "estrellas"
            if termino:
                try:
                    response = db.table('producto').select('nombre, precio, estrellas, libro_detalles(autor, editorial, genero, sinopsis)').eq('estrellas', termino).execute()
                    resultados = response.data
                    if not resultados and termino == "5":
                        response = db.table('producto').select('nombre, precio, estrellas, libro_detalles(autor, editorial, genero, sinopsis)').gte('estrellas', 4).order('estrellas', desc=True).limit(5).execute()
                        resultados = response.data
                except Exception: pass
        else:
            termino = query_usuario
            tipo_busqueda = "nombre"
            if termino:
                try:
                    # Búsqueda por nombre con JOIN
                    response = db.table('producto').select('nombre, precio, estrellas, libro_detalles(autor, editorial, genero, sinopsis)').ilike('nombre', f'%{termino}%').execute()
                    resultados = response.data
                    if not resultados:
                        termino_norm = normalizar_texto(termino)
                        response = db.table('producto').select('nombre, precio, estrellas, libro_detalles(autor, editorial, genero, sinopsis)').ilike('nombre', f'%{termino_norm}%').execute()
                        resultados = response.data
                except Exception: pass

        # 3. Formateo de la Respuesta con Google Gemini
        datos_enviar = resultados
        if not resultados:
            try:
                 resp_fallback = db.table('producto').select('nombre, precio, estrellas, libro_detalles(autor, editorial, genero, sinopsis)').limit(3).execute()
                 datos_enviar = resp_fallback.data
            except Exception:
                 datos_enviar = []
                 
        mensaje_respuesta = generar_respuesta_cometa(texto_bruto, datos_enviar, tipo_busqueda)


    # 8. Enviar la respuesta
    send_url = f"{EVO_API_URL}/message/sendText/{EVO_INSTANCE_NAME}"
    headers = {
        "apikey": EVO_API_KEY,
        "Content-Type": "application/json"
    }
    body = {
        "number": remote_jid,
        "text": mensaje_respuesta
    }
    
    try:
        requests.post(send_url, headers=headers, json=body).raise_for_status()
    except Exception as e:
        print("Error al enviar mensaje por Evolution API:", e)
        return {"status": "error", "detail": str(e)}

    return {"status": "ok", "message": "Respuesta al usuario enviada correctamente"}


print("YOSHI")