"""
Módulo de fingerprinting para anti-detección avanzada.

Bugs corregidos respecto al original:
  1. WebGL usaba getContext override por instancia → ahora parchea el prototipo.
  2. Canvas doble ruido (toDataURL llama getImageData) → flag __fp_noised.
  3. AudioContext doble ruido (createBuffer + getChannelData) → flag __fp_creating.
  4. RTCPeerConnection función-wrapper rota → class extend.
  5. Jitter performance.memory usaba Math.random() → valores deterministas.
  6. Timezone getTimezoneOffset usaba getMonth() → puede llamar getter circular;
     reemplazado por timestamps UTC precalculados.
  7. Sin validación de level → ValueError temprano.
  8. matchMedia override rompe media queries legítimas → eliminado.
"""

import random
import hashlib
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


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
    # FIX: usar field() en lugar de None para evitar shared mutable defaults
    languages: List[str] = field(default_factory=lambda: ["en-US", "en"])
    plugins: List[dict] = field(default_factory=lambda: [
        {"name": "Chrome PDF Plugin", "filename": "internal-pdf-viewer",
         "description": "Portable Document Format"},
        {"name": "Chrome PDF Viewer", "filename": "mhjfbmdgcfjbbpaeojofohoefgiehjai",
         "description": ""},
        {"name": "Native Client", "filename": "internal-nacl-plugin",
         "description": ""},
    ])


