import serpent
import Pyro5.api
import os
import socket
import threading
import time


save_directory = ".\\songs"

# Verifica que la carpeta existe y muestra un mensaje
if not os.path.exists(save_directory):
    os.makedirs(save_directory)
    print(f"Directorio de guardado creado: {save_directory}")
else:
    print(f"Directorio de guardado ya existe: {save_directory}")

@Pyro5.api.expose
class Testclass(object):
    
    def __init__(self, id, nodos):
        self.id = id  # ID único del nodo
        self.lider = 1
        self.nodos = nodos  # Lista de nodos (ID, URI)
        self.activo = True
        self.ultima_vez_recibido = time.time()  # Tiempo de recepción del último heartbeat
        self.timeout = 5  # Tiempo de espera para recibir un heartbeat

        # Banderas para controlar la creación de hilos
        self.heartbeat_activo = False
        self.deteccion_fallo_activo = False
    
    def transfer(self, data, filename):
        if Pyro5.api.config.SERIALIZER == "serpent" and isinstance(data, dict):
            data = serpent.tobytes(data)  # Convertir el diccionario en bytes si es necesario
        
        file_path = os.path.join(save_directory, filename)
        print(f"Ruta de archivo configurada: {file_path}")

        if not os.path.exists(file_path):
            try:
                with open(file_path, "wb") as f:
                    f.write(data)
                    print(f"Archivo guardado en: {file_path}")
            except Exception as e:
                print(f"Failed to save the file: {e}")
        else:
            print("Ya existe un archivo con el mismo nombre, no se volvió a guardar el archivo")
        return len(data)

    def iniciar_eleccion(self):
        """Inicia el proceso de elección (Protocolo Bully)"""
        print(f"Nodo {self.id} inicia elección...")
        # Filtrar los nodos mayores
        candidatos = [nodo for nodo in self.nodos if nodo[0] > self.id]

        # Lista para almacenar los nodos activos mayores
        nodos_activos = []

        # Comprobar si los candidatos están activos
        for candidato in candidatos:
            try:
                # Intentar contactar con el nodo candidato
                proxy = Pyro5.api.Proxy(f"PYRONAME:{candidato[1]}")
                proxy.ping()  # Ping para comprobar si el nodo está activo

                # Si llega aquí, el nodo candidato está activo
                nodos_activos.append(candidato)
                print(f"El nodo {candidato[0]} está activo.")

            except Exception as e:
                # Si no se puede contactar con el nodo, se asume que está inactivo
                print(f"Nodo {candidato[0]} no está disponible (inactivo). Error: {e}")
                
        if not nodos_activos:
            # Si no hay candidatos mayores, este nodo se convierte en líder
            self.lider = self.id
            print(f"Nodo {self.id} se convierte en el nuevo líder.")
            for nodo in self.nodos:
                if nodo[0] != self.id:
                    try:
                        proxy = Pyro5.api.Proxy(f"PYRONAME:{nodo[1]}")
                        proxy.nuevo_lider(self.id)
                    except Exception as e:
                        print(f"Nodo {nodo[1]} no está disponible para comunicarlo quien es el nuevo lider (inactivo). Error: {e}")
                
            self.iniciar_heartbeat()  # Iniciar heartbeats si se convierte en líder
        else:
            for candidato in nodos_activos:
                proxy = Pyro5.api.Proxy(f"PYRONAME:{candidato[1]}")
                try:
                    proxy.eleccion(self.id)
                except Exception as e:
                    print(f"Error al contactar con nodo {candidato[0]}: {e}")

    def eleccion(self, nodo_id):
        """Respuesta a la solicitud de elección"""
        if nodo_id < self.id:
            print(f"Nodo {self.id} recibe solicitud de elección de {nodo_id} y responde.")
            proxy = Pyro5.api.Proxy(f"PYRONAME:{self.nodos[nodo_id-1][1]}")
            proxy.aceptar_eleccion(self.id)
            self.iniciar_eleccion()
    
    def aceptar_eleccion(self, nuevo_lider_id):
        """Actualiza el nodo con el nuevo líder"""
        print(f"Nodo {self.id} acepta a {nuevo_lider_id} como líder.")
        self.lider = nuevo_lider_id

        if self.lider == self.id:
            print(f"Nodo {self.id} es ahora el líder, iniciando envío de heartbeats.")
            self.iniciar_heartbeat()  # Inicia heartbeats si se convierte en líder
    
    def nuevo_lider(self, lider_id):
        """Notifica a los nodos que hay un nuevo líder"""
        print(f"Nodo {self.id} fue notificado que el nuevo líder es {lider_id}")
        self.lider = lider_id

    def iniciar_heartbeat(self):
        """Inicia el envío de heartbeats si no está ya activo"""
        if not self.heartbeat_activo:
            self.heartbeat_activo = True
            threading.Thread(target=self.enviar_heartbeat).start()

    def enviar_heartbeat(self):
        """El líder envía heartbeats a los seguidores"""

        try:
            while self.lider == self.id and self.activo:
                for nodo in self.nodos:
                    if nodo[0] != self.id:  # No enviarse a sí mismo
                        try:
                            proxy = Pyro5.api.Proxy(f"PYRONAME:{nodo[1]}")
                            proxy.recibir_heartbeat()
                            print(f"Heartbeat enviado al nodo {nodo[0]}")
                            self.getLider();
                        except Exception as e:
                            print(f"Error al enviar heartbeat al nodo {nodo[0]}: {e}")
                time.sleep(2)  # Enviar heartbeats cada 2 segundos
        finally:
            self.heartbeat_activo = False  # Marcar el hilo como inactivo cuando termine

    def recibir_heartbeat(self):
        """Recibe un heartbeat del líder"""
        self.ultima_vez_recibido = time.time()
        print(f"Nodo {self.id} recibió heartbeat del líder.")
        
        # print(f"hilo de deteccion de fallos:... {self.deteccion_fallo_activo}")

        self.iniciar_deteccion_fallo()

    def iniciar_deteccion_fallo(self):
        """Inicia la detección de fallos si no está ya activa"""
        if not self.deteccion_fallo_activo:
            self.deteccion_fallo_activo = True
            threading.Thread(target=self.detectar_fallo_lider).start()

    def detectar_fallo_lider(self):
        """Detecta si el líder ha fallado al no recibir heartbeats"""
        try:
            while self.activo:
                time.sleep(3)
                if self.lider is not None and time.time() - self.ultima_vez_recibido > self.timeout:
                    print(f"Nodo {self.id} detecta que el líder ha fallado, iniciando elección... {time.time() - self.ultima_vez_recibido > self.timeout}")
                    self.iniciar_eleccion()
                    break  # Termina el hilo una vez que detecta el fallo y se inicia la elección
        finally:
            self.deteccion_fallo_activo = False  # Marcar el hilo como inactivo cuando termine

    def ping(self):
        """Manejo de ping para comprobar si el nodo está activo"""
        return "Nodo activo"

    def getLider(self):
        """Retorno de Lider"""
        
        print(f"Lider es el Nodo {self.lider}:... {self.nodos[self.id - 1][1]}")
        # return Pyro5.api.Proxy(f"PYRONAME:{self.nodos[self.lider][1]}")
    
# Configuración del entorno de nodos
hostname = socket.gethostname()
IPAddr = socket.gethostbyname(hostname)

# Lista de nodos (ID, URI)
nodos = [
    (1, "playlist1"),
    (2, "playlist2"),
    (3, "playlist3"),
]

# El ID de este nodo
node_id = 3 # Cambiar este ID para cada nodo que levantes (1, 2, 3, etc.)

daemon = Pyro5.server.Daemon(host=IPAddr)

ns = Pyro5.api.locate_ns()

# Registrar la clase Testclass con el sistema de nombres
nodo = Testclass(node_id, nodos)
uri = daemon.register(nodo)
ns.register(f"playlist{node_id}", uri)
print(f"Nodo {node_id} registrado con URI: {uri}")

# Iniciar hilos de heartbeat y detección de fallos de manera controlada
nodo.iniciar_heartbeat()
nodo.iniciar_deteccion_fallo()

# Iniciar el bucle de solicitudes
print("Nodo listo para recibir solicitudes.")
daemon.requestLoop()
