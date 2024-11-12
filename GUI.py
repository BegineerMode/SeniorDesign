# Code for GUI

import tkinter as tk

Debug = False

# Function that gets called when the "Camera Configuration" button is pressed
def on_camera_config_click():
    label.config(text="Camera Configuration")

# Function that gets called when the "Options" button is pressed
def on_options_click():
    label.config(text="Options")

# Creating the main window
root = tk.Tk()
root.title("GUI")  # Set the window title
root.geometry("400x300")  # Set window size

# Creating a label to display messages
label = tk.Label(root, text="Choose an option below", font=("Helvetica", 12))
label.pack(pady=20)  # Add the label to the window with some padding

# Creating a "Camera Configuration" button
camera_button = tk.Button(root, text="Camera Configuration", font=("Helvetica", 16), width=20, height=2, command=on_camera_config_click)
camera_button.pack(pady=10)  # Add the button to the window with some padding

# Creating an "Options" button
options_button = tk.Button(root, text="Options", font=("Helvetica", 16), width=20, height=2, command=on_options_click)
options_button.pack(pady=10)  # Add the button to the window with some padding

# Start the main event loop
root.mainloop()