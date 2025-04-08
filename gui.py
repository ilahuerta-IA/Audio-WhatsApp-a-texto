# In gui.py
"""Clase principal de la Interfaz Gráfica de Usuario (GUI) para AudioTranscriptorPro."""

import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk # Añadir ttk para Combobox y Progressbar
import tkinter.font as tkFont
import pathlib
import threading

# Importar módulos locales
import config
import utils
from utils import check_nvidia_smi, check_pytorch_cuda
import audio_handler
import playback
from google_transcriber import GoogleTranscriber
from whisper_transcriber import WhisperTranscriber, WHISPER_AVAILABLE # Importar check
from whisper_transcriber import _model_load_thread, _model_load_stop_event, WHISPER_AVAILABLE

class AudioTranscriptorPro:
    """Clase que gestiona la interfaz gráfica y coordina los transcriptores."""

    def __init__(self, root: tk.Tk):
        self.ventana = root
        self.ventana.title(f"Audio a Texto Pro ({config.__version__}) - Google vs Whisper")
        self.ventana.configure(bg=config.BG_COLOR)
        # Geometría inicial un poco más grande para acomodar nuevos controles
        self.ventana.geometry("850x650")
        self.ventana.protocol("WM_DELETE_WINDOW", self._on_closing) # Manejar cierre

        # --- Realizar comprobación temprana del entorno ---
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
        self.ruta_audio_wav: pathlib.Path | None = None
        self.selected_whisper_model: str | None = None # Modelo seleccionado por el usuario
        self.whisper_model_loaded = False # Flag para saber si un modelo está cargado
        self.is_loading_model = False # Flag para saber si estamos en proceso de carga

        self.google_transcription_complete = False
        self.whisper_transcription_complete = False

        # --- Animación Whisper (para transcripción, no carga) ---
        self.animacion_whisper_activa = False
        self.animacion_whisper_id = None
        self.dot_index = 0
        self.dots_refs = []

        # --- Instancias de transcriptores ---
        self.google_transcriber = GoogleTranscriber(
            update_callback=lambda text: self.ventana.after(0, self._update_texto_google, text),
            status_callback=lambda status: self.ventana.after(0, self.set_status, status),
            completion_callback=lambda success: self.ventana.after(0, self._on_google_complete, success),
            error_callback=lambda error: self.ventana.after(0, self._show_error, "Google Error", error)
        )
        # Solo instanciar Whisper si está disponible
        self.whisper_transcriber = None
        if WHISPER_AVAILABLE:
            self.whisper_transcriber = WhisperTranscriber(
                update_callback=lambda text: self.ventana.after(0, self._update_texto_whisper, text),
                status_callback=lambda status: self.ventana.after(0, self.set_status, status), # Status general
                completion_callback=lambda success: self.ventana.after(0, self._on_whisper_transcription_complete, success), # Callback para FIN de transcripción
                error_callback=lambda error: self.ventana.after(0, self._show_error, "Whisper Error", error)
            )
        else:
            print("INFO: WhisperTranscriber no se inicializará.")


        # --- Construir la interfaz ---
        self._setup_fonts()
        self._create_widgets()
        self._update_ui_state() # Estado inicial basado en flags

        # Mostrar mensaje inicial
        initial_status = "Bienvenido."
        if not WHISPER_AVAILABLE:
             initial_status += " Whisper no detectado. Por favor, instala 'openai-whisper'."
        else:
             initial_status += " Por favor, selecciona un modelo Whisper para empezar."
        self.set_status(initial_status)

    def _setup_fonts(self):
        """Configura las fuentes predeterminadas."""
        default_font = tkFont.nametofont("TkDefaultFont")
        default_font.configure(size=10) # Ligeramente más pequeño por defecto
        self.ventana.option_add("*Font", default_font)
        self.text_font = tkFont.Font(family="TkTextFont", size=11) # Fuente para texto
        self.title_font = tkFont.Font(family="TkHeadingFont", size=11, weight="bold")
        self.instruction_font = tkFont.Font(size=9, slant="italic")
        self.warning_font = tkFont.Font(size=9, weight="bold")

    def _create_widgets(self):
        """Crea todos los elementos de la interfaz gráfica."""

        # --- Frame Superior: Controles Principales y Estado ---
        frame_superior = tk.Frame(self.ventana, bg=config.BG_COLOR)
        frame_superior.pack(pady=(10, 5), padx=20, fill=tk.X)

        # --- Columna Izquierda: Instrucciones y Selección ---
        frame_controles = tk.Frame(frame_superior, bg=config.BG_COLOR)
        frame_controles.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # Instrucciones
        tk.Label(frame_controles, text="Pasos a seguir:", font=self.title_font, bg=config.BG_COLOR).pack(anchor='w')
        tk.Label(frame_controles, text="1. Selecciona modelo Whisper", font=self.instruction_font, bg=config.BG_COLOR).pack(anchor='w', padx=(5,0))
        tk.Label(frame_controles, text="2. Selecciona archivo de audio", font=self.instruction_font, bg=config.BG_COLOR).pack(anchor='w', padx=(5,0))
        tk.Label(frame_controles, text="3. Pulsa 'Transcribir'", font=self.instruction_font, bg=config.BG_COLOR).pack(anchor='w', padx=(5,0))

        # Selección de Modelo Whisper
        tk.Label(frame_controles, text="Modelo Whisper:", font=tkFont.Font(weight='bold'), bg=config.BG_COLOR).pack(anchor='w', pady=(8, 2))
        self.model_var = tk.StringVar()
        self.model_combobox = ttk.Combobox(
            frame_controles,
            textvariable=self.model_var,
            values=config.WHISPER_MODELS if WHISPER_AVAILABLE else ["Whisper no disponible"],
            state="readonly" if WHISPER_AVAILABLE else "disabled", # 'readonly' previene escritura manual
            width=15 # Ancho ajustado
        )
        if WHISPER_AVAILABLE:
            self.model_combobox.set(config.DEFAULT_WHISPER_MODEL) # Establecer valor inicial
            self.model_combobox.bind("<<ComboboxSelected>>", self._on_model_select)
        self.model_combobox.pack(anchor='w', pady=(0, 5))

        # Advertencia modelos pesados
        self.model_warning_label = tk.Label(frame_controles, text="", font=self.warning_font, fg="orange", bg=config.BG_COLOR, wraplength=180, justify=tk.LEFT)
        self.model_warning_label.pack(anchor='w', pady=(0,5))
        self._update_model_warning(config.DEFAULT_WHISPER_MODEL) # Mostrar advertencia inicial si aplica

        # Botones de Selección y Transcripción
        self.boton_seleccionar = tk.Button(frame_controles, text="Seleccionar Audio", command=self._seleccionar_audio_action, padx=10, pady=5)
        self.boton_seleccionar.pack(anchor='w', pady=(10, 5))

        self.boton_transcribir = tk.Button(frame_controles, text="Transcribir", command=self._transcribir_action, padx=10, pady=5)
        self.boton_transcribir.pack(anchor='w', pady=(5, 5))

        self.boton_terminar = tk.Button(frame_controles, text="Terminar Google", command=self._terminar_google_action, padx=10, pady=5)
        self.boton_terminar.pack(anchor='w', pady=(5, 5))

        # --- Columna Derecha: Estado y Progreso ---
        frame_estado_progreso = tk.Frame(frame_superior, bg=config.BG_COLOR)
        frame_estado_progreso.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Etiqueta de Estado General
        self.status_label = tk.Label(frame_estado_progreso, text="Inicializando...", bg=config.BG_COLOR, font=("TkDefaultFont", 10), anchor='w', justify=tk.LEFT, wraplength=550)
        self.status_label.pack(fill=tk.X, pady=(5,2))

        # Barra de Progreso (para carga de modelo)
        self.progress_var = tk.IntVar()
        self.progress_bar = ttk.Progressbar(
            frame_estado_progreso,
            orient="horizontal",
            length=300, # Ancho de la barra
            mode="determinate", # Cambiar a 'indeterminate' si no hay progreso real
            variable=self.progress_var
        )
        self.progress_bar.pack(fill=tk.X, pady=(2,5))
        self.progress_bar.pack_forget() # Ocultar inicialmente

        # Animación Whisper (Puntos para transcripción)
        self.whisper_dots_frame = tk.Frame(frame_estado_progreso, bg=config.BG_COLOR)
        self.whisper_dots_frame.pack(pady=2, anchor='w') # Anclar a la izquierda
        tk.Label(self.whisper_dots_frame, text="Whisper procesando:", bg=config.BG_COLOR, font=self.instruction_font).pack(side=tk.LEFT, padx=(0,5))
        self.dots_canvas = tk.Canvas(self.whisper_dots_frame, width=40, height=12, bg=config.BG_COLOR, highlightthickness=0)
        self.dots_canvas.pack(side=tk.LEFT)
        self.dots_refs = [self.dots_canvas.create_oval(i * 12 + 2, 2, i * 12 + 10, 10, fill=config.STATUS_COLOR_GRAY, tags=f"dot{i}") for i in range(3)]
        self.whisper_dots_frame.pack_forget() # Ocultar inicialmente

        # --- Frame Inferior: Áreas de Texto ---
        frame_textos = tk.Frame(self.ventana, bg=config.BG_COLOR)
        frame_textos.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 5))
        # Configurar el grid DENTRO de frame_textos para que las columnas se expandan por igual
        frame_textos.grid_columnconfigure(0, weight=1)  # Columna para Google
        frame_textos.grid_columnconfigure(1, weight=1)  # Columna para Whisper
        # Asegurar que la fila también se expanda verticalmente si es necesario
        frame_textos.grid_rowconfigure(0, weight=1)

        # Google
        frame_google = tk.LabelFrame(frame_textos, text="Transcripción Google Speech", font=self.title_font, bg=config.BG_COLOR, padx=5, pady=5)
        frame_google.grid(row=0, column=0, sticky='nsew', padx=(0, 5)) # 'nsew' hace que llene la celda
        self.area_texto_google = scrolledtext.ScrolledText(frame_google, wrap=tk.WORD, font=self.text_font, height=10, padx=10, pady=10, borderwidth=1, relief=tk.SOLID, state=tk.DISABLED)
        self.area_texto_google.pack(fill=tk.BOTH, expand=True)
        self.google_status_canvas = tk.Canvas(frame_google, width=10, height=10, bg=config.BG_COLOR, highlightthickness=0)
        self.google_status_canvas.place(relx=1.0, rely=0.0, x=-5, y=5, anchor=tk.NE)
        utils.draw_status_circle(self.google_status_canvas, config.STATUS_COLOR_GRAY)

        # Whisper
        frame_whisper = tk.LabelFrame(frame_textos, text="Transcripción Whisper", font=self.title_font, bg=config.BG_COLOR, padx=5, pady=5)
        frame_whisper.grid(row=0, column=1, sticky='nsew', padx=(5, 0)) # 'nsew' hace que llene la celda
        self.area_texto_whisper = scrolledtext.ScrolledText(frame_whisper, wrap=tk.WORD, font=self.text_font, height=10, padx=10, pady=10, borderwidth=1, relief=tk.SOLID, state=tk.DISABLED)
        self.area_texto_whisper.pack(fill=tk.BOTH, expand=True)
        self.whisper_status_canvas_circle = tk.Canvas(frame_whisper, width=10, height=10, bg=config.BG_COLOR, highlightthickness=0)
        self.whisper_status_canvas_circle.place(relx=1.0, rely=0.0, x=-5, y=5, anchor=tk.NE)
        utils.draw_status_circle(self.whisper_status_canvas_circle, config.STATUS_COLOR_GRAY)

        # --- Frame Final: Botones de Acción ---
        frame_botones_accion = tk.Frame(self.ventana, bg=config.BG_COLOR)
        frame_botones_accion.pack(pady=(0, 15), fill=tk.X, padx=20)
        # Google
        frame_botones_google = tk.Frame(frame_botones_accion, bg=config.BG_COLOR)
        frame_botones_google.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.boton_copiar_google = tk.Button(frame_botones_google, text="Copiar Google", command=self._copiar_google_action, state=tk.DISABLED, padx=10, pady=5)
        self.boton_copiar_google.pack(side=tk.LEFT, padx=(0,5))
        self.boton_exportar_google = tk.Button(frame_botones_google, text="Exportar Google", command=self._exportar_google_action, state=tk.DISABLED, padx=10, pady=5)
        self.boton_exportar_google.pack(side=tk.LEFT, padx=5)
        # Whisper
        frame_botones_whisper = tk.Frame(frame_botones_accion, bg=config.BG_COLOR)
        frame_botones_whisper.pack(side=tk.RIGHT, expand=True, fill=tk.X, anchor='e')
        self.boton_exportar_whisper = tk.Button(frame_botones_whisper, text="Exportar Whisper", command=self._exportar_whisper_action, state=tk.DISABLED, padx=10, pady=5)
        self.boton_exportar_whisper.pack(side=tk.RIGHT, padx=(5,0))
        self.boton_copiar_whisper = tk.Button(frame_botones_whisper, text="Copiar Whisper", command=self._copiar_whisper_action, state=tk.DISABLED, padx=10, pady=5)
        self.boton_copiar_whisper.pack(side=tk.RIGHT, padx=5)


    # --- Métodos de Acción (Triggers de Usuario) ---

    def _on_model_select(self, event=None):
        """Acción cuando se selecciona un modelo Whisper del Combobox."""
        if not self.whisper_transcriber:
             self.set_status("Error: Whisper no está disponible.")
             return

        selected = self.model_var.get()
        if not selected or selected == self.selected_whisper_model and self.whisper_model_loaded:
             print(f"Modelo '{selected}' ya seleccionado o carga no necesaria.")
             return # No hacer nada si no cambia o ya está cargado

        print(f"Acción: Selección de modelo Whisper -> {selected}")
        self.selected_whisper_model = selected
        self.whisper_model_loaded = False # Marcar como no cargado hasta que termine
        self.is_loading_model = True
        self._update_model_warning(selected)
        self._update_ui_state() # Deshabilitar controles durante la carga

        # Mostrar barra de progreso y mensaje inicial
        self.progress_var.set(0)
        self.progress_bar.pack(fill=tk.X, pady=(2,5)) # Mostrar barra
        self.set_status(f"Iniciando carga del modelo '{selected}'...")

        # Llamar a load_model en el transcriptor (en un hilo)
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
        # Esta acción ahora SÓLO debe ser posible si un modelo está cargado
        if not self.whisper_model_loaded:
             self._show_error("Error", "Debes seleccionar y cargar un modelo Whisper primero.")
             return

        print("Acción: Seleccionar audio iniciada.")
        self._stop_google_process_if_running() # Detener Google si corre

        selected_path = audio_handler.select_audio_file()
        if not selected_path:
            self.set_status("Selección cancelada. Modelo cargado: " + (self.selected_whisper_model or "Ninguno"))
            # Restaurar estado si había algo antes? Por ahora no.
            return

        self.ruta_audio_original = selected_path
        self.ruta_audio_wav = None # Resetear WAV path
        self.set_status(f"Archivo seleccionado: {self.ruta_audio_original.name}. Convirtiendo si es necesario...")
        # Resetear indicadores y áreas de texto
        utils.draw_status_circle(self.google_status_canvas, config.STATUS_COLOR_GRAY)
        utils.draw_status_circle(self.whisper_status_canvas_circle, config.STATUS_COLOR_GRAY)
        self._clear_text_areas()
        self.google_transcription_complete = False
        self.whisper_transcription_complete = False

        self._update_ui_state() # Deshabilitar 'Transcribir' mientras convierte

        # Convertir a WAV (necesario para Google y playback, bueno para Whisper)
        threading.Thread(target=self._convert_and_prepare_audio, args=(selected_path,), daemon=True).start()


    def _convert_and_prepare_audio(self, audio_path: pathlib.Path):
        """Convierte a WAV (si es necesario) y actualiza la GUI."""
        wav_path = audio_handler.convert_to_wav_if_needed(audio_path)

        def update_gui_after_conversion():
            if wav_path:
                self.ruta_audio_wav = wav_path
                self.google_transcriber.set_audio_file(self.ruta_audio_wav)
                if self.whisper_transcriber:
                     self.whisper_transcriber.set_audio_file(self.ruta_audio_wav)
                self.ventana.title(f"Audio a Texto Pro - {self.ruta_audio_original.name} ({config.__version__})")
                self.set_status(f"Audio listo. Modelo cargado: {self.selected_whisper_model}. Pulsa 'Transcribir'.")
                print(f"Audio preparado. WAV path: {self.ruta_audio_wav}")
            else:
                # Falló la conversión
                self.ruta_audio_original = None
                self.ruta_audio_wav = None
                self._show_error("Error de Conversión", f"No se pudo procesar el archivo {audio_path.name}.")
                self.set_status("Error en conversión. Selecciona otro archivo.")
                self.ventana.title(f"Audio a Texto Pro ({config.__version__}) - Google vs Whisper")

            self._update_ui_state() # Habilitar/Deshabilitar botones según estado

        self.ventana.after(0, update_gui_after_conversion)


    def _transcribir_action(self):
        """Acción del botón 'Transcribir'."""
        if not self.ruta_audio_wav:
            self._show_error("Error", "No hay un archivo de audio preparado.")
            return
        if not self.whisper_model_loaded:
             self._show_error("Error", "No hay un modelo Whisper cargado.")
             return
        if self.google_transcriber.is_running() or (self.whisper_transcriber and self.whisper_transcriber.is_running()):
            self._show_error("Información", "Ya hay una transcripción en curso.")
            return

        print("Acción: Iniciar transcripción.")
        self._reset_transcription_state_flags() # Resetear flags de completado
        self.set_status("Iniciando transcripción con Google...")
        self._update_ui_state() # Deshabilitar 'Transcribir', Habilitar 'Terminar Google'

        # Resetear indicadores visuales e iniciar animación Whisper
        utils.draw_status_circle(self.google_status_canvas, config.STATUS_COLOR_GREEN) # Google empieza
        utils.draw_status_circle(self.whisper_status_canvas_circle, config.STATUS_COLOR_RED) # Whisper pendiente
        self._start_whisper_animation() # Iniciar animación de puntos para transcripción

        # Iniciar Google Transcriber
        self.google_transcriber.start()


    def _terminar_google_action(self):
        """Acción del botón 'Terminar Google'."""
        print("Acción: Terminar transcripción Google.")
        self._stop_google_process_if_running()
        # El estado de los botones se actualiza en _on_google_complete


    def _stop_google_process_if_running(self):
        """Detiene el transcriptor de Google si está activo."""
        if self.google_transcriber.is_running():
            self.google_transcriber.stop() # Esto detendrá también el playback
            # El estado de botones y status se maneja en el callback _on_google_complete
            utils.draw_status_circle(self.google_status_canvas, config.STATUS_COLOR_GRAY) # Marcar como detenido


    def _copiar_google_action(self):
        """Acción del botón 'Copiar Google'."""
        texto = self.area_texto_google.get("1.0", tk.END).strip()
        utils.copy_to_clipboard(self.ventana, texto)

    def _exportar_google_action(self):
        """Acción del botón 'Exportar Google'."""
        texto = self.area_texto_google.get("1.0", tk.END).strip()
        utils.export_text_to_file(texto, f"Transcripción Google - {self.ruta_audio_original.stem if self.ruta_audio_original else 'audio'}")

    def _copiar_whisper_action(self):
        """Acción del botón 'Copiar Whisper'."""
        texto = self.area_texto_whisper.get("1.0", tk.END).strip()
        utils.copy_to_clipboard(self.ventana, texto)

    def _exportar_whisper_action(self):
        """Acción del botón 'Exportar Whisper'."""
        texto = self.area_texto_whisper.get("1.0", tk.END).strip()
        utils.export_text_to_file(texto, f"Transcripción Whisper ({self.selected_whisper_model}) - {self.ruta_audio_original.stem if self.ruta_audio_original else 'audio'}")


    # --- Métodos Callback (Llamados por los transcriptores y cargador) ---

    def _update_model_load_progress(self, message: str, percentage: int):
        """Actualiza la UI para mostrar el progreso de carga del modelo."""
        if not self.is_loading_model: return # Seguridad
        self.set_status(message)
        self.progress_var.set(percentage)

    def _on_model_load_complete(self, success: bool, model_name: str):
        """Callback cuando la carga del modelo Whisper termina."""
        print(f"Callback: Carga del modelo '{model_name}' completada (Éxito: {success})")
        self.is_loading_model = False
        self.progress_bar.pack_forget() # Ocultar barra de progreso

        if success:
            self.whisper_model_loaded = True
            # Asegurarse que el modelo seleccionado en la GUI coincide con el cargado
            self.selected_whisper_model = model_name
            self.model_var.set(model_name) # Actualizar combobox por si acaso
            self.set_status(f"Modelo '{model_name}' cargado. Selecciona un archivo de audio.")
        else:
            self.whisper_model_loaded = False
            self.selected_whisper_model = None # Resetear modelo seleccionado si falla
            # Mensaje de error ya mostrado por error_callback, aquí solo actualizamos estado general
            self.set_status(f"Error al cargar modelo '{model_name}'. Intenta con otro modelo o revisa la consola.")
            # No resetear combobox aquí, el usuario puede querer reintentar o elegir otro

        self._update_ui_state() # Reactivar controles según el resultado


    def _update_texto_google(self, texto_segmento: str):
        """Actualiza el área de texto de Google."""
        if not self.area_texto_google: return
        self.area_texto_google.config(state=tk.NORMAL)
        current_text = self.area_texto_google.get("1.0", tk.END).strip()
        texto_a_insertar = (" " + texto_segmento) if current_text else texto_segmento
        self.area_texto_google.insert(tk.END, texto_a_insertar)
        self.area_texto_google.see(tk.END)
        self.area_texto_google.config(state=tk.DISABLED)
        self._update_ui_state() # Habilitar botones de resultado si hay texto


    def _update_texto_whisper(self, texto_completo: str):
        """Actualiza el área de texto de Whisper."""
        if not self.area_texto_whisper: return
        self.area_texto_whisper.config(state=tk.NORMAL)
        self.area_texto_whisper.delete("1.0", tk.END)
        self.area_texto_whisper.insert("1.0", texto_completo)
        self.area_texto_whisper.see("1.0")
        self.area_texto_whisper.config(state=tk.DISABLED)
        self._update_ui_state() # Habilitar botones de resultado si hay texto

    def _on_google_complete(self, success: bool):
        """Callback cuando Google Transcriber termina."""
        print(f"Callback: Google completado (Éxito: {success})")
        self.google_transcription_complete = True
        utils.draw_status_circle(self.google_status_canvas, config.STATUS_COLOR_GREEN if success else config.STATUS_COLOR_GRAY)

        if self._stop_event_global.is_set():
             self._check_and_finalize_processes()
             return

        # Si Whisper está disponible y no ha terminado ni está corriendo, iniciarlo
        if WHISPER_AVAILABLE and self.whisper_transcriber and \
           not self.whisper_transcription_complete and \
           not self.whisper_transcriber.is_running():
            # Asegurarse de que el audio y modelo están listos
            if self.ruta_audio_wav and self.whisper_model_loaded:
                 self.set_status("Iniciando transcripción con Whisper...")
                 # La animación ya debería estar activa desde _transcribir_action
                 utils.draw_status_circle(self.whisper_status_canvas_circle, config.STATUS_COLOR_YELLOW) # Marcar como corriendo
                 self.whisper_transcriber.start()
            else:
                 print("WARN: Google terminó, pero Whisper no puede empezar (falta audio o modelo).")
                 self.whisper_transcription_complete = True # Marcar como 'completo' (no ejecutado)
                 self._stop_whisper_animation() # Detener animación si no empieza
                 utils.draw_status_circle(self.whisper_status_canvas_circle, config.STATUS_COLOR_GRAY)
                 self._check_and_finalize_processes() # Comprobar si todo ha terminado

        else:
             # Si Whisper no está disponible, ya terminó o ya está corriendo (improbable)
             self._check_and_finalize_processes()

        self._update_ui_state() # Actualizar botones


    def _on_whisper_transcription_complete(self, success: bool):
        """Callback cuando la transcripción de Whisper termina."""
        print(f"Callback: Transcripción Whisper completada (Éxito: {success})")
        self.whisper_transcription_complete = True
        self._stop_whisper_animation() # Detener animación de puntos
        utils.draw_status_circle(self.whisper_status_canvas_circle, config.STATUS_COLOR_GREEN if success else config.STATUS_COLOR_RED)

        if self._stop_event_global.is_set():
             self._check_and_finalize_processes()
             return

        self._check_and_finalize_processes() # Comprobar si todo ha terminado
        self._update_ui_state() # Actualizar botones


    def _check_and_finalize_processes(self):
         """Comprueba si ambos procesos han terminado y actualiza estado final."""
         whisper_done = not WHISPER_AVAILABLE or self.whisper_transcription_complete
         if self.google_transcription_complete and whisper_done:
             print("Ambas transcripciones finalizadas.")
             self.set_status("Proceso completado. Puedes seleccionar otro archivo o modelo.")
             # No limpiar WAV aquí, se limpia al seleccionar nuevo archivo o al salir
             self._update_ui_state() # Asegurar estado final de botones

    def _show_error(self, title: str, message: str):
        """Muestra un mensaje de error y actualiza el estado."""
        print(f"ERROR: {title} - {message}")
        messagebox.showerror(title, message)
        current_status = self.status_label.cget("text")
        if not current_status.startswith("Error"):
            self.set_status(f"Error: {title}. Revisa la consola para detalles.")
        # Podríamos necesitar resetear estados aquí dependiendo del error
        # self.is_loading_model = False # Asegurar que no se quede bloqueado cargando
        # self._update_ui_state()


    # --- Métodos de Gestión de Estado Interno y UI ---

    def set_status(self, message: str):
        """Actualiza la etiqueta de estado."""
        if self.status_label:
            self.status_label.config(text=message)
            # print(f"STATUS: {message}") # Evitar duplicar logs si ya se imprime en otro lado

    def _clear_text_areas(self):
        """Limpia el contenido de las áreas de texto."""
        self.area_texto_google.config(state=tk.NORMAL)
        self.area_texto_google.delete("1.0", tk.END)
        self.area_texto_google.config(state=tk.DISABLED)
        if self.area_texto_whisper: # Comprobar si existe
            self.area_texto_whisper.config(state=tk.NORMAL)
            self.area_texto_whisper.delete("1.0", tk.END)
            self.area_texto_whisper.config(state=tk.DISABLED)

    def _update_ui_state(self):
        """Actualiza el estado (habilitado/deshabilitado) de los widgets según el estado de la app."""
        # Combobox Modelo
        model_combo_state = tk.NORMAL if WHISPER_AVAILABLE and not self.is_loading_model and not self.google_transcriber.is_running() and not (self.whisper_transcriber and self.whisper_transcriber.is_running()) else tk.DISABLED
        if self.model_combobox: self.model_combobox.config(state=model_combo_state)

        # Botón Seleccionar Audio
        select_audio_state = tk.NORMAL if WHISPER_AVAILABLE and self.whisper_model_loaded and not self.is_loading_model and not self.google_transcriber.is_running() and not (self.whisper_transcriber and self.whisper_transcriber.is_running()) else tk.DISABLED
        self.boton_seleccionar.config(state=select_audio_state)

        # Botón Transcribir
        transcribe_state = tk.NORMAL if self.ruta_audio_wav and self.whisper_model_loaded and not self.is_loading_model and not self.google_transcriber.is_running() and not (self.whisper_transcriber and self.whisper_transcriber.is_running()) else tk.DISABLED
        self.boton_transcribir.config(state=transcribe_state)
        self.boton_transcribir.config(text="Transcribir" if transcribe_state == tk.NORMAL else "Procesando...")

        # Botón Terminar Google
        terminate_google_state = tk.NORMAL if self.google_transcriber.is_running() else tk.DISABLED
        self.boton_terminar.config(state=terminate_google_state)

        # Botones de Resultados Google
        google_results_text = self.area_texto_google.get("1.0", tk.END).strip()
        google_results_state = tk.NORMAL if google_results_text else tk.DISABLED
        self.boton_copiar_google.config(state=google_results_state)
        self.boton_exportar_google.config(state=google_results_state)

        # Botones de Resultados Whisper
        whisper_results_state = tk.DISABLED # Por defecto deshabilitado
        if WHISPER_AVAILABLE and self.area_texto_whisper:
             whisper_results_text = self.area_texto_whisper.get("1.0", tk.END).strip()
             # Habilitar solo si hay texto y no es un mensaje de error
             if whisper_results_text and not whisper_results_text.lower().startswith("error"):
                 whisper_results_state = tk.NORMAL
        if self.boton_copiar_whisper: self.boton_copiar_whisper.config(state=whisper_results_state)
        if self.boton_exportar_whisper: self.boton_exportar_whisper.config(state=whisper_results_state)


    def _reset_ui_to_initial(self):
        """Resetea la UI completamente al estado inicial (como al arrancar)."""
        self._clear_text_areas()
        self.ruta_audio_original = None
        self.ruta_audio_wav = None
        # No reseteamos el modelo seleccionado ni cargado aquí, eso se maneja por selección
        self.google_transcription_complete = False
        self.whisper_transcription_complete = False
        # self.is_loading_model = False # Ya debería estar false si no hay carga activa

        utils.draw_status_circle(self.google_status_canvas, config.STATUS_COLOR_GRAY)
        if self.whisper_status_canvas_circle: utils.draw_status_circle(self.whisper_status_canvas_circle, config.STATUS_COLOR_GRAY)
        self._stop_whisper_animation()
        self.progress_bar.pack_forget()

        initial_status = "Listo."
        if WHISPER_AVAILABLE:
            if self.whisper_model_loaded:
                 initial_status += f" Modelo '{self.selected_whisper_model}' cargado. Selecciona audio."
            else:
                 initial_status += " Selecciona un modelo Whisper."
        else:
             initial_status = "Whisper no disponible. Funcionalidad limitada."

        self.set_status(initial_status)
        self.ventana.title(f"Audio a Texto Pro ({config.__version__}) - Google vs Whisper")
        self._update_ui_state() # Actualizar estado de botones


    def _reset_transcription_state_flags(self):
        """Resetea solo los flags relacionados con una nueva transcripción."""
        self.google_transcription_complete = False
        self.whisper_transcription_complete = False
        self._clear_text_areas()
        # Los botones de resultado se actualizarán automáticamente por _update_ui_state


    # --- Animación Whisper (para TRANSCRIPCIÓN) ---

    def _animate_whisper_status(self):
        """Ciclo de animación de los puntos para la transcripción Whisper."""
        if not self.animacion_whisper_activa:
            self.whisper_dots_frame.pack_forget() # Ocultar si se detiene
            return

        # Mostrar el frame si está oculto
        if not self.whisper_dots_frame.winfo_viewable():
            self.whisper_dots_frame.pack(pady=2, anchor='w') # Mostrar antes de la barra (que debería estar oculta)

        colors = [config.STATUS_COLOR_GRAY] * 3
        colors[self.dot_index % 3] = config.STATUS_COLOR_YELLOW
        try:
            for i, color in enumerate(colors):
                if i < len(self.dots_refs):
                    self.dots_canvas.itemconfig(self.dots_refs[i], fill=color)
            self.dot_index += 1
            self.animacion_whisper_id = self.ventana.after(300, self._animate_whisper_status)
        except tk.TclError:
             print("Error TclError en animación (probablemente ventana cerrada).")
             self.animacion_whisper_activa = False


    def _start_whisper_animation(self):
        """Inicia la animación de puntos para la transcripción."""
        if not self.animacion_whisper_activa:
            self.animacion_whisper_activa = True
            self.dot_index = 0
            self._animate_whisper_status()

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
                # Resetear puntos a gris y ocultar el frame
                for i in range(len(self.dots_refs)):
                    self.dots_canvas.itemconfig(self.dots_refs[i], fill=config.STATUS_COLOR_GRAY)
                self.whisper_dots_frame.pack_forget()
            except tk.TclError: pass
            self.dot_index = 0


    # --- Gestión de Cierre y Limpieza ---
    _stop_event_global = threading.Event()

    def _stop_all_processes(self, clear_audio=True):
         """Intenta detener todos los procesos activos (Google, Whisper Transcripción, Playback)."""
         print("Intentando detener todos los procesos...")
         self._stop_google_process_if_running() # Detiene Google y Playback asociado

         # Whisper (transcripción) no se puede detener directamente, pero lo registramos
         if self.whisper_transcriber and self.whisper_transcriber.is_running():
              print("INFO: Transcripción Whisper en curso, no se puede detener directamente.")
              # No llamamos a whisper_transcriber.stop() porque no hace nada útil

         # Detener animación de transcripción si estaba activa
         self._stop_whisper_animation()

         # Cancelar carga de modelo si estuviera ocurriendo
         global _model_load_thread, _model_load_stop_event
         if _model_load_thread and _model_load_thread.is_alive():
             print("INFO: Intentando cancelar carga de modelo en curso...")
             _model_load_stop_event.set()

         if clear_audio:
             self.ruta_audio_original = None
             self.ruta_audio_wav = None
             audio_handler.cleanup_temp_wav() # Limpiar temporal


    def _on_closing(self):
        """Manejador para el evento de cierre de ventana."""
        print("Cerrando aplicación...")
        # Comprobar si hay *algún* proceso activo (carga de modelo, transcripción Google/Whisper)
        is_busy = self.is_loading_model or \
                  self.google_transcriber.is_running() or \
                  (self.whisper_transcriber and self.whisper_transcriber.is_running())

        if is_busy:
             if messagebox.askokcancel("Salir", "Hay un proceso activo (carga de modelo o transcripción).\n¿Estás seguro de que quieres salir?"):
                 self._stop_event_global.set()
                 self.set_status("Cerrando, intentando detener procesos...")
                 self._stop_all_processes(clear_audio=True) # Intentar detener todo y limpiar audio
                 # Esperar un poco a que los hilos terminen (join)
                 print("Esperando finalización de hilos (puede tardar si Whisper transcribe)...")
                 self.google_transcriber.join(timeout=1) # Google debería parar rápido
                 if self.whisper_transcriber:
                      self.whisper_transcriber.join(timeout=5) # Whisper puede tardar si transcribe
                 # Esperar al hilo de carga si existe
                 global _model_load_thread
                 if _model_load_thread and _model_load_thread.is_alive():
                      _model_load_thread.join(timeout=2)
                 self.ventana.destroy()
             else:
                 return # No cerrar
        else:
            self._stop_all_processes(clear_audio=True) # Limpiar aunque no haya nada corriendo
            self.ventana.destroy()

    def cleanup_on_exit(self):
         """Limpieza final llamada desde main.py después de cerrar la ventana."""
         print("Ejecutando limpieza final...")
         playback.quit_playback() # Asegura que pygame se cierre
         audio_handler.cleanup_temp_wav() # Limpieza final del temporal
         # Los joins ya se hicieron en _on_closing si era necesario
         print("Limpieza final completada.")