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

__version__ = "rev28"  # Control de revisión: Fusión Google Speech + Whisper (mejora tras "Terminar")


class AudioTranscriptorPro:

    def __init__(self):
        self.ventana = tk.Tk()
        self.ventana.title(
            f"Audio a Texto Pro - Transcripción Inteligente ({__version__}) - Híbrido Google/Whisper") # Título indica versión Híbrida
        self.ventana.wm_title("Audio a Texto Pro - Transcripción Inteligente (Híbrido Google/Whisper)") # Título ventana
        self.ruta_audio = ""
        self.texto_transcripcion_google = "" # Texto inicial Google Speech (rev28 - Texto Google separado)
        self.texto_transcripcion_whisper = "" # Texto mejorado Whisper (rev28 - Texto Whisper separado)
        self.reproduciendo = False
        self.reconocedor = sr.Recognizer()
        pygame.mixer.init()
        self.audio_segment = None
        self.tiempo_inicio_pausa = 0
        self.transcripcion_en_progreso = False
        self.reproduccion_en_curso = False
        self.terminar_transcripcion_flag = False
        self.whisper_model = None  # Inicializar modelo Whisper
        self.modelo_whisper_cargado = False # Flag carga modelo Whisper
        self.ruta_audio_pathlib = None
        self.whisper_transcription_thread = None # Hilo para transcripción Whisper en segundo plano (rev28)
        self.whisper_transcription_ready = False # Flag para indicar que transcripción Whisper está lista (rev28)


        # --- Interfaz Gráfica (sin cambios) ---
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


        self.area_texto = scrolledtext.ScrolledText(self.ventana,
                                                    wrap=tk.WORD,
                                                    font=("TkTextFont", 12),
                                                    height=15,
                                                    padx=10, pady=10,
                                                    borderwidth=2, relief=tk.SOLID)
        self.area_texto.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        self.area_texto.config(state=tk.NORMAL)


        frame_botones_texto = tk.Frame(self.ventana, bg='#f0f0f0')
        frame_botones_texto.pack(pady=10)

        self.boton_copiar = tk.Button(frame_botones_texto,
                                                text="Copiar Texto",
                                                command=self.copiar_texto,
                                                state=tk.DISABLED,
                                                padx=15, pady=8)
        self.boton_copiar.pack(side=tk.LEFT, padx=5)

        self.boton_exportar = tk.Button(frame_botones_texto,
                                                text="Exportar a TXT",
                                                command=self.exportar_texto,
                                                state=tk.DISABLED,
                                                padx=15, pady=8)
        self.boton_exportar.pack(side=tk.LEFT, padx=5)


    def seleccionar_audio(self): # Sin cambios
        self.ruta_audio = filedialog.askopenfilename(
            defaultextension=".mp3",
            filetypes=[("Archivos de audio", "*.mp3 *.wav *.ogg"),
                       ("Todos los archivos", "*.*")])
        if self.ruta_audio:
            self.area_texto.delete("1.0", tk.END)
            self.texto_transcripcion_google = "" # Limpiar texto Google al seleccionar nuevo audio (rev28)
            self.texto_transcripcion_whisper = "" # Limpiar texto Whisper (rev28)
            self.ruta_audio_pathlib = pathlib.Path(self.ruta_audio)

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
                f"Audio a Texto Pro - {nombre_archivo} ({__version__}) - Híbrido Google/Whisper") # Título híbrido


    def transcribir_audio(self): # Modificado para iniciar HILO WHISPER en SEGUNDO PLANO (rev28)
        if not self.ruta_audio:
            messagebox.showinfo("Información", "Por favor, selecciona un archivo de audio primero.")
            return

        if not self.transcripcion_en_progreso:
            self.transcripcion_en_progreso = True
            self.reproduccion_en_curso = True
            self.terminar_transcripcion_flag = False
            self.boton_transcribir.config(state=tk.DISABLED, text="Transcribiendo...")
            self.boton_terminar.config(state=tk.NORMAL)
            self.texto_transcripcion_google = "" # Reiniciar texto Google al iniciar transcripción (rev28)
            self.texto_transcripcion_whisper = "" # Reiniciar texto Whisper al iniciar (rev28)
            self.area_texto.delete("1.0", tk.END) # Limpiar area texto al iniciar (rev28)

            # --- Iniciar HILO para transcripción con GOOGLE SPEECH RECOGNITION (Tiempo real) ---
            threading.Thread(target=self.reproducir_y_transcribir_google_speech).start() # Iniciar hilo Google Speech (rev28)

            # --- Iniciar HILO para transcripción con WHISPER (Segundo plano - Mejora) ---
            if not self.modelo_whisper_cargado: # Cargar modelo Whisper si no está cargado
                self.cargar_modelo_whisper() # Cargar modelo Whisper (rev28)
            else: # Modelo Whisper ya cargado, iniciar transcripción en hilo
                self.iniciar_transcripcion_whisper_hilo() # Iniciar hilo transcripción Whisper (rev28)


    def cargar_modelo_whisper(self): # Carga modelo Whisper en hilo (rev28)
        threading.Thread(target=self._cargar_modelo_whisper_thread).start()


    def _cargar_modelo_whisper_thread(self): # Hilo interno carga modelo Whisper (rev28)
        try:
            self.whisper_model = whisper.load_model("tiny") # Cargar modelo Whisper "tiny"
            self.modelo_whisper_cargado = True
            self.iniciar_transcripcion_whisper_hilo() # Iniciar hilo transcripción Whisper DESPUÉS de cargar modelo (rev28)
        except Exception as e:
            print(f"Error al cargar modelo Whisper: {e}")
            self.ventana.after(0, lambda: messagebox.showerror("Error", f"Error al cargar modelo Whisper: {e}"))
            self.ventana.after(0, self.finalizar_transcripcion)


    def iniciar_transcripcion_whisper_hilo(self): # Iniciar hilo transcripción Whisper (rev28)
        self.whisper_transcription_ready = False # Reiniciar flag antes de iniciar hilo Whisper (rev28)
        self.whisper_transcription_thread = threading.Thread(target=self.transcribir_audio_whisper_background) # Crear hilo Whisper (rev28)
        self.whisper_transcription_thread.start() # Iniciar hilo Whisper (rev28)


    def transcribir_audio_whisper_background(self): # Transcripción Whisper en SEGUNDO PLANO (rev28)
        try:
            if not self.ruta_audio_pathlib: # Comprobación ruta de audio (rev28 - Seguridad)
                raise ValueError("Ruta de archivo de audio no válida para Whisper.") # Error si no hay ruta (rev28)

            # Transcribir audio COMPLETO con Whisper en segundo plano
            texto_whisper_completo = self.whisper_model.transcribe(str(self.ruta_audio_pathlib), language="es", initial_prompt="Transcripción en español.") # Transcribir audio completo (rev28)
            self.texto_transcripcion_whisper = texto_whisper_completo["text"] # Guardar texto Whisper completo (rev28)
            self.whisper_transcription_ready = True # Indicar que transcripción Whisper está lista (rev28)
            print("Transcripción con Whisper en segundo plano COMPLETA.") # Mensaje de finalización Whisper (rev28 - Opcional)

        except Exception as whisper_error: # Capturar errores Whisper
            print(f"Error en transcripción con Whisper (segundo plano): {whisper_error}") # Error Whisper (rev28)
            self.texto_transcripcion_whisper = "Error en transcripción con Whisper." # Mensaje error en texto Whisper (rev28)
            self.whisper_transcription_ready = True # Indicar como "lista" aunque haya error para finalizar proceso (rev28)


    def reproducir_y_transcribir_google_speech(self): # Transcripción GOOGLE SPEECH RECOGNITION (Tiempo real - rev28)
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

            pygame.mixer.music.load(self.audio_segment.export(format="wav"))
            pygame.mixer.music.play()

            segment_duration_ms = 30000  # Segmentos de 30 segundos


            while inicio_segmento < tiempo_audio and  self.reproduccion_en_curso and self.transcripcion_en_progreso and not self.terminar_transcripcion_flag:
                fin_segmento = min(inicio_segmento + segment_duration_ms, tiempo_audio)
                segmento = self.audio_segment[inicio_segmento:fin_segmento]

                # Exportar segmento a un archivo WAV temporal en memoria
                temp_wav_buffer = segmento.export(format="wav")

                with sr.AudioFile(temp_wav_buffer) as fuente:
                    audio_data = self.reconocedor.record(fuente)
                    start_time = time.time()
                    try:
                        texto_google = self.reconocedor.recognize_google( # Transcripción con Google Speech Recognition (rev28 - Variable texto_google)
                            audio_data, language="es-ES")
                        end_time = time.time()
                        transcription_time = end_time - start_time

                        segment_playback_duration_ms = len(segmento)
                        sleep_duration_s = (segment_playback_duration_ms / 1000) - transcription_time
                        if sleep_duration_s < 0:
                            sleep_duration_s = 0

                        self.texto_transcripcion_google += " " + texto_google # Acumular texto de Google Speech (rev28 - Acumular en variable separada)
                        self.ventana.after(0, self.actualizar_texto, texto_google) # Actualizar texto con texto de Google (rev28 - Mostrar texto Google en tiempo real)
                        if not self.boton_copiar["state"] == tk.NORMAL:
                            self.ventana.after(0, self.habilitar_botones)

                    except sr.UnknownValueError:
                        print("No se pudo entender este segmento de audio.")
                        sleep_duration_s = segment_duration_ms / 1000
                    except sr.RequestError as e:
                        print(
                            "Error en la solicitud al servicio de reconocimiento de voz: {e}"
                        )
                        sleep_duration_s = segment_duration_ms / 1000

                    sleep_delay_ms = int(sleep_duration_s * 1000)
                    if sleep_delay_ms > 0:
                        time.sleep(sleep_duration_s)

                inicio_segmento = fin_segmento

            self.ventana.after(0, self.finalizar_transcripcion)


        except Exception as e:
            print(f"Error en transcripción (Google Speech): {e}") # Mensaje de error específico Google Speech
            self.ventana.after(
                0,
                lambda: messagebox.showerror("Error",
                                                 f"Error al reproducir o transcribir (Google):\n{e}" # Error específico Google en mensaje
                                                 ))
            self.ventana.after(0, self.finalizar_transcripcion)



    def finalizar_transcripcion(self): # Modificado para MOSTRAR TEXTO WHISPER al finalizar (rev28)
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
        # self.label_info.config(text="Transcripción finalizada.")

        # --- Esperar a que la transcripción de Whisper en segundo plano termine ---
        print("Esperando a que termine la transcripción de Whisper en segundo plano...") # Mensaje de espera Whisper (rev28 - Opcional)
        if self.whisper_transcription_thread and self.whisper_transcription_thread.is_alive(): # Comprobar si hilo Whisper sigue vivo (rev28 - Seguridad)
            self.whisper_transcription_thread.join() # Esperar a que hilo Whisper termine (rev28 - Sincronización)
        print("Transcripción de Whisper en segundo plano finalizada. Actualizando texto.") # Mensaje fin espera Whisper (rev28 - Opcional)


        # --- Actualizar el área de texto con la transcripción de WHISPER ---
        if self.whisper_transcription_ready: # Comprobar si la transcripción de Whisper está lista (rev28 - Seguridad)
            texto_final = self.texto_transcripcion_whisper # Usar texto Whisper como texto final (rev28 - TEXTO FINAL = WHISPER)
            self.area_texto.delete("1.0", tk.END) # Limpiar area de texto (rev28)
            self.actualizar_texto(texto_final) # Mostrar texto Whisper en area texto (rev28 - TEXTO FINAL WHISPER)
        else: # Si Whisper NO está listo (ej. error), mostrar texto de Google Speech
            texto_final = self.texto_transcripcion_google # Usar texto Google Speech si Whisper no está listo (rev28 - Fallback Google)
            print("¡¡¡ATENCIÓN!!!: No se pudo usar transcripción de Whisper. Mostrando texto de Google Speech.") # Advertencia error Whisper (rev28)
            self.area_texto.delete("1.0", tk.END) # Limpiar area texto (rev28)
            self.actualizar_texto(texto_final) # Mostrar texto Google Speech (rev28 - Fallback GOOGLE)


        self.texto_transcripcion_google = "" # Reiniciar texto Google (rev28 - Limpieza)
        self.texto_transcripcion_whisper = "" # Reiniciar texto Whisper (rev28 - Limpieza)
        self.whisper_transcription_ready = False # Reiniciar flag Whisper (rev28 - Limpieza)
        self.whisper_transcription_thread = None # Reiniciar hilo Whisper (rev28 - Limpieza)


        if self.ruta_audio_pathlib and self.ruta_audio_pathlib.suffix.lower(
        ) == ".wav" and not os.path.samefile(self.ruta_audio,
                                                str(self.ruta_audio_pathlib)):
            try:
                os.remove(str(self.ruta_audio_pathlib))
            except Exception as e:
                print(f"Error al eliminar archivo WAV temporal: {e}")

        messagebox.showinfo("Información",
                                "Transcripción finalizada. Texto mejorado con Whisper (si disponible).") # Mensaje fin con info Whisper (rev28)


    def actualizar_texto(self, texto): # Sin cambios
        current_text = self.area_texto.get("1.0", tk.END).strip()
        if current_text:
            texto_a_insertar = " " + texto
        else:
            texto_a_insertar = texto
        self.area_texto.insert(tk.END, texto_a_insertar)
        self.area_texto.see(tk.END)


    def habilitar_botones(self): # Sin cambios
        self.boton_copiar.config(state=tk.NORMAL)
        self.boton_exportar.config(state=tk.NORMAL)


    def copiar_texto(self): # Sin cambios
        self.ventana.clipboard_clear()
        self.ventana.clipboard_append(self.area_texto.get("1.0", tk.END))
        self.ventana.update()

    def exportar_texto(self): # Sin cambios
        ruta_archivo = filedialog.asksaveasfilename(defaultextension=".txt")
        if ruta_archivo:
            texto_completo = self.area_texto.get("1.0", tk.END)
            with open(ruta_archivo, "w") as archivo:
                archivo.write(texto_completo)


    def terminar_transcripcion(self): # Sin cambios
        self.terminar_transcripcion_flag = True
        self.reproduccion_en_curso = False
        self.boton_terminar.config(state=tk.DISABLED)
        self.boton_transcribir.config(state=tk.NORMAL, text="Transcribir")
        # self.label_info.config(text="Transcripción terminada por el usuario.")


    def iniciar(self): # Cargar modelo Whisper al inicio (rev28)
        self.modelo_whisper_cargado = False # Asegurar flag en False al inicio (rev28)
        self.ventana.after(0, self.cargar_modelo_whisper) # Iniciar carga modelo Whisper al inicio (rev28)
        self.ventana.mainloop()


if __name__ == "__main__":
    app = AudioTranscriptorPro()
    app.iniciar()