# In gui.py
"""Clase principal de la Interfaz Gráfica de Usuario (GUI) para AudioTranscriptorPro."""

import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import tkinter.font as tkFont
import pathlib
import threading
import time # Necesario para el retardo en la animación de highlight y formato de tiempo
from pydub import AudioSegment, exceptions as pydub_exceptions # Importar para obtener duración

# Importar módulos locales
import config
import utils
from utils import check_nvidia_smi, check_pytorch_cuda
import audio_handler
import playback
# from google_transcriber import GoogleTranscriber # Eliminado
from whisper_transcriber import WhisperTranscriber, WHISPER_AVAILABLE
from whisper_transcriber import _model_load_thread, _model_load_stop_event # Para cancelación

class AudioTranscriptorPro:
    """Clase que gestiona la interfaz gráfica y coordina el transcriptor Whisper."""

    def __init__(self, root: tk.Tk):
        self.ventana = root
        self.ventana.title(f"Audio a Texto Pro ({config.__version__}) - Whisper") # Título actualizado
        self.ventana.configure(bg=config.BG_COLOR)
        self.ventana.geometry("800x600") # Ajustar tamaño si es necesario
        self.ventana.protocol("WM_DELETE_WINDOW", self._on_closing)

        # --- Comprobación inicial del entorno ---
        print("--- Comprobación inicial del entorno ---")
        self.nvidia_drivers_detected = check_nvidia_smi()
        print(f"Detección preliminar de drivers NVIDIA (nvidia-smi): {self.nvidia_drivers_detected}")
        self.pytorch_cuda_available = check_pytorch_cuda()
        print(f"Verificación PyTorch CUDA disponible: {self.pytorch_cuda_available}")
        self.device_to_use = 'cuda' if self.pytorch_cuda_available else 'cpu'
        print(f"Dispositivo por defecto para ejecución de modelos: '{self.device_to_use}'")
        print(f"Whisper disponible: {WHISPER_AVAILABLE}")
        print("---------------------------------------")

        # Estado de la aplicación
        self.ruta_audio_original: pathlib.Path | None = None
        self.ruta_audio_wav: pathlib.Path | None = None # Ruta al WAV temporal para playback/whisper
        self.selected_whisper_model: str | None = None
        self.whisper_model_loaded = False
        self.is_loading_model = False
        self.whisper_transcription_complete = False
        self.transcription_result: dict | None = None # Almacenará el resultado de Whisper con timings

        # --- Estado de Depuración ---
        self.is_depurating = False
        self.playback_update_timer_id = None # ID para el 'after' del highlight
        self.current_highlighted_segment_index = -1
        self.is_paused = False # Flag para saber si la reproducción está pausada
        self.audio_duration_sec: float | None = None # Duración total del audio en segundos

        # --- Animación Whisper (para transcripción) ---
        self.animacion_whisper_activa = False
        self.animacion_whisper_id = None
        self.dot_index = 0
        self.dots_refs = []

        # --- Instancia de transcriptor Whisper ---
        self.whisper_transcriber = None
        if WHISPER_AVAILABLE:
            self.whisper_transcriber = WhisperTranscriber(
                update_callback=lambda result: self.ventana.after(0, self._update_texto_whisper, result),
                status_callback=lambda status: self.ventana.after(0, self.set_status, status),
                completion_callback=lambda success, result: self.ventana.after(0, self._on_whisper_transcription_complete, success, result),
                error_callback=lambda error: self.ventana.after(0, self._show_error, "Whisper Error", error)
            )
        else:
            print("INFO: WhisperTranscriber no se inicializará.")

        # --- Construir la interfaz ---
        self._setup_fonts()
        self._create_widgets()
        self._update_ui_state()

        # Mostrar mensaje inicial
        initial_status = "Bienvenido."
        if not WHISPER_AVAILABLE:
             initial_status += " Whisper no detectado. Funcionalidad limitada."
        else:
             initial_status += f" Dispositivo: {self.device_to_use}. Selecciona un modelo Whisper."
        self.set_status(initial_status)

        # Inicializar Pygame para playback
        if not playback.init_playback():
             self._show_error("Error Crítico", "No se pudo inicializar Pygame para la reproducción. La función de depuración no estará disponible.")
             # Podríamos deshabilitar el botón depurar permanentemente aquí
             # self.boton_depurar.config(state=tk.DISABLED)

    def _setup_fonts(self):
        """Configura las fuentes predeterminadas."""
        default_font = tkFont.nametofont("TkDefaultFont")
        default_font.configure(size=10)
        self.ventana.option_add("*Font", default_font)
        self.text_font = tkFont.Font(family="TkTextFont", size=11)
        self.title_font = tkFont.Font(family="TkHeadingFont", size=11, weight="bold")
        self.instruction_font = tkFont.Font(size=9, slant="italic")
        self.warning_font = tkFont.Font(size=9, weight="bold")

    # --- NUEVA FUNCIÓN HELPER ---
    def _format_time(self, seconds: float | None) -> str:
        """Formatea segundos a una cadena MM:SS."""
        if seconds is None or seconds < 0:
            return "--:--"
        try:
            # gmtime maneja los segundos correctamente para MM:SS
            return time.strftime('%M:%S', time.gmtime(seconds))
        except ValueError: # Puede ocurrir si los segundos son muy grandes o negativos
             return "--:--"
        except Exception: # Captura general por si acaso
             return "??:??"

    def _create_widgets(self):
        """Crea todos los elementos de la interfaz gráfica."""

        # --- Frame Superior: Controles Principales y Estado ---
        frame_superior = tk.Frame(self.ventana, bg=config.BG_COLOR)
        frame_superior.pack(pady=(10, 5), padx=20, fill=tk.X)

        # --- Columna Izquierda: Instrucciones y Selección ---
        frame_controles = tk.Frame(frame_superior, bg=config.BG_COLOR)
        frame_controles.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), anchor='nw') # Anclar arriba izquierda

        tk.Label(frame_controles, text="Pasos:", font=self.title_font, bg=config.BG_COLOR).pack(anchor='w')
        tk.Label(frame_controles, text="1. Selecciona modelo Whisper", font=self.instruction_font, bg=config.BG_COLOR).pack(anchor='w', padx=(5,0))
        tk.Label(frame_controles, text="2. Selecciona archivo de audio", font=self.instruction_font, bg=config.BG_COLOR).pack(anchor='w', padx=(5,0))
        tk.Label(frame_controles, text="3. Pulsa 'Transcribir'", font=self.instruction_font, bg=config.BG_COLOR).pack(anchor='w', padx=(5,0))
        tk.Label(frame_controles, text="4. Pulsa 'Depurar' (opcional)", font=self.instruction_font, bg=config.BG_COLOR).pack(anchor='w', padx=(5,0))


        tk.Label(frame_controles, text="Modelo Whisper:", font=tkFont.Font(weight='bold'), bg=config.BG_COLOR).pack(anchor='w', pady=(8, 2))
        self.model_var = tk.StringVar()
        self.model_combobox = ttk.Combobox(
            frame_controles,
            textvariable=self.model_var,
            values=config.WHISPER_MODELS if WHISPER_AVAILABLE else ["Whisper no disponible"],
            state="readonly" if WHISPER_AVAILABLE else "disabled",
            width=15
        )
        if WHISPER_AVAILABLE:
            self.model_combobox.set(config.DEFAULT_WHISPER_MODEL)
            self.model_combobox.bind("<<ComboboxSelected>>", self._on_model_select)
        self.model_combobox.pack(anchor='w', pady=(0, 5))

        self.model_warning_label = tk.Label(frame_controles, text="", font=self.warning_font, fg="orange", bg=config.BG_COLOR, wraplength=180, justify=tk.LEFT)
        self.model_warning_label.pack(anchor='w', pady=(0,5))
        if WHISPER_AVAILABLE: self._update_model_warning(config.DEFAULT_WHISPER_MODEL)

        self.boton_seleccionar = tk.Button(frame_controles, text="Seleccionar Audio", command=self._seleccionar_audio_action, padx=10, pady=5)
        self.boton_seleccionar.pack(anchor='w', pady=(10, 5))

        self.boton_transcribir = tk.Button(frame_controles, text="Transcribir", command=self._transcribir_action, padx=10, pady=5)
        self.boton_transcribir.pack(anchor='w', pady=(5, 5))

        # --- NUEVO: Botón Depurar ---
        self.boton_depurar = tk.Button(frame_controles, text="Depurar", command=self._toggle_depuration_mode, padx=10, pady=5, state=tk.DISABLED)
        self.boton_depurar.pack(anchor='w', pady=(15, 5))

        # --- Columna Derecha: Estado y Progreso ---
        frame_estado_progreso = tk.Frame(frame_superior, bg=config.BG_COLOR)
        frame_estado_progreso.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.status_label = tk.Label(frame_estado_progreso, text="Inicializando...", bg=config.BG_COLOR, font=("TkDefaultFont", 10), anchor='nw', justify=tk.LEFT, wraplength=550)
        self.status_label.pack(fill=tk.X, pady=(5,2), anchor='nw')

        self.progress_var = tk.IntVar()
        self.progress_bar = ttk.Progressbar(
            frame_estado_progreso, orient="horizontal", length=300, mode="determinate", variable=self.progress_var
        )
        # pack/pack_forget se maneja dinámicamente

        self.whisper_dots_frame = tk.Frame(frame_estado_progreso, bg=config.BG_COLOR)
        # pack/pack_forget se maneja dinámicamente
        tk.Label(self.whisper_dots_frame, text="Whisper procesando:", bg=config.BG_COLOR, font=self.instruction_font).pack(side=tk.LEFT, padx=(0,5))
        self.dots_canvas = tk.Canvas(self.whisper_dots_frame, width=40, height=12, bg=config.BG_COLOR, highlightthickness=0)
        self.dots_canvas.pack(side=tk.LEFT)
        self.dots_refs = [self.dots_canvas.create_oval(i * 12 + 2, 2, i * 12 + 10, 10, fill=config.STATUS_COLOR_GRAY, tags=f"dot{i}") for i in range(3)]

        # --- NUEVO: Frame Controles de Playback (inicialmente oculto) ---
        self.frame_playback_controls = tk.Frame(frame_estado_progreso, bg=config.BG_COLOR)
        # Se mostrará con pack() cuando se entre en modo depuración

        self.boton_play_pause = tk.Button(self.frame_playback_controls, text="▶ Play", command=self._toggle_play_pause, width=8, padx=5, pady=2)
        self.boton_play_pause.pack(side=tk.LEFT, padx=5, pady=5)

        self.boton_stop_playback = tk.Button(self.frame_playback_controls, text="■ Stop", command=self._stop_playback_action, width=8, padx=5, pady=2)
        self.boton_stop_playback.pack(side=tk.LEFT, padx=5, pady=5)

        # Placeholder para tiempo/duración
        self.playback_time_label = tk.Label(self.frame_playback_controls, text="--:-- / --:--", bg=config.BG_COLOR, font=self.instruction_font) # Texto inicial
        self.playback_time_label.pack(side=tk.LEFT, padx=10, pady=5)


        # --- Frame Inferior: Área de Texto Única (Whisper) ---
        frame_texto_whisper = tk.Frame(self.ventana, bg=config.BG_COLOR)
        frame_texto_whisper.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 5))

        frame_whisper = tk.LabelFrame(frame_texto_whisper, text="Transcripción Whisper", font=self.title_font, bg=config.BG_COLOR, padx=5, pady=5)
        frame_whisper.pack(fill=tk.BOTH, expand=True) # Ocupa todo el espacio

        self.area_texto_whisper = scrolledtext.ScrolledText(frame_whisper, wrap=tk.WORD, font=self.text_font, height=15, padx=10, pady=10, borderwidth=1, relief=tk.SOLID, state=tk.DISABLED)
        self.area_texto_whisper.pack(fill=tk.BOTH, expand=True)
        # Configurar tag para resaltar
        self.area_texto_whisper.tag_configure("highlight", background=config.HIGHLIGHT_COLOR)
        self.whisper_status_canvas_circle = tk.Canvas(frame_whisper, width=10, height=10, bg=config.BG_COLOR, highlightthickness=0)
        self.whisper_status_canvas_circle.place(relx=1.0, rely=0.0, x=-5, y=5, anchor=tk.NE) # Indicador estado transcripción
        utils.draw_status_circle(self.whisper_status_canvas_circle, config.STATUS_COLOR_GRAY)


        # --- Frame Final: Botones de Acción (Whisper) ---
        frame_botones_accion = tk.Frame(self.ventana, bg=config.BG_COLOR)
        frame_botones_accion.pack(pady=(0, 15), fill=tk.X, padx=20)

        # Centrar botones de Copiar/Exportar
        center_frame_botones = tk.Frame(frame_botones_accion, bg=config.BG_COLOR)
        center_frame_botones.pack(anchor='center') # Centra el frame interior

        self.boton_copiar_whisper = tk.Button(center_frame_botones, text="Copiar Texto", command=self._copiar_whisper_action, state=tk.DISABLED, padx=10, pady=5)
        self.boton_copiar_whisper.pack(side=tk.LEFT, padx=5)

        self.boton_exportar_whisper = tk.Button(center_frame_botones, text="Exportar Texto", command=self._exportar_whisper_action, state=tk.DISABLED, padx=10, pady=5)
        self.boton_exportar_whisper.pack(side=tk.LEFT, padx=5)


    # --- Métodos de Acción (Triggers de Usuario) ---

    def _on_model_select(self, event=None):
        """Acción cuando se selecciona un modelo Whisper."""
        if not self.whisper_transcriber:
             self.set_status("Error: Whisper no está disponible.")
             return

        selected = self.model_var.get()
        if not selected or (selected == self.selected_whisper_model and self.whisper_model_loaded):
             print(f"Modelo '{selected}' ya seleccionado o carga no necesaria.")
             return

        print(f"Acción: Selección de modelo Whisper -> {selected}")
        # Si estamos en modo depuración, salir primero
        if self.is_depurating:
            self._toggle_depuration_mode(force_exit=True)

        self.selected_whisper_model = selected
        self.whisper_model_loaded = False
        self.is_loading_model = True
        self._update_model_warning(selected)
        self._reset_transcription_state() # Limpiar resultados anteriores
        self._update_ui_state()

        self.progress_var.set(0)
        # Simplemente empaqueta la barra sin referencia 'before' (CORREGIDO)
        self.progress_bar.pack(fill=tk.X, pady=(2,5))
        self.set_status(f"Iniciando carga del modelo '{selected}'...")

        self.whisper_transcriber.load_model(
            model_name=selected,
            progress_callback=lambda msg, perc: self.ventana.after(0, self._update_model_load_progress, msg, perc),
            model_completion_callback=lambda success, name: self.ventana.after(0, self._on_model_load_complete, success, name)
        )

    def _update_model_warning(self, model_name):
        """Actualiza la etiqueta de advertencia según el modelo."""
        warning_text = ""
        if model_name == "medium":
            warning_text = config.MODEL_MEDIUM_WARNING if self.device_to_use == 'cpu' else ""
        elif model_name == "large":
            warning_text = config.MODEL_LARGE_WARNING if self.device_to_use == 'cpu' else ""
        self.model_warning_label.config(text=warning_text)


    def _seleccionar_audio_action(self):
        """Acción del botón 'Seleccionar Audio'."""
        if not self.whisper_model_loaded:
             self._show_error("Error", "Debes seleccionar y cargar un modelo Whisper primero.")
             return
        # Si estamos en modo depuración, salir primero
        if self.is_depurating:
            self._toggle_depuration_mode(force_exit=True)

        print("Acción: Seleccionar audio iniciada.")
        selected_path = audio_handler.select_audio_file()
        if not selected_path:
            status_msg = "Selección cancelada."
            if self.selected_whisper_model:
                 status_msg += f" Modelo cargado: {self.selected_whisper_model}"
            self.set_status(status_msg)
            return

        self.ruta_audio_original = selected_path
        self.ruta_audio_wav = None
        self.audio_duration_sec = None # RESETEAR DURACIÓN
        self.set_status(f"Archivo: {self.ruta_audio_original.name}. Convirtiendo a WAV...")
        self._reset_transcription_state()
        self._update_ui_state() # Deshabilitar 'Transcribir' mientras convierte

        threading.Thread(target=self._convert_and_prepare_audio, args=(selected_path,), daemon=True).start()


    def _convert_and_prepare_audio(self, audio_path: pathlib.Path):
        """Convierte a WAV, obtiene duración y actualiza la GUI."""
        wav_path = audio_handler.convert_to_wav_if_needed(audio_path)
        duration_sec = None # Inicializar duración para este ámbito

        # Si la conversión fue exitosa, intentar obtener la duración
        if wav_path:
            try:
                print(f"Obteniendo duración de: {wav_path.name}")
                # Usar pydub para cargar el WAV temporal y obtener duración
                audio = AudioSegment.from_wav(str(wav_path))
                duration_sec = len(audio) / 1000.0 # len da ms, convertir a segundos
                print(f"Duración obtenida: {duration_sec:.2f} segundos")
            except pydub_exceptions.CouldntDecodeError:
                print(f"Advertencia: Pydub no pudo decodificar {wav_path.name} para obtener duración (posiblemente vacío o formato raro).")
            except Exception as e:
                print(f"Advertencia: No se pudo obtener la duración del archivo WAV ({wav_path.name}): {e}")
                # No es un error crítico, continuaremos sin la duración total

        def update_gui_after_conversion():
            if wav_path:
                self.ruta_audio_wav = wav_path
                self.audio_duration_sec = duration_sec # ALMACENAR DURACIÓN (puede ser None)

                if self.whisper_transcriber:
                     self.whisper_transcriber.set_audio_file(self.ruta_audio_wav)
                self.ventana.title(f"Audio a Texto Pro - {self.ruta_audio_original.name} ({config.__version__})")

                duration_str = self._format_time(self.audio_duration_sec)
                status_msg = f"Audio listo ({self.ruta_audio_wav.name} [{duration_str}])."
                if self.selected_whisper_model:
                     status_msg += f" Modelo: {self.selected_whisper_model}."
                status_msg += " Pulsa 'Transcribir'."
                self.set_status(status_msg)
                print(f"Audio preparado. WAV path: {self.ruta_audio_wav}")

                # Actualizar etiqueta de tiempo inicial
                try:
                    if self.playback_time_label.winfo_exists():
                        self.playback_time_label.config(text=f"--:-- / {self._format_time(self.audio_duration_sec)}")
                except tk.TclError: pass # Ignorar si el widget no existe

            else:
                # Falló la conversión
                self.ruta_audio_original = None
                self.ruta_audio_wav = None
                self.audio_duration_sec = None # RESETEAR DURACIÓN
                # El error ya se mostró en audio_handler
                self.set_status("Error en conversión. Selecciona otro archivo.")
                self.ventana.title(f"Audio a Texto Pro ({config.__version__}) - Whisper")
                try:
                     if self.playback_time_label.winfo_exists():
                        self.playback_time_label.config(text="--:-- / --:--") # Resetear tiempo
                except tk.TclError: pass

            self._update_ui_state()

        self.ventana.after(0, update_gui_after_conversion)


    def _transcribir_action(self):
        """Acción del botón 'Transcribir'."""
        if not self.ruta_audio_wav:
            self._show_error("Error", "No hay un archivo de audio preparado (WAV).")
            return
        if not self.whisper_model_loaded:
             self._show_error("Error", "No hay un modelo Whisper cargado.")
             return
        if self.whisper_transcriber and self.whisper_transcriber.is_running():
            self._show_error("Información", "Ya hay una transcripción en curso.")
            return
        if self.is_depurating: # No transcribir si se está depurando
             self._show_error("Información", "Sal del modo 'Depurar' antes de transcribir de nuevo.")
             return

        print("Acción: Iniciar transcripción Whisper.")
        self._reset_transcription_state()
        self.set_status(f"Iniciando transcripción con Whisper '{self.selected_whisper_model}'...")
        self._update_ui_state() # Deshabilitar controles

        utils.draw_status_circle(self.whisper_status_canvas_circle, config.STATUS_COLOR_YELLOW) # Whisper corriendo
        self._start_whisper_animation()

        # Iniciar Whisper Transcriber
        if self.whisper_transcriber:
            self.whisper_transcriber.start()


    def _copiar_whisper_action(self):
        """Acción del botón 'Copiar Texto'."""
        try:
            texto = self.area_texto_whisper.get("1.0", tk.END).strip()
            utils.copy_to_clipboard(self.ventana, texto)
        except tk.TclError:
            print("Error al copiar: El área de texto no existe.")


    def _exportar_whisper_action(self):
        """Acción del botón 'Exportar Texto'."""
        try:
            texto = self.area_texto_whisper.get("1.0", tk.END).strip()
            default_filename = f"Transcripción Whisper ({self.selected_whisper_model}) - {self.ruta_audio_original.stem if self.ruta_audio_original else 'audio'}"
            utils.export_text_to_file(texto, default_filename)
        except tk.TclError:
            print("Error al exportar: El área de texto no existe.")


    # --- Métodos Callback (Llamados por el transcriptor y cargador) ---

    def _update_model_load_progress(self, message: str, percentage: int):
        """Actualiza la UI para mostrar el progreso de carga del modelo."""
        if not self.is_loading_model: return
        self.set_status(message)
        self.progress_var.set(percentage)

    def _on_model_load_complete(self, success: bool, model_name: str):
        """Callback cuando la carga del modelo Whisper termina."""
        print(f"Callback: Carga del modelo '{model_name}' completada (Éxito: {success})")
        self.is_loading_model = False
        self.progress_bar.pack_forget()

        if success:
            self.whisper_model_loaded = True
            self.selected_whisper_model = model_name
            self.model_var.set(model_name)
            self.set_status(f"Modelo '{model_name}' cargado ({self.device_to_use}). Selecciona audio o transcribe.")
        else:
            self.whisper_model_loaded = False
            self.selected_whisper_model = None
            # El mensaje de error ya se mostró, actualizar estado general
            self.set_status(f"Error al cargar modelo '{model_name}'. Intenta de nuevo o elige otro.")

        self._update_ui_state()


    def _update_texto_whisper(self, result_data: dict):
        """Actualiza el área de texto de Whisper con el resultado completo."""
        if not self.area_texto_whisper or not self.area_texto_whisper.winfo_exists(): return

        # Almacenar el resultado completo para la depuración
        self.transcription_result = result_data
        texto_completo = result_data.get("text", "Error: No se encontró texto en el resultado.")

        try:
            self.area_texto_whisper.config(state=tk.NORMAL)
            self.area_texto_whisper.delete("1.0", tk.END)
            self.area_texto_whisper.insert("1.0", texto_completo)
            self.area_texto_whisper.see("1.0") # Ir al inicio
            self.area_texto_whisper.config(state=tk.DISABLED) # Deshabilitar edición por defecto
        except tk.TclError:
            print("Error al actualizar área de texto (posiblemente cerrada).")

        self._update_ui_state()


    def _on_whisper_transcription_complete(self, success: bool, result: dict | None):
        """Callback cuando la transcripción de Whisper termina."""
        print(f"Callback: Transcripción Whisper completada (Éxito: {success})")
        self.whisper_transcription_complete = True
        self._stop_whisper_animation()
        utils.draw_status_circle(self.whisper_status_canvas_circle, config.STATUS_COLOR_GREEN if success else config.STATUS_COLOR_RED)

        # Actualizar el resultado almacenado (incluso si falla, para mostrar el texto de error)
        self.transcription_result = result

        # Habilitar 'Depurar' solo si la transcripción fue exitosa Y tiene segmentos
        can_depurate_now = success and result and result.get("segments") and self.ruta_audio_wav
        if can_depurate_now:
            self.set_status("Transcripción completada. Puedes 'Depurar' o exportar.")
            self.boton_depurar.config(state=tk.NORMAL)
        elif success:
            self.set_status("Transcripción completada (sin info de segmentos para depurar).")
            self.boton_depurar.config(state=tk.DISABLED)
        else:
            self.set_status("Error durante la transcripción Whisper.")
            self.boton_depurar.config(state=tk.DISABLED)

        # Actualizar estado de botones
        self._update_ui_state()


    def _show_error(self, title: str, message: str):
        """Muestra un mensaje de error y actualiza el estado."""
        print(f"ERROR: {title} - {message}")
        messagebox.showerror(title, message)

        if self.is_loading_model: # Si el error ocurre durante la carga
            self.is_loading_model = False
            self.progress_bar.pack_forget()
            self._update_ui_state() # Actualizar botones tras fallo de carga

        # Actualizar estado general si no indica ya un error
        try:
             if self.status_label.winfo_exists():
                 current_status = self.status_label.cget("text")
                 if "Error" not in current_status and "Falló" not in current_status:
                      self.set_status(f"Error: {title}. Revisa la consola.")
        except tk.TclError: pass # Label podría no existir al cerrar


    # --- Métodos de Gestión de Estado Interno y UI ---

    def set_status(self, message: str):
        """Actualiza la etiqueta de estado."""
        try:
            if self.status_label and self.status_label.winfo_exists():
                self.status_label.config(text=message)
        except tk.TclError: pass # Ignorar si el widget no existe

    def _clear_text_area(self):
        """Limpia el contenido del área de texto Whisper."""
        try:
            if self.area_texto_whisper and self.area_texto_whisper.winfo_exists():
                self.area_texto_whisper.config(state=tk.NORMAL)
                self.area_texto_whisper.delete("1.0", tk.END)
                self.area_texto_whisper.config(state=tk.DISABLED) # Deshabilitado por defecto
        except tk.TclError: pass

    def _reset_transcription_state(self):
        """Resetea el estado relacionado con una transcripción específica."""
        self.whisper_transcription_complete = False
        self.transcription_result = None
        self._clear_text_area()
        utils.draw_status_circle(self.whisper_status_canvas_circle, config.STATUS_COLOR_GRAY)
        # Asegurarse de salir del modo depuración si estaba activo
        if self.is_depurating:
             self._toggle_depuration_mode(force_exit=True)
        self.boton_depurar.config(state=tk.DISABLED) # Deshabilitar depurar al resetear
        # Los botones de resultado se actualizarán automáticamente por _update_ui_state


    def _update_ui_state(self):
        """Actualiza el estado (habilitado/deshabilitado) de los widgets."""
        try: # Envolver en try/except por si se llama durante el cierre
            # Estados base
            is_transcribing = self.whisper_transcriber is not None and self.whisper_transcriber.is_running()
            is_busy_process = self.is_loading_model or is_transcribing # Ocupado por carga o transcripción

            # Combobox Modelo
            model_combo_state = tk.NORMAL if WHISPER_AVAILABLE and not is_busy_process and not self.is_depurating else tk.DISABLED
            if self.model_combobox: self.model_combobox.config(state=model_combo_state)

            # Botón Seleccionar Audio
            select_audio_state = tk.NORMAL if WHISPER_AVAILABLE and self.whisper_model_loaded and not is_busy_process and not self.is_depurating else tk.DISABLED
            self.boton_seleccionar.config(state=select_audio_state)

            # Botón Transcribir
            can_transcribe = self.ruta_audio_wav and self.whisper_model_loaded and not is_busy_process and not self.is_depurating
            transcribe_state = tk.NORMAL if can_transcribe else tk.DISABLED
            self.boton_transcribir.config(state=transcribe_state)
            self.boton_transcribir.config(text="Transcribir" if not is_transcribing else "Procesando...")

            # Botón Depurar
            can_enter_depurate = self.whisper_transcription_complete and \
                           self.transcription_result and \
                           self.transcription_result.get("segments") and \
                           self.ruta_audio_wav and \
                           not is_busy_process # Solo se puede entrar si no hay otro proceso

            if self.is_depurating:
                self.boton_depurar.config(text="Salir Depurar", state=tk.NORMAL)
            else:
                self.boton_depurar.config(text="Depurar", state=tk.NORMAL if can_enter_depurate else tk.DISABLED)

            # Área de texto Whisper (Editable solo en depuración)
            text_area_state = tk.NORMAL if self.is_depurating else tk.DISABLED
            if self.area_texto_whisper: self.area_texto_whisper.config(state=text_area_state)

            # Controles de Playback (Visibles solo en depuración)
            if self.is_depurating:
                # Simplemente empaqueta los controles sin referencia 'before' (CORREGIDO)
                self.frame_playback_controls.pack(pady=5, anchor='w') # Mostrar
            else:
                self.frame_playback_controls.pack_forget() # Ocultar

            # Botones de Resultados Whisper
            whisper_results_text = ""
            if self.area_texto_whisper and self.area_texto_whisper.winfo_exists():
                 whisper_results_text = self.area_texto_whisper.get("1.0", tk.END).strip()

            # Habilitar si hay texto y no es un mensaje de error claro
            whisper_results_state = tk.DISABLED
            if whisper_results_text and not whisper_results_text.lower().startswith("error"):
                whisper_results_state = tk.NORMAL
            # Deshabilitar si estamos procesando o depurando (copiar/exportar es del estado final)
            if is_busy_process or self.is_depurating:
                whisper_results_state = tk.DISABLED

            if self.boton_copiar_whisper: self.boton_copiar_whisper.config(state=whisper_results_state)
            if self.boton_exportar_whisper: self.boton_exportar_whisper.config(state=whisper_results_state)

        except tk.TclError:
            print("Advertencia: TclError durante _update_ui_state (probablemente ventana cerrada).")
        except Exception as e:
             print(f"Error inesperado en _update_ui_state: {e}")


    # --- Animación Whisper (TRANSCRIPCIÓN) ---

    def _animate_whisper_status(self):
        """Ciclo de animación de los puntos para la transcripción Whisper."""
        if not self.animacion_whisper_activa:
            try:
                 if self.whisper_dots_frame.winfo_exists():
                     self.whisper_dots_frame.pack_forget()
            except tk.TclError: pass
            return

        try:
            if not self.whisper_dots_frame.winfo_viewable():
                 # Mostrar después de la barra de progreso si está visible
                 if self.is_loading_model and self.progress_bar.winfo_viewable():
                     self.whisper_dots_frame.pack(pady=2, anchor='w', after=self.progress_bar)
                 else: # Si no, mostrar solo
                      self.whisper_dots_frame.pack(pady=2, anchor='w')

            colors = [config.STATUS_COLOR_GRAY] * 3
            colors[self.dot_index % 3] = config.STATUS_COLOR_YELLOW
            if self.dots_canvas.winfo_exists(): # Comprobar si el canvas aún existe
                for i, color in enumerate(colors):
                    if i < len(self.dots_refs):
                        self.dots_canvas.itemconfig(self.dots_refs[i], fill=color)
                self.dot_index += 1
                # Programar siguiente frame solo si la animación sigue activa
                if self.animacion_whisper_activa:
                    self.animacion_whisper_id = self.ventana.after(300, self._animate_whisper_status)
        except tk.TclError:
             print("Error TclError en animación (probablemente ventana cerrada).")
             self.animacion_whisper_activa = False


    def _start_whisper_animation(self):
        """Inicia la animación de puntos para la transcripción."""
        if not self.animacion_whisper_activa:
            self.animacion_whisper_activa = True
            self.dot_index = 0
            self._animate_whisper_status() # Llama a la animación recursiva

    def _stop_whisper_animation(self):
        """Detiene la animación de puntos y la oculta."""
        if self.animacion_whisper_activa:
            self.animacion_whisper_activa = False
            if self.animacion_whisper_id:
                try:
                    self.ventana.after_cancel(self.animacion_whisper_id)
                except tk.TclError: pass
                self.animacion_whisper_id = None
            try:
                 if self.dots_canvas.winfo_exists(): # Comprobar si el canvas aún existe
                    for i in range(len(self.dots_refs)):
                        self.dots_canvas.itemconfig(self.dots_refs[i], fill=config.STATUS_COLOR_GRAY)
                    self.whisper_dots_frame.pack_forget()
            except tk.TclError: pass
            self.dot_index = 0


    # --- NUEVO: Lógica de Depuración y Playback Sincronizado ---

    def _toggle_depuration_mode(self, force_exit=False):
        """Entra o sale del modo de depuración."""
        if force_exit and not self.is_depurating:
            return # No hacer nada si se fuerza salida y no se está depurando

        if not self.is_depurating and not force_exit:
            # --- Entrar en modo depuración ---
            if not self.ruta_audio_wav or not self.transcription_result or not self.transcription_result.get("segments"):
                self._show_error("Error Depuración", "No hay audio o resultado de transcripción válido para depurar.")
                return
            if not playback._mixer_initialized: # Usar flag interno de playback
                 self._show_error("Error Playback", "El módulo de reproducción de audio no se inicializó correctamente.")
                 return

            print("Entrando en modo depuración...")
            self.is_depurating = True
            self.set_status("Modo Depuración: Edita el texto y usa los controles de audio.")

            # Cargar audio en pygame si no está cargado ya
            # Es importante descargarlo primero si hubiera algo cargado previamente
            playback.unload_audio()
            if not playback.load_audio_from_path(self.ruta_audio_wav):
                 self._show_error("Error Playback", f"No se pudo cargar {self.ruta_audio_wav.name} para reproducción.")
                 self.is_depurating = False # Falló la entrada
                 self._update_ui_state()
                 return

            # Actualizar UI (habilita texto, muestra controles, deshabilita otros)
            self._update_ui_state()
            self.boton_play_pause.config(text="▶ Play") # Estado inicial del botón
            # Actualizar tiempo inicial
            total_duration_str = self._format_time(self.audio_duration_sec)
            try:
                 if self.playback_time_label.winfo_exists():
                     self.playback_time_label.config(text=f"00:00 / {total_duration_str}")
            except tk.TclError: pass

        else:
            # --- Salir del modo depuración ---
            print("Saliendo de modo depuración...")
            self.is_depurating = False
            self._stop_playback_action() # Detener audio al salir (esto resetea is_paused)
            playback.unload_audio() # Descargar audio
            self._remove_highlight() # Quitar resaltado

            # Restaurar estado UI
            self._update_ui_state()
            status_msg = "Modo Depuración finalizado."
            if self.selected_whisper_model:
                status_msg += f" Modelo: {self.selected_whisper_model}."
            if self.ruta_audio_original:
                 status_msg += f" Archivo: {self.ruta_audio_original.name}."
            self.set_status(status_msg)


    def _toggle_play_pause(self):
        """Inicia, pausa o reanuda la reproducción del audio usando flag self.is_paused."""
        if not self.is_depurating: return
        print("-" * 10)
        print(f"Toggle Play/Pause. Button: {self.boton_play_pause.cget('text')}, is_paused flag: {self.is_paused}")

        # Determinar acción basada en el estado del botón (intención del usuario)
        wants_to_play = self.boton_play_pause.cget("text") == "▶ Play"

        if wants_to_play:
            # Usuario quiere reproducir/reanudar
            if self.is_paused:
                # Estaba pausado -> Reanudar
                print("Action: Resuming (calling unpause_audio).")
                playback.unpause_audio()
                self.is_paused = False # Ya no está pausado
                # Verificar si realmente está sonando ahora
                if playback.is_playing():
                     self.boton_play_pause.config(text="❚❚ Pause")
                     self._start_highlight_update_timer()
                else:
                     print("WARN: Unpause seemed to fail, playback not busy.")
                     # Quizás el audio terminó justo al pausar? Resetear estado.
                     self.boton_play_pause.config(text="▶ Play")
                     self._stop_highlight_update_timer()
            else:
                # No estaba pausado -> Iniciar desde el principio
                print("Action: Starting playback from beginning.")
                if playback.play_audio(start_seconds=0.0):
                    self.is_paused = False # Asegurar que no está marcado como pausado
                    self.boton_play_pause.config(text="❚❚ Pause")
                    self._start_highlight_update_timer()
                else:
                    print("Error: Failed to start playback.")
                    self._show_error("Playback Error", "No se pudo iniciar la reproducción.")

        else: # wants_to_play is False (Botón muestra "❚❚ Pause")
            # Usuario quiere pausar
            # Solo tiene sentido pausar si está sonando activamente
            if playback.is_playing(): # Usamos get_busy() aquí
                print("Action: Pausing playback (calling pause_audio).")
                playback.pause_audio()
                self.is_paused = True # Marcar como pausado
                self.boton_play_pause.config(text="▶ Play")
                self._stop_highlight_update_timer()
            else:
                 # Estaba 'busy=False' aunque el botón decía Pause. Estado raro.
                 print("Warning: Tried to pause, but playback was not busy. Resetting button.")
                 self.is_paused = False # No está pausado si no estaba sonando
                 self.boton_play_pause.config(text="▶ Play")
                 self._stop_highlight_update_timer()

        print(f"End toggle. Button: {self.boton_play_pause.cget('text')}, is_paused flag: {self.is_paused}")
        print("-" * 10)


    def _stop_playback_action(self):
        """Detiene la reproducción y resetea el estado."""
        if not self.is_depurating: return
        print("Deteniendo playback...")
        playback.stop_audio()
        self._stop_highlight_update_timer()
        self._remove_highlight()
        self.is_paused = False # RESETEAR FLAG
        self.boton_play_pause.config(text="▶ Play") # Resetear botón
        # Resetear tiempo a 00:00
        total_duration_str = self._format_time(self.audio_duration_sec)
        try:
             if self.playback_time_label.winfo_exists():
                self.playback_time_label.config(text=f"00:00 / {total_duration_str}")
        except tk.TclError: pass


    def _start_highlight_update_timer(self):
        """Inicia el temporizador para actualizar el resaltado Y el tiempo."""
        # Cancelar timer anterior si existe
        if self.playback_update_timer_id:
            try:
                self.ventana.after_cancel(self.playback_update_timer_id)
            except tk.TclError: pass # Podría no existir si la ventana se está cerrando
            self.playback_update_timer_id = None # Limpiar ID

        # Llamar inmediatamente una vez para respuesta rápida (actualiza tiempo y highlight)
        self._update_playback_highlight()

        # Programar llamadas periódicas si la ventana aún existe y seguimos depurando
        try:
             if self.ventana.winfo_exists() and self.is_depurating:
                 self.playback_update_timer_id = self.ventana.after(config.PLAYBACK_UPDATE_INTERVAL_MS, self._start_highlight_update_timer)
        except tk.TclError:
             print("No se pudo programar el timer (ventana cerrada?).")
             self.playback_update_timer_id = None


    def _stop_highlight_update_timer(self):
        """Detiene el temporizador de actualización del resaltado."""
        if self.playback_update_timer_id:
            try:
                self.ventana.after_cancel(self.playback_update_timer_id)
            except tk.TclError: pass
            self.playback_update_timer_id = None


    def _remove_highlight(self):
        """Quita cualquier resaltado del texto."""
        try:
             if self.area_texto_whisper and self.area_texto_whisper.winfo_exists():
                 self.area_texto_whisper.tag_remove("highlight", "1.0", tk.END)
                 self.current_highlighted_segment_index = -1
        except tk.TclError:
             pass # El widget podría no existir al cerrar


    def _update_playback_highlight(self):
        """Actualiza el resaltado del texto Y el tiempo según la posición del audio."""
        # --- Comprobaciones iniciales ---
        if not self.is_depurating: # Salir si no estamos depurando
            if self.playback_update_timer_id: self._stop_highlight_update_timer()
            return

        # Obtener tiempo actual solo si no estamos pausados (get_pos avanza aunque esté pausado)
        current_time_ms = -1
        if not self.is_paused:
             current_time_ms = playback.get_current_pos_ms()
        else:
             # Si estamos pausados, ¿qué tiempo mostramos? Podríamos guardar el último conocido.
             # O simplemente no actualizar la etiqueta mientras está pausado. Por simplicidad,
             # usamos get_pos, pero sabiendo que puede no ser lo ideal si se necesita precisión en pausa.
             current_time_ms = playback.get_current_pos_ms() # Usamos get_pos de todos modos por ahora


        # --- Actualizar etiqueta de tiempo ---
        current_time_sec = current_time_ms / 1000.0 if current_time_ms != -1 else 0
        current_time_str = self._format_time(current_time_sec)
        total_duration_str = self._format_time(self.audio_duration_sec)
        try:
            if self.playback_time_label.winfo_exists():
                 self.playback_time_label.config(text=f"{current_time_str} / {total_duration_str}")
        except tk.TclError: pass

        # --- Comprobar si el audio ha terminado o se ha detenido ---
        # get_busy() devuelve False si se detiene o termina.
        # Necesitamos manejar el caso en que termina naturalmente mientras el botón dice "Pause".
        if not self.is_paused and not playback.is_playing():
            # Si no está pausado y no está 'busy', entonces o se detuvo o terminó.
            # Si el tiempo actual es muy cercano (o mayor) a la duración, asumimos que terminó.
            ended_naturally = False
            if self.audio_duration_sec is not None and current_time_sec >= self.audio_duration_sec - 0.1: # Margen pequeño
                 ended_naturally = True

            if ended_naturally:
                 print("Playback finalizado naturalmente.")
            else:
                 # Si no terminó naturalmente pero no está busy, algo lo detuvo externamente?
                 print("Playback detenido inesperadamente (no por pausa).")

            self._stop_playback_action() # Llama a stop, que resetea todo
            return # Salir de la función aquí


        # --- Actualizar highlight SOLO si estamos reproduciendo (no pausados) ---
        if not self.is_paused:
            # Si current_time_ms es -1 aquí, algo raro pasó, salir.
            if current_time_ms == -1: return

            segments = self.transcription_result.get("segments", []) if self.transcription_result else []
            found_segment_index = -1

            # Buscar el segmento actual
            for i, segment in enumerate(segments):
                start = segment.get('start')
                end = segment.get('end')
                if start is not None and end is not None and start <= current_time_sec < end:
                    found_segment_index = i
                    break

            # Si el segmento a resaltar no ha cambiado, no hacer nada más con el highlight
            if found_segment_index == self.current_highlighted_segment_index:
                return

            # Quitar resaltado anterior
            self._remove_highlight()

            # Aplicar nuevo resaltado si se encontró un segmento válido
            if found_segment_index != -1:
                segment_to_highlight = segments[found_segment_index]
                segment_text = segment_to_highlight.get('text', '').strip()
                if segment_text:
                    try:
                        if self.area_texto_whisper.winfo_exists():
                            # Intentar encontrar el texto. Puede ser lento en textos largos.
                            # Una optimización sería buscar desde la posición del segmento anterior.
                            start_index = self.area_texto_whisper.search(segment_text, "1.0", tk.END)
                            if start_index:
                                end_index = f"{start_index}+{len(segment_text)}c"
                                self.area_texto_whisper.tag_add("highlight", start_index, end_index)
                                self.area_texto_whisper.see(start_index) # Auto-scroll
                                self.current_highlighted_segment_index = found_segment_index
                            else:
                                print(f"WARN: No se encontró el texto del segmento '{segment_text}' en el widget.")
                                self.current_highlighted_segment_index = -1
                    except tk.TclError: pass # Widget destruido
                    except Exception as e:
                        print(f"Error inesperado al buscar/resaltar segmento: {e}")
                        self.current_highlighted_segment_index = -1
                else:
                     self.current_highlighted_segment_index = -1 # Segmento sin texto
            else:
                 self.current_highlighted_segment_index = -1 # Ningún segmento activo


    # --- Gestión de Cierre y Limpieza ---
    _stop_event_global = threading.Event() # Evento global para señalizar parada

    def _stop_all_processes(self, clear_audio=True):
         """Intenta detener todos los procesos activos (Whisper Transcripción, Playback)."""
         print("Intentando detener todos los procesos...")
         self._stop_event_global.set() # Señalizar parada global

         # Detener playback si está activo
         if self.is_depurating:
             self._toggle_depuration_mode(force_exit=True) # Esto detiene playback y limpia estado
         else:
             playback.stop_audio() # Detener por si acaso

         # Whisper (transcripción) no se puede detener directamente
         if self.whisper_transcriber and self.whisper_transcriber.is_running():
              print("INFO: Transcripción Whisper en curso, no se puede detener directamente. Esperando finalización...")
              # El join se hará en _on_closing si es necesario

         # Detener animación de transcripción si estaba activa
         self._stop_whisper_animation()

         # Cancelar carga de modelo si estuviera ocurriendo
         global _model_load_thread, _model_load_stop_event
         if _model_load_thread and _model_load_thread.is_alive():
             print("INFO: Intentando cancelar carga de modelo en curso...")
             _model_load_stop_event.set()
             # El join se hará en _on_closing

         if clear_audio:
             self.ruta_audio_original = None
             self.ruta_audio_wav = None
             audio_handler.cleanup_temp_wav()


    def _on_closing(self):
        """Manejador para el evento de cierre de ventana."""
        print("Cerrando aplicación...")

        is_busy = self.is_loading_model or \
                  (self.whisper_transcriber and self.whisper_transcriber.is_running()) or \
                  self.is_depurating # Considerar depuración como 'busy'

        user_wants_to_exit = True
        if is_busy:
             if self.is_depurating:
                 # Pregunta diferente si está depurando (podría perder cambios no guardados implícitamente)
                 user_wants_to_exit = messagebox.askokcancel("Salir", "Estás en modo Depuración. Los cambios no exportados se perderán.\n¿Estás seguro de que quieres salir?")
             else:
                  # Pregunta si está cargando o transcribiendo
                 user_wants_to_exit = messagebox.askokcancel("Salir", "Hay un proceso activo (carga de modelo o transcripción).\n¿Estás seguro de que quieres salir?")

        if user_wants_to_exit:
             self.set_status("Cerrando, intentando detener procesos...")
             self._stop_all_processes(clear_audio=True)

             print("Esperando finalización de hilos...")
             # Esperar al hilo de carga si existe
             global _model_load_thread
             if _model_load_thread and _model_load_thread.is_alive():
                  _model_load_thread.join(timeout=2)
             # Esperar al hilo de transcripción si existe y estaba corriendo
             if self.whisper_transcriber:
                  # No necesitamos llamar a is_running() aquí, join ya lo comprueba
                  self.whisper_transcriber.join(timeout=5) # Darle tiempo si estaba transcribiendo

             # Detener el timer de highlight si aún estaba activo (por si acaso)
             self._stop_highlight_update_timer()

             self.ventana.destroy() # Cerrar la ventana
        else:
             return # No cerrar


    def cleanup_on_exit(self):
         """Limpieza final llamada desde main.py después de cerrar la ventana."""
         print("Ejecutando limpieza final...")
         # Detener playback y liberar pygame (ya debería estar hecho por _on_closing, pero por seguridad)
         playback.quit_playback()
         # Limpiar archivo temporal (ya debería estar hecho, pero por seguridad)
         audio_handler.cleanup_temp_wav()
         # Los joins ya se hicieron en _on_closing si era necesario
         print("Limpieza final completada.")