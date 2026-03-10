#!/usr/bin/env python3
"""
Servidor API compatible con OpenAI para DeepSeek.

Este módulo proporciona un servidor HTTP que implementa la API de OpenAI,
permitiendo usar DeepSeek con cualquier cliente compatible.

Endpoints:
    POST /v1/chat/completions - Completions de chat
    GET /v1/models - Listar modelos disponibles
    GET /v1/models/{model} - Información de un modelo
    GET /health - Health check

Uso:
    python server.py --port 8000
    
Luego puedes usar con cualquier cliente OpenAI:
    
    from openai import OpenAI
    
    client = OpenAI(
        base_url="http://localhost:8000/v1",
        api_key="dummy"
    )
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": "Hola!"}]
    )
"""

import os
import sys
import json
import time
import uuid
import argparse
import logging
from typing import Optional, List, Dict, Any          # FIX: quitados asyncio y Generator (no usados)
from dataclasses import dataclass, asdict

# Añadir directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from flask import Flask, request, jsonify, Response, stream_with_context
    from flask_cors import CORS
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False
    print("Error: Flask no está instalado. Instala con: pip install flask flask-cors")
    sys.exit(1)

from deepseek_client.config import Config, config
from deepseek_client.client import DeepSeekClient, DeepSeekModel, DeepSeekResponse
from deepseek_client.driver_pool import DriverPool, get_pool
from deepseek_client.history import HistoryManager   # FIX #2: necesario para inicializar client


# Configuración
app = Flask(__name__)
CORS(app)

# Logger
logger = logging.getLogger("deepseek_server")

# Pool de drivers
driver_pool: Optional[DriverPool] = None


# ============================================================================
# Modelos de datos para la API
# ============================================================================

@dataclass
class ChatMessage:
    """Mensaje de chat."""
    role: str
    content: str
    name: Optional[str] = None


@dataclass
class ChatCompletionRequest:
    """Solicitud de completion."""
    model: str
    messages: List[ChatMessage]
    temperature: float = 1.0
    top_p: float = 1.0
    n: int = 1
    stream: bool = False
    stop: Optional[List[str]] = None
    max_tokens: Optional[int] = None
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    user: Optional[str] = None


@dataclass
class ChatCompletionChoice:
    """Opción de completion."""
    index: int
    message: Dict[str, str]
    finish_reason: str


@dataclass
class ChatCompletionResponse:
    """Respuesta de completion."""
    id: str
    object: str = "chat.completion"
    created: int = 0
    model: str = "deepseek-chat"
    choices: List[ChatCompletionChoice] = None
    usage: Dict[str, int] = None
    
    def __post_init__(self):
        if self.created == 0:
            self.created = int(time.time())
        if self.choices is None:
            self.choices = []
        if self.usage is None:
            self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


@dataclass
class ModelInfo:
    """Información de un modelo."""
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "deepseek"
    
    def __post_init__(self):
        if self.created == 0:
            self.created = int(time.time())


# ============================================================================
# Endpoints de la API
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    pool_status = driver_pool.get_status() if driver_pool else {}
    
    return jsonify({
        "status": "healthy",
        "driver_pool": {
            "available": pool_status.get("available_drivers", 0),
            "total": pool_status.get("total_drivers", 0)
        }
    })


@app.route('/v1/models', methods=['GET'])
def list_models():
    """Lista los modelos disponibles."""
    models = [
        ModelInfo(id="deepseek-chat"),
        ModelInfo(id="deepseek-reasoner"),
    ]
    
    return jsonify({
        "object": "list",
        "data": [asdict(m) for m in models]
    })


@app.route('/v1/models/<model_id>', methods=['GET'])
def get_model(model_id: str):
    """Obtiene información de un modelo específico."""
    if model_id not in ["deepseek-chat", "deepseek-reasoner"]:
        return jsonify({"error": f"Modelo no encontrado: {model_id}"}), 404
    
    model = ModelInfo(id=model_id)
    return jsonify(asdict(model))


@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    # FIX #1: guard — pool puede ser None si el servidor arrancó sin initialize_pool()
    if driver_pool is None:
        return jsonify({"error": "Driver pool no inicializado"}), 503

    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body requerido"}), 400

        messages = data.get('messages', [])
        if not messages:
            return jsonify({"error": "Messages requerido"}), 400

        model = data.get('model', 'deepseek-chat')
        stream = data.get('stream', False)

        # FIX #3: conversation_history era construido pero nunca usado por el cliente.
        # El contexto de conversación lo mantiene el browser en la sesión de Selenium.
        # Solo necesitamos el último mensaje de usuario.
        user_message = None
        for msg in messages:
            if msg.get('role') == 'user':
                user_message = msg.get('content', '')

        if not user_message:
            return jsonify({"error": "No se encontró mensaje de usuario"}), 400

        logger.info(f"Recibida solicitud: model={model}, stream={stream}, msg_len={len(user_message)}")

        if stream:
            return stream_response(user_message, model)
        else:
            return complete_response(user_message, model)

    except Exception as e:
        logger.error(f"Error en chat_completions: {e}")
        return jsonify({"error": str(e)}), 500


