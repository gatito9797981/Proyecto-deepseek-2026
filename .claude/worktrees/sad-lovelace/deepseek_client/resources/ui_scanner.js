/**
 * DeepSeek UI Scanner v1.1
 * Recorre el DOM buscando elementos interactivos y reporta TODOS sus metadatos al proxy.
 */
(function () {
    'use strict';

    function getUniqueSelector(el) {
        if (!el || el.nodeType !== Node.ELEMENT_NODE) return null;
        if (el.id) return `#${el.id}`;

        const testId = el.getAttribute('data-testid');
        if (testId) return `[data-testid="${testId}"]`;

        let path = [];
        let current = el;
        while (current && current.parentElement) {
            let selector = current.tagName.toLowerCase();
            if (current.className) {
                const classes = current.className.split(/\s+/).filter(c => c && !/^\d/.test(c) && !c.includes(':'));
                if (classes.length) selector += '.' + classes.slice(0, 1).join('.');
            }
            const siblings = Array.from(current.parentElement.children).filter(s => s.tagName === current.tagName);
            if (siblings.length > 1) {
                selector += `:nth-of-type(${siblings.indexOf(current) + 1})`;
            }
            path.unshift(selector);
            current = current.parentElement;
            if (path.length > 4) break;
        }
        return path.join(' > ');
    }

    function getAllAttributes(el) {
        const attrs = {};
        for (const attr of el.attributes) {
            attrs[attr.name] = attr.value;
        }
        return attrs;
    }

    function getPageMetadata() {
        const meta = {};
        // Capturar todos los meta tags
        document.querySelectorAll('meta').forEach(m => {
            const key = m.getAttribute('name') || m.getAttribute('property') || m.getAttribute('http-equiv');
            if (key) meta[key] = m.getAttribute('content');
        });

        // Capturar enlaces importantes (canonical, icons)
        const links = {};
        document.querySelectorAll('link').forEach(l => {
            const rel = l.getAttribute('rel');
            if (rel) links[rel] = l.getAttribute('href');
        });

        // Capturar JSON-LD (datos estructurados)
        const structuredData = [];
        document.querySelectorAll('script[type="application/ld+json"]').forEach(s => {
            try { structuredData.push(JSON.parse(s.innerText)); } catch (e) { }
        });

        return {
            meta,
            links,
            structuredData,
            lang: document.documentElement.lang,
            scripts_count: document.scripts.length
        };
    }

    function scan() {
        const elements = Array.from(document.querySelectorAll('button, [role="button"], textarea, a, .ds-icon-button, [aria-label], [onclick]'));
        const report = elements.map(el => {
            const rect = el.getBoundingClientRect();
            return {
                tag: el.tagName,
                text: (el.innerText || el.value || '').substring(0, 100).trim(),
                selector: getUniqueSelector(el),
                attributes: getAllAttributes(el),
                visible: rect.width > 0 && rect.height > 0,
                rect: { x: rect.x, y: rect.y, w: rect.width, h: rect.height },
                computed_style: {
                    display: window.getComputedStyle(el).display,
                    visibility: window.getComputedStyle(el).visibility
                }
            };
        }).filter(item => item.visible);

        const payload = {
            url: window.location.href,
            timestamp: new Date().toISOString(),
            title: document.title,
            page_metadata: getPageMetadata(),
            elements: report,
            html_snapshot: document.documentElement.outerHTML.substring(0, 100000) // 100k para más detalle
        };

        console.log("[UI Scanner] Enviando metadatos completos de " + report.length + " elementos...");

        fetch('/__ui_scan_report', {
            method: 'POST',
            body: JSON.stringify(payload),
            headers: { 'Content-Type': 'application/json' }
        }).catch(err => console.error("[UI Scanner Error]", err));
    }

    setTimeout(scan, 3000);
    setInterval(scan, 15000); // 15s para no saturar tanto con los nuevos datos pesados

    console.log("[DeepSeek UI Scanner] Scanner avanzado v1.1 activo.");
})();
