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
        self.id = id  # ID único del nodo
        self.lider = 1
        self.nodos = nodos  # Lista de nodos (ID, URI)
        self.activo = True
        
        self.ultima_vez_recibido = time.time()  # Tiempo de recepción del último heartbeat
        self.timeout = 5  # Tiempo de espera para recibir un heartbeat

        # Banderas para controlar la creación de hilos
        self.heartbeat_activo = False
        self.deteccion_fallo_activo = False
    
        
        self.nameserver = Pyro5.core.locate_ns()
        self.songs_states = {}  # Diccionario para almacenar el estado de cada cancion
        #self.clients = {}  # Diccionario para almacenar los proxies de los clientes
        self.vector_clock = {} 
        #self.clientes = []

    @Pyro5.api.expose
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
    def deletePlaylistShared(self, playlist_name):
        conn = self.connect_db()
        cursor = conn.cursor()

        # Obtener el ID de la playlist basado en su nombre
        cursor.execute("SELECT playlist_id FROM playlist WHERE name = ?", (playlist_name,))
        playlist_row = cursor.fetchone()
        if not playlist_row:
            return []  # Playlist no encontrada

        playlist_id = playlist_row[0]
        
        cursor.execute("""
            DELETE FROM playlist
            WHERE playlist_id = ?
        """, (playlist_id,))
        conn.commit()
        cursor.close()
    
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
    def insert_playlist_in_users_playlist(self, current_playlist, client_uri, is_leader):
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
                        (user_id, playlist_id, is_leader))  # user_leader será 1

            conn.commit()
            print(f"El usuario con id:  {user_id} hizo colaborativa la playlist con id : {playlist_id}")
            
        except Exception as e:
            print(f"Error al insertar el usuario en la playlist: {e}")
        finally:
            conn.close()

    #actualizo el clock de cada cliente en la playlist
    @Pyro5.api.expose
    def update_state(self, playlist_name, state, clock):
        current_clock.fusionar(clock)
        self.vector_clock[playlist_name] = (current_clock)

         # Notificar a todos los clientes de la playlist
        for client in self.get_clients_in_playlist(playlist_name):
            client.receive_update(playlist_name, state, current_clock.obtener_reloj())


        #actualiza estado de la cancion en la platlist
    
    @Pyro5.api.expose
    def update_playlist_state(self, playlist_name, song_name, position, state , duration ,uri_client):
        if playlist_name not in self.songs_states:
            self.songs_states[playlist_name] = {}
        self.songs_states[playlist_name] = {
            'song': song_name,
            'position': position,
            'state': state,
            'duration': duration
        }
        self.shared_status(playlist_name,uri_client)
    
    @Pyro5.api.expose
    def shared_status(self, playlist_name, client_uri):
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
        # Si la playlist es compartida (is_shared = 1), llama al método
        if is_shared == 1:
            self.sync_clients(playlist_name)
        else:
            try:
                state = self.songs_states[playlist_name]
                path = self.get_song_path(state['song'])
                print(f"holaaa{path}")
                proxy = Pyro5.api.Proxy(client_uri)
                proxy.mainThread(path, state['position'], state['state'] , state['duration'])
            except Exception as e:
                print(f"Error al actualizar las canciones del cliente {client_uri}: {e}")

    #sincroniza a todos los clientes el estado de la cancion
    @Pyro5.api.expose
    def sync_clients(self, playlist_name):
        if playlist_name not in self.songs_states:
            return

        clients = self.get_clients_in_playlist(playlist_name) 
        state = self.songs_states[playlist_name]
        for client_uri in clients: 
            print(f"CLIENTE ACTUAL   {client_uri}")
            try:
                path = self.get_song_path(state['song'])
                print(path)
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

    @Pyro5.api.expose
    def connect_db(self):
        return db.connect('spotify.db')
   
    @Pyro5.api.expose
    def get_playlist_state(self, playlist_name):
        return self.songs_states.get(playlist_name, {})    

    @Pyro5.api.expose
    def notify_clients(self , playlist_name): 
        clients = self.get_clients_in_playlist(playlist_name) 
        for cliente in clients:
            print(f"NOTIFICANDO CLIENTE {cliente}")
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


    @Pyro5.api.expose
    def transfer(self, data, filename, playlist):
        if Pyro5.api.config.SERIALIZER == "serpent" and isinstance(data, dict):
            data = serpent.tobytes(data)  # Convertir el diccionario en bytes si es necesario
        
        file_path = os.path.join(save_directory, filename)
        print(f"Ruta de archivo configurada: {file_path}")

        if not os.path.exists(file_path):
            try:
                self.shareSongFile(data, filename, playlist)
                with open(file_path, "wb") as f:
                    f.write(data)
                    print(f"Archivo guardado en: {file_path}")
                    self.propagarDatos(data, filename)
            except Exception as e:
                print(f"Failed to save the file: {e}")
        else:
            print("Ya existe un archivo con el mismo nombre, no se volvió a guardar el archivo")
        return len(data)
    
    @Pyro5.api.expose
    def shareSongFile(self, data, filename, playlist):
        clients= self.get_clients_in_playlist(playlist)
        # Enviar el archivo a cada cliente
        for client in clients:
            try:
                print(f"Enviando {filename} a {client}")
                client = Pyro5.api.Proxy(client)  # Crea un proxy para el cliente
                client.mainThreadReceiveSong(data, filename)  # Llamar al método que implementes en el cliente para recibir archivos
            except Exception as e:
                print(f"Error al enviar el archivo a {client}: {e}")


    @Pyro5.api.expose
    def propagarDatos(self, data, filename):
         for nodo in self.nodos:
            if nodo[0] != self.lider:
                try:
                    proxy = Pyro5.api.Proxy(f"PYRONAME:{nodo[1]}")
                    proxy.transfer(data, filename);
                    print(f"Nodo {nodo[1]}: Propagacion exitosa!!...")
                except Exception as e:
                    print(f"Nodo {nodo[1]} no está disponible para comunicarlo, nodo no se actualizo con la información (inactivo). Error: {e}")
            

    @Pyro5.api.expose
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

    @Pyro5.api.expose
    def eleccion(self, nodo_id):
        """Respuesta a la solicitud de elección"""
        if nodo_id < self.id:
            print(f"Nodo {self.id} recibe solicitud de elección de {nodo_id} y responde.")
            proxy = Pyro5.api.Proxy(f"PYRONAME:{self.nodos[nodo_id-1][1]}")
            proxy.aceptar_eleccion(self.id)
            self.iniciar_eleccion()
    
    @Pyro5.api.expose
    def aceptar_eleccion(self, nuevo_lider_id):
        """Actualiza el nodo con el nuevo líder"""
        print(f"Nodo {self.id} acepta a {nuevo_lider_id} como líder.")
        self.lider = nuevo_lider_id

        if self.lider == self.id:
            print(f"Nodo {self.id} es ahora el líder, iniciando envío de heartbeats.")
            self.iniciar_heartbeat()  # Inicia heartbeats si se convierte en líder
    
    @Pyro5.api.expose
    def nuevo_lider(self, lider_id):
        """Notifica a los nodos que hay un nuevo líder"""
        print(f"Nodo {self.id} fue notificado que el nuevo líder es {lider_id}")
        self.lider = lider_id

    @Pyro5.api.expose
    def iniciar_heartbeat(self):
        """Inicia el envío de heartbeats si no está ya activo"""
        if not self.heartbeat_activo:
            self.heartbeat_activo = True
            threading.Thread(target=self.enviar_heartbeat).start()

    @Pyro5.api.expose
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

    @Pyro5.api.expose
    def recibir_heartbeat(self):
        """Recibe un heartbeat del líder"""
        self.ultima_vez_recibido = time.time()
        print(f"Nodo {self.id} recibió heartbeat del líder.")
        
        # print(f"hilo de deteccion de fallos:... {self.deteccion_fallo_activo}")

        self.iniciar_deteccion_fallo()

    @Pyro5.api.expose
    def iniciar_deteccion_fallo(self):
        """Inicia la detección de fallos si no está ya activa"""
        if not self.deteccion_fallo_activo:
            self.deteccion_fallo_activo = True
            threading.Thread(target=self.detectar_fallo_lider).start()

    @Pyro5.api.expose
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

    @Pyro5.api.expose
    def ping(self):
        """Manejo de ping para comprobar si el nodo está activo"""
        return "Nodo activo"

    @Pyro5.api.expose
    def getLider(self):
        """Retorno de Lider"""
        
        print(f"Lider es el Nodo {self.lider}:... {self.nodos[self.id - 1][1]}")
        # return Pyro5.api.Proxy(f"PYRONAME:{self.nodos[self.lider][1]}")
 

    # CONSULTAS A LA BD
    
    @Pyro5.api.expose
    def connect_db(self):
        return db.connect('spotify.db')
    
    @Pyro5.api.expose
    def get_playlists(self):
        conn = self.connect_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM playlist WHERE is_shared = 1")
        playlists = cursor.fetchall()

        conn.close()
        return [playlist[1] for playlist in playlists]

    @Pyro5.api.expose
    def insertSong(self, name, path, playlist):
        conn = self.connect_db()
        cursor = conn.cursor()
        pathNew = "songs/"+path
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

    @Pyro5.api.expose
    def deleteUser(self, client_uri):
        try:
            conn = self.connect_db()
            cursor = conn.cursor()
            
            # Convertir URI a string
            client_uri_str = str(client_uri)
            
            # Paso 1: Buscar el user_id del usuario basado en su URI
            cursor.execute("SELECT user_id FROM users WHERE uri = ?", (client_uri_str,))
            user_result = cursor.fetchone()
            
            if not user_result:
                raise Exception(f"No se encontró un usuario con URI: {client_uri}")
            
            user_id = user_result[0]
            
            # Paso 2: Eliminar el usuario de la tabla users
            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            
            # Paso 3: Eliminar el usuario de la tabla users_playlist usando su user_id
            cursor.execute("DELETE FROM users_playlist WHERE user_id = ?", (user_id,))
            
            conn.commit()
            print(f"El usuario con URI {client_uri_str} y ID {user_id} fue eliminado correctamente.")
            
        except Exception as e:
            print(f"Error al eliminar el usuario: {e}")
        finally:
            conn.close()


