# Arquitectura del Proyecto

## Estructura de Directorios

```
youtubedlp/
├── src/                          # Código fuente
│   ├── api/                      # Capa de API (Endpoints)
│   │   ├── __init__.py
│   │   └── routes.py             # Rutas REST de la API
│   │
│   ├── models/                   # Capa de Modelos (DTOs)
│   │   ├── __init__.py
│   │   └── schemas.py            # Esquemas Pydantic
│   │
│   ├── services/                 # Capa de Servicios (Lógica de Negocio)
│   │   ├── __init__.py
│   │   └── downloader.py         # Servicio de descarga
│   │
│   ├── static/                   # Archivos estáticos
│   │   ├── css/
│   │   │   └── styles.css        # Estilos CSS
│   │   └── js/
│   │       └── app.js            # JavaScript del cliente
│   │
│   ├── utils/                    # Utilidades
│   │   ├── __init__.py
│   │   ├── ffmpeg_finder.py      # Búsqueda de FFmpeg
│   │   └── file_utils.py         # Utilidades de archivos
│   │
│   ├── views/                    # Templates HTML
│   │   └── index.html            # Página principal
│   │
│   ├── __init__.py
│   ├── app.py                    # Aplicación FastAPI
│   ├── config.py                 # Configuración global
│   ├── main.py                   # Punto de entrada
│   └── youtubedpl.py             # [DEPRECATED] Archivo antiguo
│
├── downloads/                    # Carpeta de descargas temporales
├── requirements.txt              # Dependencias Python
├── README.md                     # Documentación principal
└── ARCHITECTURE.md               # Este archivo

```

## Capas de la Aplicación

### 1. Capa de Presentación (Views + Static)
- **views/**: Templates HTML
- **static/**: CSS y JavaScript
- **Responsabilidad**: Interfaz de usuario

### 2. Capa de API (api/)
- **routes.py**: Endpoints REST
- **Responsabilidad**: Manejo de peticiones HTTP

### 3. Capa de Modelos (models/)
- **schemas.py**: DTOs con validación Pydantic
- **Responsabilidad**: Validación y estructura de datos

### 4. Capa de Servicios (services/)
- **downloader.py**: Lógica de descarga de videos
- **Responsabilidad**: Lógica de negocio

### 5. Capa de Utilidades (utils/)
- **ffmpeg_finder.py**: Búsqueda de FFmpeg
- **file_utils.py**: Operaciones con archivos
- **Responsabilidad**: Funciones auxiliares reutilizables

### 6. Configuración (config.py)
- Configuración centralizada
- Variables de entorno
- Constantes globales

## Flujo de Datos

```
Cliente (Browser)
    ↓
[HTML/CSS/JS] (static/)
    ↓
[API Routes] (api/routes.py)
    ↓
[Validation] (models/schemas.py)
    ↓
[Business Logic] (services/downloader.py)
    ↓
[Utilities] (utils/)
    ↓
[External Service] (yt-dlp)
    ↓
[File System] (downloads/)
    ↓
[Response] → Cliente
```

## Patrones de Diseño Implementados

### 1. Separation of Concerns (SoC)
Cada capa tiene una responsabilidad única y bien definida.

### 2. Dependency Injection
Los servicios se inyectan donde se necesitan, facilitando testing.

### 3. Repository Pattern
`DownloaderService` abstrae la lógica de descarga.

### 4. DTO Pattern (Data Transfer Objects)
`DownloadRequest` valida y estructura los datos de entrada.

### 5. Service Layer Pattern
La lógica de negocio está encapsulada en servicios.

### 6. Static Files Pattern
Separación de recursos estáticos (CSS/JS) del código Python.

## Tecnologías

- **FastAPI**: Framework web moderno y rápido
- **Pydantic**: Validación de datos
- **yt-dlp**: Descarga de videos
- **Uvicorn**: Servidor ASGI
- **HTML/CSS/JS**: Frontend vanilla (sin frameworks)

## Ventajas de esta Arquitectura

1. **Mantenibilidad**: Código organizado y fácil de mantener
2. **Escalabilidad**: Fácil agregar nuevas funcionalidades
3. **Testabilidad**: Cada capa se puede testear independientemente
4. **Reutilización**: Utilidades y servicios reutilizables
5. **Separación**: Frontend y backend claramente separados
6. **Profesionalismo**: Estructura estándar de la industria
