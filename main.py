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
EVO_INSTANCE_NAME = "YoshiBot"

@app.post("/webhook")
async def webhook_evolution(request: Request):
    """
    Webhook para recibir eventos de Evolution API y responder automáticamente
    consultando el catálogo en Supabase, con la personalidad "Russell".
    """
    # 1. Leer el JSON entrante
    payload = await request.json()
    
    # 2. Filtrar por el evento de mensajes que necesitamos (messages.upsert)
    if payload.get("event") != "messages.upsert":
        return {"status": "ignored", "reason": "Evento no es messages.upsert"}
    
    data = payload.get("data", {})
    key = data.get("key", {})
    
    # 3. Evitar que el bot se responda a sí mismo
    if key.get("fromMe"):
        return {"status": "ignored", "reason": "Mensaje enviado por el bot (fromMe=true)"}
        
    remote_jid = key.get("remoteJid")
    if not remote_jid:
        return {"status": "ignored", "reason": "No se encontró remoteJid"}

    # FILTRO: Evitar que el bot responda a mensajes de grupos
    if "@g.us" in remote_jid:
        return {"status": "ignored", "reason": "Mensaje proviene de un grupo (@g.us)"}

    # 4. Extraer el texto del mensaje
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
        return {"status": "ignored", "reason": "Texto vacío"}

    # WAKE WORD: Activación solo si la petición inicia con "yoshi"
    if not texto_bruto.lower().startswith("yoshi"):
        return {"status": "ignored", "reason": "Mensaje no usa la wake word 'yoshi'"}

    # 5. Limpieza: Remover "yoshi" (primeros 5 caracteres) y obtener el término real de búsqueda
    texto_busqueda = texto_bruto[5:].strip()
    texto_busqueda_baja = texto_busqueda.lower()

    # Partes estáticas del mensaje Russell
    saludo_russell = "¡Buenas! Soy Yoshi, su Guía Explorador de la Librería Mikrokosmos. ¿Le gustaría que le ayude en algo hoy? 🦖🎈\n\n"
    explicacion = "Puedo buscar precios y disponibilidad de cualquier libro en nuestra base de datos.\n\n"
    cierre = "\n\n¡Un explorador siempre es servicial! 🐾"

    # Comando de ayuda o si solo se escribe "Yoshi" sin término de búsqueda
    if not texto_busqueda or texto_busqueda_baja == "ayuda":
        mensaje_respuesta = (
            f"{saludo_russell}"
            f"Escriba: Yoshi [nombre del libro] para saber el precio.\n"
            f"Escriba: Yoshi ayuda para ver este mensaje de nuevo."
            f"{cierre}"
        )
    else:
        # 6. Realizar la búsqueda respectiva en Supabase
        db = get_db()
        try:
            # Buscamos coincidencias con ilike usando el texto recibido como comodín
            response = db.table('producto').select('nombre, precio').ilike('nombre', f'%{texto_busqueda}%').execute()
            resultados = response.data
        except Exception as e:
            print("Error en base de datos Supabase:", e)
            resultados = []

        # 7. Preparar el mensaje que vamos a responder
        if resultados:
            # Agarramos el primer resultado
            libro = resultados[0]
            nombre_libro = libro.get('nombre', 'Desconocido')
            precio_libro = libro.get('precio', 0)
            
            # Resultado Exitosa - Russell
            mensaje_respuesta = (
                f"{saludo_russell}"
                f"{explicacion}"
                f"¡Rastré el rastro de su libro!\n"
                f"📖 Libro: {nombre_libro}\n"
                f"💰 Precio: *${precio_libro}*"
                f"{cierre}"
            )
        else:
            # Producto no encontrado - Alternativa estilo explorador
            mensaje_respuesta = (
                f"{saludo_russell}"
                f"{explicacion}"
                f"⛺ ¡Pucha! He explorado el campamento, pero no pude encontrar el paradero de *{texto_busqueda}* por ahora. 😔\n"
                f"¿Hay algún otro título que pueda rastrear para usted?"
                f"{cierre}"
            )

    # 8. Enviar la respuesta a Evolution API de vuelta al chat
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
        # Usamos requests para mandar el POST de forma síncrona
        respuesta_evo = requests.post(send_url, headers=headers, json=body)
        respuesta_evo.raise_for_status() # Lanza excepción si el estatus HTTP es error
    except Exception as e:
        print("Error al enviar mensaje por Evolution API:", e)
        return {"status": "error", "detail": str(e)}

    return {"status": "ok", "message": "Respuesta al usuario enviada correctamente"}
