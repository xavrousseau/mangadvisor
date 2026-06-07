from nicegui import ui
import os

API_BASE_URL = os.getenv('API_BASE_URL', 'http://mangadvisor-api:8000')

with ui.header().classes('justify-between'):
    ui.label('Mangadvisor UI')
    ui.link('API docs', f'{API_BASE_URL}/docs', new_tab=True)

ui.label('Hello from NiceGUI 👋')

# Démarrage compatible multiprocessing (Docker / NiceGUI)
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(host='0.0.0.0', port=8080)
