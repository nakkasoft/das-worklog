import sys
import openai  # Import the OpenAI library for Exaone API
import os
from PyQt5 import QtWidgets, uic
from PyQt5.QtGui import QMovie
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import worklog_extractor


class WorkerThread(QThread):
    resultReady = pyqtSignal(dict)  # Signal to send the result back to the main thread
    errorOccurred = pyqtSignal(str)  # Signal to send error messages

    def __init__(self, username, jira_token, confluence_token, gerrit_tokens):
        super().__init__()
        self.username = username
        self.jira_token = jira_token
        self.confluence_token = confluence_token
        self.gerrit_tokens = gerrit_tokens

    def run(self):
        try:
            # Fetch data from Jira, Confluence, and Gerrit
            jira_data = worklog_extractor.collect_jira_data(self.username, self.jira_token)
            confluence_data = worklog_extractor.collect_confluence_data(self.username, self.confluence_token)
            gerrit_reviews, gerrit_comments = worklog_extractor.collect_gerrit_data(self.username, self.gerrit_tokens)

            # Emit the result back to the main thread
            self.resultReady.emit({
                "jira_data": jira_data,
                "confluence_data": confluence_data,
                "gerrit_reviews": gerrit_reviews,
                "gerrit_comments": gerrit_comments,
            })
        except Exception as e:
            # Emit the error message back to the main thread
            self.errorOccurred.emit(str(e))


class MyApp(QtWidgets.QMainWindow):
    def __init__(self):
        super(MyApp, self).__init__()
        uic.loadUi(r"worklog.ui", self)  # Load the .ui file

        # Connect the submit button to the callback function
        self.pushButton.clicked.connect(self.submitText)

        # Connect the close button to the close function
        self.closeButton.clicked.connect(self.closeApp)

        # Set the API key and base URL for Exa
        openai.api_key = "flp_EUGAW1hNHAFgtE4dIgivHZZTCOg4iQiKrFRzwqdL0Uhd3"  # Replace with your actual API key
        openai.api_base = "https://api.friendli.ai/serverless/v1"

        # Add a QLabel for the loading animation
        self.loadingLabel = QtWidgets.QLabel(self)
        self.loadingLabel.setGeometry(300, 150, 200, 200)  # Position and size of the animation
        self.loadingLabel.setStyleSheet("background: transparent;")
        self.loadingLabel.setAlignment(Qt.AlignCenter)  # Center the animation
        self.loadingLabel.hide()  # Initially hidden

        # Set up the loading animation
        gif_path = os.path.join(os.path.dirname(__file__), "loading.gif")  # Dynamically get the path to loading.gif
        self.loadingMovie = QMovie(gif_path)  # Use the dynamically constructed path
        self.loadingLabel.setMovie(self.loadingMovie)

    def startLoading(self):
        """Start the loading animation."""
        self.loadingLabel.show()
        self.loadingMovie.start()

    def stopLoading(self):
        """Stop the loading animation."""
        self.loadingMovie.stop()
        self.loadingLabel.hide()

    def submitText(self):
        #Get the text from the input fields
        jira_token = self.lineEdit.text()
        confluence_token = self.lineEdit_2.text()
        gerrit_token_na = self.lineEdit_3.text()
        gerrit_token_eu = self.lineEdit_4.text()
        gerrit_token_as = self.lineEdit_5.text()
        username = self.lineEdit_6.text()

        # Start the loading animation
        self.startLoading()

        # Create a worker thread to fetch data
        self.worker = WorkerThread(
            username,
            jira_token,
            confluence_token,
            {"NA": gerrit_token_na, "EU": gerrit_token_eu, "AS": gerrit_token_as},
        )
        self.worker.resultReady.connect(self.handleResult)  # Connect the result signal
        self.worker.errorOccurred.connect(self.handleError)  # Connect the error signal
        self.worker.finished.connect(self.stopLoading)  # Stop loading when the thread finishes
        self.worker.start()  # Start the worker thread

    def handleResult(self, result):
        """Handle the result from the worker thread."""
        print("Worklog data fetched successfully:", result)
        QtWidgets.QMessageBox.information(
            self, "Success", "Worklog data fetched successfully!"
        )

    def handleError(self, error_message):
        """Handle errors from the worker thread."""
        QtWidgets.QMessageBox.critical(self, "Error", f"An error occurred: {error_message}")

    def closeApp(self):
        self.close()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
