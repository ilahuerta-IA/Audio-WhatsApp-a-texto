# Audio a Texto Pro (Whisper Edition)

Aplicación de escritorio para transcribir archivos de audio utilizando el modelo Whisper de OpenAI ejecutado localmente. Permite la selección de diferentes tamaños de modelo y ofrece un modo de "Depuración" para revisar y editar la transcripción mientras se reproduce el audio sincronizadamente.

![Screenshot](https://github.com/ilahuerta-IA/Audio-WhatsApp-a-texto/blob/main/screenshot.png)


## Características Principales

*   **Selección de Archivo:** Permite seleccionar archivos de audio en formatos comunes (MP3, WAV, OGG, FLAC, M4A...).
*   **Conversión Automática:** Convierte los archivos seleccionados a formato WAV estándar usando `ffmpeg` (requerido) para la transcripción y reproducción.
*   **Transcripción con Whisper:**
    *   Utiliza la librería `openai-whisper` para realizar la transcripción localmente.
    *   Permite seleccionar el modelo Whisper a usar (`tiny`, `base`, `small`, `medium`, `large`) a través de un menú desplegable.
    *   Muestra advertencias si se seleccionan modelos grandes (`medium`, `large`) en sistemas sin GPU detectada.
    *   Carga los modelos en un hilo separado con indicación de progreso (simulado).
*   **Interfaz Gráfica:**
    *   Muestra el estado del proceso (cargando modelo, convirtiendo audio, transcribiendo, listo, error).
    *   Muestra la transcripción resultante en un área de texto.
*   **Modo Depuración:**
    *   Se activa después de una transcripción exitosa.
    *   Permite **editar directamente** el texto transcrito en el área de texto.
    *   Incluye controles de **Play/Pause y Stop** para el audio original.
    *   **Resalta automáticamente** el segmento de texto que corresponde a la parte del audio que se está reproduciendo.
*   **Funciones de Resultado:**
    *   **Copiar** el texto transcrito al portapapeles.
    *   **Exportar** el texto transcrito a un archivo `.txt`.
*   **Comprobación de Entorno:** Informa al inicio si detecta drivers NVIDIA y si PyTorch puede usar CUDA (GPU).

## Requisitos

*   **Python:** Versión 3.9 - 3.11 recomendada.
*   **FFmpeg:** **Indispensable**. `pydub` lo necesita para cargar y convertir la mayoría de formatos de audio. Debe estar instalado en tu sistema y accesible desde el PATH. Descárgalo desde [ffmpeg.org](https://ffmpeg.org/download.html).
*   **Librerías Python:** Las dependencias principales se listan en `requirements.txt`.

## Instalación y Configuración

1.  **Clonar el Repositorio:**
    ```bash
    # Usando SSH (como lo configuraste)
    git clone git@github.com:ilahuerta-IA/Audio-WhatsApp-a-texto.git
    cd Audio-WhatsApp-a-texto
    ```
    *(Si prefieres HTTPS: `git clone https://github.com/ilahuerta-IA/Audio-WhatsApp-a-texto.git`)*

2.  **Instalar FFmpeg:** Descarga FFmpeg desde [ffmpeg.org](https://ffmpeg.org/download.html) (builds de [Gyan.dev](https://gyan.dev/ffmpeg/builds/) son recomendados para Windows). Sigue las instrucciones para tu sistema operativo y **asegúrate de añadir `ffmpeg` (y `ffprobe`) al PATH de tu sistema** para que la aplicación pueda encontrarlo. Puedes verificarlo abriendo una nueva terminal y escribiendo `ffmpeg -version`.

3.  **Crear un Entorno Virtual (Muy Recomendado):**
    ```bash
    python -m venv venv
    ```
    *   Activar en Windows (Git Bash/PowerShell): `.\venv\Scripts\activate`
    *   Activar en macOS/Linux: `source venv/bin/activate`

4.  **Instalar Dependencias Python:**
    *   **(Importante - PyTorch Primero):** Whisper depende de PyTorch. Instálalo según tu sistema y si tienes GPU NVIDIA:
        *   **Para CPU solamente:**
            ```bash
            pip install torch torchvision torchaudio
            ```
        *   **Para GPU NVIDIA (CUDA):** Visita [pytorch.org](https://pytorch.org/get-started/locally/) para obtener el comando `pip install` específico para tu versión de CUDA (ej: 11.8, 12.1). Ejemplo para CUDA 12.1:
            ```bash
            pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
            ```
    *   **Instalar el resto de dependencias:**
        ```bash
        pip install -r requirements.txt
        ```

5.  **(Linux - Opcional) Instalar Tkinter:** Si usas Linux y encuentras errores relacionados con `tkinter` o `_tkinter`, puede que necesites instalarlo a nivel de sistema:
    *   Debian/Ubuntu: `sudo apt-get update && sudo apt-get install python3-tk`
    *   Fedora: `sudo dnf install python3-tkinter`

## Uso

1.  **Activar Entorno Virtual:** (Si creaste uno) Asegúrate de tenerlo activado en tu terminal.
2.  **Navegar al Directorio:** Asegúrate de estar en la carpeta raíz del proyecto (`Audio-WhatsApp-a-texto`) en tu terminal.
3.  **Ejecutar la Aplicación:**
    ```bash
    python main.py
    ```
4.  **Seleccionar Modelo:** Elige el modelo Whisper que deseas usar en el menú desplegable. Espera a que termine la carga (la barra de progreso desaparecerá).
5.  **Seleccionar Audio:** Haz clic en "Seleccionar Audio" y elige tu archivo. Espera a que se prepare (convertido a WAV).
6.  **Transcribir:** Haz clic en "Transcribir". Observa los puntos animados y el estado.
7.  **Revisar Resultado:** Una vez completado, el texto aparecerá.
8.  **(Opcional) Depurar:**
    *   Haz clic en "Depurar". Los controles de audio aparecerán y el área de texto se volverá editable.
    *   Usa "▶ Play" / "❚❚ Pause" y "■ Stop" para controlar la reproducción.
    *   El segmento de texto correspondiente al audio que suena se resaltará en amarillo.
    *   Puedes editar el texto directamente en el área mientras pausas o detienes.
    *   Haz clic en "Salir Depurar" para volver al modo normal (el texto volverá a ser no editable).
9.  **Copiar/Exportar:** Usa los botones "Copiar Texto" o "Exportar Texto" (disponibles solo cuando no se está procesando ni depurando) para guardar tu transcripción final (incluyendo tus ediciones si depuraste).

## Estructura del Proyecto

*   `main.py`: Punto de entrada, inicializa la GUI.
*   `gui.py`: Clase principal `AudioTranscriptorPro`, maneja la interfaz, estado y orquestación.
*   `config.py`: Constantes y configuración (versión, modelos, colores, etc.).
*   `utils.py`: Funciones de utilidad (portapapeles, exportar, checks de sistema).
*   `audio_handler.py`: Selección de archivo y conversión a WAV usando `pydub`.
*   `playback.py`: Control de reproducción de audio usando `pygame`.
*   `whisper_transcriber.py`: Carga de modelo y transcripción con `openai-whisper` en hilos.
*   `requirements.txt`: Lista de dependencias Python.
*   `README.md`: Este archivo.
*   `Main_Block_Diagram.html`: Diagrama visual de la arquitectura.
*   `.gitignore`: Para ignorar archivos de entorno virtual, caché, etc.
*   `screenshot.png`: Captura de pantalla de la aplicación.

## Licencia

Este proyecto utiliza `openai-whisper` que tiene licencia MIT. El código de esta aplicación en sí mismo puede ser considerado bajo misma licencia MIT (La licencia MIT es una licencia de software libre que permite a los usuarios modificar, distribuir y usar el software sin restricciones importantes) 

