"""preset forge: codec per leggere/scrivere preset di VST i cui parametri
interni NON sono esposti all'host (bypassa il limite Configure senza computer use).
Formati supportati: Serum 2 (.SerumPreset), KICK 3 (.preset XML), Smooth Operator Pro (.baby)."""
from . import serum2, kick3, smoothop  # noqa: F401
