# DeepSeek Client

Un cliente no oficial para DeepSeek (chat.deepseek.com) con capacidades avanzadas de anti-detección, diseñado para funcionar en Windows.

## 🚀 Características

### Anti-detección Avanzada
- **WebDriver Spoofing**: Elimina todas las huellas de automatización
- **Canvas Fingerprint**: Ruido determinista con semilla configurable
- **WebGL Spoofing**: Vendor y renderer personalizados
- **AudioContext Noise**: Inyección de ruido en buffers de audio
- **Navigator Spoofing**: Propiedades del navegador falsificadas
- **Screen Spoofing**: Resolución y propiedades de pantalla
- **WebRTC Leak Prevention**: Prevención de fugas WebRTC
- **Font Fingerprint Variation**: Variación en medidas de fuentes
- **Permissions API Spoofing**: Permisos falsificados
- **Performance Timing Jitter**: Variación en timing de rendimiento

### 🛠️ Interfaz de Usuario de Combate
- **Lanzador Unificado (`conectar_directo.bat`)**: Menú principal con selección numérica para arrancar el chat o escáner.
- **Modo Toggle Rápido**: Activa/Desactiva DeepThink y Búsqueda directamente desde el menú del BAT o dentro del chat.
- **Menú Numérico en Tiempo Real**: Durante el chat, usa [1] para DeepThink, [2] para Search, [3] para Historial y [4] para Nuevo Chat.
- **Blindaje de Botones**: Identificación precisa de botones (Enviar vs Adjuntar) mediante análisis dinámico de clases mutantes.

### Perfiles de Hardware
Perfiles predefinidos para simular diferentes dispositivos:
- `gaming_pc` - PC de gaming de alta gama con RTX 4090
- `gaming_pc_amd` - PC de gaming con AMD Radeon
- `work_laptop` - Laptop corporativo estándar
- `work_laptop_high` - Laptop de trabajo de alta gama
- `macbook` - MacBook Pro con Apple Silicon
- `macbook_air` - MacBook Air M2
- `linux_dev` - Estación de desarrollo Linux
- `linux_dev_nvidia` - Linux con GPU NVIDIA
- `budget_pc` - PC de gama media/baja
- `surface_pro` - Microsoft Surface Pro
- `chromebook` - Chromebook típico
- `asian_workstation` - Workstation para mercado asiático
- `european_laptop` - Laptop para mercado europeo

### Comportamiento Humano Simulado
- **Movimiento de ratón**: Curvas de Bézier con aceleración/deceleración
- **Escritura realista**: Distribución normal de tiempos, pausas en puntuación, errores ocasionales
- **Scroll natural**: Velocidad variable con easing
- **Pausas aleatorias**: Entre acciones para simular comportamiento humano

### Funcionalidades Adicionales
- **Driver Pool**: Soporte para múltiples instancias en paralelo
- **Historial de conversaciones**: Persistencia y búsqueda
- **API OpenAI Compatible**: Servidor HTTP para integración
- **Interfaz interactiva**: Terminal con Rich

## 📦 Instalación

### Requisitos previos
- Python 3.9 o superior
- Google Chrome instalado
- ChromeDriver (se instala automáticamente con undetected-chromedriver)

### Instalación rápida

```bash
cd deepseek-client
pip install -r requirements.txt
```

### Instalación con pip

```bash
pip install -e .
```

## 🔧 Configuración

### Variables de entorno

Crea un archivo `.env` en el directorio del proyecto:

```env
# Nivel de anti-detección: basic, standard, full
ANTI_DETECTION_LEVEL=full

# Perfil de fingerprint: random o nombre de perfil específico
FINGERPRINT_PROFILE=random

# Tamaño del pool de drivers
DRIVER_POOL_SIZE=1

# URL de DeepSeek
DEEPSEEK_URL=https://chat.deepseek.com

# Modo headless (sin interfaz gráfica)
HEADLESS=false

# Usar Xvfb en Linux
USE_XVFB=false

# Nivel de logging
LOG_LEVEL=INFO
```

## 📖 Uso

### Lanzador Principal (Recomendado)

Simplemente ejecuta el archivo `.bat` en la raíz del proyecto:
```bash
conectar_directo.bat
```
Esto abrirá un menú interactivo donde podrás configurar los modos (Think/Search) y lanzar el chat.

### Chat Interactivo vía Terminal

```bash
# Con modos pre-activados desde CLI
python app/interactive_chat.py --think --search

# Con perfil específico
python app/interactive_chat.py --profile gaming_pc
```

### Como librería

```python
from deepseek_client import DeepSeekClient

# Uso básico
with DeepSeekClient() as client:
    response = client.ask("¿Cuál es la capital de Francia?")
    print(response.content)

# Con perfil específico
from deepseek_client import create_client

client = create_client(profile_name="macbook")
response = client.ask("Explícame la teoría de la relatividad")
print(response.content)

# Streaming
for chunk in client.ask_stream("Cuéntame una historia"):
    print(chunk, end="", flush=True)

# Historial
messages = client.get_conversation_history()
client.save_conversation("Mi conversación")
```

