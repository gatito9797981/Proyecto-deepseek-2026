/**
 * DeepSeek Advanced Spy Mode v2
 * Comprehensive data extraction: UI, Network, Storage, and DOM Structure.
 */
(function () {
    'use strict';

    // Registro de red para interceptar peticiones fetch
    let networkLog = [];
    const originalFetch = window.fetch;
    window.fetch = function (...args) {
        const url = typeof args[0] === 'string' ? args[0] : args[0].url;
        const method = args[1]?.method || 'GET';

        const request = {
            url: url,
            method: method,
            headers: args[1]?.headers,
            timestamp: new Date().toISOString()
        };

        // Solo loguear peticiones relevantes a la API de chat para no saturar
        if (url.includes('chat') || url.includes('api')) {
            networkLog.push(request);
        }

        return originalFetch.apply(this, args);
    };

    // Función para obtener un selector CSS único y robusto
    function getCssSelector(el) {
        if (!el || el.nodeType !== Node.ELEMENT_NODE) return null;
        if (el.id) return `#${el.id}`;

        // Intentar usar data-testid si existe (común en apps modernas)
        const testId = el.getAttribute('data-testid');
        if (testId) return `[data-testid="${testId}"]`;

        let path = [];
        let current = el;
        while (current && current.parentElement) {
            let selector = current.tagName.toLowerCase();
            if (current.className) {
                const classes = current.className.split(/\s+/).filter(c => c && !/^\d/.test(c) && !c.includes(':'));
                if (classes.length) selector += '.' + classes.slice(0, 2).join('.');
            }
            const siblings = Array.from(current.parentElement.children).filter(s => s.tagName === current.tagName);
            if (siblings.length > 1) {
                const index = siblings.indexOf(current) + 1;
                selector += `:nth-of-type(${index})`;
            }
            path.unshift(selector);
            current = current.parentElement;
            if (path.length > 5) break; // Limitar profundidad
        }
        return path.join(' > ');
    }

    // Buscar elementos por contenido de texto o atributos
    function queryAdvanced(patterns) {
        const results = {};
        for (const [key, pattern] of Object.entries(patterns)) {
            const elements = Array.from(document.querySelectorAll('*')).filter(el => {
                const text = el.innerText || '';
                const role = el.getAttribute('role') || '';
                const ariaLabel = el.getAttribute('aria-label') || '';
                return pattern.test(text) || pattern.test(role) || pattern.test(ariaLabel);
            });

            results[key] = elements.slice(0, 5).map(el => ({
                selector: getCssSelector(el),
                text: el.innerText ? el.innerText.substring(0, 50).trim() : '',
                tag: el.tagName,
                rect: el.getBoundingClientRect()
            }));
        }
        return results;
    }

    function getStorage() {
        try {
            return {
                localStorage: { ...localStorage },
                sessionStorage: { ...sessionStorage },
                cookies: document.cookie
            };
        } catch (e) { return "Access Denied"; }
    }

    function scanUI() {
        try {
            const data = {
                type: 'DEEPSEEK_SPY_DATA',
                timestamp: new Date().toISOString(),
                url: window.location.href,
                title: document.title,
                storage: getStorage(),
                network: networkLog.slice(-5), // Últimas 5 peticiones
                ui: queryAdvanced({
                    send: /send|enviar/i,
                    chat_input: /message|escribe/i,
                    thinking: /deepthink|pensar/i,
                    search: /search|buscar/i,
                    attachment: /attach|adjuntar/i,
                    history: /history|historial/i
                }),
                // Captura de bloques de mensajes
                messages: Array.from(document.querySelectorAll('div[class*="markdown"], div[class*="message"]')).slice(-3).map(m => ({
                    role: m.className.includes('user') ? 'user' : 'assistant',
                    content: m.innerText.substring(0, 100),
                    selector: getCssSelector(m)
                }))
            };

            console.log("DEEPSEEK_SPY_DATA:" + JSON.stringify(data));
        } catch (err) {
            console.error("[Spy Error]", err);
        }
    }

    // Escaneo inicial y periódico
    scanUI();
    const interval = setInterval(scanUI, 2000);

    console.log("[DeepSeek Spy v2] Iniciado. Capturando todo.");

    // Limpieza al re-inyectar
    window._spyInterval = interval;
})();
