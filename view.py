# view.py
from PyQt5.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QSlider, QListWidget, QDialog, QHBoxLayout, QLabel, QComboBox,QLineEdit
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
        # self.playlistWidget = QListWidget()
        # self.playlistWidget.setWindowTitle("Playlists activas")  
        # self.playlistWidget.setVisible(False)
        # self.confirmPlaylistButton = QPushButton("Confirmar selección")
        # self.confirmPlaylistButton.setVisible(False)
        
        
        self.addSongButton = QPushButton('Agregar canción')
        self.seePlaylistsButton = QPushButton('Playlist compartidas')
        self.removeSongButton = QPushButton('Borrar canción')
        self.sharePlaylistButton = QPushButton('Hacer colaborativa')


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
        buttonLayout.addWidget(self.sharePlaylistButton)
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
        
    def closeEvent(self, event):
        # Llama al método en el controlador para manejar el cierre
        if hasattr(self.controller, 'close_app'):
            self.controller.close_app()  # Llama al método de cierre en el controlador
        event.accept()  # Acepta el evento de cierre

# Nueva clase para el diálogo de ingreso de usuario
class UserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ingresa tu nombre de usuario")
        
        # Crear un campo de texto para el nombre de usuario
        self.nameInput = QLineEdit(self)
        self.nameInput.setPlaceholderText("Tu nombre")

        # Botón para confirmar el nombre de usuario
        self.confirmButton = QPushButton("Aceptar", self)
        self.confirmButton.clicked.connect(self.accept)

        # Layout para el diálogo
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Por favor, ingresa tu nombre de usuario:"))
        layout.addWidget(self.nameInput)
        layout.addWidget(self.confirmButton)
        self.setLayout(layout)
    
    def getUserName(self):
        return self.nameInput.text()
        
class PlaylistDialog(QDialog):
    def __init__(self, playlists, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Playlist compartidas actuales")

        # Almacena las playlists
        self.playlists = playlists

        # Crear una lista de playlists
        self.playlistListWidget = QListWidget(self)
        for playlist in self.playlists:
            self.playlistListWidget.addItem(playlist)

        # Botones para confirmar o cerrar
        self.confirmButton = QPushButton("Aceptar", self)
        self.confirmButton.clicked.connect(self.accept)
        
        self.cancelButton = QPushButton("Cerrar", self)
        self.cancelButton.clicked.connect(self.reject)

        # Layout para el diálogo
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Selecciona una playlist compartida:"))
        layout.addWidget(self.playlistListWidget)
        layout.addWidget(self.confirmButton)
        layout.addWidget(self.cancelButton)
        self.setLayout(layout)

    def getSelectedPlaylist(self):
        selected_item = self.playlistListWidget.currentItem()
        if selected_item:
            return selected_item.text()
        return None