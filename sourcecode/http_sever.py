import socket
import os
import threading
import time
import datetime
import asyncio


class ResponseStatus(object):
    OK = 'HTTP/1.1 200 OK\r\n'
    NOT_MODIFIED = 'HTTP/1.1 304 Not Modified\r\n'
    BAD_REQUEST = 'HTTP/1.1 400 Bad Request\r\n'
    NOT_FOUND = 'HTTP/1.1 404 Not Found\r\n'


class HeaderFields(object):
    status_code = ''
    last_modified_time = 'Last-Modified: '
    Accept_range = 'Accept-Ranges: bytes\r\n'
    Content_length = 'Content-Length: '
    Close_connection = "Connection: close\n\n"
    GMT = "Date: " + time.strftime("%a, %d %b %Y %I:%M:%S", time.gmtime()) + " GMT\n\n"
    Alive_connection = "Connection: keep-alive\r\n"
    Time_out = "Timeout: timeout=60\r\n"
    content_type = "Content-Type: text/html;charset=UTF-8\r\n"


class HttpRequestHandler(object):
    def __init__(self):
        self.log_list = []
        self.modified_time = None
        self.last_access_time = None
        self.file_list = []

    async def add_log(self):
        """
        This is a function which append the log message to log.txt file
        return: void
        """
        async with asyncio.Lock():
            with open("log.txt", "a+") as fp:
                fp.write("ip_address,access time and return status\n[")
                for data in self.log_list:  # a list of recording
                    fp.write("'" + str(data) + "'" + ", ")
                fp.write("]\n")
                fp.write("The file he/she retrieved:\n")
                fp.write("[")
                for file_name in self.file_list:
                    fp.write("'" + str(file_name) + "'" + ", ")
                fp.write("]\n\n")
                fp.close()
            # after append all the data to log in list we need to clear it
            self.log_list.clear()
            self.file_list.clear()

    def get_modified(self, filepath):
        """
        This function is for getting the last modified time of the file
        :param filepath: it is the path which can be used to find the file
        :return: modified_time(GMT)
        """
        try:
            os_modify_time = os.path.getmtime(filepath)
            file_modify_time = time.strftime("%a, %d %b %Y %I:%M:%S GMT\r\n", time.gmtime(os_modify_time))
            # the header field to be sent to the client
            return file_modify_time
        except OSError:
            return None

    def if_modified(self, file_path, header_dic: dict):
        """
         This function is for checking which status code to send
        :param file_path: the path which can be used to find the file
        :param header_dic: the dictionary created by splitting the request message
        :return: return the response status
        """
        if 'if-modified-since' in header_dic:
            last_access_time = header_dic['if-modified-since']
            self.last_access_time = datetime.datetime.strptime(last_access_time,
                                                               '%a, %d %b %Y %H:%M:%S GMT').timestamp()
        # while initiate the last modified time
        else:
            return ResponseStatus.OK
        # the field inside the function for compare
        self.modified_time = datetime.datetime.utcfromtimestamp(os.path.getmtime(file_path)).timestamp()
        if self.last_access_time <= self.modified_time:
            return ResponseStatus.OK
        else:
            return ResponseStatus.NOT_MODIFIED

    def form_response(self, file_path, headers: HeaderFields, header_dict: dict, method: str):
        """
        this function aims to get the response message
        :param file_path: the path which can be used to find the file
        :param headers: the class header field which can be used to form the response headers
        :param header_dict: the dictionary created by splitting the request message
        :param method: The method we are using，"HEAD" or "GET"
        :return: response_header(The headers of the response message), body(The body of the response message)
        """
        try:
            response_header = ''
            body = None
            headers.last_modified_time += self.get_modified(file_path)
            headers.status_code = self.if_modified(file_path, header_dict)
            # if it is 304, no need to get the size
            if headers.status_code.find("304") < 0:
                headers.Content_length += str(os.path.getsize(file_path)) + '\r\n'
            # if it is GET method and the status code is 200, we are going to read the body from the file
            if headers.status_code.find("200") >= 0 and method != "HEAD":
                if file_path.find(".jpg") >= 0 or file_path.find(".png") >= 0:
                    fin = open(file_path, 'rb')
                    body = fin.read()
                    fin.close()
                else:
                    fin = open(file_path)
                    body = fin.read()
                    fin.close()
                    pass
            response_header += headers.status_code
            response_header += headers.last_modified_time
            response_header += "Cache-Control: max-age=3600\r\n"
            # if the code is 200 we need to have these header fields
            if "connection" in header_dict:
                if header_dict['connection'] == 'keep-alive':
                    response_header += headers.Alive_connection
                    response_header += headers.Time_out
                else:
                    response_header += "Connection: close\r\n"
            if headers.status_code.find("200") >= 0:
                response_header += headers.Content_length
                response_header += headers.Accept_range
                if file_path.find(".html"):
                    response_header += headers.content_type
                if file_path.find(".jpg") >= 0:
                    response_header += "Content-Type: image/jpeg\r\n"
                elif file_path.find(".png") >= 0:
                    response_header += "Content-Type: image/png\r\n"
            response_header += headers.GMT
            return response_header, body
        except TypeError:
            if FileNotFoundError:
                raise FileNotFoundError
            return None, None

    def form_error_response(self, file_path: str, headers: HeaderFields, method: str):
        """
        this function aims to get the 404,400 Error response message
        :param file_path: the path which can be used to find the file
        :param headers: the class header field which can be used to form the response headers
        :param method: The method we are using，"HEAD" or "GET"
        :return: the 404 and 400 error message and the message body
        """
        response_header = ''
        body = None
        headers.Content_length += str(os.path.getsize(file_path)) + '\r\n'
        if file_path.find("400") >= 0:
            headers.status_code = ResponseStatus.BAD_REQUEST
        elif file_path.find("404") >= 0:
            headers.status_code = ResponseStatus.NOT_FOUND
        response_header += headers.status_code
        response_header += headers.content_type
        response_header += headers.Content_length
        response_header += headers.Close_connection
        if (method.find("GET") >= 0 and file_path.find("404") >= 0) or file_path.find("400") >= 0:
            fin = open(file_path)
            body = fin.read()
            fin.close()
        return response_header, body

    def handle_request(self, url: str, header_dict: dict, method: str):  # url is the file path
        """
        This function is going to return two values, one is the header and response status message, the other is body
        of response message
        :param url: The url part of the request message
        :param header_dict: the dictionary created by splitting the request message
        :param method: The method we are using:"HEAD" or "GET"
        :return: The response headers,and the body of the message
        """
        headers = HeaderFields()
        # initiate the time field to let the client know it's access time
        now = time.strftime("%a, %d %b %Y %I:%M:%S", time.gmtime())
        self.log_list.append(now)
        headers.GMT = "Date: " + now + " GMT\n\n"
        try:
            # if the request target
            if url[0] != "/":
                response_header, body = self.form_error_response("htdocs/400.html", headers, method)
                self.log_list.append(headers.status_code[9:-2])
            elif url == "/":
                try:
                    url = "/index.html"
                    file_path = "htdocs" + url
                    response_header, body = self.form_response(file_path, headers, header_dict, method)
                    self.file_list.append(url)
                    self.log_list.append(headers.status_code[9:-2])
                except FileNotFoundError:
                    self.file_list.pop()
                    response_header, body = self.form_error_response("htdocs/404.html", headers, method)
                    self.log_list.append(headers.status_code[9:-2])
            elif url.find(".html") >= 0:
                try:
                    file_path = "htdocs" + url
                    self.file_list.append(url)
                    response_header, body = self.form_response(file_path, headers, header_dict, method)
                    self.log_list.append(headers.status_code[9:-2])
                except FileNotFoundError:
                    self.file_list.pop()
                    response_header, body = self.form_error_response("htdocs/404.html", headers, method)
                    self.log_list.append(headers.status_code[9:-2])
            elif url.find(".jpg") >= 0 or url.find(".png") >= 0:
                try:
                    file_path = "htdocs" + url
                    self.file_list.append(url)
                    response_header, body = self.form_response(file_path, headers, header_dict, method)
                    self.log_list.append(headers.status_code[9:-2])
                except FileNotFoundError:
                    self.file_list.pop()
                    response_header, body = self.form_error_response("htdocs/404.html", headers, method)
                    self.log_list.append(headers.status_code[9:-2])
            else:
                response_header, body = self.form_error_response("htdocs/404.html", headers, method)
                self.log_list.append(headers.status_code[9:-2])
            return response_header, body
        except TypeError:
            response_header, body = self.form_error_response("htdocs/404.html", headers, method)
            self.log_list.append(headers.status_code[9:-2])
            return response_header, body

    @staticmethod
    def format_header(request: str):
        """
        to get method and a dictionary which contains field name and value of the filed
        :param request: The request from the client which is a string
        :return: http_method, the name of the file
        """
        request = request.strip()
        first_break = request.find('\r\n')
        first_line = request[:first_break].split(' ')
        if len(first_line) != 3:
            version = None
        elif first_line[2] == "HTTP/1.1" or first_line[2] == "HTTP/1.0":
            version = first_line[2]
        else:
            version = None
        try:
            http_method = first_line[0]
            url = first_line[1]
            header_list = request.split('\r\n')
            header_dic = {}
            for header in header_list:
                if header.find(': ') >= 0:
                    field_name, field_value = header.split(': ')
                    header_dic[field_name.lower()] = field_value
            return http_method.upper(), url, header_dic, version
        except IndexError or OSError:
            pass


