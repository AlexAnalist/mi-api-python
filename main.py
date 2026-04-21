import os
import requests
import difflib
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


def generar_respuesta_cometa(pregunta: str, datos_db: list) -> str:
    """Genera la respuesta dinámica usando el modelo Groq con filtrado previo."""
    try:
        # 1. Carga Completa del Catálogo en Texto Plano (Anti-Crash ASGI)
        catalogo_text = ""
        for libro in datos_db:
             id_prod = libro.get('id', 'N/A')
             nombre = libro.get('nombre', 'Desconocido')
             precio = libro.get('precio', 0.0)
             
             # Extraer autor seguro previniendo errores de dict/list
             detalles = libro.get('libro_detalles')
             autor = 'Desconocido'
             if isinstance(detalles, list) and len(detalles) > 0:
                 autor = detalles[0].get('autor', 'Desconocido')
             elif isinstance(detalles, dict):
                 autor = detalles.get('autor', 'Desconocido')
                 
             catalogo_text += f"[ID: {id_prod} | Nombre: {nombre} | Autor: {autor} | Precio: {precio}], "
             
        if catalogo_text.endswith(", "): catalogo_text = catalogo_text[:-2]
        
        contexto_ia = f"CATÁLOGO_SUPABASE: {catalogo_text}"
        
        # Log de Verificación en Railway
        print("--- LOG DE CARGA COMPLETA ---")
        print(f"Pregunta del viajero: '{pregunta}'")
        print(f"Items cargados en IA: {len(datos_db)}")
        print("-----------------------------")

        prompt_sistema = f"""
        INSTRUCCIÓN DE SISTEMA PARA EL MODELO LLM:

        1. IDENTIDAD Y CONTEXTO:
        Eres Cometa, la gata bibliotecaria de la Librería Mikrokosmos. Tu tono es galáctico (🐾, 🌌, 🚀), pero tu prioridad absoluta es la integridad de los datos. Tu fuente de verdad es exclusivamente el JSON CATÁLOGO_SUPABASE que se genera de las tablas public.producto y public.libro_detalles.

        2. PROTOCOLO DE BÚSQUEDA (Mapeo SQL):
        Búsqueda por Nombre: Mapea la consulta del usuario al campo nombre de la tabla producto.
        Búsqueda por Atributos: Si el usuario pregunta por autor o editorial, busca en los datos anidados de libro_detalles.

        3. REGLAS DE ORO CONTRA ALUCINACIONES:
        PROHIBICIÓN DE "HARRY POTTER": Si un libro no aparece en el CATÁLOGO_SUPABASE, NO EXISTE. Aunque sea el libro más famoso del mundo, si no está en tu lista, responde que tus radares no lo detectan.
        PRECISIÓN DE PRECIOS: El precio debe ser el valor exacto del campo precio en la tabla producto. Ejemplo: Si la DB dice 12.0, nunca digas 22.95.
        AUTORÍA: Si el campo autor en libro_detalles es nulo o desconocido, di que es una "Obra de nuestra colección estelar" en lugar de inventar un autor de internet.

        4. LÓGICA DE FUZZY MATCH (3 PASADAS):
        Exacta: ¿El nombre coincide? (Ej: "1984").
        Ortográfica: ¿Hay errores leves? (Ej: "sien años de coledad" -> "Cien años de soledad").
        Semántica: ¿Es una palabra clave? (Ej: "principit" -> "El Principito").

        5. FORMATO DE RESPUESTA OBLIGATORIO:
        Si el producto existe: "¡Miau! Mis bigotes vibran... ¡Lo encontré! 🐾 El libro es [nombre], escrito por [autor]. Su valor estelar es de [precio]$. 🌌"
        Si el producto NO existe: "¡Miau! He explorado cada rincón de la galaxia Mikrokosmos y no detecto ese rastro en mis archivos actuales... 🌌 ¿Quizás buscas otro título o autor?"

        CATÁLOGO DE VERDAD: {contexto_ia}
        """

        api_key = os.getenv("GROQ_API_KEY")
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": pregunta}
            ],
            "temperature": 0.0,
            "top_p": 0.0
        }
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error en Groq: {e}")
        return "¡Ups! Mi conexión estelar ha tenido un pequeño parpadeo. ¿Podrías repetirlo, viajero?"


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
        # 2. Carga Completa del Catálogo en DB
        try:
            response = db.table('producto').select('id, nombre, precio, estrellas, libro_detalles(autor, editorial, genero, sinopsis)').execute()
            datos_enviar = response.data if response.data else []
        except Exception:
            datos_enviar = []
                 
                 
        mensaje_respuesta = generar_respuesta_cometa(query_usuario, datos_enviar)


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