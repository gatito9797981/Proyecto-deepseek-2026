"""
Pool de drivers para ejecución paralela.

Este módulo proporciona un pool de navegadores para ejecutar
múltiples tareas en paralelo de forma thread-safe.

Características:
    - Pool de drivers pre-inicializados
    - Thread-safe acquisition/release
    - Auto-scaling según demanda
    - Health checks automáticos
    - Limpieza de drivers inactivos
"""

import threading
import time
import logging
from typing import Optional, List, Callable, Any
from dataclasses import dataclass, field
from queue import Queue, Empty
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, Future

from .config import Config, config
from .driver import AntiDetectionDriver
from .profiles import get_random_profile, HardwareProfile


@dataclass
class DriverWrapper:
    """
    Wrapper para un driver en el pool.
    
    Attributes:
        driver: Instancia del driver
        driver_id: ID único del driver
        profile: Perfil de hardware usado
        created_at: Timestamp de creación
        last_used: Timestamp de último uso
        is_busy: Si está en uso
        error_count: Contador de errores
        task_count: Contador de tareas completadas
    """
    driver: AntiDetectionDriver
    driver_id: int
    profile: HardwareProfile
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    is_busy: bool = False
    error_count: int = 0
    task_count: int = 0
    
    def mark_used(self):
        """Marca el driver como usado recientemente."""
        self.last_used = time.time()
        self.task_count += 1
    
    def mark_error(self):
        """Incrementa el contador de errores."""
        self.error_count += 1
    
    def is_healthy(self) -> bool:
        """Verifica si el driver está saludable."""
        # Demasiados errores
        if self.error_count > 5:
            return False
        
        # Verificar que el driver responde
        try:
            self.driver.driver.current_url
            return True
        except Exception:
            return False
    
    def get_age(self) -> float:
        """Devuelve la edad del driver en segundos."""
        return time.time() - self.created_at
    
    def get_idle_time(self) -> float:
        """Devuelve el tiempo inactivo en segundos."""
        return time.time() - self.last_used


