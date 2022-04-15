# Informe

## Integrantes:

    - Fuentes, Tiffany
    - Renison, Iván
    - Schachner, Álvaro

## Estructura del servidor

Una vez iniciado, el servidor realiza una escucha pasiva de requests mediante un socket.
Al ser recibida y aceptada una request enviada por un cliente, se crea una conexión en un thread-pool con un máximo de `MAX_THREADS` conexiones simultáneas. Una ves que se crearon `MAX_THREADS` se acepta una conexión mas, pero no se la responde hasta que no se termina algún otra conexión, y a las nuevas conexiones que van llegando, el modulo `socket` se encarga de ponerlas en una cola.

La comunicación entre cliente y servidor se realiza mediante el protocolo HFTP, que implementa distintos comandos previamente especificados. Cada mensaje se lee en chunks de 4096 bytes ascii hasta encontrarse con un terminador de línea `'\r\n'`, todo lo que se encuentre después será considerado como un comando distinto.

Cada mensaje enviado por un cliente se guarda en un buffer de entrada, el cual es procesado cuando el mensaje es recibido en completitud (o sea, cuando llega el '`\r\n'`. Luego se hacen las acciones apropiadas para que el servidor produzca una respuesta adecuada al mensaje.

## Preguntas

### ¿Qué estrategias existen para poder implementar este mismo servidor pero con capacidad de atender múltiples clientes simultáneamente?

Se puede realizar de distintas formas, con **un solo proceso** y seleccionando cuál cliente procesar (librerias select, asyncio), utlizando **programación concurrente con hilos** (threading) o utilizando **multiples procesos en paralelo** (multiprocessing).

* Un solo proceso: El proceso se encargan de ver cual conexión a cliente hizo un pedido y lo maneja, la desventaja de este método es que mientras mas clientes se esten manejando simultáneamente, mas lento se va a responder a cada respuesta, sobre todo si es un servidor que realiza computaciones que requieran mucho hardware.

* Hilos: Aunque normalmente la programación multithreading se refiere a utilizar múltiples hilos que comparten memoria y se ejecutan simultáneamente, en Python los hilos se ejecutan de manera concurrente, es decir el procesador escoge quehilo se procesa,esto debido al GIL (Global Interpreter Lock), sin embargo, a pesar de que no se ejecutan de manera simultánea sigue siendo una buena opción para los servidores que realizan muchos procesos de I/O, ya que por lo general un thread va a estar bloqueado esperando un pedido por parte del cliente.
+ Multiproceso: Este método consiste en crear un proceso para cada cliente, los procesos no comparten memoria por lo que no se necesitan locks, y estos si se ejecutan de manera paralela. Este método requiere más soporte del hardware, ya que para correr varios procesos en paralelo deben haber varios procesadores.

Cada método tiene sus ventajas y desventajas, por lo que para cada uno hay que considerar las tareas que realiza el servidor y el hardware de la máquina donde corre el mismo.

### ¿Qué diferencia hay si se corre el servidor desde la IP “localhost”, “127.0.0.1” o la ip “0.0.0.0”?

127.0.0.1 es el IP loopback, también referido como localhost, se utiliza para establecer una conexión IP a la misma máquina siendo usada por el usuario final.

0.0.0.0 es una meta-dirección utilizada como placeholder (marcador de posición) para no especificar una dirección en particular. En el contexto del servidor, esto quiere decir que si la máquina donde corre el servidor tiene dos (o más) direcciones IP y el servidor escucha en la IP 0.0.0.0, el mismo puede ser alcanzado a través de cualquiera de esas direcciones IP.
