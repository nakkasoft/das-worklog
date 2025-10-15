import sys
import os
import json
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QTextCursor, QMovie
import worklog_extractor
import llm_processor
import email_processor
import jira_uploader
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class LoadingAnimationThread(QThread):
    """Thread to control the loading animation."""
    start_signal = pyqtSignal()  # Signal to start the animation
    stop_signal = pyqtSignal()  # Signal to stop the animation

    def __init__(self, parent=None):
        super(LoadingAnimationThread, self).__init__(parent)
        self.running = True  # Control flag for the animation loop

    def run(self):
        """Run the loading animation."""
        self.start_signal.emit()  # Notify to start the animation
        while self.running:
            self.msleep(100)  # Keep the thread alive while the animation runs

    def stop(self):
        """Stop the loading animation."""
        self.running = False
        self.stop_signal.emit()  # Notify to stop the animation

class MyApp(QtWidgets.QMainWindow):

    def send_email(self, subject, to_emails, from_email, app_password, result):
        """Send an email notification with the worklog summary."""
        try:

            # Append result content to the email body
            body += "\n\n--- Processed Result ---\n\n"
            body += json.dumps(result, indent=4, ensure_ascii=False)

            # Create the email message
            message = MIMEMultipart()
            message['From'] = from_email
            message['To'] = ", ".join(to_emails)  # Join the list of emails for the email header
            message['Subject'] = subject
            message.attach(MIMEText(body, 'plain'))

            # Send the email
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(from_email, app_password)
            server.sendmail(from_email, to_emails, message.as_string())  # Pass the list of emails here
            server.quit()

            print("Email sent successfully!")
        except Exception as e:
            print(f"Failed to send email: {e}")
            
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
        
        # Add a QLabel to display the loading animation
        self.loading_label = QtWidgets.QLabel(self)
        self.loading_label.setAlignment(Qt.AlignCenter)

        # Dynamically calculate the center of lineEdit_5
        line_edit_geometry = self.lineEdit_5.geometry()
        line_edit_center_x = line_edit_geometry.x() + line_edit_geometry.width() // 2
        line_edit_center_y = line_edit_geometry.y() + line_edit_geometry.height() // 2

        # Set the geometry of the loading_label to be centered on lineEdit_5
        loading_label_width = 100  # Width of the loading animation
        loading_label_height = 100  # Height of the loading animation
        self.loading_label.setGeometry(
            line_edit_center_x - loading_label_width // 2,
            line_edit_center_y - loading_label_height // 2,
            loading_label_width,
            loading_label_height
        )
        self.loading_label.setStyleSheet("background-color: rgba(255, 255, 255, 200);")
        self.loading_label.setVisible(False)
        self.movie = QMovie("Loading.gif")  # Path to the loading GIF
        self.loading_label.setMovie(self.movie)

        self.loading_thread = None  # Placeholder for the loading animation thread


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

        # Disable the Generate button to block further clicks
        self.pushButton.setEnabled(False)

        # Clear the logs when Generate button is pressed
        self.clearLogs()

        # 설정 파일에서 값들 읽어오기
        if not self.config:
            QtWidgets.QMessageBox.critical(self, "오류", "설정이 로드되지 않았습니다.")
            self.pushButton.setEnabled(True)  # Re-enable the button if there's an error
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
            self.worker.start_animation_signal.connect(self.startLoadingAnimation)  # Start animation
            self.worker.stop_animation_signal.connect(self.stopLoadingAnimation)  # Stop animation
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
            self.pushButton.setEnabled(True)  # Re-enable the button if there's an error
            return

    def startLoadingAnimation(self):
        """Start the loading animation."""
        self.loading_label.setVisible(True)
        self.movie.start()

    def stopLoadingAnimation(self):
        """Stop the loading animation."""
        self.movie.stop()
        self.loading_label.setVisible(False)

    def clearLogs(self):
        """Clear the logs in lineEdit_5."""
        self.lineEdit_5.clear()

    def processFetchedData(self, data):
        """Process the fetched data and generate OpenAI completion."""
        self.updateLogs("주간 보고 작성중...")
        
        try:
            username = self.config["username"]
            worklog_directory = os.path.dirname(os.path.abspath(__file__))

            # AI 처리를 별도 스레드에서 실행
            self.ai_worker = AIWorker(self.config, username, data, worklog_directory)
            self.ai_worker.log_signal.connect(self.updateLogs)
            self.ai_worker.result_signal.connect(self.handleAIResult)
            self.ai_worker.error_signal.connect(self.handleAIError)
            self.ai_worker.start_animation_signal.connect(self.startLoadingAnimation)  # Start animation
            self.ai_worker.stop_animation_signal.connect(self.stopLoadingAnimation)  # Stop animation
            self.ai_worker.start()
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"An error occurred: {e}")
            self.pushButton.setEnabled(True) # Re-enable the button if there's an error

    def handleAIResult(self, result):
        """AI 처리 결과를 처리합니다 (메인 스레드에서 실행)."""
        
        # 처리된 Jira 이슈 링크 정보 표시
        if 'jira_issue_summaries' in result and result['jira_issue_summaries']:
            self.updateLogs("📋 처리된 Jira 이슈 링크:")
            for summary_item in result['jira_issue_summaries']:
                issue_key = summary_item.get('issue_key', 'Unknown')
                original_data = summary_item.get('original_data', {})
                issue_url = original_data.get('url', f"http://jira.lge.com/issue/browse/{issue_key}")
                issue_summary = original_data.get('summary', 'No Summary')
                self.updateLogs(f"  • [{issue_key}] {issue_summary}")
                self.updateLogs(f"    {issue_url}")
            self.updateLogs("")

        self.updateLogs("✅ 주간 보고서 생성 완료!")
        
        # Jira 서브태스크 URL 표시
        if 'subtask_url' in result:
            self.updateLogs("📋 생성된 Jira 서브태스크:")
            self.updateLogs(f"  🔗 {result['subtask_url']}")
        elif 'upload_error' in result:
            self.updateLogs(f"❌ Jira 업로드 실패: {result['upload_error']}")
        elif 'upload_info' in result:
            self.updateLogs(f"⚠️ {result['upload_info']}")
        else:
            self.updateLogs("📋 결과는 Jira 서브태스크에 업로드됩니다.")

        # Send the result via email
        try:
            subject = "Dashboard Automation Service Result"

            # Initialize the LLMProcessor instance
            processor = llm_processor.LLMProcessor(self.config)

            # Process the worklog with the MD file
            result = processor.process_worklog_with_md_file(
                username=self.config.get("username", "default_user"),
                worklog_data=self.worklog_data,
                directory_path=os.path.dirname(os.path.abspath(__file__))
            )

            # Email details
            username = self.config.get("username", "default_user")  # Get the username from the config
            to_emails = [f"{username}@lge.com"]  # Dynamically set the recipient email
            from_email = "xmlautomationbot@gmail.com"  # Replace with your Gmail address
            app_password = "aetq sbde ykho herp"  # Replace with your Gmail app password

            self.send_email(subject, to_emails, from_email, app_password, result)
        except Exception as e:
            print(f"⚠️ Failed to send email: {e}")

        # Re-enable the Generate button
        self.pushButton.setEnabled(True)

    def handleAIError(self, error_msg):
        """AI 처리 오류를 처리합니다 (메인 스레드에서 실행)."""
        self.updateLogs(f"처리 실패: {error_msg}")
        QtWidgets.QMessageBox.critical(
            self, "Processing Failed", f"워크로그 처리 중 오류가 발생했습니다:\n{error_msg}"
        )

        # Re-enable the Generate button
        self.pushButton.setEnabled(True)

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
        
        # user_config.json에서 제외할 이슈 목록 읽기
        excluded_issues = []
        try:
            with open("user_config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                master_jira = config.get("master_jira", "")
                if master_jira:
                    excluded_issues.append(master_jira)
                    print(f"📋 제외 대상 마스터 이슈: {master_jira}")
        except Exception as e:
            print(f"⚠️ user_config.json 읽기 실패: {e}")
        
        print("JIRA 데이터 수집 중...")
        jira_data = worklog_extractor.collect_jira_data(username, jira_token, excluded_issues)
        print(f"JIRA 데이터 수집 완료: {len(jira_data)}개 항목")
        
        print("Confluence 데이터 수집 중...")
        confluence_data = worklog_extractor.collect_confluence_data(username, confluence_token)
        print(f"Confluence 데이터 수집 완료: {len(confluence_data)}개 항목")
        
        print("Gerrit 데이터 수집 중...")
        gerrit_reviews, gerrit_comments = worklog_extractor.collect_gerrit_data(username, gerrit_tokens)
        print(f"Gerrit 데이터 수집 완료: 리뷰 {len(gerrit_reviews)}개, 댓글 {len(gerrit_comments)}개")
        
        # 이메일 데이터 수집 (LLM 처리 없음)
        print("이메일 데이터 수집 중...")
        try:
            email_proc = email_processor.create_email_processor()
            email_data_list = email_proc.collect_email_data()  # 변경: 데이터만 수집
            print(f"이메일 데이터 수집 완료: {len(email_data_list)}개")
        except Exception as e:
            print(f"이메일 데이터 수집 중 오류: {e}")
            email_data_list = []

        # 수집된 모든 데이터 구성
        all_worklog_data = {
            "jira_data": jira_data,
            "confluence_data": confluence_data,
            "gerrit_reviews": gerrit_reviews,
            "gerrit_comments": gerrit_comments,
            "email_data": email_data_list  # 변경: 원시 이메일 데이터
        }

        # 디버깅용 파일 저장
        print("디버깅용 데이터 파일 저장 중...")
        try:
            from datetime import datetime
            
            # log 폴더 생성
            log_dir = "./log"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                print(f"📁 로그 폴더 생성: {log_dir}")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_filename = os.path.join(log_dir, f"worklog_debug_{timestamp}.json")
            
            with open(debug_filename, 'w', encoding='utf-8') as f:
                json.dump(all_worklog_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 디버깅 데이터 저장 완료: {debug_filename}")
            print(f"   - JIRA: {len(jira_data)}개")
            print(f"   - Confluence: {len(confluence_data)}개")
            print(f"   - Gerrit Reviews: {len(gerrit_reviews)}개")
            print(f"   - Gerrit Comments: {len(gerrit_comments)}개")
            print(f"   - Email Data: {len(email_data_list)}개")
            
        except Exception as e:
            print(f"⚠️ 디버깅 파일 저장 중 오류: {e}")

        print("=== fetch_all_worklog_data 완료 ===")
        return all_worklog_data

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
                self.masterJiraInput.setText(config.get("master_jira", ""))  # Load master_jira

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
            "master_jira": self.masterJiraInput.text(),  # Save master_jira
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
    start_animation_signal = pyqtSignal()  # Signal to start the loading animation
    stop_animation_signal = pyqtSignal()  # Signal to stop the loading animation

    def __init__(self, username, jira_token, confluence_token, gerrit_tokens, parent=None):
        super(Worker, self).__init__(parent)
        self.username = username
        self.jira_token = jira_token
        self.confluence_token = confluence_token
        self.gerrit_tokens = gerrit_tokens
        
        # user_config.json에서 제외할 이슈 목록 읽기
        self.excluded_issues = []
        try:
            with open("user_config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                master_jira = config.get("master_jira", "")
                if master_jira:
                    self.excluded_issues.append(master_jira)
                    print(f"📋 제외 대상 마스터 이슈: {master_jira}")
        except Exception as e:
            print(f"⚠️ user_config.json 읽기 실패: {e}")

    def run(self):
        self.log_signal.emit(f"사용자: {self.username}")
        self.log_signal.emit("설정 파일에서 토큰들이 로드되었습니다.\n")

        try:
            # Fetch data
            self.start_animation_signal.emit()
            self.log_signal.emit("JIRA 데이터 수집 중...")
            jira_data = worklog_extractor.collect_jira_data(self.username, self.jira_token, self.excluded_issues)
            self.stop_animation_signal.emit()
            self.log_signal.emit(f"JIRA 데이터 수집 완료: {len(jira_data)}개 항목\n")

            self.start_animation_signal.emit()
            self.log_signal.emit("Confluence 데이터 수집 중...")
            confluence_data = worklog_extractor.collect_confluence_data(self.username, self.confluence_token)
            self.stop_animation_signal.emit()
            self.log_signal.emit(f"Confluence 데이터 수집 완료: {len(confluence_data)}개 항목\n")

            self.start_animation_signal.emit()
            self.log_signal.emit("Gerrit 데이터 수집 중...")
            gerrit_reviews, gerrit_comments = worklog_extractor.collect_gerrit_data(self.username, self.gerrit_tokens)
            self.stop_animation_signal.emit()
            self.log_signal.emit(f"Gerrit 데이터 수집 완료: 리뷰 {len(gerrit_reviews)}개, 댓글 {len(gerrit_comments)}개\n")
            
            # 이메일 데이터 수집 (LLM 처리 없음)
            self.start_animation_signal.emit()
            self.log_signal.emit("이메일 데이터 수집 중...")
            try:
                import email_processor
                email_proc = email_processor.create_email_processor()
                email_data_list = email_proc.collect_email_data()  # 변경: 데이터만 수집
                self.stop_animation_signal.emit()
                self.log_signal.emit(f"이메일 데이터 수집 완료: {len(email_data_list)}개\n")
            except Exception as e:
                self.stop_animation_signal.emit()
                self.log_signal.emit(f"이메일 데이터 수집 중 오류: {e}\n")
                email_data_list = []
            
            # 수집된 모든 데이터 구성
            all_worklog_data = {
                "jira_data": jira_data,
                "confluence_data": confluence_data,
                "gerrit_reviews": gerrit_reviews,
                "gerrit_comments": gerrit_comments,
                "email_data": email_data_list  # 변경: 원시 이메일 데이터
            }

            # 디버깅용 파일 저장
            self.log_signal.emit("디버깅용 데이터 파일 저장 중...")
            try:
                from datetime import datetime
                
                # log 폴더 생성
                log_dir = "./log"
                if not os.path.exists(log_dir):
                    os.makedirs(log_dir)
                    self.log_signal.emit(f"📁 로그 폴더 생성: {log_dir}")
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                debug_filename = os.path.join(log_dir, f"worklog_debug_{timestamp}.json")
                
                with open(debug_filename, 'w', encoding='utf-8') as f:
                    json.dump(all_worklog_data, f, ensure_ascii=False, indent=2)
                
                self.log_signal.emit(f"✅ 디버깅 데이터 저장 완료: {debug_filename}")
                self.log_signal.emit(f"   - JIRA: {len(jira_data)}개")
                self.log_signal.emit(f"   - Confluence: {len(confluence_data)}개")
                self.log_signal.emit(f"   - Gerrit Reviews: {len(gerrit_reviews)}개")
                self.log_signal.emit(f"   - Gerrit Comments: {len(gerrit_comments)}개")
                self.log_signal.emit(f"   - Email Data: {len(email_data_list)}개")
                
            except Exception as e:
                self.log_signal.emit(f"⚠️ 디버깅 파일 저장 중 오류: {e}")
            
            self.log_signal.emit("=== 모든 데이터 수집 완료 ===")

            # Emit the fetched data
            self.data_signal.emit(all_worklog_data)
        except Exception as e:
            self.stop_animation_signal.emit()
            self.log_signal.emit(f"오류 발생: {e}")

class AIWorker(QThread):
    log_signal = pyqtSignal(str)  # Signal to send log messages to the main thread
    result_signal = pyqtSignal(dict)  # Signal to send AI processing result
    error_signal = pyqtSignal(str)  # Signal to send error messages
    start_animation_signal = pyqtSignal()  # Signal to start the loading animation
    stop_animation_signal = pyqtSignal()  # Signal to stop the loading animation

    def __init__(self, config, username, worklog_data, directory_path, parent=None):
        super(AIWorker, self).__init__(parent)
        self.config = config
        self.username = username
        self.worklog_data = worklog_data
        self.directory_path = directory_path

    def run(self):
        try:
            self.start_animation_signal.emit()  # Start the loading animation
            self.log_signal.emit("AI 처리를 시작합니다...")  # Log the start of AI processing
            self.log_signal.emit("🔄 새로운 LLM 세션을 시작합니다...")
            
            # LLMProcessor 생성 및 새 세션 시작
            processor = llm_processor.LLMProcessor(self.config)
            processor.start_new_session()  # 새로운 대화 세션 시작
            
            # 이메일 데이터 LLM 요약 처리 (새로운 방식)
            self.log_signal.emit("📧 이메일 데이터를 LLM으로 요약 중...")
            try:
                if 'email_data' in self.worklog_data and self.worklog_data['email_data']:
                    email_summaries = processor.summarize_email_batch(self.worklog_data['email_data'])
                    self.log_signal.emit(f"📧 이메일 요약 완료: {len(email_summaries)}개")
                    
                    # 워크로그 데이터에 이메일 요약 추가
                    enhanced_worklog_data = self.worklog_data.copy()
                    enhanced_worklog_data['email_summaries'] = email_summaries
                    self.worklog_data = enhanced_worklog_data
                else:
                    self.log_signal.emit("📧 요약할 이메일 데이터가 없습니다.")
                    
            except Exception as e:
                self.log_signal.emit(f"⚠️ 이메일 요약 중 오류: {e}")
                # 이메일 요약 실패해도 계속 진행
            
            # Jira 이슈 개별 요약 처리
            self.log_signal.emit("🔍 Jira 이슈들을 개별적으로 LLM 요약 중...")
            jira_summaries = []
            
            # Jira 데이터에서 상세 이슈 정보 추출
            jira_issues = []
            for data_type, data_list in self.worklog_data.items():
                if data_type == 'jira_data' and isinstance(data_list, list):
                    for item in data_list:
                        if item.get('type') == 'detailed_issue':
                            jira_issues.append(item)
            
            if jira_issues:
                self.log_signal.emit(f"📋 총 {len(jira_issues)}개의 Jira 이슈를 개별 요약합니다...")
                
                for i, issue in enumerate(jira_issues, 1):
                    try:
                        issue_key = issue.get('issue_key', 'Unknown')
                        self.log_signal.emit(f"[{i}/{len(jira_issues)}] {issue_key} 요약 중...")
                        
                        # 개별 이슈 요약
                        summary_result = processor.summarize_jira_issue(issue)
                        
                        if summary_result['success']:
                            jira_summaries.append({
                                'issue_key': summary_result['issue_key'],
                                'summary': summary_result['summary'],
                                'original_data': issue
                            })
                            self.log_signal.emit(f"✅ {issue_key} 요약 완료")
                        else:
                            self.log_signal.emit(f"❌ {issue_key} 요약 실패: {summary_result['error']}")
                            
                    except Exception as e:
                        self.log_signal.emit(f"❌ {issue.get('issue_key', 'Unknown')} 요약 중 오류: {e}")
                
                # 요약된 Jira 이슈들을 워크로그 데이터에 추가
                enhanced_worklog_data = self.worklog_data.copy()
                enhanced_worklog_data['jira_issue_summaries'] = jira_summaries
                self.worklog_data = enhanced_worklog_data
                
                self.log_signal.emit(f"🎉 Jira 이슈 개별 요약 완료: {len(jira_summaries)}개 성공")
            else:
                self.log_signal.emit("📋 요약할 Jira 이슈가 없습니다.")
            
            # 워크로그 데이터와 MD 파일을 함께 처리
            result = processor.process_worklog_with_md_file(
                username=self.username,
                worklog_data=self.worklog_data,
                directory_path=self.directory_path
            )

            self.stop_animation_signal.emit()  # Stop the loading animation
            if result['success']:
                self.log_signal.emit("AI 처리 완료!")  # Log success
                
                # 결과에 Jira 이슈 요약 정보 추가
                if 'jira_issue_summaries' in self.worklog_data:
                    result['jira_issue_summaries'] = self.worklog_data['jira_issue_summaries']
                
                # Jira 업로드 기능 추가
                try:
                    self.log_signal.emit("📋 Jira에 결과물 업로드를 시작합니다...")
                    
                    # user_config.json에서 master_jira 읽기
                    with open("user_config.json", "r", encoding="utf-8") as f:
                        config = json.load(f)
                        master_jira = config.get("master_jira", "")
                        
                    if master_jira:
                        # JiraUploader 생성
                        uploader = jira_uploader.JiraUploader(config)
                        
                        # 결과물 업로드 - 실제 주간 보고서 내용 전달
                        upload_result = uploader.upload_worklog_result(
                            result.get('summary', '주간 보고서 내용')
                        )
                        
                        if upload_result['success']:
                            subtask_url = upload_result.get('url', 'URL 정보 없음')  # 'url' 키 사용
                            self.log_signal.emit(f"✅ Jira 업로드 완료: {subtask_url}")
                            # 결과에 서브태스크 URL 정보 추가
                            result['subtask_url'] = subtask_url
                        else:
                            error_msg = upload_result.get('error', '알 수 없는 오류')
                            self.log_signal.emit(f"❌ Jira 업로드 실패: {error_msg}")
                            result['upload_error'] = error_msg
                    else:
                        self.log_signal.emit("⚠️ user_config.json에 master_jira가 설정되지 않았습니다. Jira 업로드를 건너뜁니다.")
                        result['upload_info'] = "master_jira 설정이 필요합니다."
                        
                except Exception as e:
                    self.log_signal.emit(f"❌ Jira 업로드 중 오류: {e}")
                
                self.result_signal.emit(result)  # Emit the result
            else:
                error_msg = result['error'] or "알 수 없는 오류가 발생했습니다."
                self.error_signal.emit(error_msg)  # Emit the error message
                
        except Exception as e:
            self.stop_animation_signal.emit()  # Ensure the animation stops on error
            self.error_signal.emit(str(e))  # Emit the exception message

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())

