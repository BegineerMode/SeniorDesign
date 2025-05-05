import socket

# Peer WireGuard IP and port
peer_ip = '10.0.0.3'
peer_port = 5000

# Command you want to send
command = "restart_ffmpeg"

# Create socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((peer_ip, peer_port))

# Send command
sock.sendall(command.encode())

# Optionally receive a response
response = sock.recv(1024).decode()
print(f"Response from peer: {response}")

sock.close()
