import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import os
import psutil
import datetime

# Dark “fire” theme colors
BG_COLOR = "#1e1e1e"
FG_COLOR = "#ffffff"
ACCENT_COLOR = "#f4511e"  # orange-red accent

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Substation Intrusion Detection System")
        self.geometry("1000x700")
        self.configure(bg=BG_COLOR)
        
        # Left navigation frame
        self.nav_frame = tk.Frame(self, bg=BG_COLOR)
        self.nav_frame.pack(side="left", fill="y")
        # Content frame (right side)
        self.content_frame = tk.Frame(self, bg=BG_COLOR)
        self.content_frame.pack(side="right", fill="both", expand=True)
        
        # Dictionary to hold page frames
        self.pages = {}
        
        # Navigation buttons (sidebar)
        nav_buttons = [
            ("Home", self.show_home),
            ("Private Network", self.show_private_network),
            ("Network Logs", self.show_network_logs),
            ("Camera Config", self.show_camera_config),
            ("Data Streaming", self.show_data_streaming),
            ("System Monitoring", self.show_system_monitoring)
        ]
        for (text, cmd) in nav_buttons:
            btn = tk.Button(self.nav_frame, text=text, command=cmd,
                            bg=BG_COLOR, fg=ACCENT_COLOR,
                            font=("Helvetica", 14, "bold"), relief="flat",
                            padx=20, pady=15)
            btn.pack(pady=10, fill="x")
        
        # Instantiate all pages
        self.pages["Home"] = HomePage(self.content_frame, self)
        self.pages["PrivateNetwork"] = PrivateNetworkPage(self.content_frame, self)
        self.pages["NetworkLogs"] = NetworkLogsPage(self.content_frame, self)
        self.pages["CameraConfig"] = CameraConfigPage(self.content_frame, self)
        self.pages["DataStreaming"] = DataStreamingPage(self.content_frame, self)
        self.pages["SystemMonitoring"] = SystemMonitoringPage(self.content_frame, self)
        
        # Show Home page initially
        self.show_home()

    def hide_all_pages(self):
        """Hide all page frames."""
        for page in self.pages.values():
            page.pack_forget()
            
    def show_home(self):
        self.hide_all_pages()
        self.pages["Home"].pack(fill="both", expand=True)

    def show_private_network(self):
        self.hide_all_pages()
        self.pages["PrivateNetwork"].pack(fill="both", expand=True)

    def show_network_logs(self):
        self.hide_all_pages()
        self.pages["NetworkLogs"].pack(fill="both", expand=True)

    def show_camera_config(self):
        self.hide_all_pages()
        self.pages["CameraConfig"].pack(fill="both", expand=True)

    def show_data_streaming(self):
        self.hide_all_pages()
        self.pages["DataStreaming"].pack(fill="both", expand=True)

    def show_system_monitoring(self):
        self.hide_all_pages()
        self.pages["SystemMonitoring"].pack(fill="both", expand=True)


class LoginDialog:
    """Modal login dialog at startup."""
    def __init__(self, parent):
        self.parent = parent
        self.top = tk.Toplevel(parent)
        self.top.title("Login")
        self.top.geometry("300x150")
        self.top.configure(bg=BG_COLOR)
        self.top.attributes("-topmost", True)
        self.top.grab_set()  # Make it modal
        
        tk.Label(self.top, text="Enter Password:", bg=BG_COLOR, fg=FG_COLOR).pack(pady=(20, 5))
        self.entry = tk.Entry(self.top, show="*", width=25, font=("Helvetica", 12))
        self.entry.pack(pady=5)
        self.entry.focus()
        
        login_btn = tk.Button(self.top, text="Login", command=self.check_password,
                              bg=ACCENT_COLOR, fg=FG_COLOR, relief="flat", padx=10, pady=5)
        login_btn.pack(pady=10)
        
        self.top.bind("<Return>", lambda e: self.check_password())
        
    def check_password(self):
        if self.entry.get() == "password123":  # TODO: replace with secure verification
            self.top.destroy()
        else:
            messagebox.showerror("Error", "Incorrect password!")


