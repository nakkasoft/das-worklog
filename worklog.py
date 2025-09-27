import sys
import os
import json
from PyQt5 import QtWidgets, uic
import worklog_extractor
import llm_processor
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QTextCursor  # Import QTextCursor from QtGui

class MyApp(QtWidgets.QMainWindow):
    def __init__(self):
        super(MyApp, self).__init__()
        uic.loadUi(r"worklog.ui", self)  # Load the .ui file

        # Connect the buttons to their respective functions
        self.pushButton.clicked.connect(self.submitText)  # Generate button
        self.closeButton.clicked.connect(self.closeApp)  # Close button
        self.pushButton_3.clicked.connect(self.openSettings)  # Setting button

        # 설정 파일 로드
        self.config = self.load_config()
        if not self.config:
            return  # 설정 로드 실패시 초기화 중단

    def load_config(self):
        """사용자 설정 파일을 로드합니다."""
        config_file = os.path.join(os.path.dirname(__file__), "user_config.json")
        
        if not os.path.exists(config_file):
            QtWidgets.QMessageBox.critical(
                self, "설정 파일 없음", 
                f"설정 파일을 찾을 수 없습니다: {config_file}\n"
                "user_config.json 파일을 생성하고 API 키들을 설정하세요."
            )
            return None
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # 필수 키들이 있는지 확인
            required_keys = [
                "username", "azure_openai_api_key", "azure_openai_endpoint",
                "azure_openai_api_version", "azure_openai_chat_deployment",
                "jira_token", "confluence_token", "gerrit_token_na",
                "gerrit_token_eu", "gerrit_token_as"
            ]
            
            missing_keys = [key for key in required_keys if not config.get(key) or config[key] == f"your_{key}_here"]
            
            if missing_keys:
                QtWidgets.QMessageBox.warning(
                    self, "설정 확인 필요", 
                    f"user_config.json에서 다음 설정값들을 확인하세요:\n{', '.join(missing_keys)}"
                )
            
            return config
            
        except json.JSONDecodeError as e:
            QtWidgets.QMessageBox.critical(
                self, "설정 파일 오류", 
                f"user_config.json 파일 형식이 올바르지 않습니다:\n{e}"
            )
            return None
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "파일 읽기 오류", 
                f"설정 파일을 읽는 중 오류가 발생했습니다:\n{e}"
            )
            return None
        
    def openSettings(self):
        """Open the settings dialog."""
        self.settings_dialog = SettingsDialog(self)
        self.settings_dialog.exec_()

    def submitText(self):
        # 설정 파일에서 값들 읽어오기
        if not self.config:
            QtWidgets.QMessageBox.critical(self, "오류", "설정이 로드되지 않았습니다.")
            return

        try:
            username = self.config["username"]
            jira_token = self.config["jira_token"]
            confluence_token = self.config["confluence_token"]
            gerrit_tokens = {
                "NA": self.config["gerrit_token_na"],
                "EU": self.config["gerrit_token_eu"],
                "AS": self.config["gerrit_token_as"]
            }

            # Create and start the worker thread
            self.worker = Worker(username, jira_token, confluence_token, gerrit_tokens)
            self.worker.log_signal.connect(self.updateLogs)  # Connect the log signal to updateLogs
            self.worker.data_signal.connect(self.processFetchedData)  # Connect the data signal to processFetchedData
            self.worker.start()

        except KeyError as e:
            QtWidgets.QMessageBox.critical(
                self, "설정 오류",
                f"user_config.json에 필요한 설정이 없습니다: {e}"
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "오류",
                f"작업 중 오류가 발생했습니다: {e}"
            )
            return


    def processFetchedData(self, data):
        """Process the fetched data and generate OpenAI completion."""
        try:
            username = self.config["username"]
            worklog_directory = os.path.dirname(os.path.abspath(__file__))

            # LLMProcessor 생성
            processor = llm_processor.LLMProcessor(self.config)
            
            # 워크로그 데이터와 MD 파일을 함께 처리
            result = processor.process_worklog_with_md_file(
                username=username,
                worklog_data=data,
                directory_path=worklog_directory
            )

            if result['success']:
                # MD 파일 내용이 있으면 로그에 출력
                if result['md_content']:
                    self.updateLogs("Contents of the .md file:")
                    self.updateLogs(result['md_content'])
                
                # GPT 응답 로그에 출력
                self.updateLogs("GPT 응답:")
                self.updateLogs(result['summary'])

                QtWidgets.QMessageBox.information(
                    self, "Submission Successful", f"Result: {result['summary']}"
                )
            else:
                # 처리 실패
                error_msg = result['error'] or "알 수 없는 오류가 발생했습니다."
                self.updateLogs(f"처리 실패: {error_msg}")
                QtWidgets.QMessageBox.critical(
                    self, "Processing Failed", f"워크로그 처리 중 오류가 발생했습니다:\n{error_msg}"
                )
                
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def updateLogs(self, message):
        """Update the logs in lineEdit_5."""
        self.lineEdit_5.append(message)
        self.lineEdit_5.moveCursor(QTextCursor.End)  # Auto-scroll to the end

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
        print(f"=== fetch_all_worklog_data 시작 ===")
        print(f"사용자: {username}")
        print("각 시스템에서 데이터 수집을 시작합니다...")
        
        print("JIRA 데이터 수집 중...")
        jira_data = worklog_extractor.collect_jira_data(username, jira_token)
        print(f"JIRA 데이터 수집 완료: {len(jira_data)}개 항목")
        
        print("Confluence 데이터 수집 중...")
        confluence_data = worklog_extractor.collect_confluence_data(username, confluence_token)
        print(f"Confluence 데이터 수집 완료: {len(confluence_data)}개 항목")
        
        print("Gerrit 데이터 수집 중...")
        gerrit_reviews, gerrit_comments = worklog_extractor.collect_gerrit_data(username, gerrit_tokens)
        print(f"Gerrit 데이터 수집 완료: 리뷰 {len(gerrit_reviews)}개, 댓글 {len(gerrit_comments)}개")
        
        print("=== fetch_all_worklog_data 완료 ===")
        return {
            "jira_data": jira_data,
            "confluence_data": confluence_data,
            "gerrit_reviews": gerrit_reviews,
            "gerrit_comments": gerrit_comments
        }

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        uic.loadUi(r"settings.ui", self)  # Load the settings UI file

        # Load existing settings into the input fields
        self.loadSettings()

        # Connect the buttons to their respective functions
        self.saveSettingsButton.clicked.connect(self.saveSettings)
        self.closeSettingsButton.clicked.connect(self.close)

    def loadSettings(self):
        """Load existing settings into the input fields."""
        config_file = os.path.join(os.path.dirname(__file__), "user_config.json")
        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.usernameInput.setText(config.get("username", ""))
                self.jiraTokenInput.setText(config.get("jira_token", ""))
                self.confluenceTokenInput.setText(config.get("confluence_token", ""))
                self.gerritTokenNaInput.setText(config.get("gerrit_token_na", ""))
                self.gerritTokenEuInput.setText(config.get("gerrit_token_eu", ""))
                self.gerritTokenAsInput.setText(config.get("gerrit_token_as", ""))

    def saveSettings(self):
        """Save the settings entered in the input fields."""
        config_file = os.path.join(os.path.dirname(__file__), "user_config.json")
        
        # Load the existing configuration to preserve Azure OpenAI fields
        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            config = {}

        # Update only the fields that the user can modify
        config.update({
            "username": self.usernameInput.text(),
            "jira_token": self.jiraTokenInput.text(),
            "confluence_token": self.confluenceTokenInput.text(),
            "gerrit_token_na": self.gerritTokenNaInput.text(),
            "gerrit_token_eu": self.gerritTokenEuInput.text(),
            "gerrit_token_as": self.gerritTokenAsInput.text(),
        })

        # Preserve Azure OpenAI fields if they already exist
        azure_fields = ["azure_openai_endpoint", "azure_openai_api_key", "azure_openai_api_version", "azure_openai_chat_deployment"]
        for field in azure_fields:
            if field not in config:
                config[field] = ""  # Add default value if missing

        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)

            # Reload the updated configuration
            self.parent().config = self.parent().load_config()

            QtWidgets.QMessageBox.information(self, "Success", "Settings saved successfully!")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")

