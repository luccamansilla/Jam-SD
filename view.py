from PyQt5.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QSlider, QListWidget, QHBoxLayout, QLabel, QComboBox
from PyQt5.QtCore import Qt

class MusicPlayerView(QMainWindow):
    def __init__(self):
        super().__init__()
        self.playlist = []
        self.current_playlist = None  # Añadir una variable para la playlist actual
        
        self.setWindowTitle('Reproductor de música')
        self.setGeometry(100, 100, 600, 400)

        # Crear widgets
        self.songList = QListWidget()
        self.songList.setFixedWidth(300)
        self.songList.setSelectionMode(QListWidget.SingleSelection)  # Asegúrate de que se pueda seleccionar una canción

        self.playlistWidget = QListWidget()
        self.playlistWidget.setWindowTitle("Playlists activas")  
        self.playlistWidget.setVisible(False)

        self.playlistComboBox = QComboBox()
        self.playlistComboBox.setVisible(True)

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

        # Crear la etiqueta para mostrar el nombre de la canción
        self.songNameLabel = QLabel('')
        self.songNameLabel.setAlignment(Qt.AlignCenter)

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

        playlistLayout = QHBoxLayout()
        playlistLayout.addWidget(self.playlistComboBox)

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
        layout.addWidget(self.songNameLabel)  # Agrega la etiqueta para el nombre de la canción
        layout.addLayout(controlLayout)
        layout.addLayout(playlistLayout)

        # Crear un widget central y establecer el layout
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
