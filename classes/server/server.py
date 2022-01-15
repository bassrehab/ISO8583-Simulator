'''
a Server class that handles socket connections
- Runs continuously.
- On receiving a request data, transfer control to the Controller.
- Controller will take the raw ISO message, pass it to ISO8583,
    do internal processing and return the prepared response (text) back to server.
- Server will pack the message in ASCII/ByteArray format and send the response back
'''
import socket
import select
import string
from controllers.core import *

# TODO: Import the controller class here.

class SimulatorServer(object):
    
    def __init__(self):
        # do something here
        
        self.CONNECTION_LIST = []
        self.RECV_BUFFER = 4096
        self.PORT = 5000
        self.HOST = "localhost"

        self.start_server() # start the server

    def broadcast_data(self, sock, message):
        """Send broadcast message to all clients other than the
           server socket and the client socket from which the data is received."""

        for socket in self.CONNECTION_LIST:
            if socket != self.server_socket and socket != sock:
                socket.send(message)

    def start_server(self):
        # Initialize the C-Socket struct obj
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # this has no effect, why ?

        #Set Socket Options (allow reusing of addr/port without conflict)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind the server to listen to HOST+PORT
        server_socket.bind((self.HOST, self.PORT))
        server_socket.listen(10)

        # ADDED: to expose the server socket
        self.server_socket = server_socket #Expose the socket obj as a shared member.

        # Add server socket to the list of readable connections
        self.CONNECTION_LIST.append(server_socket)

        print("[INFO] Simulator TCP Server started on " + str(self.HOST) + ':' + str(self.PORT))
        print("[INFO] Waiting for connections .. ")
        while 1:
            # List of all sockets which are ready to be read through select
            read_sockets, write_sockets, error_sockets = select.select(self.CONNECTION_LIST, [], [])

            for sock in read_sockets:

                # Got a New connection
                if sock == server_socket:
                    # Handle the case in which there is a new connection received through server_socket
                    sockfd, addr = server_socket.accept() #  Get the Socketfb obj
                    self.CONNECTION_LIST.append(sockfd)
                    print("[INFO] Client (%s, %s) connected" % addr)  # Print the internal Port the kernel assigned.

                # If existing client connection and incoming message received
                else:
                    # Data from client, process it
                    try:
                        # Wrapped in try-catch block to handle the abrupt TCP program end
                        # (connection reset by peer) by Windows.

                        # Extract the Hex format of the data from the ASCII Byte Array
                        data = sock.recv(self.RECV_BUFFER).encode("hex")


                        # echo back the client message
                        if data and len(data) != 0:
                            print('[INFO] REQ Data Received : ' + data)

                            # call the controller and send the data for handling here.
                            ctrlObj = Controller(data)
                            # Wait all processing and respond back.
                            response = ctrlObj.handler_core()
                            print('[INFO] RES Data Sent: ' + response)

                            # encode
                            encoded_response = bytearray.fromhex(str(response))
                            sock.send(encoded_response)

                    # client disconnected, so remove from socket list
                    except:
                        # Handle 'Connection Reset by peer exception" graciously.
                        self.broadcast_data(sock, "[INFO] Client (%s, %s) is offline" % addr)
                        print("[INFO] Client (%s, %s) is offline" % addr)
                        sock.close()
                        self.CONNECTION_LIST.remove(sock)
                        continue

        server_socket.close()
