import tkinter as tk
from tkinter import filedialog, ttk
import numpy as np
import rawpy
from PIL import Image, ImageTk, ExifTags
from multiprocessing import Pool
import os
import psutil
import sys
from fractions import Fraction

def process_image(file_path):
    """Process a single image file and return the result."""
    exposure_time = 0
    with rawpy.imread(file_path) as raw:
        img = raw.postprocess().astype(np.float32)
    with Image.open(file_path) as image:
        img_exif = image.getexif()
        for (k,v) in img_exif.items():
            if ExifTags.TAGS.get(k) == 'ExposureTime':
                exposure_time = v
    print("Imported ", file_path)
    return img, exposure_time

def update_preview_image(average_image):
    """Update the preview image in the UI."""
    img = Image.fromarray(np.uint8(average_image))
    img.thumbnail((600, 600))
    img_tk = ImageTk.PhotoImage(img)
    preview_image_label.config(image=img_tk)
    preview_image_label.image = img_tk

def update_status(average_image, processed_count, total_images):
    if processed_count % 100 == 1 or processed_count == total_images:
        update_preview_image(average_image / processed_count)

    progress_var.set(progress_var.get() + 1)
    status_var.set(f"Processed image {progress_var.get()}/{total_images}")

    cpu_percent = psutil.cpu_percent()
    memory_percent = psutil.virtual_memory().percent
    details_var.set(f"Threads: {os.cpu_count()}\nCPU utilization: {cpu_percent}%\nMemory utilization: {memory_percent}%")
    
    app.update_idletasks()  # Update the UI

def process_images():
    """Process the selected images."""
    file_paths = filedialog.askopenfilenames(title="Select .dng files", filetypes=[("DNG files", "*.dng")])
    if not file_paths:
        status_var.set("No files selected.")
        return

    save_path = filedialog.asksaveasfilename(title="Save as", defaultextension=".tiff", filetypes=[("TIFF files", "*.tiff")])
    if not save_path:
        status_var.set("No save path specified.")
        return

    status_var.set("Starting to process images...")
    progress_var.set(0)
    progress_bar.config(maximum=len(file_paths))
	
    total_images = len(file_paths)
    processed_count = 0
    total_exposure_time = 0
    average_image = None
    
    with Pool(processes=os.cpu_count()) as pool:
        for img, exposure_time in pool.imap_unordered(process_image, file_paths):
            total_exposure_time += exposure_time
            processed_count += 1
            if average_image is None:
                average_image = img
            else:
                average_image += img
            update_status(average_image, processed_count, total_images)
    average_image = average_image / total_images
	        
    # Save the averaged image with EXIF data
    print("Saving ", save_path)
    average_image = np.clip(average_image, 0, 255).astype(np.uint8)
    img = Image.fromarray(average_image)
    img_exif = img.getexif()
    # 33434 exif ExposureTime numerical code
    img_exif[33434] = total_exposure_time
    img.save(save_path, exif=img_exif)

    status_var.set("Finished!")
    app.bell()


app = tk.Tk()
app.title("DNG Averager")
app.configure(bg='#f0f0f0')

frame = ttk.Frame(app, padding="20 20 20 20")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

title_font = ('Arial', 14, 'bold')
label_font = ('Arial', 12)

title_label = ttk.Label(frame, text="DNG Averager", font=title_font)
title_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 20))

files_label = ttk.Label(frame, text="Select DNG files to average:", font=label_font)
files_label.grid(row=1, column=0, sticky=tk.W, padx=(10, 0))
select_files_button = ttk.Button(frame, text="Select files", command=process_images)
select_files_button.grid(row=1, column=1, sticky=tk.E, padx=(0, 10))

status_var = tk.StringVar()
status_label = ttk.Label(frame, textvariable=status_var, font=label_font)
status_label.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=(10, 0), pady=(20, 0))

progress_var = tk.IntVar()
progress_bar = ttk.Progressbar(frame, variable=progress_var, mode='determinate')
progress_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=(10, 10), pady=(10, 0))

details_var = tk.StringVar()
details_label = ttk.Label(frame, textvariable=details_var, font=label_font, wraplength=400, justify=tk.LEFT)
details_label.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=(10, 0), pady=(20, 0))

preview_image_label = ttk.Label(frame)
preview_image_label.grid(row=5, column=0, columnspan=2, padx=(10, 10), pady=(20, 0))

app.mainloop()

