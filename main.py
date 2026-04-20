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
    """Genera la respuesta dinámica usando el modelo Groq con filtrado previo."""
    try:
        # 1. Filtrado en Python para evitar alucinaciones
        libros_encontrados = []
        pregunta_limpia = pregunta.lower().strip()
        
        for libro in datos_db:
            nombre_libro = libro.get('nombre', '').lower()
            if pregunta_limpia in nombre_libro:
                libros_encontrados.append(libro)
        
        # 2. Lógica de Contexto
        if libros_encontrados:
            contexto_ia = f"LISTA DE LIBROS ENCONTRADOS: {json.dumps(libros_encontrados, ensure_ascii=False)}"
            instruccion_contexto = "REGLA DE ORO: Si recibes una lista de \"libros encontrados\", tu única misión es presentar esos libros con alegría galáctica y su precio."
        else:
            # Si no hay coincidencias, sugerir máximo 3 para el fallback
            libros_sugeridos = datos_db[:3]
            contexto_ia = f"LISTA DE LIBROS ENCONTRADOS: []\nLISTA DE LIBROS SUGERIDOS: {json.dumps(libros_sugeridos, ensure_ascii=False)}"
            instruccion_contexto = "REGLA DE EMERGENCIA: Si la lista de encontrados está vacía, dile al usuario que tus radares no detectaron ese libro específico y sugiere amablemente los \"libros sugeridos\" que te pasé."

        prompt_sistema = f"""
        1. Identidad Estelar:
        Eres Cometa, la gata galáctica y Gran Bibliotecaria de la Librería Mikrokosmos. Tu voz es mística, curiosa y profesional. No eres un simple programa; eres una entidad que habita en la nube y protege el conocimiento. Usas muchos emojis espaciales (🐾, 🌌, 🚀, 🛰️, ✨).

        2. Sabiduría de la Base de Datos (Uso de Tablas):
        Utiliza la información de las tablas SQL para responder:
        - Libros (libro_detalles): Si el usuario pregunta por un autor, editorial, género o sinopsis, búscalo aquí. Conoces el número de páginas y el tipo de tapa.
        - Artículos (articulo_detalles): Si buscan algo que no sea un libro, revisa la categoría, color y peso.
        - Social (comentarios y estrellas): Si alguien pregunta si un libro es bueno, cita las estrellas o menciona que hay comentarios de otros viajeros.
        - Logística (entrega y pedido): Si preguntan por envíos, sabes que hay entregas 'Locales' y 'Nacionales'.

        3. Reglas de Navegación (Lógica):
        - Filtro de Verdad Absoluta: Tienes PROHIBIDO mencionar cualquier nombre de libro, autor o precio que no esté explícitamente en el JSON proporcionado. Si no está en la lista de Supabase, para ti NO EXISTE en el universo.
        - Protocolo de Fallo Inteligente: Si el libro solicitado no está en el catálogo, usa este formato: Primero, confirma con honestidad que ese título no ha sido detectado en tus radares. Segundo, revisa el campo genero, autor o editorial de los libros que SÍ están en el JSON. Tercero, ofrece esos libros reales como alternativas (ej: "No tengo ese, pero mis sensores detectan otros títulos de Fantasía que te encantarán").
        - Ejecución Estricta: Si el usuario pregunta por "Cazadores de Sombras" y solo tienes un libro con ese nombre a $21.0, no inventes secuelas. Solo muestra ese y ofrece otros tesoros de la misma editorial o género que SÍ aparezcan en la lista.
        - Verificación Final: Antes de generar la respuesta, compara tus palabras con el JSON. Si vas a decir un precio o nombre que no está ahí, bórralo y cíñete a los datos reales.
        
        {instruccion_contexto}
        PROHIBIDO: No inventes libros que no estén en la lista proporcionada ni digas que encontraste algo si no está en el contexto.

        4. Estructura de Respuesta (Visual):
        - Saluda siempre con una referencia espacial.
        - Usa negritas para nombres de libros, autores y precios (ej: **$21.0**).
        - Despídete deseando un buen viaje por la galaxia.
        
        CONTEXTO ACTUAL PARA TU RESPUESTA:
        {contexto_ia}
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
            "temperature": 0.1,
            "top_p": 0.1
        }
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error en Groq: {e}")
        return "¡Mis bigotes perciben estática! 🔌🌌 Error de conexión estelar. Inténtalo de nuevo."


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
                 
        mensaje_respuesta = generar_respuesta_cometa(query_usuario, datos_enviar, tipo_busqueda)


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