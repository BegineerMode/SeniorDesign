import tkinter as tk

Debug = False

# Function to go back to the main window from the new window
def go_back(window):
    window.destroy()  # Close the current window
    root.deiconify()  # show the main window again

# Function that gets called when the "Camera Configuration" button is pressed
def on_camera_config_click():
    root.withdraw()  # closes main window
    # Create a new window for Camera Configuration
    camera_window = tk.Toplevel(root)
    camera_window.title("Camera Configuration")  # window title
    camera_window.geometry("700x400")  # window size

    label = tk.Label(camera_window, text="Camera Configuration", font=("Helvetica", 12))
    label.pack(pady=20)

    # Distance slider
    def update_distance(value):
        distance_label.config(text=f"Distance from Camera: {value} ft")

    distance_label = tk.Label(camera_window, text="Distance from Camera: 0 ft", font=("Helvetica", 12))
    distance_label.pack(pady=10)

    distance_slider = tk.Scale(camera_window, from_=0, to=200, orient="horizontal", command=update_distance)
    distance_slider.pack(pady=10)

    # Nocturnal Camera Checkbutton
    nocturnal_var = tk.IntVar()

    def show_checkboxes():
        if nocturnal_var.get() == 1:
            uv_checkbox.pack(pady=5)
            thermal_checkbox.pack(pady=5)
        else:
            uv_checkbox.pack_forget()
            thermal_checkbox.pack_forget()

    nocturnal_checkbox = tk.Checkbutton(camera_window, text="Nocturnal Camera", variable=nocturnal_var, command=show_checkboxes)
    nocturnal_checkbox.pack(pady=10)

    # UV and Thermal checkboxes
    uv_var = tk.IntVar()
    thermal_var = tk.IntVar()

    uv_checkbox = tk.Checkbutton(camera_window, text="UV", variable=uv_var)
    thermal_checkbox = tk.Checkbutton(camera_window, text="Thermal", variable=thermal_var)

    # "Back" button to close the camera window and return to the main window
    back_button = tk.Label(camera_window, text="Back to menu", fg="blue", font=("Helvetica", 12, "underline"), cursor="hand2")
    back_button.pack(side="bottom", anchor="w", padx=10, pady=10)

# Function that gets called when the "Options" button is pressed
def on_options_click():
    root.withdraw()  # Hide the main window
    # Create a new window for Options
    options_window = tk.Toplevel(root)
    options_window.title("Options")  # Set the window title
    options_window.geometry("400x300")  # Set window size

    label = tk.Label(options_window, text="Options", font=("Helvetica", 12))
    label.pack(pady=20)

    # "Back" button to close the options window and return to the main window
    back_button = tk.Button(options_window, text="Back", font=("Helvetica", 12), width=20, height=2, command=lambda: go_back(options_window))
    back_button.pack(pady=10)

# main window
root = tk.Tk()
root.title("GUI")  # Set the window title
root.geometry("400x300")  # Set window size

# text label
label = tk.Label(root, text="Choose an option below", font=("Helvetica", 12))
label.pack(pady=20)  # Add the label to the window with some padding

# Camera Configuration button
camera_button = tk.Button(root, text="Camera Configuration", font=("Helvetica", 16), width=20, height=2, command=on_camera_config_click)
camera_button.pack(pady=10)  # Add the button to the window with some padding

# Options button
options_button = tk.Button(root, text="Options", font=("Helvetica", 16), width=20, height=2, command=on_options_click)
options_button.pack(pady=10)  # Add the button to the window with some padding

# Start the main event loop
root.mainloop()