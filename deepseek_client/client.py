"""
Cliente principal para DeepSeek.

Este módulo proporciona la clase principal para interactuar con
DeepSeek (chat.deepseek.com) de forma programática.

Características:
    - Chat conversacional
    - Soporte para historial
    - Subida de archivos/imagenes (si está disponible)
    - Manejo de reintentos
    - Detección de rate limiting
"""

import re
import os
import json
import time
import random
import logging
from typing import Optional, List, Dict, Any, Generator, Callable
from dataclasses import dataclass
from enum import Enum

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementNotInteractableException
)

from .config import Config, config
from .driver import AntiDetectionDriver, create_driver
from .history import HistoryManager, Conversation, Message
from .human_behavior import get_action_delay, simulate_reading_time


class DeepSeekModel(Enum):
    """Modelos disponibles en DeepSeek."""
    DEEPSEEK_CHAT = "deepseek-chat"
    DEEPSEEK_REASONER = "deepseek-reasoner"


class ResponseState(Enum):
    """Estados de la respuesta."""
    WAITING = "waiting"
    GENERATING = "generating"
    COMPLETED = "completed"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


@dataclass
class DeepSeekResponse:
    """
    Respuesta de DeepSeek.
    
    Attributes:
        content: Contenido de la respuesta
        model: Modelo usado
        state: Estado de la respuesta
        thinking: Pensamiento del modelo (si disponible)
        metadata: Metadatos adicionales
    """
    content: str = ""
    model: str = ""
    state: ResponseState = ResponseState.COMPLETED
    thinking: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def is_complete(self) -> bool:
        """Indica si la respuesta está completa."""
        return self.state == ResponseState.COMPLETED
    
    @property
    def is_error(self) -> bool:
        """Indica si hubo un error."""
        return self.state == ResponseState.ERROR


