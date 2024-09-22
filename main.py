# main.py
import sys
from PyQt5.QtWidgets import QApplication
from view import MusicPlayerView
from controller import MusicPlayerController

def main():
    app = QApplication(sys.argv)

    # Crear la vista
    view = MusicPlayerView()

    # Crear el controlador y pasarle la vista
    controller = MusicPlayerController(view)

    view.controller = controller

    # Mostrar la vista
    view.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

