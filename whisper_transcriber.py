# In whisper_transcriber.py
"""Clase para manejar la transcripción usando Whisper."""

import threading
import time
import pathlib
import config

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    print("ADVERTENCIA: La librería 'whisper' no está instalada. La funcionalidad de Whisper no estará disponible.")
    print("Instálala con: pip install -U openai-whisper")
    whisper = None # Placeholder
    WHISPER_AVAILABLE = False

# Variable global para el modelo cargado (Singleton simple)
_whisper_model = None
_model_name_loaded = None
_model_lock = threading.Lock() # Lock para acceso a las variables globales del modelo
_model_load_thread = None # Referencia al hilo de carga actual
_model_load_stop_event = threading.Event() # Para intentar cancelar carga (si es posible)
_model_ready_event = threading.Event() # Para saber si un modelo está LISTO

def _load_model_global(model_name: str, progress_callback, completion_callback, error_callback, stop_event):
    """
    Carga el modelo Whisper de forma segura para subprocesos (se ejecuta en un hilo).
    Notifica progreso y finalización.
    """
    global _whisper_model, _model_name_loaded, _model_ready_event

    with _model_lock:
        _whisper_model = None
        _model_name_loaded = None
        _model_ready_event.clear()

    if not WHISPER_AVAILABLE:
        error_msg = "La librería Whisper no está instalada o no se pudo importar."
        print(f"ERROR: {error_msg}")
        error_callback(error_msg)
        completion_callback(False, model_name)
        return

    if stop_event.is_set():
        print(f"Carga del modelo '{model_name}' cancelada antes de empezar.")
        completion_callback(False, model_name)
        return

    try:
        print(f"Iniciando carga del modelo Whisper ({model_name})...")
        start_time = time.time()

        # Simulación de Progreso
        progress_callback(f"Preparando descarga de '{model_name}'...", 10)
        time.sleep(0.2)
        if stop_event.is_set(): raise InterruptedError("Carga cancelada durante preparación.")
        progress_callback(f"Descargando/Verificando '{model_name}'...", 30)
        time.sleep(0.5)
        progress_callback(f"Cargando '{model_name}' en memoria...", 60)
        if stop_event.is_set(): raise InterruptedError("Carga cancelada antes de load_model.")

        # Carga Real
        loaded_model = whisper.load_model(model_name)

        if stop_event.is_set():
            del loaded_model
            raise InterruptedError("Carga cancelada después de load_model.")

        end_time = time.time()
        load_duration = end_time - start_time
        print(f"Modelo Whisper ({model_name}) cargado en {load_duration:.2f} segundos.")

        with _model_lock:
            _whisper_model = loaded_model
            _model_name_loaded = model_name
            _model_ready_event.set()

        progress_callback(f"Modelo '{model_name}' cargado.", 100)
        completion_callback(True, model_name)

    except InterruptedError as ie:
        print(f"INFO: {ie}")
        progress_callback(f"Carga de '{model_name}' cancelada.", 0)
        error_callback(f"Carga del modelo '{model_name}' cancelada por el usuario.")
        completion_callback(False, model_name)

    except Exception as e:
        error_msg = f"Error crítico al cargar modelo Whisper ({model_name}): {e}"
        print(error_msg)
        with _model_lock:
            _whisper_model = None
            _model_name_loaded = None
            _model_ready_event.clear()
        progress_callback(f"Error al cargar '{model_name}'.", 0)
        error_callback(error_msg)
        completion_callback(False, model_name)


