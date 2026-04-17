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
    consultando el catálogo en Supabase, con la personalidad de "Russell".
    """
    payload = await request.json(),
    
    if payload.get("event") != "messages.upsert":
        return {"status": "ignored", "reason": "Evento no es messages.upsert"}
    
    data = payload.get("data", {})
    key = data.get("key", {})
    
    if key.get("fromMe"):
        return {"status": "ignored", "reason": "Mensaje enviado por el bot (fromMe=true)"}
        
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

    # OBLIGATORIO: Debe empezar con "Yoshi"
    if not texto_bruto.lower().startswith("yoshi"):
        return {"status": "ignored", "reason": "Mensaje no usa la wake word 'yoshi'"}

    # Limpieza "Yoshi" (primeros 5)
    texto_busqueda = texto_bruto[5:].strip()
    texto_busqueda_baja = texto_busqueda.lower()

    # Russell 
    saludo_russell = "¡Buenas! Soy Yoshi, su Guía Explorador. ¡Listo para ayudarle a rastrear tesoros literarios! 🦖🎈\n\n"
    cierre = "\n\n¡Un explorador siempre es servicial! 🐾"

    if not texto_busqueda or texto_busqueda_baja == "ayuda":
        mensaje_respuesta = (
            f"{saludo_russell}"
            f"Puede pedirme cosas así:\n"
            f"📍 Por Nombre: Yoshi [nombre del libro]\n"
            f"📍 Por Categoría: Yoshi genero [nombre del genero]\n"
            f"📍 Por Editorial: Yoshi editorial [nombre de la editorial]"
            f"{cierre}"
        )
    else:
        db = get_db()
        resultados = []
        tipo_busqueda = "nombre"
        
        # Determinar el tipo de prefijo de exploración
        if texto_busqueda_baja.startswith("genero "):
            termino = texto_busqueda[7:].strip()
            tipo_busqueda = "genero"
            if termino:
                try:
                    response = db.table('producto').select('nombre, precio, libro_detalles!inner(autor, editorial, genero, sinopsis)').ilike('libro_detalles.genero', f'%{termino}%').execute()
                    resultados = response.data
                except Exception:
                    pass
        elif texto_busqueda_baja.startswith("editorial "):
            termino = texto_busqueda[10:].strip()
            tipo_busqueda = "editorial"
            if termino:
                try:
                    response = db.table('producto').select('nombre, precio, libro_detalles!inner(autor, editorial, genero, sinopsis)').ilike('libro_detalles.editorial', f'%{termino}%').execute()
                    resultados = response.data
                except Exception:
                    pass
        else:
            termino = texto_busqueda
            tipo_busqueda = "nombre"
            if termino:
                try:
                    # Búsqueda inicial "Exacta" / frase completa
                    response = db.table('producto').select('nombre, precio').ilike('nombre', f'%{termino}%').execute()
                    resultados = response.data
                except Exception:
                    pass

        # Evaluar resultados
        if resultados:
            if tipo_busqueda == "nombre":
                libro = resultados[0]
                mensaje_respuesta = (
                    f"{saludo_russell}"
                    f"¡Rastré el rastro de su libro!\n"
                    f"📖 Libro: {libro.get('nombre')}\n"
                    f"💰 Precio: *${libro.get('precio')}*"
                    f"{cierre}"
                )
            else:
                # Género o Editorial: mostrar un pequeño catálogo (hasta 5)
                libros_texto = ""
                for lb in resultados[:5]:
                    libros_texto += f"📖 {lb.get('nombre', 'Desconocido')} - *${lb.get('precio', 0)}*\n"
                
                mensaje_respuesta = (
                    f"{saludo_russell}"
                    f"¡Pude encontrar estos tesoros en esa sección!\n\n"
                    f"{libros_texto.strip()}"
                    f"{cierre}"
                )
        else:
            # Fallback en caso de que no haya encontrado resultados exactos
            fallback_encontrado = False
            
            if tipo_busqueda == "nombre" and termino:
                # Separamos el string en palabras (para palabras razonablemente largas)
                palabras = [p for p in termino.split() if len(p) > 2]
                if palabras:
                    # Creamos la condición OR (.ilike('%word1%') or .ilike('%word2%'))
                    or_condiciones = ",".join([f"nombre.ilike.%{p}%" for p in palabras])
                    try:
                        resp_fallback = db.table('producto').select('nombre, precio').or_(or_condiciones).limit(3).execute()
                        fallback_resultados = resp_fallback.data
                        
                        if fallback_resultados:
                            fallback_encontrado = True
                            fallback_texto = ""
                            for fb in fallback_resultados:
                                fallback_texto += f"📖 {fb.get('nombre', 'Desconocido')} - *${fb.get('precio', 0)}*\n"

                            mensaje_respuesta = (
                                f"{saludo_russell}"
                                f"¡Pucha! 🏕️ No encontré exactamente ese rastro, pero encontré estos datos semejantes que podrían interesarle:\n\n"
                                f"{fallback_texto.strip()}"
                                f"{cierre}"
                            )
                    except Exception as e:
                        print("Error en fallback de Supabase:", e)
            
            if not fallback_encontrado:
                mensaje_respuesta = (
                    f"{saludo_russell}"
                    f"¡Pucha! 🏕️ He explorado el campamento, pero no pude encontrar el paradero de *{termino}* por ahora. 😔\n"
                    f"¿Hay algún otro título que pueda rastrear para usted?"
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
