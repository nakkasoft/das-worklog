import os
import json
import sys
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
        # 대화 히스토리 관리
        self.conversation_history = []
        self.session_started = False
    
    def start_new_session(self):
        """
        새로운 대화 세션 시작 (이전 대화 히스토리 초기화)
        """
        self.conversation_history = []
        self.session_started = True
        print("🔄 새로운 LLM 세션이 시작되었습니다. 이전 대화 기록이 초기화되었습니다.")
    
    def add_to_conversation(self, role, content):
        """
        대화 히스토리에 메시지 추가
        
        Args:
            role (str): "system", "user", "assistant"
            content (str): 메시지 내용
        """
        self.conversation_history.append({
            "role": role,
            "content": content
        })
    
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
            
            # templates 디렉토리도 확인 (외부 디렉토리에서)
            from worklog import config_path  # config_path 함수 import
            templates_dir = config_path('templates')  # exe와 같은 디렉토리의 templates 폴더
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
        워크로그 데이터를 LLM으로 요약 (세션 기반 대화)
        
        Args:
            username (str): 사용자명
            worklog_data (dict): 수집된 워크로그 데이터
            md_content (str, optional): 추가 참고용 마크다운 파일 내용
            
        Returns:
            str: LLM이 생성한 요약 내용
        """
        try:
            # 새 세션이 시작되지 않았다면 자동으로 시작
            if not self.session_started:
                self.start_new_session()
                
                # 시스템 메시지 추가 (세션 시작 시 한 번만)
                system_message = """당신은 다양한 직군(개발, 영업, 마케팅, PM, 기획, 운영 등)의 업무 활동을 분석하여 전문적인 주간 보고서를 작성하는 전문가입니다. 
                각 직군의 업무 특성을 이해하고, 해당 분야에 적합한 관점과 용어로 보고서를 작성해주세요.
                
                ## 핵심 역할
                - 사용자의 다양한 업무 활동(이슈 관리, 협업, 커뮤니케이션 등)을 체계적으로 분석
                - 각 직군별 KPI와 성과 지표를 고려한 맞춤형 보고서 작성
                - 비즈니스 임팩트와 협업 성과를 명확하게 표현
                - 상급자와 동료가 이해하기 쉬운 명확하고 구체적인 한국어로 작성
                
                ## 직군별 관점
                - **개발/기술**: 기술적 해결책, 품질, 성능, 아키텍처 관점
                - **영업/세일즈**: 고객 관계, 매출 기여, 영업 기회, 파이프라인 관점  
                - **마케팅**: 브랜드, 캠페인 효과, 고객 인사이트, ROI 관점
                - **PM/기획**: 프로젝트 진행률, 리스크 관리, 이해관계자 조율 관점
                - **운영/지원**: 프로세스 개선, 효율성, 고객 만족도 관점
                
                ## 작성 원칙
                1. **맥락 이해**: 사용자의 직군과 업무 특성을 파악하여 적절한 관점 적용
                2. **협업 중시**: 팀워크, 부서간 협업, 커뮤니케이션 성과 강조
                3. **성과 지향**: 정량적 지표와 정성적 성과를 균형있게 표현
                4. **전문성**: 해당 분야의 전문 용어를 적절히 사용하되 이해하기 쉽게 설명
                5. **대화형**: 사용자의 추가 요청이나 수정사항에 맥락을 유지하며 유연하게 응답"""
                
                self.add_to_conversation("system", system_message)
            
            # 프롬프트 구성
            prompt_content = self._build_prompt(username, worklog_data, md_content)
            
            # 사용자 메시지를 히스토리에 추가
            self.add_to_conversation("user", prompt_content)
            
            # Azure OpenAI API 호출 (전체 대화 히스토리 포함)
            completion = self.client.chat.completions.create(
                model=self.config["azure_openai_chat_deployment"],
                messages=self.conversation_history,
                max_completion_tokens=10000,
            )
            
            response = completion.choices[0].message.content
            
            # 어시스턴트 응답을 히스토리에 추가
            self.add_to_conversation("assistant", response)
            
            return response
            
        except Exception as e:
            raise Exception(f"LLM 요약 생성 중 오류 발생: {e}")
    
    def continue_conversation(self, user_message):
        """
        기존 세션에서 대화 계속하기
        
        Args:
            user_message (str): 사용자의 추가 질문이나 요청
            
        Returns:
            str: LLM 응답
        """
        try:
            if not self.session_started:
                raise Exception("대화 세션이 시작되지 않았습니다. 먼저 generate_worklog_summary를 호출하세요.")
            
            # 사용자 메시지를 히스토리에 추가
            self.add_to_conversation("user", user_message)
            
            # Azure OpenAI API 호출
            completion = self.client.chat.completions.create(
                model=self.config["azure_openai_chat_deployment"],
                messages=self.conversation_history,
                max_completion_tokens=10000,
            )
            
            response = completion.choices[0].message.content
            
            # 어시스턴트 응답을 히스토리에 추가
            self.add_to_conversation("assistant", response)
            
            return response
            
        except Exception as e:
            raise Exception(f"대화 계속 중 오류 발생: {e}")
    
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
        system_prompt = """아래 수집된 업무 활동 데이터를 분석하여 다양한 직군에서 활용 가능한 체계적이고 상세한 주간 보고서를 작성해주세요.

        ## 분석 대상 업무 활동
        - **이슈/티켓 관리**: Jira 등을 통한 업무 이슈 처리 및 진행 현황
        - **협업 활동**: Confluence, 코드리뷰, 회의 등을 통한 팀 협업
        - **커뮤니케이션**: 이메일을 통한 대내외 소통 및 업무 조율
        - **문서화/지식공유**: 업무 관련 문서 작성 및 정보 공유

        ## 작성 세부 지침

        ### 📊 이슈/업무 분류 기준
        - **완료**: Resolve, Resolved, Close, Closed, "Inquired to Reporter", Done 상태
        - **진행 중**: In Progress, In Review, In Development, Working 등 활성 상태
        - **대기/신규**: Open, New, To Do, Backlog, Pending 상태
        - **본인 관여**: 담당자, 보고자, 워크로그 작성자, 댓글 참여자인 이슈

        ### 🔍 직군별 맞춤 분석
        1. **개발/기술**: 기술적 해결 과정, 사용 기술스택, 품질 개선사항, 성능 최적화
        2. **영업/세일즈**: 고객 대응, 영업 기회 창출, 제안서/계약 관련 활동, 매출 기여도
        3. **마케팅**: 캠페인 기획/실행, 고객 분석, 브랜드 관리, 성과 측정
        4. **PM/기획**: 프로젝트 관리, 일정 조율, 리스크 대응, 이해관계자 커뮤니케이션
        5. **운영/지원**: 프로세스 개선, 고객 지원, 시스템 운영, 효율성 향상

        ### 📝 상세 작성 원칙
        1. **구체성**: 추상적 표현 지양, 구체적 수치와 결과 중심 서술
        2. **맥락 제공**: 단순 나열이 아닌 업무 배경과 목적 설명
        3. **영향 분석**: 개인 성과가 팀/조직에 미치는 긍정적 영향 명시
        4. **협업 강조**: 타 부서/팀과의 협력 사항과 소통 성과 부각
        5. **학습 요소**: 새로 배운 점이나 개선한 프로세스 포함
        6. **미래 지향**: 다음 주 계획과 연결되는 연속성 있는 서술

        ### 📋 품질 기준
        - **완성도**: 각 섹션이 유기적으로 연결되는 일관성 있는 보고서
        - **가독성**: 상급자와 동료가 빠르게 이해할 수 있는 명확한 구조
        - **실용성**: 의사결정에 도움이 되는 실질적이고 유용한 정보 제공
        - **전문성**: 해당 업무 분야의 특성을 반영한 전문적 관점

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
            f"사용자: {username}\n\n"
        ]
        
        # 개별 Jira 이슈 요약 추가 (최우선)
        if 'jira_issue_summaries' in worklog_data and worklog_data['jira_issue_summaries']:
            prompt_parts.extend([
                f"🔍 JIRA 이슈 개별 요약 ({len(worklog_data['jira_issue_summaries'])}개 항목):\n",
                "=== 각 이슈별 LLM 요약 결과 ===\n"
            ])
            
            for summary_item in worklog_data['jira_issue_summaries']:
                prompt_parts.append(f"\n{summary_item['summary']}\n")
            
            prompt_parts.append("\n=== 개별 요약 끝 ===\n\n")
        
        prompt_parts.extend([
            f"📋 JIRA 활동 데이터 ({len(worklog_data['jira_data'])}개 항목):\n",
            f"{json.dumps(worklog_data['jira_data'], ensure_ascii=False, indent=2)}\n\n",
            f"📝 CONFLUENCE 활동 데이터 ({len(worklog_data['confluence_data'])}개 항목):\n",
            f"{json.dumps(worklog_data['confluence_data'], ensure_ascii=False, indent=2)}\n\n",
            f"🔍 GERRIT 리뷰 데이터 ({len(worklog_data['gerrit_reviews'])}개 항목):\n",
            f"{json.dumps(worklog_data['gerrit_reviews'], ensure_ascii=False, indent=2)}\n\n",
            f"💬 GERRIT 댓글 데이터 ({len(worklog_data['gerrit_comments'])}개 항목):\n",
            f"{json.dumps(worklog_data['gerrit_comments'], ensure_ascii=False, indent=2)}\n\n"
        ])
        
        # 이메일 요약 데이터 추가 (LLM으로 요약된 경우)
        if 'email_summaries' in worklog_data and worklog_data['email_summaries']:
            prompt_parts.extend([
                f"📧 발송 이메일 요약 데이터 ({len(worklog_data['email_summaries'])}개 항목):\n",
                f"{json.dumps(worklog_data['email_summaries'], ensure_ascii=False, indent=2)}\n\n"
            ])
        # 원시 이메일 데이터 추가 (아직 요약되지 않은 경우)
        elif 'email_data' in worklog_data and worklog_data['email_data']:
            prompt_parts.extend([
                f"📧 원시 이메일 데이터 ({len(worklog_data['email_data'])}개 항목):\n",
                f"{json.dumps(worklog_data['email_data'], ensure_ascii=False, indent=2)}\n\n"
            ])
        
        prompt_parts.append("""
## 🚀 다양한 직군을 위한 포괄적 주간 보고서 작성

위에 제공된 모든 업무 활동 데이터를 종합 분석하여 다양한 직군에서 활용할 수 있는 완성도 높은 주간 보고서를 작성해주세요.

### 📊 데이터 활용 우선순위 및 전략
1. **1차 핵심**: "JIRA 이슈 개별 요약" - LLM이 미리 분석한 상세 내용을 주요 업무 성과로 활용
2. **2차 중요**: "이메일 요약 데이터" - 대내외 커뮤니케이션 활동과 협업 성과 반영  
3. **3차 보완**: Gerrit, Confluence 활동 - 기술 검토, 지식 공유, 문서화 기여도 추가
4. **구조 준수**: 제공된 MD 템플릿을 기반으로 하되 사용자의 직군 특성에 맞게 유연하게 적용

### 🎯 직군별 맞춤 작성 전략
- **개발/기술**: 코드품질, 아키텍처 개선, 기술 도입, 성능 최적화 관점 강조
- **영업/세일즈**: 고객 관계 구축, 매출 기여도, 영업 기회 발굴, 시장 피드백 중심
- **마케팅**: 브랜드 인지도, 캠페인 성과, 고객 인사이트, 시장 반응 분석 관점
- **PM/기획**: 프로젝트 진행률, 이해관계자 관리, 리스크 대응, 일정 관리 중심
- **운영/지원**: 프로세스 효율화, 고객 만족도, 시스템 안정성, 업무 개선 관점

### 📝 고품질 보고서 작성 기준
- **사실 기반**: 제공된 데이터에서만 추출된 사실을 기반으로 작성하며, 추측이나 가정은 절대 포함하지 않음
- **데이터 중심**: 수집된 Jira 이슈, 이메일, Gerrit, Confluence 데이터만을 활용하여 객관적으로 작성
- **포괄성**: 모든 직군이 이해할 수 있는 명확하고 전문적인 업무용 한국어 사용
- **구체성**: 정량적 지표와 구체적 성과를 우선하되 정성적 가치도 명확히 표현
- **협업성**: 팀워크, 부서간 협력, 외부 이해관계자와의 소통 성과 적극 부각
- **전략성**: 단순 업무 나열이 아닌 조직 목표와 연결된 전략적 기여도 강조
- **연속성**: 이전 주 계획 대비 달성도와 다음 주 계획의 논리적 연결성 확보

### 🔗 필수 포함 요소  
- 주요 Jira 이슈에는 클릭 가능한 링크 포함: [이슈키](http://jira.lge.com/issue/browse/이슈키)
- 정확한 통계와 진행률 (완료/진행중/신규 건수 등)
- 협업 파트너와 커뮤니케이션 범위 (사내외 이해관계자)
- 구체적인 비즈니스 임팩트와 조직 기여도
- 실현 가능한 다음 주 목표와 예상 리스크

### 📋 품질 검증 체크리스트
- [ ] **사실 기반 검증**: 작성된 모든 내용이 제공된 데이터에서 확인 가능한 사실인가?
- [ ] **추측/가정 제거**: 데이터에 없는 내용을 추측하거나 가정하여 작성하지 않았는가?
- [ ] 해당 직군의 상급자가 읽고 성과를 명확히 인식할 수 있는가?
- [ ] 동료들이 협업 요청이나 지원이 필요한 부분을 파악할 수 있는가?
- [ ] 조직의 전략 목표와 개인 업무의 연결고리가 명확한가?
- [ ] 다음 주 업무 계획이 구체적이고 실행 가능한가?

**중요**: 반드시 수집된 데이터에서 확인 가능한 사실만을 기반으로 작성하고, 추측이나 가정은 절대 포함하지 마세요.

지금 전문적이고 실용적인 주간 보고서를 작성해주세요.
        """)
        
        # Jira 이슈 링크 정보 추가
        if 'jira_issue_summaries' in worklog_data and worklog_data['jira_issue_summaries']:
            prompt_parts.append("""

**참고용 Jira 이슈 링크들**:
""")
            for summary_item in worklog_data['jira_issue_summaries']:
                issue_key = summary_item.get('issue_key', 'Unknown')
                original_data = summary_item.get('original_data', {})
                issue_url = original_data.get('url', f"http://jira.lge.com/issue/browse/{issue_key}")
                issue_summary = original_data.get('summary', 'No Summary')
                prompt_parts.append(f"- [{issue_key}]({issue_url}): {issue_summary}\n")
        
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

    def summarize_jira_issue(self, issue_data):
        """
        개별 Jira 이슈를 LLM으로 요약
        
        Args:
            issue_data (dict): Jira 이슈 상세 정보
            
        Returns:
            dict: 요약 결과
        """
        try:
            # Jira 이슈 요약용 프롬프트 생성
            prompt = self._build_jira_issue_prompt(issue_data)
            
            # LLM 요약 요청
            summary = self.continue_conversation(prompt)
            
            return {
                "success": True,
                "issue_key": issue_data.get("issue_key", ""),
                "summary": summary,
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "issue_key": issue_data.get("issue_key", ""),
                "summary": "",
                "error": str(e)
            }
    
    def summarize_email_batch(self, email_data_list):
        """
        이메일 데이터 배열을 배치로 LLM 요약
        
        Args:
            email_data_list (list): 이메일 데이터 배열
            
        Returns:
            list: 요약된 이메일 데이터 배열
        """
        summarized_emails = []
        
        try:
            if not email_data_list:
                print("📧 요약할 이메일이 없습니다.")
                return summarized_emails
            
            print(f"📧 총 {len(email_data_list)}개의 이메일을 순차적으로 요약합니다...")
            
            for i, email_data in enumerate(email_data_list, 1):
                try:
                    print(f"[{i}/{len(email_data_list)}] 이메일 요약 중: {email_data.get('subject', 'Unknown')[:50]}...")
                    
                    # 개별 이메일 요약
                    summary_result = self.summarize_single_email(email_data)
                    
                    if summary_result['success']:
                        summarized_emails.append({
                            'subject': email_data.get('subject', ''),
                            'to': email_data.get('to', ''),
                            'date': email_data.get('date', ''),
                            'ai_summary': summary_result['summary'],
                            'original_data': email_data
                        })
                        print(f"✅ 이메일 요약 완료")
                    else:
                        print(f"❌ 이메일 요약 실패: {summary_result['error']}")
                        # 실패한 경우에도 기본 정보는 포함
                        summarized_emails.append({
                            'subject': email_data.get('subject', ''),
                            'to': email_data.get('to', ''),
                            'date': email_data.get('date', ''),
                            'ai_summary': f"요약 실패: {summary_result['error']}",
                            'original_data': email_data
                        })
                        
                except Exception as e:
                    print(f"❌ 이메일 요약 중 오류: {e}")
                    # 오류가 있어도 다른 이메일 계속 처리
                    continue
            
            print(f"🎉 이메일 배치 요약 완료: {len(summarized_emails)}개 성공")
            return summarized_emails
            
        except Exception as e:
            raise Exception(f"이메일 배치 요약 중 오류: {e}")
    
    def summarize_single_email(self, email_data):
        """
        개별 이메일을 LLM으로 요약
        
        Args:
            email_data (dict): 이메일 데이터
            
        Returns:
            dict: 요약 결과
        """
        try:
            # 이메일 요약용 프롬프트 생성
            prompt = self._build_email_summary_prompt(email_data)
            
            # LLM 요약 요청
            summary = self.continue_conversation(prompt)
            
            return {
                "success": True,
                "summary": summary,
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "issue_key": issue_data.get("issue_key", ""),
                "summary": "",
                "error": str(e)
            }
    
    def summarize_email_batch(self, email_data_list):
        """
        이메일 데이터 배열을 배치로 LLM 요약
        
        Args:
            email_data_list (list): 이메일 데이터 배열
            
        Returns:
            list: 요약된 이메일 데이터 배열
        """
        summarized_emails = []
        
        try:
            if not email_data_list:
                print("📧 요약할 이메일이 없습니다.")
                return summarized_emails
            
            print(f"📧 총 {len(email_data_list)}개의 이메일을 순차적으로 요약합니다...")
            
            for i, email_data in enumerate(email_data_list, 1):
                try:
                    print(f"[{i}/{len(email_data_list)}] 이메일 요약 중: {email_data.get('subject', 'Unknown')[:50]}...")
                    
                    # 개별 이메일 요약
                    summary_result = self.summarize_single_email(email_data)
                    
                    if summary_result['success']:
                        summarized_emails.append({
                            'subject': email_data.get('subject', ''),
                            'to': email_data.get('to', ''),
                            'date': email_data.get('date', ''),
                            'ai_summary': summary_result['summary'],
                            'original_data': email_data
                        })
                        print(f"✅ 이메일 요약 완료")
                    else:
                        print(f"❌ 이메일 요약 실패: {summary_result['error']}")
                        # 실패한 경우에도 기본 정보는 포함
                        summarized_emails.append({
                            'subject': email_data.get('subject', ''),
                            'to': email_data.get('to', ''),
                            'date': email_data.get('date', ''),
                            'ai_summary': f"요약 실패: {summary_result['error']}",
                            'original_data': email_data
                        })
                        
                except Exception as e:
                    print(f"❌ 이메일 요약 중 오류: {e}")
                    # 오류가 있어도 다른 이메일 계속 처리
                    continue
            
            print(f"🎉 이메일 배치 요약 완료: {len(summarized_emails)}개 성공")
            return summarized_emails
            
        except Exception as e:
            raise Exception(f"이메일 배치 요약 중 오류: {e}")
    
    def summarize_single_email(self, email_data):
        """
        개별 이메일을 LLM으로 요약
        
        Args:
            email_data (dict): 이메일 데이터
            
        Returns:
            dict: 요약 결과
        """
        try:
            # 이메일 요약용 프롬프트 생성
            prompt = self._build_email_summary_prompt(email_data)
            
            # LLM 요약 요청
            summary = self.continue_conversation(prompt)
            
            return {
                "success": True,
                "summary": summary,
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "summary": "",
                "error": str(e)
            }
    
    def _build_email_summary_prompt(self, email_data):
        """
        이메일 요약용 프롬프트 생성
        
        Args:
            email_data (dict): 이메일 데이터
            
        Returns:
            str: 프롬프트 문자열
        """
        prompt = f"""다음 발신 이메일을 비즈니스 커뮤니케이션 관점에서 종합 분석하여 상세한 요약을 작성해주세요.

## 📧 이메일 기본 정보
- **제목**: {email_data.get('subject', 'N/A')}
- **수신자**: {email_data.get('to', 'N/A')}
- **참조 (CC)**: {email_data.get('cc', 'N/A') if email_data.get('cc') else '없음'}
- **발송 일시**: {email_data.get('date', 'N/A')}
- **첨부파일**: {len(email_data.get('attachments', []))}개

## 📄 이메일 전체 내용 (히스토리 포함)
{email_data.get('body_clean', '본문 없음')[:3000]}

## 🎯 상세 분석 및 요약 작성

다음 구조로 업무 맥락을 충분히 이해할 수 있는 종합적인 요약을 작성해주세요:

### 📌 [{email_data.get('subject', 'N/A')[:70]}...]

**🎯 커뮤니케이션 목적 및 배경**
- [이메일을 보내게 된 배경과 주요 목적]
- [이전 논의나 히스토리가 있다면 맥락 설명]

**👥 관련 이해관계자**
- **주 수신자**: {email_data.get('to', 'N/A')[:120]}
- **참조자**: {email_data.get('cc', 'N/A')[:120] if email_data.get('cc') else '없음'}
- **관련 부서/팀**: [내용에서 파악 가능한 관련 조직]

**📋 핵심 내용 및 메시지**
- [주요 메시지 1 - 가장 중요한 전달사항]
- [주요 메시지 2 - 구체적 요청이나 제안사항]
- [주요 메시지 3 - 중요한 결정사항이나 업데이트]
- [추가 세부사항이나 첨부 정보]

**💼 업무 영향 및 가치**
- **직군별 관점**: [개발/영업/마케팅/PM/운영 등 해당 업무 특성 반영]
- **비즈니스 임팩트**: [조직이나 프로젝트에 미치는 영향]
- **우선순위**: 높음/보통/낮음 [내용의 긴급성과 중요도 판단]

**⏰ 후속 조치 및 기대사항**
- [요청된 액션이나 피드백 사항]
- [마감일이나 중요 일정]
- [기대하는 결과나 후속 커뮤니케이션]

### 작성 지침
- **히스토리 분석**: 이메일 본문 내 이전 대화 내역도 함께 분석하여 전체 맥락 파악
- **상세 수준**: 6-8줄 정도로 충실하게 작성하여 업무 맥락을 완전히 이해할 수 있도록
- **실용성**: 상급자나 동료가 해당 커뮤니케이션의 중요도와 후속 조치를 명확히 파악할 수 있도록"""
        
        return prompt

    def _build_jira_issue_prompt(self, issue_data):
        """
        Jira 이슈 요약용 프롬프트 생성
        
        Args:
            issue_data (dict): Jira 이슈 상세 정보
            
        Returns:
            str: 프롬프트 문자열
        """
        prompt = f"""다음 업무 이슈를 다양한 직군 관점에서 분석하여 상세하고 유용한 요약을 작성해주세요.

## 📋 이슈 기본 정보
- **이슈 ID**: {issue_data.get('issue_key', 'N/A')}
- **제목**: {issue_data.get('summary', 'N/A')}
- **현재 상태**: {issue_data.get('status', 'N/A')}
- **담당자**: {issue_data.get('assignee', 'N/A')}
- **우선순위**: {issue_data.get('priority', 'N/A')}
- **이슈 타입**: {issue_data.get('issue_type', 'N/A')}
- **생성일**: {issue_data.get('created', 'N/A')}
- **최근 업데이트**: {issue_data.get('updated', 'N/A')}

## 📝 이슈 상세 설명
{issue_data.get('description', '설명 없음')}

## 💬 커뮤니케이션 이력 ({issue_data.get('comment_count', 0)}개 댓글)"""
        
        # 댓글 추가
        if issue_data.get('comments'):
            for i, comment in enumerate(issue_data['comments'][:5], 1):  # 최근 5개만
                prompt += f"""
### 댓글 {i} - {comment.get('author', 'Unknown')} ({comment.get('created', '')})
{comment.get('body', '')}"""
        
        prompt += f"""

## 워크로그 내역 ({issue_data.get('worklog_count', 0)}개)"""
        
        # 워크로그 추가
        if issue_data.get('worklogs'):
            for i, worklog in enumerate(issue_data['worklogs'][:3], 1):  # 최근 3개만
                prompt += f"""
### 워크로그 {i} - {worklog.get('author', 'Unknown')} ({worklog.get('created', '')})
- 소요 시간: {worklog.get('timeSpent', 'N/A')}
- 내용: {worklog.get('comment', '')}"""
        
        # 첨부파일 정보
        if issue_data.get('attachment_count', 0) > 0:
            prompt += f"""

## 첨부파일 ({issue_data.get('attachment_count', 0)}개)"""
            for attachment in issue_data.get('attachments', [])[:3]:  # 최근 3개만
                prompt += f"""
- {attachment.get('filename', 'N/A')} (작성자: {attachment.get('author', 'Unknown')}, 날짜: {attachment.get('created', 'N/A')})"""
        
        prompt += """

## 🎯 상세 요약 작성 요구사항

**중요**: 댓글과 워크로그의 모든 내용을 꼼꼼히 분석하여 실제 수행한 활동을 구체적으로 기록해주세요.

다음 구조로 업무 관점에서 상세하고 실용적인 요약을 작성해주세요:

### 📌 [{issue_data.get('issue_key', 'N/A')}] {issue_data.get('summary', 'N/A')[:80]}

**📊 현황 및 진행률**
- **현재 상태**: {issue_data.get('status', 'N/A')} (이전 상태에서 변경사항 포함)
- **담당 현황**: {issue_data.get('assignee', 'N/A')} / 우선순위: {issue_data.get('priority', 'N/A')}
- **진행률**: [댓글과 워크로그 기반으로 예상 진행률 제시]

**🔧 주요 수행 활동 (상세 기록 필수)**
- [구체적 작업 내용 1 - 댓글이나 워크로그에서 추출한 실제 수행 업무]
  * 세부 작업: [구체적인 기술적/업무적 세부사항]
  * 수행 방법: [어떤 방식으로 진행했는지]
  * 결과물: [산출물이나 성과]
- [구체적 작업 내용 2 - 해결 과정이나 의사결정 사항]
  * 문제 분석: [어떤 문제를 어떻게 분석했는지]
  * 해결 방안: [구체적인 해결 방법이나 대안]
  * 의사결정: [내린 결정과 그 근거]
- [구체적 작업 내용 3 - 협업이나 커뮤니케이션 내용]
  * 협업 대상: [누구와 어떤 목적으로 협업했는지]
  * 논의 내용: [구체적인 논의 사항과 결론]
  * 합의 사항: [도출된 합의나 액션 아이템]

**👥 협업 및 소통**
- [다른 팀원이나 부서와의 협력 사항]
- [중요한 의사결정이나 합의 사항]
- [외부 이해관계자와의 커뮤니케이션]

**⚠️ 이슈 및 리스크**
- [발견된 문제점이나 장애 요소]
- [해결이 필요한 의존성이나 차단 요인]
- [예상되는 지연이나 리스크 요소]

**📋 다음 단계 및 계획**
- [향후 진행 예정인 작업]
- [필요한 후속 조치나 의사결정]
- [예상 완료 일정이나 마일스톤]

### 작성 지침
- **사실 기반**: 댓글과 워크로그에서 확인 가능한 사실만 작성하며, 추측이나 해석은 피함
- **데이터 충실**: 실제 Jira 이슈에 기록된 내용만을 바탕으로 객관적으로 요약
- **활동 내역 상세화**: 단순히 "작업했다"가 아닌 구체적으로 "무엇을, 어떻게, 왜" 수행했는지 명시
  * 기술적 세부사항: 사용한 도구, 방법론, 기술 스택 등
  * 업무 프로세스: 진행 단계, 검토 과정, 승인 절차 등
  * 소요 시간/노력: 워크로그 기반 실제 투입 시간과 노력 수준
- **직군별 관점**: 개발(기술적 세부사항), 영업(고객 영향), 마케팅(브랜드 임팩트), PM(일정/리소스), 운영(프로세스 개선) 등
- **비즈니스 가치**: 단순 작업 나열이 아닌 조직에 미치는 영향과 가치 중심
- **상세 수준**: 주요 수행 활동은 10-15줄 정도로 충분히 상세하게 작성 (간략한 요약 지양)
- **실용성**: 상급자나 동료가 읽었을 때 실제 업무 상황과 기여도를 명확히 이해할 수 있는 수준
- **맥락 제공**: 각 활동이 전체 프로젝트나 목표에서 차지하는 위치와 중요도 설명"""
        
        return prompt


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
