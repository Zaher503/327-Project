import socket

HOST = '127.0.0.1'
PORT = 5000

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))

print("Client is connected to server.")
client_socket.sendall(b"This is a one way message")

client_socket.close()
print("Client connection closed.")
