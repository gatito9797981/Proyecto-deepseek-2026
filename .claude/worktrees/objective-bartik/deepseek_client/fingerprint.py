"""
Módulo de fingerprinting para anti-detección avanzada.

Este módulo genera scripts de JavaScript que se inyectan en el navegador
para falsificar las huellas digitales del dispositivo, evitando la detección
de automatización.

Técnicas implementadas:
    - WebDriver spoofing
    - Canvas fingerprint con ruido determinista
    - WebGL vendor/renderer falsos
    - AudioContext noise injection
    - Navigator properties spoofing
    - Screen resolution spoofing
    - WebRTC leak prevention
    - Font fingerprint variation
    - Permissions API spoofing
    - Performance timing jitter
"""

import random
import hashlib
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class FingerprintConfig:
    """
    Configuración de fingerprint para un perfil específico.
    
    Attributes:
        seed: Semilla para generar ruido determinista.
        webgl_vendor: Vendor de WebGL falsificado.
        webgl_renderer: Renderer de WebGL falsificado.
        hardware_concurrency: Número de núcleos de CPU.
        device_memory: Memoria del dispositivo en GB.
        platform: Plataforma del sistema.
        user_agent: User agent string.
        screen_width: Ancho de pantalla.
        screen_height: Alto de pantalla.
        color_depth: Profundidad de color.
        timezone: Zona horaria.
        languages: Lista de idiomas.
        plugins: Lista de plugins falsos.
    """
    seed: int
    webgl_vendor: str
    webgl_renderer: str
    hardware_concurrency: int
    device_memory: int
    platform: str
    user_agent: str
    screen_width: int
    screen_height: int
    color_depth: int = 24
    timezone: str = "America/New_York"
    languages: list = None
    plugins: list = None
    
    def __post_init__(self):
        if self.languages is None:
            self.languages = ["en-US", "en"]
        if self.plugins is None:
            self.plugins = [
                {"name": "Chrome PDF Plugin", "filename": "internal-pdf-viewer"},
                {"name": "Chrome PDF Viewer", "filename": "mhjfbmdgcfjbbpaeojofohoefgiehjai"},
                {"name": "Native Client", "filename": "internal-nacl-plugin"},
            ]


