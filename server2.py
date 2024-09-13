import serpent
import Pyro5.api
import os
import socket
import threading
import time
import random

# Controlador de vista
from controller import MusicPlayerController

save_directory = ".\Jam-SD\songs"

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
        self.lider = None
        self.nodos = nodos  # Lista de nodos (ID, URI)
        self.activo = True
    
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
        candidatos = [nodo for nodo in self.nodos if nodo[0] > self.id]

        if not candidatos:
            # Si no hay candidatos mayores, este nodo se convierte en líder
            self.lider = self.id
            print(f"Nodo {self.id} se convierte en el nuevo líder.")
            for nodo in self.nodos:
                if nodo[0] != self.id:
                    proxy = Pyro5.api.Proxy(f"PYRONAME:{nodo[1]}")
                    proxy.nuevo_lider(self.id)
        else:
            for candidato in candidatos:
                proxy = Pyro5.api.Proxy(f"PYRONAME:{candidato[1]}")
                # proxy = Pyro5.api.Proxy(candidato[1])
                try:
                    proxy.eleccion(self.id)
                except Exception as e:
                    print(f"Error al contactar con nodo {candidato[0]}: {e}")
                    # self.lider = self.id
                    # print(f"Nodo {self.id} se convierte en el nuevo líder.")
                    # for nodo in self.nodos:
                    #     if nodo[0] != self.id:
                    #         proxy = Pyro5.api.Proxy(f"PYRONAME:{nodo[1]}")
                    #         proxy.nuevo_lider(self.id)
    
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
    
    def nuevo_lider(self, lider_id):
        """Notifica a los nodos que hay un nuevo líder"""
        print(f"Nodo {self.id} fue notificado que el nuevo líder es {lider_id}")
        self.lider = lider_id

    def detectar_fallo_lider(self):
        """Simula la detección de un fallo del líder"""
        while self.activo:
            time.sleep(random.randint(5, 10))  # Simula la detección aleatoria de fallos
            if self.lider is None or not self.activo:
                print(f"Nodo {self.id} detecta que el líder ha fallado, iniciando elección...")
                self.iniciar_eleccion()

# Configuración del entorno de nodos
hostname = socket.gethostname()
IPAddr = socket.gethostbyname(hostname)

# Lista de nodos (ID, URI)
nodos = [
    (1, "yamilplaylist1"),
    (2, "yamilplaylist2"),
    (3, "yamilplaylist3"),
]

# El ID de este nodo
node_id = 3  # Cambiar este ID para cada nodo que levantes (1, 2, 3, etc.)

daemon = Pyro5.server.Daemon(host=IPAddr)

ns = Pyro5.api.locate_ns()

# Registrar la clase Testclass con el sistema de nombres
uri = daemon.register(Testclass(node_id, nodos))
ns.register(f"yamilplaylist{node_id}", uri)
# Sobrescribir el segundo campo del segundo elemento
# nueva_tupla = (nodos[node_id - 1][0], uri)  # Crear una nueva tupla
# nodos[node_id - 1] = nueva_tupla  # Sobrescribir el segundo elemento de la lista
print(f"Nodo {node_id} registrado con URI: {uri}")

# Iniciar hilos para la detección de fallos
nodo = Testclass(node_id, nodos)
threading.Thread(target=nodo.detectar_fallo_lider).start()

# Iniciar el bucle de solicitudes
print("Nodo listo para recibir solicitudes.")
daemon.requestLoop()