"""
DeepSeek Client - Cliente no oficial para DeepSeek con anti-detección avanzada.

Este paquete proporciona un cliente para interactuar con DeepSeek (chat.deepseek.com)
de forma programática, con múltiples técnicas de anti-detección para evitar bloqueos.

Uso básico:
    from deepseek_client import DeepSeekClient
    
    with DeepSeekClient() as client:
        response = client.ask("Hola, ¿cómo estás?")
        print(response.content)

Para más información, ver el README o la documentación.
"""

from .config import Config, config, AntiDetectionLevel
from .profiles import (
    HardwareProfile,
    get_profile,
    get_random_profile,
    list_profiles,
    get_profile_info,
    create_custom_profile,
    PROFILES
)
from .fingerprint import (
    FingerprintConfig,
    FingerprintGenerator,
    create_fingerprint_from_profile
)
from .human_behavior import (
    HumanBehavior,
    HumanTyping,
    MouseMovement,
    HumanScroll,
    BezierCurve,
    Point,
    get_action_delay,
    simulate_reading_time
)
from .driver import (
    AntiDetectionDriver,
    create_driver
)
from .driver_pool import (
    DriverPool,
    DriverWrapper,
    get_pool,
    close_pool
)
from .history import (
    HistoryManager,
    Conversation,
    Message,
    create_history_manager
)
from .client import (
    DeepSeekClient,
    DeepSeekModel,
    DeepSeekResponse,
    ResponseState,
    create_client
)


__version__ = "1.0.0"
__author__ = "DeepSeek Client Contributors"

__all__ = [
    # Configuración
    "Config",
    "config",
    "AntiDetectionLevel",
    
    # Perfiles
    "HardwareProfile",
    "get_profile",
    "get_random_profile",
    "list_profiles",
    "get_profile_info",
    "create_custom_profile",
    "PROFILES",
    
    # Fingerprinting
    "FingerprintConfig",
    "FingerprintGenerator",
    "create_fingerprint_from_profile",
    
    # Comportamiento humano
    "HumanBehavior",
    "HumanTyping",
    "MouseMovement",
    "HumanScroll",
    "BezierCurve",
    "Point",
    "get_action_delay",
    "simulate_reading_time",
    
    # Driver
    "AntiDetectionDriver",
    "create_driver",
    
    # Pool
    "DriverPool",
    "DriverWrapper",
    "get_pool",
    "close_pool",
    
    # Historial
    "HistoryManager",
    "Conversation",
    "Message",
    "create_history_manager",
    
    # Cliente
    "DeepSeekClient",
    "DeepSeekModel",
    "DeepSeekResponse",
    "ResponseState",
    "create_client",
]