class WhisperTranscriber:
    """Realiza la transcripción usando el modelo Whisper cargado."""

    def __init__(self, update_callback, status_callback, completion_callback, error_callback):
        """
        Inicializa el transcriptor Whisper.
        Args:
            update_callback (callable): Función a llamar con el resultado completo (dict).
            status_callback (callable): Función para actualizar el estado general (str).
            completion_callback (callable): Función a llamar al finalizar la transcripción (bool: success, result: dict | None).
            error_callback (callable): Función a llamar en caso de error (str).
        """
        self.audio_path = None
        self._transcription_thread = None
        self._is_running_transcription = False

        self.update_callback = update_callback
        self.status_callback = status_callback
        self.completion_callback = completion_callback
        self.error_callback = error_callback

    def load_model(self, model_name: str, progress_callback, model_completion_callback):
        """Inicia la carga del modelo Whisper especificado en un hilo separado."""
        global _model_load_thread, _model_load_stop_event, _model_name_loaded, _model_lock

        with _model_lock:
            if _model_load_thread and _model_load_thread.is_alive():
                print(f"INFO: Petición de carga para '{model_name}' mientras otro modelo podría estar cargando. Intentando cancelar anterior...")
                _model_load_stop_event.set()
                _model_load_thread.join(timeout=1.0)
                if _model_load_thread.is_alive():
                    print(f"ADVERTENCIA: El hilo de carga anterior no terminó a tiempo.")

            if _model_ready_event.is_set() and _model_name_loaded == model_name:
                print(f"Modelo '{model_name}' ya está cargado y listo.")
                progress_callback(f"Modelo '{model_name}' ya cargado.", 100)
                model_completion_callback(True, model_name)
                return

            _model_load_stop_event.clear()
            print(f"Solicitando carga del modelo: {model_name}")
            _model_load_thread = threading.Thread(
                target=_load_model_global,
                args=(model_name, progress_callback, model_completion_callback, self.error_callback, _model_load_stop_event),
                daemon=True
            )
            _model_load_thread.start()

    def set_audio_file(self, audio_path: pathlib.Path):
        """Establece la ruta del archivo de audio a transcribir."""
        self.audio_path = audio_path
        print(f"WhisperTranscriber: Audio path set to {audio_path}")

    def is_running(self) -> bool:
        """Devuelve True si la transcripción está activa."""
        return self._is_running_transcription

    def start(self):
        """Inicia la transcripción Whisper en un hilo separado."""
        global _model_name_loaded, _whisper_model, _model_ready_event

        if not self.audio_path:
            self.error_callback("Whisper: Falta la ruta al archivo de audio.")
            return
        if self.is_running():
            print("Transcripción Whisper ya en progreso.")
            return

        with _model_lock:
            if not _model_ready_event.is_set() or not _whisper_model:
                self.error_callback("Whisper: El modelo no está cargado o listo. Por favor, selecciona y carga un modelo primero.")
                return
            print(f"Whisper: Iniciando transcripción con el modelo cargado: '{_model_name_loaded}' para el archivo {self.audio_path}")

        self._is_running_transcription = True
        self._transcription_thread = threading.Thread(target=self._run_transcription, daemon=True)
        self._transcription_thread.start()

    def stop(self):
        """Whisper no soporta interrupción directa de transcribe(). Placeholder."""
        if self.is_running():
            print("Advertencia: La transcripción Whisper no se puede detener una vez iniciada.")
        else:
            print("Whisper transcriber (transcripción) no estaba corriendo.")

    def join(self, timeout=None):
        """Espera a que el hilo de transcripción termine."""
        if self._transcription_thread and self._transcription_thread.is_alive():
            self._transcription_thread.join(timeout)

    def _run_transcription(self):
        """Lógica principal de transcripción Whisper."""
        with _model_lock:
            current_model = _whisper_model
            current_model_name = _model_name_loaded

        success = False
        result_data = None # Cambiado para almacenar el dict completo

        if not current_model or not current_model_name:
             self.error_callback("Intento de transcribir con Whisper sin modelo cargado.")
             # Llamar a completion_callback con fallo
             self.completion_callback(False, None) # Pasar None como resultado
             self._is_running_transcription = False
             return
        if not self.audio_path or not self.audio_path.exists():
             self.error_callback(f"Whisper: El archivo de audio {self.audio_path} no existe o no es accesible.")
             self.completion_callback(False, None)
             self._is_running_transcription = False
             return

        try:
            self.status_callback(f"Transcribiendo con Whisper '{current_model_name}' (puede tardar)...")
            print(f"Iniciando transcripción Whisper para: {self.audio_path.name} usando {current_model_name}")
            start_time = time.time()
            audio_path_str = str(self.audio_path)

            # Ejecutar transcripción
            # word_timestamps=True es útil pero puede alentar un poco y consumir más memoria
            # segment level timestamps suelen ser suficientes para la sincronización básica.
            result_data = current_model.transcribe(
                audio_path_str,
                language=config.TARGET_LANGUAGE,
                initial_prompt=config.WHISPER_INITIAL_PROMPT,
                fp16=False, # Forzar CPU/compatibilidad general, cambiar si se tiene GPU potente y se prueba
                # word_timestamps=False # Descomentar si se prefiere usar word timestamps (más granular)
                verbose=None # Usar None o False para menos output en consola
            )

            end_time = time.time()
            print(f"Transcripción Whisper ({current_model_name}) completada en {end_time - start_time:.2f} segundos.")
            # El texto se pasa ahora dentro del result_data
            # self.status_callback("Transcripción Whisper completada.") # El status se actualiza en GUI al recibir resultado
            success = True

        except Exception as e:
            error_msg = f"Error crítico en transcripción Whisper ({current_model_name}): {e}"
            print(error_msg)
            # Crear un diccionario de error simulado si falla
            result_data = {
                "text": f"Error en transcripción Whisper ({current_model_name}):\n{e}",
                "segments": [],
                "language": config.TARGET_LANGUAGE
            }
            self.error_callback(error_msg)
            # self.status_callback("Error durante transcripción Whisper.")
            success = False
        finally:
            # IMPORTANTE: Llamar a update_callback con el diccionario completo
            # La GUI se encargará de extraer el texto y los segmentos
            self.update_callback(result_data)

            self._is_running_transcription = False
            # Notificar al GUI que el proceso de *transcripción* ha terminado
            # Se pasa el resultado para que la GUI lo tenga inmediatamente si lo necesita
            self.completion_callback(success, result_data)