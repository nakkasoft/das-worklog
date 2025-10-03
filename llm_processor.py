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
        디렉토리에서 주간 보고 템플릿 .md 파일을 찾기
        
        Args:
            directory_path (str): 검색할 디렉토리 경로
            
        Returns:
            str or None: 찾은 .md 파일의 전체 경로, 없으면 None
        """
        try:
            # 우선순위 파일들 (주간 보고 관련)
            priority_files = [
                'weekly_report_template.md',
                'weekly_report.md',
                'template.md'
            ]
            
            # templates 디렉토리도 확인
            templates_dir = os.path.join(directory_path, 'templates')
            search_dirs = [directory_path]
            if os.path.exists(templates_dir):
                search_dirs.append(templates_dir)
            
            # 우선순위 파일부터 검색
            for search_dir in search_dirs:
                for priority_file in priority_files:
                    file_path = os.path.join(search_dir, priority_file)
                    if os.path.exists(file_path):
                        print(f"✅ 주간 보고 템플릿 발견: {file_path}")
                        return file_path
            
            # 우선순위 파일이 없으면 일반 .md 파일 검색 (readme.md 제외)
            for search_dir in search_dirs:
                if os.path.exists(search_dir):
                    for file in os.listdir(search_dir):
                        if (file.lower().endswith('.md') and 
                            file.lower() not in ['readme.md', 'changelog.md', 'license.md']):
                            file_path = os.path.join(search_dir, file)
                            print(f"📄 MD 파일 발견: {file_path}")
                            return file_path
            
            print("⚠️ 주간 보고 템플릿 MD 파일을 찾을 수 없습니다.")
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
            print(f"📖 MD 파일 읽는 중: {md_file_path}")
            
            if not os.path.exists(md_file_path):
                raise Exception(f"파일이 존재하지 않습니다: {md_file_path}")
            
            with open(md_file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            if not content.strip():
                print("⚠️ MD 파일이 비어있습니다.")
                return ""
            
            print(f"✅ MD 파일 읽기 완료 ({len(content)} 문자)")
            return content
            
        except UnicodeDecodeError:
            # UTF-8로 읽기 실패시 다른 인코딩 시도
            try:
                with open(md_file_path, 'r', encoding='cp949') as file:
                    content = file.read()
                print(f"✅ MD 파일 읽기 완료 (CP949 인코딩, {len(content)} 문자)")
                return content
            except Exception as e:
                raise Exception(f"파일 읽기 중 인코딩 오류: {e}")
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
        # 기본 시스템 프롬프트
        system_prompt = """당신은 주간 보고를 아주 잘 정리하는 주간 보고 마스터입니다. 
        다음 내용을 바탕으로 주간 보고를 작성해 주세요.

        주간 보고 작성 가이드라인:
        1. Issue 현황은 내가 수정한 Issue만 포함됩니다. 내가 Resolve 처리를 했거나, 나에게 Assign된 Issue들만 Count 해주세요.
        2. 주요 처리 Issue나 주요 잔여 Issue는 Issue의 제목을 넣어 주고, Issue의 내용을 간략하게 설명해 주세요. 1~2줄 정도가 좋을 것 같습니다.
        3. 내가 해당 Issue에 대해서 수행한 작업들을 Comment Base로 작성해 주세요.
        4. 기술 관련 Issue라면 어느 정도 기술관련 내용이 들어가면 좋을 것 같습니다.

        """
        
        # MD 파일 양식이 있으면 추가
        if md_content:
            system_prompt += f"""
            === 주간 보고 양식 (다음 양식에 맞게 작성해주세요) ===
            {md_content}

            === 양식 끝 ===

            위 양식에 맞춰서 아래 워크로그 데이터를 정리해서 주간 보고서를 작성해주세요.
            """
        
        # 워크로그 데이터 추가
        prompt_parts = [
            system_prompt,
            f"\n=== 워크로그 데이터 ===\n",
            f"사용자: {username}\n\n",
            f"📋 JIRA 활동 데이터 ({len(worklog_data['jira_data'])}개 항목):\n",
            f"{json.dumps(worklog_data['jira_data'], ensure_ascii=False, indent=2)}\n\n",
            f"📝 CONFLUENCE 활동 데이터 ({len(worklog_data['confluence_data'])}개 항목):\n",
            f"{json.dumps(worklog_data['confluence_data'], ensure_ascii=False, indent=2)}\n\n",
            f"🔍 GERRIT 리뷰 데이터 ({len(worklog_data['gerrit_reviews'])}개 항목):\n",
            f"{json.dumps(worklog_data['gerrit_reviews'], ensure_ascii=False, indent=2)}\n\n",
            f"💬 GERRIT 댓글 데이터 ({len(worklog_data['gerrit_comments'])}개 항목):\n",
            f"{json.dumps(worklog_data['gerrit_comments'], ensure_ascii=False, indent=2)}\n\n"
        ]
        
        # 이메일 데이터 추가 (있는 경우)
        if 'email_summaries' in worklog_data and worklog_data['email_summaries']:
            prompt_parts.extend([
                f"📧 발송 이메일 요약 데이터 ({len(worklog_data['email_summaries'])}개 항목):\n",
                f"{json.dumps(worklog_data['email_summaries'], ensure_ascii=False, indent=2)}\n\n"
            ])
        
        prompt_parts.append("위 데이터를 바탕으로 주간 보고서를 작성해주세요.")
        
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
            print(f"🔍 MD 파일 검색 시작: {directory_path}")
            
            # MD 파일 찾기
            md_file = self.find_md_file(directory_path)
            
            if md_file:
                print(f"📄 MD 파일 발견: {md_file}")
                
                # MD 파일 읽기
                md_content = self.read_md_file(md_file)
                result['md_file'] = md_file
                result['md_content'] = md_content
                
                print(f"✅ MD 템플릿이 있습니다. 템플릿 기반으로 주간 보고서를 생성합니다.")
                print(f"📝 템플릿 내용 미리보기: {md_content[:200]}...")
                
                # LLM으로 요약 생성 (MD 템플릿 포함)
                summary = self.generate_worklog_summary(username, worklog_data, md_content)
                result['summary'] = summary
                result['success'] = True
                
            else:
                print("⚠️ MD 템플릿을 찾을 수 없습니다. 기본 형식으로 주간 보고서를 생성합니다.")
                
                # MD 파일이 없어도 워크로그만으로 요약 생성
                summary = self.generate_worklog_summary(username, worklog_data)
                result['summary'] = summary
                result['success'] = True
                
        except Exception as e:
            error_msg = f"주간 보고서 생성 중 오류: {e}"
            print(f"❌ {error_msg}")
            result['error'] = error_msg
            
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
