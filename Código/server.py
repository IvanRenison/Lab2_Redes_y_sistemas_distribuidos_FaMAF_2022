#!/usr/bin/env python
# encoding: utf-8
# Revisión 2019 (a Python 3 y base64): Pablo Ventura
# Revisión 2014 Carlos Bederián
# Revisión 2011 Nicolás Wolovick
# Copyright 2008-2010 Natalia Bidart y Daniel Moisset
# $Id: server.py 656 2013-03-18 23:49:11Z bc $

import optparse
import os
import socket
import connection
import sys
import threading
from constants import *


class Server(object):
    """
    El servidor, que crea y atiende el socket en la dirección y puerto
    especificados donde se reciben nuevas conexiones de clientes.
    """

    def __init__(self, addr=DEFAULT_ADDR, port=DEFAULT_PORT,
                 directory=DEFAULT_DIR):
        print(f"Serving {directory} on {addr}:{port}.")
        # FALTA: Crear socket del servidor, configurarlo, asignarlo
        # a una dirección y puerto, etc.

        # Chequear que el directorio existe
        if not os.path.isdir(directory):
            os.mkdir(directory)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((addr, port))

        self.socket = s
        self.directory = directory

        # Semaforo para limitar la cantidad de hilos
        # Cada ves que se crea un hilo, el nuevo hilo adquire el semaforo
        # y cuando termina, lo libera
        # Idea sacada de
        # https://stackoverflow.com/questions/1787397/how-do-i-limit-the-number-of-active-threads-in-python/5991741#5991741
        self.threadLimiter = threading.BoundedSemaphore(MAX_THREADS)


    def serve(self):
        """
        Loop principal del servidor. Se acepta una conexión a la vez
        y se espera a que concluya antes de seguir.
        """
        self.socket.listen()

        while True:
            # Aceptar una conexión al server, crear una Connection para la
            # conexión y atenderla hasta que termine.
            
            conn_socket, _ = self.socket.accept()
            conn = connection.Connection(conn_socket, self.directory)
            self.handle(conn)
    
    def handle(self, conn: connection):
        """
        Función que para manejar un cliente.
        """
        self.threadLimiter.acquire()
        def handler():
            try:
                conn.handle()
            finally:
                self.threadLimiter.release()
        thread = threading.Thread(target = handler)
        thread.start()
        

def main():
    """Parsea los argumentos y lanza el server"""

    parser = optparse.OptionParser()
    parser.add_option(
        "-p", "--port",
        help="Número de puerto TCP donde escuchar", default=DEFAULT_PORT)
    parser.add_option(
        "-a", "--address",
        help="Dirección donde escuchar", default=DEFAULT_ADDR)
    parser.add_option(
        "-d", "--datadir",
        help="Directorio compartido", default=DEFAULT_DIR)

    options, args = parser.parse_args()
    if len(args) > 0:
        parser.print_help()
        sys.exit(1)
    try:
        port = int(options.port)
    except ValueError:
        sys.stderr.write(
            f"Numero de puerto invalido: {repr(options.port)}\n")
        parser.print_help()
        sys.exit(1)

    server = Server(options.address, port, options.datadir)
    server.serve()


if __name__ == '__main__':
    main()
