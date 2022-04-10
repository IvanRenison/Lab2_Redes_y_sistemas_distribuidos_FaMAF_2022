# Informe

## Integrantes:

    - Fuentes, Tiffany
    - Renison, Iván
    - Schachner, Álvaro

## Estructura del Servidor

Una vez iniciado, el servidor realiza una escucha pasiva de requests mediante un socket.
Al ser recibida y aceptada una request enviada por un cliente, se crea una conección en un nuevo thread [que forma parte de un thread pool con un máximo expecificado en `constants.py`] hasta que se cierra la dicha conección.

La comunicación del cliente al servidor se realiza mediante el protocolo HFTP, que implementa distintos comandos especificados. Cada mensaje se lee en chunks de 4096 bytes Ascii hasta encontrarse con un terminador de línea '\r\n', todo lo que se encuentre después sera considerado como un comando distinto.

Cada mensaje enviado por un cliente se guarda en un buffer de entrada, el cual se procesa una cuando es recibido en completitud. Luego de hacer las acciones indicadas el servidor produce una respuesta adecuada al mensaje.
