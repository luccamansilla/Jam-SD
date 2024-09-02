import os
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl, QTime
from PyQt5.QtWidgets import QFileDialog
import Pyro5.api 

class MusicPlayerController:
    def __init__(self, view):
        self.view = view
        self.player = QMediaPlayer()
        self.nameserver = Pyro5.core.locate_ns()
        self.uri= self.nameserver.lookup("luccaplaylist")         
        self.client = Pyro5.api.Proxy(self.uri)

        # Conectar señales y slots
        self.view.addSongButton.clicked.connect(self.addSong)
        self.view.seePlaylistsButton.clicked.connect(self.viewPlaylists)
        self.view.removeSongButton.clicked.connect(self.removeSong)
        self.view.playButton.clicked.connect(self.playSong)
        self.view.stopButton.clicked.connect(self.stopSong)
        self.player.positionChanged.connect(self.updateProgressBar)
        self.player.durationChanged.connect(self.updateProgressBarRange)
        self.view.progressBar.sliderReleased.connect(self.setSongPosition)

    def addSong(self):
        file_path, _ = QFileDialog.getOpenFileName(self.view, "Selecciona una canción", "", "Audio Files (*.mp3 *.wav *.ogg)")
        if file_path:
            self.view.songList.addItem(file_path)
            # Asumiendo que self.view.playlist se inicializa como una lista vacía en el constructor de MusicPlayerView
            self.view.playlist.append(file_path)
            self.sendSongToServer(file_path)
            print(self.view.playlist)
            
    def viewPlaylists(self):
        if self.view.playlistWidget.isVisible():
            self.view.playlistWidget.setVisible(False)
        else:
            self.updatePlaylists()
            self.view.playlistWidget.setVisible(True)  

    def updatePlaylists(self):
        playlists = self.nameserver.list()
        print(playlists)
        for i in playlists:
            self.view.playlistWidget.addItem(i)
            
            
    def sendSongToServer(self, file_path):
        with open(file_path, "rb") as file:
            data = file.read()
            filename = os.path.basename(file.name)
            try:
                self.client.transfer(data, filename)
                print(f"Archivo {filename} enviado al servidor")
            except Exception as e:
                print(f"Error al enviar la canción al servidor: {e}")
                
    def removeSong(self):
        selected_song = self.view.songList.currentItem()
        if selected_song:
            self.view.playlist.remove(selected_song.text())
            self.view.songList.takeItem(self.view.songList.row(selected_song))

    def playSong(self):
        selected_song = self.view.songList.currentItem()

        if not selected_song:
            self.view.warningLabel.setText("No seleccionó ninguna canción")
            self.view.warningLabel.setVisible(True)
            return

        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.view.playButton.setText("Renaudar")
        elif self.player.state() == QMediaPlayer.PausedState:
            self.player.play()
            self.view.playButton.setText("Pausar")
        else:
            self.view.warningLabel.setText("")
            self.view.warningLabel.setVisible(False)
            url = QUrl.fromLocalFile(selected_song.text())
            content = QMediaContent(url)
            self.player.setMedia(content)
            self.player.play()
            self.view.playButton.setText("Pausar")

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