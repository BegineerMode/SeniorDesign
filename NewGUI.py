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
            print("Logo not found:", e)
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
        tk.Button(config_frame, text="Generate Config", command=self.generate_config,
                  bg="#0055aa", fg="white")\
            .grid(row=2, column=0, columnspan=2, pady=5)
        config_frame.columnconfigure((0,1), weight=1)
        self.update_active_tunnels()

        
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

    # def generate_keys(self):
    #     """Generate WireGuard private/public key pair and display/save them."""
    #     try:
    #         priv = subprocess.check_output("wg genkey", shell=True).decode().strip()
    #         pub = subprocess.check_output(f"echo {priv} | wg pubkey", shell=True).decode().strip()
    #     except Exception as e:
    #         messagebox.showerror("Error", f"Key generation failed: {e}")
    #         return
    #     # Display keys in text boxes
    #     self.private_text.delete(0, tk.END); self.private_text.insert(0, priv)
    #     self.public_text.delete(0, tk.END); self.public_text.insert(0, pub)
    #     # Save keys to config folder
    #     config_folder = "/etc/wireguard"
    #     os.makedirs(config_folder, exist_ok=True)
    #     priv_file = os.path.join(config_folder, "private.key")
    #     pub_file = os.path.join(config_folder, "public.key")
    #     try:
    #         with open(priv_file, "w") as f: f.write(priv)
    #         with open(pub_file, "w") as f: f.write(pub)
    #         os.chmod(priv_file, 0o600)  # secure permissions
    #         messagebox.showinfo("Saved", f"Keys saved to {config_folder}")
    #     except Exception as e:
    #         messagebox.showerror("Error", f"Failed to save keys: {e}")



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
        
        tk.Label(self, text="Camera Configuration", fg="orange", bg="#1a1a1a",
                 font=("Arial", 16)).pack(pady=5)
        
        self.recording = False
        self.video_writer = None
        self.ai_process = None  

        # FFmpeg command option
        self.use_default = tk.BooleanVar(value=True)
        self.ffmpeg_cmd_entry = tk.Entry(self, width=80, bg="#333333", fg="white")
        default_cmd = "ffmpeg -r 30 -i http://192.168.1.134:8080 -an -c:v libx264 -preset veryfast -tune zerolatency -crf 23 -minrate 3000k -maxrate 3000k -bufsize 16000k -g 60 -f mpegts udp://127.0.0.1:12345?pkt_size=1316"
        #/ffmpeg -f gdigrab -framerate 30 -i desktop -vcodec libx264 -preset ultrafast -tune zerolatency -f mpegts udp://127.0.0.1:6000
        #ffmpeg -f v4l2 -i /dev/video0 -c:v libx264 -preset veryfast -tune zerolatency -f mpegts udp://<dest_ip>:1234
        self.ffmpeg_cmd_entry.insert(0, default_cmd)
        self.ffmpeg_cmd_entry.pack(padx=10, pady=5, fill="x")

        self.ffmpeg_cmd_entry2 = tk.Entry(self, width=80, bg="#333333", fg="white")
        default_cmd2 = "ffmpeg -r 30 -i http://192.168.1.107:8080 -an -c:v libx264 -preset veryfast -tune zerolatency -crf 23 -minrate 3000k -maxrate 3000k -bufsize 16000k -g 60 -f mpegts udp://127.0.0.1:12346?pkt_size=1316"
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

        self.start_ai_btn = tk.Button(send_frame, text="Start AI Feed", command=self.start_ai_stream_listener,
                              bg="#4444aa", fg="white")
        self.start_ai_btn.grid(row=0, column=4, padx=5)

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



    def start_ai_stream_listener(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            server_socket.bind(("0.0.0.0", 9999))  # Accept on all interfaces
            server_socket.listen(1)
            print("CameraConfigPage: Waiting for AI feed...")
        except Exception as e:
            messagebox.showerror("Socket Error", f"Failed to bind socket: {e}")
            return

        def accept_connection():
            try:
                conn, _ = server_socket.accept()
                print("AI Feed connected")
                self.receive_ai_frames(conn)
            except Exception as e:
                messagebox.showerror("Connection Error", f"AI feed connection failed: {e}")

        threading.Thread(target=accept_connection, daemon=True).start()

    def receive_ai_frames(self, conn):
        data = b""
        payload_size = struct.calcsize(">L")
        while True:
            try:
                while len(data) < payload_size:
                    packet = conn.recv(4096)
                    if not packet:
                        return
                    data += packet
                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack(">L", packed_msg_size)[0]

                while len(data) < msg_size:
                    data += conn.recv(4096)
                frame_data = data[:msg_size]
                data = data[msg_size:]

                frame = pickle.loads(frame_data)
                self.display_frame(frame)
            except Exception as e:
                print(f"Error receiving AI frame: {e}")
                break

    def display_frame(self, frame):
        h, w = frame.shape[:2]

        # ✅ Convert original to RGB for padding + display
        display_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # ✅ Add visual-only top padding
        top_padding = 280
        padded_display_rgb = cv2.copyMakeBorder(display_rgb, top_padding, 0, 0, 0, cv2.BORDER_CONSTANT, value=(0, 0, 0))

        # ✅ Convert to PIL image and display
        img = Image.fromarray(padded_display_rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        self.cam1_label.imgtk = imgtk
        self.cam1_label.configure(image=imgtk, width=w, height=h + top_padding, text="")

        # ✅ Record original frame (unmodified, BGR)
        if self.recording and self.video_writer:
            self.video_writer.write(frame)




    def update_clock(self):
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=now)
        self.after(1000, self.update_clock)
    def start_sending(self):
        cmd = self.ffmpeg_cmd_entry.get() if not self.use_default.get() else self.ffmpeg_cmd_entry.get()
        cmd2 = self.ffmpeg_cmd_entry2.get() if not self.use_default.get() else self.ffmpeg_cmd_entry2.get()
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
        if hasattr(self, 'send_proc') and self.send_proc.poll() is None:
            try:
                self.send_proc.send_signal(signal.CTRL_BREAK_EVENT)
                self.send_proc.wait(timeout=5)
                self.send_proc2.send_signal(signal.CTRL_BREAK_EVENT)
                self.send_proc2.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.send_proc.kill()
                self.send_proc2.kill()
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

        self.start_response_listener()  # 👈 Add this


        try:
            # Save to JSON
            with open("ai_config.json", "w") as f:
                json.dump(config, f, indent=4)
            print("[CONFIG] Saved to ai_config.json")

            # Start finalcamera.py
            creationflags3 = subprocess.CREATE_NEW_PROCESS_GROUP
            self.ai_process = subprocess.Popen(["python", "finalcamera.py"], creationflags = subprocess.CREATE_NEW_PROCESS_GROUP)
            print("Attempting to start")
        except Exception as e:
            print(f"[ERROR] Failed to save or launch: {e}")
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
                print("[STOP] Timeout – killing process...")
                self.ai_process.kill()
            finally:
                self.ai_process = None  # ✅ Clear the reference
        else:
            print("[STOP] No active process or already stopped.")

        # ✅ Move this outside of the if-block to always reset GUI
        self.start_recv_btn.config(state="normal")
        self.stop_recv_btn.config(state="disabled")


    def start_recording(self):
        filename = time.strftime("Recording_%Y-%m-%d_%H-%M-%S") + ".mp4"
        filepath = os.path.join("Recordings", filename)

        # Use resolution of incoming feed — adjust if needed
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(filepath, fourcc, 20.0, (1280, 660))

        if not self.video_writer.isOpened():
            messagebox.showerror("Error", "Could not open video file for writing.")
            return

        self.recording = True
        self.start_rec_btn.config(state="disabled")
        self.stop_rec_btn.config(state="normal")

    def stop_recording(self):
        self.recording = False
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None

        self.start_rec_btn.config(state="normal")
        self.stop_rec_btn.config(state="disabled")

    
    def start_response_listener(self):
        def listen():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
                server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server_sock.bind(("127.0.0.1", 9998))  # Set to your preferred port
                server_sock.listen(1)
                print("[SOCKET] Waiting for AI response on 127.0.0.1:9998")

                while True:
                    try:
                        conn, addr = server_sock.accept()
                        with conn:
                            print(f"[SOCKET] Connected by {addr}")
                            while True:
                                data = conn.recv(1024)
                                if not data:
                                    break
                                message = data.decode()
                                print(f"[SOCKET] Message received: {message}")
                                # Optional: Update GUI label or text box with message
                    except Exception as e:
                        print(f"[SOCKET] Listener error: {e}")
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

        tk.Label(zone_frame, text="Zone Name:", fg="white", bg="#1a1a1a").grid(row=0, column=0, padx=5, sticky="e")
        self.zone_name_entry = tk.Entry(zone_frame, width=30, bg="#333333", fg="white")
        self.zone_name_entry.grid(row=0, column=1, padx=5)

        tk.Label(zone_frame, text="Coordinates (x1,y1,x2,y2):", fg="white", bg="#1a1a1a").grid(row=1, column=0, padx=5, sticky="e")
        self.coords_entry = tk.Entry(zone_frame, width=30, bg="#333333", fg="white")
        self.coords_entry.grid(row=1, column=1, padx=5)

        tk.Button(zone_frame, text="Add Zone", bg="#0055aa", fg="white",
                  command=self.submit_zone).grid(row=2, column=0, columnspan=2, pady=10)

        # CALIBRATION VALUES AREA
        calib_frame = tk.LabelFrame(self, text="Set Calibration Values", bg="#1a1a1a", fg="orange")
        calib_frame.pack(pady=10, padx=10, fill="x")

        tk.Label(calib_frame, text="A Value:", fg="white", bg="#1a1a1a").grid(row=0, column=0, padx=5, sticky="e")
        self.a_entry = tk.Entry(calib_frame, width=20, bg="#333333", fg="white")
        self.a_entry.grid(row=0, column=1, padx=5)

        tk.Label(calib_frame, text="B Value:", fg="white", bg="#1a1a1a").grid(row=1, column=0, padx=5, sticky="e")
        self.b_entry = tk.Entry(calib_frame, width=20, bg="#333333", fg="white")
        self.b_entry.grid(row=1, column=1, padx=5)
        
        tk.Label(calib_frame, text="C Value:", fg="white", bg="#1a1a1a").grid(row=2, column=0, padx=5, sticky="e")
        self.c_entry = tk.Entry(calib_frame, width=20, bg="#333333", fg="white")
        self.c_entry.grid(row=2, column=1, padx=5)

        tk.Button(calib_frame, text="Submit Calibration", bg="#0055aa", fg="white",
                  command=self.submit_calibration).grid(row=3, column=0, columnspan=2, pady=10)

        self.status_label = tk.Label(self, text="", fg="white", bg="#1a1a1a")
        self.status_label.pack(pady=10)

    def submit_zone(self):
        zone = self.zone_name_entry.get().strip()
        coords = self.coords_entry.get().strip()
        if zone and coords:
            self.status_label.config(text=f"Zone '{zone}' added at {coords}", fg="white")
            # You could save or draw this zone
        else:
            self.status_label.config(text="Both zone name and coordinates are required.", fg="red")


    def submit_calibration(self):
        a = self.a_entry.get().strip()
        b = self.b_entry.get().strip()
        c = self.c_entry.get().strip()
        if a and b and c:
            self.status_label.config(text=f"Calibration values set: A = {a}, B = {b}, C = {c}", fg="white")

            # Save to JSON file
            calib_data = {"a": a, "b": b, "c": c}
            with open("calibration.json", "w") as f:
                json.dump(calib_data, f)
        else:
            self.status_label.config(text="Both 'a' and 'b' values are required.", fg="red")



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