class DriverPool:
    """
    Pool thread-safe de drivers de navegador.
    
    Gestiona un conjunto de drivers pre-inicializados que pueden
    ser adquiridos y liberados de forma segura desde múltiples hilos.
    
    Uso:
        pool = DriverPool(size=3)
        
        # Usar con context manager
        with pool.acquire() as driver:
            driver.get("https://example.com")
        
        # Ejecutar tarea en paralelo
        result = pool.execute(lambda d: d.get_current_url())
    """
    
    def __init__(
        self,
        size: int = 3,
        config_obj: Optional[Config] = None,
        auto_start: bool = True,
        max_age: float = 3600,  # 1 hora
        max_idle: float = 300,  # 5 minutos
        health_check_interval: float = 60  # 1 minuto
    ):
        """
        Inicializa el pool de drivers.
        
        Args:
            size: Número de drivers en el pool
            config_obj: Configuración personalizada
            auto_start: Si inicializar drivers automáticamente
            max_age: Edad máxima de un driver en segundos
            max_idle: Tiempo máximo inactivo antes de reciclar
            health_check_interval: Intervalo de health checks
        """
        self.size = size
        self.config = config_obj or config
        self.logger = self.config.setup_logging()
        
        self.max_age = max_age
        self.max_idle = max_idle
        self.health_check_interval = health_check_interval
        
        # Estado interno
        self._drivers: List[DriverWrapper] = []
        self._available: Queue = Queue()
        self._lock = threading.RLock()
        self._next_id = 0
        self._is_running = False
        self._health_thread: Optional[threading.Thread] = None
        
        if auto_start:
            self.start()
    
    def start(self):
        """Inicia el pool y crea los drivers iniciales."""
        with self._lock:
            if self._is_running:
                return
            
            self.logger.info(f"Iniciando pool de drivers (tamaño: {self.size})")
            
            # Crear drivers iniciales
            for i in range(self.size):
                try:
                    wrapper = self._create_driver()
                    self._drivers.append(wrapper)
                    self._available.put(wrapper.driver_id)
                except Exception as e:
                    self.logger.error(f"Error creando driver {i}: {e}")
            
            self._is_running = True
            
            # Iniciar thread de health check
            self._health_thread = threading.Thread(
                target=self._health_check_loop,
                daemon=True
            )
            self._health_thread.start()
            
            self.logger.info(f"Pool iniciado con {len(self._drivers)} drivers")
    
    def _create_driver(self) -> DriverWrapper:
        """
        Crea un nuevo driver con perfil aleatorio.
        
        Returns:
            DriverWrapper: Wrapper del nuevo driver
        """
        with self._lock:
            driver_id = self._next_id
            self._next_id += 1
        
        # Perfil aleatorio para cada driver
        profile = get_random_profile()
        
        self.logger.info(f"Creando driver {driver_id} con perfil {profile.name}")
        
        driver = AntiDetectionDriver(
            profile=profile,
            config_obj=self.config,
            profile_id=f"pool_driver_{driver_id}"
        )
        
        return DriverWrapper(
            driver=driver,
            driver_id=driver_id,
            profile=profile
        )
    
    def _get_wrapper(self, driver_id: int) -> Optional[DriverWrapper]:
        """Obtiene el wrapper por ID."""
        for wrapper in self._drivers:
            if wrapper.driver_id == driver_id:
                return wrapper
        return None
    
    def acquire(self, timeout: float = 30) -> AntiDetectionDriver:
        """
        Adquiere un driver del pool.
        
        Args:
            timeout: Timeout de espera en segundos
        
        Returns:
            AntiDetectionDriver: Driver disponible
        
        Raises:
            TimeoutError: Si no hay drivers disponibles
        """
        if not self._is_running:
            raise RuntimeError("Pool no está iniciado")
        
        try:
            driver_id = self._available.get(timeout=timeout)
        except Empty:
            raise TimeoutError("No hay drivers disponibles en el pool")
        
        wrapper = self._get_wrapper(driver_id)
        
        if wrapper is None or not wrapper.is_healthy():
            # Driver no saludable, crear nuevo
            self.logger.warning(f"Driver {driver_id} no saludable, recreando...")
            
            with self._lock:
                # Eliminar wrapper antiguo
                self._drivers = [w for w in self._drivers if w.driver_id != driver_id]
                
                # Crear nuevo
                wrapper = self._create_driver()
                self._drivers.append(wrapper)
        
        wrapper.is_busy = True
        wrapper.mark_used()
        
        return wrapper.driver
    
    def release(self, driver: AntiDetectionDriver):
        """
        Libera un driver de vuelta al pool.
        
        Args:
            driver: Driver a liberar
        """
        # Encontrar el wrapper correspondiente
        wrapper = None
        for w in self._drivers:
            if w.driver is driver or w.driver.driver is driver:
                wrapper = w
                break
        
        if wrapper is None:
            self.logger.warning("Intentando liberar driver desconocido")
            return
        
        wrapper.is_busy = False
        self._available.put(wrapper.driver_id)
    
    @contextmanager
    def get_driver(self, timeout: float = 30):
        """
        Context manager para adquirir y liberar un driver.
        
        Args:
            timeout: Timeout de adquisición
        
        Yields:
            AntiDetectionDriver: Driver disponible
        
        Uso:
            with pool.get_driver() as driver:
                driver.get("https://example.com")
        """
        driver = None
        try:
            driver = self.acquire(timeout)
            yield driver
        finally:
            if driver:
                self.release(driver)
    
    def execute(
        self,
        task: Callable[[AntiDetectionDriver], Any],
        timeout: float = 60,
        driver_timeout: float = 30
    ) -> Any:
        """
        Ejecuta una tarea con un driver del pool.
        
        Args:
            task: Función que recibe un driver y devuelve un resultado
            timeout: Timeout total de la tarea
            driver_timeout: Timeout para adquirir driver
        
        Returns:
            Resultado de la tarea
        """
        with self.get_driver(driver_timeout) as driver:
            return task(driver)
    
    def execute_parallel(
        self,
        tasks: List[Callable[[AntiDetectionDriver], Any]],
        max_workers: int = None
    ) -> List[Any]:
        """
        Ejecuta múltiples tareas en paralelo.
        
        Args:
            tasks: Lista de funciones a ejecutar
            max_workers: Número máximo de workers (default: tamaño del pool)
        
        Returns:
            List[Any]: Lista de resultados
        """
        max_workers = max_workers or self.size
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.execute, task) for task in tasks]
            results = [f.result() for f in futures]
        
        return results
    
    def _health_check_loop(self):
        """Loop de health checks en background."""
        while self._is_running:
            time.sleep(self.health_check_interval)
            self._perform_health_check()
    
    def _perform_health_check(self):
        """Realiza health check de todos los drivers."""
        self.logger.debug("Realizando health check...")
        
        with self._lock:
            drivers_to_replace = []
            
            for wrapper in self._drivers:
                # Verificar edad
                if wrapper.get_age() > self.max_age:
                    self.logger.info(f"Driver {wrapper.driver_id} excedió edad máxima")
                    drivers_to_replace.append(wrapper)
                    continue
                
                # Verificar tiempo inactivo (solo si no está ocupado)
                if not wrapper.is_busy and wrapper.get_idle_time() > self.max_idle:
                    self.logger.info(f"Driver {wrapper.driver_id} inactivo por demasiado tiempo")
                    drivers_to_replace.append(wrapper)
                    continue
                
                # Verificar salud
                if not wrapper.is_healthy():
                    self.logger.warning(f"Driver {wrapper.driver_id} no saludable")
                    drivers_to_replace.append(wrapper)
            
            # Reemplazar drivers necesarios
            for wrapper in drivers_to_replace:
                self._replace_driver(wrapper)
    
    def _replace_driver(self, old_wrapper: DriverWrapper):
        """
        Reemplaza un driver por uno nuevo.
        
        Args:
            old_wrapper: Wrapper del driver a reemplazar
        """
        self.logger.info(f"Reemplazando driver {old_wrapper.driver_id}")
        
        try:
            # Cerrar driver antiguo
            old_wrapper.driver.close()
        except Exception as e:
            self.logger.warning(f"Error cerrando driver antiguo: {e}")
        
        # Crear nuevo driver
        new_wrapper = self._create_driver()
        
        with self._lock:
            # Actualizar lista de drivers
            self._drivers = [
                w for w in self._drivers 
                if w.driver_id != old_wrapper.driver_id
            ]
            self._drivers.append(new_wrapper)
            
            # Añadir a disponibles
            self._available.put(new_wrapper.driver_id)
    
    def get_status(self) -> dict:
        """
        Obtiene el estado actual del pool.
        
        Returns:
            dict: Estado del pool
        """
        with self._lock:
            total_drivers = len(self._drivers)
            busy_drivers = sum(1 for w in self._drivers if w.is_busy)
            available_drivers = self._available.qsize()
            
            return {
                "is_running": self._is_running,
                "pool_size": self.size,
                "total_drivers": total_drivers,
                "available_drivers": available_drivers,
                "busy_drivers": busy_drivers,
                "drivers": [
                    {
                        "id": w.driver_id,
                        "profile": w.profile.name,
                        "is_busy": w.is_busy,
                        "task_count": w.task_count,
                        "error_count": w.error_count,
                        "age": w.get_age(),
                        "idle_time": w.get_idle_time(),
                    }
                    for w in self._drivers
                ]
            }
    
    def resize(self, new_size: int):
        """
        Cambia el tamaño del pool.
        
        Args:
            new_size: Nuevo tamaño del pool
        """
        with self._lock:
            self.logger.info(f"Cambiando tamaño del pool: {self.size} -> {new_size}")
            
            if new_size > self.size:
                # Añadir drivers
                for _ in range(new_size - self.size):
                    wrapper = self._create_driver()
                    self._drivers.append(wrapper)
                    self._available.put(wrapper.driver_id)
            
            elif new_size < self.size:
                # Eliminar drivers (solo los disponibles)
                to_remove = self.size - new_size
                removed = 0
                
                for wrapper in list(self._drivers):
                    if removed >= to_remove:
                        break
                    
                    if not wrapper.is_busy:
                        try:
                            wrapper.driver.close()
                        except Exception:
                            pass
                        
                        self._drivers.remove(wrapper)
                        removed += 1
            
            self.size = new_size
    
    def close(self):
        """Cierra todos los drivers y detiene el pool."""
        self.logger.info("Cerrando pool de drivers...")
        
        self._is_running = False
        
        # Esperar a que termine el thread de health check
        if self._health_thread and self._health_thread.is_alive():
            self._health_thread.join(timeout=5)
        
        # Cerrar todos los drivers
        with self._lock:
            for wrapper in self._drivers:
                try:
                    wrapper.driver.close()
                except Exception as e:
                    self.logger.warning(f"Error cerrando driver {wrapper.driver_id}: {e}")
            
            self._drivers.clear()
            
            # Vaciar cola de disponibles
            while not self._available.empty():
                try:
                    self._available.get_nowait()
                except Empty:
                    break
        
        self.logger.info("Pool cerrado")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __del__(self):
        """Destructor."""
        self.close()


# Instancia global del pool (lazy initialization)
_global_pool: Optional[DriverPool] = None
_pool_lock = threading.Lock()


def get_pool(size: int = None, config_obj: Config = None) -> DriverPool:
    """
    Obtiene la instancia global del pool.
    
    Args:
        size: Tamaño del pool (solo se usa en la primera llamada)
        config_obj: Configuración (solo se usa en la primera llamada)
    
    Returns:
        DriverPool: Instancia del pool
    """
    global _global_pool
    
    with _pool_lock:
        if _global_pool is None:
            pool_size = size or config.driver_pool_size
            _global_pool = DriverPool(size=pool_size, config_obj=config_obj or config)
        
        return _global_pool


def close_pool():
    """Cierra el pool global."""
    global _global_pool
    
    with _pool_lock:
        if _global_pool is not None:
            _global_pool.close()
            _global_pool = None
