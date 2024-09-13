import os
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl, QTime
from PyQt5.QtWidgets import QFileDialog
import Pyro5.api 
import sqlite3 as db
from view import PlaylistDialog

class MusicPlayerController:
    def __init__(self, view):
        
        self.view = view
        self.player = QMediaPlayer()
        self.nameserver = Pyro5.core.locate_ns()
        self.uri= self.nameserver.lookup("playlist")         
        self.client = Pyro5.api.Proxy(self.uri)
        self.current_playlist = None
        self.current_song = None

        self.view.addSongButton.clicked.connect(self.addSong)
        self.view.seePlaylistsButton.clicked.connect(self.viewPlaylists)
        self.view.removeSongButton.clicked.connect(self.removeSong)
        self.view.playButton.clicked.connect(self.playSong)
        self.view.stopButton.clicked.connect(self.stopSong)
        self.player.positionChanged.connect(self.updateProgressBar)
        self.player.durationChanged.connect(self.updateProgressBarRange)
        self.view.progressBar.sliderReleased.connect(self.setSongPosition)
        self.view.playlistComboBox.currentIndexChanged.connect(self.onPlaylistSelected)

        self.updatePlaylists()
        
        
    def onPlaylistSelected(self): #me dice en que playlist estoy
        self.current_playlist = self.view.playlistComboBox.currentText()
        self.view.setWindowTitle(f"Reproductor de música - Playlist: {self.current_playlist}")
        self.view.songList.clear()
        songs = self.load_songs(self.view.playlistComboBox.currentText())
        for song in songs:
            self.view.songList.addItem(song[0])
            # playlist_widget.addItem(playlist[1])
        
        
    def addSong(self):
        file_path, _ = QFileDialog.getOpenFileName(self.view, "Selecciona una canción", "", "Audio Files (*.mp3 *.wav *.ogg)")
        if file_path:
            self.sendSongToServer(file_path)
            
    def viewPlaylists(self):
        dialog = PlaylistDialog(self.view)
        self.updatePlaylists()
        dialog.exec_()

    def updatePlaylists(self):
        playlists = self.get_playlists()
        self.view.playlistComboBox.clear()
        print(playlists)
        for playlist in playlists:
            self.view.playlistComboBox.addItem(str(playlist[1]))
        self.request_initial_state() #si recien entra llama al metodo para sincronizar el estado de la cancion
        
            
            
    def sendSongToServer(self, file_path):
        with open(file_path, "rb") as file:
            data = file.read()
            filename = os.path.basename(file.name)
            try:
                self.client.transfer(data, filename)
                self.insertSong(filename, filename, self.view.playlistComboBox.currentText())
                self.onPlaylistSelected()
                print(f"Archivo {filename} enviado al servidor")
            except Exception as e:
                print(f"Error al enviar la canción al servidor: {e}")
                
    def removeSong(self):
        selected_song = self.view.songList.currentItem()
        if selected_song:
            self.deleteSong(selected_song.text(), self.view.playlistComboBox.currentText())
            self.onPlaylistSelected()
            # self.view.songList.takeItem(self.view.songList.row(selected_song))

    def playSong(self):
        selected_song = self.view.songList.currentItem()
        song_name = selected_song.text()
        current_time = self.view.currentTimeLabel.text()
        if current_time == '':
            current_time = '0:0'

        if not selected_song:
            self.view.warningLabel.setText("No seleccionó ninguna canción")
            self.view.warningLabel.setVisible(True)
            return

        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.view.playButton.setText("Renaudar")
            self.client.update_playlist_state(self.current_playlist, song_name, current_time,'pausado')

        elif self.player.state() == QMediaPlayer.PausedState:
            self.player.play()
            self.view.playButton.setText("Pausar")
            self.client.update_playlist_state(self.current_playlist, song_name, current_time,'reproduciendo')

        else:
            self.view.warningLabel.setText("")
            self.view.warningLabel.setVisible(False)
            
            self.current_song = selected_song.text()
            song_path = os.path.join(os.getcwd(), 'songs', song_name)

            if not os.path.exists(song_path):
                self.view.warningLabel.setText("Archivo de canción no encontrado")
                self.view.warningLabel.setVisible(True)
                return

            url = QUrl.fromLocalFile(song_path)
            content = QMediaContent(url)
            self.player.setMedia(content)
            self.player.play()
            self.view.playButton.setText("Pausar")
            # Enviar el estado actualizado de la canción al servidor
            self.client.update_playlist_state(self.current_playlist, song_name, current_time,'reproduciendo')
            #self.update_song_state(song_name, current_time,'reproduciendo')


    def update_song_state(self, song_name, position, state):
        print("pasando")
        print(song_name)
        print(self.current_song)
        print(position)
        print(state)
        # Actualizar el nombre de la canción actual
        if str(song_name) != str(self.current_song):
            self.current_song = song_name
        
        self.view.warningLabel.setText("SEGUNDO RECIBIDOS DE LA CANCION {}".format(position))
        self.view.warningLabel.setVisible(True)
        # Actualizar la posición del reproductor
        ##self.player.setPosition(position)
        
        # Actualizar el estado del reproductor
        print('actualiza cancion')
        if state == QMediaPlayer.PlayingState:
            self.player.play()
            self.view.playButton.setText("Pausar")
        elif state == QMediaPlayer.PausedState:
            self.player.pause()
            self.view.playButton.setText("Renaudar")
        
        # Actualizar la interfaz de usuario
        ##self.view.progressBar.setValue(position)
        #self.view.currentTimeLabel.setText(QTime(0, 0).addMSecs(position).toString("mm:ss"))

    #cliente se conecta llama a este metodo para obtener estado actual de cancion
    def request_initial_state(self):
        if self.current_playlist:
            state = self.client.get_playlist_state(self.current_playlist) #metodo al servidor
            if state:
                self.update_song_state(self, state['song'], state['position'], state['state'] )

    def stopSong(self):
        self.player.stop()
        self.view.playButton.setText("Reproducir")

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

    def getPosition(self):
        return self.view.progressBar.value()
        
    def connect_db(self):
        return db.connect('spotify.db')
    
    def insert_playlist(self, name):
        conn = self.connec1t_db()
        cursor = conn.cursor()
        
        cursor.execute("INSERT INTO playlist (name) VALUES (?)", (name,))
        
        conn.commit()
        conn.close()
        
    def insertSong(self, name, path, playlist):
        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO songs (name, path) VALUES (?, ?)", (name, path))
        song_id = cursor.lastrowid
        cursor.execute("SELECT playlist_id FROM playlist WHERE name = (?)", (playlist,))
        playlist_id = cursor.fetchone()
        cursor.execute("INSERT INTO songs_playlist (song_id, playlist_id, user_upload_id) VALUES (?, ?, ?)", (song_id, playlist_id[0], "1"))
        conn.commit()
        conn.close()
        
    def deleteSong(self, name, playlist):
        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT song_id FROM songs WHERE name = (?)", (name,))
        song_id = cursor.fetchone()
        cursor.execute("SELECT playlist_id FROM playlist WHERE name = (?)", (playlist,))
        playlist_id = cursor.fetchone()
        cursor.execute("DELETE FROM songs_playlist WHERE song_id = (?) AND playlist_id = (?)", (song_id[0], playlist_id[0]))
        conn.commit()
        conn.close()
        
    def get_playlists(self):
        conn = self.connect_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM playlist")
        playlists = cursor.fetchall()

        conn.close()
        return playlists
    
    def load_playlists(self):
        playlists = self.get_playlists()
        self.playlistList.clear()  # Asumiendo que tienes un QListWidget para mostrar las playlists
        for playlist in playlists:
            self.playlistList.addItem(playlist[1]) 
            
    def load_songs(self, playlist_name):
        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT playlist_id FROM playlist WHERE name = (?)", (playlist_name,))
        playlist_id = cursor.fetchone()
        cursor.execute("SELECT songs.name FROM songs_playlist INNER JOIN songs ON songs.song_id = songs_playlist.song_id WHERE songs_playlist.playlist_id = ?",  (playlist_id[0],))
        songs = cursor.fetchall()
        return songs
        