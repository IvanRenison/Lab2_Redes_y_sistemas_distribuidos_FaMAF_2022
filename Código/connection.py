# encoding: utf-8
# Revisión 2019 (a Python 3 y base64): Pablo Ventura
# Copyright 2014 Carlos Bederián
# $Id: connection.py 455 2011-05-01 00:32:09Z carlos $

from lib2to3.pgen2.token import NEWLINE
from select import EPOLLIN
import socket
from constants import *
from base64 import b64encode
import os
import time
import sys
import traceback

class Connection(object):
    """
    Conexión punto a punto entre el servidor y un cliente.
    Se encarga de satisfacer los pedidos del cliente hasta
    que termina la conexión.
    """

    def __init__(self, socket : socket.socket, directory : str):
        # Inicialización de conexión
        self.socket = socket
        self.directory = directory
        self.connection_active = True
        self.buffer = ''

    def send(self, message, instance='Ascii', timeout=None):
        """
        Envía el mensaje 'message' al server, seguido por el terminador de
        línea del protocolo.

        Si se da un timeout, puede abortar con una excepción socket.timeout.

        También puede fallar con otras excepciones de socket.
        """
        self.socket.settimeout(timeout)
        if instance != 'Ascii':
            message = b64encode(message)
            while message:
                bytes_sent = self.socket.send(message)
                assert bytes_sent > 0
                message = message[bytes_sent:]
        else: 
            message += EOL
            while message:
                bytes_sent = self.socket.send(message.encode("ascii"))
                assert bytes_sent > 0
                message = message[bytes_sent:]
    
    def quit(self) -> str:
        """
        Cierra la conexión al cliente
        """
        response = __mk_code(CODE_OK)
        self.send(response)
        self.connection_active = False
        print("Closing connection...")
        

    def file_exist(self, filename: str) -> bool:
        return os.path.isfile(os.path.join(self.directory, filename))
    
    def filename_is_valid(self, filename : str) -> bool:
        
        invalid_chars = set(filename) - VALID_CHARS
        return (len(invalid_chars) == 0)

    def analizar_comando(self, command : list) -> str:
        """
        Analiza el comando y ejecuta la función correspondiente
        """

        args_name = command.split()
        command_name = args_name[0]

        print(f"Request: {command}")
        
        if command_name == 'get_file_listing':
            if len(args_name) == 1:
                self.get_file_listing()
            else:
                response = __mk_code(INVALID_ARGUMENTS)
                self.send(response)

            
        elif command_name == 'get_metadata':
            if len(args_name) == 2:
                self.get_metadata(args_name[1])
            else:
                response = __mk_code(INVALID_ARGUMENTS)
                self.send(response)

            
        elif command_name == 'get_slice':
            if len(args_name) == 4:
                self.get_slice(args_name[1], args_name[2], args_name[3])
            else:
                response = __mk_code(INVALID_ARGUMENTS)
                self.send(response)

            
        elif command_name == 'quit':
            if len(args_name) == 1:
                self.quit()
            else:
                response = __mk_code(INVALID_ARGUMENTS)
                self.send(response)

        else:
            #comando desconocido
            response = __mk_code(INVALID_COMMAND)
            self.send(response)


    def get_file_listing(self) -> str:
        """
        Lista los archivos de un directorio
        """
        response = __mk_code(CODE_OK) + EOL
        listing = ''

        for dir in os.listdir(self.directory):
            listing += f"{dir} {EOL}"

        response += listing
        self.send(response)
    
    def get_metadata(self, filename : str) -> str:
        """
        Devuelve el tamaño del archivo dado en bytes 
        """
        response = __mk_code(CODE_OK) + EOL

        if not self.file_exist(filename):
            response = __mk_code(FILE_NOT_FOUND)
        elif not self.filename_is_valid(filename):
            response = __mk_code(INVALID_ARGUMENTS)
        else:
            data = os.path.getsize(os.path.join(self.directory, filename))
            response += f"{str(data)}{EOL}" 
        self.send(response)


    def get_slice(self, filename : str, offset : str, size : str) -> str:
        if not self.file_exist(filename):
            response = __mk_code(FILE_NOT_FOUND)
            self.send(response)

        elif not self.filename_is_valid(filename):
            response = __mk_code(INVALID_ARGUMENTS)
            self.send(response)

        elif not offset.isdecimal() or not size.isdecimal():
            response = __mk_code(INVALID_ARGUMENTS)
            self.send(response)

        else: 
            file_size = os.path.getsize(os.path.join(self.directory, filename))
            offset = int(offset)
            size = int(size)

            if offset < 0 or file_size < offset + size:
                response = __mk_code(BAD_OFFSET)
                self.send(response)

            else: 
                pathname = os.path.join(self.directory, filename)
                response = __mk_code(CODE_OK) 
                self.send(response)
                with open(pathname, 'rb') as f:
                    f.seek(offset)

                    remaining = int(size)
                    
                    while remaining:
                        bytes_read = f.read(remaining)
                        remaining -= len(bytes_read)
                        self.send(bytes_read, 'b64encode')

                    response = ''
                    self.send(response)
                    
    def _recv(self, timeout=None):
        """
        Recibe datos y acumula en el buffer interno.

        Para uso privado del server.
        """
        self.socket.settimeout(timeout)
        data = self.socket.recv(4096).decode("ascii")
        self.buffer += data

        if len(data) == 0:
            self.connection_active = False

    def read_line(self, timeout=None):
        """
        Espera datos hasta obtener una línea completa delimitada por el
        terminador del protocolo.

        Devuelve la línea, eliminando el terminaodr y los espacios en blanco
        al principio y al final.
        """
        while not EOL in self.buffer and self.connection_active:
            if timeout is not None:
                t1 = time.process_time()
            self._recv(timeout)
            if timeout is not None:
                t2 = time.process_time()
                timeout -= t2 - t1
                t1 = t2
        if EOL in self.buffer:
            request, self.buffer = self.buffer.split(EOL, 1)
            return request.strip()
        else:
            self.connected = False
            return ""
    

    def handle(self) -> str:
        """
        Atiende eventos de la conexión hasta que termina.
        """
        print(f"Connected by: {self.socket.getsockname()}")
        while self.connection_active:
            response = self.read_line()
            if NEWLINE in response:
                response = __mk_code(BAD_EOL)
                self.send(response)
                self.connection_active = False
            elif len(response)>0:
                try:
                    self.analizar_comando(response)
                except:
                    print('INTERNAL SERVER ERROR')
                    print(traceback.format_exc())
                    response = __mk_code(INTERNAL_ERROR)
                    self.send(response)
                    self.connection_active = False
        self.socket.close()
       


def __mk_code(self, code : int) -> str:
    assert code in error_messages.keys()

    return f"{code} {error_messages[code]}"


