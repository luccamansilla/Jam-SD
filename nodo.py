import sys
import serpent
import Pyro5.api
import os
import socket
import threading
import time
import random
import sqlite3 as db


save_directory = ".\songs"

if not os.path.exists(save_directory):
    os.makedirs(save_directory)
    print(f"Directorio de guardado creado: {save_directory}")
else:
    print(f"Directorio de guardado ya existe: {save_directory}")

@Pyro5.api.expose
class Testclass(object):
    def __init__(self, id, nodos):
        self.id = 1  # ID único del nodo
        self.lider = None
        self.nodos = nodos  # Lista de nodos (ID, URI)
        self.activo = True
        self.nameserver = Pyro5.core.locate_ns()
        self.songs_states = {}  # Diccionario para almacenar el estado de cada cancion
        self.clients = {}  # Diccionario para almacenar los proxies de los clientes
        self.vector_clock = {} 
        self.clientes = []

    def get_clients_in_playlist(self, playlist_name):
        self.db_connection = db_connection
        cursor = self.db_connection.cursor()
        # Obtener el ID de la playlist basado en su nombre
        cursor.execute("SELECT playlist_id FROM playlist WHERE name = ?", (playlist_name,))
        playlist_row = cursor.fetchone()
        if not playlist_row:
            return []  # Playlist no encontrada
        playlist_id = playlist_row[0]
        # Obtener los usuarios que están en la playlist
        cursor.execute("""
            SELECT users.user_id, users.name
            FROM users
            JOIN users_playlist ON users.user_id = users_playlist.user_id
            WHERE users_playlist.playlist_id = ?
        """, (playlist_id,))

        usuarios = cursor.fetchall()
        cursor.close()

        # Devuelve la lista de clientes basados en los usuarios obtenidos
        return [self.clients.get(user_id) for user_id, _ in usuarios if user_id in self.clients]

    #actualizo el clock de cada cliente en la playlist
    def update_state(self, playlist_name, state, clock):
        current_clock.fusionar(clock)
        self.vector_clock[playlist_name] = (current_clock)

         # Notificar a todos los clientes de la playlist
        for client in self.get_clients_in_playlist(playlist_name):
            client.receive_update(playlist_name, state, current_clock.obtener_reloj())


        #actualiza estado de la cancion en la platlist
    def update_playlist_state(self, playlist_name, song_name, position, state , duration):
        if playlist_name not in self.songs_states:
            self.songs_states[playlist_name] = {}
        self.songs_states[playlist_name] = {
            'song': song_name,
            'position': position,
            'state': state,
            'duration': duration
        }
        print(self.songs_states)
        self.sync_clients(playlist_name)

    #sincroniza a todos los clientes el estado de la cancion
    def sync_clients(self, playlist_name):
        print("entre")
        if playlist_name not in self.songs_states:
            return
        
        state = self.songs_states[playlist_name]
        for client_uri in self.clientes:
            print(self.clients)
            try:
                proxy = Pyro5.api.Proxy(client_uri)
                print("pasando")
                proxy.mainThread(state['song'], state['position'], state['state'] , state['duration'])
            except Exception as e:
                print(f"Error al sincronizar con cliente para actualizar canciones {client_uri}: {e}")
   
    @Pyro5.api.expose
    def get_playlist_state(self, playlist_name):
        return self.songs_states.get(playlist_name, {})    

    @Pyro5.api.expose
    def notify_clients(self): 
        for cliente in self.clientes:
            try:
                client_proxy = Pyro5.api.Proxy(cliente)  # Crea un proxy para el cliente
                client_proxy.onPlaylistSelected()  # Llama al método expuesto en el cliente
            except Exception as e:
                print(f"Error al notificar al cliente {cliente}: {e}")

    @Pyro5.api.expose
    def register_client(self, client):
        self.clientes.append(client)
        print(f"Cliente registrado: {client}")

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
      
    def notifyClientsSongs(self):
        print(f"Clientes conectados: {self.clients}")
        for client_uri in self.clientes:
            print(self.clients)
            try:
                proxy = Pyro5.api.Proxy(client_uri)
                print(f"pasando {client_uri}")
                proxy.mainThreadUpdateSongs()
            except Exception as e:
                print(f"Error al sincronizar con cliente para actualizar canciones {client_uri}: {e}")
   
                
    # CONSULTAS A LA BD
    
    def connect_db(self):
        return db.connect('spotify.db')
    
    def get_playlists(self):
        conn = self.connect_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM playlist WHERE is_shared = 0")
        playlists = cursor.fetchall()

        conn.close()
        return playlists

    @Pyro5.api.expose
    def insertSong(self, name, path, playlist):
        conn = self.connect_db()
        cursor = conn.cursor()
        pathNew = "/songs/"+path
        cursor.execute("INSERT INTO songs (name, path) VALUES (?, ?)", (name, pathNew))
        song_id = cursor.lastrowid
        cursor.execute("SELECT playlist_id FROM playlist WHERE name = (?)", (playlist,))
        playlist_id = cursor.fetchone()
        cursor.execute("INSERT INTO songs_playlist (song_id, playlist_id, user_upload_id) VALUES (?, ?, ?)", (song_id, playlist_id[0], "1"))
        conn.commit()
        conn.close()
        self.notifyClientsSongs()
        
    @Pyro5.api.expose          
    def load_songs(self, playlist_name):
        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT playlist_id FROM playlist WHERE name = (?)", (playlist_name,))
        playlist_id = cursor.fetchone()
        cursor.execute("SELECT songs.name FROM songs_playlist INNER JOIN songs ON songs.song_id = songs_playlist.song_id WHERE songs_playlist.playlist_id = ?",  (playlist_id[0],))
        songs = cursor.fetchall()
        return songs

if __name__ == "__main__":
    node_id =1 #int(sys.argv[1])  # Toma el ID del nodo desde los argumentos de línea de comandos
    listPort =[0,5001,5002,5003];
    nodos = [
        (1, "playlist"),
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