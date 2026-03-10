"""
Driver de Selenium con anti-detección avanzada.

Este módulo proporciona un WebDriver configurado con múltiples técnicas
de anti-detección para evitar ser detectado como automatización.

Características:
    - Uso de undetected-chromedriver
    - Inyección de scripts de fingerprinting
    - Configuración de argumentos anti-detección
    - Singleton para reutilización del driver
    - Soporte para modo headless y Xvfb
"""

import os
import sys
import time
import random
import tempfile
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
from functools import wraps

# Imports opcionales con fallback
try:
    import undetected_chromedriver as uc
    HAS_UNDETECTED = True
except ImportError:
    from selenium import webdriver
    HAS_UNDETECTED = False
    print("Warning: undetected-chromedriver not installed, using regular selenium")

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    ElementNotInteractableException
)

from .config import Config, config
from .profiles import HardwareProfile, get_profile, get_random_profile
from .fingerprint import FingerprintGenerator, create_fingerprint_from_profile
from .human_behavior import HumanBehavior, get_action_delay


def retry_on_exception(max_retries: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """
    Decorador para reintentar operaciones que fallan.
    
    Args:
        max_retries: Número máximo de reintentos
        delay: Delay entre reintentos en segundos
        exceptions: Tupla de excepciones a capturar
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))  # Backoff exponencial
            raise last_exception
        return wrapper
    return decorator


class AntiDetectionDriver:
    """
    WebDriver con capacidades avanzadas de anti-detección.
    
    Esta clase encapsula la creación y configuración de un WebDriver
    con todas las técnicas de anti-detección implementadas.
    """
    
    _instance: Optional['AntiDetectionDriver'] = None
    _driver = None
    
    def __new__(cls, *args, **kwargs):
        """Implementa patrón singleton opcional."""
        if kwargs.get('singleton', False) and cls._instance is not None:
            return cls._instance
        instance = super().__new__(cls)
        return instance
    
    def __init__(
        self,
        profile: Optional[HardwareProfile] = None,
        config_obj: Optional[Config] = None,
        singleton: bool = False,
        profile_id: Optional[str] = None
    ):
        """
        Inicializa el driver con anti-detección.
        
        Args:
            profile: Perfil de hardware a usar
            config_obj: Configuración personalizada
            singleton: Si usar patrón singleton
            profile_id: ID para el perfil de Chrome
        """
        self.config = config_obj or config
        self.logger = self.config.setup_logging()
        
        # Seleccionar perfil
        if profile:
            self.profile = profile
        elif self.config.fingerprint_profile == "random":
            self.profile = get_random_profile()
        else:
            self.profile = get_profile(self.config.fingerprint_profile) or get_random_profile()
        
        self.logger.info(f"Usando perfil de hardware: {self.profile.name}")
        
        # Crear generador de fingerprint
        self.fingerprint_gen = create_fingerprint_from_profile(
            self.profile.to_dict(),
            self.config.anti_detection_level.value
        )
        
        # ID único para el perfil
        self.profile_id = profile_id or f"deepseek_{random.randint(1000, 9999)}"
        
        # Comportamiento humano
        self.human = HumanBehavior()
        
        # Estado
        self._is_initialized = False
        self._current_url = None
        
        # Inicializar driver si no es singleton o si es la primera vez
        if not singleton or AntiDetectionDriver._driver is None:
            self._driver = self._create_driver()
            if singleton:
                AntiDetectionDriver._driver = self._driver
                AntiDetectionDriver._instance = self
    
    def _create_driver(self):
        """
        Crea y configura el WebDriver con anti-detección.
        
        Returns:
            WebDriver: Driver configurado
        """
        self.logger.info("Creando WebDriver con anti-detección...")
        
        # Configurar opciones
        options = self._get_chrome_options()
        
        # Crear driver
        try:
            if HAS_UNDETECTED:
                driver = self._create_undetected_driver(options)
            else:
                driver = self._create_standard_driver(options)
            
            # Configurar timeouts
            driver.set_page_load_timeout(self.config.page_load_timeout)
            driver.implicitly_wait(5)
            
            # Inyectar scripts de fingerprinting
            self._inject_fingerprint_scripts(driver)
            
            self._is_initialized = True
            self.logger.info("WebDriver creado exitosamente")
            
            return driver
            
        except Exception as e:
            self.logger.error(f"Error creando WebDriver: {e}")
            raise
    
    def _get_chrome_options(self) -> Options:
        """
        Configura las opciones de Chrome para anti-detección.
        
        Returns:
            Options: Opciones configuradas
        """
        options = Options()
        
        # Argumentos de anti-detección básicos
        anti_detection_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-infobars',
            '--disable-dev-shm-usage',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-popup-blocking',
            '--disable-notifications',
            '--disable-translate',
            '--disable-plugins-discovery',
            '--disable-hang-monitor',
            '--disable-prompt-on-repost',
            '--disable-client-side-phishing-detection',
            '--disable-component-update',
            '--disable-default-apps',
            '--disable-extensions-file-access-check',
            '--disable-extensions-http-throttling',
            '--disable-extensions-silent-update',
            '--disable-sync',
            '--disable-background-networking',
            '--metrics-recording-only',
            '--safebrowsing-disable-auto-update',
            '--password-store=basic',
            '--use-mock-keychain',
            '--disable-features=IsolateOrigins,site-per-process',
            '--enable-features=NetworkService,NetworkServiceInProcess',
        ]
        
        for arg in anti_detection_args:
            options.add_argument(arg)
        
        # Configurar user agent
        options.add_argument(f'--user-agent={self.profile.user_agent}')
        
        # Configurar idioma
        lang = self.profile.languages[0] if self.profile.languages else 'en-US'
        options.add_argument(f'--lang={lang}')
        
        # Configurar ventana
        if not self.config.headless:
            window_size = f'--window-size={self.profile.screen_width},{self.profile.screen_height}'
            options.add_argument(window_size)
        
        # Modo headless (con precaución)
        if self.config.headless:
            self.logger.info("Ejecutando en modo headless")
            options.add_argument('--headless=new')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
        
        # Preferencias adicionales
        prefs = {
            'profile.default_content_setting_values.notifications': 2,
            'profile.default_content_setting_values.geolocation': 2,
            'profile.default_content_setting_values.media_stream': 2,
            'credentials_enable_service': False,
            'profile.password_manager_enabled': False,
            'plugins.always_open_pdf_externally': True,
            'safebrowsing.enabled': False,
        }
        options.add_experimental_option('prefs', prefs)
        
        # Habilitar logs de consola para captura de datos espía
        options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
        
        # Directorio de perfil de usuario (para persistir cookies)
        profile_dir = os.path.join(self.config.profile_dir, self.profile_id)
        os.makedirs(profile_dir, exist_ok=True)
        options.add_argument(f'--user-data-dir={profile_dir}')
        
        return options
    
    def _create_undetected_driver(self, options: Options):
        """
        Crea un driver usando undetected-chromedriver.
        
        Args:
            options: Opciones de Chrome
        
        Returns:
            WebDriver: Driver de undetected_chromedriver
        """
        self.logger.info("Usando undetected-chromedriver")
        
        # Configuración específica de undetected
        driver = uc.Chrome(
            options=options,
            use_subprocess=True,  # Usar subproceso para mejor conexión en Windows
            patcher_force_close=False,
            version_main=145,
        )
        
        return driver
    
    def _create_standard_driver(self, options: Options):
        """
        Crea un driver estándar de Selenium como fallback.
        
        Args:
            options: Opciones de Chrome
        
        Returns:
            WebDriver: Driver estándar de Selenium
        """
        self.logger.warning("Usando Selenium estándar (menor anti-detección)")
        
        from selenium.webdriver.chrome.service import Service
        
        # Intentar encontrar ChromeDriver
        try:
            service = Service()
            driver = webdriver.Chrome(service=service, options=options)
        except Exception:
            # Fallback a Chrome directo
            driver = webdriver.Chrome(options=options)
        
        # Ejecutar script CDP para anti-detección adicional
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': self.fingerprint_gen.generate_webdriver_script()
        })
        
        return driver
    
    def _inject_fingerprint_scripts(self, driver):
        """
        Inyecta los scripts de fingerprinting en el driver.
        
        Args:
            driver: WebDriver destino
        """
        self.logger.info("Inyectando scripts de fingerprinting...")
        
        # Script completo
        script = self.fingerprint_gen.generate_all_scripts()
        
        # Inyectar en todas las páginas nuevas
        try:
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': script
            })
            self.logger.info("Scripts de fingerprinting inyectados")
        except Exception as e:
            self.logger.warning(f"Error inyectando via CDP: {e}")
            # Fallback: ejecutar directamente
            driver.execute_script(script)
    
    @property
    def driver(self):
        """Devuelve el WebDriver subyacente."""
        return self._driver
    
    def get(self, url: str, wait_time: float = None):
        """
        Navega a una URL con comportamiento humano.
        
        Args:
            url: URL a navegar
            wait_time: Tiempo de espera adicional
        """
        self.logger.info(f"Navegando a: {url}")
        
        # Delay antes de navegar
        delay = get_action_delay('navigate')
        time.sleep(delay / 1000)
        
        # Navegar
        self._driver.get(url)
        self._current_url = url
        
        # Esperar a que cargue
        if wait_time:
            time.sleep(wait_time)
        
        # Simular comportamiento humano post-navegación
        self._post_navigation_behavior()
    
    def _post_navigation_behavior(self):
        """Simula comportamiento humano después de navegar."""
        # Movimiento de ratón aleatorio
        if self.human.should_move_randomly():
            try:
                self.random_mouse_move()
            except Exception:
                pass
        
        # Pequeña pausa
        time.sleep(random.uniform(0.5, 1.5))
    
    def random_mouse_move(self):
        """Realiza un movimiento de ratón aleatorio."""
        viewport = self._get_viewport_size()
        if not viewport:
            return
        
        # Posición actual (simulada, centro)
        current_x = viewport['width'] // 2
        current_y = viewport['height'] // 2
        
        # Movimiento aleatorio
        movement = self.human.generate_random_mouse_movement(
            current_x, current_y,
            max_distance=min(200, viewport['width'] // 4)
        )
        
        if movement:
            target_x, target_y = movement
            # Asegurar que está dentro del viewport
            target_x = max(0, min(viewport['width'], target_x))
            target_y = max(0, min(viewport['height'], target_y))
            
            self.human_move_to(target_x, target_y)
    
    def _get_viewport_size(self) -> Optional[Dict[str, int]]:
        """Obtiene el tamaño del viewport."""
        try:
            result = self._driver.execute_script("""
                return {
                    width: window.innerWidth,
                    height: window.innerHeight
                };
            """)
            return result
        except Exception:
            return None
    
    def human_move_to(self, x: float, y: float, element=None, speed: str = 'normal'):
        """
        Mueve el ratón a una posición de forma humana.
        
        Args:
            x: Coordenada X destino
            y: Coordenada Y destino
            element: Elemento destino (opcional)
            speed: 'normal' (Bezier) o 'fast' (Instantáneo con jitter)
        """
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.actions.mouse_button import MouseButton
        
        # Obtener posición actual del ratón (aproximada)
        try:
            current_pos = self._driver.execute_script("""
                return window.__lastMousePos || {x: window.innerWidth/2, y: window.innerHeight/2};
            """)
        except Exception:
            current_pos = {'x': self.profile.screen_width // 2, 'y': self.profile.screen_height // 2}
        
        actions = ActionChains(self._driver)

        if speed == 'fast':
            # Movimiento instantáneo con desplazamiento relativo único
            offset_x = x - current_pos['x']
            offset_y = y - current_pos['y']
            try:
                actions.move_by_offset(offset_x, offset_y).perform()
            except Exception:
                # Fallback JS si falla el offset
                self.execute_script(f"window.__lastMousePos = {{x: {x}, y: {y}}};")
        else:
            # Generar trayectoria
            path = self.human.mouse.generate_path(
                current_pos['x'], current_pos['y'],
                x, y
            )
            
            # Ejecutar movimiento
            
            for px, py in path:
                try:
                    # Obtener tamaño actual de la ventana por seguridad
                    window_size = self._driver.get_window_size()
                    max_w, max_h = window_size['width'], window_size['height']
                    
                    # Validar que el punto esté dentro de límites razonables (viewport)
                    if px < 0 or py < 0 or px >= max_w or py >= max_h:
                        self.logger.debug(f"Punto fuera de límites omitido: ({px}, {py})")
                        continue

                    # Usar move_by_offset para movimientos relativos
                    if path.index((px, py)) == 0:
                        # Primer movimiento desde posición actual
                        offset_x = px - current_pos['x']
                        offset_y = py - current_pos['y']
                    else:
                        # Movimientos relativos al punto anterior
                        prev_x, prev_y = path[path.index((px, py)) - 1]
                        offset_x = px - prev_x
                        offset_y = py - prev_y
                    
                    actions.move_by_offset(offset_x, offset_y)
                    actions.pause(0.001)
                    
                except Exception as e:
                    self.logger.debug(f"Error en paso de trayectoria: {e}")
                    continue
            
            try:
                actions.perform()
            except Exception as e:
                self.logger.debug(f"ActionChains perform omitido por límites o error: {e}")
                # Si ActionChains falla, al menos intentamos mover instantáneamente por JS
                self.execute_script(f"window.__lastMousePos = {{x: {x}, y: {y}}};")
        
        # Guardar posición actual
        try:
            self._driver.execute_script(f"""
                window.__lastMousePos = {{x: {x}, y: {y}}};
            """)
        except Exception:
            pass
    
    def human_click(self, element, move_to: bool = True, speed: str = 'normal'):
        """
        Realiza un clic de forma humana.
        
        Args:
            element: Elemento a clickear
            move_to: Si mover el ratón primero
            speed: 'normal' o 'fast'
        """
        try:
            if move_to:
                # Asegurar visibilidad
                location = element.location_once_scrolled_into_view
                size = element.size
                
                # Centro con jitter mínimo
                target_x = location['x'] + size['width'] // 2 + random.randint(-2, 2)
                target_y = location['y'] + size['height'] // 2 + random.randint(-2, 2)
                
                self.human_move_to(target_x, target_y, speed=speed)
            
            # Pequeña pausa antes del clic
            time.sleep(random.uniform(0.1, 0.3))
            
            # Realizar clic usando ActionChains para que sea 'humano'
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(self._driver)
            actions.click()
            actions.perform()
            
        except Exception as e:
            self.logger.debug(f"human_click: Simulación humana falló ({e}), usando fallbacks...")
            try:
                # Fallback: Scrollear al elemento por JS y clickear directamente
                self.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.5)
                element.click()
            except Exception as e2:
                self.logger.error(f"Fallo crítico en clic: {e2}")
                # Último recurso: clic por JS
                self.execute_script("arguments[0].click();", element)
        
        # Pausa post-clic basada en perfil humano
        time.sleep(get_action_delay('click') / 1000)
    
    def human_type(self, element, text: str, clear_first: bool = True):
        """
        Escribe texto de forma humana.
        
        Args:
            element: Elemento donde escribir
            text: Texto a escribir
            clear_first: Si limpiar el campo primero
        """
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.keys import Keys
        
        # Clic en el elemento
        self.human_click(element)
        
        if clear_first:
            # Seleccionar todo y borrar
            ActionChains(self._driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
            time.sleep(random.uniform(0.1, 0.2))
            element.send_keys(Keys.BACKSPACE)
            time.sleep(random.uniform(0.1, 0.3))
        
        # Generar secuencia de escritura
        sequence = self.human.typing.generate_typing_sequence(text)
        
        # Ejecutar escritura
        for char, delay in sequence:
            if char == '[PAUSE]':
                time.sleep(delay / 1000)
            elif char == '\b':
                element.send_keys(Keys.BACKSPACE)
                time.sleep(delay / 1000)
            else:
                element.send_keys(char)
                time.sleep(delay / 1000)
    
    def human_scroll(self, distance: int, direction: str = 'down'):
        """
        Realiza scroll de forma humana.
        
        Args:
            distance: Distancia en píxeles
            direction: 'up' o 'down'
        """
        steps = self.human.scroll.generate_scroll_steps(distance, direction)
        
        for amount, delay in steps:
            script = f"window.scrollBy(0, {amount});"
            self._driver.execute_script(script)
            time.sleep(delay / 1000)
    
    def wait_for_element(
        self,
        locator: tuple,
        timeout: float = None,
        condition: str = 'visible'
    ):
        """
        Espera a que un elemento esté disponible.
        
        Args:
            locator: Tupla (By, selector)
            timeout: Timeout en segundos
            condition: 'visible', 'clickable', 'present'
        
        Returns:
            WebElement: Elemento encontrado
        
        Raises:
            TimeoutException: Si no se encuentra el elemento
        """
        timeout = timeout or self.config.element_wait_timeout
        
        conditions = {
            'visible': EC.visibility_of_element_located,
            'clickable': EC.element_to_be_clickable,
            'present': EC.presence_of_element_located,
        }
        
        wait_condition = conditions.get(condition, EC.visibility_of_element_located)
        
        return WebDriverWait(self._driver, timeout).until(wait_condition(locator))
    
    def wait_for_text(self, locator: tuple, text: str, timeout: float = None):
        """
        Espera a que aparezca cierto texto en un elemento.
        
        Args:
            locator: Tupla (By, selector)
            text: Texto a esperar
            timeout: Timeout en segundos
        """
        timeout = timeout or self.config.element_wait_timeout
        return WebDriverWait(self._driver, timeout).until(
            EC.text_to_be_present_in_element(locator, text)
        )
    
    def find_element_safe(self, locator: tuple, timeout: float = 5):
        """
        Busca un elemento de forma segura.
        
        Args:
            locator: Tupla (By, selector)
            timeout: Timeout en segundos
        
        Returns:
            WebElement o None
        """
        try:
            return self.wait_for_element(locator, timeout)
        except TimeoutException:
            return None
    
    def is_element_present(self, locator: tuple) -> bool:
        """
        Verifica si un elemento está presente.
        
        Args:
            locator: Tupla (By, selector)
        
        Returns:
            bool: True si está presente
        """
        try:
            self._driver.find_element(*locator)
            return True
        except NoSuchElementException:
            return False
    
    def execute_script(self, script: str, *args):
        """
        Ejecuta JavaScript en la página.
        
        Args:
            script: Código JavaScript
            *args: Argumentos para el script
        
        Returns:
            Resultado del script
        """
        return self._driver.execute_script(script, *args)
    
    def get_screenshot(self, filename: str = None) -> str:
        """
        Toma una captura de pantalla.
        
        Args:
            filename: Nombre del archivo (opcional)
        
        Returns:
            str: Ruta del archivo
        """
        if filename is None:
            timestamp = int(time.time())
            filename = f"screenshot_{timestamp}.png"
        
        filepath = os.path.join(self.config.screenshot_dir, filename)
        os.makedirs(self.config.screenshot_dir, exist_ok=True)
        
        self._driver.save_screenshot(filepath)
        return filepath
    
    def get_page_source(self) -> str:
        """Devuelve el código fuente de la página actual."""
        return self._driver.page_source
    
    def get_current_url(self) -> str:
        """Devuelve la URL actual."""
        return self._driver.current_url
    
    def get_cookies(self) -> list:
        """Devuelve todas las cookies."""
        return self._driver.get_cookies()
    
    def add_cookie(self, cookie: dict):
        """Añade una cookie."""
        self._driver.add_cookie(cookie)
    
    def refresh(self):
        """Refresca la página actual."""
        self._driver.refresh()
        self._post_navigation_behavior()
    
    def go_back(self):
        """Navega hacia atrás."""
        self._driver.back()
        self._post_navigation_behavior()
    
    def close(self):
        """Cierra el driver."""
        if self._driver:
            try:
                self._driver.quit()
            except Exception as e:
                self.logger.warning(f"Error cerrando driver: {e}")
            finally:
                self._driver = None
                self._is_initialized = False
    
    def quit(self):
        """Alias para close() para compatibilidad con Selenium API."""
        self.close()
    
    def enable_spy_mode(self):
        """Inyecta el script de espionaje para monitorear el DOM y coordenadas."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        spy_script_path = os.path.join(base_dir, 'resources', 'spy_mode.js')
        
        if os.path.exists(spy_script_path):
            with open(spy_script_path, 'r', encoding='utf-8') as f:
                script_content = f.read()
            self.execute_script(script_content)
            self.logger.info("[Spy Mode] Script inyectado.")
        else:
            self.logger.error(f"[Spy Mode] Script no encontrado en {spy_script_path}")

    def take_observation_screenshot(self, name=None):
        """Toma una captura de pantalla y la guarda en la carpeta de capturas."""
        if not self._driver:
            return None
        os.makedirs("captures", exist_ok=True)
        timestamp = datetime.now().strftime('%H%M%S')
        filename = f"captures/screenshot_{timestamp}_{name if name else ''}.png"
        self._driver.save_screenshot(filename)
        self.logger.info(f"[Observation] Captura guardada: {filename}")
        return filename
    
    def get_log(self, log_type):
        """Obtiene logs del driver."""
        if not self._driver:
            return []
        return self._driver.get_log(log_type)

    def execute_script(self, script, *args):
        """Ejecuta JavaScript."""
        if not self._driver:
            return None
        return self._driver.execute_script(script, *args)

    @property
    def page_source(self):
        """Obtiene el código fuente de la página."""
        if not self._driver:
            return ""
        return self._driver.page_source

    @property
    def current_url(self):
        """Obtiene la URL actual."""
        if not self._driver:
            return ""
        return self._driver.current_url
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __del__(self):
        """Destructor."""
        # No cerrar automáticamente si es singleton
        if not hasattr(self, '_driver') or AntiDetectionDriver._instance != self:
            self.close()


def create_driver(
    profile_name: str = None,
    config_obj: Config = None,
    singleton: bool = False
) -> AntiDetectionDriver:
    """
    Función de conveniencia para crear un driver.
    
    Args:
        profile_name: Nombre del perfil de hardware
        config_obj: Configuración personalizada
        singleton: Si usar patrón singleton
    
    Returns:
        AntiDetectionDriver: Driver configurado
    """
    profile = None
    if profile_name:
        profile = get_profile(profile_name)
    
    return AntiDetectionDriver(
        profile=profile,
        config_obj=config_obj,
        singleton=singleton
    )
