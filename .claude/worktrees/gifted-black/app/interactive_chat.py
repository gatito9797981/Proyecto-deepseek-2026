#!/usr/bin/env python3
"""
Interfaz interactiva de chat para DeepSeek.

Este script proporciona una interfaz de terminal para chatear con
DeepSeek de forma interactiva, con formato bonito usando Rich.

Comandos disponibles:
    - /nuevo o /new: Iniciar nueva conversación
    - /historial o /history: Ver historial de conversaciones
    - /cargar <id>: Cargar una conversación guardada
    - /guardar [título]: Guardar la conversación actual
    - /limpiar o /clear: Limpiar la pantalla
    - /perfil o /profile: Mostrar perfil de hardware actual
    - /stats: Mostrar estadísticas
    - /ayuda o /help: Mostrar ayuda
    - /salir o /quit: Salir del programa

Uso:
    python interactive_chat.py [--headless] [--profile <nombre>]
"""

import os
import sys
import argparse
import signal
from typing import Optional

# Añadir el directorio raíz al path para imports (ahora un nivel más arriba)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.prompt import Prompt
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.theme import Theme
    from rich.live import Live
    from rich.layout import Layout
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    print("Warning: Rich not installed. Install with: pip install rich")
    print("Using basic console output instead.")

from deepseek_client.config import Config, config
from deepseek_client.client import DeepSeekClient, DeepSeekModel
from deepseek_client.profiles import get_profile_info, list_profiles


# Tema personalizado
custom_theme = Theme({
    "user": "cyan bold",
    "assistant": "green",
    "system": "yellow",
    "error": "red bold",
    "info": "blue",
    "success": "green bold",
    "thinking": "magenta italic",
})


