import sys
import serpent
import Pyro5.api
import os
import socket
import threading
import time
import random


save_directory = ".\Jam-SD\songs"

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
        self.nameserver = Pyro5.core.locate_ns()
        self.playlist_states = {}  # Diccionario para almacenar el estado de cada playlist
        self.clients = {}  # Diccionario para almacenar los proxies de los clientes
        
        #actualiza estado de la cancion en la platlist
    def update_playlist_state(self, playlist_name, song_name, position, state):
        print("entro")
        if playlist_name not in self.playlist_states:
            self.playlist_states[playlist_name] = {}
        self.playlist_states[playlist_name] = {
            'song': song_name,
            'position': position,
            'state': state
        }
        print(self.playlist_states)
        self.sync_clients(playlist_name)

    #sincroniza a todos los clientes el estado de la cancion
    def sync_clients(self, playlist_name):
        if playlist_name not in self.playlist_states:
            return
        
        state = self.playlist_states[playlist_name]
        for client_uri in self.clients:
            try:
                proxy = Pyro5.api.Proxy(client_uri)
                print("pasando")
                proxy.update_song_state(state['song'], state['position'], state['state'])
            except Exception as e:
                print(f"Error al sincronizar con cliente {client_uri}: {e}")
    
    def get_playlist_state(self, playlist_name):
        return self.playlist_states.get(playlist_name, {})          

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
                    uri = self.nameserver.lookup(nodo[1])
                    proxy = Pyro5.api.Proxy(uri)
                    proxy.nuevo_lider(self.id)
        else:
            for candidato in candidatos:
                uri = self.nameserver.lookup(candidato[1])
                proxy = Pyro5.api.Proxy(uri)
                try:
                    proxy.eleccion(self.id)
                except Exception as e:
                    print(f"Error al contactar con nodo {candidato[0]}: {e}")
    
    def eleccion(self, nodo_id):
        """Respuesta a la solicitud de elección"""
        if nodo_id < self.id:
            print(f"Nodo {self.id} recibe solicitud de elección de {nodo_id} y responde.")
            uri = self.nameserver.lookup(self.nodos[nodo_id-1][1])
            proxy = Pyro5.api.Proxy(uri)
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


if __name__ == "__main__":
    node_id =1 #int(sys.argv[1])  # Toma el ID del nodo desde los argumentos de línea de comandos
    listPort =[0,5001,5002,5003];
    nodos = [
        (1, "yamilplaylist1"),
        (2, "yamilplaylist2"),
        (3, "yamilplaylist3"),
    ]
    
    daemon = Pyro5.server.Daemon(host=socket.gethostbyname(socket.gethostname()), port=listPort[node_id])
    ns = Pyro5.api.locate_ns()

    # Registrar el nodo
    uri = daemon.register(Testclass(node_id, nodos))
    ns.register(f"playlist", uri)
    
    nodo = Testclass(node_id, nodos)
    threading.Thread(target=nodo.detectar_fallo_lider).start()

    print(f"Nodo {node_id} listo en {uri}")
    daemon.requestLoop()