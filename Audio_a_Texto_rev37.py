import os
import pathlib
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import tkinter.font as tkFont

import pygame
import speech_recognition as sr
from pydub import AudioSegment
import whisper # Importar biblioteca Whisper

__version__ = "rev37"  # Control de revisión: Whisper completa transcripción al terminar


class AudioTranscriptorPro:

    def __init__(self):
        self.ventana = tk.Tk()
        self.ventana.title(
            f"Audio a Texto Pro - Comparativa Transcripciones ({__version__}) - Google vs Whisper")
        self.ventana.wm_title("Audio a Texto Pro - Comparativa Transcripciones (Google vs Whisper)")
        self.ruta_audio = ""
        self.texto_transcripcion_google = ""
        self.texto_transcripcion_whisper = ""
        self.reproduciendo = False
        self.reconocedor = sr.Recognizer()
        pygame.mixer.init()
        self.audio_segment = None
        self.tiempo_inicio_pausa = 0
        self.transcripcion_en_progreso = False
        self.reproduccion_en_curso = False
        self.terminar_transcripcion_flag = False
        self.whisper_model = None
        self.modelo_whisper_cargado = False
        self.ruta_audio_pathlib = None
        self.whisper_transcription_thread = None
        self.google_transcription_complete = False
        self.whisper_transcription_ready = False
        self.animacion_whisper_activa = False
        self.animacion_whisper_id = None
        self.dot_index = 0
        self.dots = []

        # --- Interfaz Gráfica ---
        self.ventana.configure(bg='#f0f0f0')
        default_font = tkFont.nametofont("TkDefaultFont")
        default_font.configure(size=11)
        self.ventana.option_add("*Font", default_font)

        frame_botones_audio = tk.Frame(self.ventana, bg='#f0f0f0')
        frame_botones_audio.pack(pady=10)

        self.boton_seleccionar = tk.Button(frame_botones_audio,
                                            text="Seleccionar Audio",
                                            command=self.seleccionar_audio,
                                            padx=15, pady=8)
        self.boton_seleccionar.pack(side=tk.LEFT, padx=5)

        self.boton_transcribir = tk.Button(frame_botones_audio,
                                            text="Transcribir",
                                            command=self.transcribir_audio,
                                            state=tk.DISABLED,
                                            padx=15, pady=8)
        self.boton_transcribir.pack(side=tk.LEFT, padx=5)

        self.boton_terminar = tk.Button(frame_botones_audio,
                                         text="Terminar",
                                         command=self.terminar_transcripcion,
                                         state=tk.DISABLED,
                                         padx=15, pady=8)
        self.boton_terminar.pack(side=tk.LEFT, padx=5)

        # --- Frame para el estado de la transcripción ---
        frame_estado = tk.Frame(self.ventana, bg='#f0f0f0')
        frame_estado.pack(pady=5)
        self.status_label = tk.Label(frame_estado, text="Selecciona un archivo de audio a transcribir", bg='#f0f0f0', font=("TkDefaultFont", 10))
        self.status_label.pack()

        # --- Frame para los puntos de Whisper ---
        self.whisper_dots_frame = tk.Frame(self.ventana, bg='#f0f0f0')
        self.whisper_dots_frame.pack(pady=5)
        self.dots_canvas = tk.Canvas(self.whisper_dots_frame, width=30, height=10, bg='#f0f0f0', highlightthickness=0)
        self.dots_canvas.pack()
        self.dots = [self.dots_canvas.create_oval(i * 10, 0, i * 10 + 8, 8, fill="gray", tags=f"dot{i}") for i in range(3)]

        # --- Frame para las áreas de texto ---
        frame_textos = tk.Frame(self.ventana, bg='#f0f0f0')
        frame_textos.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # --- Área de texto para Google Speech ---
        frame_google = tk.Frame(frame_textos, bg='#f0f0f0')
        frame_google.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        label_google = tk.Label(frame_google, text="Transcripción Google Speech:", bg='#f0f0f0')
        label_google.pack(pady=(0, 5))
        self.area_texto_google = scrolledtext.ScrolledText(frame_google,
                                                            wrap=tk.WORD,
                                                            font=("TkTextFont", 12),
                                                            height=15,
                                                            padx=10, pady=10,
                                                            borderwidth=2, relief=tk.SOLID)
        self.area_texto_google.pack(fill=tk.BOTH, expand=True)
        self.area_texto_google.config(state=tk.NORMAL)

        self.google_status_canvas = tk.Canvas(frame_google, width=10, height=10, bg='#f0f0f0', highlightthickness=0)
        self.google_status_canvas.pack(anchor=tk.NE, padx=5, pady=5)
        self.draw_circle(self.google_status_canvas, "gray")

        # --- Área de texto para Whisper ---
        frame_whisper = tk.Frame(frame_textos, bg='#f0f0f0')
        frame_whisper.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        label_whisper = tk.Label(frame_whisper, text="Transcripción Whisper:", bg='#f0f0f0')
        label_whisper.pack(pady=(0, 5))
        self.area_texto_whisper = scrolledtext.ScrolledText(frame_whisper,
                                                             wrap=tk.WORD,
                                                             font=("TkTextFont", 12),
                                                             height=15,
                                                             padx=10, pady=10,
                                                             borderwidth=2, relief=tk.SOLID)
        self.area_texto_whisper.pack(fill=tk.BOTH, expand=True)
        self.area_texto_whisper.config(state=tk.NORMAL)

        self.whisper_status_canvas_circle = tk.Canvas(frame_whisper, width=10, height=10, bg='#f0f0f0', highlightthickness=0)
        self.whisper_status_canvas_circle.pack(anchor=tk.NE, padx=5, pady=5)
        self.draw_circle(self.whisper_status_canvas_circle, "gray")

        # --- Frame para botones de Google Speech ---
        frame_botones_google = tk.Frame(self.ventana, bg='#f0f0f0')
        frame_botones_google.pack(pady=5)

        self.boton_copiar_google = tk.Button(frame_botones_google,
                                               text="Copiar Texto Google",
                                               command=self.copiar_texto_google,
                                               state=tk.DISABLED,
                                               padx=15, pady=8)
        self.boton_copiar_google.pack(side=tk.LEFT, padx=5)

        self.boton_exportar_google = tk.Button(frame_botones_google,
                                                text="Exportar a TXT Google",
                                                command=self.exportar_texto_google,
                                                state=tk.DISABLED,
                                                padx=15, pady=8)
        self.boton_exportar_google.pack(side=tk.LEFT, padx=5)

        # --- Frame para botones de Whisper ---
        frame_botones_whisper = tk.Frame(self.ventana, bg='#f0f0f0')
        frame_botones_whisper.pack(pady=5)

        self.boton_copiar_whisper = tk.Button(frame_botones_whisper,
                                                text="Copiar Texto Whisper",
                                                command=self.copiar_texto_whisper,
                                                state=tk.DISABLED,
                                                padx=15, pady=8)
        self.boton_copiar_whisper.pack(side=tk.LEFT, padx=5)

        self.boton_exportar_whisper = tk.Button(frame_botones_whisper,
                                                 text="Exportar a TXT Whisper",
                                                 command=self.exportar_texto_whisper,
                                                 state=tk.DISABLED,
                                                 padx=15, pady=8)
        self.boton_exportar_whisper.pack(side=tk.LEFT, padx=5)

    def draw_circle(self, canvas, color):
        canvas.delete("circle")
        canvas.create_oval(0, 0, 10, 10, fill=color, tags="circle")

    def seleccionar_audio(self):
        self.ruta_audio = filedialog.askopenfilename(
            defaultextension=".mp3",
            filetypes=[("Archivos de audio", "*.mp3 *.wav *.ogg"),
                       ("Todos los archivos", "*.*")])
        if self.ruta_audio:
            self.area_texto_google.delete("1.0", tk.END)
            self.area_texto_whisper.delete("1.0", tk.END)
            self.texto_transcripcion_google = ""
            self.texto_transcripcion_whisper = ""
            self.ruta_audio_pathlib = pathlib.Path(self.ruta_audio)
            self.google_transcription_complete = False
            self.whisper_transcription_ready = False
            self.habilitar_botones_google(False)
            self.habilitar_botones_whisper(False)
            self.status_label.config(text="Archivo de audio seleccionado.")
            self.draw_circle(self.google_status_canvas, "gray")
            self.draw_circle(self.whisper_status_canvas_circle, "red") # Cambia a rojo al seleccionar
            self.stop_whisper_animation()

            if self.ruta_audio_pathlib.suffix.lower() != ".wav":
                try:
                    audio = AudioSegment.from_file(
                        str(self.ruta_audio_pathlib),
                        format=self.ruta_audio_pathlib.suffix[1:])
                    wav_path = str(self.ruta_audio_pathlib.with_suffix('.wav'))
                    audio.export(wav_path, format="wav", codec="pcm_s16le")
                    self.ruta_audio_pathlib = pathlib.Path(wav_path)
                except Exception as e:
                    print(f"Error al convertir a WAV: {e}")
                    messagebox.showerror("Error", f"Error al convertir a WAV: {e}")
                    return

            self.boton_transcribir.config(state=tk.NORMAL)
            self.boton_transcribir.config(text="Transcribir")
            nombre_archivo = self.ruta_audio_pathlib.name
            self.ventana.title(
                f"Audio a Texto Pro - {nombre_archivo} ({__version__}) - Google vs Whisper")


    def transcribir_audio(self):
        if not self.ruta_audio:
            messagebox.showinfo("Información", "Por favor, selecciona un archivo de audio primero.")
            return

        if not self.transcripcion_en_progreso:
            self.transcripcion_en_progreso = True
            self.reproduccion_en_curso = True
            self.terminar_transcripcion_flag = False
            self.boton_transcribir.config(state=tk.DISABLED, text="Transcribiendo...")
            self.boton_terminar.config(state=tk.NORMAL)
            self.texto_transcripcion_google = ""
            self.texto_transcripcion_whisper = ""
            self.area_texto_google.delete("1.0", tk.END)
            self.area_texto_whisper.delete("1.0", tk.END)
            self.google_transcription_complete = False
            self.whisper_transcription_ready = False
            self.habilitar_botones_google(False)
            self.habilitar_botones_whisper(False)
            self.stop_whisper_animation()

            self.status_label.config(text="Transcribiendo con Google Speech...")
            self.draw_circle(self.google_status_canvas, "green")
            self.draw_circle(self.whisper_status_canvas_circle, "red")

            # --- Iniciar transcripción con GOOGLE SPEECH RECOGNITION (Tiempo real) ---
            threading.Thread(target=self.transcribir_audio_google_speech).start()


    def transcribir_audio_google_speech(self):
        try:
            if self.audio_segment is None:
                try:
                    self.audio_segment = AudioSegment.from_wav(
                        str(self.ruta_audio_pathlib))
                except Exception as e:
                    print(f"Error al cargar WAV: {e}")
                    self.audio_segment = AudioSegment.from_file(
                        str(self.ruta_audio_pathlib), force_format="wav")

            inicio_segmento = 0
            tiempo_audio = len(self.audio_segment)
            segment_duration_ms = 30000  # Segmentos de 30 segundos

            pygame.mixer.music.load(self.audio_segment.export(format="wav"))
            pygame.mixer.music.play()

            while inicio_segmento < tiempo_audio and self.reproduccion_en_curso and self.transcripcion_en_progreso and not self.terminar_transcripcion_flag:
                fin_segmento = min(inicio_segmento + segment_duration_ms, tiempo_audio)
                segmento = self.audio_segment[inicio_segmento:fin_segmento]

                temp_wav_buffer = segmento.export(format="wav")

                with sr.AudioFile(temp_wav_buffer) as fuente:
                    audio_data = self.reconocedor.record(fuente)
                    start_time = time.time()
                    try:
                        texto_google = self.reconocedor.recognize_google(
                            audio_data, language="es-ES")
                        end_time = time.time()
                        transcription_time = end_time - start_time

                        segment_playback_duration_ms = len(segmento)
                        sleep_duration_s = (segment_playback_duration_ms / 1000) - transcription_time
                        if sleep_duration_s < 0:
                            sleep_duration_s = 0

                        self.texto_transcripcion_google += " " + texto_google
                        self.ventana.after(0, self.actualizar_texto_google, texto_google)
                        if not self.boton_copiar_google["state"] == tk.NORMAL:
                            self.ventana.after(0, self.habilitar_botones_google, True)

                    except sr.UnknownValueError:
                        print("No se pudo entender este segmento de audio (Google).")
                        sleep_duration_s = segment_duration_ms / 1000
                    except sr.RequestError as e:
                        print(f"Error en la solicitud al servicio de reconocimiento de voz (Google): {e}")
                        sleep_duration_s = segment_duration_ms / 1000

                    sleep_delay_ms = int(sleep_duration_s * 1000)
                    if sleep_delay_ms > 0:
                        time.sleep(sleep_duration_s)

                inicio_segmento = fin_segmento

                if self.terminar_transcripcion_flag: # Comprobar la bandera después de cada segmento
                    break

            self.google_transcription_complete = True
            self.ventana.after(0, self.status_label.config(text="Iniciando transcripción con Whisper..."))
            self.ventana.after(0, self.iniciar_transcripcion_whisper)
            self.ventana.after(0, self.draw_circle(self.google_status_canvas, "green")) # Mantener verde al finalizar Google
            self.ventana.after(0, pygame.mixer.music.stop) # Detener el audio al finalizar Google o al terminar

        except Exception as e:
            print(f"Error en transcripción (Google Speech): {e}")
            self.ventana.after(
                0,
                lambda: messagebox.showerror("Error",
                                                f"Error al reproducir o transcribir (Google):\n{e}"))
            self.ventana.after(0, self.finalizar_transcripcion)


    def iniciar_transcripcion_whisper(self):
        self.status_label.config(text="Transcribiendo con Whisper...")
        self.draw_circle(self.whisper_status_canvas_circle, "red")
        self.start_whisper_animation()
        if not self.modelo_whisper_cargado:
            self.cargar_modelo_whisper()
        else:
            self.iniciar_transcripcion_whisper_hilo()


    def cargar_modelo_whisper(self):
        threading.Thread(target=self._cargar_modelo_whisper_thread).start()


    def _cargar_modelo_whisper_thread(self):
        try:
            self.whisper_model = whisper.load_model("tiny")
            self.modelo_whisper_cargado = True
            self.iniciar_transcripcion_whisper_hilo()
        except Exception as e:
            print(f"Error al cargar modelo Whisper: {e}")
            # No mostrar error aquí para evitar mensaje al inicio.
            # El error se mostrará si la transcripción con Whisper falla más adelante.
            self.stop_whisper_animation()
            self.ventana.after(0, self.draw_circle(self.whisper_status_canvas_circle, "red"))


    def iniciar_transcripcion_whisper_hilo(self):
        self.whisper_transcription_ready = False
        self.whisper_transcription_thread = threading.Thread(target=self.transcribir_audio_whisper_background)
        self.whisper_transcription_thread.start()


    def transcribir_audio_whisper_background(self):
        if not self.ruta_audio_pathlib:
            print("Advertencia: No se ha seleccionado un archivo de audio para Whisper.")
            self.ventana.after(0, self.status_label.config(text="Selecciona un archivo de audio")) # Volver al mensaje inicial
            self.ventana.after(0, self.draw_circle(self.whisper_status_canvas_circle, "gray"))
            self.stop_whisper_animation()
            return

        # La bandera terminar_transcripcion_flag ya no interrumpe Whisper
        try:
            texto_whisper_completo = self.whisper_model.transcribe(str(self.ruta_audio_pathlib), language="es", initial_prompt="Transcripción en español.")
            self.texto_transcripcion_whisper = texto_whisper_completo["text"]
            self.whisper_transcription_ready = True
            self.ventana.after(0, self.actualizar_texto_whisper, self.texto_transcripcion_whisper)
            self.ventana.after(0, self.habilitar_botones_whisper, True)
            self.ventana.after(0, self.status_label.config(text="Finalizado"))
            self.ventana.after(0, self.draw_circle(self.whisper_status_canvas_circle, "green"))
            self.stop_whisper_animation()
            print("Transcripción con Whisper en segundo plano COMPLETA.")

        except Exception as whisper_error:
            print(f"Error en transcripción con Whisper (segundo plano): {whisper_error}")
            self.texto_transcripcion_whisper = "Error en transcripción con Whisper."
            self.ventana.after(0, self.actualizar_texto_whisper, self.texto_transcripcion_whisper)
            self.ventana.after(0, self.habilitar_botones_whisper, True)
            self.ventana.after(0, self.status_label.config(text="Finalizado (Error en Whisper)"))
            self.ventana.after(0, self.draw_circle(self.whisper_status_canvas_circle, "red")) # Mantener rojo si hay error
            self.whisper_transcription_ready = True # Indicar como "lista" aunque haya error
            self.stop_whisper_animation()


    def finalizar_transcripcion(self):
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        self.reproduciendo = False
        self.reproduccion_en_curso = False
        self.transcripcion_en_progreso = False
        self.terminar_transcripcion_flag = False
        self.tiempo_inicio_pausa = 0
        self.audio_segment = None
        self.boton_transcribir.config(state=tk.NORMAL, text="Transcribir")
        self.boton_terminar.config(state=tk.DISABLED)
        self.status_label.config(text="Selecciona un archivo de audio a transcribir") # Volver al mensaje inicial
        self.draw_circle(self.google_status_canvas, "gray")
        self.draw_circle(self.whisper_status_canvas_circle, "gray")
        self.stop_whisper_animation()

        if self.whisper_transcription_thread and self.whisper_transcription_thread.is_alive():
            self.whisper_transcription_thread.join()

        if self.ruta_audio_pathlib and self.ruta_audio_pathlib.suffix.lower() == ".wav" and not os.path.samefile(self.ruta_audio, str(self.ruta_audio_pathlib)):
            try:
                os.remove(str(self.ruta_audio_pathlib))
            except Exception as e:
                print(f"Error al eliminar archivo WAV temporal: {e}")

        messagebox.showinfo("Información", "Transcripción finalizada.")


    def actualizar_texto_google(self, texto):
        current_text = self.area_texto_google.get("1.0", tk.END).strip()
        if current_text:
            texto_a_insertar = " " + texto
        else:
            texto_a_insertar = texto
        self.area_texto_google.insert(tk.END, texto_a_insertar)
        self.area_texto_google.see(tk.END)


    def actualizar_texto_whisper(self, texto):
        self.area_texto_whisper.delete("1.0", tk.END)
        self.area_texto_whisper.insert(tk.END, texto)
        self.area_texto_whisper.see(tk.END)


    def habilitar_botones_google(self, habilitar=True):
        state = tk.NORMAL if habilitar else tk.DISABLED
        self.boton_copiar_google.config(state=state)
        self.boton_exportar_google.config(state=state)


    def habilitar_botones_whisper(self, habilitar=True):
        state = tk.NORMAL if habilitar else tk.DISABLED
        self.boton_copiar_whisper.config(state=state)
        self.boton_exportar_whisper.config(state=state)


    def copiar_texto_google(self):
        self.ventana.clipboard_clear()
        self.ventana.clipboard_append(self.area_texto_google.get("1.0", tk.END))
        self.ventana.update()

    def exportar_texto_google(self):
        ruta_archivo = filedialog.asksaveasfilename(defaultextension=".txt", title="Guardar transcripción de Google")
        if ruta_archivo:
            texto_completo = self.area_texto_google.get("1.0", tk.END)
            with open(ruta_archivo, "w") as archivo:
                archivo.write(texto_completo)

    def copiar_texto_whisper(self):
        self.ventana.clipboard_clear()
        self.ventana.clipboard_append(self.area_texto_whisper.get("1.0", tk.END))
        self.ventana.update()

    def exportar_texto_whisper(self):
        ruta_archivo = filedialog.asksaveasfilename(defaultextension=".txt", title="Guardar transcripción de Whisper")
        if ruta_archivo:
            texto_completo = self.area_texto_whisper.get("1.0", tk.END)
            with open(ruta_archivo, "w") as archivo:
                archivo.write(texto_completo)


    def terminar_transcripcion(self):
        if self.transcripcion_en_progreso:
            self.terminar_transcripcion_flag = True
            self.reproduccion_en_curso = False
            self.boton_terminar.config(state=tk.DISABLED)
            self.boton_transcribir.config(state=tk.NORMAL, text="Transcribir")
            self.status_label.config(text="Deteniendo transcripción de Google...")
            self.draw_circle(self.google_status_canvas, "gray")
            # Whisper sigue funcionando, así que la animación y el estado se gestionan en su propio hilo
            pygame.mixer.music.stop() # Detener el audio al pulsar "Terminar"
            self.start_whisper_animation() # Asegurar que la animación de Whisper se inicie si no lo ha hecho ya
        else:
            messagebox.showinfo("Información", "No hay ninguna transcripción en curso para terminar.")


    def iniciar(self):
        self.status_label.config(text="Selecciona un archivo de audio a transcribir") # Mensaje inicial correcto
        self.draw_circle(self.google_status_canvas, "gray") # Asegurar que los círculos estén grises al inicio
        self.draw_circle(self.whisper_status_canvas_circle, "gray")
        self.stop_whisper_animation()
        self.modelo_whisper_cargado = False
        self.ventana.after(0, self.cargar_modelo_whisper) # Cargar modelo al inicio
        self.ventana.mainloop()

    def animate_whisper_status(self):
        if not self.animacion_whisper_activa:
            return

        colors = ["gray", "gray", "gray"]
        colors[self.dot_index % 3] = "yellow"
        for i, color in enumerate(colors):
            self.dots_canvas.itemconfig(f"dot{i}", fill=color)
        self.dot_index += 1
        self.animacion_whisper_id = self.ventana.after(300, self.animate_whisper_status)

    def start_whisper_animation(self):
        if not self.animacion_whisper_activa:
            self.animacion_whisper_activa = True
            self.animate_whisper_status()

    def stop_whisper_animation(self):
        if self.animacion_whisper_activa:
            self.animacion_whisper_activa = False
            if self.animacion_whisper_id:
                self.ventana.after_cancel(self.animacion_whisper_id)
                self.animacion_whisper_id = None
            # Reset dots to gray
            for i in range(3):
                self.dots_canvas.itemconfig(f"dot{i}", fill="gray")
            self.dot_index = 0

if __name__ == "__main__":
    app = AudioTranscriptorPro()
    app.iniciar()