class InteractiveChat:
    """
    Interfaz interactiva para chat con DeepSeek.
    """
    
    def __init__(
        self,
        profile_name: Optional[str] = None,
        headless: bool = False,
        config_obj: Optional[Config] = None
    ):
        """
        Inicializa la interfaz de chat.
        
        Args:
            profile_name: Nombre del perfil de hardware
            headless: Si ejecutar en modo headless
            config_obj: Configuración personalizada
        """
        self.config = config_obj or config
        self.console = Console(theme=custom_theme) if HAS_RICH else None
        
        self.profile_name = profile_name
        self.headless = headless
        self.client: Optional[DeepSeekClient] = None
        self.is_running = False
        
        # Estadísticas
        self.message_count = 0
        self.total_tokens = 0
    
    def _print(self, message: str, style: str = None):
        """Imprime un mensaje con formato."""
        if self.console:
            self.console.print(message, style=style)
        else:
            print(message)
    
    def _print_panel(self, content: str, title: str = None, style: str = None):
        """Imprime un panel con contenido."""
        if self.console:
            self.console.print(Panel(content, title=title, border_style=style))
        else:
            print(f"\n{'='*50}")
            if title:
                print(f"  {title}")
            print('='*50)
            print(content)
            print('='*50)
    
    def _print_markdown(self, content: str):
        """Imprime contenido markdown."""
        if self.console:
            self.console.print(Markdown(content))
        else:
            print(content)
    
    def show_welcome(self):
        """Muestra el mensaje de bienvenida."""
        welcome_text = """
[bold cyan]🤖 DeepSeek Client - Interfaz Interactiva[/bold cyan]

Bienvenido al cliente no oficial de DeepSeek con anti-detección avanzada.

[yellow]Comandos disponibles:[/yellow]
  • [green]/nuevo[/green] - Iniciar nueva conversación
  • [green]/historial[/green] - Ver historial de conversaciones
  • [green]/cargar <id>[/green] - Cargar conversación guardada
  • [green]/guardar [título][/green] - Guardar conversación actual
  • [green]/limpiar[/green] - Limpiar la pantalla
  • [green]/perfil[/green] - Ver perfil de hardware
  • [green]/stats[/green] - Ver estadísticas
  • [green]/ayuda[/green] - Ver esta ayuda
  • [green]/salir[/green] - Salir del programa

[dim]Escribe tu mensaje para comenzar a chatear con DeepSeek.[/dim]
"""
        self._print_panel(welcome_text, title="Bienvenido", style="cyan")
    
    def show_help(self):
        """Muestra la ayuda."""
        help_text = """
[bold]Comandos disponibles:[/bold]

[yellow]Gestión de conversaciones:[/yellow]
  /nuevo, /new           Iniciar una nueva conversación
  /historial, /history   Listar conversaciones guardadas
  /cargar <id>           Cargar una conversación específica
  /guardar [título]      Guardar la conversación actual

[yellow]Utilidades:[/yellow]
  /limpiar, /clear       Limpiar la pantalla
  /perfil, /profile      Mostrar perfil de hardware actual
  /stats                 Mostrar estadísticas de uso
  /screenshot            Tomar captura de pantalla

[yellow]Otros:[/yellow]
  /ayuda, /help          Mostrar esta ayuda
  /salir, /quit, /exit   Salir del programa

[dim]Consejo: También puedes escribir directamente tu mensaje.[/dim]
"""
        self._print_panel(help_text, title="Ayuda", style="yellow")
    
    def show_profile(self):
        """Muestra información del perfil actual."""
        profile_info = get_profile_info(self.profile_name or "random")
        
        if profile_info:
            table = Table(title="Perfil de Hardware")
            table.add_column("Propiedad", style="cyan")
            table.add_column("Valor", style="green")
            
            table.add_row("Nombre", profile_info['name'])
            table.add_row("Descripción", profile_info['description'])
            table.add_row("Plataforma", profile_info['platform'])
            table.add_row("CPU Cores", str(profile_info['cpu_cores']))
            table.add_row("Memoria", f"{profile_info['memory_gb']} GB")
            table.add_row("Pantalla", profile_info['screen'])
            table.add_row("GPU", profile_info['gpu'][:50] + "..." if len(profile_info['gpu']) > 50 else profile_info['gpu'])
            
            if self.console:
                self.console.print(table)
            else:
                for key, value in profile_info.items():
                    print(f"  {key}: {value}")
        else:
            self._print("Perfil no encontrado", style="error")
    
    def show_stats(self):
        """Muestra estadísticas de uso."""
        stats_table = Table(title="Estadísticas de Uso")
        stats_table.add_column("Métrica", style="cyan")
        stats_table.add_column("Valor", style="green")
        
        stats_table.add_row("Mensajes enviados", str(self.message_count))
        stats_table.add_row("Tokens aproximados", str(self.total_tokens))
        
        if self.client:
            history_stats = self.client.history.get_stats()
            stats_table.add_row("Conversaciones guardadas", str(history_stats['total_conversations']))
            stats_table.add_row("Total mensajes históricos", str(history_stats['total_messages']))
        
        if self.console:
            self.console.print(stats_table)
        else:
            print("\nEstadísticas:")
            print(f"  Mensajes enviados: {self.message_count}")
            print(f"  Tokens aproximados: {self.total_tokens}")
    
    def show_history(self):
        """Muestra el historial de conversaciones."""
        if not self.client:
            self._print("Cliente no inicializado", style="error")
            return
        
        conversations = self.client.list_conversations()
        
        if not conversations:
            self._print("No hay conversaciones guardadas", style="info")
            return
        
        table = Table(title="Historial de Conversaciones")
        table.add_column("ID", style="cyan")
        table.add_column("Título", style="green")
        table.add_column("Mensajes", justify="right")
        table.add_column("Actualizado", style="dim")
        
        for conv in conversations[:20]:  # Mostrar últimas 20
            table.add_row(
                conv['id'],
                conv['title'][:40] + "..." if len(conv['title']) > 40 else conv['title'],
                str(conv['message_count']),
                conv['updated_at'][:10] if conv.get('updated_at') else "N/A"
            )
        
        if self.console:
            self.console.print(table)
        else:
            print("\nHistorial de conversaciones:")
            for conv in conversations:
                print(f"  [{conv['id']}] {conv['title']} ({conv['message_count']} msgs)")
    
    def load_conversation(self, conv_id: str):
        """Carga una conversación por su ID."""
        if not self.client:
            self._print("Cliente no inicializado", style="error")
            return
        
        if self.client.load_conversation(conv_id):
            self._print(f"Conversación {conv_id} cargada", style="success")
            
            # Mostrar mensajes de la conversación
            messages = self.client.get_conversation_history()
            for msg in messages:
                role_style = "user" if msg['role'] == 'user' else "assistant"
                self._print(f"\n[{msg['role']}]: ", style=role_style)
                self._print_markdown(msg['content'])
        else:
            self._print(f"No se encontró la conversación {conv_id}", style="error")
    
    def save_conversation(self, title: str = None):
        """Guarda la conversación actual."""
        if not self.client:
            self._print("Cliente no inicializado", style="error")
            return
        
        conv_id = self.client.save_conversation(title)
        self._print(f"Conversación guardada con ID: {conv_id}", style="success")
    
    def clear_screen(self):
        """Limpia la pantalla."""
        if self.console:
            self.console.clear()
        else:
            os.system('cls' if os.name == 'nt' else 'clear')
    
    def handle_command(self, command: str) -> bool:
        """
        Maneja un comando del usuario.
        
        Args:
            command: Comando a ejecutar
        
        Returns:
            bool: True si debe continuar, False si debe salir
        """
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else None
        
        # Comandos de salida
        if cmd in ['/salir', '/quit', '/exit', '/q']:
            return False
        
        # Comandos de ayuda
        elif cmd in ['/ayuda', '/help', '/?']:
            self.show_help()
        
        # Nueva conversación
        elif cmd in ['/nuevo', '/new']:
            if self.client:
                self.client.new_conversation()
                self._print("Nueva conversación iniciada", style="success")
        
        # Historial
        elif cmd in ['/historial', '/history', '/h']:
            self.show_history()
        
        # Cargar conversación
        elif cmd in ['/cargar', '/load']:
            if args:
                self.load_conversation(args.strip())
            else:
                self._print("Uso: /cargar <id>", style="error")
        
        # Guardar conversación
        elif cmd in ['/guardar', '/save']:
            self.save_conversation(args)
        
        # Limpiar pantalla
        elif cmd in ['/limpiar', '/clear', '/cls']:
            self.clear_screen()
        
        # Perfil
        elif cmd in ['/perfil', '/profile']:
            self.show_profile()
        
        # Stats
        elif cmd == '/stats':
            self.show_stats()
        
        # Screenshot
        elif cmd in ['/screenshot', '/captura']:
            if self.client:
                path = self.client.get_screenshot()
                self._print(f"Captura guardada: {path}", style="success")
        
        # Listar perfiles
        elif cmd == '/perfiles':
            profiles = list_profiles()
            self._print("\nPerfiles disponibles:", style="info")
            for p in profiles:
                self._print(f"  • {p}")
        
        else:
            self._print(f"Comando desconocido: {cmd}", style="error")
            self._print("Usa /ayuda para ver los comandos disponibles", style="info")
        
        return True
    
    def send_message(self, message: str):
        """
        Envía un mensaje a DeepSeek y muestra la respuesta.
        
        Args:
            message: Mensaje a enviar
        """
        if not self.client:
            self._print("Error: Cliente no inicializado", style="error")
            return
        
        # Mostrar mensaje del usuario
        self._print("\n[Usuario]: ", style="user")
        self._print_markdown(message)
        
        # Enviar y recibir respuesta
        self._print("\n[DeepSeek]: ", style="assistant")
        
        try:
            # Usar streaming si Rich está disponible
            if self.console:
                response_text = ""
                
                with self.console.status("[bold green]Generando respuesta...[/bold green]"):
                    for chunk in self.client.ask_stream(message):
                        response_text += chunk
                        self.console.print(chunk, end="", style="assistant")
                
                self.console.print()  # Nueva línea
                
            else:
                # Sin Rich, usar respuesta completa
                response = self.client.ask(message)
                print(response.content)
            
            self.message_count += 1
            self.total_tokens += len(message) // 4  # Estimación
            
        except Exception as e:
            self._print(f"\nError: {e}", style="error")
    
    def initialize_client(self) -> bool:
        """
        Inicializa el cliente de DeepSeek.
        
        Returns:
            bool: True si se inicializó correctamente
        """
        self._print("Inicializando cliente DeepSeek...", style="info")
        self._print(f"Perfil: {self.profile_name or 'aleatorio'}", style="info")
        self._print(f"Modo headless: {self.headless}", style="info")
        
        try:
            self.client = DeepSeekClient(
                profile_name=self.profile_name,
                headless=self.headless,
                config_obj=self.config
            )
            self._print("Cliente inicializado correctamente", style="success")
            return True
        
        except Exception as e:
            self._print(f"Error inicializando cliente: {e}", style="error")
            return False
    
    def run(self):
        """Ejecuta el loop principal del chat."""
        # Mostrar bienvenida
        self.show_welcome()
        
        # Inicializar cliente
        if not self.initialize_client():
            return
        
        self.is_running = True
        
        # Loop principal
        while self.is_running:
            try:
                # Obtener input del usuario
                if self.console:
                    user_input = Prompt.ask("\n[bold cyan]Tú[/bold cyan]")
                else:
                    user_input = input("\nTú: ")
                
                # Ignorar input vacío
                if not user_input.strip():
                    continue
                
                # Manejar comandos (empiezan con /)
                if user_input.startswith('/'):
                    if not self.handle_command(user_input):
                        break
                else:
                    # Enviar mensaje a DeepSeek
                    self.send_message(user_input)
            
            except KeyboardInterrupt:
                self._print("\n\nInterrumpido por el usuario", style="warning")
                break
            
            except EOFError:
                break
        
        # Cleanup
        self.shutdown()
    
    def shutdown(self):
        """Limpieza al salir."""
        self._print("\nCerrando cliente...", style="info")
        
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
        
        self._print("¡Hasta pronto!", style="success")


def main():
    """Punto de entrada principal."""
    parser = argparse.ArgumentParser(
        description="Interfaz interactiva para DeepSeek",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python interactive_chat.py
  python interactive_chat.py --headless
  python interactive_chat.py --profile gaming_pc
  python interactive_chat.py --profile macbook --headless

Variables de entorno:
  ANTI_DETECTION_LEVEL  Nivel de anti-detección (basic, standard, full)
  FINGERPRINT_PROFILE   Perfil de fingerprint (random o nombre específico)
  DRIVER_POOL_SIZE      Tamaño del pool de drivers
  HEADLESS              Ejecutar en modo headless (true/false)
        """
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Ejecutar navegador en modo headless'
    )
    
    parser.add_argument(
        '--profile',
        type=str,
        default=None,
        choices=list_profiles(),
        help='Perfil de hardware a usar'
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
    import logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear y ejecutar chat
    chat = InteractiveChat(
        profile_name=args.profile,
        headless=args.headless
    )
    
    # Manejar señales
    def signal_handler(sig, frame):
        chat.is_running = False
        chat.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Ejecutar
    chat.run()


if __name__ == "__main__":
    main()
