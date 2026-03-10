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
from .token_manager import TokenManager


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

    # Selectores para DeepSeek (Verificados Exhaustivamente Marzo 2026)
    SELECTORS = {
        # Input de chat (Clase exacta detectada)
        'chat_input': (By.CSS_SELECTOR, 'textarea._27c9245'),
        'chat_input_fallback': (By.TAG_NAME, 'textarea'),

        # Botón de enviar (Verificado: _7436101, pierde .disabled al escribir)
        'send_button': (By.CSS_SELECTOR, 'div._7436101[role="button"]'),
        
        # Respuesta y Pensamiento
        'message_bubble': (By.CSS_SELECTOR, 'div.ds-message._63c77b1'),
        'response_markdown': (By.CSS_SELECTOR, 'div.ds-markdown'),
        'thinking_content': (By.CSS_SELECTOR, 'div.e1675d8b.ds-think-content'),

        # Modos (DeepThink / Search) - Usan la misma clase base
        'toggle_button_base': (By.CSS_SELECTOR, 'div.ds-atom-button'),
        'deepthink_toggle': (By.XPATH, '//div[contains(@class, "ds-atom-button") and contains(., "DeepThink")]'),
        'search_toggle': (By.XPATH, '//div[contains(@class, "ds-atom-button") and contains(., "Search")]'),

        # Otros
        'new_chat_button': (By.CSS_SELECTOR, 'div._5a8ac7a'), # Botón con icono plus "New chat"
        'generating_indicator': (By.CSS_SELECTOR, '.ds-m-stop-button, .ds-icon--loading'), 
        'stop_button': (By.CSS_SELECTOR, '.ds-m-stop-button, [role="button"][aria-label*="stop" i]'),
        'error_container': (By.CSS_SELECTOR, '.ds-error-message, [role="alert"]'),
        'model_selector': (By.CSS_SELECTOR, 'div.e5bf614e'), # Contenedor de iconos de modelo
        'file_upload': (By.CSS_SELECTOR, 'input[type="file"]'),
        
        # Botón de adjuntar (Verificado: f02f0e25, siempre habilitado a la izquierda del enviar)
        'attach_button': (By.CSS_SELECTOR, 'div.f02f0e25[role="button"]'),
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

        if headless is not None:
            self.config.headless = headless

        self.logger = self.config.setup_logging()

        self.driver = create_driver(
            profile_name=profile_name,
            config_obj=self.config
        )

        self.history = history_manager or HistoryManager(self.config.history_dir)

        self._is_logged_in = False
        self._current_model = DeepSeekModel.DEEPSEEK_CHAT
        self._last_response: Optional[DeepSeekResponse] = None
        self._conversation_started = False
        self._interaction_count = 0  # <--- Trust Score para Bypass JS

        self.api_headers = {
            "x-app-version": "20241129.1",
            "x-client-version": "1.7.0",
            "x-client-platform": "web"
        }

        self.token_manager = TokenManager(
            driver=self.driver.driver, # Raw Selenium WebDriver
            logger=self.logger,
            alert_callback=self._handle_token_alert
        )

        if auto_login:
            self._navigate_to_deepseek()

    def _handle_token_alert(self, message: str):
        """Callback ejecutado por el TokenManager si la sesión está en peligro."""
        self.logger.critical(message)
        print(f"\n\033[91m{message}\033[0m\n")

    def _navigate_to_deepseek(self):
        """Navega a DeepSeek de forma optimizada."""
        try:
            self.logger.info(f"Navegando a {self.config.deepseek_url}")
            self.driver.get(self.config.deepseek_url)
            
            # Esperar a que la página cargue y detecte el input
            # No intentamos inyectar ya que el perfil deepseek_main mantiene la sesión
            self._wait_for_chat_input(timeout=30)
            self._is_logged_in = True
            self.logger.info("DeepSeek cargado y sesión detectada correctamente")
            
            # Iniciar monitoreo del Token JWT
            self.token_manager.start_monitoring()
            
        except TimeoutException:
            self.logger.warning("No se detectó el chat input. Es posible que se requiera intervención manual.")
        except Exception as e:
            self.logger.error(f"Error crítico en navegación: {e}")
            raise e


    def _wait_for_chat_input(self, timeout: float = 30):
        """Espera a que la página de chat esté lista."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # 1. Intentar por selector de clase detectado (Alta prioridad)
                by, val = self.SELECTORS['chat_input']
                element = self.driver.driver.find_element(by, val)
                if element and element.is_displayed():
                    return element
            except Exception:
                try:
                    # 2. Fallback a cualquier textarea visible
                    elements = self.driver.driver.find_elements(By.TAG_NAME, "textarea")
                    for el in elements:
                        if el.is_displayed():
                            return el
                except Exception:
                    pass
            time.sleep(0.5)

        raise TimeoutException("No se encontró el input de chat después de 30s")

    def _find_element_safe(self, selector_name: str, timeout: float = 5):
        """Busca un elemento de forma segura."""
        by, value = self.SELECTORS[selector_name]
        try:
            return self.driver.wait_for_element((by, value), timeout)
        except TimeoutException:
            return None

    def _find_button_by_heuristics(self, name_patterns: list, role_selector: str = 'button, [role="button"]'):
        """
        Buscador universal de botones por heurística.
        
        Args:
            name_patterns: Lista de strings/regex a buscar en ARIA label o texto
            role_selector: Selector CSS para los elementos potenciales
        """
        try:
            potential_btns = self.driver.driver.find_elements(By.CSS_SELECTOR, role_selector)
            for btn in potential_btns:
                if not btn.is_displayed():
                    continue
                
                # Revisar ARIA, texto y título
                aria = (btn.get_attribute("aria-label") or "").lower()
                text = (btn.text or "").lower()
                title = (btn.get_attribute("title") or "").lower()
                
                for p in name_patterns:
                    p_lower = p.lower()
                    if p_lower in aria or p_lower in text or p_lower in title:
                        if btn.get_attribute("aria-disabled") != "true":
                            return btn
                            
            # Fallback a búsqueda por clases semánticas si no se encontró por nombre
            ds_btns = self.driver.driver.find_elements(By.CLASS_NAME, "ds-icon-button")
            for btn in ds_btns:
                if btn.is_displayed() and btn.get_attribute("aria-disabled") != "true":
                    # Este fallback es arriesgado, usar solo si name_patterns falló
                    pass # Se implementará solo para botones específicos
        except Exception:
            pass
        return None

    def _get_chat_input(self):
        """Obtiene el elemento de input de chat de forma robusta."""
        # 1. Intentar por selectores conocidos
        for selector_name in ['chat_input', 'chat_input_fallback']:
            element = self._find_element_safe(selector_name, timeout=1)
            if element and element.is_displayed():
                return element
        
        # 2. Búsqueda genérica de textarea
        try:
            elements = self.driver.driver.find_elements(By.TAG_NAME, "textarea")
            for el in elements:
                if el.is_displayed():
                    return el
        except Exception:
            pass
            
        raise NoSuchElementException("No se pudo encontrar el input de chat")

    def _get_send_button(self):
        """Obtiene el botón de enviar usando heurística universal."""
        # 1. Intentar por selector directo (que ahora incluye div[role="button"])
        element = self._find_element_safe('send_button', timeout=1)
        if element and element.is_displayed() and element.get_attribute("aria-disabled") != "true":
            return element
            
        # 2. Heurística avanzada
        return self._find_button_by_heuristics(["send", "enviar", "confirmar"])

    def _is_generating(self) -> bool:
        """Detecta generación activa por crecimiento del contenido + DOM."""
        script = """
        try {
            // 1. Buscar botón stop por SVG path (más estable que clases)
            let svgPaths = document.querySelectorAll('path');
            for (let p of svgPaths) {
                let d = p.getAttribute('d') || '';
                // Rectángulo stop de DeepSeek (varias variantes)
                if (d.startsWith('M2') || d.includes('4.88') || d.includes('19.12')) return true;
            }
            
            // 2. Cualquier elemento con clase que contenga "stop" o "loading"
            let all = document.querySelectorAll('[class]');
            for (let el of all) {
                let cls = el.className || '';
                if (typeof cls === 'string' && (
                    cls.includes('stop') || 
                    cls.includes('loading') || 
                    cls.includes('generating') ||
                    cls.includes('blink') ||
                    cls.includes('cursor')
                )) return true;
            }
            
            // 3. Input deshabilitado = está generando
            let textarea = document.querySelector('textarea');
            if (textarea && textarea.disabled) return true;
            
        } catch(e) {}
        return false;
        """
        try:
            return bool(self.driver.driver.execute_script(script))
        except Exception:
            return False

    def _wait_for_response(self, timeout: float = None) -> Generator[str, None, None]:
        """
        Espera la respuesta del modelo y la devuelve como stream entrelazado.

        Yields:
            str: Partes de la respuesta (pensamiento + texto final)
        """
        timeout = timeout or self.config.response_timeout
        start_time = time.time()

        last_content = ""
        last_thinking = ""
        stable_count = 0
        last_growth_time = time.time()  # Track cuándo creció el contenido por última vez
        has_emitted_thinking_header = False
        has_emitted_response_header = False

        time.sleep(1.0)  # Esperar montaje inicial de React

        while time.time() - start_time < timeout:
            try:
                thinking_content = self._get_thinking_content()
                content = self._get_response_content()
                is_gen = self._is_generating()
                
                # 1. Emitir Pensamientos primero (DeepThink)
                if thinking_content and len(thinking_content) > len(last_thinking):
                    if not has_emitted_thinking_header:
                        yield "\n\n🤔 **Pensamiento de DeepSeek:**\n"
                        has_emitted_thinking_header = True
                        
                    new_thinking = thinking_content[len(last_thinking):]
                    yield new_thinking
                    last_thinking = thinking_content
                    stable_count = 0
                    last_growth_time = time.time()
                
                # 2. Emitir Respuesta Final cuando empieza a poblarse
                if content and len(content) > len(last_content):
                    if not has_emitted_response_header:
                        yield "\n\n💡 **Respuesta:**\n"
                        has_emitted_response_header = True
                        
                    new_content = content[len(last_content):]
                    yield new_content
                    last_content = content
                    stable_count = 0
                    last_growth_time = time.time()

                # Solo considerar "terminado" si:
                # 1. JS dice que no genera
                # 2. Contenido no creció en los últimos 4 segundos
                # 3. stable_count acumuló suficiente (3 ticks)
                time_since_growth = time.time() - last_growth_time
                
                if not is_gen and (content or thinking_content) and time_since_growth > 4.0:
                    stable_count += 1
                    if stable_count >= 3:
                        # Flush final por seguridad
                        final_think = self._get_thinking_content()
                        final_content = self._get_response_content()
                        
                        if final_think and len(final_think) > len(last_thinking):
                            yield final_think[len(last_thinking):]
                            
                        if final_content and len(final_content) > len(last_content):
                            yield final_content[len(last_content):]
                        return
                else:
                    # Si sigue generando o creció recientemente, resetear stable
                    if is_gen:
                        stable_count = 0

                time.sleep(0.1)

            except StaleElementReferenceException:
                time.sleep(0.5)
                continue
            except Exception as e:
                self.logger.warning(f"Error esperando respuesta: {e}")
                time.sleep(0.5)

        if not last_content:
            raise TimeoutException("Timeout esperando respuesta de DeepSeek")

    def _get_response_content(self) -> str:
        """Obtiene el contenido de la respuesta actual directamente en V8 (Zero-Latency)."""
        script = """
        try {
            // Buscamos todas las burbujas posibles del asistente
            let allBlocks = Array.from(document.querySelectorAll('.ds-markdown, div[class*="markdown"]'));
            if (allBlocks.length > 0) {
                // Tomar el último gran bloque
                let lastBlock = allBlocks[allBlocks.length - 1];
                
                // Si el bloque está dentro de DeepThink (.ds-think-content), significa que 
                // aún no llega el markdown de respuesta real. Retornamos vacío.
                if (lastBlock.closest('.ds-think-content') || lastBlock.closest('[class*="think"]')) {
                    return "";
                }
                
                return lastBlock.innerText || lastBlock.textContent || "";
            }
        } catch(e) {}
        return "";
        """
        try:
            return str(self.driver.driver.execute_script(script)).strip()
        except:
            return ""

    def _get_thinking_content(self) -> str:
        """Obtiene el contenido del 'pensamiento' (DeepThink R1) desde V8 (Zero-Latency)."""
        script = """
        try {
            // Extracción directa del contenedor especializado del pensamiento R1
            let thinkBlocks = Array.from(document.querySelectorAll('.ds-think-content, [class*="think-content"]'));
            if (thinkBlocks.length > 0) {
                let lastBlock = thinkBlocks[thinkBlocks.length - 1];
                return lastBlock.innerText || lastBlock.textContent || "";
            }
        } catch(e) {}
        return "";
        """
        try:
            return str(self.driver.driver.execute_script(script)).strip()
        except:
            return ""

    def _check_for_errors(self) -> Optional[str]:
        """Verifica si hay mensajes de error o rate limit en la página."""
        try:
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
        Incorpora un Bypass JS "Atómico" de latencia nula si ya hay Trust Score.
        """
        for attempt in range(2):
            try:
                chat_input = self._get_chat_input()
                send_button = self._get_send_button()
                
                # Zero-Latency JS Bypass: Si ya demostramos humanidad 2 veces, inyecar texto atómicamente
                if getattr(self, '_interaction_count', 0) >= 2 and send_button:
                    self.logger.info("🚀 Usando Bypass Atómico JS para escribir sin latencia humana...")
                    script = """
                    let input = arguments[0];
                    let text = arguments[1];
                    let btn = arguments[2];
                    
                    // Rellenar contenido engañando al State de React
                    let nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
                    nativeInputValueSetter.call(input, text);
                    // React 15+ requiere ambos eventos y con bubbles: true
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    
                    // Asegurar que React detecte el cambio de estado antes del clic
                    setTimeout(() => {
                        if (!btn.disabled && btn.getAttribute('aria-disabled') !== 'true') {
                            btn.click();
                        }
                    }, 50);
                    """
                    self.driver.driver.execute_script(script, chat_input, message, send_button)
                    self._interaction_count += 1
                    time.sleep(0.1) # Breve pausa por el setTimeout
                else:
                    self.logger.info(f"Escritura lenta de validación humana en curso... (Trust Score: {getattr(self, '_interaction_count', 0)}/2)")
                    self.driver.human_type(chat_input, message, clear_first=True)
                    time.sleep(random.uniform(0.3, 0.6))
                    send_button = self._get_send_button()
                    if send_button and send_button.is_enabled():
                        try:
                            self.driver.driver.execute_script("arguments[0].click();", send_button)
                            time.sleep(0.3)
                        except Exception as e:
                            self.logger.warning(f"Fallo clic JS, usando Ctrl+Enter: {e}")
                            chat_input.send_keys(Keys.CONTROL, Keys.RETURN)
                    else:
                        # Fallback directo a teclas de envío si no hay botón
                        chat_input.send_keys(Keys.CONTROL, Keys.RETURN)
                        
                    if hasattr(self, '_interaction_count'):
                        self._interaction_count += 1
                
                self.logger.info(f"Mensaje enviado (intento {attempt+1})")
                return
            except Exception as e:
                self.logger.warning(f"Error en envío (intento {attempt+1}): {e}")
                if "stale" in str(e).lower():
                    time.sleep(0.8)
                    continue
                else:
                    try:
                        self._get_chat_input().send_keys(Keys.RETURN)
                        return
                    except Exception:
                        pass
                if attempt == 1:
                    raise e

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

                error_msg = str(e).lower()
                if 'rate' in error_msg or 'limit' in error_msg:
                    # FIX 4: usar config.retry_backoff, no hardcoded 2
                    wait_time = self.config.retry_delay * (self.config.retry_backoff ** attempt) * 2
                    self.logger.info(f"Rate limit detectado, esperando {wait_time}s")
                    time.sleep(wait_time)
                else:
                    wait_time = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                    time.sleep(wait_time)

                    if not self._is_logged_in:
                        self._navigate_to_deepseek()

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

        if not continue_conversation and self._conversation_started:
            self.new_conversation()

        if model and model != self._current_model:
            self._switch_model(model)

        error = self._check_for_errors()
        if error:
            raise Exception(f"Error detectado: {error}")

        self._send_message(message)
        self._conversation_started = True

        self.history.current_conversation.add_message(
            role="user",
            content=message
        )

        full_response = ""          # Respuesta combinada del stream (puede incluir etiquetas visuales)
        for chunk in self._wait_for_response(timeout):
            if stream_callback:
                stream_callback(chunk)
            full_response += chunk

        # FIX F3-01: pensamiento obtenido limpio del DOM (ya se mostró visualmente en stream).
        thinking = self._get_thinking_content()

        # FIX F4-02: guardar en historial SOLO la respuesta pura, sin etiquetas Markdown del stream.
        clean_response = full_response
        separator = "\n\n\U0001f4a1 **Respuesta:**\n"
        if separator in full_response:
            clean_response = full_response.split(separator, 1)[-1]

        response = DeepSeekResponse(
            content=clean_response,
            model=self._current_model.value,
            state=ResponseState.COMPLETED,
            thinking=thinking,
            metadata={"conversation_id": self.history.current_conversation.id}
        )

        self.history.current_conversation.add_message(
            role="assistant",
            content=clean_response,
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
        if not continue_conversation and self._conversation_started:
            self.new_conversation()

        self._send_message(message)
        self._conversation_started = True

        self.history.current_conversation.add_message(
            role="user",
            content=message
        )

        full_response = ""
        for chunk in self._wait_for_response(timeout):
            full_response += chunk
            yield chunk

        self.history.current_conversation.add_message(
            role="assistant",
            content=full_response
        )

    def new_conversation(self):
        """Inicia una nueva conversación."""
        self.logger.info("Iniciando nueva conversación")

        if self.history.current_conversation.messages:
            self.history.save_conversation()
 
        self.history.new_conversation()
        self._interaction_count = 0  # <--- Resetear contador de Bypass JS (Fix 4)
 
        # Intentar encontrar botón de "New Chat" por heurística
        new_chat_btn = self._find_element_safe('new_chat_button', timeout=1) or \
                       self._find_button_by_heuristics(["new chat", "nuevo chat", "iniciar chat"])
                       
        if new_chat_btn:
            try:
                self.driver.human_click(new_chat_btn)
                time.sleep(1)
            except Exception:
                self.driver.refresh()
        else:
            self.driver.refresh()

        self._conversation_started = False
        self._last_response = None

    def _switch_model(self, model: DeepSeekModel):
        """Cambia el modelo de DeepSeek usando heurística universal."""
        self.logger.info(f"Cambiando a modelo: {model.value}")
 
        try:
            # 1. Encontrar el selector de modelo
            model_selector = self._find_element_safe('model_selector', timeout=3) or \
                             self._find_button_by_heuristics(["model", "version", "chat-model"])
 
            if model_selector:
                self.driver.human_click(model_selector)
                time.sleep(0.5)
 
                # 2. Seleccionar la opción
                model_option = self.driver.find_element_safe(
                    (By.XPATH, f'//*[contains(text(), "{model.value}")]')
                ) or self.driver.find_element_safe(
                    (By.XPATH, f'//*[@role="option"][contains(., "{model.value}")]')
                )
 
                if model_option:
                    self.driver.human_click(model_option)
                    self._current_model = model
 
        except Exception as e:
            self.logger.warning(f"Error cambiando modelo: {e}")
 
    def toggle_deepthink(self, enable: bool = True):
        """Activa o desactiva el modo DeepThink (R1)."""
        btn = self._find_element_safe('deepthink_toggle', timeout=2)
        
        if btn:
            # Detectar si está activo por clase de color o aria
            is_active = "checked" in (btn.get_attribute("class") or "") or \
                        "active" in (btn.get_attribute("class") or "") or \
                        btn.get_attribute("aria-checked") == "true"
            
            if is_active != enable:
                self.driver.human_click(btn)
                self.logger.info(f"Modo DeepThink {'activado' if enable else 'desactivado'}")

    def toggle_search(self, enable: bool = True):
        """Activa o desactiva el modo Búsqueda (Search)."""
        btn = self._find_element_safe('search_toggle', timeout=2)
        
        if btn:
            is_active = "checked" in (btn.get_attribute("class") or "") or \
                        "active" in (btn.get_attribute("class") or "") or \
                        btn.get_attribute("aria-checked") == "true"
            
            if is_active != enable:
                self.driver.human_click(btn)
                self.logger.info(f"Modo Búsqueda {'activada' if enable else 'desactivada'}")

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
            # 1. Encontrar input oculto
            file_input = self._find_element_safe('file_upload', timeout=1)
 
            if not file_input:
                # 2. Si no hay input directo, buscar el botón de adjuntar
                attach_btn = self._find_element_safe('attach_button', timeout=1) or \
                             self._find_button_by_heuristics(["attach", "adjuntar", "upload", "file"])
                if attach_btn:
                    self.driver.human_click(attach_btn)
                    time.sleep(0.5)
                    file_input = self._find_element_safe('file_upload', timeout=3)

            if file_input:
                # Desenmascarar el input si está oculto (común en apps web modernas)
                self.driver.driver.execute_script(
                    "arguments[0].style.display = 'block'; arguments[0].style.visibility = 'visible';", 
                    file_input
                )
                time.sleep(0.2)
                file_input.send_keys(file_path)
                time.sleep(2)
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error subiendo archivo: {e}")
            self.cancel_attachment()
            return False

    def cancel_attachment(self):
        """Si el popup de adjuntos se queda abierto bloqueando la página, lo cierra."""
        try:
            self.logger.info("Enviando ESCAPE para cerrar cualquier popup de adjuntos bloqueante...")
            self.driver.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(0.5)
        except Exception as e:
            self.logger.debug(f"Error al intentar cerrar popup: {e}")

    def get_conversation_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """Obtiene el historial de la conversación actual."""
        messages = self.history.current_conversation.get_last_messages(limit)
        return [m.to_openai_format() for m in messages]

    def save_conversation(self, title: str = None) -> str:
        """Guarda la conversación actual."""
        if title:
            self.history.current_conversation.title = title
        self.history.save_conversation()
        return self.history.current_conversation.id

    def load_conversation(self, conversation_id: str) -> bool:
        """Carga una conversación guardada."""
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
        try:
            if hasattr(self, 'token_manager'):
                self.token_manager.stop_monitoring()
        except Exception:
            pass

        # FIX 5: guards para __init__ parcialmente fallido
        try:
            if hasattr(self, 'history') and self.history.current_conversation.messages:
                self.history.save_conversation()
        except Exception:
            pass

        try:
            if hasattr(self, 'driver') and self.driver:
                self.logger.info("Cerrando cliente DeepSeek")
                self.driver.close()
        except Exception:
            pass

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