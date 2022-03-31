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

    def file_exist(self, filename: str) -> bool:
        
        return os.path.isfile(os.path.join(self.directory, filename))
    
    def filename_is_valid(self, filename : str) -> bool:
        
        invalid_chars = set(filename) - VALID_CHARS
        return (invalid_chars == [])

    def analizar_comando(self, command : str) -> str:
        """
        Analiza el comando y ejecuta la función correspondiente
        """

        args_name = command.split()
        command_name = args_name[0]
        
        if command_name == 'get_file_listing':
            if len(args_name) == 1:
                response = self.get_file_listing()
            else:
                return __mk_code(INVALID_ARGUMENTS)
            
        elif command_name == 'get_metadata':
            if len(args_name) == 2:
                response = self.get_metadata(args_name[1])
            else:
                return __mk_code(INVALID_ARGUMENTS)
            
        elif command_name == 'get_slice':
            if len(args_name) == 4:
                response = self.get_slice(args_name[1], args_name[2], args_name[3])
            else:
                return __mk_code(INVALID_ARGUMENTS)
            
        elif command_name == 'quit':
            if len(args_name) == 1:
                return self.quit()
            else:
                return __mk_code(INVALID_ARGUMENTS)

        else:
            #comando desconocido
            return __mk_code(INVALID_COMMAND)

        return response

    def get_file_listing(self) -> str:
        """
        Lista los archivos de un directorio
        """
        response = __mk_code(CODE_OK)

        try:
            for dir in os.listdir(self.directory):
                response += f"{dir}{EOL}"
        except:
            print('INTERNAL SERVER ERROR')
            return __mk_code(INTERNAL_ERROR)

        return response
    
    def get_metadata(self, filename : str) -> str:
        """
        Devuelve el tamaño del archivo dado en bytes 
        """
        response = __mk_code(CODE_OK)

        if not self.file_exist(filename):
            return __mk_code(FILE_NOT_FOUND)

        if not self.filename_is_valid(filename):
            return __mk_code(INVALID_ARGUMENTS)

        else:
            try:
                data = os.path.getsize(os.path.join(self.directory, filename))
                response += f"{str(data)}{EOL}"
            except:
                print('INTERNAL SERVER ERROR')
                return __mk_code(INTERNAL_ERROR)

        return response

    
    def get_slice(self, filename : str, offset : str, size : str) -> str:
        if not self.filename_exists(filename):
            return __mk_code(FILE_NOT_FOUND)

        elif not self.filename_is_valid(filename):
            return __mk_code(INVALID_ARGUMENTS)

        try:
            offset = int(offset)
            size = int(size)
        except:
            return __mk_code(INVALID_ARGUMENTS)

        # TODO
        #elif fsize := os.path.get_size() offset < 0 or size < 0:
        #    return __mk_code(INVALID_ARGUMENTS)


        with open(filename, "r") as f:
            f.seek(offset)
            chunk = f.read(size).encode()
            b64_chunk = b64encode(chunk)

            response += f"{b64_chunk}{EOL}"

        return response
    
    def quit(self) -> str:
        """
        Cierra la conexión al cliente
        """
        response = __mk_code(CODE_OK)
        self.connection_active = False
        
        return response 
    

    def handle(self):
        """
        Atiende eventos de la conexión hasta que termina.
        """

        # Maneja el envío y recepción de datos hasta la desconexión
        buffer = ""

        while self.connection_active:
            while EOL not in buffer and len(buffer) < 4096:
                rec = self.sock.recv(2048)
                buffer += rec
            
            if len(buffer) >= 4096:
                # El comando es muy largo, manejo de error de largo de comando
                self.socket.send(__mk_code(BAD_REQUEST))
                self.connection_active = False
            else:
                request, buffer = buffer.split(EOL, 1)
            
                if NEWLINE in request:
                    self.socket.send(__mk_code(BAD_EOL))
                    self.connection_active = False
                else:
                    try:
                        response = self.analizar_comando(request)
                    except:
                        print('INTERNAL SERVER ERROR')
                        response = __mk_code(INTERNAL_ERROR)
                    self.socket.send(response)
        self.socket.close()



def __mk_code(code : int) -> str:
    assert code in error_messages.keys()

    return f"{code} {error_messages[code]}{EOL}"


