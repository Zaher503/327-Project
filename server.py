import socket

HOST = '0.0.0.0'
PORT = 5000

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(5)
print(f"server on {HOST}:{PORT}")


connection, address = server_socket.accept()
print(f"connection from {address}")

while True:
    data = connection.recv(1024)
    if not data:
        break

    print(f"received: {data.decode()}")
    
connection.close()
server_socket.close()
print("connection closed")