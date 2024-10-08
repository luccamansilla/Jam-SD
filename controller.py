import os
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl, QTime
from PyQt5.QtWidgets import QFileDialog ,QDialog
import Pyro5.api 
import serpent
import sqlite3 as db
from view import UserDialog, PlaylistDialog
import threading
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt5.QtCore import QTimer
import socket



class MusicPlayerController(QObject):
    
    update_gui_signal = pyqtSignal(str, str, str, str)  # Define la señal (ej: para actualizar canción, posición, estado)
    update_gui_signalSongs  = pyqtSignal()
    update_gui_ReceiveSong  = pyqtSignal(dict, str)
    
    def __init__(self, view):
        super().__init__()  # Asegúrate de llamar al constructor de QObject

        # Mostrar la ventana modal para ingresar el nombre de usuario
        client_ip = socket.gethostbyname(socket.gethostname())
        self.user_name = self.getUserName()
        print(f"Usuario ingresado: {self.user_name}")  # Solo para comprobar que obtenemos el nombre

        # Crear el Daemon Pyro y registrar el objeto del cliente
        daemon = Pyro5.api.Daemon(host=client_ip)  # Crear el daemon Pyro para el cliente
        self.client_uri = daemon.register(self)  # Registrar el objeto cliente

        # Registrar el cliente en el servidor (pasar el URI del cliente al servidor)
        nameserver = Pyro5.api.locate_ns()
        self.server_uri = nameserver.lookup("playlist2")  # Busca el servidor
        self.client = Pyro5.api.Proxy(self.server_uri)
        #self.client.register_client(self.client_uri)  # Pasar el URI del cliente al servidor

        print(f"Cliente registrado en el servidor con URI: {self.client_uri}")

         # Iniciar el daemon en un hilo separado para escuchar invocaciones desde el servidor
        self.daemon_thread = threading.Thread(target=daemon.requestLoop)
        self.daemon_thread.daemon = True  # El hilo se detiene cuando el programa principal termina
        self.daemon_thread.start()

        self.view = view
        self.player = QMediaPlayer()
        self.current_playlist = f"{self.user_name}Playlist"
        self.current_song = None
        self.current_time = None
        self.current_duration = None
        self.current_state = None
        self.vector_clocks = {}  # {playlist_name: RelojVectorial}


        self.update_gui_signal.connect(self.update_song_state)#conecion al principa;
        self.update_gui_signalSongs.connect(self.onPlaylistSelected)#conecion al principa;
        self.update_gui_ReceiveSong.connect(self.receiveFile)#conecion al principa;
        self.view.addSongButton.clicked.connect(self.addSong)
        self.view.sharePlaylistButton.clicked.connect(self.makeCollaborative)
        self.view.seePlaylistsButton.clicked.connect(self.viewPlaylists)
        self.view.removeSongButton.clicked.connect(self.removeSong)
        self.view.playButton.clicked.connect(self.playSong)
        self.view.stopButton.clicked.connect(self.stopSong)
        self.player.positionChanged.connect(self.updateProgressBar)
        self.player.durationChanged.connect(self.updateProgressBarRange)
        self.view.progressBar.sliderReleased.connect(self.setSongPosition)
        self.client.insert_client(self.user_name,self.client_uri)

        
    @pyqtSlot()  
    def onPlaylistSelected(self):
        self.view.setWindowTitle(f"Reproductor de música - Playlist: {self.current_playlist}")
        self.view.songList.clear()
        songs = self.client.load_songs(self.current_playlist)
        for song in songs:
            self.view.songList.addItem(song[0])
            
    def loadSongPlaylist(self, playlist):
        self.view.setWindowTitle(f"Reproductor de música - Playlist: {playlist}")
        self.view.songList.clear()
        songs = self.client.load_songs(playlist)
        for song in songs:
            self.view.songList.addItem(song[0])
            # playlist_widget.addItem(playlist[1])
        
        
    def addSong(self):
        file_path, _ = QFileDialog.getOpenFileName(self.view, "Selecciona una canción", "", "Audio Files (*.mp3 *.wav *.ogg)")
        if file_path:
            self.sendSongToServer(file_path)
            
    def viewPlaylists(self):
        playlists = self.client.get_playlists()
        print(playlists)
        dialog = PlaylistDialog(playlists, self.view)  
        if dialog.exec_() == QDialog.Accepted:
            selected_playlist = dialog.getSelectedPlaylist()
            self.current_playlist = selected_playlist
            self.client.insert_playlist_in_users_playlist(self.current_playlist, self.client_uri, 0)
            self.loadSongPlaylist(selected_playlist)
            self.request_initial_state()

    def getUserName(self):
            # Crear el diálogo para obtener el nombre de usuario
            dialog = UserDialog()

            # Mostrar el diálogo de forma modal (espera a que se cierre para continuar)
            if dialog.exec_() == QDialog.Accepted:
                return dialog.getUserName()
            return "UsuarioDesconocido"  # Valor por defecto si no se ingresa nada
        
            
    def sendSongToServer(self, file_path):
        with open(file_path, "rb") as file:
            data = file.read()
            filename = os.path.basename(file.name)
            try:
                self.client.transfer(data, filename, self.current_playlist)
                self.client.insertSong(filename, filename, self.current_playlist)
                self.client.get_shared_status(self.current_playlist, self.client_uri)
                print(f"Archivo {filename} enviado al servidor")
            except Exception as e:
                print(f"Error al enviar la canción al servidor: {e}")
                
    def removeSong(self):
        selected_song = self.view.songList.currentItem()
        if selected_song:
            self.client.deleteSong(selected_song.text(), self.current_playlist)
            self.client.get_shared_status(self.current_playlist, self.client_uri)
            # self.view.songList.takeItem(self.view.songList.row(selected_song))


    #hacer playlist colaborativa
    def makeCollaborative(self):
        self.client.insert_playlist_in_users_playlist(self.current_playlist, self.client_uri, 1) 
        self.client.update_is_shared(self.current_playlist) #pone en 1 la playlist en columna is_shared


    def playSong(self):
        song_name = self.view.songList.currentItem().text() if self.view.songList.currentItem() else self.current_song
        current_time = self.view.currentTimeLabel.text() if self.view.currentTimeLabel.text() else self.current_time
        duration = self.view.durationTimeLabel.text() if self.view.durationTimeLabel.text() else self.current_duration

        # if not selected_song:
        #     self.view.warningLabel.setText("No seleccionó ninguna canción")
        #     self.view.warningLabel.setVisible(True)
        #     return        

        # reproductor = reproduciendo
        if self.player.state() == QMediaPlayer.PlayingState:
            self.client.update_playlist_state(self.current_playlist, song_name, current_time, 'pausado', duration, self.client_uri)
        #reproductor = pausado
        elif self.player.state() == QMediaPlayer.PausedState:
            self.client.update_playlist_state(self.current_playlist, song_name, current_time, 'renaudar', duration, self.client_uri)
    
        else:
            # Primera vez que se reproduce una canción
            if not song_name:
                self.view.warningLabel.setText("No hay canción seleccionada")
                self.view.warningLabel.setVisible(True)
                return        
            song_path = os.path.join(os.getcwd(), 'songs', song_name)
            if not os.path.exists(song_path):
                self.view.warningLabel.setText("Archivo de canción no encontrado")
                self.view.warningLabel.setVisible(True)
                return
            self.current_song = song_name
            if self.current_state == "pausado":
                self.client.update_playlist_state(self.current_playlist, song_name, current_time, 'renaudar',duration,self.client_uri)
                self.client.update_playlist_state(self.current_playlist, song_name, current_time, 'renaudar',duration,self.client_uri)
            else:
                self.client.update_playlist_state(self.current_playlist, song_name, current_time, 'reproduciendo',duration,self.client_uri)
           
                self.client.update_playlist_state(self.current_playlist, song_name, current_time, 'reproduciendo',duration,self.client_uri)
           

    def close_app(self):
        self.client.deleteUser(self.client_uri)
        clients = self.client.get_clients_in_playlist(self.current_playlist)
        if len(clients) == 0:
            self.client.deletePlaylistShared(self.current_playlist)
        print(f"se fue el usuario {self.client_uri}")


    @Pyro5.api.expose #llamo al hilo principal
    def mainThread(self, song_name, position, state , duration):
        self.update_gui_signal.emit(song_name, position, state ,duration)
        
    @Pyro5.api.expose #llamo al hilo principal para actualizar canciones
    def mainThreadUpdateSongs(self):
        self.update_gui_signalSongs.emit()
    
    @Pyro5.api.expose #llamo al hilo principal para actualizar canciones
    def mainThreadReceiveSong(self, data, filename):
        self.update_gui_ReceiveSong.emit(data, filename)

    
    @pyqtSlot(str, str, str, str)
    def update_song_state(self, song_path, position, state , duration):
        try:
            path = os.path.join(os.getcwd(), song_path)
            print(f"PATH DESDE UPLOAD SONG STATE{path}")
            self.view.warningLabel.setText("SEGUNDO RECIBIDOS DE LA CANCION {}".format(position))
            self.view.warningLabel.setVisible(True)

           # Convertir posición y duración a milisegundos
            position_milliseconds = self.convert_to_milliseconds(position)
            duration_milliseconds = self.convert_to_milliseconds(duration)
            
            # Actualizar la interfaz de usuario
            self.updateProgressBar(position_milliseconds) 
            self.updateProgressBarRange(duration_milliseconds)

            self.player.setPosition(position_milliseconds)
            print(state)
            if state == 'pausado':
                self.player.pause()
                self.view.playButton.setText("Reanudar")
            elif state == 'reproduciendo':
                if song_path:  
                    url = QUrl.fromLocalFile(path)
                    content = QMediaContent(url)
                    self.player.setMedia(content)
                    self.player.setPosition(position_milliseconds)
                    self.player.play()
                self.view.playButton.setText("Pausar")
            elif state == 'renaudar':                
                if not self.player.media().isNull():
                    print("El QMediaPlayer tiene un archivo cargado.")
                else:
                    print("No hay archivo cargado en el QMediaPlayer.")
                    url = QUrl.fromLocalFile(path)
                    content = QMediaContent(url)
                    self.player.setMedia(content)
                    self.player.setPosition(position_milliseconds)
                self.player.play()
                self.view.playButton.setText("Pausar")
            elif state == 'stop':
                print("ENTRO STOP")
                self.player.stop()
                self.view.playButton.setText("Reproducir")
                self.player.setMedia(QMediaContent())

        except Exception as e:
            print(f"Error en update_song_state: {e}")

    def convert_to_milliseconds(self, time):
        if isinstance(time, str):
            try:
                minutes, seconds = map(int, time.split(':'))
                return (minutes * 60 + seconds) * 1000
            except ValueError:
                print(f"Error al convertir el tiempo: {time}")
                return 0

    #cliente se conecta llama a este metodo para obtener estado actual de cancion
    def request_initial_state(self):
        if self.current_playlist:
            try:
                state = self.client.get_playlist_state(self.current_playlist)
                print(f"ESTADOS {state}")
                if state:
                    print(f"ESTADO CANCIOIN VOLVIEWNDO {state['song']}")
                    self.current_song = state['song']
                    self.current_time = state['position']
                    self.current_duration = state['duration']
                    self.current_state = state['state']
                    path = self.client.get_song_path(state['song'])
                    self.mainThread(path, state['position'], state['state'] , state['duration'])
            except Exception as e:
                print(f"Error al solicitar el estado inicial de la playlist: {e}")

    #recibo el clock del el servidor para actualizar el clock del cliente
    def receive_update(self, playlist_name, state, clock):
        if playlist_name not in self.vector_clocks:
            num_clients = len(self.servidor.get_clients_in_playlist(playlist_name))
            self.vector_clocks[playlist_name] = RelojVectorial(num_clients)
        self.vector_clocks[playlist_name].fusionar(clock)
        # Actualizar la interfaz o estado local según el estado recibido
        print(f"Actualización recibida para playlist {playlist_name}: {state}, Reloj: {self.vector_clocks[playlist_name]}")
      
    
    @pyqtSlot(dict, str)  
    def receiveFile(self, data, filename):
        file_path = os.path.join("songs", filename)
        if Pyro5.api.config.SERIALIZER == "serpent" and isinstance(data, dict):
            data = serpent.tobytes(data)
        print(f"FILE PATH {file_path}")
        try:
            with open(file_path, "wb") as file:
                file.write(data)
                print(f"Archivo {filename} guardado en el cliente en: {file_path}")
        except Exception as e:
            print(f"Error al guardar el archivo {filename} en el cliente: {e}")
        
    def stopSong(self):
        selected_song = self.view.songList.currentItem()
        song_name = None
        current_time = '0:0'
        duration = '0:0'
        self.client.update_playlist_state(self.current_playlist, song_name, current_time, 'stop', duration, self.client_uri)


    def updateProgressBar(self, position):
        self.view.progressBar.setValue(position)
        current_time = QTime(0, 0).addMSecs(position)
        self.view.currentTimeLabel.setText(current_time.toString("mm:ss"))
    
    def updateProgressBarRange(self, duration): #asegura el rango de la barra usar cuando cambiemos de cancion
        self.view.progressBar.setRange(0, duration)
        total_time = QTime(0, 0).addMSecs(duration)
        self.view.durationTimeLabel.setText(total_time.toString("mm:ss"))

    def setSongPosition(self):
        new_position = self.view.progressBar.value()
        self.player.setPosition(new_position)

    def getPosition(self):
        return self.view.progressBar.value()
        
    def connect_db(self):
        return db.connect('spotify.db')
    
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
        
    def get_playlists(self):
        conn = self.connect_db()
        cursor = conn.cursor()

        # Ajustar la consulta para obtener solo las playlists donde user_leader = 1
        cursor.execute("SELECT name FROM playlist WHERE is_shared = 0")
        playlists = cursor.fetchall()

        conn.close()
        return [playlist[0] for playlist in playlists]

    
    def load_playlists(self):
        playlists = self.get_playlists()
        self.playlistList.clear()  # Asumiendo que tienes un QListWidget para mostrar las playlists
        for playlist in playlists:
            self.playlistList.addItem(playlist[1]) 
    

    def initialize_vector_clock(self, playlist_name):
        # Obtener los user_id en la playlist
        user_ids = self.load_user_ids_in_playlist(playlist_name)

        # Crear un reloj vectorial de longitud igual al número de usuarios en la playlist
        vector_clock = [0] * len(user_ids)

        # Asignar la posición en el vector basada en el orden de los IDs (o algún criterio)
        self.vector_position = user_ids.index(self.user_id)

        return vector_clock



        
        