async def http_sever(client_connection, client_address, timeout=60):
    """
    This function is used to be work as a single http sever, the asynchronize is for the written process
    :param client_connection: connection from the client host
    :param client_address:  address which need to be written in to the log.txt file
    :param timeout: Keep alive in this time interval
    :return: NULL
    """
    handler = HttpRequestHandler()
    handler.log_list.append(client_address)
    client_connection.settimeout(timeout)
    flag = False # this flag is used to detect whether we need to keep alive
    while True:
        if flag: # if the flag is true then now we can close the connection
            client_connection.close()
            break
        try:
            request = client_connection.recv(1024).decode()
        except socket.timeout:
            client_connection.close()
            break
        try:
            if not request:
                client_connection.close()
                break
            http_method, url, header_dic, version = handler.format_header(request)
            if 'connection' in header_dic.keys():
                if header_dic['connection'] == 'close':
                    flag = True
        except TypeError:
            headers = HeaderFields()
            headers.GMT = time.strftime("%a, %d %b %Y %I:%M:%S", time.gmtime())
            response_header, body = handler.form_error_response("htdocs/400.html", headers, "")
            handler.log_list.append(headers.GMT)
            handler.log_list.append(headers.status_code[9:-2])
            client_connection.sendall(response_header.encode())
            client_connection.sendall(body.encode())
            client_connection.close()
            break
        try:
            if http_method == "GET" and version != None:
                # print("file name is" + filename)
                response_header, body = handler.handle_request(url, header_dic, http_method)
                client_connection.sendall(response_header.encode())
                if response_header.find("200") >= 0 or response_header.find("404") >= 0 or response_header.find(
                        "400") >= 0:
                    if isinstance(body, str):
                        client_connection.sendall(body.encode())
                    else:
                        client_connection.sendall(body)
                if response_header.find("404") >= 0 or response_header.find("400") >= 0:
                    client_connection.close()
                    await handler.add_log()
                    break
            elif http_method == "HEAD" and version != None:
                # print("file name is" + filename)
                response_header, body = handler.handle_request(url, header_dic, http_method)
                client_connection.sendall(response_header.encode())
                # because it is HEAD method so no need to send body which is the message body
            else:
                # if the method is incorrect then we send 400 to user
                headers = HeaderFields()
                headers.GMT = time.strftime("%a, %d %b %Y %I:%M:%S", time.gmtime())
                response_header, body = handler.form_error_response("htdocs/400.html", headers, http_method)
                handler.log_list.append(headers.GMT)
                handler.log_list.append(headers.status_code[9:-2])
                client_connection.sendall(response_header.encode())
                client_connection.sendall(body.encode())
                client_connection.close()
                break
            await handler.add_log()
        except IndexError:
            pass


def single_thread(client_connection, client_address):
    """
    this function is aiming to call the asynchronize function
    :param client_connection: connection from the client
    :param client_address: The address of the client host
    :return: NULL
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(http_sever(client_connection, client_address))


def start_sever(sever_host: str, sever_port: int):
    """
    act to listen to client, when a client try to connect to the sever, we will be able to receive in this function
    :param sever_host: IP of our host
    :param sever_port: port number of the sever
    :return: NULL
    """
    sever_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sever_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sever_socket.bind((sever_host, sever_port))
    sever_socket.listen(1)
    while True:
        client_connection, client_address = sever_socket.accept()
        # print(client_address)
        request_thread = threading.Thread(target=single_thread, args=(client_connection, client_address[0],))
        request_thread.start()


def main():
    sever_host = 'localhost'
    sever_port = 8000
    start_sever(sever_host, sever_port)


main()
