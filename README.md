# Audio-WhatsApp-a-texto
# Audio a Texto Pro - Transcripción Inteligente Híbrida Google/Whisper

[![Versión Rev37](https://img.shields.io/badge/Versión-Rev37-blue.svg)](https://github.com/ilahuerta-IA/Audio-WhatsApp-a-texto/releases/tag/rev37)

**Audio a Texto Pro** es una aplicación de escritorio en Python diseñada para realizar **transcripciones de audio a texto de forma inteligente y mejorada**.  Combina la rapidez de **Google Speech Recognition** para la transcripción en tiempo real durante la reproducción del audio, con la precisión del modelo **Whisper de OpenAI** para una transcripción mejorada en segundo plano.

Esta herramienta es ideal para:

* Transcribir **grabaciones de voz, audios de WhatsApp, podcasts, conferencias, entrevistas**, etc.
* Obtener **transcripciones rápidas y preliminares** con Google Speech mientras el audio se reproduce.
* Conseguir una **transcripción final más precisa** gracias a Whisper.
* **Comparar las transcripciones** generadas por Google Speech y Whisper.

## Características Principales

* **Transcripción Híbrida:**
    * **Google Speech Recognition (Tiempo Real):** Muestra la transcripción del audio en tiempo real mientras se reproduce, ideal para obtener un borrador inicial inmediato.
    * **Whisper de OpenAI (Segundo Plano):** Realiza una transcripción más precisa del audio completo en segundo plano utilizando el modelo Whisper "tiny" para mejorar la exactitud.
* **Interfaz Gráfica Intuitiva:** Desarrollada con Tkinter, ofrece una interfaz de usuario sencilla y fácil de usar para seleccionar archivos de audio, iniciar la transcripción, detener la transcripción de Google (sin interrumpir Whisper), copiar y exportar el texto de ambas transcripciones.
* **Soporte de Formatos de Audio:** Compatible con archivos de audio en formatos **MP3, WAV, y OGG**.  Convierte automáticamente otros formatos compatibles a WAV para su procesamiento.
* **Indicador de Estado:** Muestra el estado de la transcripción de Google y Whisper con indicadores visuales.
* **Animación de Actividad Whisper:** Incorpora una animación visual para indicar que Whisper está procesando la transcripción en segundo plano.
* **Whisper Continúa al Terminar:** Al pulsar el botón "Terminar", solo se detiene la transcripción de Google; Whisper continúa transcribiendo el audio completo en segundo plano.
* **Software Libre y de Código Abierto.**

## Instalación y Configuración

Sigue estos pasos para instalar y configurar **Audio a Texto Pro** en tu ordenador:

**1.  Requisitos Previos:**

    * **Python 3.8 o superior:** Asegúrate de tener Python instalado. Puedes descargarlo desde [https://www.python.org/downloads/](https://www.python.org/downloads/). Durante la instalación, marca la opción "Add Python to PATH" para poder ejecutar Python desde la terminal.
    * **pip (gestor de paquetes de Python):** Normalmente se instala junto con Python. Verifica que lo tienes instalado abriendo la terminal y ejecutando: `pip --version`.  Si no está instalado, consulta la documentación oficial de Python para su instalación.
    * **FFmpeg (opcional, pero recomendado para mejor soporte de formatos de audio):** FFmpeg es una herramienta muy útil para el procesamiento de audio y vídeo. Aunque la aplicación intentará convertir formatos de audio sin él, tener FFmpeg instalado **mejorará la compatibilidad y robustez**, especialmente para formatos como MP3.
        * **Windows:** Puedes descargarlo desde [https://www.ffmpeg.org/download.html#build-windows](https://www.ffmpeg.org/download.html#build-windows).  Descarga la versión "Essentials" o "Full" para tu sistema operativo.  Una vez descargado, descomprime el archivo ZIP y añade la carpeta `bin` de FFmpeg a tu variable de entorno `PATH` de Windows para poder ejecutar `ffmpeg` desde la terminal. Hay muchos tutoriales online sobre cómo hacer esto, busca "añadir ffmpeg a path windows".
        * **macOS (con Homebrew):** Si tienes Homebrew instalado, puedes instalar FFmpeg con el comando: `brew install ffmpeg`
        * **Linux (ejemplo en Debian/Ubuntu):** Puedes instalarlo con el comando: `sudo apt install ffmpeg`

**2.  Descargar el código fuente:**

    * Descarga el código fuente de **Audio a Texto Pro** desde este repositorio de GitHub. Puedes hacerlo clonando el repositorio con Git (recomendado si sabes usar Git):

        ```bash
        git clone [https://github.com/ilahuerta-IA/Audio-WhatsApp-a-texto.git](https://github.com/ilahuerta-IA/Audio-WhatsApp-a-texto.git)
        ```

        O descargando el código como archivo ZIP desde la página del repositorio en GitHub y descomprimiéndolo en tu ordenador.

**3.  Crear un entorno virtual (recomendado):**

    * Abre la terminal y navega hasta la carpeta donde descargaste el código de **Audio a Texto Pro**.
    * Crea un entorno virtual para aislar las dependencias del proyecto:

        ```bash
        python -m venv whisper_env
        ```

    * Activa el entorno virtual:
        * **Windows:** `whisper_env\Scripts\activate`
        * **macOS y Linux:** `source whisper_env/bin/activate`

        El nombre del entorno virtual (`whisper_env` en este caso) aparecerá entre paréntesis en la línea de comandos para indicar que está activado.

**4.  Instalar las dependencias de Python:**

    * Con el entorno virtual activado, ejecuta el siguiente comando para instalar las bibliotecas Python necesarias:

        ```bash
        pip install -r requirements.txt
        ```

        Este comando instalará las bibliotecas listadas en el archivo `requirements.txt` que se encuentra en el repositorio, incluyendo:
        * `SpeechRecognition`
        * `PyDub`
        * `pygame`
        * `openai-whisper`
        * `tkinter` (normalmente ya viene preinstalado con Python, pero se incluye por si acaso)
        * `wheel` (necesario para la instalación de Whisper en algunos sistemas)

**5.  Ejecutar la aplicación:**

    * Asegúrate de que el entorno virtual `whisper_env` está activado.
    * Navega hasta la carpeta del proyecto (si no estás ya en ella).
    * Ejecuta la aplicación con el comando:

        ```bash
        python Audio_a_Texto_rev37.py
        ```

    La ventana de **Audio a Texto Pro** debería aparecer en tu pantalla, lista para transcribir tus archivos de audio.

## Estructura del Código

El código principal de la aplicación se encuentra en el archivo `Audio_a_Texto_rev37.py`. Las principales partes del código son:

* **Importaciones de bibliotecas:** Se importan las bibliotecas necesarias para la interfaz gráfica (Tkinter), procesamiento de audio (PyDub, SpeechRecognition, Whisper, Pygame).
* **Clase `AudioTranscriptorPro`:** Encapsula la lógica principal de la aplicación y la interfaz gráfica.
    * **`__init__`:** Inicializa la ventana principal, la interfaz gráfica, variables y carga el modelo Whisper en segundo plano.
    * **`seleccionar_audio`:** Permite al usuario seleccionar un archivo de audio y prepara la aplicación para la transcripción.
    * **`transcribir_audio`:** Inicia el proceso de transcripción, lanzando hilos para la transcripción con Google Speech (en tiempo real) y Whisper (en segundo plano).
    * **`transcribir_audio_google_speech`:** Reproduce el audio en segmentos y utiliza Google Speech Recognition para la transcripción en tiempo real.
    * **`transcribir_audio_whisper_background`:** Realiza la transcripción del audio completo en segundo plano utilizando el modelo Whisper.
    * **`finalizar_transcripcion`:** Se ejecuta al finalizar la transcripción (ya sea al terminar el audio o al pulsar "Terminar"). Detiene la transcripción de Google y permite que Whisper continúe.
    * **Funciones auxiliares:** `actualizar_texto_google`, `actualizar_texto_whisper`, `habilitar_botones_google`, `habilitar_botones_whisper`, `copiar_texto_google`, `exportar_texto_google`, `copiar_texto_whisper`, `exportar_texto_whisper`, `terminar_transcripcion`, `cargar_modelo_whisper`, `animate_whisper_status`, `start_whisper_animation`, `stop_whisper_animation`, `draw_circle`, etc., gestionan la interfaz de usuario, el control de la transcripción y otras tareas.
    * **`iniciar`:** Inicia el bucle principal de la aplicación Tkinter.
* **Bloque `if __name__ == "__main__":`:** Crea una instancia de la clase `AudioTranscriptorPro` y ejecuta la aplicación al iniciar el script.
* **Archivo `requirements.txt`:** Lista las bibliotecas Python necesarias para el proyecto.

## Uso Básico

1.  **Seleccionar Audio:** Pulsa el botón "Seleccionar Audio" y elige el archivo de audio que deseas transcribir (MP3, WAV, OGG).
2.  **Transcribir:** Pulsa el botón "Transcribir". La reproducción del audio comenzará y la transcripción con Google Speech aparecerá en tiempo real en el área de texto correspondiente.
3.  **Terminar (Opcional):** Si deseas detener la transcripción de Google antes de que termine el audio, pulsa el botón "Terminar". Whisper continuará transcribiendo en segundo plano.
4.  **Esperar la Transcripción de Whisper:** Una vez que Whisper termine de procesar el audio, su transcripción aparecerá en el área de texto correspondiente. Puedes observar la animación de los tres puntos debajo del mensaje de estado mientras Whisper está trabajando.
5.  **Texto Final:** Una vez que ambas transcripciones estén completas, podrás comparar los resultados.
6.  **Copiar o Exportar:** Utiliza los botones "Copiar Texto Google", "Exportar a TXT Google", "Copiar Texto Whisper" y "Exportar a TXT Whisper" para gestionar las transcripciones.

## Limitaciones y Posibles Mejoras

* **Modelo Whisper "tiny":** Se utiliza el modelo "tiny" de Whisper para mantener la aplicación ligera y con bajos requisitos de recursos. Modelos más grandes de Whisper ("small", "medium", "large") ofrecen mayor precisión pero requieren más recursos y tiempo de procesamiento. En futuras versiones se podría permitir al usuario elegir el modelo de Whisper.
* **Idioma Español:** Actualmente la aplicación está configurada para transcribir en español (`language='es'` en Whisper). Se podría añadir la opción de seleccionar el idioma en la interfaz de usuario en versiones futuras.
* **Errores en Transcripciones Automáticas:** A pesar de las mejoras con Whisper, las transcripciones automáticas nunca son perfectas. Es posible que se sigan produciendo errores, especialmente en audios con ruido, mala calidad de sonido o acentos muy marcados. Siempre es recomendable revisar y editar el texto final para asegurar la máxima precisión.
* **Posible Integración Futura con IA para Corrección:** En futuras versiones, se podría reintroducir la corrección de texto con IA utilizando APIs como LanguageTool u otras alternativas para mejorar aún más la calidad de las transcripciones.

## Licencia

Uso libre para fines personales y no comerciales. Para uso comercial, contactar con el autor.


---
