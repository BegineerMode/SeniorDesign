import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
from PIL import Image, ImageTk
import subprocess, os, time, ctypes, signal
import psutil
import time
import threading
import json
import cv2
import socket
import pickle
import struct
import serial
import numpy as np
from queue import Queue


ZONES_FILE = "zones.json"
arduino_port = "COM3" #change depending on device (COM3 or 6)
baud_rate = 9600
arduino = None


class Logger:
    text_widget = None
    max_lines = 80
    log_file = "network_output.log"
    frozen = False  # ← new

    @staticmethod
    def set_output(widget):
        Logger.text_widget = widget

    @staticmethod
    def freeze(state: bool):
        Logger.frozen = state

    @staticmethod
    def log(message):
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
        log_message = f"{timestamp} {message}\n"
        print(log_message.strip())

        # Log to file
        try:
            with open(Logger.log_file, "a") as f:
                f.write(log_message)
            with open(Logger.log_file, "r") as f:
                lines = f.readlines()
            if len(lines) > Logger.max_lines:
                with open(Logger.log_file, "w") as f:
                    f.writelines(lines[-Logger.max_lines:])
        except Exception as e:
            print(f"[LOGGER ERROR] File logging failed: {e}")

        # Display to GUI unless frozen
        if Logger.text_widget and not Logger.frozen:
            Logger.text_widget.insert(tk.END, log_message)
            Logger.text_widget.see(tk.END)
            gui_lines = int(Logger.text_widget.index('end-1c').split('.')[0])
            if gui_lines > Logger.max_lines:
                Logger.text_widget.delete("1.0", f"{gui_lines - Logger.max_lines + 1}.0")

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WireGuard GUI")
        self.geometry("1300x800")  # or even 1400x900

        self.configure(bg="#1a1a1a")  # Dark fire-themed background
        # Load logo image (flame+substation motif)
        try:
            img = Image.open("logo.png").resize((80, 80))
            self.logo_image = ImageTk.PhotoImage(img)
        except Exception as e:
            self.logo_image = None
            Logger.log(f"Logo not found: {e}")
        # Menu for navigation
        menubar = tk.Menu(self)
        page_menu = tk.Menu(menubar, tearoff=0)
        page_menu.add_command(label="Home", command=lambda: self.show_frame("HomePage"))
        page_menu.add_command(label="Private Network", command=lambda:self.show_frame("PrivateNetworkPage"))
        page_menu.add_command(label="Camera Config", command=lambda: self.show_frame("CameraConfigPage"))
        page_menu.add_command(label="Network Logs", command=lambda: self.show_frame("NetworkLogsPage"))
        page_menu.add_command(label="Data Streaming", command=lambda: self.show_frame("DataStreamingPage"))
        page_menu.add_command(label="System Monitoring", command=lambda: self.show_frame("SystemMonitoringPage"))
        page_menu.add_command(label="Settings", command=lambda: self.show_frame("SettingsPage"))
        page_menu.add_command(label="Calibration / Zones", command=lambda: self.show_frame("CalibrationPage"))
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
                  DataStreamingPage, SystemMonitoringPage, SettingsPage, CalibrationPage):
            frame = F(container, self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        threading.Thread(target=self.connect_arduino, daemon=True).start()
        self.show_frame("HomePage")
        # Ensure Recordings folder exists
        if not os.path.exists("Recordings"):
            os.makedirs("Recordings")

    def connect_arduino(self):
        global arduino
        try:
            arduino = serial.Serial(arduino_port, baud_rate, timeout=1)
            Logger.log(f"Connected to Arduino on {arduino_port}")
        except Exception as e:
            Logger.log(f"Error connecting to Arduino: {e}")
            arduino = None


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
        tk.Label(self, text="Substation Intrusion Detection System - Home", fg="white", bg="#1a1a1a",
                 font=("Arial", 18)).pack(pady=10)
        tk.Label(self, text="Welcome! Use the menu to navigate.", fg="white", bg="#1a1a1a").pack()

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
        self.active_tunnels_var = tk.StringVar()
        self.active_tunnels_var.set("Active Tunnels: None")
        tk.Label(self, textvariable=self.active_tunnels_var, fg="white", bg="#1a1a1a").pack(pady=(5,15))
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
        # Private/Public Key Display
        tk.Label(config_frame, text="Private Key:", fg="white", bg="#1a1a1a").grid(row=3, column=0, sticky="e", padx=5)
        self.private_text = tk.Entry(config_frame, width=60, bg="#333333", fg="white")
        self.private_text.grid(row=3, column=1, padx=5)

        tk.Label(config_frame, text="Public Key:", fg="white", bg="#1a1a1a").grid(row=4, column=0, sticky="e", padx=5)
        self.public_text = tk.Entry(config_frame, width=60, bg="#333333", fg="white")
        self.public_text.grid(row=4, column=1, padx=5)

        tk.Button(config_frame, text="Generate Key Pair", bg="#007700", fg="white",
                command=self.generate_keys).grid(row=5, column=0, columnspan=2, pady=5)

        tk.Button(config_frame, text="Save Config to File", bg="#888800", fg="white",
                command=self.save_config_file).grid(row=6, column=0, columnspan=2, pady=5)
        tk.Button(config_frame, text="Delete Config File", bg="#aa0000", fg="white",
          command=self.delete_config_file).grid(row=7, column=0, columnspan=2, pady=5)


        tk.Button(config_frame, text="Generate Config", command=self.generate_config,
                  bg="#0055aa", fg="white")\
            .grid(row=2, column=0, columnspan=2, pady=5)
        config_frame.columnconfigure((0,1), weight=1)
        self.update_active_tunnels()


    def delete_config_file(self):
        path = filedialog.askopenfilename(
            title="Select Config File to Delete",
            filetypes=[("WireGuard Config", "*")]
        )
        if not path:
            return

        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete:\n{path}?")
        if not confirm:
            return

        try:
            os.remove(path)
            messagebox.showinfo("Deleted", f"File deleted:\n{path}")
            Logger.log(f"File Deleted: {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete file:\n{e}")

    def save_config_file(self):
        config_data = self.config_text.get("1.0", tk.END).strip()
        if not config_data:
            messagebox.showwarning("Empty Config", "No config to save.")
            return

        path = filedialog.asksaveasfilename(defaultextension=".conf",
                                            filetypes=[("WireGuard Config", "*.conf")],
                                            title="Save Config As")
        if not path:
            return  # user cancelled

        try:
            with open(path, "w") as f:
                f.write(config_data)
            messagebox.showinfo("Saved", f"Configuration saved to:\n{path}")
            Logger.log(f"File Created: {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config:\n{e}")

    def get_active_tunnels(self):
        try:
            output = subprocess.check_output(["wg", "show", "interfaces"])
            tunnels = output.decode().split()
            return tunnels
        except Exception:
            pass

    def update_active_tunnels(self):
        active = self.get_active_tunnels()
        if active:
            self.active_tunnels_var.set(f"Active Tunnel(s): {', '.join(active)}")
        else:
            self.active_tunnels_var.set("Active Tunnels: None")

        # 📢 Call itself again after 5 seconds
        self.after(5000, self.update_active_tunnels)

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



    def tunnels(self):
        # Step 1: Ask user if they want to START or STOP a tunnel
        action = messagebox.askquestion("Tunnel Action", "Do you want to start a tunnel? (Select 'No' to stop a tunnel)")
        start_tunnel = True if action == 'yes' else False

        # Step 2: Ask user to select a WireGuard .conf file
        config_path = filedialog.askopenfilename(
            title="Select WireGuard Config",
            filetypes=[("WireGuard Config", "*")]
        )
        if not config_path:
            return  # user canceled the dialog
        

        # Step 3: WireGuard executable path
        wireguard_exe = r"C:\Program Files\WireGuard\wireguard.exe"
        tunnel_name = os.path.splitext(os.path.basename(config_path))[0]
        tunnel_name = tunnel_name.replace(".conf", "")  # name without .conf




        # Step 4: Check admin rights
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except:
            is_admin = False

        try:
            if start_tunnel:
                # ✅ YOUR ORIGINAL WAY: use full config path when starting
                args = [wireguard_exe, "/installtunnelservice", config_path]
                Logger.log(f"Starting Tunnel: {tunnel_name}")
                if is_admin:
                    subprocess.run(args, check=True)
                else:
                    params = f'/installtunnelservice "{config_path}"'
                    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", wireguard_exe, params, None, 1)
                    if result <= 32:
                        raise PermissionError("Failed to elevate permissions.")

                messagebox.showinfo("Success", f"Tunnel '{tunnel_name}' activated.")

            else:
                # 🛑 STOPPING needs just the tunnel name
                args = [wireguard_exe, "/uninstalltunnelservice", tunnel_name]
                Logger.log(f"Stopping Tunnel: {tunnel_name}")
                if is_admin:
                    subprocess.run(args, check=True)
                else:
                    params = f'/uninstalltunnelservice {tunnel_name}'
                    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", wireguard_exe, params, None, 1)
                    if result <= 32:
                        raise PermissionError("Failed to elevate permissions.")

                messagebox.showinfo("Success", f"Tunnel '{tunnel_name}' deactivated.")

            # Step 5: Log activity if relay_var is set
            if self.relay_var.get():
                with open("network.log", "a") as f:
                    f.write(f"[{time.ctime()}] {'Activated' if start_tunnel else 'Deactivated'} tunnel {tunnel_name}\n")

        except Exception as e:
            messagebox.showerror("Error", f"Tunnel operation failed:\n{e}")
    
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

        self.frame_queue = Queue(maxsize=10)

        
        tk.Label(self, text="Camera Configuration", fg="orange", bg="#1a1a1a",
                 font=("Arial", 16)).pack(pady=5)
        
        self.recording = False
        self.video_writer = None
        self.ai_process = None  

        # FFmpeg command option
        self.use_default = tk.BooleanVar(value=True)
        self.ffmpeg_cmd_entry = tk.Entry(self, width=80, bg="#333333", fg="white")
        default_cmd = "ffmpeg -r 30 -i Scene2Cam1.ts -an -c:v libx264 -preset veryfast -tune zerolatency -crf 23 -minrate 3000k -maxrate 3000k -bufsize 16000k -g 60 -f mpegts udp://127.0.0.1:12345?pkt_size=1316"
        #/ffmpeg -f gdigrab -framerate 30 -i desktop -vcodec libx264 -preset ultrafast -tune zerolatency -f mpegts udp://127.0.0.1:6000
        #ffmpeg -f v4l2 -i /dev/video0 -c:v libx264 -preset veryfast -tune zerolatency -f mpegts udp://<dest_ip>:1234
        self.ffmpeg_cmd_entry.insert(0, default_cmd)
        self.ffmpeg_cmd_entry.pack(padx=10, pady=5, fill="x")

        self.ffmpeg_cmd_entry2 = tk.Entry(self, width=80, bg="#333333", fg="white")
        default_cmd2 = "ffmpeg -r 30 -i Scene2Cam2.ts -an -c:v libx264 -preset veryfast -tune zerolatency -crf 23 -minrate 3000k -maxrate 3000k -bufsize 16000k -g 60 -f mpegts udp://127.0.0.1:12346?pkt_size=1316"
        #/ffmpeg -f gdigrab -framerate 30 -i desktop -vcodec libx264 -preset ultrafast -tune zerolatency -f mpegts udp://127.0.0.1:6000
        #ffmpeg -f v4l2 -i /dev/video0 -c:v libx264 -preset veryfast -tune zerolatency -f mpegts udp://<dest_ip>:1234
        self.ffmpeg_cmd_entry2.insert(0, default_cmd2)
        self.ffmpeg_cmd_entry2.pack(padx=10, pady=5, fill="x")

        self.ffmpeg_cmd_entry_receiving = tk.Entry(self, width=80, bg="#333333", fg="white")
        default_cmd_receiving = "udp://127.0.0.1:12345?fifo_size=1000000&overrun_nonfatal=1"
        self.ffmpeg_cmd_entry_receiving.insert(0, default_cmd_receiving)
        self.ffmpeg_cmd_entry_receiving.pack(padx=10, pady=5, fill="x")
        
        self.ffmpeg_cmd_entry_receiving2 = tk.Entry(self, width=80, bg="#333333", fg="white")
        default_cmd_receiving2 = "udp://127.0.0.1:12346?fifo_size=1000000&overrun_nonfatal=1"
        self.ffmpeg_cmd_entry_receiving2.insert(0, default_cmd_receiving2)
        self.ffmpeg_cmd_entry_receiving2.pack(padx=10, pady=5, fill="x")
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
        self.start_recv_btn = tk.Button(send_frame, text="Start Receiving Feeds",
                                        command=self.start_receiving, bg="#00aa00", fg="white")
        self.start_recv_btn.grid(row=0, column=2, padx=5)

        # self.start_ai_btn = tk.Button(send_frame, text="Start AI Feed", command=self.start_ai_stream_listener,
        #                       bg="#4444aa", fg="white")
        # self.start_ai_btn.grid(row=0, column=4, padx=5)

        self.stop_recv_btn = tk.Button(send_frame, text="Stop Receiving Feeds",
                                       command=self.stop_receiving, bg="#aa0000", fg="white", state="disabled")
        self.stop_recv_btn.grid(row=0, column=3, padx=5)
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
        # Live display placeholders
        display_frame = tk.Frame(self, bg="#1a1a1a", height=700)
        display_frame.pack(fill="both", expand=False, pady=(10, 0))

        self.cam1_label = tk.Label(display_frame, text="Live Feed", bg="black", fg="white")
        self.cam1_label.config(width=960, height=480)
        self.cam1_label.pack(pady=(10, 0))  # Push down by 40 pixels

        self.cam1_label.pack_propagate(False)


        self.cam1_label.pack_propagate(False)
        display_frame.pack_propagate(False)
        display_frame.config(height=660, width=1280)
        self.cam1_label.update_idletasks()




        # self.cam2_label = tk.Label(display_frame, text="Live Feed 2",
        #                            bg="black", fg="white", width=40, height=10)
        # self.cam2_label.grid(row=0, column=1, padx=5)
        
        # # Schedule options
        # sched_frame = tk.Frame(self, bg="#1a1a1a")
        # sched_frame.pack(pady=5, fill="x")
        # tk.Label(sched_frame, text="Add Recording Schedule (HH:MM):",
        #          fg="white", bg="#1a1a1a").grid(row=0, column=0, padx=5)
        # self.schedule_entry = tk.Entry(sched_frame, width=10, bg="#333333", fg="white")
        # self.schedule_entry.grid(row=0, column=1)
        # tk.Button(sched_frame, text="Add", command=self.add_schedule,
        #           bg="#0055aa", fg="white").grid(row=0, column=2, padx=5)
        # self.schedule_list = tk.Listbox(sched_frame, bg="#222222", fg="white", height=4)
        # self.schedule_list.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="we")
        # sched_frame.columnconfigure(2, weight=1)
        # self.recording_schedule = []



    # def start_ai_stream_listener(self):
    #     server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #     try:
    #         server_socket.bind(("0.0.0.0", 9999))
    #         server_socket.listen(1)
    #         print("[LISTENER] Waiting for AI feed on port 9999...")
    #     except Exception as e:
    #         messagebox.showerror("Socket Error", f"Failed to bind socket: {e}")
    #         return

    #     def accept_connection():
    #         try:
    #             conn, _ = server_socket.accept()
    #             print("[LISTENER] AI feed connected.")
    #             threading.Thread(target=self.receive_ai_frames, args=(conn,), daemon=True).start()
    #             self.display_from_queue()  # call it directly — it uses Tkinter's after()
    #         except Exception as e:
    #             messagebox.showerror("Connection Error", f"Failed to accept AI connection: {e}")

    #     threading.Thread(target=accept_connection, daemon=True).start()

    # def receive_ai_frames(self, conn):
    #     recv_last = time.time()
    #     recv_frames =0
    #     data = b""
    #     header_size = struct.calcsize(">LLL")
    #     while True:
    #         try:
    #             while len(data) < header_size:
    #                 packet = conn.recv(4096)
    #                 if not packet:
    #                     return
    #                 data += packet

    #             packed_header = data[:header_size]
    #             data = data[header_size:]
    #             frame_size, w, h = struct.unpack(">LLL", packed_header)

    #             while len(data) < frame_size:
    #                 data += conn.recv(4096)

    #             frame_data = data[:frame_size]
    #             data = data[frame_size:]
    #             frame = np.frombuffer(frame_data, dtype=np.uint8).reshape((h, w, 3))

    #             if not self.frame_queue.full():
    #                 self.frame_queue.put(frame)
    #                 recv_frames += 1
    #                 if time.time() - recv_last >= 1:
    #                     print(f"[RECEIVER FPS] {recv_frames}")
    #                     recv_frames = 0
    #                     recv_last = time.time()



    #         except Exception as e:
    #             print(f"[RECEIVER ERROR] {e}")
    #             break

    # def display_from_queue(self):
    #     def update_frame():
    #         if not self.frame_queue.empty():
    #             frame = self.frame_queue.get()
    #             cv2.imshow("Live Feed", frame)
    #             cv2.waitKey(1)
    #         self.after(1, update_frame)
    #     self.after(1, update_frame)





    def update_clock(self):
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=now)
        self.after(1000, self.update_clock)
    def start_sending(self):
        cmd = self.ffmpeg_cmd_entry.get() if not self.use_default.get() else self.ffmpeg_cmd_entry.get()
        cmd2 = self.ffmpeg_cmd_entry2.get() if not self.use_default.get() else self.ffmpeg_cmd_entry2.get()
        self.start_response_listener()  # 👈 Add this
        try:
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
            self.send_proc = subprocess.Popen(cmd, shell=True, creationflags=creationflags)
            creationflags2 = subprocess.CREATE_NEW_PROCESS_GROUP
            self.send_proc2 = subprocess.Popen(cmd2, shell=True, creationflags=creationflags2)
            self.start_send_btn.config(state="disabled")
            self.stop_send_btn.config(state="normal")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start sending feed: {e}")
    def stop_sending(self):
        try:
            # Safely terminate process 1
            if hasattr(self, 'send_proc') and self.send_proc:
                if self.send_proc.poll() is None:
                    self.send_proc.send_signal(signal.CTRL_BREAK_EVENT)
                    self.send_proc.wait(timeout=5)
                self.send_proc = None  # Clean up even if already exited

            # Safely terminate process 2
            if hasattr(self, 'send_proc2') and self.send_proc2:
                if self.send_proc2.poll() is None:
                    self.send_proc2.send_signal(signal.CTRL_BREAK_EVENT)
                    self.send_proc2.wait(timeout=5)
                self.send_proc2 = None  # Clean up

        except subprocess.TimeoutExpired:
            print("[STOP] FFmpeg timeout — force kill")
            # ⬇️
            Logger.log("[STOP] FFmpeg timeout — force kill")

            if self.send_proc:
                self.send_proc.kill()
            if self.send_proc2:
                self.send_proc2.kill()
        except Exception as e:
            print(f"[STOP] Error: {e}")
            # ⬇️
            Logger.log(f"[STOP] Error: {e}")

        finally:
            self.start_send_btn.config(state="normal")
            self.stop_send_btn.config(state="disabled")
    def start_receiving(self):
        
        #self.cam2_label.config(text="Receiving Feed 2...")
        cmd = self.ffmpeg_cmd_entry_receiving.get() if not self.use_default.get() else self.ffmpeg_cmd_entry_receiving.get()
        cmd2 = self.ffmpeg_cmd_entry_receiving2.get() if not self.use_default.get() else self.ffmpeg_cmd_entry_receiving2.get()

        config = {
            "camera1": cmd,
            "camera2": cmd2,
            # Add more entries as needed
        }

        try:
            # Save to JSON
            with open("ai_config.json", "w") as f:
                json.dump(config, f, indent=4)
            print("[CONFIG] Saved to ai_config.json")
            # ⬇️
            Logger.log("[CONFIG] Saved to ai_config.json")

            # Start finalcamera.py
            creationflags3 = subprocess.CREATE_NEW_PROCESS_GROUP
            self.ai_process = subprocess.Popen(["python", "finalcamera.py"], creationflags = subprocess.CREATE_NEW_PROCESS_GROUP)
            print("Attempting to start")
            # ⬇️
            Logger.log("Attempting to start finalcamera.py")
        except Exception as e:
            print(f"[ERROR] Failed to save or launch: {e}")
            # ⬇️
            Logger.log(f"[ERROR] Failed to save or launch: {e}")

        finally:
            self.stop_recv_btn.config(state="normal")
            self.start_recv_btn.config(state="disabled")
    def stop_receiving(self):
    # self.cam2_label.config(text="Live Feed 2")

        if self.ai_process and self.ai_process.poll() is None:
            try:
                self.ai_process.send_signal(signal.CTRL_BREAK_EVENT)
                self.ai_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("[STOP] Timeout - killing process...")
                # ⬇️
                Logger.log("[STOP] Timeout - killing process...")

                self.ai_process.kill()
            finally:
                self.ai_process = None  # ✅ Clear the reference
        else:
            print("[STOP] No active process or already stopped.")
            # ⬇️
            Logger.log("[STOP] No active process or already stopped.")


        # ✅ Move this outside of the if-block to always reset GUI
        self.start_recv_btn.config(state="normal")
        self.stop_recv_btn.config(state="disabled")


    def start_recording(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(("127.0.0.1", 10002))
                sock.sendall(b"StartRecording")
            self.start_rec_btn.config(state="disabled")
            self.stop_rec_btn.config(state="normal")
        except Exception as e:
            messagebox.showerror("Recording Error", f"Failed to start recording: {e}")


    def stop_recording(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(("127.0.0.1", 10002))
                sock.sendall(b"StopRecording")
            self.start_rec_btn.config(state="normal")
            self.stop_rec_btn.config(state="disabled")
        except Exception as e:
            messagebox.showerror("Recording Error", f"Failed to stop recording: {e}")


    
    def start_response_listener(self):
        def listen():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
                server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                port_wanted = 10000
                server_sock.bind(("0.0.0.0", port_wanted))  # Set to your preferred port
                server_sock.listen(1)
                print(f"[SOCKET] Waiting for AI response on 0.0.0.0:{port_wanted}")
                # ⬇️
                Logger.log(f"[SOCKET] Waiting for AI response on 0.0.0.0:{port_wanted}")


                while True:
                    try:
                        conn, addr = server_sock.accept()
                        with conn:
                            print(f"[SOCKET] Connected by {addr}")
                            # ⬇️
                            Logger.log(f"[SOCKET] Connected by {addr}")

                            while True:
                                data = conn.recv(1024)
                                if not data:
                                    break
                                message = data.decode()
                                print(f"[SOCKET] Message received: {message}")
                                # ⬇️
                                Logger.log(f"[SOCKET] Message received: {message}")

                                if message == "Alarm":
                                    arduino.write(b"RED_ON\n")
                                # Optional: Update GUI label or text box with message
                                if message == "Stop":
                                    arduino.write(b"RED_OFF\n")
                    except Exception as e:
                        print(f"[SOCKET] Listener error: {e}")
                        # ⬇️
                        Logger.log(f"[SOCKET] Listener error: {e}")

                        break

        threading.Thread(target=listen, daemon=True).start()

    # def add_schedule(self):
    #     time_str = self.schedule_entry.get().strip()
    #     if time_str:
    #         self.schedule_list.insert(tk.END, time_str)
    #         self.recording_schedule.append(time_str)
    #         self.schedule_entry.delete(0, tk.END)

class NetworkLogsPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        tk.Label(self, text="Network Logs", fg="orange", bg="#1a1a1a",
                 font=("Arial", 16)).pack(pady=5)
        self.last_size = 0
        self.text = tk.Text(self, bg="#222222", fg="white")
        self.text.pack(fill="both", expand=True, padx=10, pady=10)
        Logger.set_output(self.text)

        # Load past logs from file
        try:
            if os.path.exists(Logger.log_file):
                with open(Logger.log_file, "r") as f:
                    lines = f.readlines()[-Logger.max_lines:]
                    for line in lines:
                        self.text.insert(tk.END, line)
                self.text.see(tk.END)
        except Exception as e:
            Logger.log(f"[LOGGER ERROR] Failed to load previous logs: {e}")

        self.freeze = False
        self.stop_event = threading.Event()

        btn_frame = tk.Frame(self, bg="#1a1a1a")
        btn_frame.pack(pady=5)
        self.freeze_btn = tk.Button(btn_frame, text="Freeze", command=self.toggle_freeze,
                                    bg="#ffaa00", fg="black")
        self.freeze_btn.grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Clear Logs", command=self.clear_logs,
                  bg="#0055aa", fg="white").grid(row=0, column=1, padx=5)

    def toggle_freeze(self):
        self.freeze = not self.freeze
        Logger.freeze(self.freeze)
        self.freeze_btn.config(text="Unfreeze" if self.freeze else "Freeze")


    def clear_logs(self):
        self.text.delete("1.0", tk.END)

class DataStreamingPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.is_paused = False  # Track pause state
        self.fast_forward = False  # Track fast-forward state
        self.frame_rate = 30  # FPS assumed



        tk.Label(self, text="Data Streaming (Recordings)", fg="orange", bg="#1a1a1a",
                 font=("Arial", 16)).pack(pady=5)

        # Main content frame (horizontal split)
        content_frame = tk.Frame(self, bg="#1a1a1a")
        content_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Left: File list
        self.listbox = tk.Listbox(content_frame, bg="#222222", fg="white", width=40)
        self.listbox.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.listbox.bind('<Double-1>', self.play_selected)

        # Right: Video feed + close button
        self.video_container = tk.Frame(content_frame, bg="#1a1a1a")
        self.video_container.pack(side="right", padx=5)

        self.video_label = tk.Label(self.video_container, bg="black", width=960, height=480)
        self.video_label.pack()

        btn_frame = tk.Frame(self.video_container, bg="#1a1a1a")
        btn_frame.pack(pady=5)

        self.pause_btn = tk.Button(btn_frame, text="Pause", command=self.toggle_pause,
                                bg="#ffaa00", fg="black", width=6)
        self.pause_btn.grid(row=0, column=0, padx=5)

        self.ff_btn = tk.Button(btn_frame, text=">>", command=self.toggle_fast_forward,
                        bg="#0077ff", fg="white", width=4)
        self.ff_btn.grid(row=0, column=2, padx=5)

        # ⏪ Rewind
        self.rewind_btn = tk.Button(btn_frame, text="⏪", command=self.rewind_video,
                                    bg="#555555", fg="white", width=4)
        self.rewind_btn.grid(row=0, column=3, padx=5)

        # Timestamp entry
        self.timestamp_entry = tk.Entry(btn_frame, width=8, bg="#333333", fg="white")
        self.timestamp_entry.grid(row=0, column=4, padx=(10, 0))

        self.jump_btn = tk.Button(btn_frame, text="Go", command=self.jump_to_time,
                                bg="#0055aa", fg="white")
        self.jump_btn.grid(row=0, column=5, padx=5)



        self.close_btn = tk.Button(btn_frame, text="X", command=self.stop_video,
                                bg="#aa0000", fg="white", width=3)
        self.close_btn.grid(row=0, column=1, padx=5)

        self.cap = None
        self.frame_after_id = None

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if hasattr(self, 'pause_btn'):
            self.pause_btn.config(text="Resume" if self.is_paused else "Pause")

    def toggle_fast_forward(self):
        self.fast_forward = not self.fast_forward
        self.ff_btn.config(bg="#00cc00" if self.fast_forward else "#0077ff")

    def rewind_video(self):
        if self.cap:
            current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            target_frame = max(0, current_frame - (self.frame_rate * 5))  # Go back 5 seconds
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

    def jump_to_time(self):
        if not self.cap:
            return
        time_str = self.timestamp_entry.get().strip()
        try:
            parts = list(map(int, time_str.split(":")))
            if len(parts) == 3:
                h, m, s = parts
            elif len(parts) == 2:
                h = 0
                m, s = parts
            elif len(parts) == 1:
                h = 0
                m = 0
                s = parts[0]
            else:
                raise ValueError("Invalid format")

            total_seconds = h * 3600 + m * 60 + s
            frame_num = int(total_seconds * self.frame_rate)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        except Exception:
            messagebox.showerror("Invalid Input", "Use format HH:MM:SS or MM:SS")

    def on_show(self):
        self.refresh_list()

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        files = sorted(os.listdir("Recordings"))
        for f in files:
            if f.lower().endswith((".mp4", ".ts", ".mov")):
                self.listbox.insert(tk.END, f)

    def play_selected(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return
        filename = self.listbox.get(sel[0])
        path = os.path.join("Recordings", filename)

        self.stop_video()
        self.cap = cv2.VideoCapture(path)
        self.update_frame()

    def update_frame(self):
        if self.cap and self.cap.isOpened():
            if self.is_paused:
                self.frame_after_id = self.after(100, self.update_frame)
                return

            ret, frame = self.cap.read()
            if ret:
                # Resize and convert color for Tkinter display
                frame = cv2.resize(frame, (960, 480))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(image=img)

                # Update label with new frame
                self.video_label.imgtk = imgtk
                self.video_label.config(image=imgtk)

                # Schedule next frame
                delay = 5 if self.fast_forward else 30
                self.frame_after_id = self.after(delay, self.update_frame)

            else:
                self.stop_video()


    def stop_video(self):
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.frame_after_id:
            self.after_cancel(self.frame_after_id)
            self.frame_after_id = None
        self.video_label.config(image="")

    # def play_selected(self, event):
    #     sel = self.listbox.curselection()
    #     if sel:
    #         filename = self.listbox.get(sel[0])
    #         path = os.path.join("Recordings", filename)
    #         try:
    #             if os.name == 'nt':
    #                 os.startfile(path)
    #             else:
    #                 subprocess.Popen(['xdg-open', path])
    #         except Exception as e:
    #             messagebox.showerror("Error", f"Cannot open file: {e}")

class CalibrationPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        tk.Label(self, text="Calibration / Virtual Zones", fg="orange", bg="#1a1a1a",
                 font=("Arial", 16)).pack(pady=10)

        # ZONE CONFIG AREA
        zone_frame = tk.LabelFrame(self, text="Add Virtual Zone", bg="#1a1a1a", fg="orange")
        zone_frame.pack(pady=10, padx=10, fill="x")

        # VIEW ZONES AREA
        view_frame = tk.LabelFrame(self, text="View All Zones", bg="#1a1a1a", fg="orange")
        view_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.zone_listbox = tk.Listbox(view_frame, bg="#222222", fg="white", width=50, height=6)
        self.zone_listbox.pack(padx=10, pady=5, fill="both", expand=True)

        self.remove_zone_btn = tk.Button(view_frame, text="Remove Selected Zone", bg="#aa0000", fg="white",
                                 command=self.remove_selected_zone)
        self.remove_zone_btn.pack(pady=5)


        scrollbar = tk.Scrollbar(view_frame)
        scrollbar.pack(side="right", fill="y")
        self.zone_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.zone_listbox.yview)

        tk.Label(zone_frame, text="Zone Name:", fg="white", bg="#1a1a1a").grid(row=0, column=0, padx=5, sticky="e")
        self.zone_name_entry = tk.Entry(zone_frame, width=30, bg="#333333", fg="white")
        self.zone_name_entry.grid(row=0, column=1, padx=5, columnspan=3)

        self.zone_points = []
        for i in range(4):
            tk.Label(zone_frame, text=f"Point {i+1} X:", fg="white", bg="#1a1a1a").grid(row=i+1, column=0, sticky="e", padx=5)
            x_entry = tk.Entry(zone_frame, width=10, bg="#333333", fg="white")
            x_entry.grid(row=i+1, column=1, padx=5)

            tk.Label(zone_frame, text="Z:", fg="white", bg="#1a1a1a").grid(row=i+1, column=2, sticky="e")
            z_entry = tk.Entry(zone_frame, width=10, bg="#333333", fg="white")
            z_entry.grid(row=i+1, column=3, padx=5)

            self.zone_points.append((x_entry, z_entry))

        # Button moved to row 5
        tk.Button(zone_frame, text="Add Zone", bg="#0055aa", fg="white",
                command=self.submit_zone).grid(row=5, column=0, columnspan=4, pady=10)

        # Track all zones
        self.zones = {}
        self.load_zones_from_file()



        # # CALIBRATION VALUES AREA
        # calib_frame = tk.LabelFrame(self, text="Set Calibration Values", bg="#1a1a1a", fg="orange")
        # calib_frame.pack(pady=10, padx=10, fill="x")

        # tk.Label(calib_frame, text="A Value:", fg="white", bg="#1a1a1a").grid(row=0, column=0, padx=5, sticky="e")
        # self.a_entry = tk.Entry(calib_frame, width=20, bg="#333333", fg="white")
        # self.a_entry.grid(row=0, column=1, padx=5)

        # tk.Label(calib_frame, text="B Value:", fg="white", bg="#1a1a1a").grid(row=1, column=0, padx=5, sticky="e")
        # self.b_entry = tk.Entry(calib_frame, width=20, bg="#333333", fg="white")
        # self.b_entry.grid(row=1, column=1, padx=5)
        
        # tk.Label(calib_frame, text="C Value:", fg="white", bg="#1a1a1a").grid(row=2, column=0, padx=5, sticky="e")
        # self.c_entry = tk.Entry(calib_frame, width=20, bg="#333333", fg="white")
        # self.c_entry.grid(row=2, column=1, padx=5)

        # tk.Button(calib_frame, text="Submit Calibration", bg="#0055aa", fg="white",
        #           command=self.submit_calibration).grid(row=3, column=0, columnspan=2, pady=10)

        # self.status_label = tk.Label(self, text="", fg="white", bg="#1a1a1a")
        # self.status_label.pack(pady=10)

    def save_zones_to_file(self):
        try:
            with open(ZONES_FILE, "w") as f:
                json.dump(self.zones, f, indent=4)
            print("[ZONES] Zones saved to zones.json")
            # ⬇️
            Logger.log("[ZONES] Zones saved to zones.json")

        except Exception as e:
            print(f"[ERROR] Failed to save zones: {e}")
            # ⬇️
            Logger.log(f"[ERROR] Failed to save zones: {e}")


    def load_zones_from_file(self):
        if not os.path.exists(ZONES_FILE):
            return

        try:
            with open(ZONES_FILE, "r") as f:
                self.zones = json.load(f)
            self.update_zone_listbox()
            print(f"[ZONES] Loaded zones from {ZONES_FILE}")
            # ⬇️
            Logger.log(f"[ZONES] Loaded zones from {ZONES_FILE}")

        except Exception as e:
            print(f"[ERROR] Failed to load zones: {e}")
            # ⬇️
            Logger.log(f"[ERROR] Failed to load zones: {e}")


    def remove_selected_zone(self):
        selection = self.zone_listbox.curselection()
        if not selection:
            self.status_label.config(text="No zone selected to remove.", fg="red")
            return

        # Get selected zone name
        line = self.zone_listbox.get(selection[0])
        zone_name = line.split(":")[0]

        # Remove from dict and update listbox
        if zone_name in self.zones:
            del self.zones[zone_name]
            self.status_label.config(text=f"Removed zone: {zone_name}", fg="white")
            Logger.log(f"Removed Zone: {zone_name}")
            self.update_zone_listbox()
            self.save_zones_to_file()

        else:
            self.status_label.config(text=f"Zone '{zone_name}' not found.", fg="red")


    def submit_zone(self):
        zone_name = self.zone_name_entry.get().strip()
        if not zone_name:
            zone_name = f"zone{len(getattr(self, 'zones', {})) + 1}"

        coords = []
        try:
            for x_entry, z_entry in self.zone_points:
                x = float(x_entry.get())
                z = float(z_entry.get())
                coords.append([x, z])
        except ValueError:
            self.status_label.config(text="All coordinates must be valid numbers.", fg="red")
            return

        if len(coords) != 4:
            self.status_label.config(text="Exactly 4 (x, z) points required.", fg="red")
            return

        # Store the zone
        if not hasattr(self, 'zones'):
            self.zones = {}
        self.zones[zone_name] = coords
        self.status_label.config(text=f"Zone '{zone_name}' added.", fg="white")

        # Clear inputs
        self.zone_name_entry.delete(0, tk.END)
        for x_entry, z_entry in self.zone_points:
            x_entry.delete(0, tk.END)
            z_entry.delete(0, tk.END)
        print(f"[ZONES] Current zones: {self.zones}")
        # ⬇️
        Logger.log(f"[ZONES] Current zones: {self.zones}")


        self.update_zone_listbox()
        self.save_zones_to_file()


    def update_zone_listbox(self):
        self.zone_listbox.delete(0, tk.END)
        for name, coords in self.zones.items():
            line = f"{name}: {coords}"
            self.zone_listbox.insert(tk.END, line)



    # def submit_calibration(self):
    #     a = self.a_entry.get().strip()
    #     b = self.b_entry.get().strip()
    #     c = self.c_entry.get().strip()
    #     if a and b and c:
    #         self.status_label.config(text=f"Calibration values set: A = {a}, B = {b}, C = {c}", fg="white")

    #         # Save to JSON file
    #         calib_data = {"a": a, "b": b, "c": c}
    #         with open("calibration.json", "w") as f:
    #             json.dump(calib_data, f)
    #     else:
    #         self.status_label.config(text="Both 'a' and 'b' values are required.", fg="red")

class SystemMonitoringPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        tk.Label(self, text="System Monitoring", fg="orange", bg="#1a1a1a",
                 font=("Arial", 16)).pack(pady=5)
        self.cpu_label = tk.Label(self, text="", fg="white", bg="#1a1a1a")
        self.cpu_label.pack()
        self.mem_label = tk.Label(self, text="", fg="white", bg="#1a1a1a")
        self.mem_label.pack()
        self.tunnel_status_label = tk.Label(self, text="", fg="white", bg="#1a1a1a")
        self.tunnel_status_label.pack()
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
            self.tunnel_status_label.config(text="wg0 interface not active")
        self.uptime_label.config(text=f"Uptime: {hours}h {mins}m")
        self.after(5000, self.update_stats)
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
        

class SettingsPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.controller = controller

        tk.Label(self, text="Settings", fg="orange", bg="#1a1a1a",
                 font=("Arial", 16)).pack(pady=5)

        self.settings_path = "settings.json"
        self.settings = self.load_settings()

        # Dark mode
        self.dark_mode_var = tk.BooleanVar(value=self.settings.get("dark_mode", True))
        tk.Checkbutton(self, text="Dark Mode", variable=self.dark_mode_var,
                       command=self.toggle_dark_mode,
                       fg="white", bg="#1a1a1a", selectcolor="#333333",
                       activebackground="#333333", activeforeground="white").pack(anchor="w", padx=10, pady=5)

        self.entries = {}

        fields = [
            ("arduino_port", "Arduino COM Port"),
            ("socket_ai_response_ip", "AI Response IP"),
            ("socket_ai_response_port", "AI Response Port"),
            ("socket_recording_port", "Recording Socket Port"),
            ("camera1_receive_url", "Camera 1 Receive URL"),
            ("camera2_receive_url", "Camera 2 Receive URL"),
            ("frame_rate", "Default Frame Rate"),
            ("log_file", "Log File Name")
        ]

        for key, label in fields:
            frame = tk.Frame(self, bg="#1a1a1a")
            frame.pack(anchor="w", padx=10, pady=2, fill="x")
            tk.Label(frame, text=label + ":", fg="white", bg="#1a1a1a").pack(side="left")
            entry = tk.Entry(frame, width=40, bg="#333333", fg="white")
            entry.insert(0, self.settings.get(key, ""))
            entry.pack(side="left", padx=5)
            self.entries[key] = entry

        tk.Button(self, text="Save Settings", command=self.save_settings,
                  bg="#0055aa", fg="white").pack(pady=10)

    def toggle_dark_mode(self):
        if self.dark_mode_var.get():
            bg = "#1a1a1a"; fg = "white"
        else:
            bg = "white"; fg = "black"
        self.controller.configure(bg=bg)
        for frame in self.controller.frames.values():
            frame.configure(bg=bg)
            for widget in frame.winfo_children():
                try:
                    widget.configure(bg=bg, fg=fg)
                except:
                    pass

    def load_settings(self):
        try:
            with open(self.settings_path, "r") as f:
                return json.load(f)
        except:
            return {}

    def save_settings(self):
        updated = {key: entry.get() for key, entry in self.entries.items()}
        updated["dark_mode"] = self.dark_mode_var.get()
        try:
            with open(self.settings_path, "w") as f:
                json.dump(updated, f, indent=4)
            messagebox.showinfo("Settings", "Settings saved successfully.")
        except Exception as e:
            messagebox.showerror("Settings", f"Failed to save settings: {e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
