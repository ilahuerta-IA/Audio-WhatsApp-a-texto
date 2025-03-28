# whisper_transcriber.py
"""Clase para manejar la transcripción usando Whisper."""

import threading
import whisper # Mantener importación original
import pathlib
import time
import config

# Variable global para el modelo cargado (Singleton simple)
_whisper_model = None
_model_name_loaded = None
_model_lock = threading.Lock()
_model_loaded_event = threading.Event()

def _load_model_global(model_name: str, status_callback, error_callback):
    """Carga el modelo Whisper de forma segura para subprocesos (se ejecuta en un hilo)."""
    global _whisper_model, _model_name_loaded
    with _model_lock:
        if _whisper_model and _model_name_loaded == model_name:
            print(f"Modelo Whisper '{model_name}' ya estaba cargado.")
            _model_loaded_event.set() # Asegurar que el evento esté activo
            return # Ya cargado

        # Si hay un modelo diferente cargado, ¿deberíamos descargarlo?
        # Por ahora, simplemente cargamos el nuevo. Whisper podría manejar esto internamente.
        _whisper_model = None
        _model_name_loaded = None
        _model_loaded_event.clear() # Indicar que no está listo

    try:
        status_callback(f"Cargando modelo Whisper ({model_name})...")
        print(f"Iniciando carga del modelo Whisper ({model_name})...")
        start_time = time.time()
        loaded_model = whisper.load_model(model_name)
        end_time = time.time()
        print(f"Modelo Whisper ({model_name}) cargado en {end_time - start_time:.2f} segundos.")
        status_callback(f"Modelo Whisper ({model_name}) cargado.")

        with _model_lock:
             _whisper_model = loaded_model
             _model_name_loaded = model_name
             _model_loaded_event.set() # Marcar como listo

    except Exception as e:
        error_msg = f"Error crítico al cargar modelo Whisper ({model_name}): {e}"
        print(error_msg)
        error_callback(error_msg)
        # Asegurarse de que el estado refleje el fallo
        with _model_lock:
            _whisper_model = None
            _model_name_loaded = None
            _model_loaded_event.clear() # No está listo
        status_callback(f"Error al cargar modelo Whisper.")


class WhisperTranscriber:
    """Realiza la transcripción usando el modelo Whisper cargado."""

    def __init__(self, update_callback, status_callback, completion_callback, error_callback):
        """
        Inicializa el transcriptor Whisper.
        Args:
            update_callback (callable): Función a llamar con el texto completo (str).
            status_callback (callable): Función para actualizar el estado (str).
            completion_callback (callable): Función a llamar al finalizar (bool: success).
            error_callback (callable): Función a llamar en caso de error (str).
        """
        self.audio_path = None
        self._thread = None
        self._is_running = False

        # Callbacks
        self.update_callback = update_callback
        self.status_callback = status_callback
        self.completion_callback = completion_callback
        self.error_callback = error_callback

        # Iniciar carga del modelo en segundo plano si no se ha hecho
        if not _model_loaded_event.is_set():
             # Asegurarse de que solo un hilo inicie la carga
             # (Aunque _load_model_global ya tiene un lock, doble check)
             if not hasattr(WhisperTranscriber, "_model_loading_started"):
                 WhisperTranscriber._model_loading_started = True
                 print("Disparando carga inicial del modelo Whisper...")
                 threading.Thread(target=_load_model_global,
                                  args=(config.WHISPER_MODEL_NAME, self.status_callback, self.error_callback),
                                  daemon=True).start()


    def set_audio_file(self, audio_path: pathlib.Path):
        """Establece la ruta del archivo de audio a transcribir (puede ser original o WAV)."""
        self.audio_path = audio_path

    def is_running(self) -> bool:
        """Devuelve True si la transcripción está activa."""
        return self._is_running

    def start(self):
        """Inicia la transcripción Whisper en un hilo separado."""
        if not self.audio_path:
            self.error_callback("Falta la ruta al archivo de audio para Whisper.")
            return
        if self.is_running():
            print("Transcripción Whisper ya en progreso.")
            return

        # Esperar a que el modelo esté cargado
        if not _model_loaded_event.is_set():
            if _whisper_model is None and _model_name_loaded is None: # Si falló la carga
                 self.error_callback(f"El modelo Whisper ({config.WHISPER_MODEL_NAME}) no se pudo cargar previamente.")
            else: # Si todavía está cargando
                self.status_callback("Esperando a que termine la carga del modelo Whisper...")
                # Podríamos esperar aquí con _model_loaded_event.wait() o simplemente reintentar más tarde
                self.error_callback("Modelo Whisper aún cargando. Inténtalo de nuevo en unos segundos.")
            return

        self._is_running = True
        self._thread = threading.Thread(target=self._run_transcription, daemon=True)
        self._thread.start()

    def stop(self):
        """Whisper no soporta interrupción directa de transcribe(). Esta función es placeholder."""
        if self.is_running():
            print("Advertencia: La transcripción Whisper no se puede detener una vez iniciada.")
            # No podemos detener el hilo de Whisper fácilmente si está en medio de model.transcribe()
            # Solo podemos esperar a que termine.
        else:
            print("Whisper transcriber no estaba corriendo.")


    def join(self, timeout=None):
        """Espera a que el hilo de transcripción termine."""
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout)

    def _run_transcription(self):
        """Lógica principal de transcripción Whisper."""
        global _whisper_model
        success = False
        result_text = "Error: Transcripción Whisper no iniciada correctamente."

        if not _whisper_model:
             self.error_callback("Intento de transcribir con Whisper sin modelo cargado.")
             self.completion_callback(False)
             self._is_running = False
             return

        try:
            self.status_callback("Transcribiendo con Whisper (puede tardar)...")
            print(f"Iniciando transcripción Whisper para: {self.audio_path.name}")
            start_time = time.time()

            # Asegurarse de que la ruta es un string
            audio_path_str = str(self.audio_path)

            # Ejecutar transcripción (bloqueante)
            # Considerar usar fp16=False si hay problemas de GPU/CPU
            result = _whisper_model.transcribe(
                audio_path_str,
                language=config.TARGET_LANGUAGE,
                initial_prompt=config.WHISPER_INITIAL_PROMPT
                # verbose=True # Descomentar para más detalles durante la transcripción
            )
            result_text = result["text"]

            end_time = time.time()
            print(f"Transcripción Whisper completada en {end_time - start_time:.2f} segundos.")
            self.status_callback("Transcripción Whisper completada.")
            success = True

        except Exception as e:
            error_msg = f"Error crítico en transcripción Whisper: {e}"
            print(error_msg)
            result_text = f"Error en transcripción Whisper:\n{e}" # Mostrar error en GUI
            self.error_callback(error_msg)
            self.status_callback("Error durante transcripción Whisper.")
            success = False
        finally:
            # Actualizar la GUI con el resultado (texto o error)
            self.update_callback(result_text)
            self._is_running = False
            # Notificar al GUI que el proceso (exitoso o no) ha terminado
            self.completion_callback(success)