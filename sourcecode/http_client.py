import socket
clientSocket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
# addr='127.0.0.1'
serverName= '127.0.0.1'
clientPort=30602
# clientSocket.bind((addr,clientPort))
serverPort=8000
clientSocket.connect((serverName,serverPort))
to_sever='HEAD /index.html HTTP/0.0\r\nHost: www.example.com\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:87.0) Gecko/20100101 Firefox/87.0\r\nAccept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8\r\nAccept-Language: en-US,en;q=0.5\r\nAccept-Encoding: gzip, deflate, br\r\nConnection: keep-alive\r\nIf-Modified-Since: Tue, 8 Apr 2023 08:00:00 GMT\n\n'
print(to_sever)
clientSocket.sendall(to_sever.encode())
sentence=clientSocket.recv(1024).decode()
print(sentence)
sentence=clientSocket.recv(1024).decode()
print(sentence)
clientSocket.close()
# print("HELLOW WORLD")