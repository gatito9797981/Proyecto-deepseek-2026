"""
Configuración del cliente DeepSeek mediante variables de entorno.

Este módulo gestiona toda la configuración del proyecto, permitiendo
personalizar el comportamiento del cliente mediante variables de entorno
o valores por defecto seguros.

Variables de entorno soportadas:
    - ANTI_DETECTION_LEVEL: Nivel de anti-detección (basic, standard, full)
    - FINGERPRINT_PROFILE: Perfil de fingerprint (random o nombre específico)
    - DRIVER_POOL_SIZE: Tamaño del pool de drivers
    - DEEPSEEK_URL: URL de DeepSeek (por defecto: https://chat.deepseek.com)
    - HEADLESS: Ejecutar en modo headless (true/false)
    - USE_XVFB: Usar Xvfb en Linux (true/false)
    - LOG_LEVEL: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
"""

import os
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class AntiDetectionLevel(Enum):
    """Niveles de anti-detección disponibles."""
    BASIC = "basic"
    STANDARD = "standard"
    FULL = "full"


@dataclass
class Config:
    """
    Configuración principal del cliente DeepSeek.
    
    Attributes:
        anti_detection_level: Nivel de anti-detección a aplicar.
        fingerprint_profile: Perfil de hardware a usar.
        driver_pool_size: Número de drivers en el pool.
        deepseek_url: URL base de DeepSeek.
        headless: Si ejecutar en modo headless.
        use_xvfb: Si usar Xvfb en Linux.
        log_level: Nivel de logging.
        typing_speed_mean: Velocidad media de escritura (ms por carácter).
        typing_speed_std: Desviación estándar de velocidad de escritura.
        mouse_speed: Velocidad base del ratón.
        retry_attempts: Número de reintentos ante errores.
        retry_delay: Delay base entre reintentos (segundos).
        page_load_timeout: Timeout de carga de página (segundos).
        element_wait_timeout: Timeout de espera de elementos (segundos).
    """
    
    # Configuración principal
    anti_detection_level: AntiDetectionLevel = AntiDetectionLevel.FULL
    fingerprint_profile: str = "random"
    driver_pool_size: int = 1
    deepseek_url: str = "https://chat.deepseek.com"
    
    # Configuración del navegador
    headless: bool = False
    use_xvfb: bool = False
    
    # Configuración de logging
    log_level: str = "INFO"
    
    # Configuración de comportamiento humano
    typing_speed_mean: float = 50.0  # ms por carácter
    typing_speed_std: float = 20.0
    mouse_speed: float = 1.0  # multiplicador
    typing_error_rate: float = 0.02  # 2% de errores
    
    # Configuración de reintentos
    retry_attempts: int = 3
    retry_delay: float = 5.0
    retry_backoff: float = 2.0  # multiplicador exponencial
    
    # Timeouts
    page_load_timeout: int = 60
    element_wait_timeout: int = 30
    response_timeout: int = 300  # 5 minutos para respuestas largas
    
    # Directorios
    profile_dir: str = field(default_factory=lambda: os.path.join(os.getcwd(), "browser_profiles"))
    screenshot_dir: str = field(default_factory=lambda: os.path.join(os.getcwd(), "screenshots"))
    history_dir: str = field(default_factory=lambda: os.path.join(os.getcwd(), "chat_history"))
    
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
        
        return cls(
            anti_detection_level=anti_detection_level,
            fingerprint_profile=os.getenv("FINGERPRINT_PROFILE", "random"),
            driver_pool_size=int(os.getenv("DRIVER_POOL_SIZE", "1")),
            deepseek_url=os.getenv("DEEPSEEK_URL", "https://chat.deepseek.com"),
            headless=os.getenv("HEADLESS", "false").lower() == "true",
            use_xvfb=os.getenv("USE_XVFB", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )
    
    def setup_logging(self) -> logging.Logger:
        """
        Configura el sistema de logging.
        
        Returns:
            logging.Logger: Logger configurado.
        """
        logger = logging.getLogger("deepseek_client")
        logger.setLevel(getattr(logging, self.log_level, logging.INFO))
        
        # Evitar duplicar handlers
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
        """Crea los directorios necesarios si no existen."""
        for directory in [self.profile_dir, self.screenshot_dir, self.history_dir]:
            os.makedirs(directory, exist_ok=True)


# Instancia global de configuración
config = Config.from_env()