class FingerprintGenerator:
    """
    Generador de scripts de fingerprinting para anti-detección.

    Esta clase genera código JavaScript que se inyecta en el navegador
    para falsificar varias APIs y propiedades del dispositivo.
    """

    VALID_LEVELS = {"basic", "standard", "full"}

    def __init__(self, config: FingerprintConfig, level: str = "full"):
        """
        Inicializa el generador de fingerprinting.

        Args:
            config: Configuración del fingerprint.
            level: Nivel de anti-detección (basic, standard, full).
        """
        # FIX #7: validación temprana
        if level not in self.VALID_LEVELS:
            raise ValueError(
                f"level debe ser uno de {self.VALID_LEVELS}, recibido: '{level}'"
            )
        self.config = config
        self.level = level
        self._rng = random.Random(config.seed)

    def _noise_value(self, base: float, variance: float = 0.1) -> float:
        """Genera un valor con ruido determinista basado en la semilla."""
        noise = self._rng.uniform(-variance, variance)
        return base + (base * noise)

    # ─────────────────────────────────────────────
    # Compatibilidad: get_seed() para driver.py
    # ─────────────────────────────────────────────

    def get_seed(self) -> int:
        return self.config.seed

    def generate_webdriver_script(self) -> str:
        """
        Falsifica navigator.webdriver, elimina variables ChromeDriver/Selenium
        y protege la integridad de la prototype chain para evitar detección
        via toString() o Symbol.toStringTag.
        """
        return """
        (function() {
            'use strict';
            try {
                // Eliminar del prototipo
                try { delete Object.getPrototypeOf(navigator).webdriver; } catch(e) {}

                Object.defineProperty(navigator, 'webdriver', {
                    get: function() { return undefined; },
                    configurable: true,
                    enumerable: true
                });

                // Variables inyectadas por ChromeDriver/Selenium
                ['$cdc_asdjflasutopfhvcZLmcfl_', '$cdc_', '$wdc_'].forEach(function(v) {
                    try { delete window[v]; } catch(e) {}
                });
                [
                    '__webdriver_script_fn', '$cdc_asdjflasutopfhvcZLmcfl_',
                    '__selenium_evaluate', '__selenium_unwrapped',
                    '__webdriver_evaluate', '__webdriver_unwrapped',
                    '__fxdriver_evaluate', '__fxdriver_unwrapped',
                    '__lastEvaluateTime'
                ].forEach(function(v) { try { delete document[v]; } catch(e) {} });

                // NUEVO: prototype chain integrity
                // Los detectores llaman Function.prototype.toString en funciones
                // nativas para ver si fueron reemplazadas. Parchamos toString
                // para que funciones modificadas sigan pareciendo nativas.
                const _nativeToString = Function.prototype.toString;
                const _proxied = new WeakSet();

                function _markNative(fn) {
                    try { _proxied.add(fn); } catch(e) {}
                    return fn;
                }
                window._fpMarkNative = _markNative;

                Function.prototype.toString = function() {
                    if (_proxied.has(this)) {
                        return 'function ' + (this.name || '') + '() { [native code] }';
                    }
                    return _nativeToString.call(this);
                };
                // Marcar nuestro propio toString como nativo
                _proxied.add(Function.prototype.toString);

                // NUEVO: document.hasFocus y visibilityState
                try {
                    document.hasFocus = _markNative(function() { return true; });
                    Object.defineProperty(document, 'visibilityState', { get: function() { return 'visible'; }, configurable: true });
                    Object.defineProperty(document, 'hidden', { get: function() { return false; }, configurable: true });
                } catch(e) {}

                // NUEVO: window.chrome.runtime más completo
                window.chrome = window.chrome || {};
                window.chrome.app = window.chrome.app || {};
                window.chrome.runtime = window.chrome.runtime || {};
                window.chrome.runtime.connect = _markNative(function() { return { postMessage: function(){}, disconnect: function(){}, onMessage: { addListener: function(){}, removeListener: function(){} } }; });
                window.chrome.runtime.sendMessage = _markNative(function() {});
                window.chrome.runtime.onMessage = { addListener: function(){}, removeListener: function(){} };
                window.chrome.runtime.id = undefined;
                window.chrome.loadTimes = _markNative(function() { return {}; });
                window.chrome.csi = _markNative(function() { return { startE: Date.now(), onloadT: Date.now(), pageT: 0, tran: 15 }; });

            } catch (e) {}
        })();
        """

    def generate_canvas_script(self) -> str:
        """
        Ruido determinista en canvas.
        FIX #2: flag __fp_noised evita doble ruido cuando toDataURL llama getImageData.
        Solo aplica a canvases pequeños (≤280x60) usados para fingerprinting.
        """
        seed = self.config.seed
        return f"""
        (function() {{
            'use strict';
            try {{
                const SEED = {seed};

                function seededRandom(s) {{
                    const x = Math.sin(s) * 10000;
                    return x - Math.floor(x);
                }}

                // FIX #2: función de ruido centralizada
                function addNoise(imageData) {{
                    const data = imageData.data;
                    let ns = SEED;
                    for (let i = 0; i < data.length; i += 4) {{
                        ns += 1;
                        const noise = Math.floor(seededRandom(ns) * 3) - 1;
                        data[i]   = Math.max(0, Math.min(255, data[i]   + noise));
                        data[i+1] = Math.max(0, Math.min(255, data[i+1] + noise));
                        data[i+2] = Math.max(0, Math.min(255, data[i+2] + noise));
                    }}
                    return imageData;
                }}

                const _origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
                const _origToDataURL    = HTMLCanvasElement.prototype.toDataURL;
                const _origToBlob       = HTMLCanvasElement.prototype.toBlob;

                // toDataURL: aplica ruido y marca flag para que getImageData no lo duplique
                HTMLCanvasElement.prototype.toDataURL = function(type) {{
                    if (this.width <= 280 && this.height <= 60) {{
                        const ctx = this.getContext('2d');
                        if (ctx && !this.__fp_noised) {{
                            try {{
                                this.__fp_noised = true;
                                const img = _origGetImageData.call(ctx, 0, 0, this.width, this.height);
                                addNoise(img);
                                ctx.putImageData(img, 0, 0);
                            }} catch(e) {{}} finally {{
                                this.__fp_noised = false;
                            }}
                        }}
                    }}
                    return _origToDataURL.apply(this, arguments);
                }};

                // toBlob: mismo patrón
                HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {{
                    if (this.width <= 280 && this.height <= 60) {{
                        const ctx = this.getContext('2d');
                        if (ctx && !this.__fp_noised) {{
                            try {{
                                this.__fp_noised = true;
                                const img = _origGetImageData.call(ctx, 0, 0, this.width, this.height);
                                addNoise(img);
                                ctx.putImageData(img, 0, 0);
                            }} catch(e) {{}} finally {{
                                this.__fp_noised = false;
                            }}
                        }}
                    }}
                    return _origToBlob.apply(this, arguments);
                }};

                // getImageData: ruido solo si NO estamos dentro de toDataURL/toBlob
                CanvasRenderingContext2D.prototype.getImageData = function(sx, sy, sw, sh) {{
                    const result = _origGetImageData.apply(this, arguments);
                    if (this.canvas && this.canvas.__fp_noised) return result;
                    if (sw <= 280 && sh <= 60) addNoise(result);
                    return result;
                }};

            }} catch (e) {{

            }}
        }})();
        """

    def generate_webgl_script(self) -> str:
        """
        FIX #1: parchea el prototipo directamente en lugar de hacer override
        de getContext por instancia (que era detectable y menos robusto).
        Incluye mapa de constantes WebGL reales en lugar de índice consecutivo.
        """
        vendor   = self.config.webgl_vendor
        renderer = self.config.webgl_renderer

        # Mapa de constantes WebGL reales → valores spoofed
        webgl_params = {
            0x0D33: 16384,   # MAX_TEXTURE_SIZE
            0x84E8: 16384,   # MAX_RENDERBUFFER_SIZE
            0x8869: 16,      # MAX_VERTEX_ATTRIBS
            0x8B4A: 4096,    # MAX_VERTEX_UNIFORM_VECTORS
            0x8B49: 1024,    # MAX_FRAGMENT_UNIFORM_VECTORS
            0x8B4C: 16,      # MAX_VERTEX_TEXTURE_IMAGE_UNITS
            0x8B4D: 32,      # MAX_COMBINED_TEXTURE_IMAGE_UNITS
            0x8872: 16,      # MAX_TEXTURE_IMAGE_UNITS
            0x851C: 16384,   # MAX_CUBE_MAP_TEXTURE_SIZE
            0x8D57: 4,       # MAX_SAMPLES
            0x8CDF: 8,       # MAX_COLOR_ATTACHMENTS
            0x8824: 8,       # MAX_DRAW_BUFFERS
            # NUEVO: WebGL2 parámetros extendidos
            0x806F: 256,     # MAX_3D_TEXTURE_SIZE
            0x8073: 256,     # MAX_ARRAY_TEXTURE_LAYERS
            0x8A2B: 14,      # MAX_VERTEX_UNIFORM_BLOCKS
            0x8A2D: 14,      # MAX_FRAGMENT_UNIFORM_BLOCKS
            0x8A2E: 28,      # MAX_COMBINED_UNIFORM_BLOCKS
            0x8A2F: 72,      # MAX_UNIFORM_BUFFER_BINDINGS
            0x8A30: 65536,   # MAX_UNIFORM_BLOCK_SIZE
            0x8E82: 4,       # MAX_TRANSFORM_FEEDBACK_SEPARATE_ATTRIBS
        }
        params_js = json.dumps({str(k): v for k, v in webgl_params.items()})

        return f"""
        (function() {{
            'use strict';
            try {{
                const VENDOR   = '{vendor}';
                const RENDERER = '{renderer}';
                const PARAMS   = {params_js};

                function patchWebGL(ctx) {{
                    if (!ctx || !ctx.prototype) return;

                    const _origGP = ctx.prototype.getParameter;
                    ctx.prototype.getParameter = function(parameter) {{
                        if (parameter === 37445 || parameter === 0x9245) return VENDOR;
                        if (parameter === 37446 || parameter === 0x9246) return RENDERER;
                        if (parameter === 0x1F02) return 'WebGL 1.0 (OpenGL ES 2.0 Chromium)';
                        if (parameter === 0x8B8C) return 'WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)';
                        if (parameter === 0x1F00) return 'Google Inc.';
                        const key = String(parameter);
                        if (PARAMS.hasOwnProperty(key)) return PARAMS[key];
                        return _origGP.apply(this, arguments);
                    }};

                    const _origGE = ctx.prototype.getExtension;
                    ctx.prototype.getExtension = function(name) {{
                        if (name === 'WEBGL_debug_renderer_info') {{
                            return {{ UNMASKED_VENDOR_WEBGL: 0x9245, UNMASKED_RENDERER_WEBGL: 0x9246 }};
                        }}
                        return _origGE.apply(this, arguments);
                    }};

                    const _origGSE = ctx.prototype.getSupportedExtensions;
                    ctx.prototype.getSupportedExtensions = function() {{
                        const exts = _origGSE.apply(this, arguments) || [];
                        return exts.filter(function(e) {{ return !e.includes('debug'); }});
                    }};

                    // NUEVO: getShaderPrecisionFormat — usado para GPU fingerprinting
                    if (ctx.prototype.getShaderPrecisionFormat) {{
                        const _origGSPF = ctx.prototype.getShaderPrecisionFormat;
                        ctx.prototype.getShaderPrecisionFormat = function(shaderType, precisionType) {{
                            const result = _origGSPF.apply(this, arguments);
                            // Devolver valores estándar consistentes para evitar fingerprint por precisión GPU
                            if (result) {{
                                return {{ rangeMin: 127, rangeMax: 127, precision: 23 }};
                            }}
                            return result;
                        }};
                    }}
                }}

                if (typeof WebGLRenderingContext  !== 'undefined') patchWebGL(WebGLRenderingContext);
                if (typeof WebGL2RenderingContext !== 'undefined') patchWebGL(WebGL2RenderingContext);

                // NUEVO: OffscreenCanvas — misma cobertura que Canvas normal
                if (typeof OffscreenCanvas !== 'undefined') {{
                    try {{
                        const _origOCGetContext = OffscreenCanvas.prototype.getContext;
                        OffscreenCanvas.prototype.getContext = function(type, attrs) {{
                            const ctx = _origOCGetContext.apply(this, arguments);
                            if (ctx && (type === 'webgl' || type === 'webgl2')) {{
                                patchWebGL(ctx.constructor);
                            }}
                            return ctx;
                        }};
                    }} catch(e) {{}}
                }}

            }} catch (e) {{}}
        }})();
        """

    def generate_audio_script(self) -> str:
        """
        FIX #3: flag __fp_creating evita doble ruido entre createBuffer y getChannelData.
        Incluye OfflineAudioContext, createOscillator y createDynamicsCompressor.
        """
        seed = self.config.seed
        return f"""
        (function() {{
            'use strict';
            try {{
                const SEED = {seed};

                function seededRandom(s) {{
                    const x = Math.sin(s) * 10000;
                    return x - Math.floor(x);
                }}

                // getChannelData con ruido, respeta flag __fp_creating
                if (typeof AudioBuffer !== 'undefined' && AudioBuffer.prototype) {{
                    const _origGCD = AudioBuffer.prototype.getChannelData;
                    AudioBuffer.prototype.getChannelData = function(channel) {{
                        const data = _origGCD.call(this, channel);
                        if (!this.__fp_creating) {{
                            for (let i = 0; i < data.length; i++) {{
                                data[i] += seededRandom(SEED + i + (channel||0) * 10000) * 0.0002 - 0.0001;
                            }}
                        }}
                        return data;
                    }};
                }}

                if (typeof AudioContext !== 'undefined' && AudioContext.prototype) {{
                    // FIX #3: createBuffer marca buffer para evitar doble ruido
                    const _origCB = AudioContext.prototype.createBuffer;
                    AudioContext.prototype.createBuffer = function(ch, len, sr) {{
                        const buf = _origCB.apply(this, arguments);
                        buf.__fp_creating = true;
                        for (let c = 0; c < ch; c++) {{
                            const d = buf.getChannelData(c);
                            for (let i = 0; i < d.length; i++) {{
                                d[i] += seededRandom(SEED + i + c * 10000) * 0.0001 - 0.00005;
                            }}
                        }}
                        buf.__fp_creating = false;
                        return buf;
                    }};

                    // createOscillator: variación de frecuencia
                    const _origCO = AudioContext.prototype.createOscillator;
                    AudioContext.prototype.createOscillator = function() {{
                        const osc = _origCO.apply(this, arguments);
                        const _sv = osc.frequency.setValueAtTime.bind(osc.frequency);
                        osc.frequency.setValueAtTime = function(value, startTime) {{
                            const noise = seededRandom(SEED + startTime * 1000) * 0.0001 - 0.00005;
                            return _sv(value * (1 + noise), startTime);
                        }};
                        return osc;
                    }};

                    // createDynamicsCompressor: variación en parámetros
                    const _origCDC = AudioContext.prototype.createDynamicsCompressor;
                    AudioContext.prototype.createDynamicsCompressor = function() {{
                        const comp = _origCDC.apply(this, arguments);
                        const noise = seededRandom(SEED);
                        comp.threshold.value += noise * 0.1;
                        comp.knee.value      += noise * 0.1;
                        comp.ratio.value     += noise * 0.01;
                        return comp;
                    }};
                }}

                // OfflineAudioContext: ruido en buffer final
                if (typeof OfflineAudioContext !== 'undefined' && OfflineAudioContext.prototype) {{
                    const _origSR = OfflineAudioContext.prototype.startRendering;
                    OfflineAudioContext.prototype.startRendering = function() {{
                        return _origSR.apply(this, arguments).then(function(buffer) {{
                            for (let ch = 0; ch < buffer.numberOfChannels; ch++) {{
                                const data = buffer.getChannelData(ch);
                                for (let i = 0; i < data.length; i++) {{
                                    data[i] += seededRandom(SEED + i + ch * 10000) * 0.00001 - 0.000005;
                                }}
                            }}
                            return buffer;
                        }});
                    }};
                }}

            }} catch (e) {{

            }}
        }})();
        """

    def generate_navigator_script(self) -> str:
        """Falsifica propiedades del navigator incluyendo plugins y mimeTypes."""
        ua = self.config.user_agent
        app_version = ua.split("Mozilla/")[1] if "Mozilla/" in ua else "5.0"
        return f"""
        (function() {{
            'use strict';
            try {{
                const props = {{
                    hardwareConcurrency: {self.config.hardware_concurrency},
                    deviceMemory:        {self.config.device_memory},
                    platform:            '{self.config.platform}',
                    vendor:              'Google Inc.',
                    vendorSub:           '',
                    productSub:          '20030107',
                    cookieEnabled:       true,
                    doNotTrack:          null,
                    maxTouchPoints:      0,
                    appCodeName:         'Mozilla',
                    appName:             'Netscape',
                    appVersion:          '{app_version}',
                    product:             'Gecko',
                    pdfViewerEnabled:    true,
                    languages:           {json.dumps(self.config.languages)},
                    language:            '{self.config.languages[0] if self.config.languages else "en-US"}',
                    onLine:              true
                }};

                for (const [prop, value] of Object.entries(props)) {{
                    try {{
                        Object.defineProperty(navigator, prop, {{
                            get: function() {{ return value; }},
                            configurable: true, enumerable: true
                        }});
                    }} catch (e) {{}}
                }}

                // Plugins
                const pluginsData = {json.dumps(self.config.plugins)};
                const pluginArray = {{
                    length: pluginsData.length,
                    item: function(i) {{ return this[i] || null; }},
                    namedItem: function(n) {{
                        for (let i = 0; i < this.length; i++) {{
                            if (this[i].name === n) return this[i];
                        }}
                        return null;
                    }},
                    refresh: function() {{}}
                }};
                pluginsData.forEach(function(p, i) {{
                    pluginArray[i] = {{
                        name: p.name, filename: p.filename,
                        description: p.description || p.name,
                        length: 1,
                        item: function() {{ return {{}}; }},
                        namedItem: function() {{ return {{}}; }}
                    }};
                }});
                Object.defineProperty(navigator, 'plugins', {{
                    get: function() {{ return pluginArray; }},
                    configurable: true, enumerable: true
                }});

                // mimeTypes
                const mimeTypesData = {{
                    'application/pdf': {{
                        description: 'Portable Document Format', suffixes: 'pdf',
                        type: 'application/pdf', enabledPlugin: pluginArray[0]
                    }},
                    'application/x-google-chrome-pdf': {{
                        description: 'Portable Document Format', suffixes: 'pdf',
                        type: 'application/x-google-chrome-pdf', enabledPlugin: pluginArray[0]
                    }}
                }};
                Object.defineProperty(navigator, 'mimeTypes', {{
                    get: function() {{
                        return {{
                            length: Object.keys(mimeTypesData).length,
                            item: function(i) {{ return Object.values(mimeTypesData)[i] || null; }},
                            namedItem: function(n) {{ return mimeTypesData[n] || null; }},
                            ...mimeTypesData
                        }};
                    }},
                    configurable: true, enumerable: true
                }});

                // getBattery
                if (navigator.getBattery) {{
                    Object.defineProperty(navigator, 'getBattery', {{
                        value: function() {{
                            return Promise.resolve({{
                                charging: true, chargingTime: 0,
                                dischargingTime: Infinity, level: 0.92,
                                onchargingchange: null, onchargingtimechange: null,
                                ondischargingtimechange: null, onlevelchange: null,
                                addEventListener: function() {{}}, removeEventListener: function() {{}}
                            }});
                        }},
                        configurable: true, writable: true
                    }});
                }}

                // connection completo
                try {{
                    const _conn = {{
                        rtt: 50, downlink: 10, effectiveType: '4g',
                        saveData: false, type: 'wifi', onchange: null,
                        addEventListener: function() {{}}, removeEventListener: function() {{}}
                    }};
                    Object.defineProperty(navigator, 'connection', {{
                        get: function() {{ return _conn; }}, configurable: true
                    }});
                }} catch(e) {{}}

                // NUEVO: speechSynthesis con voces realistas (vacía = detectable)
                try {{
                    const _voices = [
                        {{ voiceURI: 'Google US English', name: 'Google US English', lang: 'en-US', localService: false, default: true }},
                        {{ voiceURI: 'Google UK English Female', name: 'Google UK English Female', lang: 'en-GB', localService: false, default: false }},
                        {{ voiceURI: 'Google español', name: 'Google español', lang: 'es-ES', localService: false, default: false }},
                    ];
                    if (!window.speechSynthesis) {{
                        window.speechSynthesis = {{
                            pending: false, speaking: false, paused: false,
                            onvoiceschanged: null,
                            getVoices: function() {{ return _voices; }},
                            speak: function() {{}}, cancel: function() {{}},
                            pause: function() {{}}, resume: function() {{}}
                        }};
                    }} else {{
                        const _origGV = window.speechSynthesis.getVoices.bind(window.speechSynthesis);
                        window.speechSynthesis.getVoices = function() {{
                            const real = _origGV();
                            return real.length > 0 ? real : _voices;
                        }};
                    }}
                }} catch(e) {{}}

                // NUEVO: history.length > 0 (siempre 0 en bot = detectable)
                try {{
                    Object.defineProperty(window.history, 'length', {{
                        get: function() {{ return 3; }}, configurable: true
                    }});
                }} catch(e) {{}}

            }} catch (e) {{}}
        }})();
        """

    def generate_screen_script(self) -> str:
        """Falsifica resolución de pantalla y devicePixelRatio."""
        w = self.config.screen_width
        h = self.config.screen_height
        cd = self.config.color_depth
        return f"""
        (function() {{
            'use strict';
            try {{
                const _screenProps = [
                    ['width', {w}], ['height', {h}],
                    ['availWidth', {w}], ['availHeight', {h} - 40],
                    ['colorDepth', {cd}], ['pixelDepth', {cd}],
                    ['top', 0], ['left', 0], ['availTop', 0], ['availLeft', 0]
                ];
                _screenProps.forEach(function(pair) {{
                    try {{
                        Object.defineProperty(screen, pair[0], {{
                            get: function() {{ return pair[1]; }},
                            configurable: true, enumerable: true
                        }});
                    }} catch(e) {{}}
                }});

                try {{
                    Object.defineProperty(screen, 'orientation', {{
                        get: function() {{
                            return {{
                                type: 'landscape-primary', angle: 0, onchange: null,
                                addEventListener: function() {{}},
                                removeEventListener: function() {{}},
                                dispatchEvent: function() {{ return true; }}
                            }};
                        }},
                        configurable: true
                    }});
                }} catch(e) {{}}

                Object.defineProperty(window, 'devicePixelRatio', {{
                    get: function() {{ return 1; }}, configurable: true
                }});
                Object.defineProperty(window, 'outerWidth', {{
                    get: function() {{ return {w}; }}, configurable: true
                }});
                Object.defineProperty(window, 'outerHeight', {{
                    get: function() {{ return {h} - 40; }}, configurable: true
                }});

            }} catch (e) {{

            }}
        }})();
        """

    def generate_webrtc_script(self) -> str:
        """
        FIX #4: usa class extend en lugar de función-wrapper para RTCPeerConnection.
        Preserva instanceof y propiedades estáticas correctamente.
        Incluye SDP leak prevention.
        """
        return """
        (function() {
            'use strict';
            try {
                const OrigRTC = window.RTCPeerConnection
                             || window.webkitRTCPeerConnection
                             || window.mozRTCPeerConnection;
                if (!OrigRTC) return;

                // FIX #4: class extend preserva instanceof y propiedades estáticas
                class PatchedRTC extends OrigRTC {
                    constructor(config, constraints) {
                        const patched = Object.assign({}, config || {}, { iceServers: [] });
                        super(patched, constraints);
                    }
                }

                // SDP leak prevention
                const _origCreateOffer = PatchedRTC.prototype.createOffer;
                PatchedRTC.prototype.createOffer = function(options) {
                    return _origCreateOffer.call(this, options).then(function(offer) {
                        if (offer && offer.sdp) {
                            offer.sdp = offer.sdp.replace(/\r\na=candidate:.*/g, '');
                        }
                        return offer;
                    });
                };

                window.RTCPeerConnection       = PatchedRTC;
                window.webkitRTCPeerConnection = PatchedRTC;
                window.mozRTCPeerConnection    = PatchedRTC;

            } catch (e) {

            }
        })();
        """

    def generate_font_script(self) -> str:
        """Ruido determinista en measureText y variación en offsetWidth/Height."""
        seed = self.config.seed
        return f"""
        (function() {{
            'use strict';
            try {{
                const SEED = {seed};
                function seededRandom(s) {{
                    const x = Math.sin(s) * 10000;
                    return x - Math.floor(x);
                }}

                // measureText con ruido determinista por seed
                const _origMT = CanvasRenderingContext2D.prototype.measureText;
                CanvasRenderingContext2D.prototype.measureText = function(text) {{
                    const m = _origMT.call(this, text);
                    const noise = seededRandom(SEED + text.length) * 0.1 - 0.05;
                    return {{
                        width:                    m.width + noise,
                        actualBoundingBoxLeft:    m.actualBoundingBoxLeft    || 0,
                        actualBoundingBoxRight:   (m.actualBoundingBoxRight  || m.width) + noise,
                        actualBoundingBoxAscent:  m.actualBoundingBoxAscent  || 0,
                        actualBoundingBoxDescent: m.actualBoundingBoxDescent || 0,
                        fontBoundingBoxAscent:    m.fontBoundingBoxAscent    || 0,
                        fontBoundingBoxDescent:   m.fontBoundingBoxDescent   || 0,
                        emHeightAscent:           m.emHeightAscent           || 0,
                        emHeightDescent:          m.emHeightDescent          || 0,
                        hangingBaseline:          m.hangingBaseline          || 0,
                        alphabeticBaseline:       m.alphabeticBaseline       || 0,
                        ideographicBaseline:      m.ideographicBaseline      || 0
                    }};
                }};

                // offsetWidth/Height con micro-variación
                [['offsetWidth',7],['offsetHeight',13],['clientWidth',17],['clientHeight',19]]
                .forEach(function(pair) {{
                    const desc = Object.getOwnPropertyDescriptor(HTMLElement.prototype, pair[0]);
                    if (!desc) return;
                    Object.defineProperty(HTMLElement.prototype, pair[0], {{
                        get: function() {{
                            const v = desc.get.call(this);
                            return typeof v === 'number' ? v + (v * (pair[1] % 10)) / 10000 : v;
                        }},
                        configurable: true
                    }});
                }});

            }} catch (e) {{

            }}
        }})();
        """

    def generate_permissions_script(self) -> str:
        """Falsifica Permissions API y enumerateDevices."""
        return """
        (function() {
            'use strict';
            try {
                if (navigator.permissions && navigator.permissions.query) {
                    const _origQuery = navigator.permissions.query.bind(navigator.permissions);
                    navigator.permissions.query = function(parameters) {
                        const prompted = [
                            'geolocation','notifications','push','midi',
                            'camera','microphone','clipboard-read','clipboard-write',
                            'payment-handler','persistent-storage','accelerometer',
                            'gyroscope','magnetometer','screen-wake-lock','xr-spatial-tracking'
                        ];
                        const state = prompted.includes(parameters.name) ? 'prompt' : 'prompt';
                        return Promise.resolve({
                            state: state, status: state, onchange: null,
                            addEventListener: function() {},
                            removeEventListener: function() {},
                            dispatchEvent: function() { return true; }
                        });
                    };
                }

                if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
                    navigator.mediaDevices.enumerateDevices = function() {
                        return Promise.resolve([
                            { deviceId: 'default', kind: 'audioinput',  label: '', groupId: 'default' },
                            { deviceId: 'default', kind: 'audiooutput', label: '', groupId: 'default' },
                            { deviceId: 'default', kind: 'videoinput',  label: '', groupId: 'default' }
                        ]);
                    };
                }

            } catch (e) {

            }
        })();
        """

    def generate_performance_script(self) -> str:
        """
        FIX #5: performance.memory usa valores fijos deterministas, no Math.random().
        Jitter en performance.now redondeado a 0.1ms para imitar throttling real.
        """
        return """
        (function() {
            'use strict';
            try {
                const _origNow = performance.now.bind(performance);
                performance.now = function() {
                    const raw = _origNow();
                    // FIX #5: redondear a 0.1ms + ruido mínimo (imita throttling Chrome/Firefox)
                    return Math.round(raw * 10) / 10 + (Math.random() * 0.1 - 0.05);
                };

                // Date.now: interceptar para consistencia con performance.now
                const _origDateNow = Date.now.bind(Date);
                Date.now = function() { return _origDateNow(); };

                // FIX #5: memory con valores fijos (no random, para consistencia)
                if (typeof performance !== 'undefined') {
                    Object.defineProperty(performance, 'memory', {
                        get: function() {
                            return {
                                jsHeapSizeLimit:  2172649472,
                                totalJSHeapSize:  50000000,
                                usedJSHeapSize:   30000000
                            };
                        },
                        configurable: true
                    });
                }

                // RAF timing
                if (window.requestAnimationFrame) {
                    const _origRAF = window.requestAnimationFrame;
                    window.requestAnimationFrame = function(callback) {
                        return _origRAF(function(ts) {
                            callback(Math.round(ts * 10) / 10 + (Math.random() * 0.1 - 0.05));
                        });
                    };
                }

            } catch (e) {

            }
        })();
        """

    def generate_timezone_script(self) -> str:
        """
        FIX #6: getTimezoneOffset usa timestamps UTC precalculados para evitar
        recursión. La versión original usaba getMonth() que puede llamar
        internamente al getter que estamos sobreescribiendo.
        """
        tz = self.config.timezone
        return f"""
        (function() {{
            'use strict';
            try {{
                const targetTimezone = '{tz}';

                if (typeof Intl !== 'undefined' && Intl.DateTimeFormat) {{
                    const _OrigDTF = Intl.DateTimeFormat;
                    Intl.DateTimeFormat = function(locales, options) {{
                        return new _OrigDTF(locales, Object.assign({{}}, options || {{}}, {{
                            timeZone: targetTimezone
                        }}));
                    }};
                    Intl.DateTimeFormat.prototype = _OrigDTF.prototype;
                    Intl.DateTimeFormat.supportedLocalesOf = _OrigDTF.supportedLocalesOf;
                }}

                // FIX #6: precalcular timestamps DST fuera del getter
                (function() {{
                    const year = new Date().getUTCFullYear();
                    const dstStart = Date.UTC(year, 2, 8,  2, 0, 0);
                    const dstEnd   = Date.UTC(year, 10, 1, 2, 0, 0);

                    const offsets = {{
                        'America/New_York':    [240, 300],
                        'America/Los_Angeles': [420, 480],
                        'Europe/London':       [-60,   0],
                        'Europe/Paris':        [-120, -60],
                        'Asia/Tokyo':          [-540, -540],
                        'Asia/Shanghai':       [-480, -480]
                    }};
                    const pair = offsets[targetTimezone] || [0, 0];

                    Date.prototype.getTimezoneOffset = function() {{
                        // getTime() no llama getTimezoneOffset → sin recursión
                        const ts = this.getTime();
                        return (ts >= dstStart && ts < dstEnd) ? pair[0] : pair[1];
                    }};
                }})();

            }} catch (e) {{

            }}
        }})();
        """

    def generate_iframe_script(self) -> str:
        """
        FIX #8: eliminado el override de matchMedia que rompía media queries
        legítimas de la página. Solo mantiene outerWidth/Height.
        """
        return f"""
        (function() {{
            'use strict';
            try {{
                // Solo corregir dimensiones de ventana
                // FIX #8: matchMedia eliminado — rompía CSS responsive de la página
                Object.defineProperty(window, 'outerWidth', {{
                    get: function() {{ return {self.config.screen_width}; }},
                    configurable: true
                }});
                Object.defineProperty(window, 'outerHeight', {{
                    get: function() {{ return {self.config.screen_height} - 40; }},
                    configurable: true
                }});
            }} catch (e) {{

            }}
        }})();
        """

    def generate_antibot_extras_script(self) -> str:
        """
        Técnicas adicionales anti-bot de alto impacto:
        - Notification API state (ausencia = sospechosa)
        - serviceWorker present (ausencia = sospechosa)
        - CSS getComputedStyle micro-variación
        - setTimeout/setInterval precision fingerprint
        - iframe sandbox detection
        - Error stack trace sanitization
        """
        seed = self.config.seed
        return f"""
        (function() {{
            'use strict';

            // Notification API: estado 'default' (no granted ni denied = bot típico)
            try {{
                if (typeof Notification !== 'undefined') {{
                    Object.defineProperty(Notification, 'permission', {{
                        get: function() {{ return 'default'; }}, configurable: true
                    }});
                }}
            }} catch(e) {{}}

            // serviceWorker: presencia esperada en Chrome real
            try {{
                if (!navigator.serviceWorker) {{
                    Object.defineProperty(navigator, 'serviceWorker', {{
                        get: function() {{
                            return {{
                                ready: Promise.resolve({{}}),
                                register: function() {{ return Promise.resolve({{}}); }},
                                getRegistration: function() {{ return Promise.resolve(undefined); }},
                                getRegistrations: function() {{ return Promise.resolve([]); }},
                                addEventListener: function() {{}},
                                removeEventListener: function() {{}}
                            }};
                        }},
                        configurable: true
                    }});
                }}
            }} catch(e) {{}}

            // setTimeout/setInterval: normalizar precision para evitar timing fingerprint
            try {{
                const _origST = window.setTimeout;
                const _origSI = window.setInterval;
                window.setTimeout = function(fn, delay) {{
                    return _origST(fn, Math.max(delay || 0, 1));
                }};
                window.setInterval = function(fn, delay) {{
                    return _origSI(fn, Math.max(delay || 0, 1));
                }};
            }} catch(e) {{}}

            // Error stack traces: sanitizar paths de Selenium/ChromeDriver
            try {{
                const _origPrepare = Error.prepareStackTrace;
                Error.prepareStackTrace = function(err, stack) {{
                    if (_origPrepare) {{
                        const result = _origPrepare(err, stack);
                        if (typeof result === 'string') {{
                            return result
                                .replace(/chromedriver/gi, 'chrome')
                                .replace(/selenium/gi, 'browser')
                                .replace(/webdriver/gi, 'driver');
                        }}
                        return result;
                    }}
                    return stack.toString();
                }};
            }} catch(e) {{}}

            // CSS getComputedStyle: micro-variación para evitar font/layout fingerprint
            try {{
                const _seed = {seed};
                function _sr(s) {{ const x = Math.sin(s) * 10000; return x - Math.floor(x); }}
                const _origGCS = window.getComputedStyle;
                window.getComputedStyle = function(el, pseudo) {{
                    const style = _origGCS.call(window, el, pseudo);
                    const _origGPV = style.getPropertyValue.bind(style);
                    style.getPropertyValue = function(prop) {{
                        const val = _origGPV(prop);
                        // Solo añadir micro-variación a propiedades de dimensión
                        if (prop === 'letter-spacing' || prop === 'word-spacing') {{
                            const noise = _sr(_seed + prop.length) * 0.02 - 0.01;
                            const num = parseFloat(val);
                            if (!isNaN(num)) return (num + noise) + 'px';
                        }}
                        return val;
                    }};
                    return style;
                }};
            }} catch(e) {{}}

        }})();
        """

    def generate_all_scripts(self) -> str:
        """
        Genera todos los scripts combinados según el nivel configurado.
        """
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
                self.generate_timezone_script(),
            ]
        else:  # full
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
                self.generate_antibot_extras_script(),
            ]

        return "\n".join(scripts)

    def get_script_hash(self) -> str:
        """Hash MD5 del script generado."""
        return hashlib.md5(self.generate_all_scripts().encode()).hexdigest()


def create_fingerprint_from_profile(profile: Dict[str, Any],
                                    level: str = "full") -> FingerprintGenerator:
    """
    Crea un FingerprintGenerator desde un dict de HARDWARE_PROFILES.

    Args:
        profile: dict con keys del perfil de hardware.
        level:   nivel de anti-detección (basic | standard | full).
    """
    config = FingerprintConfig(
        seed=profile.get("seed", random.randint(1, 1000000)),
        webgl_vendor=profile.get("webgl_vendor", "Google Inc. (NVIDIA)"),
        webgl_renderer=profile.get("webgl_renderer", "ANGLE (NVIDIA GeForce RTX 3080)"),
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