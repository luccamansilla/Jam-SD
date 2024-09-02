# view.py
from PyQt5.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QSlider, QListWidget, QLineEdit, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt

class MusicPlayerView(QMainWindow):
    def __init__(self):
        super().__init__()
        self.playlist = []
        
        self.setWindowTitle('Reproductor de música')
        self.setGeometry(100, 100, 600, 400)

        # Crear widgets
        self.songList = QListWidget()
        self.songList.setFixedWidth(300)
        
        # Playlists activas
        self.playlistWidget = QListWidget()
        self.playlistWidget.setWindowTitle("Playlists activas")  
        self.playlistWidget.setVisible(False)

        self.addSongButton = QPushButton('Agregar canción')
        self.seePlaylistsButton = QPushButton('Enlistar Playlists')
        self.removeSongButton = QPushButton('Borrar canción')

        self.playButton = QPushButton('Reproducir')
        self.stopButton = QPushButton('Parar')

        self.progressBar = QSlider(Qt.Horizontal)
        self.progressBar.setRange(0, 100)

        # Crear etiquetas de tiempo
        self.currentTimeLabel = QLabel('')
        self.durationTimeLabel = QLabel('')

        # Crear el layout para la barra de progreso y las etiquetas
        progressLayout = QHBoxLayout()
        progressLayout.addWidget(self.currentTimeLabel)
        progressLayout.addWidget(self.progressBar)
        progressLayout.addWidget(self.durationTimeLabel)

        # Crear el layout
        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.addSongButton)
        buttonLayout.addWidget(self.seePlaylistsButton)
        buttonLayout.addWidget(self.removeSongButton)

        controlLayout = QHBoxLayout()
        controlLayout.addWidget(self.playButton)
        controlLayout.addWidget(self.stopButton)

        # Mensaje de error cuando empieza canción sin seleccionar
        self.warningLabel = QLabel('')
        self.warningLabel.setStyleSheet("color: red")
        self.warningLabel.setVisible(False)

        layout = QVBoxLayout()
        layout.addWidget(QLabel('Playlist'))
        layout.addWidget(self.songList)
        layout.addLayout(buttonLayout)
        layout.addLayout(progressLayout)
        layout.addWidget(self.warningLabel)
        layout.addLayout(controlLayout)

        # Crear un widget central y establecer el layout
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
