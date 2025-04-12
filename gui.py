# In gui.py
"""Clase principal de la Interfaz Gráfica de Usuario (GUI) para AudioTranscriptorPro."""

import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import tkinter.font as tkFont
import pathlib
import threading
import time # Necesario para formato de tiempo y timers
from pydub import AudioSegment, exceptions as pydub_exceptions # Para obtener duración

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
    """
    Clase principal que gestiona la interfaz gráfica y coordina el transcriptor Whisper
    para la aplicación AudioTranscriptorPro.
    """

    def __init__(self, root: tk.Tk):
        """
        Inicializa la ventana principal, los componentes de la interfaz,
        el estado de la aplicación y los transcriptores.

        Args:
            root (tk.Tk): La ventana raíz de Tkinter.
        """
        self.ventana = root
        self.ventana.title(f"Audio a Texto Pro ({config.__version__}) - Whisper")
        self.ventana.configure(bg=config.BG_COLOR)
        self.ventana.geometry("800x600")
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

        # --- Estado de la Aplicación ---
        self.ruta_audio_original: pathlib.Path | None = None
        self.ruta_audio_wav: pathlib.Path | None = None
        self.selected_whisper_model: str | None = None
        self.whisper_model_loaded = False
        self.is_loading_model = False
        self.whisper_transcription_complete = False
        self.transcription_result: dict | None = None # Almacena resultado Whisper con {text, segments, language}

        # --- Estado de Depuración ---
        self.is_depurating = False
        self.playback_update_timer_id = None
        self.current_highlighted_segment_index = -1
        self.is_paused = False # Flag para estado de pausa de Pygame
        self.audio_duration_sec: float | None = None # Duración del archivo cargado

        # --- Estado de Animación (para carga/transcripción) ---
        self.animacion_whisper_activa = False
        self.animacion_whisper_id = None
        self.dot_index = 0
        self.dots_refs = []

        # --- Instancia del Transcriptor Whisper ---
        self.whisper_transcriber = None
        if WHISPER_AVAILABLE:
            self.whisper_transcriber = WhisperTranscriber(
                update_callback=lambda result: self.ventana.after(0, self._update_texto_whisper, result),
                status_callback=lambda status: self.ventana.after(0, self.set_status, status),
                completion_callback=lambda success, result: self.ventana.after(0, self._on_whisper_transcription_complete, success, result),
                error_callback=lambda error: self.ventana.after(0, self._show_error, "Whisper Error", error)
            )
        else:
            print("INFO: WhisperTranscriber no se inicializará (librería no encontrada).")

        # --- Construcción de la Interfaz ---
        self._setup_fonts()
        self._create_widgets()
        self._update_ui_state() # Establecer estado inicial de los botones/widgets

        # --- Estado Inicial y Playback ---
        initial_status = "Bienvenido."
        if not WHISPER_AVAILABLE:
             initial_status += " Whisper no disponible. Instala 'openai-whisper'."
        else:
             initial_status += f" Dispositivo: {self.device_to_use}. Selecciona un modelo Whisper."
        self.set_status(initial_status)

        if not playback.init_playback():
             self._show_error("Error Crítico", "No se pudo inicializar Pygame para la reproducción. La función de depuración no estará disponible.")
             # Podríamos deshabilitar permanentemente el botón depurar aquí si fuera necesario.

    def _setup_fonts(self):
        """Configura las fuentes predeterminadas para la aplicación."""
        default_font = tkFont.nametofont("TkDefaultFont")
        default_font.configure(size=10)
        self.ventana.option_add("*Font", default_font)
        self.text_font = tkFont.Font(family="TkTextFont", size=11) # Fuente principal para transcripción
        self.title_font = tkFont.Font(family="TkHeadingFont", size=11, weight="bold") # Títulos de frames
        self.instruction_font = tkFont.Font(size=9, slant="italic") # Textos guía
        self.warning_font = tkFont.Font(size=9, weight="bold") # Advertencias (modelos grandes)

    def _format_time(self, seconds: float | None) -> str:
        """Formatea segundos a una cadena MM:SS, manejando None o valores inválidos."""
        if seconds is None or seconds < 0:
            return "--:--"
        try:
            return time.strftime('%M:%S', time.gmtime(seconds))
        except (ValueError, OSError): # gmtime puede fallar con valores muy grandes o negativos
             return "--:--"
        except Exception: # Captura general
             return "??:??"

    def _create_widgets(self):
        """Crea y organiza todos los widgets de la interfaz gráfica."""

        # --- Frame Superior: Controles Principales y Estado ---
        frame_superior = tk.Frame(self.ventana, bg=config.BG_COLOR)
        frame_superior.pack(pady=(10, 5), padx=20, fill=tk.X)

        # --- Columna Izquierda: Instrucciones y Selección ---
        frame_controles = tk.Frame(frame_superior, bg=config.BG_COLOR)
        frame_controles.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), anchor='nw')

        tk.Label(frame_controles, text="Pasos:", font=self.title_font, bg=config.BG_COLOR).pack(anchor='w')
        tk.Label(frame_controles, text="1. Selecciona modelo Whisper", font=self.instruction_font, bg=config.BG_COLOR).pack(anchor='w', padx=(5,0))
        tk.Label(frame_controles, text="2. Selecciona archivo de audio", font=self.instruction_font, bg=config.BG_COLOR).pack(anchor='w', padx=(5,0))
        tk.Label(frame_controles, text="3. Pulsa 'Transcribir'", font=self.instruction_font, bg=config.BG_COLOR).pack(anchor='w', padx=(5,0))
        tk.Label(frame_controles, text="4. Pulsa 'Depurar' (opcional)", font=self.instruction_font, bg=config.BG_COLOR).pack(anchor='w', padx=(5,0))

        tk.Label(frame_controles, text="Modelo Whisper:", font=tkFont.Font(weight='bold'), bg=config.BG_COLOR).pack(anchor='w', pady=(8, 2))
        self.model_var = tk.StringVar()
        self.model_combobox = ttk.Combobox(
            frame_controles, textvariable=self.model_var, width=15,
            values=config.WHISPER_MODELS if WHISPER_AVAILABLE else ["Whisper no disponible"],
            state="readonly" if WHISPER_AVAILABLE else "disabled"
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
        self.boton_depurar = tk.Button(frame_controles, text="Depurar", command=self._toggle_depuration_mode, padx=10, pady=5, state=tk.DISABLED)
        self.boton_depurar.pack(anchor='w', pady=(15, 5))

        # --- Columna Derecha: Estado, Progreso y Playback ---
        frame_estado_progreso = tk.Frame(frame_superior, bg=config.BG_COLOR)
        frame_estado_progreso.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.status_label = tk.Label(frame_estado_progreso, text="Inicializando...", bg=config.BG_COLOR, font=("TkDefaultFont", 10), anchor='nw', justify=tk.LEFT, wraplength=550)
        self.status_label.pack(fill=tk.X, pady=(5,2), anchor='nw')

        self.progress_var = tk.IntVar()
        self.progress_bar = ttk.Progressbar(
            frame_estado_progreso, orient="horizontal", length=300, mode="determinate", variable=self.progress_var
        ) # Se muestra/oculta dinámicamente

        # Frame Controles de Playback (Modo Depuración)
        self.frame_playback_controls = tk.Frame(frame_estado_progreso, bg=config.BG_COLOR)
        # Se muestra/oculta dinámicamente
        self.boton_play_pause = tk.Button(self.frame_playback_controls, text="▶ Play", command=self._toggle_play_pause, width=8, padx=5, pady=2)
        self.boton_play_pause.pack(side=tk.LEFT, padx=5, pady=5)
        self.boton_stop_playback = tk.Button(self.frame_playback_controls, text="■ Stop", command=self._stop_playback_action, width=8, padx=5, pady=2)
        self.boton_stop_playback.pack(side=tk.LEFT, padx=5, pady=5)
        self.playback_time_label = tk.Label(self.frame_playback_controls, text="--:-- / --:--", bg=config.BG_COLOR, font=self.instruction_font)
        self.playback_time_label.pack(side=tk.LEFT, padx=10, pady=5)

        # Frame Animación Puntos (Transcripción)
        self.whisper_dots_frame = tk.Frame(frame_estado_progreso, bg=config.BG_COLOR)
        # Se muestra/oculta dinámicamente
        tk.Label(self.whisper_dots_frame, text="Whisper procesando:", bg=config.BG_COLOR, font=self.instruction_font).pack(side=tk.LEFT, padx=(0,5))
        self.dots_canvas = tk.Canvas(self.whisper_dots_frame, width=40, height=12, bg=config.BG_COLOR, highlightthickness=0)
        self.dots_canvas.pack(side=tk.LEFT)
        self.dots_refs = [self.dots_canvas.create_oval(i * 12 + 2, 2, i * 12 + 10, 10, fill=config.STATUS_COLOR_GRAY, tags=f"dot{i}") for i in range(3)]

        # --- Frame Inferior: Área de Texto Transcripción Whisper ---
        frame_texto_whisper = tk.Frame(self.ventana, bg=config.BG_COLOR)
        frame_texto_whisper.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 5))

        frame_whisper = tk.LabelFrame(frame_texto_whisper, text="Transcripción Whisper", font=self.title_font, bg=config.BG_COLOR, padx=5, pady=5)
        frame_whisper.pack(fill=tk.BOTH, expand=True)

        self.area_texto_whisper = scrolledtext.ScrolledText(frame_whisper, wrap=tk.WORD, font=self.text_font, height=15, padx=10, pady=10, borderwidth=1, relief=tk.SOLID, state=tk.DISABLED)
        self.area_texto_whisper.pack(fill=tk.BOTH, expand=True)
        self.area_texto_whisper.tag_configure("highlight", background=config.HIGHLIGHT_COLOR)
        self.whisper_status_canvas_circle = tk.Canvas(frame_whisper, width=10, height=10, bg=config.BG_COLOR, highlightthickness=0)
        self.whisper_status_canvas_circle.place(relx=1.0, rely=0.0, x=-5, y=5, anchor=tk.NE)
        utils.draw_status_circle(self.whisper_status_canvas_circle, config.STATUS_COLOR_GRAY)

        # --- Frame Final: Botones de Acción (Copiar/Exportar) ---
        frame_botones_accion = tk.Frame(self.ventana, bg=config.BG_COLOR)
        frame_botones_accion.pack(pady=(0, 15), fill=tk.X, padx=20)
        center_frame_botones = tk.Frame(frame_botones_accion, bg=config.BG_COLOR)
        center_frame_botones.pack(anchor='center')
        self.boton_copiar_whisper = tk.Button(center_frame_botones, text="Copiar Texto", command=self._copiar_whisper_action, state=tk.DISABLED, padx=10, pady=5)
        self.boton_copiar_whisper.pack(side=tk.LEFT, padx=5)
        self.boton_exportar_whisper = tk.Button(center_frame_botones, text="Exportar Texto", command=self._exportar_whisper_action, state=tk.DISABLED, padx=10, pady=5)
        self.boton_exportar_whisper.pack(side=tk.LEFT, padx=5)


    # --- Métodos de Acción (Callbacks de Widgets) ---

    def _on_model_select(self, event=None):
        """Manejador para la selección de un nuevo modelo Whisper en el Combobox."""
        if not self.whisper_transcriber:
             self.set_status("Error: Whisper no está disponible.")
             return
        selected = self.model_var.get()
        if not selected or (selected == self.selected_whisper_model and self.whisper_model_loaded):
             return

        print(f"Acción: Selección de modelo Whisper -> {selected}")
        if self.is_depurating: self._toggle_depuration_mode(force_exit=True)

        self.selected_whisper_model = selected
        self.whisper_model_loaded = False
        self.is_loading_model = True
        self._update_model_warning(selected)
        self._reset_transcription_state()
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
        """Actualiza la etiqueta de advertencia según el modelo seleccionado (CPU vs GPU)."""
        warning_text = ""
        if self.device_to_use == 'cpu':
            if model_name == "medium": warning_text = config.MODEL_MEDIUM_WARNING
            elif model_name == "large": warning_text = config.MODEL_LARGE_WARNING
        try:
            if self.model_warning_label.winfo_exists():
                self.model_warning_label.config(text=warning_text)
        except tk.TclError: pass

    def _seleccionar_audio_action(self):
        """Manejador para el botón 'Seleccionar Audio'."""
        if not self.whisper_model_loaded:
             self._show_error("Error", "Debes seleccionar y cargar un modelo Whisper primero.")
             return
        if self.is_depurating: self._toggle_depuration_mode(force_exit=True)

        print("Acción: Seleccionar audio iniciada.")
        selected_path = audio_handler.select_audio_file()
        if not selected_path:
            status_msg = "Selección cancelada."
            if self.selected_whisper_model: status_msg += f" Modelo cargado: {self.selected_whisper_model}"
            self.set_status(status_msg)
            return

        self.ruta_audio_original = selected_path
        self.ruta_audio_wav = None
        self.audio_duration_sec = None
        self.set_status(f"Archivo: {self.ruta_audio_original.name}. Convirtiendo a WAV...")
        self._reset_transcription_state()
        self._update_ui_state()

        threading.Thread(target=self._convert_and_prepare_audio, args=(selected_path,), daemon=True).start()

    def _convert_and_prepare_audio(self, audio_path: pathlib.Path):
        """
        Hilo trabajador: Intenta convertir audio a WAV y obtener su duración.
        Luego llama a _update_gui_after_conversion para actualizar la UI.
        """
        wav_path = audio_handler.convert_to_wav_if_needed(audio_path)
        duration_sec = None
        if wav_path:
            try:
                audio = AudioSegment.from_wav(str(wav_path))
                duration_sec = len(audio) / 1000.0
            except pydub_exceptions.CouldntDecodeError:
                 print(f"Advertencia: Pydub no pudo decodificar {wav_path.name} para obtener duración.")
            except FileNotFoundError:
                 print("Error: No se encontró el archivo WAV temporal para obtener duración.")
            except Exception as e:
                print(f"Advertencia: No se pudo obtener la duración del archivo WAV ({wav_path.name}): {e}")
        self.ventana.after(0, self._update_gui_after_conversion, wav_path, duration_sec)

    def _update_gui_after_conversion(self, wav_path: pathlib.Path | None, duration_sec: float | None):
        """Actualiza la interfaz gráfica después de intentar la conversión de audio."""
        if wav_path:
            self.ruta_audio_wav = wav_path
            self.audio_duration_sec = duration_sec
            if self.whisper_transcriber: self.whisper_transcriber.set_audio_file(self.ruta_audio_wav)
            self.ventana.title(f"Audio a Texto Pro - {self.ruta_audio_original.name} ({config.__version__})")
            duration_str = self._format_time(self.audio_duration_sec)
            status_msg = f"Audio listo ({self.ruta_audio_wav.name} [{duration_str}])."
            if self.selected_whisper_model: status_msg += f" Modelo: {self.selected_whisper_model}."
            status_msg += " Pulsa 'Transcribir'."
            self.set_status(status_msg)
            print(f"Audio preparado. WAV path: {self.ruta_audio_wav}, Duración: {duration_str}")
            try:
                if self.playback_time_label.winfo_exists():
                    self.playback_time_label.config(text=f"--:-- / {duration_str}")
            except tk.TclError: pass
        else:
            self.ruta_audio_original = None
            self.ruta_audio_wav = None
            self.audio_duration_sec = None
            self.set_status("Error en conversión. Selecciona otro archivo.")
            self.ventana.title(f"Audio a Texto Pro ({config.__version__}) - Whisper")
            try:
                 if self.playback_time_label.winfo_exists(): self.playback_time_label.config(text="--:-- / --:--")
            except tk.TclError: pass
        self._update_ui_state()

    def _transcribir_action(self):
        """Manejador para el botón 'Transcribir'."""
        if not self.ruta_audio_wav:
            self._show_error("Error", "No hay un archivo de audio preparado (WAV).")
            return
        if not self.whisper_model_loaded:
             self._show_error("Error", "No hay un modelo Whisper cargado.")
             return
        if self.whisper_transcriber and self.whisper_transcriber.is_running():
            self._show_error("Información", "Ya hay una transcripción en curso.")
            return
        if self.is_depurating:
             self._show_error("Información", "Sal del modo 'Depurar' antes de transcribir de nuevo.")
             return

        print("Acción: Iniciar transcripción Whisper.")
        self._reset_transcription_state()
        self.set_status(f"Iniciando transcripción con Whisper '{self.selected_whisper_model}'...")
        self._update_ui_state()
        utils.draw_status_circle(self.whisper_status_canvas_circle, config.STATUS_COLOR_YELLOW)
        self._start_whisper_animation()
        if self.whisper_transcriber: self.whisper_transcriber.start()

    def _copiar_whisper_action(self):
        """Manejador para el botón 'Copiar Texto'."""
        try:
            if self.area_texto_whisper and self.area_texto_whisper.winfo_exists():
                texto = self.area_texto_whisper.get("1.0", tk.END).strip()
                utils.copy_to_clipboard(self.ventana, texto)
            else: print("Error al copiar: El área de texto no está disponible.")
        except tk.TclError: print("Error TclError al intentar copiar texto.")

    def _exportar_whisper_action(self):
        """Manejador para el botón 'Exportar Texto'."""
        try:
            if self.area_texto_whisper and self.area_texto_whisper.winfo_exists():
                texto = self.area_texto_whisper.get("1.0", tk.END).strip()
                default_filename = "Transcripcion_Whisper"
                if self.selected_whisper_model: default_filename += f"_{self.selected_whisper_model}"
                if self.ruta_audio_original: default_filename += f"_{self.ruta_audio_original.stem}"
                else: default_filename += "_audio"
                utils.export_text_to_file(texto, default_filename)
            else: print("Error al exportar: El área de texto no está disponible.")
        except tk.TclError: print("Error TclError al intentar exportar texto.")

    # --- Métodos Callback ---

    def _update_model_load_progress(self, message: str, percentage: int):
        """Actualiza la barra de progreso y el estado durante la carga del modelo."""
        if not self.is_loading_model: return
        self.set_status(message)
        self.progress_var.set(percentage)

    def _on_model_load_complete(self, success: bool, model_name: str):
        """Callback ejecutado cuando la carga del modelo Whisper finaliza."""
        print(f"Callback: Carga del modelo '{model_name}' completada (Éxito: {success})")
        self.is_loading_model = False
        if self.progress_bar.winfo_exists(): self.progress_bar.pack_forget()
        if success:
            self.whisper_model_loaded = True
            self.selected_whisper_model = model_name
            self.model_var.set(model_name)
            self.set_status(f"Modelo '{model_name}' cargado ({self.device_to_use}). Selecciona audio o transcribe.")
        else:
            self.whisper_model_loaded = False
            self.selected_whisper_model = None
            self.set_status(f"Error al cargar modelo '{model_name}'. Intenta de nuevo o elige otro.")
        self._update_ui_state()

    def _update_texto_whisper(self, result_data: dict):
        """Callback para actualizar el área de texto con el resultado de Whisper."""
        if not self.area_texto_whisper or not self.area_texto_whisper.winfo_exists(): return

        self.transcription_result = result_data
        texto_completo = result_data.get("text", "Error: No se encontró texto en el resultado.")
        try:
            self.area_texto_whisper.config(state=tk.NORMAL)
            self.area_texto_whisper.delete("1.0", tk.END)
            self.area_texto_whisper.insert("1.0", texto_completo)
            self.area_texto_whisper.see("1.0")
            if not self.is_depurating: self.area_texto_whisper.config(state=tk.DISABLED)
        except tk.TclError: print("Error TclError al actualizar área de texto.")
        self._update_ui_state()

    def _on_whisper_transcription_complete(self, success: bool, result: dict | None):
        """Callback ejecutado cuando la transcripción de Whisper finaliza."""
        print(f"Callback: Transcripción Whisper completada (Éxito: {success})")
        self.whisper_transcription_complete = True
        self._stop_whisper_animation()
        utils.draw_status_circle(self.whisper_status_canvas_circle, config.STATUS_COLOR_GREEN if success else config.STATUS_COLOR_RED)
        self.transcription_result = result # Guardar incluso si falla

        # Comprobar si se puede entrar en modo depuración ahora
        can_depurate_now = success and result and isinstance(result.get("segments"), list) and len(result["segments"]) > 0 and self.ruta_audio_wav and playback._mixer_initialized
        if can_depurate_now:
            self.set_status("Transcripción completada. Puedes 'Depurar' o exportar.")
            # _update_ui_state habilitará el botón
        elif success:
            self.set_status("Transcripción completada (sin info de segmentos para depurar).")
        else:
            self.set_status("Error durante la transcripción Whisper.")
        self._update_ui_state() # Actualizar estado de botones (incluyendo Depurar)

    def _show_error(self, title: str, message: str):
        """Muestra un mensaje de error en un messagebox y en la consola."""
        print(f"ERROR: {title} - {message}")
        messagebox.showerror(title, message)
        if self.is_loading_model:
            self.is_loading_model = False
            if self.progress_bar.winfo_exists(): self.progress_bar.pack_forget()
            self._update_ui_state()
        try:
             if self.status_label.winfo_exists():
                 current_status = self.status_label.cget("text")
                 if "Error" not in current_status and "Falló" not in current_status:
                      self.set_status(f"Error: {title}. Revisa la consola.")
        except tk.TclError: pass

    # --- Métodos de Gestión de Estado Interno y UI ---

    def set_status(self, message: str):
        """Actualiza la etiqueta de estado general de la aplicación."""
        try:
            if self.status_label and self.status_label.winfo_exists():
                self.status_label.config(text=message)
        except tk.TclError: pass

    def _clear_text_area(self):
        """Limpia el contenido del área de texto de Whisper."""
        try:
            if self.area_texto_whisper and self.area_texto_whisper.winfo_exists():
                self.area_texto_whisper.config(state=tk.NORMAL)
                self.area_texto_whisper.delete("1.0", tk.END)
                self.area_texto_whisper.config(state=tk.DISABLED)
        except tk.TclError: pass

    def _reset_transcription_state(self):
        """Resetea el estado relacionado con una transcripción específica."""
        self.whisper_transcription_complete = False
        self.transcription_result = None
        self._clear_text_area()
        utils.draw_status_circle(self.whisper_status_canvas_circle, config.STATUS_COLOR_GRAY)
        if self.is_depurating: self._toggle_depuration_mode(force_exit=True)
        # No configurar botón depurar aquí, _update_ui_state lo hará al final

    def _update_ui_state(self):
        """Actualiza el estado habilitado/deshabilitado de los widgets."""
        try:
            is_transcribing = self.whisper_transcriber is not None and self.whisper_transcriber.is_running()
            is_busy_process = self.is_loading_model or is_transcribing

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
            # Verificación más explícita de segments como lista no vacía
            has_valid_segments = self.transcription_result and isinstance(self.transcription_result.get("segments"), list) and len(self.transcription_result["segments"]) > 0
            can_enter_depurate = (
                self.whisper_transcription_complete and
                has_valid_segments and
                self.ruta_audio_wav and
                playback._mixer_initialized and
                not is_busy_process
            )
            if self.is_depurating:
                self.boton_depurar.config(text="Salir Depurar", state=tk.NORMAL)
            else:
                self.boton_depurar.config(text="Depurar", state=tk.NORMAL if can_enter_depurate else tk.DISABLED)

            # Área de texto Whisper
            text_area_state = tk.NORMAL if self.is_depurating else tk.DISABLED
            if self.area_texto_whisper: self.area_texto_whisper.config(state=text_area_state)

            # Controles de Playback
            if self.frame_playback_controls.winfo_exists():
                should_be_visible = self.is_depurating
                is_visible = self.frame_playback_controls.winfo_viewable()
                if should_be_visible and not is_visible:
                    self.frame_playback_controls.pack(pady=5, anchor='w', after=self.status_label) # Usar referencia estable
                elif not should_be_visible and is_visible:
                    self.frame_playback_controls.pack_forget()

            # Botones Copiar/Exportar
            whisper_results_text = ""
            if self.area_texto_whisper and self.area_texto_whisper.winfo_exists():
                 whisper_results_text = self.area_texto_whisper.get("1.0", tk.END).strip()
            can_copy_export = whisper_results_text and not whisper_results_text.lower().startswith("error") and not is_busy_process and not self.is_depurating
            results_state = tk.NORMAL if can_copy_export else tk.DISABLED
            if self.boton_copiar_whisper: self.boton_copiar_whisper.config(state=results_state)
            if self.boton_exportar_whisper: self.boton_exportar_whisper.config(state=results_state)

        except tk.TclError: pass
        except Exception as e: print(f"Error inesperado en _update_ui_state: {e}")

    # --- Animación de Puntos ---

    def _animate_whisper_status(self):
        """Ciclo que actualiza los puntos animados durante la transcripción."""
        try:
            if not self.animacion_whisper_activa or not self.ventana.winfo_exists():
                if hasattr(self, 'whisper_dots_frame') and self.whisper_dots_frame.winfo_exists(): self.whisper_dots_frame.pack_forget()
                self.animacion_whisper_activa = False
                if self.animacion_whisper_id: self.ventana.after_cancel(self.animacion_whisper_id); self.animacion_whisper_id = None
                return

            if self.whisper_dots_frame.winfo_exists():
                if not self.whisper_dots_frame.winfo_viewable():
                    # Mostrar después de status label
                    self.whisper_dots_frame.pack(pady=2, anchor='w', after=self.status_label)
            else: self.animacion_whisper_activa = False; return

            colors = [config.STATUS_COLOR_GRAY] * 3
            colors[self.dot_index % 3] = config.STATUS_COLOR_YELLOW
            if self.dots_canvas.winfo_exists():
                for i, color in enumerate(colors):
                    if i < len(self.dots_refs): self.dots_canvas.itemconfig(self.dots_refs[i], fill=color)
                self.dot_index += 1
                if self.animacion_whisper_activa:
                    if self.animacion_whisper_id: self.ventana.after_cancel(self.animacion_whisper_id)
                    self.animacion_whisper_id = self.ventana.after(300, self._animate_whisper_status)
            else: self.animacion_whisper_activa = False; self._stop_whisper_animation() # Llama a limpiar
        except tk.TclError as e:
             print(f"Error TclError en animación: {e}"); self._stop_whisper_animation()
        except Exception as e:
             print(f"Error inesperado en animación: {e}"); self._stop_whisper_animation()

    def _start_whisper_animation(self):
        """Inicia la animación de puntos."""
        if not self.animacion_whisper_activa:
            self.animacion_whisper_activa = True
            self.dot_index = 0
            self._animate_whisper_status()

    def _stop_whisper_animation(self):
        """Detiene la animación de puntos y la oculta."""
        was_active = self.animacion_whisper_activa
        self.animacion_whisper_activa = False
        if self.animacion_whisper_id:
            try: self.ventana.after_cancel(self.animacion_whisper_id)
            except tk.TclError: pass
            self.animacion_whisper_id = None
        if was_active:
            try:
                 if self.dots_canvas.winfo_exists():
                    for i in range(len(self.dots_refs)): self.dots_canvas.itemconfig(self.dots_refs[i], fill=config.STATUS_COLOR_GRAY)
                 if self.whisper_dots_frame.winfo_exists(): self.whisper_dots_frame.pack_forget()
            except tk.TclError: pass
        self.dot_index = 0

    # --- Lógica de Depuración y Playback ---

    def _toggle_depuration_mode(self, force_exit=False):
        """Entra o sale del modo de depuración."""
        if force_exit and not self.is_depurating: return

        if not self.is_depurating and not force_exit:
            # --- Entrar ---
            if not self.ruta_audio_wav or not self.transcription_result or not isinstance(self.transcription_result.get("segments"), list) or not self.transcription_result["segments"]:
                self._show_error("Error Depuración", "No hay audio o resultado con segmentos válido para depurar.")
                return
            if not playback._mixer_initialized:
                 self._show_error("Error Playback", "Módulo de reproducción no inicializado.")
                 return

            print("Entrando en modo depuración...")
            self.is_depurating = True
            self.set_status("Modo Depuración: Edita el texto y usa los controles de audio.")
            playback.unload_audio() # Descargar anterior por si acaso
            if not playback.load_audio_from_path(self.ruta_audio_wav):
                 self._show_error("Error Playback", f"No se pudo cargar {self.ruta_audio_wav.name}.")
                 self.is_depurating = False; self._update_ui_state(); return

            self._update_ui_state() # Actualiza UI (botones, area texto editable, controles visibles)
            self.boton_play_pause.config(text="▶ Play")
            total_duration_str = self._format_time(self.audio_duration_sec)
            try:
                 if self.playback_time_label.winfo_exists(): self.playback_time_label.config(text=f"00:00 / {total_duration_str}")
            except tk.TclError: pass
        else:
            # --- Salir ---
            print("Saliendo de modo depuración...")
            self.is_depurating = False
            self._stop_playback_action()
            playback.unload_audio()
            self._remove_highlight()
            self._update_ui_state() # Actualiza UI (botones, area texto no editable, controles ocultos)
            status_msg = "Modo Depuración finalizado."
            if self.selected_whisper_model: status_msg += f" Modelo: {self.selected_whisper_model}."
            if self.ruta_audio_original: status_msg += f" Archivo: {self.ruta_audio_original.name}."
            self.set_status(status_msg)

    def _toggle_play_pause(self):
        """Manejador para el botón Play/Pause en modo depuración."""
        if not self.is_depurating: return
        wants_to_play = self.boton_play_pause.cget("text") == "▶ Play"
        if wants_to_play:
            if self.is_paused: # Reanudar
                playback.unpause_audio()
                self.is_paused = False
                if playback.is_playing(): self.boton_play_pause.config(text="❚❚ Pause"); self._start_highlight_update_timer()
                else: self.boton_play_pause.config(text="▶ Play"); self._stop_highlight_update_timer() # Falló reanudar?
            else: # Empezar de 0
                if playback.play_audio(start_seconds=0.0):
                    self.is_paused = False; self.boton_play_pause.config(text="❚❚ Pause"); self._start_highlight_update_timer()
                else: self._show_error("Playback Error", "No se pudo iniciar la reproducción.")
        else: # Pausar
            if playback.is_playing():
                playback.pause_audio(); self.is_paused = True
                self.boton_play_pause.config(text="▶ Play"); self._stop_highlight_update_timer()
            else: # Ya estaba detenido? Resetear botón
                 self.is_paused = False; self.boton_play_pause.config(text="▶ Play"); self._stop_highlight_update_timer()

    def _stop_playback_action(self):
        """Manejador para el botón Stop en modo depuración."""
        if not self.is_depurating: return
        print("Deteniendo playback...")
        playback.stop_audio()
        self._stop_highlight_update_timer()
        self._remove_highlight()
        self.is_paused = False
        if self.boton_play_pause.winfo_exists(): self.boton_play_pause.config(text="▶ Play")
        total_duration_str = self._format_time(self.audio_duration_sec)
        try:
             if self.playback_time_label.winfo_exists(): self.playback_time_label.config(text=f"00:00 / {total_duration_str}")
        except tk.TclError: pass

    def _start_highlight_update_timer(self):
        """Inicia el temporizador periódico para actualizar highlight y tiempo."""
        if self.playback_update_timer_id:
            try: self.ventana.after_cancel(self.playback_update_timer_id)
            except tk.TclError: pass
            self.playback_update_timer_id = None
        self._update_playback_highlight() # Llamada inicial
        try: # Programar siguiente si aplica
             if self.ventana.winfo_exists() and self.is_depurating:
                 self.playback_update_timer_id = self.ventana.after(config.PLAYBACK_UPDATE_INTERVAL_MS, self._start_highlight_update_timer)
        except tk.TclError: self.playback_update_timer_id = None

    def _stop_highlight_update_timer(self):
        """Detiene el temporizador de actualización."""
        if self.playback_update_timer_id:
            try: self.ventana.after_cancel(self.playback_update_timer_id)
            except tk.TclError: pass
            self.playback_update_timer_id = None

    def _remove_highlight(self):
        """Quita el resaltado del texto."""
        try:
             if self.area_texto_whisper and self.area_texto_whisper.winfo_exists():
                 self.area_texto_whisper.tag_remove("highlight", "1.0", tk.END)
                 self.current_highlighted_segment_index = -1
        except tk.TclError: pass

    def _update_playback_highlight(self):
        """Actualiza etiqueta de tiempo y resalta segmento actual."""
        if not self.is_depurating:
            if self.playback_update_timer_id: self._stop_highlight_update_timer()
            return

        current_time_ms = playback.get_current_pos_ms()
        current_time_sec = current_time_ms / 1000.0 if current_time_ms != -1 else 0
        current_time_str = self._format_time(current_time_sec)
        total_duration_str = self._format_time(self.audio_duration_sec)
        try:
            if self.playback_time_label.winfo_exists(): self.playback_time_label.config(text=f"{current_time_str} / {total_duration_str}")
        except tk.TclError: pass

        if not self.is_paused:
            is_busy = playback.is_playing()
            if not is_busy and current_time_ms != -1: # Terminó o se detuvo
                ended_naturally = self.audio_duration_sec is not None and current_time_sec >= self.audio_duration_sec - 0.15
                print(f"Playback {'finalizado naturalmente' if ended_naturally else 'detenido'}.")
                self._stop_playback_action(); return

            # Actualizar highlight solo si no está pausado
            if current_time_ms == -1: return
            segments = self.transcription_result.get("segments", []) if self.transcription_result else []
            if not segments: return
            found_segment_index = -1
            for i, segment in enumerate(segments):
                start = segment.get('start'); end = segment.get('end')
                if isinstance(start, (int, float)) and isinstance(end, (int, float)) and start <= current_time_sec < end:
                    found_segment_index = i; break
            if found_segment_index != self.current_highlighted_segment_index:
                self._remove_highlight()
                if found_segment_index != -1:
                    self.current_highlighted_segment_index = found_segment_index
                    segment_text = segments[found_segment_index].get('text', '').strip()
                    if segment_text:
                        try:
                            if self.area_texto_whisper.winfo_exists():
                                start_index = self.area_texto_whisper.search(segment_text, "1.0", tk.END, exact=True)
                                if start_index:
                                    end_index = f"{start_index}+{len(segment_text)}c"
                                    self.area_texto_whisper.tag_add("highlight", start_index, end_index)
                                    self.area_texto_whisper.see(start_index)
                                else: self.current_highlighted_segment_index = -1 # Resetear si no se encuentra texto
                        except tk.TclError: pass
                        except Exception as e: print(f"Error al resaltar: {e}"); self.current_highlighted_segment_index = -1
                    else: self.current_highlighted_segment_index = -1 # Segmento sin texto
                else: self.current_highlighted_segment_index = -1 # Ningún segmento en este tiempo

    # --- Gestión de Cierre y Limpieza ---
    _stop_event_global = threading.Event()

    def _stop_all_processes(self, clear_audio=True):
         """Intenta detener hilos, playback y limpiar recursos."""
         print("Intentando detener todos los procesos...")
         self._stop_event_global.set()
         if self.is_depurating:
             self._stop_playback_action(); playback.unload_audio(); self._remove_highlight()
             self.is_depurating = False
         else: playback.stop_audio()
         self._stop_whisper_animation(); self._stop_highlight_update_timer()
         global _model_load_thread, _model_load_stop_event
         if _model_load_thread and _model_load_thread.is_alive():
             print("INFO: Intentando cancelar carga de modelo..."); _model_load_stop_event.set()
         if clear_audio:
             self.ruta_audio_original = None; self.ruta_audio_wav = None
             audio_handler.cleanup_temp_wav()

    def _on_closing(self):
        """Manejador para el evento de cierre de la ventana principal."""
        print("Cerrando aplicación...")
        is_busy = self.is_loading_model or (self.whisper_transcriber and self.whisper_transcriber.is_running()) or self.is_depurating
        user_wants_to_exit = True
        if is_busy:
             prompt_message = "¿Estás seguro de que quieres salir?"
             if self.is_depurating: prompt_message = "Estás en modo Depuración. Cambios no exportados se perderán.\n" + prompt_message
             elif self.is_loading_model: prompt_message = "Se está cargando un modelo.\n" + prompt_message
             elif self.whisper_transcriber and self.whisper_transcriber.is_running(): prompt_message = "Hay una transcripción en curso (no se puede detener).\n" + prompt_message
             user_wants_to_exit = messagebox.askokcancel("Salir", prompt_message)

        if user_wants_to_exit:
             self.set_status("Cerrando, intentando detener procesos...")
             self._stop_all_processes(clear_audio=True)
             print("Esperando finalización de hilos...")
             global _model_load_thread
             if _model_load_thread and _model_load_thread.is_alive(): _model_load_thread.join(timeout=2.0)
             if self.whisper_transcriber: self.whisper_transcriber.join(timeout=5.0)
             self.ventana.destroy()
        else: print("Cierre cancelado por el usuario.")

    def cleanup_on_exit(self):
         """Limpieza final llamada desde main.py después de cerrar la ventana."""
         print("Ejecutando limpieza final...")
         playback.quit_playback()
         audio_handler.cleanup_temp_wav()
         print("Limpieza final completada.")