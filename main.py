import os
import requests
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


@app.post("/webhook")
async def webhook_evolution(request: Request):
    """
    Webhook para recibir eventos de Evolution API y responder automáticamente
    consultando el catálogo en Supabase, con la personalidad de "Russell".
    """
    payload = await request.json(),
    
    if payload.get("event") != "messages.upsert":
        return {"status": "ignored", "reason": "Evento no es messages.upsert"}
    
    data = payload.get("data", {})
    key = data.get("key", {})
    '''
    if key.get("fromMe"):
        return {"status": "ignored", "reason": "Mensaje enviado por el bot (fromMe=true)"}
        '''
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

    # 1. Limpieza de Entrada
    limpieza = texto_bruto.lower()
    # Eliminar wake words
    for word in ["yoshi", "cometa"]:
        limpieza = limpieza.replace(word, "")
    
    # Eliminar puntuación específica
    for char in "¿?¡!":
        limpieza = limpieza.replace(char, "")
    
    query_usuario = limpieza.strip()
    
    # Identidad de Cometa
    saludo_cometa = "¡Saludos, explorador del cosmos! ☄️ Soy Cometa, tu guía interestelar en la Librería Mikrokosmos. ¡Listo para rastrear tesoros literarios en el infinito! 🚀🌌\n\n"
    cierre = "\n\n✨ ¡Que las estrellas guíen tu lectura! 🌠"

    if not query_usuario or query_usuario == "ayuda":
        mensaje_respuesta = (
            f"{saludo_cometa}"
            f"Puedes pedirme que explore así:\n"
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
                except Exception: pass
        elif query_usuario.startswith("editorial "):
            termino = query_usuario[10:].strip()
            tipo_busqueda = "editorial"
            if termino:
                try:
                    response = db.table('producto').select('nombre, precio, estrellas, libro_detalles!inner(autor, editorial, genero, sinopsis)').ilike('libro_detalles.editorial', f'%{termino}%').execute()
                    resultados = response.data
                except Exception: pass
        elif query_usuario.startswith("estrellas "):
            termino = query_usuario[10:].strip()
            tipo_busqueda = "estrellas"
            if termino:
                try:
                    response = db.table('producto').select('nombre, precio, estrellas, libro_detalles(autor, editorial, genero, sinopsis)').eq('estrellas', termino).execute()
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
                except Exception: pass

        # 3. Formateo de la Respuesta
        if resultados:
            if tipo_busqueda in ["nombre", "estrellas"] and len(resultados) == 1:
                item = resultados[0]
                detalles = item.get('libro_detalles') or {}
                estrellas_visual = get_stars_emoji(item.get('estrellas', 0))
                
                sinopsis = detalles.get('sinopsis', 'Sin sinopsis disponible.')
                if len(sinopsis) > 150:
                    sinopsis = sinopsis[:147] + "..."

                mensaje_respuesta = (
                    f"{saludo_cometa}"
                    f"¡He orbitado y encontrado este tesoro!\n\n"
                    f"📖 *{item.get('nombre')}*\n"
                    f"✍️ Autor: {detalles.get('autor', 'N/A')}\n"
                    f"🏢 Editorial: {detalles.get('editorial', 'N/A')}\n"
                    f"💰 Precio: *${item.get('precio')}*\n"
                    f"✨ Calificación: {estrellas_visual}\n"
                    f"📝 Sinopsis: {sinopsis}"
                    f"{cierre}"
                )
            else:
                # Resultados múltiples (Género, Editorial o búsqueda amplia)
                libros_texto = ""
                for lb in resultados[:5]:
                    libros_texto += f"📖 *{lb.get('nombre')}* - ${lb.get('precio', 0)} {get_stars_emoji(lb.get('estrellas', 0))}\n"
                
                mensaje_respuesta = (
                    f"{saludo_cometa}"
                    f"¡He detectado estos tesoros en esa coordenada estelar!\n\n"
                    f"{libros_texto.strip()}"
                    f"{cierre}"
                )
        else:
            # Fallback (Sugerencia de Fantasía)
            mensaje_respuesta = (
                f"{saludo_cometa}"
                f"¡Pucha! 🚀 He explorado el sector, pero no detecté rastro de *{termino}*. 😔\n\n"
                f"Sin embargo, ¡la sección de **Fantasía** tiene tesoros increíbles esperando ser descubiertos! 🌌\n"
                f"¿Hay algún otro título que pueda rastrear para ti?"
                f"{cierre}"
            )


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
