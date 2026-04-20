# 🏗️ ARQUITECTURA DEL PROYECTO: COMETA, LA GATA GALÁCTICA

Este documento describe la esencia y el flujo tecnológico de **Cometa**, la gata astronauta que gestiona la Librería Mikrokosmos a través de WhatsApp.

---

## 📁 Directorio Raíz (`/`)

### 📄 [DATA.txt](file:///c:/Users/lsamu/OneDrive/Desktop/PROYECTO%20AUTO/DATA.txt)
> **El Vademécum de Credenciales**
> Contiene URLs de Supabase, API Keys de Evolution API, claves de Google Gemini y registros de Railway. Es el soporte técnico para configurar las variables de entorno.

---

## 📂 Directorio API (`/mi-api-python`)

### 🐍 [main.py](file:///c:/Users/lsamu/OneDrive/Desktop/PROYECTO%20AUTO/mi-api-python/main.py)
> **El Cerebro Cuántico**
> Desarrollado con **FastAPI**, es el motor central del proyecto. Sus funciones críticas son:
> 1. **Detección de Wake-Words**: Solo responde a mensajes que inicien estrictamente con "Cometa".
> 2. **Radar de Búsqueda de Dos Niveles**:
>    - **Escaneo Primario**: Búsqueda exacta vía `.ilike()`.
>    - **Escaneo de Respaldo**: Normalización de texto (sin acentos) para asegurar resultados resilientes.
> 3. **Integración de IA (Gemini 1.5 Flash)**: Envía los datos puros de Supabase a la IA para que esta redacte una respuesta personalizada con la identidad de Cometa.
> 4. **Filtros de Estilo Estelares**: La IA decide dinámicamente si mostrar o no las estrellas (⭐) basándose en si el comando original solicitó calificaciones.

### 📋 [requirements.txt](file:///c:/Users/lsamu/OneDrive/Desktop/PROYECTO%20AUTO/mi-api-python/requirements.txt)
> **La Lista de Suministros Galácticos**
> Define las dependencias críticas: `fastapi`, `supabase`, `google-generativeai` (IA), `requests` y `python-dotenv`.

---

## ⚙️ Flujo Operativo del Webhook

1. **Entrada**: Evolution API recibe el mensaje de WhatsApp y dispara un POST hacia la API.
2. **Validación**: `main.py` verifica la *wake-word* (Cometa). Si no está, ignora el mensaje.
3. **Consulta SQL**: El motor busca en las tablas `producto` y `libro_detalles` usando el "Radar de Acentos".
4. **Fallback Cognitivo**: Si no hay libros, el sistema trae 3 recomendaciones aleatorias de la base de datos.
5. **Procesamiento IA**: Se inyectan los datos crudos de Supabase en un *System Prompt* de Gemini, el cual asume la identidad de "Cometa" y redacta la respuesta final.
6. **Despegue**: El mensaje redactado se envía de vuelta al usuario a través de Evolution API.

---

## 🛠️ Tecnologías Principales
- **Backend:** Python / FastAPI
- **Base de Datos:** Supabase (PostgreSQL)
- **Cerebro Artificial:** Google Gemini (1.5 Flash)
- **Mensajería:** Evolution API (WhatsApp)
- **Despliegue:** Railway (Puerto dinámico 8080)
