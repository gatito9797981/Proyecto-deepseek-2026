#!/usr/bin/env python3
"""
Proxy Anthropic -> DeepSeek Server.

Claude Code envía peticiones en formato Anthropic Messages API.
Este proxy las recibe, las traduce al formato OpenAI (chat/completions)
y las reenvía al servidor DeepSeek local en el puerto 8000.

Endpoints implementados:
    POST /v1/messages              -> Anthropic Messages API
    GET  /v1/models               -> Lista de modelos
    GET  /health                  -> Health check
"""

import os
import sys
import json
import time
import uuid
import logging
import argparse
import requests
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS

# Añadir directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
CORS(app)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("anthropic_proxy")

# URL del servidor DeepSeek
DEEPSEEK_SERVER = os.getenv("DEEPSEEK_SERVER_URL", "http://127.0.0.1:8000")


def extract_text_from_content(content) -> str:
    """Extrae texto de un campo content de Anthropic (str o lista de bloques)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    # Ignorar llamadas a herramientas por ahora
                    pass
        return "\n".join(parts)
    return str(content)


def anthropic_to_openai_messages(messages: list) -> list:
    """Convierte mensajes Anthropic a formato OpenAI."""
    openai_msgs = []
    for msg in messages:
        role = msg.get("role", "user")
        content = extract_text_from_content(msg.get("content", ""))
        # Anthropic usa 'assistant', OpenAI también — compatible directo
        openai_msgs.append({"role": role, "content": content})
    return openai_msgs


def openai_to_anthropic_response(openai_resp: dict, model: str) -> dict:
    """Convierte respuesta OpenAI chat/completions a formato Anthropic Messages."""
    choices = openai_resp.get("choices", [])
    content_text = ""
    if choices:
        content_text = choices[0].get("message", {}).get("content", "")

    usage = openai_resp.get("usage", {})
    return {
        "id": f"msg_{uuid.uuid4().hex[:24]}",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": content_text}],
        "model": model,
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0)
        }
    }


@app.route('/health', methods=['GET'])
def health():
    """Health check."""
    try:
        r = requests.get(f"{DEEPSEEK_SERVER}/health", timeout=2)
        backend_ok = r.status_code == 200
    except Exception:
        backend_ok = False
    return jsonify({
        "status": "healthy",
        "backend": "ok" if backend_ok else "not_reachable",
        "backend_url": DEEPSEEK_SERVER
    })


@app.route('/v1/models', methods=['GET'])
def list_models():
    """Lista modelos disponibles en formato Anthropic."""
    return jsonify({
        "data": [
            {"type": "model", "id": "claude-sonnet-4-6", "display_name": "DeepSeek (via proxy)"},
            {"type": "model", "id": "claude-3-5-sonnet-20241022", "display_name": "DeepSeek (via proxy)"},
            {"type": "model", "id": "deepseek-chat", "display_name": "DeepSeek Chat"},
        ]
    })


@app.route('/v1/messages', methods=['POST'])
def messages():
    """
    Endpoint principal: Anthropic Messages API.
    Claude Code llama aquí. Nosotros lo redirigimos a DeepSeek.
    """
    try:
        data = request.get_json() or {}
        model = data.get("model", "deepseek-chat")
        stream = data.get("stream", False)
        max_tokens = data.get("max_tokens", 8096)

        # Sistema
        system = data.get("system", "")

        # Traducir mensajes
        raw_messages = data.get("messages", [])
        openai_messages = []

        if system:
            openai_messages.append({"role": "system", "content": system})

        openai_messages.extend(anthropic_to_openai_messages(raw_messages))

        if not openai_messages:
            return jsonify({"type": "error", "error": {"type": "invalid_request_error", "message": "messages requerido"}}), 400

        # Solo el último mensaje de usuario para resumir
        user_content = next(
            (m["content"] for m in reversed(openai_messages) if m["role"] == "user"), ""
        )
        logger.info(f"[/v1/messages] model={model}, msgs={len(openai_messages)}, user_len={len(user_content)}")

        # Llamar al servidor DeepSeek
        openai_payload = {
            "model": "deepseek-chat",
            "messages": openai_messages,
            "max_tokens": max_tokens,
            "stream": False  # Simplificado: sin streaming por ahora
        }

        try:
            resp = requests.post(
                f"{DEEPSEEK_SERVER}/v1/chat/completions",
                json=openai_payload,
                timeout=300
            )
            resp.raise_for_status()
            openai_resp = resp.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error llamando al servidor DeepSeek: {e}")
            return jsonify({
                "type": "error",
                "error": {
                    "type": "server_error",
                    "message": f"Backend DeepSeek no disponible: {e}"
                }
            }), 502

        # Convertir respuesta al formato Anthropic
        anthropic_resp = openai_to_anthropic_response(openai_resp, model)
        logger.info(f"[/v1/messages] Respuesta OK, output_tokens={anthropic_resp['usage']['output_tokens']}")
        return jsonify(anthropic_resp)

    except Exception as e:
        logger.error(f"[/v1/messages] Error: {e}", exc_info=True)
        return jsonify({
            "type": "error",
            "error": {"type": "server_error", "message": str(e)}
        }), 500


def main():
    parser = argparse.ArgumentParser(description="Proxy Anthropic -> DeepSeek")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4000)
    parser.add_argument("--backend", default="http://127.0.0.1:8000",
                        help="URL del servidor DeepSeek")
    args = parser.parse_args()

    global DEEPSEEK_SERVER
    DEEPSEEK_SERVER = args.backend

    print(f"""
╔════════════════════════════════════════════════════╗
║         Anthropic → DeepSeek Proxy                 ║
╠════════════════════════════════════════════════════╣
║  Proxy:   http://{args.host}:{args.port}
║  Backend: {args.backend}
╠════════════════════════════════════════════════════╣
║  Acepta: POST /v1/messages  (Claude Code)           ║
║  Reenvía a: /v1/chat/completions (DeepSeek srv)     ║
╚════════════════════════════════════════════════════╝
""")

    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
