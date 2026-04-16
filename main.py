import os
from fastapi import FastAPI, HTTPException
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
