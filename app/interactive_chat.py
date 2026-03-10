#!/usr/bin/env python3
"""
Interfaz Interactiva Profesional — DeepSeek Client
=======================================================
UI avanzada con Rich, modo streaming en tiempo real,
barra de estado persistente y sistema de comandos mejorado.
"""

import os
import sys
import logging
import argparse
import signal
import time
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.table import Table
    from rich.prompt import Prompt
    from rich.theme import Theme
    from rich.text import Text
    from rich.rule import Rule
    from rich.columns import Columns
    from rich.align import Align
    from rich.padding import Padding
    from rich.style import Style
    from rich.live import Live
    from rich.spinner import Spinner
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from deepseek_client.config import Config, config
from deepseek_client.client import DeepSeekClient, DeepSeekModel
from deepseek_client.profiles import get_profile_info, list_profiles
from deepseek_client.tts_manager import TTSManager


# ─── Paleta de colores coherente ─────────────────────────────────────────────
THEME = Theme({
    "brand":       "bold bright_cyan",
    "user_label":  "bold cyan",
    "user_msg":    "white",
    "ai_label":    "bold bright_green",
    "ai_msg":      "bright_white",
    "think_label": "bold magenta",
    "think_msg":   "magenta italic",
    "cmd":         "bold yellow",
    "success":     "bold green",
    "warning":     "bold yellow",
    "error":       "bold red",
    "info":        "bright_blue",
    "dim":         "dim white",
    "accent":      "bold bright_magenta",
    "header":      "bold bright_white on #1a1a2e",
    "status_on":   "bold bright_green",
    "status_off":  "dim white",
})

LOGO = r"""
 ██████╗ ███████╗███████╗██████╗ ███████╗███████╗██╗  ██╗
 ██╔══██╗██╔════╝██╔════╝██╔══██╗██╔════╝██╔════╝██║ ██╔╝
 ██║  ██║█████╗  █████╗  ██████╔╝███████╗█████╗  █████╔╝ 
 ██║  ██║██╔══╝  ██╔══╝  ██╔═══╝ ╚════██║██╔══╝  ██╔═██╗ 
 ██████╔╝███████╗███████╗██║     ███████║███████╗██║  ██╗
 ╚═════╝ ╚══════╝╚══════╝╚═╝     ╚══════╝╚══════╝╚═╝  ╚═╝"""


def _icon(name: str) -> str:
    icons = {
        "think": "🧠", "search": "🔍", "voice": "🎙️",
        "chat":  "💬", "save":   "💾", "load":  "📂",
        "new":   "✨", "exit":   "🚪", "help":  "❓",
        "stats": "📊", "profile": "🖥️", "shot": "📸",
        "upload": "📎", "ok": "✅", "err": "❌", "warn": "⚠️",
        "user": "👤", "ai": "🤖", "think_bubble": "💭",
    }
    return icons.get(name, "•")


class StatusBar:
    """Barra de estado reutilizable que muestra los modos activos."""

    def __init__(self, chat: "InteractiveChat"):
        self.chat = chat

    def render(self) -> Panel:
        c = self.chat

        def flag(icon, label, enabled):
            style = "status_on" if enabled else "status_off"
            state = "● ON" if enabled else "○ OFF"
            return Text.assemble(
                (f" {icon} ", ""),
                (label, style),
                (" ", ""),
                (state, style),
                ("  ", ""),
            )

        row = Text()
        row.append_text(flag(_icon("think"),  "DeepThink", c.think_enabled))
        row.append_text(flag(_icon("search"), "Search",    c.search_enabled))
        row.append_text(flag(_icon("voice"),  "Voz TTS",   c.tts.enabled))
        row.append("  │  ", style="dim")
        row.append(f"{_icon('chat')} Msgs: {c.message_count}", style="dim")
        row.append("  │  ", style="dim")
        now = datetime.now().strftime("%H:%M:%S")
        row.append(f"🕐 {now}", style="dim")

        return Panel(
            Align.center(row),
            box=box.HORIZONTALS,
            style="on #0d0d1a",
            padding=(0, 1),
        )