def _build_client(driver) -> DeepSeekClient:
    """
    FIX #2: construye un DeepSeekClient válido reutilizando un driver del pool.
    __new__ bypasea __init__, por lo que hay que inicializar todos los atributos
    que _ask_impl() necesita para no lanzar AttributeError.
    """
    client = DeepSeekClient.__new__(DeepSeekClient)
    client.driver = driver
    client.config = config
    client.logger = logger
    client.history = HistoryManager(config.history_dir)
    client._is_logged_in = True          # el driver del pool ya tiene sesión activa
    client._current_model = DeepSeekModel.DEEPSEEK_CHAT
    client._last_response = None
    client._conversation_started = False
    client.api_headers = {
        "x-app-version": "20241129.1",
        "x-client-version": "1.7.0",
        "x-client-platform": "web"
    }
    client._interaction_count = 0          # FIX F3-02: necesario para _send_message
    return client


def complete_response(message: str, model: str):          # FIX #3: eliminado param history inutilizado
    try:
        with driver_pool.get_driver() as driver:
            client = _build_client(driver)                # FIX #2: usa helper completo
            response = client.ask(message)

            if response.is_error:
                return jsonify({"error": response.metadata.get("error", "Error desconocido")}), 500

            completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
            completion = ChatCompletionResponse(
                id=completion_id,
                model=model,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message={"role": "assistant", "content": response.content},
                        finish_reason="stop"
                    )
                ],
                usage={
                    "prompt_tokens": len(message) // 4,
                    "completion_tokens": len(response.content) // 4,
                    "total_tokens": (len(message) + len(response.content)) // 4
                }
            )
            return jsonify(asdict(completion))

    except Exception as e:
        logger.error(f"Error en complete_response: {e}")
        return jsonify({"error": str(e)}), 500


def stream_response(message: str, model: str):            # FIX #3: eliminado param history inutilizado
    def generate():
        try:
            completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"

            initial_chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]
            }
            yield f"data: {json.dumps(initial_chunk)}\n\n"

            with driver_pool.get_driver() as driver:     # FIX #1: driver_pool ya validado arriba
                client = _build_client(driver)            # FIX #2: usa helper completo

                full_content = ""
                for chunk in client.ask_stream(message):
                    full_content += chunk
                    data_chunk = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{"index": 0, "delta": {"content": chunk}, "finish_reason": None}]
                    }
                    yield f"data: {json.dumps(data_chunk)}\n\n"

                final_chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Error en stream_response: {e}")
            yield f"data: {json.dumps({'error': {'message': str(e), 'type': 'internal_error'}})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


# ============================================================================
# Inicialización y arranque
# ============================================================================

def initialize_pool(size: int = 1):
    """
    Inicializa el pool de drivers.
    
    Args:
        size: Tamaño del pool
    """
    global driver_pool
    
    logger.info(f"Inicializando pool de drivers (tamaño: {size})")
    driver_pool = DriverPool(size=size, auto_start=True)
    logger.info("Pool de drivers inicializado")


def shutdown_pool():
    """Cierra el pool de drivers."""
    global driver_pool
    
    if driver_pool:
        logger.info("Cerrando pool de drivers...")
        driver_pool.close()
        driver_pool = None


def create_app(pool_size: int = 1) -> Flask:
    """
    Crea y configura la aplicación Flask.
    
    Args:
        pool_size: Tamaño del pool de drivers
    
    Returns:
        Flask: Aplicación configurada
    """
    initialize_pool(pool_size)
    return app


def main():
    """Punto de entrada principal."""
    parser = argparse.ArgumentParser(
        description="Servidor API compatible con OpenAI para DeepSeek",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python server.py
  python server.py --port 8080 --pool-size 3
  python server.py --host 0.0.0.0 --port 8000

Uso con cliente OpenAI:
  
  from openai import OpenAI
  
  client = OpenAI(
      base_url="http://localhost:8000/v1",
      api_key="dummy"
  )
  
  response = client.chat.completions.create(
      model="deepseek-chat",
      messages=[{"role": "user", "content": "Hola!"}]
  )
        """
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        help='Host para el servidor (default: 127.0.0.1)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Puerto para el servidor (default: 8000)'
    )
    
    parser.add_argument(
        '--pool-size',
        type=int,
        default=1,
        help='Tamaño del pool de drivers (default: 1)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Ejecutar en modo debug'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Nivel de logging'
    )
    
    args = parser.parse_args()
    
    # Configurar logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Banner
    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║     DeepSeek API Server - Compatible with OpenAI SDK      ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  Server: http://{args.host}:{args.port}
    ║  Pool Size: {args.pool_size}
    ║  Log Level: {args.log_level}
    ╠═══════════════════════════════════════════════════════════╣
    ║  Endpoints:                                               ║
    ║    POST /v1/chat/completions                              ║
    ║    GET  /v1/models                                        ║
    ║    GET  /health                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Inicializar pool
        initialize_pool(args.pool_size)
        
        # Ejecutar servidor
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            threaded=True
        )
    
    finally:
        shutdown_pool()


if __name__ == "__main__":
    main()
