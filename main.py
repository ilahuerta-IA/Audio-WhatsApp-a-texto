# main.py
"""Punto de entrada principal para la aplicación AudioTranscriptorPro."""

import tkinter as tk
import sys
# Añadir directorio padre al path si es necesario para encontrar módulos locales
# import os
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from gui import AudioTranscriptorPro
    import playback # Importar para llamar a quit_playback al final
    import audio_handler # Importar para llamar cleanup al final
except ImportError as e:
     print(f"Error al importar módulos: {e}")
     print("Asegúrate de ejecutar este script desde el directorio que contiene 'audio_transcriptor_pro' o de que la estructura de carpetas es correcta.")
     sys.exit(1)


if __name__ == "__main__":
    root = None # Inicializar a None
    app = None  # Inicializar a None
    try:
        print("Iniciando aplicación AudioTranscriptorPro...")
        root = tk.Tk()
        app = AudioTranscriptorPro(root)
        root.mainloop() # Bloquea hasta que la ventana se cierra
    except Exception as e:
         print(f"Error fatal durante la ejecución de la aplicación: {e}")
         # Aquí podrías intentar guardar logs o mostrar un mensaje final
    finally:
        # --- Limpieza después de que mainloop termine (ventana cerrada) ---
        print("Saliendo de la aplicación...")

        # Llamar a la limpieza específica de la GUI si la app se inicializó
        if app:
             try:
                 app.cleanup_on_exit()
             except Exception as cleanup_err:
                 print(f"Error durante app.cleanup_on_exit(): {cleanup_err}")

        # Asegurarse de que Pygame se cierre independientemente de la GUI
        # playback.quit_playback() ya es llamado por app.cleanup_on_exit()
        # audio_handler.cleanup_temp_wav() ya es llamado por app.cleanup_on_exit()

        print("Limpieza completa. Adiós.")
        sys.exit(0) # Salir limpiamente