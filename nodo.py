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
        #self.clients = {}  # Diccionario para almacenar los proxies de los clientes
        self.vector_clock = {} 
        #self.clientes = []

    def get_clients_in_playlist(self, playlist_name):
        conn = self.connect_db()
        cursor = conn.cursor()

        # Obtener el ID de la playlist basado en su nombre
        cursor.execute("SELECT playlist_id FROM playlist WHERE name = ?", (playlist_name,))
        playlist_row = cursor.fetchone()
        if not playlist_row:
            return []  # Playlist no encontrada

        playlist_id = playlist_row[0]

        # Obtener los usuarios que están en la playlist junto con sus URIs
        cursor.execute("""
            SELECT users.user_id, users.uri
            FROM users
            JOIN users_playlist ON users.user_id = users_playlist.user_id
            WHERE users_playlist.playlist_id = ?
        """, (playlist_id,))

        usuarios = cursor.fetchall()
        cursor.close()

        # Convertir las URIs de cadena a objetos Pyro URI y devolverlas
        return [Pyro5.api.URI(uri) for _, uri in usuarios]
    
    @Pyro5.api.expose
    def get_shared_status(self, playlist_name, client_uri):
        conn = self.connect_db()
        cursor = conn.cursor()
        # Obtener el valor de is_shared basado en el nombre de la playlist
        cursor.execute("SELECT is_shared FROM playlist WHERE name = ?", (playlist_name,))
        playlist_row = cursor.fetchone()
        cursor.close()
        conn.close()
        if playlist_row is None:
            return None  # Playlist no encontrada
        is_shared = playlist_row[0]
        # Si la playlist es compartida (is_shared = 1), llama al método notify_clients
        if is_shared == 1:
            self.notify_clients(playlist_name)
        else:
            try:
                client_proxy = Pyro5.api.Proxy(client_uri)  
                client_proxy.mainThreadUpdateSongs()  
            except Exception as e:
                print(f"Error al actualizar las canciones del cliente {client_uri}: {e}")


    @Pyro5.api.expose
    def insert_playlist_in_users_playlist(self, current_playlist, client_uri):
        try:
            conn = self.connect_db()
            cursor = conn.cursor()
            client_uri_str = str(client_uri)
            
            # Paso 1: Buscar el ID de la playlist basado en current_playlist
            cursor.execute("SELECT playlist_id FROM playlist WHERE name = ?", (current_playlist,))
            playlist_result = cursor.fetchone()

            if playlist_result:
                playlist_id = playlist_result[0]
            else:
                raise Exception(f"No se encontró la playlist con nombre: {current_playlist}")
            
            # Paso 2: Buscar el ID del usuario basado en client_uri
            cursor.execute("SELECT user_id FROM users WHERE uri = ?", (client_uri_str,))
            user_result = cursor.fetchone()

            if user_result:
                user_id = user_result[0]
            else:
                raise Exception(f"No se encontró el usuario con URI: {client_uri}")
            
            # Paso 3: Insertar en la tabla users_playlist (user_id, playlist_id, user_leader)
            cursor.execute("INSERT INTO users_playlist (user_id, playlist_id, user_leader) VALUES (?, ?, ?)", 
                        (user_id, playlist_id, 1))  # user_leader será 1

            conn.commit()
            print(f"El usuario con id:  {user_id} hizo colaborativa la playlist con id : {playlist_id}")
            
        except Exception as e:
            print(f"Error al insertar el usuario en la playlist: {e}")
        finally:
            conn.close()

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
        self.sync_clients(playlist_name)

    #sincroniza a todos los clientes el estado de la cancion
    def sync_clients(self, playlist_name):
        if playlist_name not in self.songs_states:
            return

        clients = self.get_clients_in_playlist(playlist_name) 
        state = self.songs_states[playlist_name]
        for client_uri in clients: 
            try:
                path = self.get_song_path(state['song'])
                proxy = Pyro5.api.Proxy(client_uri)
                proxy.mainThread(path, state['position'], state['state'] , state['duration'])
            except Exception as e:
                print(f"Error al sincronizar con cliente para actualizar canciones {client_uri}: {e}")

    @Pyro5.api.expose
    def get_song_path(self, song_name):
        conn = self.connect_db()
        cursor = conn.cursor()
        # Consulta para obtener el path de la canción dado su nombre
        cursor.execute("SELECT path FROM songs WHERE name = ?", (song_name,))
        song_path = cursor.fetchone()

        if song_path is not None:
            return song_path[0]  # Devolver solo el path
        else:
            return None  # Si no se encuentra la canción, retornar None

    def connect_db(self):
        return db.connect('spotify.db')
   
    @Pyro5.api.expose
    def get_playlist_state(self, playlist_name):
        return self.songs_states.get(playlist_name, {})    

    @Pyro5.api.expose
    def notify_clients(self , playlist_name): 
        clients = self.get_clients_in_playlist(playlist_name) 
        
        for cliente in clients:
            try:
                client_proxy = Pyro5.api.Proxy(cliente)  # Crea un proxy para el cliente
                client_proxy.mainThreadUpdateSongs()  # Llama al método expuesto en el cliente
            except Exception as e:
                print(f"Error al notificar al cliente {cliente}: {e}")

    @Pyro5.api.expose
    def insert_client(self, client_name, client_uri):
        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (name, uri) VALUES (?, ?)", (client_name, str(client_uri)))
        conn.commit()
        conn.close()
        self.insert_playlist(client_name)

    @Pyro5.api.expose
    def insert_playlist(self, name):
        conn = self.connect_db()
        cursor = conn.cursor()
        formatted_name = f"{name}Playlist"
        cursor.execute("INSERT INTO playlist (name, is_shared) VALUES (?, ?)", (formatted_name,0))
        conn.commit()
        conn.close()
        
    @Pyro5.api.expose
    def update_is_shared(self, playlist_name):
        conn = self.connect_db()
        cursor = conn.cursor()
        # Actualizar el valor de is_shared a 1 para la playlist específica
        cursor.execute("UPDATE playlist SET is_shared = 1 WHERE name = ?", (playlist_name,))        
        conn.commit()
        conn.close()


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

        
    @Pyro5.api.expose          
    def load_songs(self, playlist_name):
        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT playlist_id FROM playlist WHERE name = (?)", (playlist_name,))
        playlist_id = cursor.fetchone()
        cursor.execute("SELECT songs.name FROM songs_playlist INNER JOIN songs ON songs.song_id = songs_playlist.song_id WHERE songs_playlist.playlist_id = ?",  (playlist_id[0],))
        songs = cursor.fetchall()
        return songs

    @Pyro5.api.expose
    def deleteSong(self, name, playlist):
        conn = self.connect_db()
        cursor = conn.cursor()
        # 1. Obtener el playlist_id por su nombre
        cursor.execute("SELECT playlist_id FROM playlist WHERE name = ?", (playlist,))
        playlist_id = cursor.fetchone()
        if not playlist_id:
            conn.close()
            return "La playlist no existe en la base de datos."
        playlist_id = playlist_id[0]
        # 2. Obtener todos los song_id que coincidan con el playlist_id en la tabla songs_playlist
        cursor.execute("SELECT song_id FROM songs_playlist WHERE playlist_id = ?", (playlist_id,))
        song_ids = cursor.fetchall()
        if not song_ids:
            conn.close()
            return "No hay canciones asociadas a esta playlist."
        # 3. Buscar en la tabla songs por cada song_id para encontrar el nombre que coincida
        for song_id_tuple in song_ids:
            song_id = song_id_tuple[0]
            cursor.execute("SELECT name FROM songs WHERE song_id = ?", (song_id,))
            song_name = cursor.fetchone()
            # 4. Comparar el nombre con el proporcionado
            if song_name and song_name[0] == name:
                # 5. Eliminar la relación en songs_playlist
                cursor.execute("DELETE FROM songs_playlist WHERE song_id = ? AND playlist_id = ?", (song_id, playlist_id))
                conn.commit()
                conn.close()
                return f"La canción '{name}' ha sido eliminada de la playlist '{playlist}'."
        # Si no se encontró la canción
        conn.close()
        return "La canción no se encontró en la playlist."


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