class DeepSeekClient:
    """
    Cliente para interactuar con DeepSeek.
    
    Este cliente automatiza la interacción con chat.deepseek.com
    usando un navegador controlado con anti-detección.
    
    Uso básico:
        client = DeepSeekClient()
        response = client.ask("¿Cuál es la capital de Francia?")
        print(response.content)
        
        # Con historial
        client.ask("¿Y su población?", continue_conversation=True)
    """
    
    # Selectores para DeepSeek (Actualizados Marzo 2026)
    SELECTORS = {
        # Input de chat
        'chat_input': (By.ID, 'chat-input'),
        'chat_input_fallback': (By.CSS_SELECTOR, 'textarea._27c9245, textarea[placeholder*="DeepSeek"]'),
        
        # Botón de enviar
        'send_button': (By.CSS_SELECTOR, 'div.d4910adc, button.d4910adc'),
        'send_button_fallback': (By.CSS_SELECTOR, 'div[aria-label="Send"], button:has(svg)'),

        # Respuesta y Pensamiento
        'message_bubble': (By.CSS_SELECTOR, 'div.ds-message._63c77b1'),
        'response_markdown': (By.CSS_SELECTOR, 'div.ds-markdown'),
        'thinking_content': (By.CSS_SELECTOR, 'div.e1675d8b.ds-think-content'),
        
        # Modos (DeepThink / Search)
        'deepthink_toggle': (By.CSS_SELECTOR, 'div._2bd7b35:nth-child(1)'), # Ajustado según coordenadas
        'search_toggle': (By.CSS_SELECTOR, 'div._2bd7b35:nth-child(2)'),
        
        # Estado
        'generating_indicator': (By.CSS_SELECTOR, '.ds-icon--loading, .ds-m-stop-button'),
        'stop_button': (By.CSS_SELECTOR, '.ds-m-stop-button'),
        
        # Errores
        'error_container': (By.CSS_SELECTOR, '.ds-error-message, [role="alert"]'),
    }
    
    def __init__(
        self,
        config_obj: Optional[Config] = None,
        profile_name: Optional[str] = None,
        headless: Optional[bool] = None,
        auto_login: bool = True,
        history_manager: Optional[HistoryManager] = None
    ):
        """
        Inicializa el cliente de DeepSeek.
        
        Args:
            config_obj: Configuración personalizada
            profile_name: Nombre del perfil de hardware
            headless: Si ejecutar en modo headless
            auto_login: Si navegar automáticamente a DeepSeek
            history_manager: Gestor de historial personalizado
        """
        self.config = config_obj or config
        
        # Override headless si se especifica
        if headless is not None:
            self.config.headless = headless
        
        self.logger = self.config.setup_logging()
        
        # Crear driver
        self.driver = create_driver(
            profile_name=profile_name,
            config_obj=self.config
        )
        
        # Gestor de historial
        self.history = history_manager or HistoryManager(self.config.history_dir)
        
        # Estado
        self._is_logged_in = False
        self._current_model = DeepSeekModel.DEEPSEEK_CHAT
        self._last_response: Optional[DeepSeekResponse] = None
        self._conversation_started = False
        
        self.api_headers = {
            "x-app-version": "20241129.1",
            "x-client-version": "1.7.0",
            "x-client-platform": "web"
        }
        
        # Intentar cargar credenciales desde .env
        self.saved_user_token = os.getenv("DEEPSEEK_USER_TOKEN")
        self.saved_waf_token = os.getenv("DEEPSEEK_WAF_TOKEN")
        self.saved_smid_v2 = os.getenv("DEEPSEEK_SMIDV2")
        
        # Navegar a DeepSeek
        if auto_login:
            self._navigate_to_deepseek()
    
    def _navigate_to_deepseek(self):
        """Navega a DeepSeek y espera a que cargue."""
        self.logger.info(f"Navegando a {self.config.deepseek_url}")
        
        self.driver.get(self.config.deepseek_url)
        
        # Esperar a que cargue la página
        try:
            WebDriverWait(self.driver.driver, 30).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # Esperar a que aparezca el input de chat o aplicar auth
            if self.saved_user_token and self.saved_waf_token:
                try:
                    self._apply_saved_auth()
                    self.driver.driver.refresh()
                    self._wait_for_chat_input(timeout=15)
                except Exception as e:
                    self.logger.warning(f"Error aplicando autenticación: {e}")
            else:
                self._wait_for_chat_input(timeout=30)
            
            self._is_logged_in = True
            self.logger.info("Página de DeepSeek cargada correctamente")
            
        except Exception as e:
            self.logger.error(f"FALLO EN NAVEGACIÓN: {e}")
            print(f"\n[!] Error al navegar: {e}")
            print("[!] El navegador permanecerá abierto para diagnóstico.")
    
    def _apply_saved_auth(self):
        """Inyecta cookies y localStorage para bypass de autenticación."""
        self.logger.info("Aplicando credenciales maestras (Cookies + LocalStorage)...")
        domain = "chat.deepseek.com"
        
        # 1. Cookies para WAF y sesión
        cookies = [
            {"name": "aws-waf-token", "value": self.saved_waf_token, "domain": domain},
        ]
        if self.saved_smid_v2:
            cookies.append({"name": "smidV2", "value": self.saved_smid_v2, "domain": domain})
        
        for cookie in cookies:
            try:
                self.driver.driver.add_cookie(cookie)
            except Exception as e:
                self.logger.warning(f"Error aplicando cookie {cookie['name']}: {e}")
        
        # 2. LocalStorage para userToken (Crucial en Marzo 2026)
        try:
            # userToken se guarda como un objeto JSON stringificado
            ut_obj = json.dumps({"value": self.saved_user_token, "__version__": "0"})
            js_script = f"localStorage.setItem('userToken', {json.dumps(ut_obj)});"
            self.driver.driver.execute_script(js_script)
            self.logger.info("userToken inyectado en LocalStorage correctamente.")
        except Exception as e:
            self.logger.error(f"Error inyectando LocalStorage: {e}")

    def _wait_for_chat_input(self, timeout: float = 30):
        """Espera a que el input de chat esté disponible."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Intentar diferentes selectores
                for selector_name in ['chat_input', 'chat_input_fallback']:
                    by, value = self.SELECTORS[selector_name]
                    element = self.driver.driver.find_element(by, value)
                    if element and element.is_displayed():
                        return element
            except NoSuchElementException:
                pass
            
            time.sleep(0.5)
        
        raise TimeoutException("No se encontró el input de chat")
    
    def _find_element_safe(self, selector_name: str, timeout: float = 5):
        """Busca un elemento de forma segura."""
        by, value = self.SELECTORS[selector_name]
        try:
            return self.driver.wait_for_element((by, value), timeout)
        except TimeoutException:
            return None
    
    def _get_chat_input(self):
        """Obtiene el elemento de input de chat."""
        for selector_name in ['chat_input', 'chat_input_fallback']:
            element = self._find_element_safe(selector_name, timeout=2)
            if element:
                return element
        
        raise NoSuchElementException("No se pudo encontrar el input de chat")
    
    def _get_send_button(self):
        """Obtiene el botón de enviar."""
        for selector_name in ['send_button', 'send_button_fallback']:
            element = self._find_element_safe(selector_name, timeout=2)
            if element:
                return element
        return None
    
    def _is_generating(self) -> bool:
        """Verifica si el modelo está generando una respuesta."""
        try:
            # Buscar indicador de carga o botón de stop
            loading = self._find_element_safe('generating_indicator', timeout=0.1)
            stop_btn = self._find_element_safe('stop_button', timeout=0.1)
            
            return loading is not None or stop_btn is not None
        except Exception:
            return False
    
    def _wait_for_response(self, timeout: float = None) -> Generator[str, None, None]:
        """
        Espera la respuesta del modelo y la devuelve como stream.
        
        Yields:
            str: Partes de la respuesta
        """
        timeout = timeout or self.config.response_timeout
        start_time = time.time()
        
        last_content = ""
        stable_count = 0
        max_stable_checks = 3  # Número de checks consecutivos sin cambios para considerar completo
        
        while time.time() - start_time < timeout:
            try:
                # Verificar si sigue generando
                is_generating = self._is_generating()
                
                # Obtener contenido actual
                content = self._get_response_content()
                
                # Si hay nuevo contenido, emitir
                if content and len(content) > len(last_content):
                    new_content = content[len(last_content):]
                    yield new_content
                    last_content = content
                    stable_count = 0
                
                # Verificar si la respuesta está completa
                if not is_generating and content:
                    stable_count += 1
                    if stable_count >= max_stable_checks:
                        self.logger.debug("Respuesta completa detectada")
                        break
                
                # Pausa antes del siguiente check
                time.sleep(0.3)
                
            except StaleElementReferenceException:
                # Elemento obsoleto, reintentar
                time.sleep(0.5)
                continue
            except Exception as e:
                self.logger.warning(f"Error esperando respuesta: {e}")
                time.sleep(0.5)
        
        # Devolver contenido final
        if last_content:
            return last_content
        
        raise TimeoutException("Timeout esperando respuesta de DeepSeek")
    
    def _get_response_content(self) -> str:
        """Obtiene el contenido de la respuesta actual (Markdown)."""
        try:
            # Buscar el último mensaje del asistente usando la clase específica
            by, value = self.SELECTORS['message_bubble']
            bubbles = self.driver.driver.find_elements(by, value)
            if not bubbles:
                # Fallback a markdown genérico
                by, value = self.SELECTORS['response_markdown']
                elements = self.driver.driver.find_elements(by, value)
                return elements[-1].text.strip() if elements else ""
            
            # El último bubble es la respuesta actual
            last_bubble = bubbles[-1]
            try:
                # Buscar markdown dentro del bubble (excluyendo el thinking)
                by_md, val_md = self.SELECTORS['response_markdown']
                md_element = last_bubble.find_element(by_md, val_md)
                return md_element.text.strip()
            except NoSuchElementException:
                return last_bubble.text.strip()
            
        except Exception as e:
            self.logger.debug(f"Error obteniendo contenido: {e}")
            return ""
    
    def _get_thinking_content(self) -> str:
        """Obtiene el contenido del 'pensamiento' (DeepThink) si está disponible."""
        try:
            by, value = self.SELECTORS['thinking_content']
            elements = self.driver.driver.find_elements(by, value)
            if elements:
                # Devolver el texto del último bloque de pensamiento
                return elements[-1].text.strip()
            return ""
        except Exception as e:
            self.logger.debug(f"Error obteniendo pensamiento: {e}")
            return ""
    
    def _check_for_errors(self) -> Optional[str]:
        """Verifica si hay mensajes de error o rate limit en la página."""
        try:
            # Buscar mensajes de error usando el contenedor unificado
            error_element = self._find_element_safe('error_container', timeout=0.1)
            if error_element:
                text = error_element.text
                if "rate limit" in text.lower():
                    return "Rate limit detectado"
                return text
                
        except Exception:
            pass
        
        return None
    
    def _send_message(self, message: str) -> None:
        """
        Envía un mensaje a DeepSeek con redundancia ante fallos de UI.
        
        Args:
            message: Mensaje a enviar
        """
        # Intentar el flujo de envío hasta 2 veces si hay elementos stale
        for attempt in range(2):
            try:
                # Obtener input (re-activar si es necesario)
                chat_input = self._get_chat_input()
                
                # Simular escritura humana
                if attempt == 0:
                    self.driver.human_type(chat_input, message, clear_first=True)
                
                # Pequeña pausa antes de enviar
                time.sleep(random.uniform(0.3, 0.6))
                
                # Intentar enviar mediante el botón (usando modo Rápido)
                send_button = self._get_send_button()
                
                if send_button and send_button.is_enabled():
                    try:
                        # Usar velocidad rápida para el botón de envío
                        self.driver.human_click(send_button, speed='fast')
                        time.sleep(0.2)
                    except Exception as e:
                        self.logger.warning(f"Fallo clic rápido, usando Enter: {e}")
                        chat_input.send_keys(Keys.RETURN)
                else:
                    # Usar Enter como fallback primario
                    chat_input.send_keys(Keys.RETURN)
                
                self.logger.info(f"Mensaje enviado (intento {attempt+1})")
                return # Éxito
                
            except Exception as e:
                self.logger.warning(f"Error en envío (intento {attempt+1}): {e}")
                if "stale" in str(e).lower():
                    time.sleep(0.5)
                    continue # Reintentar buscando elementos nuevos
                else:
                    # Otros errores: intentar Enter como último recurso
                    try:
                        self._get_chat_input().send_keys(Keys.RETURN)
                        return
                    except:
                        pass
                if attempt == 1: raise e
    
    def ask(
        self,
        message: str,
        continue_conversation: bool = True,
        model: Optional[DeepSeekModel] = None,
        timeout: float = None,
        stream_callback: Optional[Callable[[str], None]] = None,
        retries: int = None
    ) -> DeepSeekResponse:
        """
        Envía un mensaje a DeepSeek y obtiene la respuesta.
        
        Args:
            message: Mensaje a enviar
            continue_conversation: Si continuar la conversación actual
            model: Modelo a usar (opcional)
            timeout: Timeout personalizado
            stream_callback: Callback para streaming
            retries: Número de reintentos
        
        Returns:
            DeepSeekResponse: Respuesta del modelo
        """
        retries = retries or self.config.retry_attempts
        last_error = None
        
        for attempt in range(retries):
            try:
                return self._ask_impl(
                    message=message,
                    continue_conversation=continue_conversation,
                    model=model,
                    timeout=timeout,
                    stream_callback=stream_callback
                )
            except Exception as e:
                last_error = e
                self.logger.warning(f"Intento {attempt + 1} fallido: {e}")
                
                # Verificar si es rate limit
                error_msg = str(e).lower()
                if 'rate' in error_msg or 'limit' in error_msg:
                    # Esperar más tiempo para rate limits
                    wait_time = self.config.retry_delay * (2 ** attempt) * 2
                    self.logger.info(f"Rate limit detectado, esperando {wait_time}s")
                    time.sleep(wait_time)
                else:
                    # Delay normal con backoff
                    wait_time = self.config.retry_delay * (2 ** attempt)
                    time.sleep(wait_time)
                    
                    # Reintentar navegación si es necesario
                    if not self._is_logged_in:
                        self._navigate_to_deepseek()
        
        # Si todos los intentos fallan
        return DeepSeekResponse(
            content="",
            state=ResponseState.ERROR,
            metadata={"error": str(last_error)}
        )
    
    def _ask_impl(
        self,
        message: str,
        continue_conversation: bool,
        model: Optional[DeepSeekModel],
        timeout: float,
        stream_callback: Optional[Callable[[str], None]]
    ) -> DeepSeekResponse:
        """Implementación interna de ask()."""
        
        # Verificar si necesitamos nueva conversación
        if not continue_conversation and self._conversation_started:
            self.new_conversation()
        
        # Cambiar modelo si es necesario
        if model and model != self._current_model:
            self._switch_model(model)
        
        # Verificar errores antes de enviar
        error = self._check_for_errors()
        if error:
            raise Exception(f"Error detectado: {error}")
        
        # Enviar mensaje
        self._send_message(message)
        self._conversation_started = True
        
        # Guardar mensaje del usuario en historial
        self.history.current_conversation.add_message(
            role="user",
            content=message
        )
        
        # Esperar y recopilar respuesta
        full_response = ""
        thinking = ""
        
        for chunk in self._wait_for_response(timeout):
            if stream_callback:
                stream_callback(chunk)
            full_response += chunk
        
        # Obtener thinking si está disponible
        thinking = self._get_thinking_content()
        
        # Crear respuesta
        response = DeepSeekResponse(
            content=full_response,
            model=self._current_model.value,
            state=ResponseState.COMPLETED,
            thinking=thinking,
            metadata={
                "conversation_id": self.history.current_conversation.id
            }
        )
        
        # Guardar respuesta en historial
        self.history.current_conversation.add_message(
            role="assistant",
            content=full_response,
            metadata={"thinking": thinking, "model": self._current_model.value}
        )
        
        self._last_response = response
        return response
    
    def ask_stream(
        self,
        message: str,
        continue_conversation: bool = True,
        timeout: float = None
    ) -> Generator[str, None, None]:
        """
        Envía un mensaje y devuelve la respuesta como stream.
        
        Args:
            message: Mensaje a enviar
            continue_conversation: Si continuar la conversación
            timeout: Timeout personalizado
        
        Yields:
            str: Partes de la respuesta
        """
        # Verificar si necesitamos nueva conversación
        if not continue_conversation and self._conversation_started:
            self.new_conversation()
        
        # Enviar mensaje
        self._send_message(message)
        self._conversation_started = True
        
        # Guardar mensaje del usuario
        self.history.current_conversation.add_message(
            role="user",
            content=message
        )
        
        # Stream de respuesta
        full_response = ""
        for chunk in self._wait_for_response(timeout):
            full_response += chunk
            yield chunk
        
        # Guardar respuesta completa
        self.history.current_conversation.add_message(
            role="assistant",
            content=full_response
        )
    
    def new_conversation(self):
        """Inicia una nueva conversación."""
        self.logger.info("Iniciando nueva conversación")
        
        # Guardar conversación actual si existe
        if self.history.current_conversation.messages:
            self.history.save_conversation()
        
        # Crear nueva conversación
        self.history.new_conversation()
        
        # Click en nuevo chat si está disponible
        new_chat_btn = self._find_element_safe('new_chat_button', timeout=2)
        if new_chat_btn:
            try:
                self.driver.human_click(new_chat_btn)
                time.sleep(1)
            except Exception:
                # Recargar página como fallback
                self.driver.refresh()
        
        self._conversation_started = False
        self._last_response = None
    
    def _switch_model(self, model: DeepSeekModel):
        """Cambia el modelo de DeepSeek."""
        self.logger.info(f"Cambiando a modelo: {model.value}")
        
        try:
            # Buscar selector de modelo
            model_selector = self._find_element_safe('model_selector', timeout=3)
            
            if model_selector:
                self.driver.human_click(model_selector)
                time.sleep(0.5)
                
                # Buscar opción del modelo
                # Esto depende de la estructura específica de DeepSeek
                model_option = self.driver.find_element_safe(
                    (By.XPATH, f'//*[contains(text(), "{model.value}")]')
                )
                
                if model_option:
                    self.driver.human_click(model_option)
                    self._current_model = model
            
        except Exception as e:
            self.logger.warning(f"Error cambiando modelo: {e}")
    
    def upload_file(self, file_path: str) -> bool:
        """
        Sube un archivo a DeepSeek (si está soportado).
        
        Args:
            file_path: Ruta del archivo
        
        Returns:
            bool: True si se subió correctamente
        """
        self.logger.info(f"Subiendo archivo: {file_path}")
        
        try:
            # Buscar input de archivo
            file_input = self._find_element_safe('file_upload', timeout=3)
            
            if not file_input:
                # Intentar click en botón de attach
                attach_btn = self._find_element_safe('attach_button', timeout=2)
                if attach_btn:
                    self.driver.human_click(attach_btn)
                    time.sleep(0.5)
                    file_input = self._find_element_safe('file_upload', timeout=3)
            
            if file_input:
                file_input.send_keys(file_path)
                time.sleep(2)  # Esperar a que suba
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error subiendo archivo: {e}")
            return False
    
    def get_conversation_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """
        Obtiene el historial de la conversación actual.
        
        Args:
            limit: Número máximo de mensajes
        
        Returns:
            List[Dict]: Historial de mensajes
        """
        messages = self.history.current_conversation.get_last_messages(limit)
        return [m.to_openai_format() for m in messages]
    
    def save_conversation(self, title: str = None) -> str:
        """
        Guarda la conversación actual.
        
        Args:
            title: Título opcional
        
        Returns:
            str: ID de la conversación
        """
        if title:
            self.history.current_conversation.title = title
        
        self.history.save_conversation()
        return self.history.current_conversation.id
    
    def load_conversation(self, conversation_id: str) -> bool:
        """
        Carga una conversación guardada.
        
        Args:
            conversation_id: ID de la conversación
        
        Returns:
            bool: True si se cargó correctamente
        """
        conversation = self.history.load_conversation(conversation_id)
        return conversation is not None
    
    def list_conversations(self) -> List[Dict[str, Any]]:
        """Lista todas las conversaciones guardadas."""
        return self.history.list_conversations()
    
    def get_screenshot(self, filename: str = None) -> str:
        """Toma una captura de pantalla."""
        return self.driver.get_screenshot(filename)
    
    def close(self):
        """Cierra el cliente y el navegador."""
        self.logger.info("Cerrando cliente DeepSeek")
        
        # Guardar conversación actual
        if self.history.current_conversation.messages:
            self.history.save_conversation()
        
        # Cerrar driver
        self.driver.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __del__(self):
        """Destructor."""
        try:
            self.close()
        except Exception:
            pass


def create_client(
    profile_name: str = None,
    headless: bool = False,
    config_obj: Config = None
) -> DeepSeekClient:
    """
    Función de conveniencia para crear un cliente.
    
    Args:
        profile_name: Nombre del perfil de hardware
        headless: Si ejecutar en modo headless
        config_obj: Configuración personalizada
    
    Returns:
        DeepSeekClient: Cliente configurado
    """
    return DeepSeekClient(
        profile_name=profile_name,
        headless=headless,
        config_obj=config_obj
    )
