import os
import json
from openai import AzureOpenAI


class LLMProcessor:
    """LLM을 이용한 워크로그 데이터 처리 클래스"""
    
    def __init__(self, config):
        """
        LLMProcessor 초기화
        
        Args:
            config (dict): Azure OpenAI 설정 정보
        """
        self.config = config
        self.client = AzureOpenAI(
            azure_endpoint=config["azure_openai_endpoint"],
            api_key=config["azure_openai_api_key"],
            api_version=config["azure_openai_api_version"],
        )
    
    def find_md_file(self, directory_path):
        """
        디렉토리에서 첫 번째 .md 파일을 찾기 (readme.md 제외)
        
        Args:
            directory_path (str): 검색할 디렉토리 경로
            
        Returns:
            str or None: 찾은 .md 파일의 전체 경로, 없으면 None
        """
        try:
            for file in os.listdir(directory_path):
                if file.lower().endswith('.md') and file.lower() != 'readme.md':
                    return os.path.join(directory_path, file)
            return None
        except Exception as e:
            raise Exception(f"디렉토리 검색 중 오류 발생: {e}")
    
    def read_md_file(self, md_file_path):
        """
        .md 파일 읽기
        
        Args:
            md_file_path (str): .md 파일 경로
            
        Returns:
            str: 파일 내용
        """
        try:
            with open(md_file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            raise Exception(f"파일 읽기 중 오류 발생: {e}")
    
    def generate_worklog_summary(self, username, worklog_data, md_content=None):
        """
        워크로그 데이터를 LLM으로 요약
        
        Args:
            username (str): 사용자명
            worklog_data (dict): 수집된 워크로그 데이터
            md_content (str, optional): 추가 참고용 마크다운 파일 내용
            
        Returns:
            str: LLM이 생성한 요약 내용
        """
        try:
            # 프롬프트 구성
            prompt_content = self._build_prompt(username, worklog_data, md_content)
            
            # Azure OpenAI API 호출
            completion = self.client.chat.completions.create(
                model=self.config["azure_openai_chat_deployment"],
                messages=[
                    {
                        "role": "user",
                        "content": prompt_content
                    }
                ],
                max_completion_tokens=10000,
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"LLM 요약 생성 중 오류 발생: {e}")
    
    def _build_prompt(self, username, worklog_data, md_content=None):
        """
        LLM 요청용 프롬프트 구성
        
        Args:
            username (str): 사용자명
            worklog_data (dict): 워크로그 데이터
            md_content (str, optional): 마크다운 파일 내용
            
        Returns:
            str: 구성된 프롬프트
        """
        prompt_parts = [
            "다음 내용을 요약해줘.\n",
            f"USERNAME: {username}\n",
            f"WORKLOG DATA:\n",
            f"JIRA Activities: {len(worklog_data['jira_data'])} items\n",
            f"JIRA Data: {worklog_data['jira_data']}\n\n",
            f"CONFLUENCE Activities: {len(worklog_data['confluence_data'])} items\n",
            f"CONFLUENCE Data: {worklog_data['confluence_data']}\n\n",
            f"GERRIT Reviews: {len(worklog_data['gerrit_reviews'])} items\n",
            f"GERRIT Reviews Data: {worklog_data['gerrit_reviews']}\n\n",
            f"GERRIT Comments: {len(worklog_data['gerrit_comments'])} items\n",
            f"GERRIT Comments Data: {worklog_data['gerrit_comments']}\n\n"
        ]
        
        if md_content:
            prompt_parts.append(f"File Content:\n{md_content}")
        
        return "".join(prompt_parts)
    
    def process_worklog_with_md_file(self, username, worklog_data, directory_path):
        """
        워크로그 데이터와 MD 파일을 함께 처리하여 요약 생성
        
        Args:
            username (str): 사용자명
            worklog_data (dict): 워크로그 데이터
            directory_path (str): MD 파일을 찾을 디렉토리 경로
            
        Returns:
            dict: 처리 결과 {'success': bool, 'summary': str, 'md_file': str, 'md_content': str, 'error': str}
        """
        result = {
            'success': False,
            'summary': None,
            'md_file': None,
            'md_content': None,
            'error': None
        }
        
        try:
            # MD 파일 찾기
            md_file = self.find_md_file(directory_path)
            
            if md_file:
                # MD 파일 읽기
                md_content = self.read_md_file(md_file)
                result['md_file'] = md_file
                result['md_content'] = md_content
                
                # LLM으로 요약 생성
                summary = self.generate_worklog_summary(username, worklog_data, md_content)
                result['summary'] = summary
                result['success'] = True
                
            else:
                # MD 파일이 없어도 워크로그만으로 요약 생성
                summary = self.generate_worklog_summary(username, worklog_data)
                result['summary'] = summary
                result['success'] = True
                
        except Exception as e:
            result['error'] = str(e)
            
        return result


def create_llm_processor(config_file_path):
    """
    설정 파일에서 LLMProcessor 인스턴스 생성
    
    Args:
        config_file_path (str): user_config.json 파일 경로
        
    Returns:
        LLMProcessor: 초기화된 LLMProcessor 인스턴스
        
    Raises:
        Exception: 설정 파일 오류 또는 LLMProcessor 생성 실패
    """
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 필수 키 확인
        required_keys = [
            "azure_openai_endpoint",
            "azure_openai_api_key", 
            "azure_openai_api_version",
            "azure_openai_chat_deployment"
        ]
        
        missing_keys = [key for key in required_keys if not config.get(key)]
        if missing_keys:
            raise Exception(f"설정 파일에 필수 Azure OpenAI 설정이 누락되었습니다: {missing_keys}")
        
        return LLMProcessor(config)
        
    except FileNotFoundError:
        raise Exception(f"설정 파일을 찾을 수 없습니다: {config_file_path}")
    except json.JSONDecodeError as e:
        raise Exception(f"설정 파일 형식이 올바르지 않습니다: {e}")
    except Exception as e:
        raise Exception(f"LLMProcessor 생성 중 오류 발생: {e}")


# 사용 예제
if __name__ == "__main__":
    # 예제 사용법
    try:
        # 설정 파일에서 LLMProcessor 생성
        processor = create_llm_processor("user_config.json")
        
        # 예제 워크로그 데이터
        sample_data = {
            'jira_data': [],
            'confluence_data': [],
            'gerrit_reviews': [],
            'gerrit_comments': []
        }
        
        # 현재 디렉토리에서 MD 파일과 함께 처리
        result = processor.process_worklog_with_md_file(
            username="test_user",
            worklog_data=sample_data,
            directory_path="./templates"
        )
        
        if result['success']:
            print("✓ 처리 성공!")
            if result['md_file']:
                print(f"  사용된 MD 파일: {result['md_file']}")
            print(f"  요약 길이: {len(result['summary'])}자")
        else:
            print(f"✗ 처리 실패: {result['error']}")
            
    except Exception as e:
        print(f"오류: {e}")
