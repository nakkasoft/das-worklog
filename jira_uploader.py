import os
import json
import requests
from datetime import datetime
import re  # 추가: Markdown 변환에 사용


class JiraUploader:
    """Jira에 서브태스크 생성 및 업로드를 처리하는 클래스"""
    
    def __init__(self, config):
        """
        JiraUploader 초기화
        
        Args:
            config (dict): 사용자 설정 정보
        """
        self.config = config
        self.base_url = "http://jira.lge.com/issue"
        self.username = config["username"]
        self.token = config["jira_token"]
        self.master_jira = config.get("master_jira", "")
        
        # 마스터 Jira URL에서 이슈 키 추출
        if self.master_jira:
            self.master_issue_key = self.extract_issue_key(self.master_jira)
        else:
            self.master_issue_key = None
            
        print(f"🎯 마스터 Jira: {self.master_issue_key}")
    
    def extract_issue_key(self, jira_url):
        """
        Jira URL에서 이슈 키 추출
        
        Args:
            jira_url (str): Jira 이슈 URL
            
        Returns:
            str: 이슈 키 (예: CLUSTWORK-16153)
        """
        try:
            # URL에서 이슈 키 추출 (마지막 / 뒤의 부분)
            return jira_url.split('/')[-1]
        except:
            return None
    
    def get_master_and_subtasks(self):
        """
        마스터 이슈와 그 서브태스크들의 키 목록을 가져오기
        
        Returns:
            list: 제외할 이슈 키 목록
        """
        if not self.master_issue_key:
            return []
        
        excluded_issues = [self.master_issue_key]
        
        try:
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.token}"
            }
            
            # 마스터 이슈 정보 가져오기
            url = f"{self.base_url}/rest/api/2/issue/{self.master_issue_key}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            issue_data = response.json()
            
            # 서브태스크 목록 가져오기
            subtasks = issue_data.get("fields", {}).get("subtasks", [])
            for subtask in subtasks:
                excluded_issues.append(subtask["key"])
            
            print(f"📋 분석 제외 이슈: {excluded_issues}")
            return excluded_issues
            
        except Exception as e:
            print(f"⚠️ 마스터 이슈 정보 가져오기 실패: {e}")
            return [self.master_issue_key]  # 최소한 마스터는 제외
    
    def create_subtask(self, summary, description, attachment_content=None):
        """
        마스터 이슈에 서브태스크 생성
        
        Args:
            summary (str): 서브태스크 제목
            description (str): 서브태스크 설명
            attachment_content (str, optional): 첨부할 내용
            
        Returns:
            dict: 생성 결과 {'success': bool, 'issue_key': str, 'url': str, 'error': str}
        """
        if not self.master_issue_key:
            return {
                'success': False,
                'issue_key': None,
                'url': None,
                'error': 'master_jira가 설정되지 않았습니다.'
            }
        
        try:
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}"
            }
            
            # 마스터 이슈 정보 가져오기 (프로젝트 정보 필요)
            master_url = f"{self.base_url}/rest/api/2/issue/{self.master_issue_key}"
            master_response = requests.get(master_url, headers=headers)
            master_response.raise_for_status()
            master_data = master_response.json()
            
            project_key = master_data["fields"]["project"]["key"]
            
            # 서브태스크 생성 데이터
            subtask_data = {
                "fields": {
                    "project": {
                        "key": project_key
                    },
                    "parent": {
                        "key": self.master_issue_key
                    },
                    "summary": summary,
                    "description": description,
                    "issuetype": {
                        "name": "Sub-task"
                    },
                    "assignee": {
                        "name": self.username
                    }
                }
            }
            
            # 서브태스크 생성
            create_url = f"{self.base_url}/rest/api/2/issue"
            response = requests.post(create_url, headers=headers, json=subtask_data)
            response.raise_for_status()
            
            result = response.json()
            issue_key = result["key"]
            issue_url = f"{self.base_url}/browse/{issue_key}"
            
            print(f"✅ Jira 서브태스크 생성 완료: {issue_key}")
            
            # 첨부파일이 있으면 추가
            if attachment_content:
                self.add_attachment(issue_key, attachment_content)
            
            return {
                'success': True,
                'issue_key': issue_key,
                'url': issue_url,
                'error': None
            }
            
        except Exception as e:
            error_msg = f"서브태스크 생성 실패: {e}"
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'issue_key': None,
                'url': None,
                'error': error_msg
            }
    
    def add_attachment(self, issue_key, content, filename="worklog_summary.md"):
        """
        이슈에 첨부파일 추가
        
        Args:
            issue_key (str): 이슈 키
            content (str): 첨부할 내용
            filename (str): 파일명
        """
        try:
            # 임시 파일 생성
            log_dir = "./log"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            temp_file = os.path.join(log_dir, filename)
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Jira에 첨부파일 업로드
            headers = {
                "Authorization": f"Bearer {self.token}",
                "X-Atlassian-Token": "no-check"
            }
            
            url = f"{self.base_url}/rest/api/2/issue/{issue_key}/attachments"
            
            with open(temp_file, 'rb') as f:
                files = {'file': (filename, f, 'text/markdown')}
                response = requests.post(url, headers=headers, files=files)
                response.raise_for_status()
            
            print(f"📎 첨부파일 업로드 완료: {filename}")
            
            # 임시 파일 삭제
            os.remove(temp_file)
            
        except Exception as e:
            print(f"⚠️ 첨부파일 업로드 실패: {e}")
    
    def markdown_to_jira(self, md: str) -> str:
        """Markdown을 Jira Wiki Markup(Wiki 스타일)으로 단순 변환.
        고급 Markdown (복잡한 nested list, 혼합 표 등)은 최소 규칙만 처리.
        원본 보존이 필요하면 별도로 첨부하고, description에는 변환본 사용.
        """
        lines = md.splitlines()
        out = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # 코드 블록 처리 ```lang ... ``` -> {code:lang} ... {code}
            if line.strip().startswith("```"):
                lang = line.strip()[3:].strip()
                out.append(f"{{code:{lang}}}" if lang else "{code}")
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    out.append(lines[i])
                    i += 1
                if i < len(lines):  # closing ```
                    out.append("{code}")
                    i += 1
                continue
            # 표 블록 탐지: '|' 로 시작 (헤더 줄 이후 구분선 포함)
            if line.strip().startswith('|') and '|' in line.strip()[1:]:
                table_block = []
                while i < len(lines) and lines[i].strip().startswith('|'):
                    table_block.append(lines[i])
                    i += 1
                # 파싱
                if table_block:
                    # 헤더 줄
                    header = table_block[0]
                    header_cells = [c.strip() for c in header.strip().strip('|').split('|')]
                    out.append('|| ' + ' || '.join(header_cells) + ' ||')
                    # 나머지 (두번째 줄이 --- 구분선이면 skip)
                    body_rows = table_block[1:]
                    if body_rows and re.match(r'^\|\s*[-: ]+\|', body_rows[0]):
                        body_rows = body_rows[1:]
                    for row in body_rows:
                        cells = [c.strip() for c in row.strip().strip('|').split('|')]
                        out.append('| ' + ' | '.join(cells) + ' |')
                continue
            # 헤더 변환 ###### -> h6.
            m = re.match(r'^(#{1,6})\s+(.*)$', line)
            if m:
                level = len(m.group(1))
                text = m.group(2).strip()
                out.append(f"h{level}. {text}")
                i += 1
                continue
            # 수평선 --- -> ----
            if re.match(r'^\s*---+\s*$', line):
                out.append('----')
                i += 1
                continue
            # 순서 없는 리스트 - / * -> *
            if re.match(r'^\s*[-*]\s+.+', line):
                out.append(re.sub(r'^\s*[-*]\s+', lambda m: ' ' * (len(m.group(0)) - len(m.group(0).lstrip())) + '* ', line))
                i += 1
                continue
            # 순서 있는 리스트 1. -> #
            if re.match(r'^\s*\d+\.\s+.+', line):
                out.append(re.sub(r'^\s*\d+\.\s+', '# ', line))
                i += 1
                continue
            # 굵게 **text** -> *text*
            line = re.sub(r'\*\*(.+?)\*\*', r'*\1*', line)
            out.append(line)
            i += 1
        return '\n'.join(out)

    def upload_worklog_result(self, summary_content):
        """
        워크로그 결과를 Jira 서브태스크로 업로드
        
        Args:
            summary_content (str): 주간 보고서 내용(Markdown 원본)
            
        Returns:
            dict: 업로드 결과
        """
        try:
            # 현재 날짜로 제목 생성
            today = datetime.now().strftime("%Y-%m-%d")
            summary = f"주간 보고서 - {today} ({self.username})"
            
            # Markdown -> Jira 변환 (description 전용)
            jira_body = self.markdown_to_jira(summary_content)
            description = (f"자동 생성된 주간 보고서입니다.\n\n"\
                           f"작성자: {self.username}\n"\
                           f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"\
                           f"{jira_body}")
            
            # 서브태스크 생성
            result = self.create_subtask(
                summary=summary,
                description=description,
                attachment_content=summary_content  # 첨부에는 원본 Markdown 유지
            )
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'issue_key': None,
                'url': None,
                'error': f"워크로그 업로드 실패: {e}"
            }


def create_jira_uploader(config_file_path="user_config.json"):
    """
    설정 파일에서 JiraUploader 인스턴스 생성
    
    Args:
        config_file_path (str): user_config.json 파일 경로
        
    Returns:
        JiraUploader: 초기화된 JiraUploader 인스턴스
    """
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        return JiraUploader(config)
        
    except Exception as e:
        raise Exception(f"JiraUploader 생성 중 오류 발생: {e}")


# 사용 예제
if __name__ == "__main__":
    try:
        uploader = create_jira_uploader()
        
        # 테스트용 주간 보고서 내용
        test_content = """
# 주간 보고서

## 이번 주 주요 성과
- JIRA 이슈 5개 해결
- 코드 리뷰 3건 완료
- 이메일 업무 처리

## 다음 주 계획
- 새로운 기능 개발
- 테스트 케이스 작성
"""
        
        # 서브태스크 생성 및 업로드
        result = uploader.upload_worklog_result(test_content)
        
        if result['success']:
            print(f"✅ 업로드 성공: {result['url']}")
        else:
            print(f"❌ 업로드 실패: {result['error']}")
            
    except Exception as e:
        print(f"오류: {e}")