### Servidor API OpenAI Compatible

```bash
# Iniciar servidor
python app/server.py --port 8000 --pool-size 2

# Ver opciones
python app/server.py --help
```

Luego usa con cualquier cliente OpenAI:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy"  # No se necesita API key real
)

# Completions
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "user", "content": "Hola, ¿cómo estás?"}
    ]
)
print(response.choices[0].message.content)

# Streaming
stream = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "Escribe un poema"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### Usando curl

```bash
# Completions
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hola"}]
  }'

# Listar modelos
curl http://localhost:8000/v1/models
```

## 📁 Estructura del Proyecto

```
deepseek-client/
├── app/                  # Puntos de entrada de la aplicación
│   ├── interactive_chat.py # Terminal interactiva (Rich)
│   └── server.py           # Servidor API OpenAI compatible
├── deepseek_client/      # Núcleo del motor
│   ├── resources/        # Scripts JS internos (spy_mode.js)
│   ├── config.py         # Configuración y variables de entorno
│   ├── fingerprint.py    # Generador de fingerprints
│   ├── driver.py         # WebDriver anti-detección (High-Speed support)
│   ├── client.py         # Lógica principal de DeepSeek
│   └── ...               # Otros módulos internos
├── tools/                # Herramientas de diagnóstico y extracción
│   ├── smoke_test.py     # Prueba de estabilidad
│   ├── extract_data.py   # Captura de tráfico SSE/JSON
│   └── ...               # Scripts auxiliares
├── .env                  # Configuración de sesión y tokens
├── conectar_directo.bat  # Lanzador rápido para Windows
└── requirements.txt      # Dependencias
```

## 🎯 Comandos del Chat Interactivo

| Comando / Tecla | Descripción |
|---------|-------------|
| `[1]` o `/think` | Activar/Desactivar modo DeepThink (R1) |
| `[2]` o `/search` | Activar/Desactivar búsqueda en la web |
| `[3]` o `/historial`| Ver y seleccionar conversaciones anteriores |
| `[4]` o `/nuevo` | Iniciar nueva conversación limpando la UI |
| `/limpiar` | Limpiar la pantalla de la terminal |
| `/perfil` | Mostrar perfil de hardware actual |
| `/stats` | Ver estadísticas de uso |
| `/salir` | Salir del programa |

## ⚙️ Niveles de Anti-detección

### Basic
- WebDriver spoofing básico
- Navigator properties spoofing

### Standard
- Todo lo de Basic
- Canvas fingerprint spoofing
- WebGL spoofing
- Screen spoofing

### Full (recomendado)
- Todas las técnicas de anti-detección
- AudioContext noise
- WebRTC leak prevention
- Font fingerprint variation
- Permissions API spoofing
- Performance timing jitter
- Timezone spoofing

## 🔒 Consideraciones de Seguridad

- Este proyecto es para uso educativo y de investigación
- Respeta los términos de servicio de DeepSeek
- No uses para automatización maliciosa o spam
- El proyecto no almacena credenciales

## 🐛 Solución de Problemas

### Chrome no encontrado
Asegúrate de tener Google Chrome instalado en la ubicación estándar.

### Error de ChromeDriver
El driver se descarga automáticamente. Si hay problemas:
```bash
pip install --upgrade undetected-chromedriver
```

### Rate Limiting
Si encuentras rate limits, aumenta los delays:
```python
config = Config(
    typing_speed_mean=100,  # Más lento
    retry_delay=10.0  # Más tiempo entre reintentos
)
```

## ⚠️ Limitaciones Actuales

- **Sesión Manual**: Requiere la extracción periódica del `userToken` y cookies de AWS WAF mediante el extractor de herramientas.
- **Headless Mode**: Aunque está soportado, es más propenso a ser desafiado por Cloudflare/AWS WAF en entornos de alta protección.
- **Recursos**: El uso de múltiples drivers en el pool consume memoria RAM significativa (~800MB por instancia).
- **Interacción Humana**: La alta velocidad de envío (clic rápido) es segura, pero movimientos excesivamente robóticos en ráfagas largas podrían disparar alertas preventivas.

## 📄 Licencia

MIT License - Ver archivo LICENSE para más detalles.

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:
1. Haz fork del repositorio
2. Crea una rama para tu feature
3. Envía un pull request

## 📝 Changelog

### v1.1.0 (Marzo 2026)
- **Corrección Crítica de Selectores**: Separación absoluta entre botones de `Enviar` y `Adjuntar` mediante análisis de estado mutante.
- **Menú Maestro BAT**: Implementación de lanzador numérico de estados en `conectar_directo.bat`.
- **Modos Interactivos**: Soporte para cambio de modos vía teclado (1, 2, 3, 4) dentro del bucle de chat.
- **Cierre de Modales**: Implementación de lógica de escape (`Keys.ESCAPE`) para desbloquear la interfaz cuando se abren popups de adjuntos.

### v1.0.0
- Versión inicial con Anti-detección avanzada.

---

**Nota**: Este proyecto no está afiliado con DeepSeek. Es un proyecto independiente creado con fines educativos.
