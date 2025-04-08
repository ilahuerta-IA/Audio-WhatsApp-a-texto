# In whisper_transcriber.py
"""Clase para manejar la transcripción usando Whisper."""

import threading
import time
import pathlib
import math # para simular progreso
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

# NUEVO: Evento para saber si un modelo está LISTO para ser usado
_model_ready_event = threading.Event()

def _load_model_global(model_name: str, progress_callback, completion_callback, error_callback, stop_event):
    """
    Carga el modelo Whisper de forma segura para subprocesos (se ejecuta en un hilo).
    Notifica progreso y finalización.
    """
    global _whisper_model, _model_name_loaded, _model_ready_event

    # --- Comprobación inicial y reseteo ---
    # Siempre limpiar estado anterior antes de intentar cargar uno nuevo
    with _model_lock:
        _whisper_model = None
        _model_name_loaded = None
        _model_ready_event.clear() # Marcar como no listo

    if not WHISPER_AVAILABLE:
        error_msg = "La librería Whisper no está instalada o no se pudo importar."
        print(f"ERROR: {error_msg}")
        error_callback(error_msg)
        completion_callback(False, model_name) # Indicar fallo
        return

    if stop_event.is_set():
        print(f"Carga del modelo '{model_name}' cancelada antes de empezar.")
        completion_callback(False, model_name) # Indicar fallo (cancelación)
        return

    try:
        print(f"Iniciando carga del modelo Whisper ({model_name})...")
        start_time = time.time()

        # --- Simulación de Progreso (Whisper no lo ofrece directamente) ---
        # Etapa 1: Descarga (simulada) - Podría ser más larga si no está en caché
        progress_callback(f"Preparando descarga de '{model_name}' (si es necesario)...", 10)
        time.sleep(0.5) # Simular algo de tiempo
        if stop_event.is_set(): raise InterruptedError("Carga cancelada durante preparación.")
        progress_callback(f"Descargando/Verificando '{model_name}'...", 30)
        time.sleep(1) # Simular más tiempo

        # Etapa 2: Carga en memoria
        progress_callback(f"Cargando '{model_name}' en memoria...", 60)
        if stop_event.is_set(): raise InterruptedError("Carga cancelada antes de load_model.")

        # --- Carga Real ---
        # NOTA: whisper.load_model puede imprimir su propio progreso de descarga a la consola
        loaded_model = whisper.load_model(model_name) # Esta es la parte bloqueante y larga

        if stop_event.is_set():
            # Aunque ya cargó, si se pidió parar, no lo marcamos como listo
            # Intentar liberar memoria si es posible (difícil sin API explícita)
            del loaded_model
            raise InterruptedError("Carga cancelada después de load_model.")

        end_time = time.time()
        load_duration = end_time - start_time
        print(f"Modelo Whisper ({model_name}) cargado en {load_duration:.2f} segundos.")

        # --- Actualización final y estado ---
        with _model_lock:
            _whisper_model = loaded_model
            _model_name_loaded = model_name
            _model_ready_event.set() # ¡Modelo listo!

        progress_callback(f"Modelo '{model_name}' cargado.", 100)
        completion_callback(True, model_name) # Indicar éxito

    except InterruptedError as ie:
        print(f"INFO: {ie}")
        # Estado ya limpiado al inicio o gestionado antes de la excepción
        progress_callback(f"Carga de '{model_name}' cancelada.", 0)
        error_callback(f"Carga del modelo '{model_name}' cancelada por el usuario.") # Informar a GUI
        completion_callback(False, model_name) # Indicar fallo (cancelación)

    except Exception as e:
        error_msg = f"Error crítico al cargar modelo Whisper ({model_name}): {e}"
        print(error_msg)
        # Asegurar limpieza si falla
        with _model_lock:
            _whisper_model = None
            _model_name_loaded = None
            _model_ready_event.clear()
        progress_callback(f"Error al cargar '{model_name}'.", 0)
        error_callback(error_msg) # Notificar error detallado
        completion_callback(False, model_name) # Indicar fallo