class Worker(QThread):
    log_signal = pyqtSignal(str)  # Signal to send log messages to the main thread
    data_signal = pyqtSignal(dict)  # Signal to send fetched data to the main thread

    def __init__(self, username, jira_token, confluence_token, gerrit_tokens, parent=None):
        super(Worker, self).__init__(parent)
        self.username = username
        self.jira_token = jira_token
        self.confluence_token = confluence_token
        self.gerrit_tokens = gerrit_tokens

    def run(self):
        self.log_signal.emit(f"사용자: {self.username}")
        self.log_signal.emit("설정 파일에서 토큰들이 로드되었습니다.\n")

        try:
            # Fetch data
            self.log_signal.emit("JIRA 데이터 수집 중...")
            jira_data = worklog_extractor.collect_jira_data(self.username, self.jira_token)
            self.log_signal.emit(f"JIRA 데이터 수집 완료: {len(jira_data)}개 항목\n")

            self.log_signal.emit("Confluence 데이터 수집 중...")
            confluence_data = worklog_extractor.collect_confluence_data(self.username, self.confluence_token)
            self.log_signal.emit(f"Confluence 데이터 수집 완료: {len(confluence_data)}개 항목\n")

            self.log_signal.emit("Gerrit 데이터 수집 중...")
            gerrit_reviews, gerrit_comments = worklog_extractor.collect_gerrit_data(self.username, self.gerrit_tokens)
            self.log_signal.emit(f"Gerrit 데이터 수집 완료: 리뷰 {len(gerrit_reviews)}개, 댓글 {len(gerrit_comments)}개\n")

            self.log_signal.emit("=== 모든 데이터 수집 완료 ===")

            # Emit the fetched data
            self.data_signal.emit({
                "jira_data": jira_data,
                "confluence_data": confluence_data,
                "gerrit_reviews": gerrit_reviews,
                "gerrit_comments": gerrit_comments
            })
        except Exception as e:
            self.log_signal.emit(f"오류 발생: {e}")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
