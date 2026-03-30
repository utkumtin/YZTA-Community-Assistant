"""
Tüm handler modüllerini Slack App'e kayıt eder.
Bu dosya import edildiğinde, commands ve events içindeki
@app.command / @app.view / @app.action dekoratörleri otomatik olarak aktive olur.
"""
from .commands import challenge as challenge_commands
from .commands import internal as internal_commands
from .commands import evaluation as evaluation_commands
from .commands import jury as jury_commands

from .events import challenge as challenge_events
from .events import internal as internal_events
from .events import evaluation as evaluation_events
