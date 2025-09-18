import sys
import openai  # Import the OpenAI library for Exaone API
import os
from PyQt5 import QtWidgets, uic

class MyApp(QtWidgets.QMainWindow):
    def __init__(self):
        super(MyApp, self).__init__()
        uic.loadUi(r"d:\WorklogApplication\worklog.ui", self)  # Load the .ui file

        # Connect the submit button to the callback function
        self.pushButton.clicked.connect(self.submitText)

        # Connect the close button to the close function
        self.closeButton.clicked.connect(self.closeApp)

        # Set the API key and base URL for Exaone
        openai.api_key = "flp_EUGAW1hNHAFgtE4dIgivHZZTCOg4iQiKrFRzwqdL0Uhd3"  # Replace with your actual API key
        openai.api_base = "https://api.friendli.ai/serverless/v1"

    def submitText(self):
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

                # Send the input data and file content to the Exaone agent
                response = openai.ChatCompletion.create(
                    model="LGAI-EXAONE/EXAONE-4.0.1-32B",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant to use the data, find the person(Noted on the MD file) and list up worklog and share the full report"},
                        {"role": "user", "content": f"Enter the following input site:\nInput1: {user_input1}\nInput2: {user_input2}\nFile Content:\n{md_content}"}
                    ],
                )

                # Handle the response from the Exaone agent
                message = response["choices"][0]["message"]["content"]
                print("Message from Exaone Agent:", message)

                # Notify the user of success and print the final success message
                QtWidgets.QMessageBox.information(self, "Submission Successful", f"Result from Exaone Agent: {message}")
                print("Final Success: The message has been processed successfully.")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"An error occurred: {e}")
        else:
            QtWidgets.QMessageBox.warning(self, "No .md File Found", "No valid .md file found in the WorklogApplication directory.")

    def closeApp(self):
        self.close()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
