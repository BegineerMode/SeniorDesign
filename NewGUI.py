import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
from PIL import Image, ImageTk
import subprocess, os, time, ctypes
import psutil

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WireGuard GUI")
        self.geometry("1000x700")
        self.configure(bg="#1a1a1a")  # Dark fire-themed background
        # Load logo image (flame+substation motif)
        try:
            img = Image.open("logo.png").resize((80, 80))
            self.logo_image = ImageTk.PhotoImage(img)
        except Exception as e:
            self.logo_image = None
            print("Logo not found:", e)
        # Menu for navigation
        menubar = tk.Menu(self)
        page_menu = tk.Menu(menubar, tearoff=0)
        page_menu.add_command(label="Home", command=lambda: self.show_frame("HomePage"))
        page_menu.add_command(label="Private Network", command=self.open_private_page)
        page_menu.add_command(label="Camera Config", command=lambda: self.show_frame("CameraConfigPage"))
        page_menu.add_command(label="Network Logs", command=lambda: self.show_frame("NetworkLogsPage"))
        page_menu.add_command(label="Data Streaming", command=lambda: self.show_frame("DataStreamingPage"))
        page_menu.add_command(label="System Monitoring", command=lambda: self.show_frame("SystemMonitoringPage"))
        page_menu.add_command(label="Settings", command=self.open_settings_page)
        page_menu.add_separator()
        page_menu.add_command(label="Quit", command=self.destroy)
        menubar.add_cascade(label="Menu", menu=page_menu)
        self.config(menu=menubar)
        # Container for pages
        container = tk.Frame(self, bg="#1a1a1a")
        container.pack(fill='both', expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        self.frames = {}
        for F in (HomePage, PrivateNetworkPage, CameraConfigPage, NetworkLogsPage,
                  DataStreamingPage, SystemMonitoringPage, SettingsPage):
            frame = F(container, self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        self.show_frame("HomePage")
        # Ensure Recordings folder exists
        if not os.path.exists("Recordings"):
            os.makedirs("Recordings")
    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        if hasattr(frame, 'on_show'):
            frame.on_show()
    def open_private_page(self):
        pw = simpledialog.askstring("Password Required", "Enter password:", show="*")
        if pw == "password":
            self.show_frame("PrivateNetworkPage")
        else:
            messagebox.showerror("Error", "Incorrect password")
    def open_settings_page(self):
        pw = simpledialog.askstring("Password Required", "Enter password:", show="*")
        if pw == "password":
            self.show_frame("SettingsPage")
        else:
            messagebox.showerror("Error", "Incorrect password")

class BasePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#1a1a1a")
        self.controller = controller
        # Add logo at top if available
        if controller.logo_image:
            logo = tk.Label(self, image=controller.logo_image, bg="#1a1a1a")
            logo.pack(side="top", pady=10)

class HomePage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        tk.Label(self, text="WireGuard GUI - Home", fg="white", bg="#1a1a1a",
                 font=("Arial", 18)).pack(pady=10)
        tk.Label(self, text="Welcome to the WireGuard GUI. Use the menu to navigate.", fg="white", bg="#1a1a1a").pack()

class PrivateNetworkPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        tk.Label(self, text="Private Network Configuration", fg="orange", bg="#1a1a1a",
                 font=("Arial", 16)).pack(pady=5)
        # Relay server toggle
        self.relay_var = tk.BooleanVar()
        tk.Checkbutton(self, text="Act as Relay Server", variable=self.relay_var,
                       fg="white", bg="#1a1a1a", selectcolor="#333333",
                       activebackground="#333333", activeforeground="white").pack(pady=5)
        # Deactivate tunnel button
        tk.Button(self, text="Deactivate/Tunnel", command=self.tunnels,
                  bg="#aa0000", fg="white").pack(pady=5)
        tk.Label(self, text="Active Tunnels: wg0, wg1 (example)", fg="white", bg="#1a1a1a").pack(pady=(5,15))
        # Create Config section
        config_frame = tk.LabelFrame(self, text="Create Config Template", fg="orange", bg="#1a1a1a")
        config_frame.pack(fill="x", padx=10, pady=10)
        self.template_var = tk.StringVar(value="p2p")
        tk.Radiobutton(config_frame, text="Peer-to-Peer Template", variable=self.template_var, value="p2p",
                       fg="white", bg="#1a1a1a", selectcolor="#333333")\
            .grid(row=0, column=0, padx=5, pady=2, sticky="w")
        tk.Radiobutton(config_frame, text="Relay Server Template", variable=self.template_var, value="relay",
                       fg="white", bg="#1a1a1a", selectcolor="#333333")\
            .grid(row=0, column=1, padx=5, pady=2, sticky="w")
        self.config_text = tk.Text(config_frame, height=6, bg="#222222", fg="white")
        self.config_text.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="we")
        tk.Button(config_frame, text="Generate Config", command=self.generate_config,
                  bg="#0055aa", fg="white")\
            .grid(row=2, column=0, columnspan=2, pady=5)
        config_frame.columnconfigure((0,1), weight=1)
    def tunnels(self):
        # Step 1: Ask user to select a WireGuard .conf file
        config_path = filedialog.askopenfilename(
            title="Select WireGuard Config",
            filetypes=[("WireGuard Config", "*")]
        )
        if not config_path:
            return  # user canceled the dialog

        # Step 2: Define the WireGuard executable path and arguments
        wireguard_exe = r"C:\Program Files\WireGuard\wireguard.exe"
        args = [wireguard_exe, "/installtunnelservice", config_path]

        # Step 3: Check for admin rights
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except:
            is_admin = False

        if is_admin:
            # Already admin: run the command directly
            try:
                subprocess.run(args, check=True)
                messagebox.showinfo("Success", "WireGuard tunnel activated.")
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Error", f"Activation failed: {e}")
        else:
            # Not admin: re-run the WireGuard command elevated
            # Using ShellExecute with 'runas' will prompt UAC
            params = f'/installtunnelservice "{config_path}"'
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", wireguard_exe, params, None, 1
            )
            if result <= 32:
                messagebox.showerror("Error", "Failed to elevate permissions.")

        messagebox.showinfo("Tunnels", "All active WireGuard tunnels have been deactivated.")
        # If relay, log activity
        if self.relay_var.get():
            with open("network.log", "a") as f:
                f.write(f"[{time.ctime()}] Relay server deactivated all tunnels\n")
    def generate_config(self):
        if self.template_var.get() == "p2p":
            template = (
                "# Peer-to-Peer WireGuard config template\n"
                "[Interface]\nAddress = 10.0.0.1/24\nPrivateKey = <your_key>\n\n"
                "[Peer]\nPublicKey = <peer_key>\nAllowedIPs = 10.0.0.2/32\n"
            )
        else:
            template = (
                "# Relay/Reverse Tunnel WireGuard config template\n"
                "[Interface]\nAddress = 10.0.1.1/24\nPrivateKey = <relay_key>\nListenPort = 51820\n\n"
                "[Peer]\n# Peer behind NAT\nPublicKey = <peer_key>\nAllowedIPs = 10.0.1.2/32\n"
                "Endpoint = <relay_ip>:51820\nPersistentKeepalive = 25\n"
            )
        self.config_text.delete("1.0", tk.END)
        self.config_text.insert(tk.END, template)

class CameraConfigPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        tk.Label(self, text="Camera Configuration", fg="orange", bg="#1a1a1a",
                 font=("Arial", 16)).pack(pady=5)
        # FFmpeg command option
        self.use_default = tk.BooleanVar(value=True)
        tk.Radiobutton(self, text="Use default FFmpeg command", variable=self.use_default, value=True,
                       fg="white", bg="#1a1a1a", selectcolor="#333333").pack(anchor="w", padx=10)
        tk.Radiobutton(self, text="Use custom command", variable=self.use_default, value=False,
                       fg="white", bg="#1a1a1a", selectcolor="#333333").pack(anchor="w", padx=10)
        self.ffmpeg_cmd_entry = tk.Entry(self, width=80, bg="#333333", fg="white")
        default_cmd = "ffmpeg -f v4l2 -i /dev/video0 -c:v libx264 -preset veryfast -tune zerolatency -f mpegts udp://<dest_ip>:1234"
        self.ffmpeg_cmd_entry.insert(0, default_cmd)
        self.ffmpeg_cmd_entry.pack(padx=10, pady=5, fill="x")
        # Sending feed controls
        send_frame = tk.Frame(self, bg="#1a1a1a")
        send_frame.pack(pady=5)
        self.start_send_btn = tk.Button(send_frame, text="Start Sending Feed",
                                        command=self.start_sending, bg="#00aa00", fg="white")
        self.start_send_btn.grid(row=0, column=0, padx=5)
        self.stop_send_btn = tk.Button(send_frame, text="Stop Sending Feed",
                                       command=self.stop_sending, bg="#aa0000", fg="white", state="disabled")
        self.stop_send_btn.grid(row=0, column=1, padx=5)
        # Receiving feed controls
        recv_frame = tk.Frame(self, bg="#1a1a1a")
        recv_frame.pack(pady=5)
        self.start_recv_btn = tk.Button(recv_frame, text="Start Receiving Feeds",
                                        command=self.start_receiving, bg="#00aa00", fg="white")
        self.start_recv_btn.grid(row=0, column=0, padx=5)
        self.stop_recv_btn = tk.Button(recv_frame, text="Stop Receiving Feeds",
                                       command=self.stop_receiving, bg="#aa0000", fg="white", state="disabled")
        self.stop_recv_btn.grid(row=0, column=1, padx=5)
        # Live display placeholders
        display_frame = tk.Frame(self, bg="#1a1a1a")
        display_frame.pack(pady=10)
        self.cam1_label = tk.Label(display_frame, text="Live Feed 1",
                                   bg="black", fg="white", width=40, height=10)
        self.cam1_label.grid(row=0, column=0, padx=5)
        self.cam2_label = tk.Label(display_frame, text="Live Feed 2",
                                   bg="black", fg="white", width=40, height=10)
        self.cam2_label.grid(row=0, column=1, padx=5)
        # Time display
        self.time_label = tk.Label(self, text="", fg="white", bg="#1a1a1a", font=("Arial", 14))
        self.time_label.pack(pady=5)
        self.update_clock()
        # Recording controls
        rec_frame = tk.Frame(self, bg="#1a1a1a")
        rec_frame.pack(pady=5)
        self.start_rec_btn = tk.Button(rec_frame, text="Start Recording",
                                       command=self.start_recording, bg="#00aa00", fg="white")
        self.start_rec_btn.grid(row=0, column=0, padx=5)
        self.stop_rec_btn = tk.Button(rec_frame, text="Stop Recording",
                                      command=self.stop_recording, bg="#aa0000", fg="white", state="disabled")
        self.stop_rec_btn.grid(row=0, column=1, padx=5)
        # Schedule options
        sched_frame = tk.Frame(self, bg="#1a1a1a")
        sched_frame.pack(pady=5, fill="x")
        tk.Label(sched_frame, text="Add Recording Schedule (HH:MM):",
                 fg="white", bg="#1a1a1a").grid(row=0, column=0, padx=5)
        self.schedule_entry = tk.Entry(sched_frame, width=10, bg="#333333", fg="white")
        self.schedule_entry.grid(row=0, column=1)
        tk.Button(sched_frame, text="Add", command=self.add_schedule,
                  bg="#0055aa", fg="white").grid(row=0, column=2, padx=5)
        self.schedule_list = tk.Listbox(sched_frame, bg="#222222", fg="white", height=4)
        self.schedule_list.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="we")
        sched_frame.columnconfigure(2, weight=1)
        self.recording_schedule = []
    def update_clock(self):
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=now)
        self.after(1000, self.update_clock)
    def start_sending(self):
        cmd = self.ffmpeg_cmd_entry.get() if not self.use_default.get() else self.ffmpeg_cmd_entry.get()
        try:
            self.send_proc = subprocess.Popen(cmd, shell=True)
            self.start_send_btn.config(state="disabled")
            self.stop_send_btn.config(state="normal")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start sending feed: {e}")
    def stop_sending(self):
        if hasattr(self, 'send_proc'):
            self.send_proc.terminate()
            self.start_send_btn.config(state="normal")
            self.stop_send_btn.config(state="disabled")
    def start_receiving(self):
        self.cam1_label.config(text="Receiving Feed 1...")
        self.cam2_label.config(text="Receiving Feed 2...")
        self.start_recv_btn.config(state="disabled")
        self.stop_recv_btn.config(state="normal")
    def stop_receiving(self):
        self.cam1_label.config(text="Live Feed 1")
        self.cam2_label.config(text="Live Feed 2")
        self.start_recv_btn.config(state="normal")
        self.stop_recv_btn.config(state="disabled")
    def start_recording(self):
        filename = time.strftime("%Y%m%d_%H%M%S") + ".mp4"
        filepath = os.path.join("Recordings", filename)
        with open(filepath, "w") as f:
            f.write("Dummy recording data")
        self.start_rec_btn.config(state="disabled")
        self.stop_rec_btn.config(state="normal")
    def stop_recording(self):
        self.start_rec_btn.config(state="normal")
        self.stop_rec_btn.config(state="disabled")
    def add_schedule(self):
        time_str = self.schedule_entry.get().strip()
        if time_str:
            self.schedule_list.insert(tk.END, time_str)
            self.recording_schedule.append(time_str)
            self.schedule_entry.delete(0, tk.END)

class NetworkLogsPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        tk.Label(self, text="Network Logs", fg="orange", bg="#1a1a1a",
                 font=("Arial", 16)).pack(pady=5)
        self.text = tk.Text(self, bg="#222222", fg="white")
        self.text.pack(fill="both", expand=True, padx=10, pady=10)
        self.freeze = False
        btn_frame = tk.Frame(self, bg="#1a1a1a")
        btn_frame.pack(pady=5)
        self.freeze_btn = tk.Button(btn_frame, text="Freeze", command=self.toggle_freeze,
                                    bg="#ffaa00", fg="black")
        self.freeze_btn.grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Clear Logs", command=self.clear_logs,
                  bg="#0055aa", fg="white").grid(row=0, column=1, padx=5)
    def on_show(self):
        self.update_logs()
    def update_logs(self):
        if not self.freeze:
            try:
                with open("network.log", "r") as f:
                    content = f.read()
            except FileNotFoundError:
                content = ""
            self.text.delete("1.0", tk.END)
            self.text.insert(tk.END, content)
        self.after(2000, self.update_logs)
    def toggle_freeze(self):
        self.freeze = not self.freeze
        self.freeze_btn.config(text="Unfreeze" if self.freeze else "Freeze")
    def clear_logs(self):
        open("network.log", "w").close()
        self.text.delete("1.0", tk.END)

class DataStreamingPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        tk.Label(self, text="Data Streaming (Recordings)", fg="orange", bg="#1a1a1a",
                 font=("Arial", 16)).pack(pady=5)
        self.listbox = tk.Listbox(self, bg="#222222", fg="white")
        self.listbox.pack(fill="both", expand=True, padx=10, pady=10)
        self.listbox.bind('<Double-1>', self.play_selected)
    def on_show(self):
        self.refresh_list()
    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        files = sorted(os.listdir("Recordings"))
        for f in files:
            self.listbox.insert(tk.END, f)
    def play_selected(self, event):
        sel = self.listbox.curselection()
        if sel:
            filename = self.listbox.get(sel[0])
            path = os.path.join("Recordings", filename)
            try:
                if os.name == 'nt':
                    os.startfile(path)
                else:
                    subprocess.Popen(['xdg-open', path])
            except Exception as e:
                messagebox.showerror("Error", f"Cannot open file: {e}")

class SystemMonitoringPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        tk.Label(self, text="System Monitoring", fg="orange", bg="#1a1a1a",
                 font=("Arial", 16)).pack(pady=5)
        self.cpu_label = tk.Label(self, text="", fg="white", bg="#1a1a1a")
        self.cpu_label.pack()
        self.mem_label = tk.Label(self, text="", fg="white", bg="#1a1a1a")
        self.mem_label.pack()
        self.vpn_label = tk.Label(self, text="", fg="white", bg="#1a1a1a")
        self.vpn_label.pack()
        self.uptime_label = tk.Label(self, text="", fg="white", bg="#1a1a1a")
        self.uptime_label.pack()
        self.update_stats()
    def update_stats(self):
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        uptime_sec = time.time() - psutil.boot_time()
        hours = int(uptime_sec // 3600)
        mins = int((uptime_sec % 3600) // 60)
        self.cpu_label.config(text=f"CPU Usage: {cpu}%")
        self.mem_label.config(text=f"Memory Usage: {mem}%")
        # VPN (wg0) bandwidth
        counters = psutil.net_io_counters(pernic=True)
        if 'wg0' in counters:
            sent = counters['wg0'].bytes_sent
            recv = counters['wg0'].bytes_recv
            self.vpn_label.config(text=f"wg0 Sent: {sent} bytes, Recv: {recv} bytes")
        else:
            self.vpn_label.config(text="wg0 interface not active")
        self.uptime_label.config(text=f"Uptime: {hours}h {mins}m")
        self.after(5000, self.update_stats)

class SettingsPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        tk.Label(self, text="Settings", fg="orange", bg="#1a1a1a",
                 font=("Arial", 16)).pack(pady=5)
        self.dark_mode_var = tk.BooleanVar(value=True)
        tk.Checkbutton(self, text="Dark Mode", variable=self.dark_mode_var,
                       command=self.toggle_dark_mode,
                       fg="white", bg="#1a1a1a", selectcolor="#333333",
                       activebackground="#333333", activeforeground="white").pack(anchor="w", padx=10)
        self.autoconnect_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self, text="Auto-Reconnect VPN", variable=self.autoconnect_var,
                       fg="white", bg="#1a1a1a", selectcolor="#333333",
                       activebackground="#333333", activeforeground="white").pack(anchor="w", padx=10)
        self.startup_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self, text="Start on System Boot", variable=self.startup_var,
                       fg="white", bg="#1a1a1a", selectcolor="#333333",
                       activebackground="#333333", activeforeground="white").pack(anchor="w", padx=10)
        tk.Label(self, text="User Preferences:", fg="white", bg="#1a1a1a",
                 font=("Arial", 12)).pack(anchor="w", padx=10, pady=(10,0))
        self.pref_entry = tk.Entry(self, width=40, bg="#333333", fg="white")
        self.pref_entry.pack(padx=10, pady=5)
        tk.Button(self, text="Save Settings", command=self.save_settings,
                  bg="#0055aa", fg="white").pack(pady=10)
    def toggle_dark_mode(self):
        if self.dark_mode_var.get():
            bg = "#1a1a1a"; fg = "white"; btn_bg = "#333333"
        else:
            bg = "white"; fg = "black"; btn_bg = "lightgrey"
        self.controller.configure(bg=bg)
        for frame in self.controller.frames.values():
            frame.configure(bg=bg)
            for widget in frame.winfo_children():
                try:
                    widget.configure(bg=bg, fg=fg)
                except:
                    pass
    def save_settings(self):
        messagebox.showinfo("Settings", "Settings saved (placeholder).")

if __name__ == "__main__":
    app = App()
    app.mainloop()