class WhisperTranscriber:
    """Realiza la transcripción usando el modelo Whisper cargado."""

    def __init__(self, update_callback, status_callback, completion_callback, error_callback):
        """
        Inicializa el transcriptor Whisper. NO carga el modelo aquí.
        Args:
            update_callback (callable): Función a llamar con el texto completo (str).
            status_callback (callable): Función para actualizar el estado general (str).
            completion_callback (callable): Función a llamar al finalizar la transcripción (bool: success).
            error_callback (callable): Función a llamar en caso de error (str).
        """
        self.audio_path = None
        self._transcription_thread = None
        self._is_running_transcription = False # Estado específico de la transcripción

        # Callbacks
        self.update_callback = update_callback
        self.status_callback = status_callback # Para estado general
        self.completion_callback = completion_callback # Para fin de transcripción
        self.error_callback = error_callback

        # --- NO iniciar carga del modelo aquí ---
        # if not _model_ready_event.is_set() and WHISPER_AVAILABLE:
        #     pass # La carga se hará explícitamente


    def load_model(self, model_name: str, progress_callback, model_completion_callback):
        """
        Inicia la carga del modelo Whisper especificado en un hilo separado.
        Args:
            model_name (str): Nombre del modelo a cargar (e.g., "tiny", "base").
            progress_callback (callable): Función para reportar progreso (mensaje: str, porcentaje: int).
            model_completion_callback (callable): Función a llamar al finalizar la CARGA (success: bool, loaded_model_name: str).
        """
        global _model_load_thread, _model_load_stop_event, _model_name_loaded, _model_lock

        with _model_lock:
            # Si ya hay un hilo cargando, intentar detenerlo antes de empezar uno nuevo
            if _model_load_thread and _model_load_thread.is_alive():
                print(f"INFO: Petición de carga para '{model_name}' mientras otro modelo ('{_model_name_loaded}') podría estar cargando. Intentando cancelar anterior...")
                _model_load_stop_event.set() # Señalizar al hilo anterior que pare
                # Esperar un poco a que el hilo anterior reaccione
                # Nota: Esto no garantiza que pare si está bloqueado en C/GPU
                _model_load_thread.join(timeout=1.0)
                if _model_load_thread.is_alive():
                    print(f"ADVERTENCIA: El hilo de carga anterior para '{_model_name_loaded}' no terminó a tiempo.")
                    # Considerar si abortar la nueva carga o continuar
                    # Por ahora, continuamos, pero el estado podría ser inconsistente

            # Si el modelo solicitado ya está cargado y listo, avisar y salir
            if _model_ready_event.is_set() and _model_name_loaded == model_name:
                print(f"Modelo '{model_name}' ya está cargado y listo.")
                progress_callback(f"Modelo '{model_name}' ya cargado.", 100)
                model_completion_callback(True, model_name)
                return

            # Preparar para nueva carga
            _model_load_stop_event.clear() # Resetear evento de parada
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

    def is_running(self) -> bool:
        """Devuelve True si la transcripción está activa."""
        # Ahora se refiere a la transcripción, no a la carga del modelo
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

        # --- Comprobación CLAVE: ¿Está el modelo correcto cargado y listo? ---
        with _model_lock:
            if not _model_ready_event.is_set() or not _whisper_model:
                # Esto puede ocurrir si la carga falló o nunca se inició
                self.error_callback("Whisper: El modelo no está cargado o listo. Por favor, selecciona y carga un modelo primero.")
                return
            # Podríamos añadir una comprobación extra si la GUI pasara el modelo esperado
            # expected_model = ... # obtener de GUI si fuera necesario
            # if _model_name_loaded != expected_model:
            #     self.error_callback(f"Whisper: Modelo cargado '{_model_name_loaded}' no coincide con el esperado '{expected_model}'.")
            #     return

            print(f"Whisper: Iniciando transcripción con el modelo cargado: '{_model_name_loaded}'")


        self._is_running_transcription = True
        # Renombrar el hilo para claridad
        self._transcription_thread = threading.Thread(target=self._run_transcription, daemon=True)
        self._transcription_thread.start()

    def stop(self):
        """Whisper no soporta interrupción directa de transcribe(). Placeholder."""
        if self.is_running():
            print("Advertencia: La transcripción Whisper no se puede detener una vez iniciada.")
            # No podemos detener el hilo de Whisper fácilmente si está en medio de model.transcribe()
            # Solo podemos esperar a que termine.
            # NO cambiamos self._is_running_transcription aquí, se hará en _run_transcription.
        else:
            print("Whisper transcriber (transcripción) no estaba corriendo.")

    def join(self, timeout=None):
        """Espera a que el hilo de transcripción termine."""
        if self._transcription_thread and self._transcription_thread.is_alive():
            self._transcription_thread.join(timeout)

    def _run_transcription(self):
        """Lógica principal de transcripción Whisper."""
        # Acceder al modelo global de forma segura
        with _model_lock:
            current_model = _whisper_model
            current_model_name = _model_name_loaded

        success = False
        result_text = "Error: Transcripción Whisper no iniciada correctamente."

        if not current_model or not current_model_name:
             self.error_callback("Intento de transcribir con Whisper sin modelo cargado.")
             self.completion_callback(False) # Notificar fallo de transcripción
             self._is_running_transcription = False
             return

        try:
            # Usar status_callback para el estado general de la app
            self.status_callback(f"Transcribiendo con Whisper '{current_model_name}' (puede tardar)...")
            print(f"Iniciando transcripción Whisper para: {self.audio_path.name} usando {current_model_name}")
            start_time = time.time()

            # Asegurarse de que la ruta es un string
            audio_path_str = str(self.audio_path)

            # Ejecutar transcripción (bloqueante)
            result = current_model.transcribe(
                audio_path_str,
                language=config.TARGET_LANGUAGE,
                initial_prompt=config.WHISPER_INITIAL_PROMPT,
                # fp16=False # Descomentar si se usa CPU o hay problemas con fp16
                # verbose=None # None suele ser un buen balance, True da mucho detalle
            )
            result_text = result["text"]

            end_time = time.time()
            print(f"Transcripción Whisper ({current_model_name}) completada en {end_time - start_time:.2f} segundos.")
            self.status_callback("Transcripción Whisper completada.") # Actualizar estado general
            success = True

        except Exception as e:
            error_msg = f"Error crítico en transcripción Whisper ({current_model_name}): {e}"
            print(error_msg)
            result_text = f"Error en transcripción Whisper ({current_model_name}):\n{e}" # Mostrar error en GUI
            self.error_callback(error_msg) # Reportar error específico
            self.status_callback("Error durante transcripción Whisper.") # Actualizar estado general
            success = False
        finally:
            # Actualizar la GUI con el resultado (texto o error)
            # IMPORTANTE: Usar el callback específico para el texto de Whisper
            self.update_callback(result_text)
            self._is_running_transcription = False
            # Notificar al GUI que el proceso de *transcripción* ha terminado
            self.completion_callback(success)