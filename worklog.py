import sys
import openai  # Import the OpenAI library for Exaone API
import os
from PyQt5 import QtWidgets, uic
import worklog_extractor

class MyApp(QtWidgets.QMainWindow):
    def __init__(self):
        super(MyApp, self).__init__()
        uic.loadUi(r"worklog.ui", self)  # Load the .ui file

        # Connect the submit button to the callback function
        self.pushButton.clicked.connect(self.submitText)

        # Connect the close button to the close function
        self.closeButton.clicked.connect(self.closeApp)

        # Set the API key and base URL for Exaone
        openai.api_key = "flp_EUGAW1hNHAFgtE4dIgivHZZTCOg4iQiKrFRzwqdL0Uhd3"  # Replace with your actual API key
        openai.api_base = "https://api.friendli.ai/serverless/v1"

    def submitText(self):
        # Get the text from the input fields
        jira_token = self.lineEdit.text()
        confluence_token = self.lineEdit_2.text()
        gerrit_token_na = self.lineEdit_3.text()
        gerrit_token_eu = self.lineEdit_4.text()
        gerrit_token_as = self.lineEdit_6.text()
        username = self.lineEdit_5.text()


        rtn = self.fetch_all_worklog_data(username, jira_token, confluence_token, {"NA": gerrit_token_na, "EU": gerrit_token_eu, "AS": gerrit_token_as})
        print(rtn)

        # Define the directory where the .md file should exist
        worklog_directory = os.path.dirname(os.path.abspath(__file__))

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
                        {
                            "role": "system",
                            "content": (
                                "You are a helpful assistant. Use the provided data to find the person "
                                "(noted in the MD file), list their worklog, and share the full report."
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                f"USERNAME: {username}\n"
                                f"WORKLOG DATA:\n"
                                f"JIRA Activities: {len(rtn['jira_data'])} items\n"
                                f"JIRA Data: {rtn['jira_data']}\n\n"
                                f"CONFLUENCE Activities: {len(rtn['confluence_data'])} items\n"
                                f"CONFLUENCE Data: {rtn['confluence_data']}\n\n"
                                f"GERRIT Reviews: {len(rtn['gerrit_reviews'])} items\n"
                                f"GERRIT Reviews Data: {rtn['gerrit_reviews']}\n\n"
                                f"GERRIT Comments: {len(rtn['gerrit_comments'])} items\n"
                                f"GERRIT Comments Data: {rtn['gerrit_comments']}\n\n"
                                f"File Content:\n{md_content}"
                            ),
                        },
                    ],
                )

                # Handle the response from the Exaone agent
                #message = response["choices"][0]["message"]["content"]
                message = response.choices[0].message.content
                print("Message from Exaone Agent:", message)

                # Notify the user of success and print the final success message
                QtWidgets.QMessageBox.information(
                    self, "Submission Successful", f"Result from Exaone Agent: {message}"
                )
                print("Final Success: The message has been processed successfully.")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"An error occurred: {e}")
        else:
            QtWidgets.QMessageBox.warning(
                self, "No .md File Found", "No valid .md file found in the WorklogApplication directory."
            )

    def closeApp(self):
        self.close()

    def fetch_all_worklog_data(self, username, jira_token, confluence_token, gerrit_tokens):
        """
        worklog_extractor의 collect_jira_data, collect_confluence_data, collect_gerrit_data를 호출하여
        모든 데이터를 가져오는 함수
        Args:
            username (str): 사용자명
            jira_token (str): Jira API 토큰
            confluence_token (str): Confluence API 토큰
            gerrit_tokens (dict): Gerrit 서버별 토큰 {"NA": token, "EU": token, "AS": token}
        Returns:
            dict: 모든 시스템의 데이터
        """
        jira_data = worklog_extractor.collect_jira_data(username, jira_token)
        confluence_data = worklog_extractor.collect_confluence_data(username, confluence_token)
        gerrit_reviews, gerrit_comments = worklog_extractor.collect_gerrit_data(username, gerrit_tokens)
        return {
            "jira_data": jira_data,
            "confluence_data": confluence_data,
            "gerrit_reviews": gerrit_reviews,
            "gerrit_comments": gerrit_comments
        }


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
