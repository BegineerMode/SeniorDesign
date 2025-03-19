import tkinter as tk

Debug = False

# Stack to keep track of the history of pages
page_history = []

# Function to switch to a new page
def switch_to_page(current_page, create_next_page):
    # Save the current page in the history stack
    page_history.append(current_page)
    # Destroy the current page
    current_page.destroy()
    # Create the next page
    create_next_page()

# Function to go back to the previous page
def go_back(current_page):
    # Destroy the current page
    current_page.destroy()
    # Retrieve the last page from the history stack
    if page_history:
        previous_page = page_history.pop()
        previous_page()

# Function to create the Home Page
def home_page():
    home_page = tk.Tk()
    home_page.title("Home Page")
    
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
    
    # Button to go to the Private Network Page
    Camera_Configuration = tk.Button(
        home_page,
        text="Camera Configuration",
        command=lambda: switch_to_page(home_page, CameraConfiguration)
    )
    Camera_Configuration.pack(pady=10)
    
    Network_logs = tk.Button(
        home_page,
        text="Network Logs",
        command=lambda: switch_to_page(home_page, NetworkLogs)
    )
    Network_logs.pack(pady=10)

    Data_Streaming = tk.Button(
        home_page,
        text="Data Streaming",
        command=lambda: switch_to_page(home_page, DataStreaming)
    )
    home_page.mainloop()

# Function to create the Private Network Page
def PrivateNetwork():
    private_page = tk.Tk()
    private_page.title("Private Network Page")
    
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

#Function to Navigate to the Camera Config page
def CameraConfiguration():

    # Create the Camera Config page
    private_window = tk.Tk()
    private_window.title("Camera Config")
    
    # Set dimensions for the Camera Config page
    window_width = 600
    window_height = 400
    screen_width = private_window.winfo_screenwidth()
    screen_height = private_window.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    private_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # Add content and a "Go Back" button to the Camera Config page
    label = tk.Label(private_window, text="Welcome to the Camera Config Page!", font=("Arial", 14))
    label.pack(pady=20)
    
    go_back_button = tk.Button(private_window, text="Go Back to Home Page", command=lambda: go_back(private_window))
    go_back_button.pack(pady=10)
    
    private_window.mainloop()

# Function to create the Network Logs page
def NetworkLogs():

    # Create the Network Logs page
    network_logs = tk.Tk()
    network_logs.title("Network Logs")
    
    # Set dimensions for the Network Logs page
    window_width = 600
    window_height = 400
    screen_width = network_logs.winfo_screenwidth()
    screen_height = network_logs.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    network_logs.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # Add content and a "Go Back" button to the Camera Config page
    label = tk.Label(network_logs, text="Network Logs", font=("Helvetica", 28))
    label.pack(pady=20)
    
    go_back_button = tk.Button(network_logs, text="Go Back to Home Page", command=lambda: go_back(network_logs))
    go_back_button.pack(pady=10)
    
    network_logs.mainloop()

# Function to create the Data Streaming page
def DataStreaming():

    # Create the Camera Config page
    private_window = tk.Tk()
    private_window.title("Data Streaming")
    
    # Set dimensions for the Camera Config page
    window_width = 600
    window_height = 400
    screen_width = private_window.winfo_screenwidth()
    screen_height = private_window.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    private_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # Add content and a "Go Back" button to the Camera Config page
    label = tk.Label(private_window, text="Welcome to the Data Streaming Page!", font=("Arial", 14))
    label.pack(pady=20)
    
    go_back_button = tk.Button(private_window, text="Go Back to Home Page", command=lambda: go_back(private_window))
    go_back_button.pack(pady=10)
    
    private_window.mainloop()
# Function to create the Data Collection page
#Function to Navigate to the Camera Config page

# Create the home page initially
home_page()