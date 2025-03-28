# gui.py
"""Clase principal de la Interfaz Gráfica de Usuario (GUI) para AudioTranscriptorPro."""

import tkinter as tk
from tkinter import scrolledtext, messagebox
import tkinter.font as tkFont
import pathlib
import threading

# Importar módulos locales
import config
import utils
import audio_handler
import playback
from google_transcriber import GoogleTranscriber
from whisper_transcriber import WhisperTranscriber


class AudioTranscriptorPro:
    """Clase que gestiona la interfaz gráfica y coordina los transcriptores."""

    def __init__(self, root: tk.Tk):
        self.ventana = root
        self.ventana.title(f"Audio a Texto Pro ({config.__version__}) - Google vs Whisper")
        self.ventana.configure(bg=config.BG_COLOR)
        self.ventana.protocol("WM_DELETE_WINDOW", self._on_closing) # Manejar cierre

        # Estado de la aplicación
        self.ruta_audio_original: pathlib.Path | None = None
        self.ruta_audio_wav: pathlib.Path | None = None # Ruta al WAV (original o temporal)
        self.google_transcription_complete = False
        self.whisper_transcription_complete = False

        # --- Animación Whisper ---
        self.animacion_whisper_activa = False
        self.animacion_whisper_id = None
        self.dot_index = 0
        self.dots_refs = [] # Referencias a los óvalos del canvas

        # --- Instancias de transcriptores ---
        # Pasar métodos de la GUI como callbacks usando lambda o métodos directos
        # Usar self.ventana.after para asegurar ejecución en hilo principal de Tkinter
        self.google_transcriber = GoogleTranscriber(
            update_callback=lambda text: self.ventana.after(0, self._update_texto_google, text),
            status_callback=lambda status: self.ventana.after(0, self.set_status, status),
            completion_callback=lambda success: self.ventana.after(0, self._on_google_complete, success),
            error_callback=lambda error: self.ventana.after(0, self._show_error, "Google Error", error)
        )
        self.whisper_transcriber = WhisperTranscriber(
            update_callback=lambda text: self.ventana.after(0, self._update_texto_whisper, text),
            status_callback=lambda status: self.ventana.after(0, self.set_status, status),
            completion_callback=lambda success: self.ventana.after(0, self._on_whisper_complete, success),
            error_callback=lambda error: self.ventana.after(0, self._show_error, "Whisper Error", error)
        )

        # --- Construir la interfaz ---
        self._setup_fonts()
        self._create_widgets()
        self._reset_ui_state() # Estado inicial

        # Iniciar carga del modelo Whisper en segundo plano (lo hace el init de WhisperTranscriber)
        self.set_status("Listo. Selecciona un archivo de audio.")


    def _setup_fonts(self):
        """Configura las fuentes predeterminadas."""
        default_font = tkFont.nametofont("TkDefaultFont")
        default_font.configure(size=11)
        self.ventana.option_add("*Font", default_font)
        # Fuente para áreas de texto podría ser diferente si se desea
        self.text_font = tkFont.Font(family="TkTextFont", size=12)

    def _create_widgets(self):
        """Crea todos los elementos de la interfaz gráfica."""

        # --- Botones de Control Principal ---
        frame_botones_audio = tk.Frame(self.ventana, bg=config.BG_COLOR)
        frame_botones_audio.pack(pady=10)

        self.boton_seleccionar = tk.Button(frame_botones_audio, text="Seleccionar Audio", command=self._seleccionar_audio_action, padx=15, pady=8)
        self.boton_seleccionar.pack(side=tk.LEFT, padx=5)

        self.boton_transcribir = tk.Button(frame_botones_audio, text="Transcribir", command=self._transcribir_action, state=tk.DISABLED, padx=15, pady=8)
        self.boton_transcribir.pack(side=tk.LEFT, padx=5)

        self.boton_terminar = tk.Button(frame_botones_audio, text="Terminar Google", command=self._terminar_google_action, state=tk.DISABLED, padx=15, pady=8)
        self.boton_terminar.pack(side=tk.LEFT, padx=5)

        # --- Etiqueta de Estado ---
        frame_estado = tk.Frame(self.ventana, bg=config.BG_COLOR)
        frame_estado.pack(pady=5, fill=tk.X, padx=20)
        self.status_label = tk.Label(frame_estado, text="", bg=config.BG_COLOR, font=("TkDefaultFont", 10), anchor='w')
        self.status_label.pack(fill=tk.X)

        # --- Animación Whisper (Puntos) ---
        self.whisper_dots_frame = tk.Frame(self.ventana, bg=config.BG_COLOR)
        self.whisper_dots_frame.pack(pady=2)
        self.dots_canvas = tk.Canvas(self.whisper_dots_frame, width=40, height=12, bg=config.BG_COLOR, highlightthickness=0)
        self.dots_canvas.pack()
        # Crear puntos y guardar referencias
        self.dots_refs = [self.dots_canvas.create_oval(i * 12 + 2, 2, i * 12 + 10, 10, fill=config.STATUS_COLOR_GRAY, tags=f"dot{i}") for i in range(3)]


        # --- Áreas de Texto ---
        frame_textos = tk.Frame(self.ventana, bg=config.BG_COLOR)
        frame_textos.pack(fill=tk.BOTH, expand=True, padx=20, pady=(5, 10))

        # Google
        frame_google = tk.LabelFrame(frame_textos, text="Transcripción Google Speech", bg=config.BG_COLOR, padx=5, pady=5)
        frame_google.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.area_texto_google = scrolledtext.ScrolledText(frame_google, wrap=tk.WORD, font=self.text_font, height=15, padx=10, pady=10, borderwidth=1, relief=tk.SOLID)
        self.area_texto_google.pack(fill=tk.BOTH, expand=True)
        self.area_texto_google.config(state=tk.DISABLED) # Empezar deshabilitado

        # Indicador de estado Google
        self.google_status_canvas = tk.Canvas(frame_google, width=10, height=10, bg=config.BG_COLOR, highlightthickness=0)
        self.google_status_canvas.place(relx=1.0, rely=0.0, x=-5, y=5, anchor=tk.NE) # Esquina superior derecha
        utils.draw_status_circle(self.google_status_canvas, config.STATUS_COLOR_GRAY)


        # Whisper
        frame_whisper = tk.LabelFrame(frame_textos, text="Transcripción Whisper", bg=config.BG_COLOR, padx=5, pady=5)
        frame_whisper.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        self.area_texto_whisper = scrolledtext.ScrolledText(frame_whisper, wrap=tk.WORD, font=self.text_font, height=15, padx=10, pady=10, borderwidth=1, relief=tk.SOLID)
        self.area_texto_whisper.pack(fill=tk.BOTH, expand=True)
        self.area_texto_whisper.config(state=tk.DISABLED) # Empezar deshabilitado

        # Indicador de estado Whisper
        self.whisper_status_canvas_circle = tk.Canvas(frame_whisper, width=10, height=10, bg=config.BG_COLOR, highlightthickness=0)
        self.whisper_status_canvas_circle.place(relx=1.0, rely=0.0, x=-5, y=5, anchor=tk.NE) # Esquina superior derecha
        utils.draw_status_circle(self.whisper_status_canvas_circle, config.STATUS_COLOR_GRAY)


        # --- Botones de Acción por Transcriptor ---
        frame_botones_accion = tk.Frame(self.ventana, bg=config.BG_COLOR)
        frame_botones_accion.pack(pady=(5, 15), fill=tk.X, padx=20)

        # Botones Google (izquierda)
        frame_botones_google = tk.Frame(frame_botones_accion, bg=config.BG_COLOR)
        frame_botones_google.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.boton_copiar_google = tk.Button(frame_botones_google, text="Copiar Google", command=self._copiar_google_action, state=tk.DISABLED, padx=10, pady=5)
        self.boton_copiar_google.pack(side=tk.LEFT, padx=(0,5))
        self.boton_exportar_google = tk.Button(frame_botones_google, text="Exportar Google", command=self._exportar_google_action, state=tk.DISABLED, padx=10, pady=5)
        self.boton_exportar_google.pack(side=tk.LEFT, padx=5)


        # Botones Whisper (derecha)
        frame_botones_whisper = tk.Frame(frame_botones_accion, bg=config.BG_COLOR)
        frame_botones_whisper.pack(side=tk.RIGHT, expand=True, fill=tk.X, anchor='e')

        self.boton_exportar_whisper = tk.Button(frame_botones_whisper, text="Exportar Whisper", command=self._exportar_whisper_action, state=tk.DISABLED, padx=10, pady=5)
        self.boton_exportar_whisper.pack(side=tk.RIGHT, padx=(5,0))
        self.boton_copiar_whisper = tk.Button(frame_botones_whisper, text="Copiar Whisper", command=self._copiar_whisper_action, state=tk.DISABLED, padx=10, pady=5)
        self.boton_copiar_whisper.pack(side=tk.RIGHT, padx=5)


    # --- Métodos de Acción (Triggers de Usuario) ---

    def _seleccionar_audio_action(self):
        """Acción del botón 'Seleccionar Audio'."""
        print("Acción: Seleccionar audio iniciada.")
        # Detener cualquier proceso activo antes de seleccionar nuevo archivo
        self._stop_all_processes(clear_audio=False) # No limpiar audio aún

        selected_path = audio_handler.select_audio_file()
        if not selected_path:
            self.set_status("Selección cancelada.")
            # Restaurar estado si había algo antes? Por ahora no.
            return

        self.ruta_audio_original = selected_path
        self.set_status(f"Archivo seleccionado: {self.ruta_audio_original.name}. Convirtiendo si es necesario...")
        utils.draw_status_circle(self.google_status_canvas, config.STATUS_COLOR_GRAY)
        utils.draw_status_circle(self.whisper_status_canvas_circle, config.STATUS_COLOR_GRAY)
        self._clear_text_areas()


        # Convertir a WAV (necesario para Google y playback, opcional para Whisper)
        # Ejecutar en hilo para no bloquear GUI durante conversión
        threading.Thread(target=self._convert_and_prepare_audio, args=(selected_path,), daemon=True).start()


    def _convert_and_prepare_audio(self, audio_path: pathlib.Path):
        """Convierte a WAV (si es necesario) y actualiza la GUI."""
        wav_path = audio_handler.convert_to_wav_if_needed(audio_path)

        # Actualizar GUI en hilo principal
        def update_gui_after_conversion():
            if wav_path:
                self.ruta_audio_wav = wav_path
                self.google_transcriber.set_audio_file(self.ruta_audio_wav)
                 # Whisper puede usar el original o el WAV, pasemos WAV por consistencia si se creó
                self.whisper_transcriber.set_audio_file(self.ruta_audio_wav)
                self.ventana.title(f"Audio a Texto Pro - {self.ruta_audio_original.name} ({config.__version__})")
                self.boton_transcribir.config(state=tk.NORMAL, text="Transcribir")
                self.set_status("Listo para transcribir.")
                print(f"Audio preparado. WAV path: {self.ruta_audio_wav}")
            else:
                # Falló la conversión
                self.ruta_audio_original = None
                self.ruta_audio_wav = None
                self.boton_transcribir.config(state=tk.DISABLED)
                self.set_status("Error en la conversión. Selecciona otro archivo.")
                self.ventana.title(f"Audio a Texto Pro ({config.__version__}) - Google vs Whisper")

        self.ventana.after(0, update_gui_after_conversion)


    def _transcribir_action(self):
        """Acción del botón 'Transcribir'."""
        if not self.ruta_audio_wav:
            self._show_error("Error", "No hay un archivo de audio preparado para transcribir.")
            return
        if self.google_transcriber.is_running() or self.whisper_transcriber.is_running():
            self._show_error("Información", "Ya hay una transcripción en curso.")
            return

        print("Acción: Iniciar transcripción.")
        self._reset_transcription_state()
        self.set_status("Iniciando transcripción con Google...")
        self.boton_transcribir.config(state=tk.DISABLED, text="Procesando...")
        self.boton_terminar.config(state=tk.NORMAL) # Habilitar botón para parar Google
        utils.draw_status_circle(self.google_status_canvas, config.STATUS_COLOR_GREEN)
        utils.draw_status_circle(self.whisper_status_canvas_circle, config.STATUS_COLOR_RED) # Whisper pendiente

        # Iniciar Google Transcriber
        self.google_transcriber.start()


    def _terminar_google_action(self):
        """Acción del botón 'Terminar Google'."""
        print("Acción: Terminar transcripción Google.")
        if self.google_transcriber.is_running():
            self.google_transcriber.stop()
            self.boton_terminar.config(state=tk.DISABLED)
            self.set_status("Deteniendo Google... Whisper continuará si se inició.")
            utils.draw_status_circle(self.google_status_canvas, config.STATUS_COLOR_GRAY)
            # No cambiar estado del botón 'Transcribir' aquí, esperar a _on_google_complete
        else:
            print("Google no estaba corriendo.")


    def _copiar_google_action(self):
        """Acción del botón 'Copiar Google'."""
        texto = self.area_texto_google.get("1.0", tk.END).strip()
        utils.copy_to_clipboard(self.ventana, texto)

    def _exportar_google_action(self):
        """Acción del botón 'Exportar Google'."""
        texto = self.area_texto_google.get("1.0", tk.END).strip()
        utils.export_text_to_file(texto, "Guardar transcripción de Google")

    def _copiar_whisper_action(self):
        """Acción del botón 'Copiar Whisper'."""
        texto = self.area_texto_whisper.get("1.0", tk.END).strip()
        utils.copy_to_clipboard(self.ventana, texto)

    def _exportar_whisper_action(self):
        """Acción del botón 'Exportar Whisper'."""
        texto = self.area_texto_whisper.get("1.0", tk.END).strip()
        utils.export_text_to_file(texto, "Guardar transcripción de Whisper")


    # --- Métodos Callback (Llamados por los transcriptores) ---

    def _update_texto_google(self, texto_segmento: str):
        """Actualiza el área de texto de Google (llamado desde hilo)."""
        if not self.area_texto_google: return # Seguridad
        self.area_texto_google.config(state=tk.NORMAL)
        current_text = self.area_texto_google.get("1.0", tk.END).strip()
        texto_a_insertar = (" " + texto_segmento) if current_text else texto_segmento
        self.area_texto_google.insert(tk.END, texto_a_insertar)
        self.area_texto_google.see(tk.END) # Auto-scroll
        self.area_texto_google.config(state=tk.DISABLED)
        # Habilitar botones si es la primera vez que llega texto
        if self.boton_copiar_google['state'] == tk.DISABLED:
            self._habilitar_botones_resultado(google=True)

    def _update_texto_whisper(self, texto_completo: str):
        """Actualiza el área de texto de Whisper con el texto final (llamado desde hilo)."""
        if not self.area_texto_whisper: return # Seguridad
        self.area_texto_whisper.config(state=tk.NORMAL)
        self.area_texto_whisper.delete("1.0", tk.END)
        self.area_texto_whisper.insert("1.0", texto_completo)
        self.area_texto_whisper.see("1.0") # Ir al inicio
        self.area_texto_whisper.config(state=tk.DISABLED)
        if texto_completo and not texto_completo.startswith("Error"):
             self._habilitar_botones_resultado(whisper=True)
        else:
             self._habilitar_botones_resultado(whisper=False) # Deshabilitar si hay error


    def _on_google_complete(self, success: bool):
        """Callback cuando Google Transcriber termina (o es detenido)."""
        print(f"Callback: Google completado (Éxito: {success})")
        self.google_transcription_complete = True
        self.boton_terminar.config(state=tk.DISABLED) # Deshabilitar siempre al terminar Google
        # Marcar estado final de Google
        utils.draw_status_circle(self.google_status_canvas, config.STATUS_COLOR_GREEN if success else config.STATUS_COLOR_GRAY)

        if self._stop_event_global.is_set(): # Si la app se está cerrando
             self._check_all_processes_finished()
             return

        # Si Google terminó (correctamente o detenido) y Whisper no ha terminado, iniciar Whisper
        if not self.whisper_transcription_complete and self.ruta_audio_wav: # Usar WAV también para Whisper
             # Podríamos tener un flag para no iniciar Whisper si Google fue detenido manualmente?
             # Por ahora, lo iniciamos siempre que Google termine.
             if not self.whisper_transcriber.is_running():
                 self.set_status("Iniciando transcripción con Whisper...")
                 self._start_whisper_animation() # Iniciar animación
                 utils.draw_status_circle(self.whisper_status_canvas_circle, config.STATUS_COLOR_RED) # Marcar como pendiente/corriendo
                 self.whisper_transcriber.start()
             else:
                 print("Whisper ya estaba corriendo (esto no debería pasar si se inicia tras Google).")
        else:
             # Si Whisper ya terminó (improbable) o no hay audio, comprobar si todo ha terminado
             self._check_all_processes_finished()

    def _on_whisper_complete(self, success: bool):
        """Callback cuando Whisper Transcriber termina."""
        print(f"Callback: Whisper completado (Éxito: {success})")
        self.whisper_transcription_complete = True
        self._stop_whisper_animation() # Detener animación
        utils.draw_status_circle(self.whisper_status_canvas_circle, config.STATUS_COLOR_GREEN if success else config.STATUS_COLOR_RED) # Verde si éxito, Rojo si error

        if self._stop_event_global.is_set(): # Si la app se está cerrando
             self._check_all_processes_finished()
             return

        # Comprobar si ambos han terminado
        self._check_all_processes_finished()


    def _check_all_processes_finished(self):
         """Comprueba si ambos procesos han terminado y actualiza la UI final."""
         if self.google_transcription_complete and self.whisper_transcription_complete:
             print("Ambas transcripciones finalizadas.")
             self.set_status("Proceso completado.")
             self.boton_transcribir.config(text="Transcribir", state=tk.NORMAL if self.ruta_audio_wav else tk.DISABLED)
             # Limpiar WAV temporal si existe
             # audio_handler.cleanup_temp_wav() # Mover limpieza a _on_closing o al seleccionar nuevo archivo


    def _show_error(self, title: str, message: str):
        """Muestra un mensaje de error y actualiza el estado."""
        print(f"ERROR: {title} - {message}")
        messagebox.showerror(title, message)
        # Actualizar estado para reflejar el error
        current_status = self.status_label.cget("text")
        if not current_status.startswith("Error"): # No sobrescribir si ya hay error
            self.set_status(f"Error: {title}. Revisa la consola para detalles.")
        # Podríamos intentar resetear botones aquí si el error es grave
        # self.boton_transcribir.config(text="Transcribir", state=tk.NORMAL if self.ruta_audio_wav else tk.DISABLED)
        # self.boton_terminar.config(state=tk.DISABLED)


    # --- Métodos de Gestión de Estado Interno y UI ---

    def set_status(self, message: str):
        """Actualiza la etiqueta de estado."""
        if self.status_label: # Comprobar si existe
            self.status_label.config(text=message)
            print(f"STATUS: {message}") # Loguear estado

    def _clear_text_areas(self):
        """Limpia el contenido de las áreas de texto."""
        self.area_texto_google.config(state=tk.NORMAL)
        self.area_texto_google.delete("1.0", tk.END)
        self.area_texto_google.config(state=tk.DISABLED)

        self.area_texto_whisper.config(state=tk.NORMAL)
        self.area_texto_whisper.delete("1.0", tk.END)
        self.area_texto_whisper.config(state=tk.DISABLED)

    def _habilitar_botones_resultado(self, google: bool | None = None, whisper: bool | None = None):
        """Habilita o deshabilita los botones de copiar/exportar."""
        if google is not None:
            state_google = tk.NORMAL if google else tk.DISABLED
            self.boton_copiar_google.config(state=state_google)
            self.boton_exportar_google.config(state=state_google)
        if whisper is not None:
            state_whisper = tk.NORMAL if whisper else tk.DISABLED
            self.boton_copiar_whisper.config(state=state_whisper)
            self.boton_exportar_whisper.config(state=state_whisper)


    def _reset_ui_state(self):
        """Resetea la UI a su estado inicial o después de una tarea."""
        self._clear_text_areas()
        self.boton_transcribir.config(text="Transcribir", state=tk.DISABLED)
        self.boton_terminar.config(state=tk.DISABLED)
        self._habilitar_botones_resultado(google=False, whisper=False)
        utils.draw_status_circle(self.google_status_canvas, config.STATUS_COLOR_GRAY)
        utils.draw_status_circle(self.whisper_status_canvas_circle, config.STATUS_COLOR_GRAY)
        self._stop_whisper_animation()
        self.set_status("Selecciona un archivo de audio.")
        self.ventana.title(f"Audio a Texto Pro ({config.__version__}) - Google vs Whisper")


    def _reset_transcription_state(self):
        """Resetea el estado relacionado con una nueva transcripción."""
        self.google_transcription_complete = False
        self.whisper_transcription_complete = False
        self._clear_text_areas()
        self._habilitar_botones_resultado(google=False, whisper=False)


    # --- Animación Whisper ---

    def _animate_whisper_status(self):
        """Ciclo de animación de los puntos para Whisper."""
        if not self.animacion_whisper_activa:
            return

        # Ciclo de colores amarillo -> gris -> gris -> amarillo ...
        colors = [config.STATUS_COLOR_GRAY] * 3
        colors[self.dot_index % 3] = config.STATUS_COLOR_YELLOW
        try:
            for i, color in enumerate(colors):
                if i < len(self.dots_refs): # Asegurarse que la referencia existe
                    self.dots_canvas.itemconfig(self.dots_refs[i], fill=color)
            self.dot_index += 1
            self.animacion_whisper_id = self.ventana.after(300, self._animate_whisper_status)
        except tk.TclError:
             # El canvas podría haber sido destruido si la ventana se cerró abruptamente
             print("Error TclError en animación (probablemente ventana cerrada).")
             self.animacion_whisper_activa = False


    def _start_whisper_animation(self):
        """Inicia la animación de puntos."""
        if not self.animacion_whisper_activa:
            self.animacion_whisper_activa = True
            self.dot_index = 0 # Reiniciar índice
            self._animate_whisper_status()

    def _stop_whisper_animation(self):
        """Detiene la animación de puntos y los resetea a gris."""
        if self.animacion_whisper_activa:
            self.animacion_whisper_activa = False
            if self.animacion_whisper_id:
                try:
                    self.ventana.after_cancel(self.animacion_whisper_id)
                except tk.TclError: pass # Ignorar si ya no existe el after_id
                self.animacion_whisper_id = None
            # Resetear puntos a gris
            try:
                for i in range(len(self.dots_refs)):
                    self.dots_canvas.itemconfig(self.dots_refs[i], fill=config.STATUS_COLOR_GRAY)
            except tk.TclError: pass # Ignorar si el canvas ya no existe
            self.dot_index = 0

    # --- Gestión de Cierre y Limpieza ---
    _stop_event_global = threading.Event() # Evento para señalar cierre global

    def _stop_all_processes(self, clear_audio=True):
         """Intenta detener todos los procesos activos."""
         print("Intentando detener todos los procesos...")
         if self.google_transcriber.is_running():
              self.google_transcriber.stop()
         if self.whisper_transcriber.is_running():
              self.whisper_transcriber.stop() # Whisper no se detiene realmente, pero lo marcamos

         playback.stop_audio()
         playback.unload_audio()
         self._stop_whisper_animation()

         if clear_audio:
             self.ruta_audio_original = None
             self.ruta_audio_wav = None
             audio_handler.cleanup_temp_wav()


    def _on_closing(self):
        """Manejador para el evento de cierre de ventana."""
        print("Cerrando aplicación...")
        if self.google_transcriber.is_running() or self.whisper_transcriber.is_running():
             if messagebox.askokcancel("Salir", "Hay una transcripción en curso.\n¿Estás seguro de que quieres salir?"):
                 self._stop_event_global.set() # Señalizar cierre a los hilos
                 self.set_status("Cerrando, esperando finalización de hilos...")
                 self._stop_all_processes(clear_audio=True)
                 # Esperar un poco a que los hilos terminen (join)
                 self.google_transcriber.join(timeout=2)
                 self.whisper_transcriber.join(timeout=5) # Whisper puede tardar más
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
         # No necesitamos join aquí si _on_closing ya lo hizo
         print("Limpieza final completada.")