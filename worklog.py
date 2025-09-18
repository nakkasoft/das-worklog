import sys
import os
import requests  # Import requests for API communication
from PyQt5 import QtWidgets, uic
from PyQt5.QtGui import QMovie
from PyQt5.QtCore import Qt

class MyApp(QtWidgets.QMainWindow):
    def __init__(self):
        super(MyApp, self).__init__()
        uic.loadUi(r"d:\WorklogApplication\worklog.ui", self)  # Load the .ui file

        # Connect the submit button to the callback function
        self.pushButton.clicked.connect(self.submitText)

        # Connect the close button to the close function
        self.closeButton.clicked.connect(self.closeApp)

        # Add a QLabel for the loading animation
        self.loadingLabel = QtWidgets.QLabel(self)
        self.loadingLabel.setGeometry(300, 300, 200, 200)  # Position and size of the animation
        self.loadingLabel.setStyleSheet("background: transparent;")
        self.loadingLabel.setAlignment(Qt.AlignCenter)  # Center the animation
        self.loadingLabel.hide()  # Initially hidden

        # Set up the loading animation
        self.loadingMovie = QMovie(r"d:\WorklogApplication\loading.gif")  # Path to the loading GIF
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
        # Start the loading animation
        self.startLoading()

        # Get the text from the input fields
        user_input1 = self.lineEdit.text()
        user_input2 = self.lineEdit_2.text()

        # Define the directory where the .md file should exist
        worklog_directory = r"d:\WorklogApplication"

        # Find the first valid .md file in the directory
        md_file = None
        for file in os.listdir(worklog_directory):
            if file.lower().endswith('.md'):
                md_file = os.path.join(worklog_directory, file)
                break

        # Check if a valid .md file was found
        if md_file:
            try:
                with open(md_file, 'r', encoding='utf-8') as file:
                    md_content = file.read()
                print("Contents of the .md file:")
                print(md_content)

                # Send the input data and file content to the Copilot agent
                copilot_url = "http://copilot-agent-url/api/process"  # Replace with the actual Copilot agent URL
                payload = {
                    "input1": user_input1,
                    "input2": user_input2,
                    "file_content": md_content
                }
                # Package the json and send the Json to the Copilot agent to conduct the worklog.
                response = requests.post(copilot_url, json=payload)

                # Handle the response from the Copilot agent
                if response.status_code == 200:
                    result = response.json()
                    message = result.get('message', 'Success')
                    print("Message from Copilot Agent:", message)

                    # Notify the user of success and print the final success message
                    QtWidgets.QMessageBox.information(self, "Submission Successful", f"Result from Copilot Agent: {message}")
                    print("Final Success: The message has been processed successfully.")
                else:
                    QtWidgets.QMessageBox.warning(self, "Submission Failed", f"Failed to connect to Copilot Agent. Status Code: {response.status_code}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"An error occurred: {e}")
        else:
            QtWidgets.QMessageBox.warning(self, "No .md File Found", "No valid .md file found in the WorklogApplication directory.")

        # Stop the loading animation
        self.stopLoading()

    def closeApp(self):
        self.close()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
