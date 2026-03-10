import threading
import queue
import time
import re
import logging

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

class TTSManager:
    """
    Gestor de Síntesis de Voz (Text-to-Speech) asíncrono.
    Mantiene un hilo en background que consume fragmentos de texto
    y los narra usando el motor nativo del SO (SAPI5/NSSpeech).
    """
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._enabled = False
        self._queue = queue.Queue()
        self._thread = None
        self._is_running = False
        
        # Buffer para juntar oraciones antes de decirlas
        self._buffer = ""
        
        if pyttsx3 is None:
            self.logger.warning("pyttsx3 no está instalado. El motor de voz estará deshabilitado.")
            return
            
        try:
            # Inicializar motor para verificar que funciona
            engine = pyttsx3.init()
            # Buscar y fijar voz en español
            self._set_spanish_voice(engine)
            # Opcional: Configurar velocidad
            engine.setProperty('rate', 170) 
            self._has_engine = True
        except Exception as e:
            self.logger.error(f"Fallo al inicializar motor TTS nativo: {e}")
            self._has_engine = False

    def _set_spanish_voice(self, engine):
        """Busca y establece la primera voz en español disponible."""
        try:
            voices = engine.getProperty('voices')
            for voice in voices:
                name_id = (voice.name + voice.id).lower()
                if 'spanish' in name_id or 'es_' in name_id or 'es-' in name_id or 'español' in name_id:
                    engine.setProperty('voice', voice.id)
                    self.logger.info(f"Voz configurada a: {voice.name}")
                    return
            self.logger.warning("No se encontró una voz puramente en español; se usará la default.")
        except Exception as e:
            self.logger.debug(f"Error asignando voz en español: {e}")

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        if value and not getattr(self, '_has_engine', False):
            self.logger.warning("No se puede activar la Voz porque el motor falló/no está instalado.")
            return
            
        self._enabled = value
        if self._enabled and not self._is_running:
            self._start_thread()
        elif not self._enabled and self._is_running:
            # Al apagar, limpiamos la cola
            self.stop()

    def _start_thread(self):
        self._is_running = True
        self._thread = threading.Thread(target=self._worker, daemon=True, name="TTSWorker")
        self._thread.start()
        self.logger.info("Hilo TTS iniciado.")

    def stop(self):
        self._is_running = False
        self._enabled = False
        # Limpiar cola actual
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self._buffer = ""

    def speak(self, text: str):
        """Añade texto crudo a la cola de voz si está habilitado."""
        if not self._enabled:
            return
        self._queue.put(text)

    def speak_stream_chunk(self, chunk: str):
        """
        Recibe chunks de un stream (token a token).
        Los acumula hasta formar una oración completa o puntuación final,
        momento en el que se envían al motor TTS para que la prosodia sea natural.
        """
        if not self._enabled:
            return
            
        self._buffer += chunk
        
        # Separadores de fin de pensamiento u oración
        if any(punct in chunk for punct in ['.', '!', '?', '\n']):
            sentence = self._buffer.strip()
            if sentence:
                self.speak(sentence)
            self._buffer = ""

    def flush_buffer(self):
        """Fuerza al buffer final a ser narrado."""
        if self._buffer.strip():
            self.speak(self._buffer.strip())
            self._buffer = ""

    def _clean_markdown(self, text: str) -> str:
        """Limpia el texto de símbolos Markdown para que la voz robótica no los deletree."""
        # Remover asteriscos (bold/italic)
        text = text.replace('*', '')
        # Remover formato de código
        text = re.sub(r'```.*?```', ' bloque de código ', text, flags=re.DOTALL)
        text = re.sub(r'`(.*?)`', r'\1', text)
        # Remover enlaces [texto](url) -> texto
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        # Remover hashes de títulos
        text = text.replace('#', '')
        return text.strip()

    def _worker(self):
        """Hilo en background que ejecuta los comandos bloqueantes de pyttsx3."""
        try:
            # pyttsx3.init() debe correr en el hilo que lo va a usar para evitar crashes COM de Windows
            engine = pyttsx3.init()
            self._set_spanish_voice(engine)
            engine.setProperty('rate', 170)
        except Exception:
            self._is_running = False
            return
            
        while self._is_running:
            try:
                # Timeout rápido para poder verificar el flag _is_running frecuentemente
                text = self._queue.get(timeout=0.5)
                clean_text = self._clean_markdown(text)
                
                if clean_text:
                    engine.say(clean_text)
                    engine.runAndWait()
                    
                self._queue.task_done()
            except queue.Empty:
                pass
            except Exception as e:
                self.logger.debug(f"Error en TTS worker: {e}")
                
        # Limpiar motor al salir
        try:
            engine.stop()
        except:
            pass
