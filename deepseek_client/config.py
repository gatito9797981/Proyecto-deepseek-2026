"""
Configuración del cliente DeepSeek mediante variables de entorno.

Este módulo gestiona toda la configuración del proyecto, permitiendo
personalizar el comportamiento del cliente mediante variables de entorno
o valores por defecto seguros.

Variables de entorno soportadas:
    - ANTI_DETECTION_LEVEL: Nivel de anti-detección (basic, standard, full)
    - FINGERPRINT_PROFILE: Perfil de fingerprint (random o nombre específico)
    - DRIVER_POOL_SIZE: Tamaño del pool de drivers (default: 1)
    - DEEPSEEK_URL: URL de DeepSeek (default: https://chat.deepseek.com)
    - HEADLESS: Ejecutar en modo headless (true/false, default: false)
    - USE_XVFB: Usar Xvfb en Linux (true/false, default: false)
    - LOG_LEVEL: Nivel de logging (DEBUG, INFO, WARNING, ERROR, default: INFO)
    - PAGE_LOAD_TIMEOUT: Timeout carga de página en segundos (default: 60)
    - ELEMENT_WAIT_TIMEOUT: Timeout espera de elementos en segundos (default: 30)
    - RESPONSE_TIMEOUT: Timeout de respuesta en segundos (default: 300)
    - RETRY_ATTEMPTS: Número de reintentos ante errores (default: 3)
    - RETRY_DELAY: Delay base entre reintentos en segundos (default: 5.0)
    - RETRY_BACKOFF: Multiplicador exponencial de reintentos (default: 2.0)
    - TYPING_SPEED_MEAN: Velocidad media de escritura en ms/carácter (default: 50)
    - TYPING_SPEED_STD: Desviación estándar de escritura en ms (default: 20)
    - TYPING_ERROR_RATE: Tasa de errores de escritura 0.0-1.0 (default: 0.02)
    - MOUSE_SPEED: Multiplicador de velocidad del ratón (default: 1.0)
"""

import os
import logging
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()


class AntiDetectionLevel(Enum):
    """Niveles de anti-detección disponibles."""
    BASIC = "basic"
    STANDARD = "standard"
    FULL = "full"


@dataclass
class Config:
    anti_detection_level: AntiDetectionLevel = AntiDetectionLevel.FULL
    fingerprint_profile: str = "work_laptop"
    driver_pool_size: int = 1
    deepseek_url: str = "https://chat.deepseek.com"
    headless: bool = False
    use_xvfb: bool = False
    log_level: str = "INFO"
    typing_speed_mean: float = 50.0
    typing_speed_std: float = 20.0
    mouse_speed: float = 1.0
    typing_error_rate: float = 0.02
    retry_attempts: int = 3
    retry_delay: float = 5.0
    retry_backoff: float = 2.0
    page_load_timeout: int = 60
    element_wait_timeout: int = 30
    response_timeout: int = 300
    # Directorios — relativos al módulo, no al CWD del proceso
    profile_dir: str = field(default_factory=lambda: str(Path(__file__).parent / "browser_profiles"))
    screenshot_dir: str = field(default_factory=lambda: str(Path(__file__).parent / "screenshots"))
    history_dir: str = field(default_factory=lambda: str(Path(__file__).parent / "chat_history"))
    proxy: Optional[str] = None

    @classmethod
    def from_env(cls) -> "Config":
        """
        Crea una configuración desde variables de entorno.

        Returns:
            Config: Instancia de configuración con valores de entorno.
        """
        level_map = {
            "basic": AntiDetectionLevel.BASIC,
            "standard": AntiDetectionLevel.STANDARD,
            "full": AntiDetectionLevel.FULL,
        }
        level_str = os.getenv("ANTI_DETECTION_LEVEL", "full").lower()
        anti_detection_level = level_map.get(level_str, AntiDetectionLevel.FULL)

        def _float(key: str, default: float) -> float:
            try:
                return float(os.getenv(key, str(default)))
            except ValueError:
                return default

        def _int(key: str, default: int) -> int:
            try:
                return int(os.getenv(key, str(default)))
            except ValueError:
                return default

        def _bool(key: str, default: bool) -> bool:
            return os.getenv(key, str(default)).lower() == "true"

        return cls(
            anti_detection_level=anti_detection_level,
            fingerprint_profile=os.getenv("FINGERPRINT_PROFILE", "work_laptop"),
            driver_pool_size=_int("DRIVER_POOL_SIZE", 1),
            deepseek_url=os.getenv("DEEPSEEK_URL", "https://chat.deepseek.com"),
            headless=_bool("HEADLESS", False),
            use_xvfb=_bool("USE_XVFB", False),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            page_load_timeout=_int("PAGE_LOAD_TIMEOUT", 60),
            element_wait_timeout=_int("ELEMENT_WAIT_TIMEOUT", 30),
            response_timeout=_int("RESPONSE_TIMEOUT", 300),
            retry_attempts=_int("RETRY_ATTEMPTS", 3),
            retry_delay=_float("RETRY_DELAY", 5.0),
            retry_backoff=_float("RETRY_BACKOFF", 2.0),
            typing_speed_mean=_float("TYPING_SPEED_MEAN", 50.0),
            typing_speed_std=_float("TYPING_SPEED_STD", 20.0),
            typing_error_rate=_float("TYPING_ERROR_RATE", 0.02),
            mouse_speed=_float("MOUSE_SPEED", 1.0),
        )

    def setup_logging(self) -> logging.Logger:
        logger = logging.getLogger("deepseek_client")
        logger.setLevel(getattr(logging, self.log_level, logging.INFO))
        logger.propagate = False  # Evitar duplicados si el root logger tiene handlers
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def ensure_directories(self) -> None:
        for directory in [self.profile_dir, self.screenshot_dir, self.history_dir]:
            os.makedirs(directory, exist_ok=True)


config = Config.from_env()