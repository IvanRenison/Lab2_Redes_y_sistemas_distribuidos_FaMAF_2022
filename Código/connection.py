# encoding: utf-8
# Revisión 2019 (a Python 3 y base64): Pablo Ventura
# Copyright 2014 Carlos Bederián
# $Id: connection.py 455 2011-05-01 00:32:09Z carlos $

import socket
from constants import *
from base64 import b64encode
import os
import traceback


class Connection(object):
    """
    Conexión punto a punto entre el servidor y un cliente.
    Se encarga de satisfacer los pedidos del cliente hasta
    que termina la conexión.
    """

    def __init__(self, socket: socket.socket, directory: str):
        # Inicialización de conexión
        self.socket = socket
        self.directory = directory
        self.connection_active = True
        self.buffer = ''
        print(f"Connected by: {self.socket.getsockname()}")

    def send(self, message: bytes | str, instance='ascii'):
        """
        Envía el mensaje 'message' al server, seguido por el terminador de
        línea del protocolo.

        instance tiene que se 'ascii' o 'b64encode', si no falla con una excepción
        En caso de que sea 'ascii' agrega un '\\r\\n' al final

        También puede fallar con otras excepciones de socket.
        """
        if instance == 'b64encode':
            message = b64encode(message)
        elif instance == 'ascii':
            message += EOL
            message = message.encode("ascii")
        else:
            # Nunca se deberia llamar a send con otra cosa
            raise Exception(f"send: Invalid instance '{instance}'")

        while len(message) > 0:
            bytes_sent = self.socket.send(message)
            assert bytes_sent > 0
            message = message[bytes_sent:]

    def quit(self):
        """
        Cierra la conexión al cliente
        """
        response = mk_code(CODE_OK)
        self.send(response)
        self.connection_active = False
        print("Closing connection...")

    def file_exist(self, filename: str) -> bool:
        return os.path.isfile(os.path.join(self.directory, filename))

    def filename_is_valid(self, filename: str) -> bool:

        invalid_chars = set(filename) - VALID_CHARS
        return (len(invalid_chars) == 0)

    def analizar_comando(self, command: str):
        """
        Analiza el comando y ejecuta la función correspondiente
        """

        args = command.split()

        print(f"Request: {command}")

        match args:
            # En cada caso, si los argumentos son cantidad y tipo correctos
            # ejecuta la función correspondiente, que se encarga de enviar la
            # respuesta
            case ['get_file_listing']:
                self.get_file_listing()
            case ['get_metadata', filename]:
                self.get_metadata(filename)
            case ['get_slice', filename, offset, size] if offset.isdecimal() and size.isdecimal():
                self.get_slice(filename, int(offset), int(size))
            case ['quit']:
                self.quit()
            case ['get_file_listing', *_] | ['get_metadata', *_] | ['get_slice', *_] | ['quit', *_]:
                response = mk_code(INVALID_ARGUMENTS)
                self.send(response)
            case _:
                response = mk_code(INVALID_COMMAND)
                self.send(response)

    def get_file_listing(self):
        """
        Lista los archivos de un directorio
        """
        response = mk_code(CODE_OK) + EOL

        for dir in os.listdir(self.directory):
            response += f"{dir} {EOL}"

        self.send(response)

    def get_metadata(self, filename: str):
        """
        Devuelve el tamaño del archivo dado en bytes
        """
        response = mk_code(CODE_OK) + EOL

        if not self.file_exist(filename):
            response = mk_code(FILE_NOT_FOUND)
            self.send(response)

        elif not self.filename_is_valid(filename):
            response = mk_code(INVALID_ARGUMENTS)
            self.send(response)

        else:
            data = os.path.getsize(os.path.join(self.directory, filename))
            response += f"{str(data)}"
            self.send(response)

    def get_slice(self, filename: str, offset: int, size: int):
        if not self.file_exist(filename):
            response = mk_code(FILE_NOT_FOUND)
            self.send(response)

        elif not self.filename_is_valid(filename):
            response = mk_code(INVALID_ARGUMENTS)
            self.send(response)

        else:
            file_size = os.path.getsize(os.path.join(self.directory, filename))

            if offset < 0 or file_size < offset + size:
                response = mk_code(BAD_OFFSET)
                self.send(response)

            else:
                pathname = os.path.join(self.directory, filename)
                response = mk_code(CODE_OK)
                self.send(response)
                with open(pathname, 'rb') as f:  # r = lectura, b = binario
                    f.seek(offset)

                    remaining = size

                    while remaining > 0:
                        bytes_read = f.read(remaining)
                        remaining -= len(bytes_read)
                        self.send(bytes_read, instance='b64encode')
                            # Los archivos se codifican con b64encode

                    response = ''
                    self.send(response)

    def _recv(self):
        """
        Recibe datos y acumula en el buffer interno.

        Para uso privado del server.
        """
        try:
            data = self.socket.recv(4096).decode("ascii")
            self.buffer += data

            if len(data) == 0:
                self.connection_active = False

        except UnicodeError:
            response = mk_code(BAD_REQUEST)
            self.send(response)
            self.connection_active = False
            print("Closing connection...")

    def read_line(self):
        """
        Espera datos hasta obtener una línea completa delimitada por el
        terminador del protocolo.

        Devuelve la línea, eliminando el terminaodr y los espacios en blanco
        al principio y al final.
        """
        while EOL not in self.buffer and self.connection_active:
            self._recv()

        if EOL in self.buffer:
            request, self.buffer = self.buffer.split(EOL, 1)
            return request.strip()
        else:
            self.connected = False
            return ""

    def handle(self):
        """
        Atiende eventos de la conexión hasta que termina.
        """
        while self.connection_active:
            response = self.read_line()
            if NEWLINE in response:
                response = mk_code(BAD_EOL)
                self.send(response)
                self.connection_active = False
                print("Closing connection...")
            elif len(response) > 0:
                try:
                    self.analizar_comando(response)
                except Exception:
                    print('INTERNAL SERVER ERROR')
                    print(traceback.format_exc())
                    response = mk_code(INTERNAL_ERROR)
                    self.send(response)
                    self.connection_active = False
                    print("Closing connection...")
        self.socket.close()


def mk_code(code: int) -> str:
    assert code in error_messages.keys()

    return f"{code} {error_messages[code]}"
