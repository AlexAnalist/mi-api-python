import os
from fastapi import FastAPI, HTTPException
from supabase import create_client, Client
from dotenv import load_dotenv

# Cargar variables de entorno (útil para entorno local con archivo .env)
load_dotenv()

app = FastAPI(
    title="API con Supabase", 
    description="API básica usando FastAPI conectada a Supabase"
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


@app.get("/")
def read_root():
    """Endpoint básico para confirmar que la API está en línea."""
    return {"status": "ok", "message": "La API está funcionando correctamente."}


@app.get("/api/test-db")
def test_supabase_connection():
    """Endpoint para probar la lectura de datos desde Supabase."""
    if not supabase:
        raise HTTPException(
            status_code=500, 
            detail="El cliente de Supabase no está configurado. Revisa tus variables de entorno."
        )
    
    try:
        # IMPORTANTE: Reemplaza 'tu_tabla_aqui' con el nombre de una tabla real en tu base de datos
        # Limitamos el resultado a 5 registros para la prueba
        response = supabase.table('tu_tabla_aqui').select('*').limit(5).execute()
        
        return {
            "status": "success",
            "data": response.data
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error al intentar consultar Supabase: {str(e)}"
        )
