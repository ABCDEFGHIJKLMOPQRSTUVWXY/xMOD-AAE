import sys
import os
import pygame
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from ui.main_window import MainWindow


def main():
    os.environ["QT_QPA_PLATFORM"] = "windows:darkmode=0"
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

    pygame.init()
    pygame.mixer.init()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    try:
        sys.exit(app.exec())
    finally:
        pygame.mixer.quit()
        pygame.quit()


if __name__ == "__main__":
    main()
