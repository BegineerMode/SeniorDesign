import tkinter as tk
from tkinter import messagebox
import sys
import threading
import os

Debug = False

# Stack to keep track of the history of pages
page_history = []

def on_close():
    #handles the wondow close event
    print("Window successfully closed!")
    sys.exit() #terminate the script
# Function to switch to a new page
def switch_to_page(current_page, create_next_page):
    # Save the current page in the history stack
    page_history.append(current_page)
    # Destroy the current page
    current_page.withdraw()
    # Create the next page
    create_next_page()

# Function to go back to the previous page
def go_back(current_page):
    # Destroy the current page
    current_page.withdraw()
    # Retrieve the last page from the history stack
    if page_history:
        previous_page = page_history.pop()
        previous_page.deiconify()

# Function to create the Home Page
def home_page():
    home_page = tk.Tk()
    home_page.title("Home Page")
    
    #handle window close event
    home_page.protocol("WM_DELETE_WINDOW", on_close)
    # Set the dimensions for the Home Page
    window_width = 900
    window_height = 700
    screen_width = home_page.winfo_screenwidth()
    screen_height = home_page.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    home_page.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # Add content to the Home Page
    label = tk.Label(home_page, text="Welcome to the Home Page!", font=("Arial", 16))
    label.pack(pady=20)
    
    # Button to go to the Private Network Page
    private_network_button = tk.Button(
        home_page,
        text="Go to Private Network",
        command=lambda: switch_to_page(home_page, PrivateNetwork)
    )
    private_network_button.pack(pady=10)
    
    # Button to go to the Camera Configuration Page
    Camera_Configuration = tk.Button(
        home_page,
        text="Camera Configuration",
        command=lambda: switch_to_page(home_page, CameraConfiguration)
    )
    Camera_Configuration.pack(pady=10)
    
    # Button to go to the Network Logs Page
    Network_logs = tk.Button(
        home_page,
        text="Network Logs",
        command=lambda: switch_to_page(home_page, NetworkLogs)
    )
    Network_logs.pack(pady=10)

    # Button to go to the Data Streaming Page
    Data_Streaming = tk.Button(
        home_page,
        text="Data Streaming",
        command=lambda: switch_to_page(home_page, DataStreaming)
    )
    Data_Streaming.pack(pady=10)

    # Button to go to the Camera Configuration Page
    Data_Collection = tk.Button(
        home_page,
        text="Data Collection",
        command=lambda: switch_to_page(home_page, DataCollection)
    )
    Data_Collection.pack(pady=10)

    home_page.mainloop()

# Simulated function to check if the stream is running (replace this with your actual stream status check)
def is_stream_running():
    """
    Function to check if the stream is running.
    Replace this with actual stream status checking logic.
    """
    # Example: Check if a process is running by name
    stream_running = os.system("tasklist | findstr VLC.exe") == 0  # Modify based on your stream process
    return stream_running

# Function to run the external code for stream access
def access_stream():
    """
    Function to access the stream by running another code/script.
    Replace 'stream_access.py' with the actual script you want to run.
    """
    try:
        threading.Thread(target=lambda: os.system("python stream_access.py")).start()  # Replace with actual code
        messagebox.showinfo("Stream Access", "Accessing the stream...")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to access the stream: {e}")
# Function to create the Private Network Page
def PrivateNetwork():
    private_page = tk.Tk()
    private_page.title("Private Network Page")

    # Attach the close protocol to the secondary window
    private_page.protocol("WM_DELETE_WINDOW", on_close)

    # Set the dimensions for the Private Network Page
    window_width = 600
    window_height = 400
    screen_width = private_page.winfo_screenwidth()
    screen_height = private_page.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    private_page.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # Add content to the Private Network Page
    label = tk.Label(private_page, text="Welcome to the Private Network!", font=("Arial", 14))
    label.pack(pady=20)
    
    # "Back" button to go to the previous page
    back_button = tk.Button(
        private_page,
        text="Go Back",
        command=lambda: go_back(private_page)
    )
    back_button.pack(pady=10)
    
    private_page.mainloop()

