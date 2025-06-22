import exchange
import ui
import strategy  # Make sure strategy module is imported
import time  # For timestamp handling

if __name__ == "__main__":
    app = ui.QApplication([])
    window = ui.MainWindow()
    window.show()
    app.exec()