class InteractiveChat:
    """Interfaz interactiva avanzada para DeepSeek."""

    COMMANDS = {
        # Toggles
        "/think":       ("think",   "Alternar modo DeepThink R1"),
        "/t":           ("think",   ""),
        "/search":      ("search",  "Alternar búsqueda web"),
        "/s":           ("search",  ""),
        "/voz":         ("voice",   "Alternar narración TTS"),
        "/voice":       ("voice",   ""),
        "/v":           ("voice",   ""),
        # Conversación
        "/nuevo":       ("new",     "Nueva conversación"),
        "/new":         ("new",     ""),
        "/historial":   ("history", "Ver historial de chats"),
        "/history":     ("history", ""),
        "/h":           ("history", ""),
        "/cargar":      ("load",    "Cargar conversación por ID"),
        "/load":        ("load",    ""),
        "/guardar":     ("save",    "Guardar conversación actual"),
        "/save":        ("save",    ""),
        "/exportar":    ("export",  "Exportar conversación a .txt"),
        # Archivos
        "/upload":      ("upload",  "Subir archivo al chat"),
        "/subir":       ("upload",  ""),
        # Utilidades
        "/limpiar":     ("clear",   "Limpiar pantalla"),
        "/clear":       ("clear",   ""),
        "/cls":         ("clear",   ""),
        "/perfil":      ("profile", "Ver perfil de hardware"),
        "/profile":     ("profile", ""),
        "/perfiles":    ("profiles","Listar todos los perfiles"),
        "/stats":       ("stats",   "Estadísticas de sesión"),
        "/screenshot":  ("shot",    "Captura de pantalla del navegador"),
        "/captura":     ("shot",    ""),
        "/modelo":      ("model",   "Cambiar modelo (chat/reasoner)"),
        "/ping":        ("ping",    "Verificar conexión con DeepSeek"),
        # Meta
        "/ayuda":       ("help",    "Mostrar esta ayuda"),
        "/help":        ("help",    ""),
        "/?":           ("help",    ""),
        "/salir":       ("exit",    "Salir del programa"),
        "/quit":        ("exit",    ""),
        "/exit":        ("exit",    ""),
        "/q":           ("exit",    ""),
    }

    SHORTCUTS = {
        "1": "/think",
        "2": "/search",
        "3": "/voz",
        "4": "/historial",
        "5": "/nuevo",
        "6": "/stats",
        "7": "/guardar",
        "8": "/salir",
    }

    def __init__(
        self,
        profile_name: Optional[str] = None,
        headless: bool = False,
        config_obj: Optional[Config] = None,
        initial_think: bool = False,
        initial_search: bool = False,
        initial_voice: bool = False,
    ):
        self.config       = config_obj or config
        self.console      = Console(theme=THEME) if HAS_RICH else None
        self.profile_name = profile_name
        self.headless     = headless
        self.client: Optional[DeepSeekClient] = None
        self.is_running   = False
        self.tts          = TTSManager(self.config.setup_logging())
        self.status_bar   = StatusBar(self)

        # Estado de modos
        self.think_enabled  = initial_think
        self.search_enabled = initial_search
        self.tts.enabled    = initial_voice

        # Stats
        self.message_count  = 0
        self.session_start  = datetime.now()

    # ── Helpers de impresión ─────────────────────────────────────────────────

    def out(self, msg, style: str = ""):
        if self.console:
            self.console.print(msg, style=style or "")
        else:
            print(msg if isinstance(msg, str) else str(msg))

    def rule(self, title: str = "", style: str = "dim"):
        if self.console:
            self.console.print(Rule(title, style=style))

    def success(self, msg: str):
        self.out(f"  {_icon('ok')} {msg}", "success")

    def error(self, msg: str):
        self.out(f"  {_icon('err')} {msg}", "error")

    def info(self, msg: str):
        self.out(f"  ℹ  {msg}", "info")

    def warn(self, msg: str):
        self.out(f"  {_icon('warn')} {msg}", "warning")

    # ── Pantallas principales ────────────────────────────────────────────────

    def show_splash(self):
        """Pantalla de bienvenida con logo ASCII."""
        if not self.console:
            print("=== DeepSeek Interactive Chat ===")
            return

        self.console.clear()
        logo_text = Text(LOGO, style="bold bright_cyan")
        tagline    = Text(
            "  Cliente no oficial con anti-detección avanzada • Selenium + Rich TUI",
            style="dim italic"
        )
        version    = Text("  v2.0 Pro  •  Marzo 2026", style="dim")

        self.console.print(Align.center(logo_text))
        self.console.print(Align.center(tagline))
        self.console.print(Align.center(version))
        self.console.print()

    def show_shortcut_menu(self):
        """Menú de atajos numéricos compacto sobre el prompt."""
        if not self.console:
            return

        think_s  = "[status_on]ON[/status_on]"  if self.think_enabled  else "[status_off]OFF[/status_off]"
        search_s = "[status_on]ON[/status_on]"  if self.search_enabled else "[status_off]OFF[/status_off]"
        voz_s    = "[status_on]ON[/status_on]"  if self.tts.enabled    else "[status_off]OFF[/status_off]"

        lines = (
            f"  [cmd]\\[1][/cmd] 🧠 Think {think_s}  "
            f"[cmd]\\[2][/cmd] 🔍 Search {search_s}  "
            f"[cmd]\\[3][/cmd] 🎙️ Voz {voz_s}  "
            f"[dim]│[/dim]  "
            f"[cmd]\\[4][/cmd] 📂 Historial  "
            f"[cmd]\\[5][/cmd] ✨ Nuevo  "
            f"[cmd]\\[6][/cmd] 📊 Stats  "
            f"[cmd]\\[7][/cmd] 💾 Guardar  "
            f"[cmd]\\[8][/cmd] 🚪 Salir"
        )
        self.console.print(Panel(lines, box=box.SIMPLE, style="on #0d0d1a", padding=(0, 0)))

    def show_help(self):
        """Tabla de ayuda completa y bien formateada."""
        if not self.console:
            print("Comandos: /think /search /voz /nuevo /historial /guardar /salir")
            return

        self.rule("AYUDA — Comandos disponibles", "bright_cyan")
        sections = [
            ("🧠 Modos IA", [
                ("/think  /t  [1]",  "Alternar DeepThink R1 (razonamiento extendido)"),
                ("/search /s  [2]",  "Alternar búsqueda web en tiempo real"),
                ("/voz    /v  [3]",  "Alternar narración TTS en español"),
                ("/modelo",          "Cambiar modelo (deepseek-chat / deepseek-reasoner)"),
            ]),
            ("💬 Conversación", [
                ("/nuevo  /new  [5]",      "Iniciar nueva conversación"),
                ("/historial  /h  [4]",    "Ver historial y cargar conversación"),
                ("/cargar <id>",           "Cargar conversación por ID o prefijo"),
                ("/guardar [título]  [7]", "Guardar conversación actual con título opcional"),
                ("/exportar",             "Exportar conversación actual a archivo .txt"),
            ]),
            ("📎 Archivos", [
                ("/upload <ruta>",  "Subir documento o imagen al chat activo"),
            ]),
            ("🛠 Utilidades", [
                ("/stats  [6]",     "Ver estadísticas de la sesión actual"),
                ("/perfil",         "Ver perfil de hardware/fingerprint activo"),
                ("/perfiles",       "Listar todos los perfiles disponibles"),
                ("/screenshot",     "Captura de pantalla del navegador"),
                ("/ping",           "Verificar conexión con DeepSeek"),
                ("/limpiar",        "Limpiar la pantalla"),
            ]),
            ("❌ Salida", [
                ("/salir  /q  [8]", "Guardar y salir del programa"),
            ]),
        ]

        for title, cmds in sections:
            t = Table(
                title=title, box=box.SIMPLE_HEAVY,
                title_style="bold bright_cyan", show_header=False,
                padding=(0, 2), expand=False
            )
            t.add_column("Comando", style="cmd", no_wrap=True, min_width=28)
            t.add_column("Descripción", style="dim white")
            for cmd, desc in cmds:
                t.add_row(cmd, desc)
            self.console.print(t)

        self.console.print(
            Padding("[dim]Consejo: tambien puedes escribir numeros del 1-8 como atajos.[/dim]", (1, 4))
        )
        self.rule("", "dim")

    def show_profile(self):
        """Tabla del perfil de hardware activo."""
        profile_name = self.profile_name or (self.config.fingerprint_profile if hasattr(self.config, 'fingerprint_profile') else "random")
        info = get_profile_info(profile_name)

        if not info:
            self.warn(f"Perfil '{profile_name}' no encontrado. Es posible que se use uno random.")
            return

        t = Table(
            title=f"{_icon('profile')} Perfil de Hardware — {info['name']}",
            box=box.ROUNDED, border_style="bright_cyan", show_header=False, padding=(0, 2)
        )
        t.add_column("Propiedad", style="info", min_width=16)
        t.add_column("Valor",     style="bright_white")

        t.add_row("Descripción", info["description"])
        t.add_row("Plataforma",  info["platform"])
        t.add_row("CPU Cores",   str(info["cpu_cores"]))
        t.add_row("RAM",         f"{info['memory_gb']} GB")
        t.add_row("Resolución",  info["screen"])
        gpu = info["gpu"]
        t.add_row("GPU", (gpu[:60] + "…") if len(gpu) > 60 else gpu)

        self.out(t)

    def show_stats(self):
        """Panel de estadísticas de la sesión."""
        elapsed = datetime.now() - self.session_start
        mins    = int(elapsed.total_seconds() // 60)
        secs    = int(elapsed.total_seconds() % 60)

        rows = [
            ("Mensajes enviados",     str(self.message_count)),
            ("Tiempo de sesión",      f"{mins}m {secs}s"),
            ("DeepThink activo",      "✅ Sí" if self.think_enabled  else "❌ No"),
            ("Búsqueda activa",       "✅ Sí" if self.search_enabled else "❌ No"),
            ("Voz TTS activa",        "✅ Sí" if self.tts.enabled    else "❌ No"),
            ("Modo headless",         "✅ Sí" if self.headless       else "❌ No"),
            ("Perfil hardware",       self.profile_name or "random"),
        ]

        if self.client:
            hist = self.client.history.get_stats()
            rows += [
                ("Conversaciones guardadas", str(hist.get("total_conversations", 0))),
                ("Total msgs históricos",    str(hist.get("total_messages", 0))),
            ]

        t = Table(
            title=f"{_icon('stats')} Estadísticas de Sesión",
            box=box.ROUNDED, border_style="bright_magenta", show_header=False, padding=(0, 2)
        )
        t.add_column("Métrica", style="info",         min_width=26)
        t.add_column("Valor",   style="bright_white")

        for label, val in rows:
            t.add_row(label, val)

        self.out(t)

    def show_history(self):
        """Tabla interactiva del historial de conversaciones."""
        if not self.client:
            self.error("Cliente no inicializado.")
            return

        conversations = self.client.list_conversations()
        if not conversations:
            self.info("No hay conversaciones guardadas todavía.")
            return

        t = Table(
            title=f"{_icon('load')} Historial de Conversaciones",
            box=box.ROUNDED, border_style="bright_blue",
            show_lines=False, padding=(0, 1)
        )
        t.add_column("#",        style="dim",         width=4, justify="right")
        t.add_column("ID",       style="bright_blue", width=10, no_wrap=True)
        t.add_column("Título",   style="bright_white",max_width=44)
        t.add_column("Msgs",     justify="right",     style="info",  width=6)
        t.add_column("Fecha",    style="dim",         width=12)

        for i, conv in enumerate(conversations[:25], 1):
            title   = conv["title"]
            title   = (title[:42] + "…") if len(title) > 42 else title
            id_short = conv["id"][:8]
            fecha   = (conv.get("updated_at") or conv.get("created_at") or "")[:10]
            t.add_row(str(i), id_short, title, str(conv["message_count"]), fecha)

        self.out(t)

        if self.console:
            choice = Prompt.ask(
                "\n  [bold cyan]ID o nº a cargar[/bold cyan] [dim](Enter para cancelar)[/dim]",
                default=""
            ).strip()
        else:
            choice = input("\n  ID o nº a cargar (Enter cancela): ").strip()

        if not choice:
            return

        # Resolver por número de fila
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(conversations):
                self._load_by_id(conversations[idx]["id"])
                return

        # Resolver por prefijo de ID
        matches = [c["id"] for c in conversations if c["id"].startswith(choice)]
        if matches:
            self._load_by_id(matches[0])
        else:
            self.error(f"No se encontró ninguna conversación con '{choice}'.")

    def _load_by_id(self, conv_id: str):
        """Carga y muestra una conversación por su ID completo."""
        if self.client.load_conversation(conv_id):
            self.success(f"Conversación {conv_id[:8]}… cargada.")
            self.rule("Historial de mensajes", "bright_blue")
            for msg in self.client.get_conversation_history(limit=20):
                if msg["role"] == "user":
                    self._show_user_bubble(msg["content"])
                else:
                    self._show_ai_bubble(msg["content"])
            self.rule("", "dim")
        else:
            self.error(f"No se encontró la conversación {conv_id}.")

    def show_profiles_list(self):
        """Lista todos los perfiles de hardware disponibles."""
        profiles = list_profiles()
        t = Table(
            title=f"{_icon('profile')} Perfiles de Hardware disponibles",
            box=box.SIMPLE_HEAVY, border_style="cyan", show_header=False
        )
        t.add_column("Perfil", style="cmd")
        for p in profiles:
            active = " ← activo" if p == (self.profile_name or "") else ""
            t.add_row(p + active)
        self.out(t)

    # ── Burbujas de chat ─────────────────────────────────────────────────────

    def _show_user_bubble(self, content: str):
        self.rule()
        if self.console:
            self.console.print(
                Panel(
                    Markdown(content) if len(content) > 80 else Text(content, style="user_msg"),
                    title=f"[user_label]{_icon('user')} Tú[/user_label]",
                    title_align="left",
                    border_style="cyan",
                    padding=(0, 2),
                )
            )
        else:
            print(f"\n[TÚ]: {content}")

    def _show_thinking_header(self):
        if self.console:
            self.console.print(
                Panel(
                    "",
                    title=f"[think_label]{_icon('think_bubble')} Pensamiento DeepSeek[/think_label]",
                    title_align="left",
                    border_style="magenta",
                    padding=(0, 1),
                )
            )

    def _show_ai_bubble(self, content: str, thinking: str = ""):
        if self.console:
            body = Markdown(content) if content.strip() else Text("")
            self.console.print(
                Panel(
                    body,
                    title=f"[ai_label]{_icon('ai')} DeepSeek[/ai_label]",
                    title_align="left",
                    border_style="bright_green",
                    padding=(0, 2),
                )
            )
        else:
            print(f"\n[DeepSeek]: {content}")

    # ── Lógica de envío ──────────────────────────────────────────────────────

    def send_message(self, message: str):
        """Envía el mensaje y muestra la respuesta en streaming."""
        if not self.client:
            self.error("Cliente no inicializado.")
            return

        self._show_user_bubble(message)

        # Sincronizar modos antes de enviar
        self.client.toggle_deepthink(self.think_enabled)
        self.client.toggle_search(self.search_enabled)

        full_response = ""

        try:
            if self.console:
                # Streaming con panel dinámico
                panel_title  = f"[ai_label]{_icon('ai')} DeepSeek[/ai_label]"
                joined       = ""                # Acumulador de texto (más eficiente que join(list) en cada ciclo)
                _last_render = 0.0               # Timestamp del último repintado
                _RENDER_MS   = 0.08             # Throttle: repintar máximo cada 80ms (~12fps)

                THINK_SEP = "\n\n🤔 **Pensamiento de DeepSeek:**\n"
                RESP_SEP  = "\n\n💡 **Respuesta:**\n"

                with Live(
                    Panel("…", title=panel_title, border_style="bright_green", padding=(0, 2)),
                    console=self.console,
                    auto_refresh=False,          # Desactivar auto-refresh; nosotros controlamos cuándo redibujar
                    vertical_overflow="visible",
                ) as live:
                    for chunk in self.client.ask_stream(message):
                        joined       += chunk
                        full_response += chunk
                        self.tts.speak_stream_chunk(chunk)

                        # Throttle: solo redibujar si han pasado >= 80ms desde el último repintado
                        now = time.monotonic()
                        if now - _last_render < _RENDER_MS:
                            continue
                        _last_render = now

                        # Construir texto de visualización separando Pensamiento y Respuesta
                        display_text = Text()
                        if THINK_SEP in joined:
                            _, after_think = joined.split(THINK_SEP, 1)
                            if RESP_SEP in after_think:
                                think_content, resp_content = after_think.split(RESP_SEP, 1)
                                display_text.append(f"💭 {think_content.strip()}\n\n", style="think_msg")
                                display_text.append(f"💡 {resp_content}", style="ai_msg")
                            else:
                                display_text.append(f"💭 {after_think}", style="think_msg")
                        else:
                            display_text.append(joined, style="ai_msg")

                        live.update(Panel(
                            display_text,
                            title=panel_title,
                            border_style="bright_green",
                            padding=(0, 2),
                        ))
                        live.refresh()           # Forzar repintado manual solo cuando el throttle lo permite

                    # Repintado final con el texto completo (garantiza que el último chunk siempre se muestra)
                    if joined:
                        display_text = Text()
                        if THINK_SEP in joined:
                            _, after_think = joined.split(THINK_SEP, 1)
                            if RESP_SEP in after_think:
                                think_content, resp_content = after_think.split(RESP_SEP, 1)
                                display_text.append(f"💭 {think_content.strip()}\n\n", style="think_msg")
                                display_text.append(f"💡 {resp_content}", style="ai_msg")
                            else:
                                display_text.append(f"💭 {after_think}", style="think_msg")
                        else:
                            display_text.append(joined, style="ai_msg")
                        live.update(Panel(display_text, title=panel_title, border_style="bright_green", padding=(0, 2)))
                        live.refresh()

                self.tts.flush_buffer()

            else:
                # Sin Rich: respuesta completa
                response      = self.client.ask(message)
                full_response = response.content
                print(f"\n[DeepSeek]: {full_response}")
                if full_response:
                    self.tts.speak(full_response)

            self.message_count += 1

        except KeyboardInterrupt:
            self.warn("Respuesta interrumpida.")
        except Exception as e:
            self.error(f"Error al obtener respuesta: {e}")

    # ── Comandos ─────────────────────────────────────────────────────────────

    def handle_command(self, raw: str) -> bool:
        """Interpreta el comando y ejecuta la acción correspondiente. Devuelve False para salir."""
        parts = raw.strip().split(maxsplit=1)
        key   = parts[0].lower()
        arg   = parts[1].strip() if len(parts) > 1 else None

        action = self.COMMANDS.get(key, (None, None))[0]

        # ─ toggles ─
        if action == "think":
            self.think_enabled = not self.think_enabled
            label = "ON ✅" if self.think_enabled else "OFF ❌"
            msg   = f"{_icon('think')} DeepThink {label}"
            (self.success if self.think_enabled else self.warn)(msg)
            if self.client:
                self.client.toggle_deepthink(self.think_enabled)

        elif action == "search":
            self.search_enabled = not self.search_enabled
            label = "ON ✅" if self.search_enabled else "OFF ❌"
            (self.success if self.search_enabled else self.warn)(f"{_icon('search')} Search {label}")
            if self.client:
                self.client.toggle_search(self.search_enabled)

        elif action == "voice":
            self.tts.enabled = not self.tts.enabled
            label = "ON ✅" if self.tts.enabled else "OFF ❌"
            (self.success if self.tts.enabled else self.warn)(f"{_icon('voice')} Voz TTS {label}")

        # ─ conversación ─
        elif action == "new":
            if self.client:
                self.client.new_conversation()
            self.message_count = 0
            self.success(f"{_icon('new')} Nueva conversación iniciada.")

        elif action == "history":
            self.show_history()

        elif action == "load":
            if arg:
                self._load_by_id(arg)
            else:
                self.show_history()

        elif action == "save":
            if self.client:
                title  = arg or datetime.now().strftime("Chat %Y-%m-%d %H:%M")
                cid    = self.client.save_conversation(title)
                self.success(f"{_icon('save')} Guardado con ID: {cid[:8]}…")
            else:
                self.error("No hay cliente activo.")

        elif action == "export":
            self._export_conversation()

        # ─ archivos ─
        elif action == "upload":
            if not arg:
                self.warn("Uso: /upload <C:/ruta/al/archivo.pdf>")
            elif not os.path.exists(arg):
                self.error(f"El archivo no existe: {arg}")
            elif self.client:
                if self.client.upload_file(arg):
                    self.success(f"{_icon('upload')} Archivo adjuntado: {os.path.basename(arg)}")
                else:
                    self.error("No se pudo adjuntar el archivo.")
            else:
                self.error("Cliente no inicializado.")

        # ─ utilidades ─
        elif action == "stats":
            self.show_stats()

        elif action == "profile":
            self.show_profile()

        elif action == "profiles":
            self.show_profiles_list()

        elif action == "shot":
            if self.client:
                path = self.client.get_screenshot()
                self.success(f"{_icon('shot')} Captura guardada: {path}")
            else:
                self.error("Cliente no inicializado.")

        elif action == "model":
            self._switch_model_interactive()

        elif action == "ping":
            self._ping()

        elif action == "clear":
            if self.console:
                self.console.clear()
                self.show_splash()

        elif action == "help":
            self.show_help()

        elif action == "exit":
            return False

        else:
            self.error(f"Comando desconocido: [bold]{key}[/bold]")
            self.info("Escribe [cmd]/ayuda[/cmd] para ver todos los comandos.")

        return True

    def _switch_model_interactive(self):
        """Menú para cambiar el modelo de IA."""
        if not self.client:
            self.error("Cliente no inicializado.")
            return

        if self.console:
            choice = Prompt.ask(
                "  [bold cyan]Elige modelo[/bold cyan]",
                choices=["chat", "reasoner"],
                default="chat"
            )
        else:
            choice = input("Modelo (chat/reasoner): ").strip()

        model_map = {
            "chat":      DeepSeekModel.DEEPSEEK_CHAT,
            "reasoner":  DeepSeekModel.DEEPSEEK_REASONER,
        }
        model = model_map.get(choice)
        if model:
            self.client._switch_model(model)
            self.success(f"Modelo cambiado a: [bold]{choice}[/bold]")
        else:
            self.error("Modelo no válido.")

    def _ping(self):
        """Verifica la conexión activa con DeepSeek."""
        if not self.client:
            self.error("Cliente no inicializado.")
            return
        try:
            url = self.client.driver.driver.current_url
            if "deepseek.com" in url:
                self.success(f"Conexión OK — {url}")
            else:
                self.warn(f"En página inesperada: {url}")
        except Exception as e:
            self.error(f"Error de conexión: {e}")

    def _export_conversation(self):
        """Exporta la conversación actual a un archivo .txt."""
        if not self.client:
            self.error("Cliente no inicializado.")
            return

        messages = self.client.get_conversation_history(limit=200)
        if not messages:
            self.info("No hay mensajes en la conversación actual.")
            return

        fname = f"deepseek_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(f"# Exportación DeepSeek — {datetime.now().isoformat()}\n\n")
            for msg in messages:
                role = "Tú" if msg["role"] == "user" else "DeepSeek"
                f.write(f"## {role}\n{msg['content']}\n\n---\n\n")

        self.success(f"Conversación exportada a: {fname}")

    # ── Inicialización ───────────────────────────────────────────────────────

    def initialize_client(self) -> bool:
        """Inicializa el cliente con spinner de carga."""
        if self.console:
            with self.console.status(
                "[info]Iniciando navegador con anti-detección…[/info]",
                spinner="dots2",
            ):
                try:
                    self.client = DeepSeekClient(
                        profile_name=self.profile_name,
                        headless=self.headless,
                        config_obj=self.config,
                    )
                except Exception as e:
                    self.error(f"Error inicializando cliente: {e}")
                    return False
        else:
            try:
                self.client = DeepSeekClient(
                    profile_name=self.profile_name,
                    headless=self.headless,
                    config_obj=self.config,
                )
            except Exception as e:
                print(f"Error: {e}")
                return False

        self.success("Cliente DeepSeek inicializado correctamente.")
        return True

    # ── Loop principal ───────────────────────────────────────────────────────

    def run(self):
        """Loop principal del chat."""
        self.show_splash()

        if not self.initialize_client():
            return

        self.is_running = True
        self.show_help()

        while self.is_running:
            try:
                # Mostrar menú de atajos + barra de estado
                if self.console:
                    self.console.print()
                    self.show_shortcut_menu()
                    self.out(self.status_bar.render())
                    user_input = Prompt.ask(
                        "\n  [bold bright_cyan]Tú[/bold bright_cyan] [dim]»[/dim]"
                    )
                else:
                    user_input = input("\nTú > ")

                text = user_input.strip()
                if not text:
                    continue

                # Atajos numéricos
                if text in self.SHORTCUTS:
                    if not self.handle_command(self.SHORTCUTS[text]):
                        break
                    continue

                # Comandos con /
                if text.startswith("/"):
                    if not self.handle_command(text):
                        break
                    continue

                # Mensaje normal
                self.send_message(text)

            except KeyboardInterrupt:
                self.tts.stop()
                self.out("\n")
                self.warn("Interrupted — usa [cmd]/salir[/cmd] para salir correctamente.")
            except EOFError:
                break

        self.shutdown()

    def shutdown(self):
        """Limpieza y cierre."""
        self.rule("Cerrando…", "dim")
        self.tts.stop()
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
        self.success("¡Hasta la próxima! 👋")


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="DeepSeek Interactive Chat — UI Profesional",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python interactive_chat.py
  python interactive_chat.py --headless
  python interactive_chat.py --profile gaming_pc --think
  python interactive_chat.py --profile macbook --search --log-level DEBUG
        """
    )
    parser.add_argument("--headless",   action="store_true",  help="Navegador en modo headless")
    parser.add_argument("--profile",    default=None,         choices=list_profiles(), help="Perfil de hardware")
    parser.add_argument("--think",      action="store_true",  help="Iniciar con DeepThink activado")
    parser.add_argument("--search",     action="store_true",  help="Iniciar con Búsqueda activada")
    parser.add_argument("--voice",      action="store_true",  help="Iniciar con Voz TTS activada")
    parser.add_argument("--log-level",  default="WARNING",    choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    chat = InteractiveChat(
        profile_name=args.profile,
        headless=args.headless,
        initial_think=args.think,
        initial_search=args.search,
        initial_voice=args.voice,
    )

    def _sig(sig, frame):
        chat.is_running = False
        chat.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _sig)
    signal.signal(signal.SIGTERM, _sig)

    chat.run()


if __name__ == "__main__":
    main()
