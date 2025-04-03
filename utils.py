# utils.py
"""Funciones de utilidad para la GUI y manejo de archivos."""

import subprocess
import platform
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import config

try:
    import torch
except ImportError:
    # Si PyTorch no está instalado, definimos un placeholder
    # para que el resto del código no falle al intentar llamar a check_pytorch_cuda
    print("ADVERTENCIA: PyTorch no está instalado. Funcionalidad GPU no disponible.")
    torch = None # Definir torch como None

def draw_status_circle(canvas: tk.Canvas, color: str):
    """Dibuja un círculo de estado en el canvas especificado."""
    canvas.delete("circle")
    canvas.create_oval(0, 0, 10, 10, fill=color, tags="circle")

def copy_to_clipboard(window: tk.Tk, text: str):
    """Copia el texto proporcionado al portapapeles."""
    if not text:
        print("Intento de copiar texto vacío.")
        return
    try:
        window.clipboard_clear()
        window.clipboard_append(text.strip())
        window.update() # Necesario para que funcione inmediatamente
        print("Texto copiado al portapapeles.")
    except Exception as e:
        print(f"Error al copiar al portapapeles: {e}")
        messagebox.showwarning("Copiar Error", f"No se pudo copiar el texto:\n{e}")


def export_text_to_file(text: str, title: str):
    """Abre un diálogo para guardar el texto en un archivo .txt."""
    if not text:
        messagebox.showwarning("Exportar Error", "No hay texto para exportar.")
        return
    ruta_archivo = filedialog.asksaveasfilename(
        defaultextension=".txt",
        title=title,
        filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")]
    )
    if ruta_archivo:
        try:
            with open(ruta_archivo, "w", encoding='utf-8') as archivo:
                archivo.write(text)
            print(f"Texto exportado a {ruta_archivo}")
            messagebox.showinfo("Exportación Exitosa", f"Archivo guardado en:\n{ruta_archivo}")
        except Exception as e:
            print(f"Error al exportar a TXT: {e}")
            messagebox.showerror("Error de Exportación", f"No se pudo guardar el archivo:\n{e}")

def check_nvidia_smi():
    """
    Verifica si el comando 'nvidia-smi' se puede ejecutar correctamente.

    Returns:
        bool: True si 'nvidia-smi' se ejecuta con éxito (código de retorno 0),
              False en caso contrario.
    """
    command = "nvidia-smi"
    try:
        # Configuración para ocultar ventana en Windows y capturar salida
        startupinfo = None
        creationflags = 0
        if platform.system() == "Windows":
            # Importar solo si es Windows para evitar dependencia innecesaria
            import subprocess
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE # Ocultar ventana
            creationflags = subprocess.CREATE_NO_WINDOW

        # Ejecutar el comando
        subprocess.run(
            [command],
            check=True, # Lanza excepción si el comando falla (return code != 0)
            stdout=subprocess.PIPE, # Capturar salida estándar
            stderr=subprocess.PIPE, # Capturar salida de error
            startupinfo=startupinfo, # Aplicar si es Windows
            creationflags=creationflags # Aplicar si es Windows
        )
        print("INFO: Comando 'nvidia-smi' encontrado y ejecutado con éxito.")
        return True
    except FileNotFoundError:
        print("WARN: Comando 'nvidia-smi' no encontrado. Asegúrate de que los drivers NVIDIA están instalados y en el PATH.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"WARN: Comando 'nvidia-smi' encontrado pero falló al ejecutarse (Código: {e.returncode}). Drivers podrían no estar funcionales.")
        return False
    except Exception as e:
        print(f"ERROR: Ocurrió un error inesperado al intentar ejecutar 'nvidia-smi': {e}")
        return False

def check_pytorch_cuda():
    """
    Verifica si PyTorch detecta una GPU CUDA disponible y utilizable.

    Esta es la comprobación definitiva para saber si se puede usar 'cuda'.

    Returns:
        bool: True si torch.cuda.is_available() devuelve True, False en caso contrario
              (incluyendo si PyTorch no está instalado o hay errores).
    """
    if torch is None:
        print("INFO: Verificación PyTorch CUDA omitida (PyTorch no importado).")
        return False # No se puede usar CUDA si torch no está

    try:
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            gpu_name = torch.cuda.get_device_name(0) # Obtener nombre de la GPU 0
            print(f"INFO: PyTorch detecta CUDA disponible. GPU: {gpu_name}")
        else:
            print("INFO: PyTorch NO detecta CUDA disponible (usará CPU).")
        return cuda_available
    except Exception as e:
        # Capturar otros posibles errores durante la comprobación de CUDA
        print(f"ERROR: Ocurrió un error inesperado al verificar PyTorch CUDA: {e}")
        return False
