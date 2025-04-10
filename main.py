# main.py
"""Punto de entrada principal para la aplicación AudioTranscriptorPro."""

import tkinter as tk
import sys
import os
import config

# Añadir directorio actual al path para asegurar importaciones locales
# sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    # Comprobar si los módulos necesarios existen antes de importarlos puede ser útil
    # para dar mensajes más claros si falta alguno.
    required_files = ['gui.py', 'config.py', 'utils.py', 'audio_handler.py', 'playback.py', 'whisper_transcriber.py']
    for fname in required_files:
        if not os.path.exists(fname):
            print(f"ERROR FATAL: Falta el archivo requerido '{fname}'. Asegúrate de que todos los archivos estén en el mismo directorio.")
            sys.exit(1)

    from gui import AudioTranscriptorPro
    import playback # Importar para llamar a quit_playback al final
    import audio_handler # Importar para llamar cleanup al final

except ImportError as e:
     print(f"Error al importar módulos: {e}")
     print("Asegúrate de tener todas las dependencias instaladas (tkinter, pydub, pygame, openai-whisper, torch) y que los archivos .py estén juntos.")
     sys.exit(1)
except Exception as e:
     print(f"Ocurrió un error inesperado durante la importación inicial: {e}")
     sys.exit(1)


if __name__ == "__main__":
    root = None
    app = None
    try:
        print(f"Iniciando aplicación AudioTranscriptorPro ({config.__version__})...")
        root = tk.Tk()
        # Opcional: Establecer un icono
        # try:
        #     # Reemplaza 'icon.ico' o 'icon.png' con tu archivo de icono
        #     if os.path.exists('icon.ico'):
        #         root.iconbitmap('icon.ico')
        #     elif os.path.exists('icon.png'):
        #         # Para PNG u otros formatos, podrías necesitar PhotoImage
        #         img = tk.PhotoImage(file='icon.png')
        #         root.tk.call('wm', 'iconphoto', root._w, img)
        # except Exception as icon_err:
        #     print(f"Advertencia: No se pudo establecer el icono de la ventana: {icon_err}")

        app = AudioTranscriptorPro(root)
        root.mainloop()
    except tk.TclError as e:
         # Errores comunes de Tkinter, como problemas al crear widgets
         print(f"Error fatal de Tkinter: {e}")
         if "display" in str(e).lower():
              print("Posible problema: No se puede conectar al servidor de pantalla (entorno sin GUI?).")
    except Exception as e:
         print(f"Error fatal durante la ejecución de la aplicación: {e}")
         import traceback
         traceback.print_exc() # Imprimir traceback completo para depuración
    finally:
        print("Saliendo de la aplicación...")

        # Llamar a la limpieza específica de la GUI si la app se inicializó
        if app:
             try:
                 # La limpieza principal ahora está en app.cleanup_on_exit()
                 app.cleanup_on_exit()
             except Exception as cleanup_err:
                 print(f"Error durante app.cleanup_on_exit(): {cleanup_err}")
        else:
             # Si app no se inicializó, intentar limpiar pygame directamente
             print("Intentando limpieza manual de playback...")
             playback.quit_playback()
             audio_handler.cleanup_temp_wav()


        print("Limpieza completa. Adiós.")
        # sys.exit(0) # mainloop() ya sale, no es estrictamente necesario