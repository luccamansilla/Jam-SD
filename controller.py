import os
from lamport_clock import LamportClock
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl, QTime
from PyQt5.QtWidgets import QFileDialog
import Pyro5.api 


class MusicPlayerController:
    def __init__(self, view):
        self.view = view
        self.player = QMediaPlayer()
        self.nameserver = Pyro5.core.locate_ns()
        self.uri = self.nameserver.lookup("luccaplaylist")
        self.client = Pyro5.api.Proxy(self.uri)
         # Reloj lógico de Lamport
        self.lamport_clock = LamportClock()

        # Diccionario para almacenar playlists y sus canciones
        self.playlists = {}
        self.current_playlist = None  # Playlist actual seleccionada

        # Conectar señales y slots
        self.view.addSongButton.clicked.connect(self.addSong)
        self.view.seePlaylistsButton.clicked.connect(self.viewPlaylists)
        self.view.removeSongButton.clicked.connect(self.removeSong)
        self.view.playButton.clicked.connect(self.playSong)
        self.view.stopButton.clicked.connect(self.stopSong)
        self.player.positionChanged.connect(self.updateProgressBar)
        self.player.durationChanged.connect(self.updateProgressBarRange)
        self.view.progressBar.sliderReleased.connect(self.setSongPosition)
        self.view.playlistComboBox.currentIndexChanged.connect(self.onPlaylistSelected)

        # Inicializar playlists
        self.updatePlaylists()

    def addSong(self):
        if self.current_playlist is None:
            self.view.warningLabel.setText("Seleccione una playlist primero")
            self.view.warningLabel.setStyleSheet("color: red;")
            self.view.warningLabel.setVisible(True)
            return

        # Actualizar reloj lógico 
        self.lamport_clock.increment()
        timestamp = self.lamport_clock.get_time()

        file_path, _ = QFileDialog.getOpenFileName(self.view, "Selecciona una canción", "", "Audio Files (*.mp3 *.wav *.ogg)")
        if file_path:
            song_name = os.path.basename(file_path)
            
            # Verificar si la canción ya existe en la playlist
            if any(os.path.basename(song) == song_name for song in self.playlists[self.current_playlist]):
                self.view.warningLabel.setText("La canción ya se encuentra en la playlist")
                self.view.warningLabel.setStyleSheet("color: red;")
                self.view.warningLabel.setVisible(True)
                return
            
            # Si no existe, agregar la canción a la playlist
            self.view.warningLabel.setText("")
            self.view.warningLabel.setVisible(False)
            self.view.songList.addItem(song_name)
            self.playlists[self.current_playlist].append(file_path)  # Agregar canción a la playlist actual
            print(f"Canción '{song_name}' agregada a la playlist '{self.current_playlist}'.")
            
             # Envio la cancion y el timepo al servidor , Después de recibir la respuesta del servidor (su hora)
            response_data, server_timestamp = self.sendSongToServer(file_path, timestamp)
            self.lamport_clock.update(server_timestamp) #actualizo con el reloj del servidor

    def viewPlaylists(self):
        if self.view.playlistWidget.isVisible():
            self.view.playlistWidget.setVisible(False)
        else:
            self.updatePlaylists()
            self.view.playlistWidget.setVisible(True)

    def updatePlaylists(self):
        self.view.playlistWidget.clear()
        self.view.playlistComboBox.clear()
        self.playlists = {}  # Limpiar playlists actuales
        playlists = self.nameserver.list()
        for playlist_name in playlists:
            self.view.playlistComboBox.addItem(playlist_name)
            self.playlists[playlist_name] = []  # Inicializar lista de canciones para cada playlist

    def sendSongToServer(self, file_path , timestamp):
        self.lamport_clock.increment()   #accion incremento reloj lamport
        timestamp = self.lamport_clock.get_time()

        with open(file_path, "rb") as file:
            data = file.read()
            filename = os.path.basename(file.name)
            try:
                response_data ,server_timestamp = self.client.transfer(data, filename, timestamp)  # Ahora recibe el timestamp del servidor
                print(f"Archivo '{filename}' enviado al servidor.")
                return response_data, server_timestamp
            except Exception as e:
                print(f"Error al enviar la canción al servidor: {e}")
                return None, timestamp  # En caso de error, devolver el timestamp local


    def removeSong(self):
        if self.current_playlist is None:
            self.view.warningLabel.setText("Seleccione una playlist primero")
            self.view.warningLabel.setVisible(True)
            return

        selected_song = self.view.songList.currentItem()
        if selected_song:
            song_name = selected_song.text()
            song_path = next((p for p in self.playlists[self.current_playlist] if os.path.basename(p) == song_name), None)
            if song_path:
                self.playlists[self.current_playlist].remove(song_path)
                self.view.songList.takeItem(self.view.songList.row(selected_song))
                print(f"Canción '{song_name}' eliminada de la playlist '{self.current_playlist}'.")

                 # incremento reloj y Informa al servidor que la canción ha sido eliminada lamport
                self.lamport_clock.increment()
                timestamp = self.lamport_clock.get_time()
                try:
                    server_timestamp = self.client.removeSongFromPlaylist(song_name, self.current_playlist, timestamp)
                    self.lamport_clock.update(server_timestamp)
                except Exception as e:
                    print(f"Error al informar al servidor sobre la eliminación de la canción: {e}")


    def playSong(self):
        selected_song = self.view.songList.currentItem()

        if not selected_song:
            self.view.warningLabel.setText("No seleccionó ninguna canción")
            self.view.warningLabel.setVisible(True)
            return

        #incremento reloj lamport
        self.lamport_clock.increment()
        timestamp = self.lamport_clock.get_time()

        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.view.playButton.setText("Renaudar")
             
             # Informar al servidor que la canción ha sido pausada
            try:
                server_timestamp = self.client.updatePlaybackState(selected_song.text(), "paused", timestamp)
                self.lamport_clock.update(server_timestamp)
            except Exception as e:
                print(f"Error al enviar el estado de reproducción al servidor: {e}")
        
        elif self.player.state() == QMediaPlayer.PausedState:
            self.player.play()
            self.view.playButton.setText("Pausar")

             # Informar al servidor que la canción ha sido reanudada
            try:
                server_timestamp = self.client.updatePlaybackState(selected_song.text(), "playing", timestamp)
                self.lamport_clock.update(server_timestamp)  # Actualizar con el timestamp del servidor
            except Exception as e:
                print(f"Error al enviar el estado de reproducción al servidor: {e}")
        
        else:
            self.view.warningLabel.setText("")
            self.view.warningLabel.setVisible(False)
            song_path = next((p for p in self.playlists[self.current_playlist] if os.path.basename(p) == selected_song.text()), None)
            if song_path:
                url = QUrl.fromLocalFile(song_path)
                content = QMediaContent(url)
                self.player.setMedia(content)
                self.player.play()
                self.view.playButton.setText("Pausar")
                self.view.songNameLabel.setText(f"Reproduciendo: {os.path.basename(song_path)}")

                # Informar al servidor que la canción ha comenzado a reproducirse
                try:
                    server_timestamp = self.client.updatePlaybackState(selected_song.text(), "playing", timestamp)
                    self.lamport_clock.update(server_timestamp)  # Actualizar con el timestamp del servidor
                except Exception as e:
                    print(f"Error al enviar el estado de reproducción al servidor: {e}")


    def stopSong(self):
        selected_song = self.view.songList.currentItem()
        self.player.stop()
        self.view.playButton.setText("Reproducir")

        # incremento reloj y Informar al servidor que la canción ha sido detenida
        self.lamport_clock.increment()
        timestamp = self.lamport_clock.get_time()
        try:
            server_timestamp = self.client.updatePlaybackState(selected_song.text(), "stopped", timestamp)
            self.lamport_clock.update(server_timestamp)
        except Exception as e:
            print(f"Error al enviar el estado de reproducción al servidor: {e}")


    def updateProgressBar(self, position):
        self.view.progressBar.setValue(position)
        current_time = QTime(0, 0).addMSecs(position)
        self.view.currentTimeLabel.setText(current_time.toString("mm:ss"))

    def updateProgressBarRange(self, duration):
        self.view.progressBar.setRange(0, duration)
        total_time = QTime(0, 0).addMSecs(duration)
        self.view.durationTimeLabel.setText(total_time.toString("mm:ss"))

    def setSongPosition(self):
        new_position = self.view.progressBar.value()
        self.player.setPosition(new_position)

    def onPlaylistSelected(self): #me dice en que playlist estoy
        self.current_playlist = self.view.playlistComboBox.currentText()
        self.view.setWindowTitle(f"Reproductor de música - Playlist: {self.current_playlist}")
        self.updateSongList()

    def updateSongList(self): #actualizo la interfaz con la lista de canciones segun la playlist
        self.view.songList.clear()
        if self.current_playlist in self.playlists:
            for song_path in self.playlists[self.current_playlist]:
                self.view.songList.addItem(os.path.basename(song_path))