class FingerprintGenerator:
    """
    Generador de scripts de fingerprinting para anti-detección.
    
    Esta clase genera código JavaScript que se inyecta en el navegador
    para falsificar varias APIs y propiedades del dispositivo.
    """
    
    def __init__(self, config: FingerprintConfig, level: str = "full"):
        """
        Inicializa el generador de fingerprinting.
        
        Args:
            config: Configuración del fingerprint.
            level: Nivel de anti-detección (basic, standard, full).
        """
        self.config = config
        self.level = level
        self._rng = random.Random(config.seed)
    
    def _noise_value(self, base: float, variance: float = 0.1) -> float:
        """Genera un valor con ruido determinista basado en la semilla."""
        noise = self._rng.uniform(-variance, variance)
        return base + (base * noise)
    
    def generate_webdriver_script(self) -> str:
        """
        Genera script para falsificar la propiedad navigator.webdriver.
        
        Returns:
            str: Script JavaScript para inyección.
        """
        return """
        // WebDriver Spoofing - Nivel máximo de ocultamiento
        (function() {
            'use strict';
            try {
                // Eliminar propiedad webdriver completamente
                delete Object.getPrototypeOf(navigator).webdriver;
                
                // Redefinir como undefined (no false, que es sospechoso)
                Object.defineProperty(navigator, 'webdriver', {
                    get: function() { return undefined; },
                    configurable: true,
                    enumerable: true
                });
                
                // Eliminar $cdc_ y $wdc_ variables usadas por ChromeDriver
                delete window.$cdc_asdjflasutopfhvcZLmcfl_;
                delete window.$cdc_;
                delete window.$wdc_;
                
                // Eliminar __webdriver_script_fn
                delete document.__webdriver_script_fn;
                delete document.$cdc_asdjflasutopfhvcZLmcfl_;
                
                // Ocultar __selenium_evaluate, __selenium_unwrapped
                delete document.__selenium_evaluate;
                delete document.__selenium_unwrapped;
                delete document.__webdriver_evaluate;
                delete document.__webdriver_unwrapped;
                delete document.__fxdriver_evaluate;
                delete document.__fxdriver_unwrapped;
                
                // Eliminar __lastEvaluateTime
                delete document.__lastEvaluateTime;
                
                // Limpiar funciones de Selenium - Desactivado por inestabilidad
                
                console.log('[Anti-Detection] WebDriver spoofing aplicado');
            } catch (e) {
                console.error('[Anti-Detection] Error en WebDriver spoofing:', e);
            }
        })();
        """
    
    def generate_canvas_script(self) -> str:
        """
        Genera script para añadir ruido al canvas fingerprint.
        
        El ruido es determinista basado en la semilla, por lo que
        siempre genera el mismo fingerprint para un mismo seed.
        
        Returns:
            str: Script JavaScript para inyección.
        """
        seed = self.config.seed
        return f"""
        // Canvas Fingerprint Spoofing con ruido determinista
        (function() {{
            'use strict';
            try {{
                const SEED = {seed};
                
                // Generador de números pseudo-aleatorios determinista
                function seededRandom(seed) {{
                    const x = Math.sin(seed) * 10000;
                    return x - Math.floor(x);
                }}
                
                // Función para añadir ruido sutil a los datos de imagen
                function addNoiseToImageData(imageData) {{
                    const data = imageData.data;
                    let noiseSeed = SEED;
                    
                    for (let i = 0; i < data.length; i += 4) {{
                        // Añadir ruido de ±1 a cada canal RGB (no alpha)
                        noiseSeed += 1;
                        const noise = Math.floor(seededRandom(noiseSeed) * 3) - 1;
                        data[i] = Math.max(0, Math.min(255, data[i] + noise));     // R
                        data[i + 1] = Math.max(0, Math.min(255, data[i + 1] + noise)); // G
                        data[i + 2] = Math.max(0, Math.min(255, data[i + 2] + noise)); // B
                        // Alpha (data[i + 3]) sin modificar
                    }}
                    return imageData;
                }}
                
                // Override toDataURL
                const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function(type) {{
                    try {{
                        // Solo añadir ruido a canvas pequeños (fingerprinting)
                        if (this.width <= 280 && this.height <= 60) {{
                            const ctx = this.getContext('2d');
                            if (ctx) {{
                                const imageData = ctx.getImageData(0, 0, this.width, this.height);
                                const noisyData = addNoiseToImageData(imageData);
                                ctx.putImageData(noisyData, 0, 0);
                            }}
                        }}
                    }} catch (e) {{
                        // Canvas tainted o contexto no disponible
                    }}
                    return originalToDataURL.apply(this, arguments);
                }};
                
                // Override toBlob
                const originalToBlob = HTMLCanvasElement.prototype.toBlob;
                HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {{
                    try {{
                        if (this.width <= 280 && this.height <= 60) {{
                            const ctx = this.getContext('2d');
                            if (ctx) {{
                                const imageData = ctx.getImageData(0, 0, this.width, this.height);
                                const noisyData = addNoiseToImageData(imageData);
                                ctx.putImageData(noisyData, 0, 0);
                            }}
                        }}
                    }} catch (e) {{}}
                    return originalToBlob.apply(this, arguments);
                }};
                
                // Override getImageData
                const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
                CanvasRenderingContext2D.prototype.getImageData = function(sx, sy, sw, sh) {{
                    const imageData = originalGetImageData.apply(this, arguments);
                    
                    // Solo añadir ruido a canvas pequeños
                    if (sw <= 280 && sh <= 60) {{
                        return addNoiseToImageData(imageData);
                    }}
                    return imageData;
                }};
                
                console.log('[Anti-Detection] Canvas fingerprint spoofing aplicado');
            }} catch (e) {{
                console.error('[Anti-Detection] Error en Canvas spoofing:', e);
            }}
        }})();
        """
    
    def generate_webgl_script(self) -> str:
        """
        Genera script para falsificar información de WebGL.
        
        Returns:
            str: Script JavaScript para inyección.
        """
        vendor = self.config.webgl_vendor
        renderer = self.config.webgl_renderer
        
        return f"""
        // WebGL Fingerprint Spoofing
        (function() {{
            'use strict';
            try {{
                const FAKE_VENDOR = '{vendor}';
                const FAKE_RENDERER = '{renderer}';
                
                // Función para obtener contexto WebGL original
                function getOriginalGetContext() {{
                    return HTMLCanvasElement.prototype.getContext;
                }}
                
                // Override getContext para interceptar WebGL
                const originalGetContext = HTMLCanvasElement.prototype.getContext;
                HTMLCanvasElement.prototype.getContext = function(type, attributes) {{
                    const context = originalGetContext.call(this, type, attributes);
                    
                    if (context && (type === 'webgl' || type === 'webgl2' || type === 'experimental-webgl')) {{
                        // Override getParameter
                        const originalGetParameter = context.getParameter.bind(context);
                        context.getParameter = function(parameter) {{
                            // UNMASKED_VENDOR_WEBGL
                            if (parameter === 0x9245 || parameter === 37445) {{
                                return FAKE_VENDOR;
                            }}
                            // UNMASKED_RENDERER_WEBGL
                            if (parameter === 0x9246 || parameter === 37446) {{
                                return FAKE_RENDERER;
                            }}
                            // VERSION
                            if (parameter === 0x1F02) {{
                                return 'WebGL 1.0 (OpenGL ES 2.0 Chromium)';
                            }}
                            // SHADING_LANGUAGE_VERSION
                            if (parameter === 0x8B8C) {{
                                return 'WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)';
                            }}
                            // VENDOR
                            if (parameter === 0x1F00) {{
                                return 'Google Inc. (NVIDIA)';
                            }}
                            return originalGetParameter(parameter);
                        }};
                        
                        // Override getExtension para no exponer extensiones sospechosas
                        const originalGetExtension = context.getExtension.bind(context);
                        context.getExtension = function(name) {{
                            // Bloquear extensiones que podrían revelar información
                            if (name === 'WEBGL_debug_renderer_info') {{
                                return {{
                                    UNMASKED_VENDOR_WEBGL: 0x9245,
                                    UNMASKED_RENDERER_WEBGL: 0x9246
                                }};
                            }}
                            return originalGetExtension(name);
                        }};
                        
                        // Override getSupportedExtensions
                        const originalGetSupportedExtensions = context.getSupportedExtensions.bind(context);
                        context.getSupportedExtensions = function() {{
                            const extensions = originalGetSupportedExtensions() || [];
                            // Filtrar extensiones que podrían ser usadas para fingerprinting
                            return extensions.filter(ext => !ext.includes('debug'));
                        }};
                    }}
                    
                    return context;
                }};
                
                console.log('[Anti-Detection] WebGL spoofing aplicado');
            }} catch (e) {{
                console.error('[Anti-Detection] Error en WebGL spoofing:', e);
            }}
        }})();
        """
    
    def generate_audio_script(self) -> str:
        """
        Genera script para añadir ruido al AudioContext fingerprint.
        
        Returns:
            str: Script JavaScript para inyección.
        """
        seed = self.config.seed
        return f"""
        // AudioContext Fingerprint Spoofing
        (function() {{
            'use strict';
            try {{
                const SEED = {seed};
                
                function seededRandom(seed) {{
                    const x = Math.sin(seed) * 10000;
                    return x - Math.floor(x);
                }}
                
                // Override AudioContext
                const OriginalAudioContext = window.AudioContext || window.webkitAudioContext;
                if (OriginalAudioContext) {{
                    const NewAudioContext = function(contextOptions) {{
                        const ctx = new OriginalAudioContext(contextOptions);
                        
                        // Override createOscillator
                        const originalCreateOscillator = ctx.createOscillator.bind(ctx);
                        ctx.createOscillator = function() {{
                            const oscillator = originalCreateOscillator();
                            // Añadir pequeña variación en la frecuencia
                            const originalFrequency = oscillator.frequency;
                            const originalSetValueAtTime = originalFrequency.setValueAtTime.bind(originalFrequency);
                            originalFrequency.setValueAtTime = function(value, startTime) {{
                                const noise = seededRandom(SEED + startTime * 1000) * 0.0001 - 0.00005;
                                return originalSetValueAtTime(value * (1 + noise), startTime);
                            }};
                            return oscillator;
                        }};
                        
                        // Override createDynamicsCompressor
                        const originalCreateDynamicsCompressor = ctx.createDynamicsCompressor.bind(ctx);
                        ctx.createDynamicsCompressor = function() {{
                            const compressor = originalCreateDynamicsCompressor();
                            // Añadir pequeña variación en los parámetros
                            const noise = seededRandom(SEED);
                            compressor.threshold.value += noise * 0.1;
                            compressor.knee.value += noise * 0.1;
                            compressor.ratio.value += noise * 0.01;
                            return compressor;
                        }};
                        
                        // Override createAnalyser
                        const originalCreateAnalyser = ctx.createAnalyser.bind(ctx);
                        ctx.createAnalyser = function() {{
                            const analyser = originalCreateAnalyser();
                            const originalGetFloatFrequencyData = analyser.getFloatFrequencyData.bind(analyser);
                            analyser.getFloatFrequencyData = function(array) {{
                                originalGetFloatFrequencyData(array);
                                // Añadir ruido sutil a los datos
                                for (let i = 0; i < array.length; i++) {{
                                    array[i] += seededRandom(SEED + i) * 0.001 - 0.0005;
                                }}
                            }};
                            return analyser;
                        }};
                        
                        return ctx;
                    }};
                    
                    // Copiar prototipo y propiedades estáticas
                    NewAudioContext.prototype = OriginalAudioContext.prototype;
                    Object.setPrototypeOf(NewAudioContext, OriginalAudioContext);
                    
                    // Reemplazar en window
                    if (window.AudioContext) window.AudioContext = NewAudioContext;
                    if (window.webkitAudioContext) window.webkitAudioContext = NewAudioContext;
                }}
                
                // Override OfflineAudioContext
                if (window.OfflineAudioContext) {{
                    const OriginalOfflineAudioContext = window.OfflineAudioContext;
                    const NewOfflineAudioContext = function(numberOfChannels, length, sampleRate) {{
                        const ctx = new OriginalOfflineAudioContext(numberOfChannels, length, sampleRate);
                        
                        // Override startRendering
                        const originalStartRendering = ctx.startRendering.bind(ctx);
                        ctx.startRendering = function() {{
                            const promise = originalStartRendering();
                            return promise.then(buffer => {{
                                // Añadir ruido sutil al buffer
                                for (let channel = 0; channel < buffer.numberOfChannels; channel++) {{
                                    const data = buffer.getChannelData(channel);
                                    for (let i = 0; i < data.length; i++) {{
                                        data[i] += seededRandom(SEED + i + channel * 10000) * 0.00001 - 0.000005;
                                    }}
                                }}
                                return buffer;
                            }});
                        }};
                        
                        return ctx;
                    }};
                    
                    NewOfflineAudioContext.prototype = OriginalOfflineAudioContext.prototype;
                    window.OfflineAudioContext = NewOfflineAudioContext;
                }}
                
                console.log('[Anti-Detection] AudioContext spoofing aplicado');
            }} catch (e) {{
                console.error('[Anti-Detection] Error en Audio spoofing:', e);
            }}
        }})();
        """
    
    def generate_navigator_script(self) -> str:
        """
        Genera script para falsificar propiedades del navigator.
        
        Returns:
            str: Script JavaScript para inyección.
        """
        return f"""
        // Navigator Properties Spoofing
        (function() {{
            'use strict';
            try {{
                const navigatorProps = {{
                    hardwareConcurrency: {self.config.hardware_concurrency},
                    deviceMemory: {self.config.device_memory},
                    platform: '{self.config.platform}',
                    vendor: 'Google Inc.',
                    vendorSub: '',
                    productSub: '20030107',
                    cookieEnabled: true,
                    doNotTrack: null,
                    maxTouchPoints: 0,
                    appCodeName: 'Mozilla',
                    appName: 'Netscape',
                    appVersion: '{self.config.user_agent.split("Mozilla/")[1] if "Mozilla/" in self.config.user_agent else "5.0"}',
                    oscpu: undefined,
                    buildID: undefined,
                    product: 'Gecko',
                    pdfViewerEnabled: true,
                    languages: {json.dumps(self.config.languages)},
                    language: '{self.config.languages[0] if self.config.languages else "en-US"}',
                    onLine: true
                }};
                
                // Aplicar cada propiedad
                for (const [prop, value] of Object.entries(navigatorProps)) {{
                    try {{
                        Object.defineProperty(navigator, prop, {{
                            get: function() {{ return value; }},
                            configurable: true,
                            enumerable: true
                        }});
                    }} catch (e) {{
                        // Algunas propiedades pueden no ser configurables
                    }}
                }}
                
                // Override plugins
                const pluginsArray = {json.dumps(self.config.plugins)};
                const pluginArray = {{
                    length: pluginsArray.length,
                    item: function(index) {{
                        return this[index] || null;
                    }},
                    namedItem: function(name) {{
                        for (let i = 0; i < this.length; i++) {{
                            if (this[i].name === name) return this[i];
                        }}
                        return null;
                    }},
                    refresh: function() {{}},
                    ...Object.fromEntries(pluginsArray.map((p, i) => [i, {{
                        name: p.name,
                        filename: p.filename,
                        description: p.name,
                        length: 1,
                        item: function() {{ return {{}}; }},
                        namedItem: function() {{ return {{}}; }}
                    }}]))
                }};
                
                Object.defineProperty(navigator, 'plugins', {{
                    get: function() {{ return pluginArray; }},
                    configurable: true,
                    enumerable: true
                }});
                
                // Override mimeTypes
                const mimeTypes = {{
                    'application/pdf': {{
                        description: 'Portable Document Format',
                        suffixes: 'pdf',
                        type: 'application/pdf',
                        enabledPlugin: pluginArray[0]
                    }},
                    'application/x-google-chrome-pdf': {{
                        description: 'Portable Document Format',
                        suffixes: 'pdf',
                        type: 'application/x-google-chrome-pdf',
                        enabledPlugin: pluginArray[0]
                    }}
                }};
                
                Object.defineProperty(navigator, 'mimeTypes', {{
                    get: function() {{
                        return {{
                            length: Object.keys(mimeTypes).length,
                            item: function(index) {{
                                return Object.values(mimeTypes)[index] || null;
                            }},
                            namedItem: function(name) {{
                                return mimeTypes[name] || null;
                            }},
                            ...mimeTypes
                        }};
                    }},
                    configurable: true,
                    enumerable: true
                }});
                
                // Override getBattery
                if (navigator.getBattery) {{
                    Object.defineProperty(navigator, 'getBattery', {{
                        value: function() {{
                            return Promise.resolve({{
                                charging: true,
                                chargingTime: 0,
                                dischargingTime: Infinity,
                                level: 1.0,
                                onchargingchange: null,
                                onchargingtimechange: null,
                                ondischargingtimechange: null,
                                onlevelchange: null
                            }});
                        }},
                        configurable: true,
                        writable: true
                    }});
                }}
                
                // Override getConnection
                if (navigator.connection) {{
                    Object.defineProperty(navigator.connection, 'rtt', {{
                        get: function() {{ return 50 + Math.floor(Math.random() * 50); }},
                        configurable: true
                    }});
                }}
                
                console.log('[Anti-Detection] Navigator spoofing aplicado');
            }} catch (e) {{
                console.error('[Anti-Detection] Error en Navigator spoofing:', e);
            }}
        }})();
        """
    
    def generate_screen_script(self) -> str:
        """
        Genera script para falsificar información de pantalla.
        
        Returns:
            str: Script JavaScript para inyección.
        """
        return f"""
        // Screen Properties Spoofing
        (function() {{
            'use strict';
            try {{
                const screenProps = {{
                    width: {self.config.screen_width},
                    height: {self.config.screen_height},
                    availWidth: {self.config.screen_width},
                    availHeight: {self.config.screen_height} - 40,  // Taskbar
                    colorDepth: {self.config.color_depth},
                    pixelDepth: {self.config.color_depth},
                    top: 0,
                    left: 0,
                    availTop: 0,
                    availLeft: 0,
                    orientation: {{
                        type: 'landscape-primary',
                        angle: 0,
                        onchange: null
                    }},
                    devicePixelRatio: 1
                }};
                
                // Aplicar a screen
                for (const [prop, value] of Object.entries(screenProps)) {{
                    if (prop === 'orientation' || prop === 'devicePixelRatio') continue;
                    try {{
                        Object.defineProperty(screen, prop, {{
                            get: function() {{ return value; }},
                            configurable: true,
                            enumerable: true
                        }});
                    }} catch (e) {{}}
                }}
                
                // Override orientation
                try {{
                    Object.defineProperty(screen, 'orientation', {{
                        get: function() {{
                            return {{
                                type: 'landscape-primary',
                                angle: 0,
                                onchange: null,
                                addEventListener: function() {{}},
                                removeEventListener: function() {{}},
                                dispatchEvent: function() {{ return true; }}
                            }};
                        }},
                        configurable: true
                    }});
                }} catch (e) {{}}
                
                // Override window.devicePixelRatio
                Object.defineProperty(window, 'devicePixelRatio', {{
                    get: function() {{ return 1; }},
                    configurable: true
                }});
                
                // Override outerWidth/outerHeight
                Object.defineProperty(window, 'outerWidth', {{
                    get: function() {{ return {self.config.screen_width}; }},
                    configurable: true
                }});
                Object.defineProperty(window, 'outerHeight', {{
                    get: function() {{ return {self.config.screen_height} - 40; }},
                    configurable: true
                }});
                
                console.log('[Anti-Detection] Screen spoofing aplicado');
            }} catch (e) {{
                console.error('[Anti-Detection] Error en Screen spoofing:', e);
            }}
        }})();
        """
    
    def generate_webrtc_script(self) -> str:
        """
        Genera script para prevenir WebRTC leaks.
        
        Returns:
            str: Script JavaScript para inyección.
        """
        return """
        // WebRTC Leak Prevention
        (function() {
            'use strict';
            try {
                // Override RTCPeerConnection
                if (window.RTCPeerConnection) {
                    const OriginalRTCPeerConnection = window.RTCPeerConnection;
                    
                    window.RTCPeerConnection = function(configuration, constraints) {
                        // Filtrar servidores STUN/TURN que podrían revelar IP
                        if (configuration && configuration.iceServers) {
                            configuration.iceServers = configuration.iceServers.filter(server => {
                                // Solo permitir servidores específicos
                                return false; // Bloquear todos por defecto
                            });
                        }
                        
                        const pc = new OriginalRTCPeerConnection(configuration, constraints);
                        
                        // Override createDataChannel
                        const originalCreateDataChannel = pc.createDataChannel.bind(pc);
                        pc.createDataChannel = function(label, options) {
                            // Limitar creación de canales de datos
                            return originalCreateDataChannel(label, options);
                        };
                        
                        return pc;
                    };
                    
                    window.RTCPeerConnection.prototype = OriginalRTCPeerConnection.prototype;
                }
                
                // Override webkitRTCPeerConnection (legacy)
                if (window.webkitRTCPeerConnection) {
                    window.webkitRTCPeerConnection = window.RTCPeerConnection;
                }
                
                // Bloquear RTCDataChannel - Suavizado para no lanzar errores
                if (window.RTCDataChannel) {
                    const OriginalRTCDataChannel = window.RTCDataChannel;
                    window.RTCDataChannel = function() {
                        console.log('[Anti-Detection] RTCDataChannel blocked (silent)');
                        return {};
                    };
                }
                
                // Bloquear acceso a IP local via WebRTC
                const originalCreateOffer = RTCPeerConnection.prototype.createOffer;
                RTCPeerConnection.prototype.createOffer = function(options) {
                    const promise = originalCreateOffer.call(this, options);
                    return promise.then(offer => {
                        // Modificar SDP para evitar revelar IPs locales
                        if (offer && offer.sdp) {
                            offer.sdp = offer.sdp.replace(/\\r\\na=candidate:.*/g, '');
                        }
                        return offer;
                    });
                };
                
                console.log('[Anti-Detection] WebRTC leak prevention aplicado');
            } catch (e) {
                console.error('[Anti-Detection] Error en WebRTC prevention:', e);
            }
        })();
        """
    
    def generate_font_script(self) -> str:
        """
        Genera script para añadir variación en font fingerprinting.
        
        Returns:
            str: Script JavaScript para inyección.
        """
        seed = self.config.seed
        return f"""
        // Font Fingerprint Spoofing
        (function() {{
            'use strict';
            try {{
                const SEED = {seed};
                
                function seededRandom(seed) {{
                    const x = Math.sin(seed) * 10000;
                    return x - Math.floor(x);
                }}
                
                // Override measureText para añadir variación sutil
                const originalMeasureText = CanvasRenderingContext2D.prototype.measureText;
                CanvasRenderingContext2D.prototype.measureText = function(text) {{
                    const metrics = originalMeasureText.call(this, text);
                    
                    // Añadir variación sutil en las medidas
                    const noise = seededRandom(SEED + text.length) * 0.1 - 0.05;
                    
                    // Crear un nuevo objeto con valores modificados
                    return {{
                        width: metrics.width + noise,
                        actualBoundingBoxLeft: metrics.actualBoundingBoxLeft || 0,
                        actualBoundingBoxRight: (metrics.actualBoundingBoxRight || metrics.width) + noise,
                        actualBoundingBoxAscent: metrics.actualBoundingBoxAscent || 0,
                        actualBoundingBoxDescent: metrics.actualBoundingBoxDescent || 0,
                        fontBoundingBoxAscent: metrics.fontBoundingBoxAscent || 0,
                        fontBoundingBoxDescent: metrics.fontBoundingBoxDescent || 0,
                        emHeightAscent: metrics.emHeightAscent || 0,
                        emHeightDescent: metrics.emHeightDescent || 0,
                        hangingBaseline: metrics.hangingBaseline || 0,
                        alphabeticBaseline: metrics.alphabeticBaseline || 0,
                        ideographicBaseline: metrics.ideographicBaseline || 0
                    }};
                }};
                
                console.log('[Anti-Detection] Font fingerprint spoofing aplicado');
            }} catch (e) {{
                console.error('[Anti-Detection] Error en Font spoofing:', e);
            }}
        }})();
        """
    
    def generate_permissions_script(self) -> str:
        """
        Genera script para falsificar la Permissions API.
        
        Returns:
            str: Script JavaScript para inyección.
        """
        return """
        // Permissions API Spoofing
        (function() {
            'use strict';
            try {
                // Override permissions.query
                if (navigator.permissions && navigator.permissions.query) {
                    const originalQuery = navigator.permissions.query.bind(navigator.permissions);
                    
                    navigator.permissions.query = function(parameters) {
                        const permissionName = parameters.name;
                        
                        // Respuestas predefinidas para permisos comunes
                        const defaultPermissions = {
                            'geolocation': 'prompt',
                            'notifications': 'prompt',
                            'push': 'prompt',
                            'midi': 'prompt',
                            'camera': 'prompt',
                            'microphone': 'prompt',
                            'clipboard-read': 'prompt',
                            'clipboard-write': 'prompt',
                            'payment-handler': 'prompt',
                            'persistent-storage': 'prompt',
                            'accelerometer': 'prompt',
                            'gyroscope': 'prompt',
                            'magnetometer': 'prompt',
                            'screen-wake-lock': 'prompt',
                            'xr-spatial-tracking': 'prompt'
                        };
                        
                        const state = defaultPermissions[permissionName] || 'prompt';
                        
                        return Promise.resolve({
                            state: state,
                            status: state,
                            onchange: null,
                            addEventListener: function() {},
                            removeEventListener: function() {},
                            dispatchEvent: function() { return true; }
                        });
                    };
                }
                
                // Override mediaDevices.enumerateDevices
                if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
                    const originalEnumerateDevices = navigator.mediaDevices.enumerateDevices.bind(navigator.mediaDevices);
                    
                    navigator.mediaDevices.enumerateDevices = function() {
                        // Devolver dispositivos genéricos
                        return Promise.resolve([
                            { deviceId: 'default', kind: 'audioinput', label: '', groupId: 'default' },
                            { deviceId: 'default', kind: 'audiooutput', label: '', groupId: 'default' },
                            { deviceId: 'default', kind: 'videoinput', label: '', groupId: 'default' }
                        ]);
                    };
                }
                
                console.log('[Anti-Detection] Permissions spoofing aplicado');
            } catch (e) {
                console.error('[Anti-Detection] Error en Permissions spoofing:', e);
            }
        })();
        """
    
    def generate_performance_script(self) -> str:
        """
        Genera script para añadir jitter a las funciones de timing.
        
        Returns:
            str: Script JavaScript para inyección.
        """
        return """
        // Performance Timing Jitter
        (function() {
            'use strict';
            try {
                // Jitter base (±0.1ms)
                const JITTER_RANGE = 0.1;
                
                // Override performance.now()
                const originalNow = performance.now.bind(performance);
                let lastNow = originalNow();
                let offset = 0;
                
                performance.now = function() {
                    const realNow = originalNow();
                    
                    // Solo añadir jitter si el tiempo avanzó
                    if (realNow > lastNow) {
                        offset += (Math.random() - 0.5) * JITTER_RANGE * 2;
                        lastNow = realNow;
                    }
                    
                    return realNow + offset;
                };
                
                // Override Date.now()
                const originalDateNow = Date.now;
                Date.now = function() {
                    return Math.floor(originalDateNow() + (Math.random() - 0.5) * JITTER_RANGE * 2);
                };
                
                // Performance memory spoofing
                if (performance.memory) {
                    Object.defineProperty(performance, 'memory', {
                        get: function() {
                            return {
                                totalJSHeapSize: 50000000 + Math.floor(Math.random() * 50000000),
                                usedJSHeapSize: 30000000 + Math.floor(Math.random() * 30000000),
                                jsHeapSizeLimit: 2000000000
                            };
                        },
                        configurable: true
                    });
                }
                
                // Override requestAnimationFrame timing
                const originalRAF = window.requestAnimationFrame;
                window.requestAnimationFrame = function(callback) {
                    return originalRAF(function(timestamp) {
                        // Añadir jitter sutil al timestamp
                        callback(timestamp + (Math.random() - 0.5) * JITTER_RANGE);
                    });
                };
                
                console.log('[Anti-Detection] Performance timing jitter aplicado');
            } catch (e) {
                console.error('[Anti-Detection] Error en Performance jitter:', e);
            }
        })();
        """
    
    def generate_timezone_script(self) -> str:
        """
        Genera script para falsificar timezone.
        
        Returns:
            str: Script JavaScript para inyección.
        """
        return f"""
        // Timezone Spoofing
        (function() {{
            'use strict';
            try {{
                const targetTimezone = '{self.config.timezone}';
                
                // Override Intl.DateTimeFormat
                const OriginalDateTimeFormat = Intl.DateTimeFormat;
                Intl.DateTimeFormat = function(locales, options) {{
                    return new OriginalDateTimeFormat(locales, {{
                        ...options,
                        timeZone: targetTimezone
                    }});
                }};
                Intl.DateTimeFormat.prototype = OriginalDateTimeFormat.prototype;
                Intl.DateTimeFormat.supportedLocalesOf = OriginalDateTimeFormat.supportedLocalesOf;
                
                // Override Date.getTimezoneOffset
                const targetOffsets = {{
                    'America/New_York': 300,
                    'America/Los_Angeles': 480,
                    'Europe/London': 0,
                    'Europe/Paris': -60,
                    'Asia/Tokyo': -540,
                    'Asia/Shanghai': -480
                }};
                
                const offset = targetOffsets[targetTimezone] || 0;
                
                Object.defineProperty(Date.prototype, 'getTimezoneOffset', {{
                    value: function() {{
                        // Ajustar según horario de verano
                        const month = this.getMonth();
                        if (targetTimezone === 'America/New_York') {{
                            // DST: marzo-noviembre
                            if (month >= 2 && month <= 10) return 240;
                            return 300;
                        }}
                        return offset;
                    }},
                    configurable: true,
                    writable: true
                }});
                
                console.log('[Anti-Detection] Timezone spoofing aplicado');
            }} catch (e) {{
                console.error('[Anti-Detection] Error en Timezone spoofing:', e);
            }}
        }})();
        """
    
    def generate_iframe_script(self) -> str:
        """
        Genera script para prevenir detección via iframes.
        
        Returns:
            str: Script JavaScript para inyección.
        """
        return """
        // iframe Detection Prevention
        (function() {
            'use strict';
            try {
                // Ocultar que la página está siendo automatizada
                Object.defineProperty(window, 'outerWidth', {
                    get: function() { return window.innerWidth; },
                    configurable: true
                });
                
                Object.defineProperty(window, 'outerHeight', {
                    get: function() { return window.innerHeight + 100; },  // +100 for browser chrome
                    configurable: true
                });
                
                // Prevenir detección de window size
                const originalMatchMedia = window.matchMedia;
                window.matchMedia = function(query) {
                    const result = originalMatchMedia(query);
                    
                    // Falsificar media queries
                    if (query.includes('width') || query.includes('height')) {
                        return {
                            matches: false,
                            media: query,
                            onchange: null,
                            addListener: function() {},
                            removeListener: function() {},
                            addEventListener: function() {},
                            removeEventListener: function() {},
                            dispatchEvent: function() { return false; }
                        };
                    }
                    
                    return result;
                };
                
                console.log('[Anti-Detection] iframe detection prevention aplicado');
            } catch (e) {
                console.error('[Anti-Detection] Error en iframe prevention:', e);
            }
        })();
        """
    
    def generate_all_scripts(self) -> str:
        """
        Genera todos los scripts de fingerprinting combinados.
        
        Returns:
            str: Script JavaScript combinado para inyección.
        """
        scripts = [
            self.generate_webdriver_script(),
            self.generate_canvas_script(),
            self.generate_webgl_script(),
            self.generate_audio_script(),
            self.generate_navigator_script(),
            self.generate_screen_script(),
            self.generate_webrtc_script(),
            self.generate_font_script(),
            self.generate_permissions_script(),
            self.generate_performance_script(),
            self.generate_timezone_script(),
            self.generate_iframe_script(),
        ]
        
        # Filtrar según nivel
        if self.level == "basic":
            scripts = [
                self.generate_webdriver_script(),
                self.generate_navigator_script(),
            ]
        elif self.level == "standard":
            scripts = [
                self.generate_webdriver_script(),
                self.generate_canvas_script(),
                self.generate_webgl_script(),
                self.generate_navigator_script(),
                self.generate_screen_script(),
            ]
        
        return "\n".join(scripts)
    
    def get_script_hash(self) -> str:
        """
        Devuelve un hash del script para verificación.
        
        Returns:
            str: Hash MD5 del script.
        """
        script = self.generate_all_scripts()
        return hashlib.md5(script.encode()).hexdigest()


def create_fingerprint_from_profile(profile: Dict[str, Any], level: str = "full") -> FingerprintGenerator:
    """
    Crea un generador de fingerprint desde un perfil de hardware.
    
    Args:
        profile: Diccionario con configuración del perfil.
        level: Nivel de anti-detección.
    
    Returns:
        FingerprintGenerator: Generador configurado.
    """
    config = FingerprintConfig(
        seed=profile.get("seed", random.randint(1, 1000000)),
        webgl_vendor=profile.get("webgl_vendor", "Google Inc. (NVIDIA)"),
        webgl_renderer=profile.get("webgl_renderer", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0)"),
        hardware_concurrency=profile.get("hardware_concurrency", 8),
        device_memory=profile.get("device_memory", 8),
        platform=profile.get("platform", "Win32"),
        user_agent=profile.get("user_agent", ""),
        screen_width=profile.get("screen_width", 1920),
        screen_height=profile.get("screen_height", 1080),
        timezone=profile.get("timezone", "America/New_York"),
        languages=profile.get("languages", ["en-US", "en"]),
    )
    
    return FingerprintGenerator(config, level)
