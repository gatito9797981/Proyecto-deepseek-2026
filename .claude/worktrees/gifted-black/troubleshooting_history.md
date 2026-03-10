# Historial de Errores y Correcciones

Este documento detalla los problemas técnicos encontrados durante el desarrollo y cómo han sido resueltos.

## 🛠️ Errores Corregidos

### 1. Error de coordenadas "Move Target Out of Bounds"
- **Problema**: El driver intentaba mover el ratón a coordenadas absolutas de la página que excedían las dimensiones de la ventana visible (viewport), causando un error crítico de Selenium.
- **Solución**: Se implementó el uso de `location_once_scrolled_into_view` para obtener coordenadas relativas al viewport y se añadió un modo de "clic rápido" que salta directamente al elemento con jitter aleatorio.

### 2. Elementos Obsoletos (StaleElementReferenceException)
- **Problema**: El botón de envío de DeepSeek cambiaba su estado en memoria justo cuando el driver intentaba interactuar con él tras la escritura.
- **Solución**: Se añadió una lógica de "re-búsqueda" automática. Si el elemento falla por ser obsoleto, el cliente lo busca nuevamente en el DOM y reintenta la acción en milisegundos.

### 3. Error de Clave "loading_indicator"
- **Problema**: El código intentaba acceder a un selector llamado `loading_indicator` que no existía en el diccionario de selectores (el nombre correcto era `generating_indicator`).
- **Solución**: Unificación de nombres de selectores y adición de bloques `try-except` para que la detección de respuesta sea resiliente a pequeños cambios en la UI.

### 4. Inyección de userToken en LocalStorage
- **Problema**: DeepSeek rechazaba los tokens inyectados como texto plano; ahora requiere un objeto JSON stringificado con metadatos de versión.
- **Solución**: Se actualizó el script de inyección para enviar el token en el formato exacto: `{"value": "TOKEN", "__version__": "0"}`.

### 5. Cierre Prematuro del Driver (excludeSwitches)
- **Problema**: `undetected-chromedriver` lanzaba excepciones en Windows al intentar procesar `excludeSwitches` de forma estándar.
- **Solución**: Se depuró la configuración de opciones para asegurar la compatibilidad con el parche automático del driver en Windows.

## ⏳ Pendiente de Mejora

- **Automatización de Sesión**: La extracción de tokens sigue siendo un proceso manual iniciado por herramientas externas.
- **Detección de Cloudflare**: Aunque el bypass actual funciona, un cambio agresivo en las reglas de WAF podría requerir una actualización del motor de fingerprinting.
- **Memoria**: Optimizar el consumo de RAM del pool de drivers cuando se ejecutan más de 3 instancias en paralelo.
