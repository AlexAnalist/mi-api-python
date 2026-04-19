# 🏗️ ARQUITECTURA DEL PROYECTO

Este documento describe la esencia y propósito de cada archivo que compone este ecosistema de Chat-BOT y API.

---

## 📁 Directorio Raíz (`/`)

### 📄 [DATA.txt](file:///c:/Users/lsamu/OneDrive/Desktop/PROYECTO%20AUTO/DATA.txt)
> **El Vademécum de Credenciales**
> Contiene toda la información crítica para el despliegue y conexión: enlaces de repositorios, URLs de Supabase, API Keys de Evolution API y registros de Railway. Es la referencia técnica para configurar el entorno.

---

## 📂 Directorio API (`/mi-api-python`)

### 🐍 [main.py](file:///c:/Users/lsamu/OneDrive/Desktop/PROYECTO%20AUTO/mi-api-python/main.py)
> **El Cerebro Operativo**
> Es el núcleo lógico del proyecto. Desarrollado con **FastAPI**, cumple dos funciones principales:
> 1. **API REST**: Expone endpoints para consultar el catálogo de libros, géneros y editoriales desde Supabase.
> 2. **Motor de Chatbot**: Gestiona los webhooks de **Evolution API**. Implementa la lógica de "Yoshi" (el guía explorador), procesando mensajes de WhatsApp, buscando en la base de datos y respondiendo con una personalidad amigable.

### 📋 [requirements.txt](file:///c:/Users/lsamu/OneDrive/Desktop/PROYECTO%20AUTO/mi-api-python/requirements.txt)
> **La Lista de Suministros**
> Define todas las librerías necesarias para que el proyecto funcione: `fastapi`, `supabase`, `requests`, y `python-dotenv`. Asegura que el entorno de ejecución sea idéntico en desarrollo y producción.

### ⚙️ [Procfile](file:///c:/Users/lsamu/OneDrive/Desktop/PROYECTO%20AUTO/mi-api-python/Procfile)
> **La Hoja de Ruta de Despliegue**
> Archivo de configuración para plataformas como Railway o Heroku. Indica el comando exacto para iniciar el servidor web usando `uvicorn`.

### 📖 [README.md](file:///c:/Users/lsamu/OneDrive/Desktop/PROYECTO%20AUTO/mi-api-python/README.md)
> **El Manual de Bienvenida**
> Documento de presentación del proyecto. (Nota: Actualmente es una versión simplificada que puede ser expandida).

---

## 🛠️ Tecnologías Principales
- **Backend:** Python / FastAPI
- **Base de Datos:** Supabase (PostgreSQL)
- **Mensajería:** Evolution API (WhatsApp)
- **Despliegue:** Railway / Procfile
