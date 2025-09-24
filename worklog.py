import sys
# Exaone openai 라이브러리 제거 후 Azure OpenAI 클라이언트 사용
from openai import AzureOpenAI
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

        # Azure OpenAI 설정 (환경변수 없으면 기본값 사용)
        self.azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "https://25-fianl-hac.openai.azure.com/")
        self.azure_api_key = os.environ.get("AZURE_OPENAI_API_KEY", "<실제 api key>")  # 실제 키는 환경변수로
        self.azure_api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
        self.chat_deployment = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-5")

        self.client = AzureOpenAI(
            azure_endpoint=self.azure_endpoint,
            api_key=self.azure_api_key,
            api_version=self.azure_api_version,
        )

    def submitText(self):
        # Get the text from the input fields (현재는 하드코딩)
        # jira_token = self.lineEdit.text()
        # confluence_token = self.lineEdit_2.text()
        # gerrit_token_na = self.lineEdit_3.text()
        # gerrit_token_eu = self.lineEdit_4.text()
        # gerrit_token_as = self.lineEdit_6.text()
        # username = self.lineEdit_5.text()

        jira_token = "MTA4MzUzNTI1NTAyOnXnU99C/Zu49GfWhXycDagAAndf"
        confluence_token = "NjAxODE5MzExMTEwOkDiAFWAKKzbeQp3/AqJmWTUh3vl"
        gerrit_token_na = "yZwbBlrmsaDz6JOsZWuvZdU2If5nZKpMS3s+3IvC4w"
        gerrit_token_eu = "rW9mDWeDyX7tDlkV79RuMxn5J0wrmkdeG+ur9Sa5qg"
        gerrit_token_as = "rvJyHHHHdeHCynvi3fzuHwI1SOUwFstQBGfT6E1v9Q"
        username = "sangyeob.na"

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

                # Azure OpenAI(Chat Completions) 호출
                completion = self.client.chat.completions.create(
                    model=self.chat_deployment,
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                "다음 내용을 요약해줘.\n"
                                f"USERNAME: {username}\n"
                                f"WORKLOG DATA:\n"
                                f"JIRA Activities: {rtn['jira_data']} items\n"
                                f"JIRA Data: {rtn['jira_data']}\n\n"
                                f"CONFLUENCE Activities: {rtn['confluence_data']} items\n"
                                f"CONFLUENCE Data: {rtn['confluence_data']}\n\n"
                                f"GERRIT Reviews: {rtn['gerrit_reviews']} items\n"
                                f"GERRIT Reviews Data: {rtn['gerrit_reviews']}\n\n"
                                f"GERRIT Comments: {rtn['gerrit_comments']} items\n"
                                f"GERRIT Comments Data: {rtn['gerrit_comments']}\n\n"
                                f"File Content:\n{md_content}"
                            ),
                        },
                    ],
                    max_completion_tokens=10000,
                )

                message = completion.choices[0].message.content
                print("GPT 응답:", message)

                QtWidgets.QMessageBox.information(
                    self, "Submission Successful", f"Result: {message}"
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
