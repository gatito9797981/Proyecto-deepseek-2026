# Plan Futuro y Hoja de Ruta (Roadmap)

Este documento esboza las mejoras sugeridas para las próximas versiones del DeepSeek Client.

## ⚡ Rendimiento y Eficiencia

### 1. Gestión de Caché de Navegador
- Implementar un sistema de limpieza automática de `Service Workers` y caché de telemetría para evitar que la carpeta `browser_profiles` crezca indefinidamente.
- Optimizar la carga de la página bloqueando recursos innecesarios (imágenes pesadas, trackers de terceros) mediante el driver.

### 2. Multi-threading nativo en el Driver Pool
- Refinar el `DriverPool` para permitir una sincronización más fina de los estados de los drivers, reduciendo el overhead de CPU al inicializar instancias masivas.

## 🛡️ Robustez y Anti-detección

### 1. Refresco Automático de Sesión (Auto-Auth)
- Implementar un servicio en segundo plano que detecte cuando el `userToken` está por expirar y lo refresque automáticamente si es posible, o que notifique al usuario mediante una alerta UI.

### 2. Trayectorias de Ratón basadas en IA
- Reemplazar el generador de Bezier por un modelo entrenado en movimientos humanos reales para superar los algoritmos de detección de comportamiento (Behavioral Biometrics) más avanzados.

## 🚀 Expansión de Funcionalidades

### 1. Soporte Multimedia
- Añadir capacidad para subir archivos y documentos directamente desde el cliente (simulación de Drag & Drop y file selector).
- Integración de síntesis de voz (TTS) para lectura de respuestas en el chat interactivo.

### 2. Integraciones de Mensajería
- Crear puentes (bridges) oficiales para:
  - **Telegram Bot**: Controlar la instancia de DeepSeek desde Telegram.
  - **Discord Bot**: Integrar la IA en canales de Discord.
  - **Webhook Support**: Notificaciones automáticas cuando la IA termine de procesar tareas largas.

## 📊 Analítica y Control
- Añadir un panel (Dashboard) web local sencillo para monitorizar el estado de los drivers del pool, el consumo de tokens y el historial de capturas de pantalla de forma visual.
