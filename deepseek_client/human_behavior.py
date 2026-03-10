"""
Módulo de comportamiento humano simulado.

Este módulo proporciona funciones para simular comportamiento humano
en interacciones con el navegador, incluyendo:
    - Movimiento de ratón con curvas de Bézier
    - Escritura con timing realista
    - Scroll natural
    - Pausas aleatorias

El objetivo es hacer que la automatización sea indistinguible
de un usuario humano real.
"""

import random
import math
import time
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass


@dataclass
class Point:
    """Punto 2D con coordenadas x, y."""
    x: float
    y: float
    
    def __iter__(self):
        return iter((self.x, self.y))
    
    def __add__(self, other: 'Point') -> 'Point':
        return Point(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: 'Point') -> 'Point':
        return Point(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar: float) -> 'Point':
        return Point(self.x * scalar, self.y * scalar)
    
    def distance_to(self, other: 'Point') -> float:
        """Calcula la distancia euclidiana a otro punto."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


class BezierCurve:
    """
    Generador de curvas de Bézier cúbicas para movimiento de ratón.
    
    Las curvas de Bézier permiten crear trayectorias suaves y naturales
    que imitan el movimiento humano, con aceleración y desaceleración.
    """
    
    @staticmethod
    def cubic_bezier(t: float, p0: Point, p1: Point, p2: Point, p3: Point) -> Point:
        """
        Calcula un punto en una curva de Bézier cúbica.
        
        La curva de Bézier cúbica está definida por 4 puntos de control:
        - p0: punto inicial
        - p1, p2: puntos de control que definen la curvatura
        - p3: punto final
        
        Args:
            t: Parámetro entre 0 y 1
            p0, p1, p2, p3: Puntos de control
        
        Returns:
            Point: Punto en la curva para el valor de t
        """
        t2 = t * t
        t3 = t2 * t
        mt = 1 - t
        mt2 = mt * mt
        mt3 = mt2 * mt
        
        x = mt3 * p0.x + 3 * mt2 * t * p1.x + 3 * mt * t2 * p2.x + t3 * p3.x
        y = mt3 * p0.y + 3 * mt2 * t * p1.y + 3 * mt * t2 * p2.y + t3 * p3.y
        
        return Point(x, y)
    
    @staticmethod
    def generate_control_points(start: Point, end: Point, randomness: float = 0.5) -> Tuple[Point, Point]:
        """
        Genera puntos de control intermedios para una curva de Bézier.
        
        Los puntos de control se generan para crear una curva natural
        que simule el movimiento de un ratón humano.
        
        Args:
            start: Punto inicial
            end: Punto final
            randomness: Factor de aleatoriedad (0-1)
        
        Returns:
            Tuple[Point, Point]: Dos puntos de control intermedios
        """
        # Vector del movimiento
        delta = end - start
        
        # Punto medio
        mid = start + delta * 0.5
        
        # Distancia del movimiento
        distance = start.distance_to(end)
        
        # Factor de curvatura basado en la distancia
        # Movimientos más largos tienen curvas más pronunciadas
        curve_factor = min(distance * 0.3, 100) * randomness
        
        # Generar desplazamiento perpendicular
        perpendicular = Point(-delta.y, delta.x)
        if perpendicular.x != 0 or perpendicular.y != 0:
            length = math.sqrt(perpendicular.x ** 2 + perpendicular.y ** 2)
            perpendicular = Point(perpendicular.x / length, perpendicular.y / length)
        
        # Offset aleatorio perpendicular
        offset = perpendicular * curve_factor * random.choice([-1, 1])
        
        # Puntos de control con variación
        control1 = Point(
            mid.x - delta.x * 0.25 + offset.x + random.uniform(-10, 10),
            mid.y - delta.y * 0.25 + offset.y + random.uniform(-10, 10)
        )
        control2 = Point(
            mid.x + delta.x * 0.25 - offset.x + random.uniform(-10, 10),
            mid.y + delta.y * 0.25 - offset.y + random.uniform(-10, 10)
        )
        
        return control1, control2
    
    @staticmethod
    def generate_curve(
        start: Point,
        end: Point,
        num_points: int = 50,
        randomness: float = 0.5
    ) -> List[Point]:
        """
        Genera una lista de puntos que forman una curva de Bézier.
        
        Args:
            start: Punto inicial
            end: Punto final
            num_points: Número de puntos a generar
            randomness: Factor de aleatoriedad
        
        Returns:
            List[Point]: Lista de puntos de la curva
        """
        control1, control2 = BezierCurve.generate_control_points(start, end, randomness)
        
        # Aplicar easing para aceleración/desaceleración
        points = []
        for i in range(num_points):
            # Easing cuadrático: lento al inicio y al final
            t = i / (num_points - 1)
            eased_t = t * t * (3 - 2 * t)  # Smoothstep
            
            point = BezierCurve.cubic_bezier(eased_t, start, control1, control2, end)
            points.append(point)
        
        return points


class MouseMovement:
    """
    Simulador de movimiento de ratón humano.
    
    Proporciona métodos para mover el cursor de forma natural
    con aceleración, desaceleración y trayectorias curvas.
    """
    
    def __init__(
        self,
        base_speed: float = 800.0,  # píxeles por segundo
        acceleration: float = 1.5,
        randomness: float = 0.4
    ):
        """
        Inicializa el simulador de movimiento.
        
        Args:
            base_speed: Velocidad base en píxeles/segundo
            acceleration: Factor de aceleración
            randomness: Factor de aleatoriedad (0-1)
        """
        self.base_speed = base_speed
        self.acceleration = acceleration
        self.randomness = randomness
    
    def calculate_duration(self, distance: float) -> float:
        """
        Calcula la duración del movimiento basándose en la distancia.
        
        Los humanos nos movemos más rápido en distancias largas,
        pero la relación no es lineal (ley de Fitts).
        
        Args:
            distance: Distancia en píxeles
        
        Returns:
            float: Duración en segundos
        """
        # Ley de Fitts simplificada
        # Tiempo = a + b * log2(distancia/amplitud + 1)
        # Simplificado para obtener valores realistas
        
        if distance < 10:
            return random.uniform(0.05, 0.1)
        elif distance < 100:
            return random.uniform(0.1, 0.3)
        elif distance < 500:
            return random.uniform(0.3, 0.6)
        else:
            # Movimientos largos: ~800-1200 píxeles/segundo
            return distance / (self.base_speed * random.uniform(0.8, 1.2))
    
    def generate_path(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        num_points: Optional[int] = None
    ) -> List[Tuple[float, float]]:
        """
        Genera una trayectoria de movimiento de ratón.
        
        Args:
            start_x, start_y: Coordenadas iniciales
            end_x, end_y: Coordenadas finales
            num_points: Número de puntos (auto si None)
        
        Returns:
            List[Tuple[float, float]]: Lista de coordenadas (x, y)
        """
        start = Point(start_x, start_y)
        end = Point(end_x, end_y)
        
        distance = start.distance_to(end)
        
        # Calcular número de puntos basado en la distancia
        if num_points is None:
            duration = self.calculate_duration(distance)
            # ~60 puntos por segundo para movimiento suave
            num_points = max(5, int(duration * 60))
        
        # Generar curva
        points = BezierCurve.generate_curve(start, end, num_points, self.randomness)
        
        return [(p.x, p.y) for p in points]
    
    def generate_timed_path(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float
    ) -> List[Tuple[float, float, float]]:
        """
        Genera una trayectoria con tiempos para cada punto.
        
        Args:
            start_x, start_y: Coordenadas iniciales
            end_x, end_y: Coordenadas finales
        
        Returns:
            List[Tuple[float, float, float]]: Lista de (x, y, delay_ms)
        """
        start = Point(start_x, start_y)
        end = Point(end_x, end_y)
        
        distance = start.distance_to(end)
        duration = self.calculate_duration(distance)
        
        # Número de puntos basado en la duración
        num_points = max(5, int(duration * 60))
        
        # Generar curva
        points = BezierCurve.generate_curve(start, end, num_points, self.randomness)
        
        # Calcular delays con perfil de velocidad
        # Velocidad más lenta al inicio y al final (easing)
        result = []
        total_delay = 0.0
        
        for i, point in enumerate(points):
            # Easing cuadrático
            t = i / max(1, num_points - 1)
            ease = t * t * (3 - 2 * t)
            
            # Velocidad variable (más rápido en el medio)
            speed_factor = 0.3 + 0.7 * (4 * ease * (1 - ease))  # Pico en el medio
            
            # Delay entre puntos
            base_delay = duration / num_points * 1000  # ms
            delay = base_delay / speed_factor * random.uniform(0.8, 1.2)
            
            total_delay += delay
            result.append((point.x, point.y, delay))
        
        return result


class HumanTyping:
    """
    Simulador de escritura humana.
    
    Genera delays realistas entre teclas, pausas en puntuación,
    errores ocasionales y correcciones.
    """
    
    # Caracteres que requieren más tiempo
    SLOW_CHARS = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()_+{}|:"<>?')
    
    # Puntuación que causa pausas
    PUNCTUATION = set('.,;:!?')
    
    # Caracteres que frecuentemente se escriben mal
    COMMON_ERRORS = {
        'a': ['s', 'q'],
        's': ['a', 'd', 'w'],
        'd': ['s', 'f', 'e'],
        'f': ['d', 'g', 'r'],
        'g': ['f', 'h', 't'],
        'h': ['g', 'j', 'y'],
        'j': ['h', 'k', 'u'],
        'k': ['j', 'l', 'i'],
        'l': ['k', 'o', 'p'],
        'e': ['w', 'r', 'd'],
        'r': ['e', 't', 'f'],
        't': ['r', 'y', 'g'],
        'y': ['t', 'u', 'h'],
        'u': ['y', 'i', 'j'],
        'i': ['u', 'o', 'k'],
        'o': ['i', 'p', 'l'],
        'n': ['b', 'm', 'j'],
        'm': ['n', 'k', 'l'],
        'b': ['v', 'n', 'g'],
        'v': ['c', 'b', 'f'],
        'c': ['x', 'v', 'd'],
        'x': ['z', 'c', 's'],
        'z': ['x', 'a', 's'],
        ' ': [' ', 'n', 'm', 'b'],
    }
    
    def __init__(
        self,
        mean_delay: float = 25.0,  # ms
        std_delay: float = 10.0,
        error_rate: float = 0.005,
        pause_on_punctuation: float = 0.15,  # probabilidad de pausa
        pause_duration: float = 200.0  # ms
    ):
        """
        Inicializa el simulador de escritura.
        
        Args:
            mean_delay: Delay medio entre teclas (ms)
            std_delay: Desviación estándar del delay
            error_rate: Tasa de errores (0-1)
            pause_on_punctuation: Probabilidad de pausa en puntuación
            pause_duration: Duración base de pausas (ms)
        """
        self.mean_delay = mean_delay
        self.std_delay = std_delay
        self.error_rate = error_rate
        self.pause_on_punctuation = pause_on_punctuation
        self.pause_duration = pause_duration
    
    def get_char_delay(self, char: str, prev_char: Optional[str] = None) -> float:
        """
        Calcula el delay para escribir un carácter específico.
        
        Args:
            char: Carácter a escribir
            prev_char: Carácter anterior (para contexto)
        
        Returns:
            float: Delay en milisegundos
        """
        # Distribución normal con límites
        delay = random.gauss(self.mean_delay, self.std_delay)
        delay = max(20, min(200, delay))  # Clamp entre 20-200ms
        
        # Ajustes basados en el carácter
        if char in self.SLOW_CHARS:
            delay *= random.uniform(1.2, 1.5)  # Mayúsculas y símbolos más lentos
        
        if char == ' ':
            delay *= random.uniform(0.8, 1.1)
        
        # Transiciones entre manos (mayúsculas después de minúsculas, etc.)
        if prev_char and prev_char.islower() and char.isupper():
            delay *= random.uniform(1.3, 1.6)
        
        # Variación aleatoria adicional
        delay *= random.uniform(0.9, 1.1)
        
        return delay
    
    def should_pause(self, char: str) -> bool:
        """
        Determina si debe haber una pausa después del carácter.
        
        Args:
            char: Carácter escrito
        
        Returns:
            bool: True si debe pausar
        """
        if char in self.PUNCTUATION:
            return random.random() < self.pause_on_punctuation
        return False
    
    def get_pause_duration(self, char: str) -> float:
        """
        Obtiene la duración de una pausa.
        
        Args:
            char: Carácter que causó la pausa
        
        Returns:
            float: Duración en milisegundos
        """
        # Pausas más largas para puntos y signos de interrogación
        if char in '.!?':
            return self.pause_duration * random.uniform(1.5, 2.5)
        elif char in ',;':
            return self.pause_duration * random.uniform(0.5, 1.0)
        else:
            return self.pause_duration * random.uniform(0.8, 1.2)
    
    def generate_error(self, char: str) -> Optional[str]:
        """
        Genera un error de escritura posible.
        
        Args:
            char: Carácter original
        
        Returns:
            Optional[str]: Carácter erróneo o None
        """
        if char.lower() in self.COMMON_ERRORS and random.random() < self.error_rate:
            wrong_chars = self.COMMON_ERRORS[char.lower()]
            wrong = random.choice(wrong_chars)
            # Mantener mayúscula si aplica
            return wrong.upper() if char.isupper() else wrong
        return None
    
    def type_text(
        self,
        text: str,
        callback: Callable[[str, float], None]
    ) -> List[Tuple[str, float]]:
        """
        Simula escribir un texto completo.
        
        Args:
            text: Texto a escribir
            callback: Función llamada con (carácter, delay) para cada tecla
        
        Returns:
            List[Tuple[str, float]]: Historial de (carácter, delay)
        """
        history = []
        prev_char = None
        
        for char in text:
            # Posible error
            wrong_char = self.generate_error(char)
            
            if wrong_char:
                # Escribir carácter incorrecto
                delay = self.get_char_delay(wrong_char, prev_char)
                history.append((wrong_char, delay))
                callback(wrong_char, delay)
                prev_char = wrong_char
                
                # Pausa antes de corregir
                correction_delay = random.uniform(100, 300)
                time.sleep(correction_delay / 1000)
                
                # Borrar carácter incorrecto
                backspace_delay = self.get_char_delay('\b', wrong_char)
                history.append(('\b', backspace_delay))
                callback('\b', backspace_delay)
            
            # Escribir carácter correcto
            delay = self.get_char_delay(char, prev_char)
            history.append((char, delay))
            callback(char, delay)
            prev_char = char
            
            # Pausa en puntuación
            if self.should_pause(char):
                pause = self.get_pause_duration(char)
                time.sleep(pause / 1000)
        
        return history
    
    def generate_typing_sequence(self, text: str) -> List[Tuple[str, float]]:
        """
        Genera una secuencia de escritura sin ejecutarla.
        
        Args:
            text: Texto a escribir
        
        Returns:
            List[Tuple[str, float]]: Secuencia de (carácter, delay_ms)
        """
        sequence = []
        prev_char = None
        
        for char in text:
            # Posible error
            wrong_char = self.generate_error(char)
            
            if wrong_char:
                # Carácter incorrecto
                delay = self.get_char_delay(wrong_char, prev_char)
                sequence.append((wrong_char, delay))
                prev_char = wrong_char
                
                # Pausa antes de corregir
                correction_delay = random.uniform(100, 300)
                sequence.append(('[PAUSE]', correction_delay))
                
                # Borrar
                backspace_delay = self.get_char_delay('\b', wrong_char)
                sequence.append(('\b', backspace_delay))
            
            # Carácter correcto
            delay = self.get_char_delay(char, prev_char)
            sequence.append((char, delay))
            prev_char = char
            
            # Pausa en puntuación
            if self.should_pause(char):
                pause = self.get_pause_duration(char)
                sequence.append(('[PAUSE]', pause))
        
        return sequence


class HumanScroll:
    """
    Simulador de scroll natural con velocidad variable.
    
    Simula el comportamiento de scroll humano con:
    - Velocidad variable
    - Aceleración/desaceleración
    - Pausas aleatorias
    """
    
    def __init__(
        self,
        base_distance: int = 300,
        base_duration: float = 0.5,
        randomness: float = 0.3
    ):
        """
        Inicializa el simulador de scroll.
        
        Args:
            base_distance: Distancia base de scroll en píxeles
            base_duration: Duración base en segundos
            randomness: Factor de aleatoriedad
        """
        self.base_distance = base_distance
        self.base_duration = base_duration
        self.randomness = randomness
    
    def generate_scroll_steps(
        self,
        distance: int,
        direction: str = 'down'
    ) -> List[Tuple[int, float]]:
        """
        Genera pasos de scroll con timing.
        
        Args:
            distance: Distancia total a scrollear
            direction: 'up' o 'down'
        
        Returns:
            List[Tuple[int, float]]: Lista de (scroll_amount, delay_ms)
        """
        if distance == 0:
            return []
        
        sign = 1 if direction == 'down' else -1
        
        # Número de "movimientos de rueda"
        num_movements = max(1, int(abs(distance) / self.base_distance * random.uniform(0.8, 1.5)))
        
        steps = []
        remaining = abs(distance)
        
        for i in range(num_movements):
            if remaining <= 0:
                break
            
            # Cantidad variable por movimiento
            amount = min(
                remaining,
                int(self.base_distance * random.uniform(0.5, 1.5))
            )
            
            # Con aceleración al inicio y desaceleración al final
            progress = i / num_movements
            speed_factor = 1.0
            
            if progress < 0.2:
                # Aceleración
                speed_factor = 0.5 + progress * 2.5
            elif progress > 0.8:
                # Desaceleración
                speed_factor = 0.5 + (1 - progress) * 2.5
            
            # Delay entre movimientos
            delay = self.base_duration / num_movements * 1000 / speed_factor
            delay *= random.uniform(0.7, 1.3)
            
            steps.append((sign * amount, delay))
            remaining -= amount
        
        return steps


class HumanBehavior:
    """
    Clase principal que combina todos los comportamientos humanos.
    
    Proporciona una interfaz unificada para simular comportamiento
    humano completo en interacciones con navegadores.
    """
    
    def __init__(
        self,
        mouse_speed: float = 1.0,
        typing_speed: float = 1.0,
        error_rate: float = 0.02,
        randomness: float = 0.4
    ):
        """
        Inicializa el simulador de comportamiento.
        
        Args:
            mouse_speed: Multiplicador de velocidad de ratón
            typing_speed: Multiplicador de velocidad de escritura
            error_rate: Tasa de errores de escritura
            randomness: Factor de aleatoriedad general
        """
        self.mouse = MouseMovement(
            base_speed=800 * mouse_speed,
            randomness=randomness
        )
        self.typing = HumanTyping(
            mean_delay=50 / typing_speed,
            std_delay=20 / typing_speed,
            error_rate=error_rate
        )
        self.scroll = HumanScroll(randomness=randomness)
        self.randomness = randomness
    
    def random_delay(self, min_ms: float = 50, max_ms: float = 200) -> float:
        """
        Genera un delay aleatorio.
        
        Args:
            min_ms: Delay mínimo en milisegundos
            max_ms: Delay máximo en milisegundos
        
        Returns:
            float: Delay en milisegundos
        """
        return random.uniform(min_ms, max_ms)
    
    def thinking_pause(self, complexity: str = 'simple') -> float:
        """
        Genera una pausa de "pensamiento".
        
        Args:
            complexity: 'simple', 'medium', 'complex'
        
        Returns:
            float: Duración en milisegundos
        """
        if complexity == 'simple':
            return random.uniform(100, 500)
        elif complexity == 'medium':
            return random.uniform(500, 1500)
        else:  # complex
            return random.uniform(1500, 4000)
    
    def should_move_randomly(self) -> bool:
        """
        Determina si debe hacer un movimiento aleatorio de ratón.
        
        Returns:
            bool: True si debe mover aleatoriamente
        """
        return random.random() < self.randomness * 0.1  # 10% del randomness
    
    def generate_random_mouse_movement(
        self,
        current_x: float,
        current_y: float,
        max_distance: float = 100
    ) -> Optional[Tuple[float, float]]:
        """
        Genera un movimiento de ratón aleatorio cercano.
        
        Args:
            current_x, current_y: Posición actual
            max_distance: Distancia máxima del movimiento
        
        Returns:
            Optional[Tuple[float, float]]: Nueva posición o None
        """
        if not self.should_move_randomly():
            return None
        
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(10, max_distance)
        
        new_x = current_x + distance * math.cos(angle)
        new_y = current_y + distance * math.sin(angle)
        
        return (new_x, new_y)


def get_action_delay(action: str) -> float:
    """
    Obtiene un delay apropiado para una acción específica.
    
    Args:
        action: Tipo de acción ('click', 'type', 'scroll', 'wait', 'navigate')
    
    Returns:
        float: Delay en milisegundos
    """
    delays = {
        'click': (50, 200),
        'double_click': (100, 300),
        'type': (30, 100),
        'scroll': (50, 150),
        'wait': (500, 2000),
        'navigate': (1000, 3000),
        'form_submit': (500, 1500),
        'page_load': (1000, 3000),
    }
    
    min_delay, max_delay = delays.get(action, (100, 500))
    return random.uniform(min_delay, max_delay)


def simulate_reading_time(text_length: int, wpm: int = 250) -> float:
    """
    Simula el tiempo de lectura de un texto.
    
    Args:
        text_length: Longitud del texto en caracteres
        wpm: Palabras por minuto de lectura
    
    Returns:
        float: Tiempo de lectura en milisegundos
    """
    # Aproximadamente 5 caracteres por palabra
    words = text_length / 5
    
    # Tiempo base
    minutes = words / wpm
    ms = minutes * 60 * 1000
    
    # Añadir variación
    ms *= random.uniform(0.7, 1.3)
    
    return ms
