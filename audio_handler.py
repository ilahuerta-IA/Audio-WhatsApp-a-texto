# audio_handler.py

import os
import pathlib
from tkinter import filedialog, messagebox
from pydub import AudioSegment, exceptions as pydub_exceptions
import config

# Variable para guardar la ruta del archivo temporal si se crea
_temp_wav_path: pathlib.Path | None = None

def select_audio_file() -> pathlib.Path | None:
    """Abre diálogo para seleccionar archivo de audio, devuelve Path o None."""
    global _temp_wav_path # Asegurarse de resetear al seleccionar nuevo archivo
    cleanup_temp_wav() # Limpiar anterior si existe
    _temp_wav_path = None

    ruta_audio_str = filedialog.askopenfilename(
        defaultextension=config.DEFAULT_EXTENSION,
        filetypes=config.AUDIO_FILE_TYPES
    )
    if ruta_audio_str:
        print(f"Archivo seleccionado: {ruta_audio_str}")
        return pathlib.Path(ruta_audio_str)
    else:
        print("Selección de archivo cancelada.")
        return None

def convert_to_wav_if_needed(audio_path: pathlib.Path) -> pathlib.Path | None:
    """
    Intenta cargar el archivo de audio y SIEMPRE lo re-exporta a un WAV estándar temporal.
    Esto valida y normaliza el archivo, incluso si ya tenía extensión .wav.
    Devuelve la ruta al archivo WAV temporal si tiene éxito.
    Devuelve None si hay error en la carga o conversión.
    Almacena la ruta temporal en _temp_wav_path si se crea una.
    """
    global _temp_wav_path

    # Crear nombre para archivo temporal WAV
    temp_wav_path_obj = audio_path.with_name(f"{audio_path.stem}_temp_playback.wav") # Nombre específico

    try:
        print(f"Intentando cargar: {audio_path.name}...")
        audio = AudioSegment.from_file(str(audio_path))

        print(f"Cargado con éxito. Re-exportando a WAV estándar: {temp_wav_path_obj.name}...")
        # Exportar a WAV estándar (PCM 16-bit little-endian es lo más compatible)
        audio.export(str(temp_wav_path_obj), format="wav", codec="pcm_s16le")
        print(f"Re-exportación exitosa: {temp_wav_path_obj.name}")
        _temp_wav_path = temp_wav_path_obj # Guardar ruta temporal
        return temp_wav_path_obj
    except pydub_exceptions.CouldntDecodeError as e:
        error_msg = (f"Pydub/FFmpeg no pudo decodificar el archivo: {audio_path.name}. "
                     f"Puede estar corrupto o en un formato no soportado.\nError: {e}")
        print(error_msg)
        messagebox.showerror("Error de Carga/Conversión", error_msg)
    except FileNotFoundError as e:
        error_msg = (f"No se encontró ffmpeg o ffprobe. Pydub los necesita.\n"
                     f"Asegúrate de que estén instalados y en el PATH del sistema.\nError: {e}")
        print(error_msg)
        messagebox.showerror("Error de Dependencia", error_msg)
    except Exception as e:
        error_msg = f"Error inesperado al procesar {audio_path.name}: {e}"
        print(error_msg)
        messagebox.showerror("Error Inesperado", error_msg)
        if temp_wav_path_obj.exists():
            try:
                os.remove(temp_wav_path_obj)
            except OSError: pass

    _temp_wav_path = None # Falló la conversión/carga
    return None

def get_temp_wav_path() -> pathlib.Path | None:
    """Devuelve la ruta del archivo WAV temporal si existe."""
    return _temp_wav_path

def cleanup_temp_wav():
    """Elimina el archivo WAV temporal si existe."""
    global _temp_wav_path
    if _temp_wav_path and _temp_wav_path.exists():
        try:
            print(f"Eliminando archivo WAV temporal: {_temp_wav_path.name}")
            os.remove(_temp_wav_path)
            _temp_wav_path = None
        except Exception as e:
            print(f"Advertencia: No se pudo eliminar el archivo WAV temporal {_temp_wav_path.name}: {e}")
    else:
        _temp_wav_path = None