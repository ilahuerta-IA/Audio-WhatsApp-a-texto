# Audio-WhatsApp-a-texto
# Audio a Texto Pro - Transcripción Inteligente Híbrida Google/Whisper/IA

[![Versión Rev30](https://img.shields.io/badge/Versión-Rev30-blue.svg)](https://github.com/ilahuerta-IA/Audio-WhatsApp-a-texto/releases/tag/rev30)

**Audio a Texto Pro** es una aplicación de escritorio en Python diseñada para realizar **transcripciones de audio a texto de forma inteligente y mejorada**.  Combina la rapidez de **Google Speech Recognition** para la transcripción en tiempo real durante la reproducción del audio, con la precisión del modelo **Whisper de OpenAI** para una transcripción mejorada en segundo plano, y la **corrección de texto con IA mediante la API de LanguageTool** para refinar el texto final.

Esta herramienta es ideal para:

*   Transcribir **grabaciones de voz, audios de WhatsApp, podcasts, conferencias, entrevistas**, etc.
*   Obtener **transcripciones rápidas y preliminares** con Google Speech mientras el audio se reproduce.
*   Conseguir una **transcripción final más precisa y pulida** gracias a Whisper y la corrección con IA.
*   **Mejorar la calidad de las transcripciones automáticas**, corrigiendo errores ortográficos, gramaticales y de estilo.

## Características Principales

*   **Transcripción Híbrida:**
    *   **Google Speech Recognition (Tiempo Real):** Muestra la transcripción del audio en tiempo real mientras se reproduce, ideal para obtener un borrador inicial inmediato.
    *   **Whisper de OpenAI (Segundo Plano):**  Realiza una transcripción más precisa del audio completo en segundo plano utilizando el modelo Whisper "tiny" para mejorar la exactitud.
    *   **Corrección de Texto con IA (LanguageTool API):**  Aplica una fase de post-corrección al texto de Whisper utilizando la API de LanguageTool para corregir errores ortográficos, gramaticales, de acentuación y mejorar el estilo del texto final.
*   **Interfaz Gráfica Intuitiva:**  Desarrollada con Tkinter, ofrece una interfaz de usuario sencilla y fácil de usar para seleccionar archivos de audio, iniciar la transcripción, detenerla, copiar y exportar el texto.
*   **Soporte de Formatos de Audio:**  Compatible con archivos de audio en formatos **MP3, WAV, y OGG**.  Convierte automáticamente otros formatos compatibles a WAV para su procesamiento.
*   **Feedback Visual "Terminando... (Procesando IA...)":**  Indica claramente cuando la aplicación está procesando la corrección con IA al finalizar la transcripción, mejorando la experiencia del usuario.
*   **Chunking para API de IA:** Implementa segmentación del texto antes de enviarlo a la API de LanguageTool para evitar errores por tamaño excesivo de la solicitud (Error 413).
*   **Software Libre y de Código Abierto.**

## Instalación y Configuración

Sigue estos pasos para instalar y configurar **Audio a Texto Pro** en tu ordenador:

**1.  Requisitos Previos:**

    *   **Python 3.8 o superior:** Asegúrate de tener Python instalado. Puedes descargarlo desde [https://www.python.org/downloads/](https://www.python.org/downloads/). Durante la instalación, marca la opción "Add Python to PATH" para poder ejecutar Python desde la terminal.
    *   **pip (gestor de paquetes de Python):**  Normalmente se instala junto con Python. Verifica que lo tienes instalado abriendo la terminal y ejecutando: `pip --version`.  Si no está instalado, consulta la documentación oficial de Python para su instalación.
    *   **FFmpeg (opcional, pero recomendado para mejor soporte de formatos de audio):** FFmpeg es una herramienta muy útil para el procesamiento de audio y vídeo. Aunque la aplicación intentará convertir formatos de audio sin él, tener FFmpeg instalado **mejorará la compatibilidad y robustez**, especialmente para formatos como MP3.
        *   **Windows:** Puedes descargarlo desde [https://www.ffmpeg.org/download.html#build-windows](https://www.ffmpeg.org/download.html#build-windows).  Descarga la versión "Essentials" o "Full" para tu sistema operativo.  Una vez descargado, descomprime el archivo ZIP y añade la carpeta `bin` de FFmpeg a tu variable de entorno `PATH` de Windows para poder ejecutar `ffmpeg` desde la terminal. Hay muchos tutoriales online sobre cómo hacer esto, busca "añadir ffmpeg a path windows".
        *   **macOS (con Homebrew):** Si tienes Homebrew instalado, puedes instalar FFmpeg con el comando: `brew install ffmpeg`
        *   **Linux (ejemplo en Debian/Ubuntu):**  Puedes instalarlo con el comando: `sudo apt install ffmpeg`

**2.  Descargar el código fuente:**

    *   Descarga el código fuente de **Audio a Texto Pro** desde este repositorio de GitHub. Puedes hacerlo clonando el repositorio con Git (recomendado si sabes usar Git):

        ```bash
        git clone [https://github.com/ilahuerta-IA/Audio-WhatsApp-a-texto.git](https://github.com/ilahuerta-IA/Audio-WhatsApp-a-texto.git)
        ```

        O descargando el código como archivo ZIP desde la página del repositorio en GitHub y descomprimiéndolo en tu ordenador.

**3.  Crear un entorno virtual (recomendado):**

    *   Abre la terminal y navega hasta la carpeta donde descargaste el código de **Audio a Texto Pro**.
    *   Crea un entorno virtual para aislar las dependencias del proyecto:

        ```bash
        python -m venv whisper_env
        ```

    *   Activa el entorno virtual:
        *   **Windows:**  `whisper_env\Scripts\activate`
        *   **macOS y Linux:** `source whisper_env/bin/activate`

        El nombre del entorno virtual (`whisper_env` en este caso) aparecerá entre paréntesis en la línea de comandos para indicar que está activado.

**4.  Instalar las dependencias de Python:**

    *   Con el entorno virtual activado, ejecuta el siguiente comando para instalar las bibliotecas Python necesarias:

        ```bash
        pip install -r requirements.txt
        ```

        Este comando instalará las bibliotecas listadas en el archivo `requirements.txt` que se encuentra en el repositorio, incluyendo:
        *   `SpeechRecognition`
        *   `PyDub`
        *   `pygame`
        *   `whisper-openai`
        *   `requests`
        *   `tkinter` (normalmente ya viene preinstalado con Python, pero se incluye por si acaso)
        *   `wheel` (necesario para la instalación de Whisper en algunos sistemas)

**5.  Ejecutar la aplicación:**

    *   Asegúrate de que el entorno virtual `whisper_env` está activado.
    *   Navega hasta la carpeta del proyecto (si no estás ya en ella).
    *   Ejecuta la aplicación con el comando:

        ```bash
        python Audio_a_Texto_Pro.py
        ```

        O si has renombrado el archivo a `Audio_a_Texto_Pro_rev30.py`:

        ```bash
        python Audio_a_Texto_Pro_rev30.py
        ```

    La ventana de **Audio a Texto Pro** debería aparecer en tu pantalla, lista para transcribir tus archivos de audio.

## Estructura del Código

El código principal de la aplicación se encuentra en el archivo `Audio_a_Texto_Pro.py` (o `Audio_a_Texto_Pro_rev30.py` en la última versión).  Las principales partes del código son:

*   **Importaciones de bibliotecas:** Se importan las bibliotecas necesarias para la interfaz gráfica (Tkinter), procesamiento de audio (PyDub, SpeechRecognition, Whisper, Pygame) y llamadas a la API (requests, json).
*   **Clase `AudioTranscriptorPro`:**  Encapsula la lógica principal de la aplicación y la interfaz gráfica.
    *   **`__init__`:** Inicializa la ventana principal, la interfaz gráfica, variables y carga el modelo Whisper en segundo plano.
    *   **`seleccionar_audio`:** Permite al usuario seleccionar un archivo de audio y prepara la aplicación para la transcripción.
    *   **`transcribir_audio`:** Inicia el proceso de transcripción, lanzando hilos para la transcripción con Google Speech (en tiempo real) y Whisper (en segundo plano).
    *   **`reproducir_y_transcribir_google_speech`:**  Reproduce el audio en segmentos y utiliza Google Speech Recognition para la transcripción en tiempo real.
    *   **`transcribir_audio_whisper_background`:** Realiza la transcripción del audio completo en segundo plano utilizando el modelo Whisper.
    *   **`finalizar_transcripcion`:**  Se ejecuta al finalizar la transcripción (ya sea al terminar el audio o al pulsar "Terminar").  Inicia la corrección con IA, espera a que Whisper termine y muestra el texto final mejorado.
    *   **`corregir_texto_con_ia`:**  Implementa la lógica para enviar el texto de Whisper a la API de LanguageTool, segmentando el texto ("chunking") para evitar errores por tamaño excesivo, y aplica las correcciones recibidas de la API.
    *   **`mostrar_mensaje_terminando_procesando_ia` / `ocultar_mensaje_procesando_ia_y_mostrar_texto_final`:**  Controlan el feedback visual "Terminando... (Procesando IA...)" durante la corrección con IA.
    *   **Funciones auxiliares:**  `actualizar_texto`, `habilitar_botones`, `copiar_texto`, `exportar_texto`, `terminar_transcripcion`, `cargar_modelo_whisper`, etc., gestionan la interfaz de usuario, el control de la transcripción y otras tareas.
    *   **`iniciar`:** Inicia el bucle principal de la aplicación Tkinter.
*   **Bloque `if __name__ == "__main__":`:**  Crea una instancia de la clase `AudioTranscriptorPro` y ejecuta la aplicación al iniciar el script.
*   **Archivo `requirements.txt`:**  Lista las bibliotecas Python necesarias para el proyecto.

## Uso Básico

1.  **Seleccionar Audio:**  Pulsa el botón "Seleccionar Audio" y elige el archivo de audio que deseas transcribir (MP3, WAV, OGG).
2.  **Transcribir:** Pulsa el botón "Transcribir". La reproducción del audio comenzará y la transcripción con Google Speech aparecerá en tiempo real en el área de texto.
3.  **Terminar (Opcional):** Si deseas detener la transcripción antes de que termine el audio, pulsa el botón "Terminar".  Si dejas que el audio se reproduzca completo, la transcripción finalizará automáticamente al terminar el audio.
4.  **Esperar el Texto Final Mejorado:**  Después de pulsar "Terminar" (o al finalizar el audio), espera unos segundos mientras la aplicación procesa la transcripción con Whisper y la corrección con IA.  Verás el mensaje "Terminando... (Procesando IA...)" en el botón "Transcribir".
5.  **Texto Final:**  Una vez que el procesamiento de IA termine, el área de texto se actualizará para mostrar el texto final, que será la transcripción de Whisper mejorada con la corrección de LanguageTool API.
6.  **Copiar o Exportar:**  Utiliza los botones "Copiar Texto" para copiar el texto al portapapeles o "Exportar a TXT" para guardar el texto en un archivo TXT.

## Limitaciones y Posibles Mejoras

*   **Dependencia de la API de LanguageTool:** La calidad de la corrección con IA depende de la disponibilidad y calidad de la API de LanguageTool (versión "Plus" en esta versión).  En caso de problemas con la API, la aplicación mostrará el texto de Whisper sin corregir (o incluso el texto de Google Speech como último recurso).
*   **Modelo Whisper "tiny":** Se utiliza el modelo "tiny" de Whisper para mantener la aplicación ligera y con bajos requisitos de recursos.  Modelos más grandes de Whisper ("small", "medium", "large") ofrecen mayor precisión pero requieren más recursos y tiempo de procesamiento.  En futuras versiones se podría permitir al usuario elegir el modelo de Whisper.
*   **Estrategia de corrección de IA básica:** La aplicación utiliza una estrategia de corrección simple al aplicar las sugerencias de la API de LanguageTool (reemplazo directo de la primera sugerencia).  Se podrían explorar estrategias más sofisticadas para la aplicación de correcciones en el futuro.
*   **Idioma Español:**  Actualmente la aplicación está configurada para transcribir y corregir en español (`language='es'` en Whisper y LanguageTool API).  Se podría añadir la opción de seleccionar el idioma en la interfaz de usuario en versiones futuras.
*   **Errores en Transcripciones Automáticas:**  A pesar de las mejoras con Whisper y la IA, las transcripciones automáticas nunca son perfectas.  Es posible que se sigan produciendo errores, especialmente en audios con ruido, mala calidad de sonido o acentos muy marcados.  Siempre es recomendable revisar y editar el texto final para asegurar la máxima precisión.

## Licencia

[Aquí podrías añadir información sobre la licencia de tu proyecto, por ejemplo, si es MIT License, GPL, etc. Si no vas a usar una licencia específica, puedes indicar algo como "Uso libre para fines personales y no comerciales. Para uso comercial, contactar con el autor."]

## Contacto

[Aquí puedes añadir tu información de contacto, por ejemplo, tu correo electrónico o perfil de GitHub, si quieres que te contacten para comentarios, sugerencias o contribuciones.]

---

¡Espero que esta descripción de `README.md` te sea útil! Puedes copiar y pegar este texto en un archivo llamado `README.md` en la raíz de tu repositorio de GitHub.  Puedes ajustarlo y mejorarlo según lo consideres necesario. ¡Mucha suerte con tu proyecto!