# Function to Navigate to the Camera Config page
# Camera configuration window with distance input
def CameraConfiguration():
    # Create the Camera Config page
    private_window = tk.Toplevel()  # Use Toplevel for secondary window
    private_window.title("Camera Config")

    # Attach the close protocol to the secondary window
    private_window.protocol("WM_DELETE_WINDOW", on_close)

    # Set dimensions for the Camera Config page
    window_width = 600
    window_height = 400
    screen_width = private_window.winfo_screenwidth()
    screen_height = private_window.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    private_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # Add content to the Camera Config page
    label = tk.Label(private_window, text="Camera Configuration", font=("Arial", 14))
    label.pack(pady=20)

    # Distance input field
    distance_label = tk.Label(private_window, text="Enter distance between cameras:", font=("Arial", 12))
    distance_label.pack()

    distance_entry = tk.Entry(private_window, font=("Arial", 12))
    distance_entry.pack(pady=5)

    # Dropdown menu for units
    unit_var = tk.StringVar(value="meters")  # Default unit
    units = ["meters", "feet"]
    
    unit_dropdown = tk.OptionMenu(private_window, unit_var, *units)
    unit_dropdown.pack(pady=5)

    # Save button
    save_button = tk.Button(private_window, text="Save Distance", 
                            command=lambda: save_distance(distance_entry, unit_var))
    save_button.pack(pady=10)

    # Go Back button
    go_back_button = tk.Button(private_window, text="Go Back to Home Page", 
                               command=lambda: go_back(private_window))
    go_back_button.pack(pady=10)

    private_window.mainloop()

# Function to handle the distance input
def save_distance(entry, unit_var):
    distance = entry.get()
    unit = unit_var.get()

    try:
        # Validate and convert distance to float
        distance_value = float(distance)
        messagebox.showinfo("Distance Saved", f"Distance: {distance_value} {unit}")
        print(f"Distance saved: {distance_value} {unit}")  # For debugging
    except ValueError:
        messagebox.showerror("Invalid Input", "Please enter a valid number for distance")

# Function to create the Network Logs page
def NetworkLogs():

    # Create the Network Logs page
    network_logs = tk.Tk()
    network_logs.title("Network Logs")
    
    # Attach the close protocol to the secondary window
    network_logs.protocol("WM_DELETE_WINDOW", on_close)

    # Set dimensions for the Network Logs page
    window_width = 600
    window_height = 400
    screen_width = network_logs.winfo_screenwidth()
    screen_height = network_logs.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    network_logs.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # Add content and a "Go Back" button to the Network Logs page
    label = tk.Label(network_logs, text="Network Logs", font=("Helvetica", 28))
    label.pack(pady=20)
    
    go_back_button = tk.Button(network_logs, text="Go Back to Home Page", command=lambda: go_back(network_logs))
    go_back_button.pack(pady=10)
    
    network_logs.mainloop()

# Function to create the Data Streaming page
# Data Streaming Window with Stream Status
def DataStreaming():
    private_window = tk.Toplevel()  # Use Toplevel for secondary window
    private_window.title("Data Streaming")

    # Attach close protocol
    private_window.protocol("WM_DELETE_WINDOW", on_close)

    # Set dimensions
    window_width = 600
    window_height = 400
    screen_width = private_window.winfo_screenwidth()
    screen_height = private_window.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    private_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # Stream status label
    status_label = tk.Label(private_window, text="Checking stream status...", font=("Arial", 14))
    status_label.pack(pady=20)

    # Function to update the stream status dynamically
    def update_status():
        if is_stream_running():
            status_label.config(text="Stream Status: RUNNING", fg="green")
            access_button.config(state="normal")  # Enable access button
        else:
            status_label.config(text="Stream Status: NOT RUNNING", fg="red")
            access_button.config(state="disabled")  # Disable access button

    # Button to access the stream (initially disabled)
    access_button = tk.Button(private_window, text="Access Stream", command=access_stream, state="disabled")
    access_button.pack(pady=10)

    # Go Back button
    go_back_button = tk.Button(private_window, text="Go Back to Home Page", command=lambda: go_back(private_window))
    go_back_button.pack(pady=10)

    # Update the stream status after window loads
    private_window.after(100, update_status)

    private_window.mainloop()

# Function to create the Data Collection page
def DataCollection():

    # Create the Data Collection page
    private_window = tk.Tk()
    private_window.title("Data Collection")

    # Attach the close protocol to the secondary window
    private_window.protocol("WM_DELETE_WINDOW", on_close)
    
    # Set dimensions for the Data Collection page
    window_width = 600
    window_height = 400
    screen_width = private_window.winfo_screenwidth()
    screen_height = private_window.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    private_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # Add content and a "Go Back" button to the Data Collection page
    label = tk.Label(private_window, text="Welcome to the Data Collection Page!", font=("Arial", 14))
    label.pack(pady=20)
    
    go_back_button = tk.Button(private_window, text="Go Back to Home Page", command=lambda: go_back(private_window))
    go_back_button.pack(pady=10)
    
    private_window.mainloop()

# Create the home page initially
home_page()