# Configuración del entorno de nodos
hostname = socket.gethostname()
IPAddr = socket.gethostbyname(hostname)
print(f"IP NODO {IPAddr}")
# Lista de nodos (ID, URI)
nodos = [
    (1, "playlist1"),
    (2, "playlist2"),
    # (3, "playlist3"),
]

# El ID de este nodo
node_id = 1 # Cambiar este ID para cada nodo que levantes (1, 2, 3, etc.)

daemon = Pyro5.server.Daemon(host=IPAddr)

ns = Pyro5.api.locate_ns()

# Registrar la clase Testclass con el sistema de nombres
nodo = Testclass(node_id, nodos)
uri = daemon.register(nodo)
ns.register(f"playlist{node_id}", uri)
print(f"Nodo {node_id} registrado con URI: {uri}")

# Iniciar hilos de heartbeat y detección de fallos de manera controlada
# nodo.iniciar_heartbeat()
# nodo.iniciar_deteccion_fallo()

# Iniciar el bucle de solicitudes
print("Nodo listo para recibir solicitudes.")
daemon.requestLoop()

# if __name__ == "__main__":
#     node_id =1 #int(sys.argv[1])  # Toma el ID del nodo desde los argumentos de línea de comandos
#     listPort =[0,5001,5002,5003];
#     nodos = [
#         (1, "playlist"),
#     ]
    
#     daemon = Pyro5.server.Daemon(host=socket.gethostbyname(socket.gethostname()), port=listPort[node_id])
#     ns = Pyro5.api.locate_ns()

#     # Registrar el nodo
#     uri = daemon.register(Testclass(node_id, nodos))
#     ns.register(f"playlist", uri)
    
#     nodo = Testclass(node_id, nodos)
#     threading.Thread(target=nodo.detectar_fallo_lider).start()

#     print(f"Nodo {node_id} listo en {uri}")
#     daemon.requestLoop()