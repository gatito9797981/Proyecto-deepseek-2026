"""
Perfiles de hardware para fingerprinting.

Este módulo define perfiles de hardware predefinidos que simulan
diferentes tipos de dispositivos. Cada perfil tiene valores coherentes
y realistas para evitar inconsistencias que puedan ser detectadas.

Perfiles disponibles:
    - gaming_pc: PC de gaming de alta gama
    - work_laptop: Laptop de trabajo corporativo
    - macbook: MacBook Pro moderno
    - linux_dev: Estación de desarrollo Linux
    - budget_pc: PC de gama media/baja
    - surface_pro: Microsoft Surface Pro

Uso:
    from deepseek_client.profiles import get_profile, get_random_profile
    
    # Obtener un perfil específico
    profile = get_profile("gaming_pc")
    
    # Obtener un perfil aleatorio
    profile = get_random_profile()
"""

import random
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class HardwareProfile:
    """
    Perfil de hardware completo para fingerprinting.
    
    Attributes:
        name: Nombre identificador del perfil.
        description: Descripción humana del perfil.
        platform: Plataforma del sistema operativo.
        hardware_concurrency: Número de hilos de CPU.
        device_memory: Memoria del dispositivo en GB.
        webgl_vendor: Vendor de WebGL.
        webgl_renderer: Renderer de WebGL.
        screen_width: Ancho de pantalla.
        screen_height: Alto de pantalla.
        device_pixel_ratio: Ratio de píxeles del dispositivo.
        timezone: Zona horaria.
        languages: Lista de idiomas del navegador.
        user_agent: User agent string.
        fonts: Lista de fuentes disponibles.
        plugins: Lista de plugins del navegador.
        seed_base: Base para generar semillas deterministas.
    """
    name: str
    description: str
    platform: str
    hardware_concurrency: int
    device_memory: int
    webgl_vendor: str
    webgl_renderer: str
    screen_width: int
    screen_height: int
    device_pixel_ratio: float = 1.0
    timezone: str = "America/New_York"
    languages: List[str] = field(default_factory=lambda: ["en-US", "en"])
    user_agent: str = ""
    fonts: List[str] = field(default_factory=list)
    plugins: List[Dict[str, str]] = field(default_factory=list)
    seed_base: int = 0
    
    def __post_init__(self):
        """Genera user agent si no está definido."""
        if not self.user_agent:
            self.user_agent = self._generate_user_agent()
        if not self.fonts:
            self.fonts = self._get_default_fonts()
        if not self.plugins:
            self.plugins = self._get_default_plugins()
    
    def _generate_user_agent(self) -> str:
        """Genera un user agent realista basado en el perfil."""
        chrome_version = f"{random.randint(110, 120)}.0.{random.randint(5000, 6000)}.{random.randint(100, 200)}"
        
        if self.platform == "Win32":
            return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"
        elif self.platform == "MacIntel":
            return f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"
        elif self.platform == "Linux x86_64":
            return f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"
        else:
            return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"
    
    def _get_default_fonts(self) -> List[str]:
        """Devuelve fuentes por defecto según la plataforma."""
        if self.platform == "Win32":
            return [
                "Arial", "Arial Black", "Arial Narrow", "Calibri", "Cambria",
                "Cambria Math", "Comic Sans MS", "Consolas", "Courier", "Courier New",
                "Georgia", "Impact", "Lucida Console", "Lucida Sans Unicode",
                "Microsoft Sans Serif", "Palatino Linotype", "Segoe UI", "Tahoma",
                "Times", "Times New Roman", "Trebuchet MS", "Verdana"
            ]
        elif self.platform == "MacIntel":
            return [
                "American Typewriter", "Andale Mono", "Arial", "Arial Black",
                "Arial Narrow", "Arial Rounded MT Bold", "Avenir", "Avenir Next",
                "Baskerville", "Big Caslon", "Bodoni 72", "Bradley Hand", "Brush Script MT",
                "Chalkboard", "Chalkboard SE", "Chalkduster", "Charter", "Cochin",
                "Comic Sans MS", "Copperplate", "Courier", "Courier New", "DIN Alternate",
                "Futura", "Geneva", "Gill Sans", "Helvetica", "Helvetica Neue", "Herculanum",
                "Impact", "InaiMathi", "Kailasa", "Kannada MN", "Kannada Sangam MN",
                "Kefa", "Khmer MN", "Khmer Sangam MN", "Kohinoor Bangla", "Kohinoor Devanagari",
                "Kohinoor Gujarati", "Kohinoor Telugu", "Kokonor", "Krungthep", "KufiStandardGK",
                "Lao MN", "Lao Sangam MN", "Lucida Grande", "Luminari", "Malayalam MN",
                "Malayalam Sangam MN", "Marker Felt", "Menlo", "Microsoft Sans Serif",
                "Mishafi", "Mishafi Gold", "Monaco", "Mshtakan", "Mukta Mahee",
                "Muna", "Myanmar MN", "Myanmar Sangam MN", "Nadeem", "New Peninim MT",
                "Noteworthy", "Noto Nastaliq Urdu", "Noto Sans Kannada", "Noto Sans Myanmar",
                "Noto Sans Oriya", "Noto Serif Myanmar", "Optima", "Oriya MN",
                "Oriya Sangam MN", "PT Mono", "PT Sans", "PT Serif", "Palatino",
                "Papyrus", "Phosphate", "PingFang HK", "PingFang SC", "PingFang TC",
                "Plantagenet Cherokee", "Raanana", "Rockwell", "STIX Two Math", "STIX Two Text",
                "STIXGeneral", "STIXIntegralsD", "STIXIntegralsSm", "STIXIntegralsUp",
                "STIXIntegralsUpD", "STIXIntegralsUpSm", "STIXNonUnicode", "STIXSizeFiveSym",
                "STIXSizeFourSym", "STIXSizeOneSym", "STIXSizeThreeSym", "STIXSizeTwoSym",
                "STIXVariants", "Sana", "Sathu", "Savoye LET", "SignPainter", "Silom",
                "Sinhala MN", "Sinhala Sangam MN", "Skia", "Snell Roundhand", "Songti SC",
                "Songti TC", "STFangsong", "STHeiti", "STKaiti", "STSong", "Sukhumvit Set",
                "Symbol", "System Font", "Tamil MN", "Tamil Sangam MN", "Telugu MN",
                "Telugu Sangam MN", "Thonburi", "Times", "Times New Roman", "Trattatello",
                "Trebuchet MS", "Verdana", "Waseem", "Zapf Dingbats", "Zapfino"
            ]
        else:  # Linux
            return [
                "Arial", "Cantarell", "Comic Sans MS", "Courier New", "DejaVu Sans",
                "DejaVu Sans Mono", "DejaVu Serif", "Droid Sans", "FreeMono", "FreeSans",
                "FreeSerif", "Garuda", "Georgia", "Impact", "Liberation Mono",
                "Liberation Sans", "Liberation Serif", "Loma", "Norasi", "Noto Color Emoji",
                "Noto Mono", "Noto Sans", "Noto Sans CJK SC", "Noto Sans CJK TC",
                "Noto Serif", "Purisa", "Sawasdee", "TlwgMono", "TlwgTypewriter",
                "Tlwg Typist", "Tlwg Typo", "Ubuntu", "Ubuntu Condensed", "Ubuntu Mono",
                "Umpush", "URW Bookman", "URW Gothic", "URW Palladio", "Verdana", "Waree"
            ]
    
    def _get_default_plugins(self) -> List[Dict[str, str]]:
        """Devuelve plugins por defecto."""
        return [
            {"name": "Chrome PDF Plugin", "filename": "internal-pdf-viewer", "description": "Portable Document Format"},
            {"name": "Chrome PDF Viewer", "filename": "mhjfbmdgcfjbbpaeojofohoefgiehjai", "description": ""},
            {"name": "Native Client", "filename": "internal-nacl-plugin", "description": ""},
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el perfil a diccionario."""
        return {
            "name": self.name,
            "description": self.description,
            "platform": self.platform,
            "hardware_concurrency": self.hardware_concurrency,
            "device_memory": self.device_memory,
            "webgl_vendor": self.webgl_vendor,
            "webgl_renderer": self.webgl_renderer,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "device_pixel_ratio": self.device_pixel_ratio,
            "timezone": self.timezone,
            "languages": self.languages,
            "user_agent": self.user_agent,
            "fonts": self.fonts,
            "plugins": self.plugins,
            "seed_base": self.seed_base,
        }
    
    def get_seed(self, instance_id: int = 0) -> int:
        """
        Genera una semilla determinista para una instancia.
        
        Args:
            instance_id: ID de la instancia (para múltiples navegadores).
        
        Returns:
            int: Semilla para el generador de fingerprint.
        """
        return self.seed_base + instance_id * 10000 + random.randint(0, 9999)


# ============================================================================
# DEFINICIÓN DE PERFILES
# ============================================================================

PROFILES: Dict[str, HardwareProfile] = {
    "gaming_pc": HardwareProfile(
        name="gaming_pc",
        description="PC de gaming de alta gama con GPU NVIDIA RTX",
        platform="Win32",
        hardware_concurrency=16,  # Ryzen 9 o Intel i9
        device_memory=32,
        webgl_vendor="Google Inc. (NVIDIA)",
        webgl_renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 4090 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        screen_width=2560,
        screen_height=1440,
        timezone="America/New_York",
        languages=["en-US", "en"],
        seed_base=100000,
    ),
    
    "gaming_pc_amd": HardwareProfile(
        name="gaming_pc_amd",
        description="PC de gaming con GPU AMD Radeon",
        platform="Win32",
        hardware_concurrency=12,
        device_memory=16,
        webgl_vendor="Google Inc. (AMD)",
        webgl_renderer="ANGLE (AMD, AMD Radeon RX 7900 XTX Direct3D11 vs_5_0 ps_5_0, D3D11)",
        screen_width=2560,
        screen_height=1440,
        timezone="America/Los_Angeles",
        languages=["en-US", "en"],
        seed_base=200000,
    ),
    
    "work_laptop": HardwareProfile(
        name="work_laptop",
        description="Laptop corporativo Dell/HP estándar",
        platform="Win32",
        hardware_concurrency=8,
        device_memory=16,
        webgl_vendor="Google Inc. (Intel)",
        webgl_renderer="ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        screen_width=1920,
        screen_height=1080,
        timezone="America/Chicago",
        languages=["en-US", "en"],
        seed_base=300000,
    ),
    
    "work_laptop_high": HardwareProfile(
        name="work_laptop_high",
        description="Laptop de trabajo de alta gama con GPU dedicada",
        platform="Win32",
        hardware_concurrency=8,
        device_memory=32,
        webgl_vendor="Google Inc. (NVIDIA)",
        webgl_renderer="ANGLE (NVIDIA, NVIDIA Quadro T2000 with Max-Q Design Direct3D11 vs_5_0 ps_5_0, D3D11)",
        screen_width=1920,
        screen_height=1080,
        timezone="America/New_York",
        languages=["en-US", "en"],
        seed_base=310000,
    ),
    
    "macbook": HardwareProfile(
        name="macbook",
        description="MacBook Pro con chip Apple Silicon",
        platform="MacIntel",
        hardware_concurrency=8,
        device_memory=16,
        webgl_vendor="Apple Inc.",
        webgl_renderer="Apple M1 Pro",
        screen_width=2560,
        screen_height=1600,
        device_pixel_ratio=2.0,
        timezone="America/Los_Angeles",
        languages=["en-US", "en"],
        seed_base=400000,
    ),
    
    "macbook_air": HardwareProfile(
        name="macbook_air",
        description="MacBook Air M2",
        platform="MacIntel",
        hardware_concurrency=8,
        device_memory=8,
        webgl_vendor="Apple Inc.",
        webgl_renderer="Apple M2",
        screen_width=2560,
        screen_height=1664,
        device_pixel_ratio=2.0,
        timezone="America/New_York",
        languages=["en-US", "en"],
        seed_base=410000,
    ),
    
    "linux_dev": HardwareProfile(
        name="linux_dev",
        description="Estación de desarrollo Linux Ubuntu",
        platform="Linux x86_64",
        hardware_concurrency=12,
        device_memory=32,
        webgl_vendor="Mesa",
        webgl_renderer="Mesa Intel(R) UHD Graphics 770 (ADL-S GT1)",
        screen_width=2560,
        screen_height=1440,
        timezone="America/Denver",
        languages=["en-US", "en"],
        seed_base=500000,
    ),
    
    "linux_dev_nvidia": HardwareProfile(
        name="linux_dev_nvidia",
        description="Estación Linux con GPU NVIDIA",
        platform="Linux x86_64",
        hardware_concurrency=16,
        device_memory=64,
        webgl_vendor="NVIDIA Corporation",
        webgl_renderer="NVIDIA GeForce RTX 3080/PCIe/SSE2",
        screen_width=3840,
        screen_height=2160,  # 4K
        timezone="Europe/London",
        languages=["en-US", "en", "es"],
        seed_base=510000,
    ),
    
    "budget_pc": HardwareProfile(
        name="budget_pc",
        description="PC de gama media/baja",
        platform="Win32",
        hardware_concurrency=4,
        device_memory=8,
        webgl_vendor="Google Inc. (Intel)",
        webgl_renderer="ANGLE (Intel, Intel(R) HD Graphics 4000 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        screen_width=1366,
        screen_height=768,
        timezone="America/New_York",
        languages=["en-US", "en"],
        seed_base=600000,
    ),
    
    "surface_pro": HardwareProfile(
        name="surface_pro",
        description="Microsoft Surface Pro",
        platform="Win32",
        hardware_concurrency=4,
        device_memory=8,
        webgl_vendor="Google Inc. (Intel)",
        webgl_renderer="ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        screen_width=2736,
        screen_height=1824,
        device_pixel_ratio=2.0,
        timezone="America/New_York",
        languages=["en-US", "en"],
        seed_base=700000,
    ),
    
    "chromebook": HardwareProfile(
        name="chromebook",
        description="Chromebook típico",
        platform="Linux x86_64",
        hardware_concurrency=4,
        device_memory=4,
        webgl_vendor="Mesa",
        webgl_renderer="Mesa Intel(R) HD Graphics 400 (BSW)",
        screen_width=1920,
        screen_height=1080,
        timezone="America/Los_Angeles",
        languages=["en-US", "en"],
        seed_base=800000,
    ),
    
    "asian_workstation": HardwareProfile(
        name="asian_workstation",
        description="Workstation para mercado asiático",
        platform="Win32",
        hardware_concurrency=8,
        device_memory=16,
        webgl_vendor="Google Inc. (NVIDIA)",
        webgl_renderer="ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        screen_width=1920,
        screen_height=1080,
        timezone="Asia/Shanghai",
        languages=["zh-CN", "zh", "en-US", "en"],
        seed_base=900000,
    ),
    
    "european_laptop": HardwareProfile(
        name="european_laptop",
        description="Laptop para mercado europeo",
        platform="Win32",
        hardware_concurrency=8,
        device_memory=16,
        webgl_vendor="Google Inc. (Intel)",
        webgl_renderer="ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
        screen_width=1920,
        screen_height=1080,
        timezone="Europe/Paris",
        languages=["fr-FR", "fr", "en-US", "en"],
        seed_base=950000,
    ),
}


def get_profile(name: str) -> Optional[HardwareProfile]:
    """
    Obtiene un perfil por su nombre.
    
    Args:
        name: Nombre del perfil.
    
    Returns:
        HardwareProfile o None si no existe.
    """
    return PROFILES.get(name)


def get_random_profile() -> HardwareProfile:
    """
    Obtiene un perfil aleatorio.
    
    Los perfiles más comunes tienen mayor probabilidad de ser seleccionados.
    
    Returns:
        HardwareProfile: Perfil aleatorio.
    """
    # Pesos para dar preferencia a perfiles más comunes
    weights = {
        "work_laptop": 20,
        "gaming_pc": 15,
        "macbook": 15,
        "budget_pc": 15,
        "linux_dev": 10,
        "work_laptop_high": 8,
        "gaming_pc_amd": 5,
        "macbook_air": 5,
        "linux_dev_nvidia": 3,
        "surface_pro": 2,
        "chromebook": 1,
        "asian_workstation": 1,
        "european_laptop": 1,
    }
    
    profiles = list(PROFILES.keys())
    profile_weights = [weights.get(p, 1) for p in profiles]
    
    chosen = random.choices(profiles, weights=profile_weights, k=1)[0]
    return PROFILES[chosen]


def list_profiles() -> List[str]:
    """
    Lista todos los perfiles disponibles.
    
    Returns:
        List[str]: Lista de nombres de perfiles.
    """
    return list(PROFILES.keys())


def get_profile_info(name: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene información detallada de un perfil.
    
    Args:
        name: Nombre del perfil.
    
    Returns:
        Dict con información del perfil o None.
    """
    profile = get_profile(name)
    if profile:
        return {
            "name": profile.name,
            "description": profile.description,
            "platform": profile.platform,
            "cpu_cores": profile.hardware_concurrency,
            "memory_gb": profile.device_memory,
            "screen": f"{profile.screen_width}x{profile.screen_height}",
            "gpu": profile.webgl_renderer,
        }
    return None


def validate_profile_compatibility(profile_name: str) -> bool:
    """
    Valida si un perfil es compatible con el sistema actual.
    
    Args:
        profile_name: Nombre del perfil.
    
    Returns:
        bool: True si es compatible.
    """
    profile = get_profile(profile_name)
    if not profile:
        return False
    
    # Por ahora todos los perfiles son compatibles
    # En una implementación real, se podría verificar el OS del host
    return True


def create_custom_profile(
    name: str,
    platform: str = "Win32",
    hardware_concurrency: int = 8,
    device_memory: int = 16,
    webgl_vendor: str = "Google Inc. (Intel)",
    webgl_renderer: str = "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    screen_width: int = 1920,
    screen_height: int = 1080,
    timezone: str = "America/New_York",
    languages: List[str] = None,
    **kwargs
) -> HardwareProfile:
    """
    Crea un perfil personalizado.
    
    Args:
        name: Nombre del perfil.
        platform: Plataforma del sistema.
        hardware_concurrency: Número de hilos de CPU.
        device_memory: Memoria en GB.
        webgl_vendor: Vendor de WebGL.
        webgl_renderer: Renderer de WebGL.
        screen_width: Ancho de pantalla.
        screen_height: Alto de pantalla.
        timezone: Zona horaria.
        languages: Lista de idiomas.
        **kwargs: Argumentos adicionales.
    
    Returns:
        HardwareProfile: Perfil personalizado.
    """
    if languages is None:
        languages = ["en-US", "en"]
    
    return HardwareProfile(
        name=name,
        description=f"Custom profile: {name}",
        platform=platform,
        hardware_concurrency=hardware_concurrency,
        device_memory=device_memory,
        webgl_vendor=webgl_vendor,
        webgl_renderer=webgl_renderer,
        screen_width=screen_width,
        screen_height=screen_height,
        timezone=timezone,
        languages=languages,
        seed_base=kwargs.get("seed_base", random.randint(1000000, 2000000)),
    )
