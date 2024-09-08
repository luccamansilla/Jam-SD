import serpent
import Pyro5.api
# from Pyro5.api import expose, serve, config
import Pyro5.socketutil
import os
import hashlib
# import Pyro5.api
import socket
from lamport_clock import LamportClock  # Importa la clase LamportClock


save_directory = "C:/Users/bandi/OneDrive/Escritorio/songs"

# Verifica que la carpeta existe y muestra un mensaje
if not os.path.exists(save_directory):
    os.makedirs(save_directory)
    print(f"Directorio de guardado creado: {save_directory}")
else:
    print(f"Directorio de guardado ya existe: {save_directory}")

@Pyro5.api.expose
class Testclass(object):
    def __init__(self):
        self.lamport_clock = LamportClock()


    #@Pyro5.api.expose
    def updatePlaybackState(self, song_name, state, client_timestamp):
        self.lamport_clock.update(client_timestamp)
        server_timestamp = self.lamport_clock.get_time()
        # Actualiza el estado de reproducción en el servidor
        print(f"Actualización: '{song_name}' está {state}.")
        return server_timestamp
    
    #@Pyro5.api.expose
    def removeSongFromPlaylist(self, song_name, playlist_name, client_timestamp):
        self.lamport_clock.update(client_timestamp)
        server_timestamp = self.lamport_clock.get_time()
        # Elimina la canción de la playlist
        print(f"Eliminando canción '{song_name}' de la playlist '{playlist_name}'.")
        return server_timestamp
        

    # @Pyro5.api.expose
    def transfer(self, data, filename, client_timestamp):
        self.lamport_clock.update(client_timestamp)
        timestamp = self.lamport_clock.get_time()

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
            print("Ya existe un archivo con el mismo nombre, no se volvio a guardar el archivo")
        return len(data), timestamp #devuelve el tiempo del servidor y el cliente obtiene este tiempo y se actualiza.

hostname = socket.gethostname()
IPAddr = socket.gethostbyname(hostname)

daemon = Pyro5.server.Daemon(host=IPAddr)
ns = Pyro5.api.locate_ns()
print(ns)
uri = daemon.register(Testclass)
ns.register("luccaplaylist", uri)
print("Ready")
daemon.requestLoop()
