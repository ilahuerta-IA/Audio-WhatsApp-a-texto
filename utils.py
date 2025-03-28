# utils.py
"""Funciones de utilidad para la GUI y manejo de archivos."""

import tkinter as tk
from tkinter import filedialog, messagebox
import config

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