# google_transcriber.py
"""Clase para manejar la transcripción usando Google Speech Recognition."""

import threading
import time
import io
import speech_recognition as sr
from pydub import AudioSegment
import pathlib
import playback
import config

class GoogleTranscriber:
    """Realiza la transcripción en tiempo real (simulado) con Google Speech Rec."""

    def __init__(self, update_callback, status_callback, completion_callback, error_callback):
        """
        Inicializa el transcriptor.
        Args:
            update_callback (callable): Función a llamar con cada fragmento de texto transcrito (str).
            status_callback (callable): Función para actualizar el estado (str).
            completion_callback (callable): Función a llamar al finalizar (bool: success).
            error_callback (callable): Función a llamar en caso de error (str).
        """
        self.recognizer = sr.Recognizer()
        self.audio_segment = None
        self.wav_path = None
        self._stop_event = threading.Event()
        self._thread = None
        self._is_running = False

        # Callbacks
        self.update_callback = update_callback
        self.status_callback = status_callback
        self.completion_callback = completion_callback
        self.error_callback = error_callback

    def set_audio_file(self, wav_path: pathlib.Path):
        """Establece la ruta del archivo WAV a transcribir."""
        self.wav_path = wav_path
        self.audio_segment = None # Forzar recarga

    def is_running(self) -> bool:
        """Devuelve True si la transcripción está activa."""
        return self._is_running

    def start(self):
        """Inicia el proceso de transcripción en un hilo separado."""
        if not self.wav_path:
            self.error_callback("Falta la ruta al archivo WAV para Google.")
            return
        if self.is_running():
            print("Transcripción Google ya en progreso.")
            return

        self._stop_event.clear()
        self._is_running = True
        self._thread = threading.Thread(target=self._run_transcription, daemon=True)
        self._thread.start()

    def stop(self):
        """Señaliza al hilo de transcripción que debe detenerse."""
        if self.is_running():
            print("Enviando señal de parada a Google transcriber...")
            self._stop_event.set()
            # La parada real y limpieza ocurren dentro del hilo al detectar el evento
            # Detener la reproducción inmediatamente
            playback.stop_audio()
        else:
            print("Google transcriber no estaba corriendo.")

    def join(self, timeout=None):
        """Espera a que el hilo de transcripción termine."""
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout)

    def _load_audio(self) -> bool:
        """Carga el archivo de audio WAV."""
        if self.audio_segment is None:
            self.status_callback("Cargando audio para Google...")
            try:
                self.audio_segment = AudioSegment.from_wav(str(self.wav_path))
                print(f"Audio cargado para Google: {self.wav_path.name}")
                self.status_callback("Audio cargado.")
                return True
            except Exception as e:
                error_msg = f"Error al cargar WAV para Google: {e}"
                print(error_msg)
                self.error_callback(error_msg)
                return False
        return True # Ya estaba cargado

    def _run_transcription(self):
        """Lógica principal de transcripción ejecutada en el hilo."""
        success = False
        try:
            if not self._load_audio():
                return # Error ya reportado en _load_audio

            inicio_segmento = 0
            tiempo_audio = len(self.audio_segment)
            segment_duration_ms = config.GOOGLE_CHUNK_DURATION_MS

            # Cargar para reproducir
            if not playback.load_audio_segment(self.audio_segment):
                 self.error_callback("No se pudo cargar el audio para reproducción.")
                 # Continuar con la transcripción igualmente? O detener? Detener es más seguro.
                 return

            playback.play_audio()
            self.status_callback("Transcribiendo con Google Speech...")

            while inicio_segmento < tiempo_audio and not self._stop_event.is_set():
                fin_segmento = min(inicio_segmento + segment_duration_ms, tiempo_audio)
                if fin_segmento <= inicio_segmento: break # Evitar segmentos vacíos al final

                segmento = self.audio_segment[inicio_segmento:fin_segmento]

                # Transcribir segmento
                texto_segmento = self._transcribe_segment(segmento)

                # Actualizar GUI (si hay texto)
                if texto_segmento:
                    self.update_callback(texto_segmento)

                # Calcular y esperar para simular tiempo real
                # (Esta parte es compleja de sincronizar perfectamente)
                segment_playback_duration_s = len(segmento) / 1000.0
                # Idealmente, mediríamos cuánto tardó _transcribe_segment,
                # pero por simplicidad, usamos un pequeño delay.
                # Una mejor aproximación requiere más lógica.
                sleep_duration_s = segment_playback_duration_s * 0.8 # Esperar un % de la duración
                if not self._stop_event.is_set() and sleep_duration_s > 0.05: # No dormir si es muy corto
                     time.sleep(sleep_duration_s)


                inicio_segmento = fin_segmento

            # --- Fin del bucle ---
            if self._stop_event.is_set():
                print("Transcripción Google detenida por usuario.")
                self.status_callback("Transcripción Google detenida.")
                success = False # No completada
            else:
                print("Transcripción Google finalizada.")
                self.status_callback("Transcripción Google completada.")
                success = True # Completada exitosamente

        except Exception as e:
            error_msg = f"Error inesperado en transcripción Google: {e}"
            print(error_msg)
            self.error_callback(error_msg)
            success = False
        finally:
            # Asegurarse de detener la reproducción y limpiar
            playback.stop_audio()
            # No descargamos aquí, puede ser necesario para Whisper si usa el mismo archivo
            self._is_running = False
            self.completion_callback(success) # Notificar al GUI

    def _transcribe_segment(self, segmento: AudioSegment) -> str | None:
        """Transcribe un único segmento de audio."""
        if self._stop_event.is_set(): return None

        temp_wav_buffer = io.BytesIO()
        try:
            segmento.export(temp_wav_buffer, format="wav")
            temp_wav_buffer.seek(0)
        except Exception as e:
            print(f"Error exportando segmento para Google: {e}")
            return None # No se pudo procesar este segmento

        with sr.AudioFile(temp_wav_buffer) as fuente:
            if self._stop_event.is_set(): return None
            try:
                # Ajustar sensibilidad al ruido ambiente si es necesario
                # self.recognizer.adjust_for_ambient_noise(fuente, duration=0.5)
                audio_data = self.recognizer.record(fuente)
            except ValueError:
                print("Segmento de audio vacío o inválido para Google.")
                return None
            except Exception as e:
                 print(f"Error grabando segmento con sr.AudioFile: {e}")
                 return None

            if self._stop_event.is_set(): return None

            try:
                # print("DEBUG: Enviando segmento a Google...")
                texto_google = self.recognizer.recognize_google(
                    audio_data, language=config.TARGET_LANGUAGE)
                # print(f"DEBUG: Recibido de Google: '{texto_google}'")
                return texto_google
            except sr.UnknownValueError:
                print("Google: Segmento no entendido.")
                return None # No es un error, simplemente no entendió
            except sr.RequestError as e:
                print(f"Google: Error de solicitud - {e}")
                # Podríamos reintentar o notificar error más grave
                self.error_callback(f"Error de conexión con Google Speech: {e}")
                # Considerar detener todo si los errores persisten?
                # self._stop_event.set() # Descomentar para detener en error de red
                return None
            except Exception as e:
                 print(f"Error inesperado en recognize_google: {e}")
                 return None