class HomePage(tk.Frame):
    """Home page with welcome banner."""
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller
        
        banner_text = "Welcome to Substation IDS\n\"Secure your network, secure your future.\""
        tk.Label(self, text=banner_text, font=("Helvetica", 24, "bold"),
                 fg=ACCENT_COLOR, bg=BG_COLOR, justify="center").pack(pady=100)


class PrivateNetworkPage(tk.Frame):
    """Private Network page for managing WireGuard tunnels."""
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller
        self.selected_config = None  # currently selected config file
        
        # Use grid for better spacing
        self.columnconfigure(0, weight=1)
        
        # Activate/Deactivate buttons
        tk.Button(self, text="Activate Tunnel", command=self.activate_tunnel,
                  bg=ACCENT_COLOR, fg=FG_COLOR, font=("Helvetica", 12), relief="flat")\
            .grid(row=0, column=0, pady=10, padx=20, sticky="ew")
        tk.Button(self, text="Deactivate Tunnel", command=self.deactivate_tunnel,
                  bg=ACCENT_COLOR, fg=FG_COLOR, font=("Helvetica", 12), relief="flat")\
            .grid(row=1, column=0, pady=10, padx=20, sticky="ew")
        
        # File picker for WireGuard config
        tk.Label(self, text="Select WireGuard Config:", bg=BG_COLOR, fg=FG_COLOR)\
            .grid(row=2, column=0, pady=(20, 5))
        tk.Button(self, text="Choose Config File", command=self.choose_config,
                  bg=ACCENT_COLOR, fg=FG_COLOR, font=("Helvetica", 12), relief="flat")\
            .grid(row=3, column=0, pady=5, sticky="ew", padx=20)
        self.config_path_label = tk.Label(self, text="", bg=BG_COLOR, fg=FG_COLOR, wraplength=500)
        self.config_path_label.grid(row=4, column=0, pady=5)
        
        # List of active tunnels
        tk.Label(self, text="Active Tunnels:", bg=BG_COLOR, fg=FG_COLOR)\
            .grid(row=5, column=0, pady=(20, 5))
        self.active_list = tk.Listbox(self, bg="#333333", fg=FG_COLOR, height=5,
                                      font=("Helvetica", 10))
        self.active_list.grid(row=6, column=0, pady=5, padx=20, sticky="ew")
        
        # Key pair generation
        tk.Button(self, text="Generate Key Pair", command=self.generate_keys,
                  bg=ACCENT_COLOR, fg=FG_COLOR, font=("Helvetica", 12), relief="flat")\
            .grid(row=7, column=0, pady=(20, 5), padx=20, sticky="ew")
        tk.Label(self, text="Private Key:", bg=BG_COLOR, fg=FG_COLOR)\
            .grid(row=8, column=0, pady=(10, 0), padx=20, sticky="w")
        self.private_text = tk.Entry(self, bg="#333333", fg=FG_COLOR, font=("Helvetica", 10))
        self.private_text.grid(row=9, column=0, pady=5, padx=20, sticky="ew")
        tk.Label(self, text="Public Key:", bg=BG_COLOR, fg=FG_COLOR)\
            .grid(row=10, column=0, pady=(10, 0), padx=20, sticky="w")
        self.public_text = tk.Entry(self, bg="#333333", fg=FG_COLOR, font=("Helvetica", 10))
        self.public_text.grid(row=11, column=0, pady=5, padx=20, sticky="ew")
        
        # Start periodic update of active tunnels list
        self.update_active_tunnels()
        
    def choose_config(self):
        """Open file dialog to select a config file."""
        file = filedialog.askopenfilename(title="Select WireGuard Config",
                                          filetypes=[("All Files", "*.*")])
        if file:
            self.selected_config = file
            self.config_path_label.config(text=file)
    
    def is_tunnel_active(self, name):
        """Check if a given tunnel interface is active via 'wg show'."""
        try:
            output = subprocess.check_output(["wg", "show", name])
            return bool(output.strip())
        except subprocess.CalledProcessError:
            return False

    def activate_tunnel(self):
        """Activate the selected WireGuard tunnel (if not already active)."""
        if not self.selected_config:
            messagebox.showwarning("No Config", "Please select a config file first.")
            return
        name = os.path.splitext(os.path.basename(self.selected_config))[0]
        if self.is_tunnel_active(name):
            messagebox.showinfo("Info", f"Tunnel {name} is already active.")
            return
        try:
            # Use sudo for wg-quick if needed
            subprocess.run(["sudo", "wg-quick", "up", self.selected_config], check=True)
            messagebox.showinfo("Success", f"Activated {name}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        
    def deactivate_tunnel(self):
        """Deactivate the selected WireGuard tunnel (if it is active)."""
        if not self.selected_config:
            messagebox.showwarning("No Config", "Please select a config file first.")
            return
        name = os.path.splitext(os.path.basename(self.selected_config))[0]
        if not self.is_tunnel_active(name):
            messagebox.showinfo("Info", f"Tunnel {name} is not active.")
            return
        try:
            subprocess.run(["sudo", "wg-quick", "down", self.selected_config], check=True)
            messagebox.showinfo("Success", f"Deactivated {name}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_active_tunnels(self):
        """Update the listbox with currently active tunnels every 10 seconds."""
        self.active_list.delete(0, tk.END)
        try:
            output = subprocess.check_output(["wg", "show", "interfaces"])
            tunnels = output.decode().split()
            for t in tunnels:
                self.active_list.insert(tk.END, t)
        except Exception:
            pass
        self.after(10000, self.update_active_tunnels)

    def generate_keys(self):
        """Generate WireGuard private/public key pair and display/save them."""
        try:
            priv = subprocess.check_output("wg genkey", shell=True).decode().strip()
            pub = subprocess.check_output(f"echo {priv} | wg pubkey", shell=True).decode().strip()
        except Exception as e:
            messagebox.showerror("Error", f"Key generation failed: {e}")
            return
        # Display keys in text boxes
        self.private_text.delete(0, tk.END); self.private_text.insert(0, priv)
        self.public_text.delete(0, tk.END); self.public_text.insert(0, pub)
        # Save keys to config folder
        config_folder = "/etc/wireguard"
        os.makedirs(config_folder, exist_ok=True)
        priv_file = os.path.join(config_folder, "private.key")
        pub_file = os.path.join(config_folder, "public.key")
        try:
            with open(priv_file, "w") as f: f.write(priv)
            with open(pub_file, "w") as f: f.write(pub)
            os.chmod(priv_file, 0o600)  # secure permissions
            messagebox.showinfo("Saved", f"Keys saved to {config_folder}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save keys: {e}")


class NetworkLogsPage(tk.Frame):
    """Page to display and filter network/WireGuard logs."""
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller
        
        self.log_file = "/var/log/syslog"  # Path to log file (adjust as needed)
        self.search_var = tk.StringVar()
        
        # Toolbar frame for filter and export
        toolbar = tk.Frame(self, bg=BG_COLOR)
        toolbar.pack(fill="x", pady=5)
        self.search_entry = tk.Entry(toolbar, textvariable=self.search_var,
                                     bg="#333333", fg=FG_COLOR, width=30)
        self.search_entry.pack(side="left", padx=(10,5))
        self.search_entry.insert(0, "Filter logs...")
        self.search_entry.bind("<FocusIn>", lambda e: self.search_entry.delete(0, tk.END))
        tk.Button(toolbar, text="Search", command=self.filter_logs,
                  bg=ACCENT_COLOR, fg=FG_COLOR, relief="flat")\
            .pack(side="left", padx=5)
        tk.Button(toolbar, text="Export Log", command=self.export_log,
                  bg=ACCENT_COLOR, fg=FG_COLOR, relief="flat")\
            .pack(side="left", padx=5)
        
        # Text widget to display logs
        self.logs_text = tk.Text(self, bg="#333333", fg=FG_COLOR,
                                 font=("Courier", 10))
        self.logs_text.pack(fill="both", expand=True, padx=10, pady=(0,10))
        
        self.load_logs()

    def load_logs(self):
        """Load log file contents into the text widget."""
        self.logs_text.delete(1.0, tk.END)
        try:
            with open(self.log_file, "r") as f:
                data = f.read()
            self.logs_text.insert(tk.END, data)
        except Exception as e:
            self.logs_text.insert(tk.END, f"Could not read log: {e}")

    def filter_logs(self):
        """Filter log lines by the search term."""
        term = self.search_var.get()
        self.logs_text.delete(1.0, tk.END)
        try:
            with open(self.log_file, "r") as f:
                lines = f.readlines()
        except Exception as e:
            self.logs_text.insert(tk.END, f"Error reading log: {e}")
            return
        for line in lines:
            if term.lower() in line.lower():
                self.logs_text.insert(tk.END, line)

    def export_log(self):
        """Save the currently displayed logs to a file in the logs/ folder."""
        logs_dir = "logs"
        os.makedirs(logs_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(logs_dir, f"log_{timestamp}.txt")
        try:
            content = self.logs_text.get(1.0, tk.END)
            with open(out_path, "w") as f:
                f.write(content)
            messagebox.showinfo("Exported", f"Log saved to {out_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save log: {e}")


class CameraConfigPage(tk.Frame):
    """Camera configuration page with recording schedules."""
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller
        
        tk.Label(self, text="Recording Schedules:", bg=BG_COLOR,
                 fg=FG_COLOR, font=("Helvetica", 12, "bold")).pack(pady=(10,5))
        self.schedule_list = tk.Listbox(self, bg="#333333", fg=FG_COLOR,
                                        height=5, font=("Helvetica", 10))
        self.schedule_list.pack(padx=10, fill="x")
        # Example schedules (in practice, load from config)
        self.schedule_list.insert(tk.END, "Daily 00:00-06:00")
        self.schedule_list.insert(tk.END, "Mon-Fri 18:00-23:00")
        
        tk.Button(self, text="Delete Schedule", command=self.delete_schedule,
                  bg=ACCENT_COLOR, fg=FG_COLOR, relief="flat")\
            .pack(pady=10)
        
        # Live camera feed placeholder (enlarged)
        tk.Label(self, text="Live Camera Feed:", bg=BG_COLOR,
                 fg=FG_COLOR, font=("Helvetica", 12, "bold")).pack(pady=(20,5))
        self.feed_canvas = tk.Canvas(self, width=800, height=450, bg="#000000")
        self.feed_canvas.pack(pady=5)

    def delete_schedule(self):
        sel = self.schedule_list.curselection()
        if not sel:
            messagebox.showwarning("Select", "No schedule selected.")
            return
        self.schedule_list.delete(sel[0])
        messagebox.showinfo("Deleted", "Schedule deleted.")


class DataStreamingPage(tk.Frame):
    """Lists recorded video files with timestamps."""
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller
        
        tk.Label(self, text="Recorded Videos:", bg=BG_COLOR,
                 fg=FG_COLOR, font=("Helvetica", 12, "bold")).pack(pady=(10,5))
        self.videos_list = tk.Listbox(self, bg="#333333", fg=FG_COLOR,
                                      font=("Helvetica", 10))
        self.videos_list.pack(padx=10, fill="both", expand=True)
        self.load_videos()

    def load_videos(self):
        video_dir = "videos"
        os.makedirs(video_dir, exist_ok=True)
        for f in os.listdir(video_dir):
            if f.lower().endswith((".mp4", ".avi", ".mkv")):
                path = os.path.join(video_dir, f)
                ts = os.path.getctime(path)
                dt = datetime.datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M:%S")
                self.videos_list.insert(tk.END, f"{f} ({dt})")


class SystemMonitoringPage(tk.Frame):
    """Live system monitoring (CPU/Mem graph, tunnel status, etc.)."""
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller
        
        # Canvas for real-time CPU/Memory graph
        self.graph_canvas = tk.Canvas(self, width=800, height=300, bg="#000000")
        self.graph_canvas.pack(pady=10)
        
        # Labels for status and stats
        self.tunnel_status_label = tk.Label(self, text="Tunnel Status: Unknown",
                                            bg=BG_COLOR, fg=FG_COLOR,
                                            font=("Helvetica", 12))
        self.tunnel_status_label.pack(pady=5)
        self.data_stats_label = tk.Label(self, text="Incoming: 0 B, Outgoing: 0 B",
                                         bg=BG_COLOR, fg=FG_COLOR,
                                         font=("Helvetica", 12))
        self.data_stats_label.pack(pady=5)
        self.health_label = tk.Label(self, text="Connection Health: Unknown",
                                     bg=BG_COLOR, fg=FG_COLOR,
                                     font=("Helvetica", 12))
        self.health_label.pack(pady=5)
        
        self.cpu_data = [0]*30
        self.mem_data = [0]*30
        
        # Start periodic updates
        self.update_graph()
        self.update_tunnel_status()

    def update_graph(self):
        """Update the CPU/Memory usage graph every second."""
        self.cpu_data.pop(0)
        self.mem_data.pop(0)
        self.cpu_data.append(psutil.cpu_percent())
        self.mem_data.append(psutil.virtual_memory().percent)
        
        self.graph_canvas.delete("all")
        w, h = 800, 300
        # Plot lines for CPU (blue) and Memory (red)
        for i in range(29):
            x1 = (i/29)*w; x2 = ((i+1)/29)*w
            y1 = h - (self.cpu_data[i]/100.0 * h)
            y2 = h - (self.cpu_data[i+1]/100.0 * h)
            self.graph_canvas.create_line(x1, y1, x2, y2, fill="blue", width=2)
            y1m = h - (self.mem_data[i]/100.0 * h)
            y2m = h - (self.mem_data[i+1]/100.0 * h)
            self.graph_canvas.create_line(x1, y1m, x2, y2m, fill="red", width=2)
        # Legends
        self.graph_canvas.create_text(10, 10, text="CPU (%)", fill="blue", anchor="nw",
                                      font=("Helvetica", 10))
        self.graph_canvas.create_text(10, 25, text="Memory (%)", fill="red", anchor="nw",
                                      font=("Helvetica", 10))
        
        self.after(1000, self.update_graph)

    def update_tunnel_status(self):
        """Update tunnel status, network I/O, and health status every 10 seconds."""
        try:
            output = subprocess.check_output(["wg", "show", "interfaces"])
            tunnels = output.decode().split()
            if tunnels:
                self.tunnel_status_label.config(text="Tunnel Status: Active", fg="green")
            else:
                self.tunnel_status_label.config(text="Tunnel Status: Down", fg="red")
        except Exception:
            self.tunnel_status_label.config(text="Tunnel Status: Unknown", fg="orange")
        
        # Network I/O stats
        net = psutil.net_io_counters()
        inc = net.bytes_recv
        out = net.bytes_sent
        self.data_stats_label.config(text=f"Incoming: {inc} B, Outgoing: {out} B")
        
        # Connection health (green if OK, red if critical)
        if self.cpu_data[-1] > 90 or self.mem_data[-1] > 90:
            self.health_label.config(text="Connection Health: Critical", fg="red")
        else:
            self.health_label.config(text="Connection Health: Good", fg="green")
        
        self.after(10000, self.update_tunnel_status)


if __name__ == "__main__":
    app = App()
    app.withdraw()  # Hide main window until login completes
    login = LoginDialog(app)
    app.wait_window(login.top)  # Wait for login dialog to close
    app.deiconify()  # Show main window after successful login
    app.mainloop()
