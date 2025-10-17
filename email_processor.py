import os
import email
import email.policy
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
from datetime import datetime
import re
from bs4 import BeautifulSoup
import llm_processor

CONFIG_FILE_PATH = "user_config.json"
OUTLOOK_FOLDER_PATH = r"./outlook"

class EmailProcessor:
    """EML 파일 파싱 및 이메일 요약 처리 클래스"""
    
    def __init__(self, config, llm_processor=None):
        """
        EmailProcessor 초기화
        
        Args:
            config (dict): 설정 정보 (LLM 설정 포함)
            llm_processor (LLMProcessor, optional): 외부 LLMProcessor 인스턴스. 없으면 새로 생성
        """
        self.config = config
        if llm_processor:
            self.llm_processor = llm_processor
            self.use_external_llm = True
            print("📧 이메일 프로세서가 외부 LLM 세션을 사용합니다.")
        else:
            import llm_processor as llm_mod
            self.llm_processor = llm_mod.LLMProcessor(config)
            self.use_external_llm = False
            print("📧 이메일 프로세서가 독립적인 LLM 인스턴스를 생성했습니다.")
    
    def find_eml_files(self):
        """
        Outlook 폴더에서 EML 파일들을 찾기
        
        Returns:
            list: 찾은 EML 파일들의 경로 리스트
        """
        eml_files = []
        outlook_folder_path = OUTLOOK_FOLDER_PATH
        
        try:
            if not os.path.exists(outlook_folder_path):
                raise Exception(f"폴더가 존재하지 않습니다: {outlook_folder_path}")
            
            print(f"🔍 EML 파일 검색 중: {outlook_folder_path}")
            
            for root, dirs, files in os.walk(outlook_folder_path):
                for file in files:
                    if file.lower().endswith('.eml'):
                        file_path = os.path.join(root, file)
                        eml_files.append(file_path)
                        print(f"📧 EML 파일 발견: {file}")
            
            print(f"✅ 총 {len(eml_files)}개의 EML 파일을 발견했습니다.")
            return eml_files
            
        except Exception as e:
            raise Exception(f"EML 파일 검색 중 오류 발생: {e}")
    
    def parse_eml_file(self, eml_file_path):
        """
        EML 파일을 파싱하여 이메일 정보 추출
        
        Args:
            eml_file_path (str): EML 파일 경로
            
        Returns:
            dict: 파싱된 이메일 정보
        """
        try:
            print(f"📖 EML 파일 파싱 중: {os.path.basename(eml_file_path)}")
            
            # EML 파일 읽기
            with open(eml_file_path, 'rb') as f:
                raw_email = f.read()
            
            # 이메일 파싱 (현대적인 정책 사용)
            msg = email.message_from_bytes(raw_email, policy=email.policy.default)
            
            # 기본 정보 추출
            email_data = {
                'file_path': eml_file_path,
                'file_name': os.path.basename(eml_file_path),
                'subject': self._decode_header(msg.get('Subject', '')),
                'from': self._decode_header(msg.get('From', '')),
                'to': self._decode_header(msg.get('To', '')),
                'cc': self._decode_header(msg.get('Cc', '')),
                'bcc': self._decode_header(msg.get('Bcc', '')),
                'date': self._parse_date(msg.get('Date', '')),
                'message_id': msg.get('Message-ID', ''),
                'body_text': '',
                'body_html': '',
                'attachments': [],
                'is_multipart': msg.is_multipart()
            }
            
            # 본문 및 첨부파일 추출
            self._extract_body_and_attachments(msg, email_data)
            
            # 본문 텍스트 정리
            email_data['body_clean'] = self._clean_email_body(email_data)
            
            print(f"✅ 이메일 파싱 완료: {email_data['subject'][:50]}...")
            return email_data
            
        except Exception as e:
            raise Exception(f"EML 파일 파싱 중 오류 발생: {e}")
    
    def _decode_header(self, header_value):
        """이메일 헤더 디코딩"""
        if not header_value:
            return ""
        
        try:
            decoded = email.header.decode_header(header_value)
            result = ""
            for text, encoding in decoded:
                if isinstance(text, bytes):
                    result += text.decode(encoding or 'utf-8', errors='ignore')
                else:
                    result += text
            return result.strip()
        except Exception:
            return str(header_value)
    
    def _parse_date(self, date_str):
        """이메일 날짜 파싱"""
        if not date_str:
            return None
        
        try:
            # email.utils.parsedate_to_datetime 사용
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str).isoformat()
        except Exception:
            return date_str
    
    def _extract_body_and_attachments(self, msg, email_data):
        """이메일 본문과 첨부파일 추출"""
        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = part.get("Content-Disposition", "")
                content_type = part.get_content_type()
                
                # 첨부파일 처리
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        email_data['attachments'].append({
                            'filename': self._decode_header(filename),
                            'content_type': content_type,
                            'size': len(part.get_payload(decode=True) or b'')
                        })
                
                # 본문 처리
                elif content_type == "text/plain" and not email_data['body_text']:
                    try:
                        email_data['body_text'] = part.get_content()
                    except Exception:
                        payload = part.get_payload(decode=True)
                        if payload:
                            email_data['body_text'] = payload.decode('utf-8', errors='ignore')
                
                elif content_type == "text/html" and not email_data['body_html']:
                    try:
                        email_data['body_html'] = part.get_content()
                    except Exception:
                        payload = part.get_payload(decode=True)
                        if payload:
                            email_data['body_html'] = payload.decode('utf-8', errors='ignore')
        else:
            # 단일 파트 메시지
            content_type = msg.get_content_type()
            try:
                content = msg.get_content()
            except Exception:
                payload = msg.get_payload(decode=True)
                content = payload.decode('utf-8', errors='ignore') if payload else ""
            
            if content_type == "text/plain":
                email_data['body_text'] = content
            elif content_type == "text/html":
                email_data['body_html'] = content
            else:
                email_data['body_text'] = content
    
    def _clean_email_body(self, email_data):
        """이메일 본문 정리"""
        # HTML이 있으면 텍스트로 변환
        if email_data['body_html']:
            try:
                soup = BeautifulSoup(email_data['body_html'], 'html.parser')
                text = soup.get_text()
                # 여러 줄바꿈을 하나로 정리
                text = re.sub(r'\n\s*\n', '\n\n', text)
                return text.strip()
            except Exception:
                pass
        
        # 일반 텍스트 사용
        if email_data['body_text']:
            text = email_data['body_text']
            # 여러 줄바꿈을 하나로 정리
            text = re.sub(r'\n\s*\n', '\n\n', text)
            return text.strip()
        
        return ""
    
    def summarize_email(self, email_data):
        """
        이메일 내용을 LLM으로 요약
        
        Args:
            email_data (dict): 파싱된 이메일 데이터
            
        Returns:
            str: LLM이 생성한 이메일 요약
        """
        try:
            print(f"🤖 이메일 요약 생성 중: {email_data['subject'][:50]}...")
            
            # 이메일 요약용 프롬프트 구성
            prompt = self._build_email_summary_prompt(email_data)
            
            if self.use_external_llm:
                # 외부 LLM 세션을 사용하는 경우 (세션 기반 대화)
                summary = self.llm_processor.continue_conversation(prompt)
            else:
                # 독립적인 LLM 인스턴스를 사용하는 경우 (기존 방식)
                completion = self.llm_processor.client.chat.completions.create(
                    model=self.config["azure_openai_chat_deployment"],
                    messages=[
                        {
                            "role": "system",
                            "content": "당신은 이메일 요약 전문가입니다. 이전 대화 내용은 모두 잊고, 오직 현재 제공되는 이메일 데이터만을 기반으로 요약을 작성해주세요. 매번 새로운 독립적인 작업으로 처리해주세요."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_completion_tokens=1000,
                )
                summary = completion.choices[0].message.content
            
            print(f"✅ 이메일 요약 완료")
            return summary
            
        except Exception as e:
            raise Exception(f"이메일 요약 생성 중 오류 발생: {e}")
    
    def _build_email_summary_prompt(self, email_data):
        """이메일 요약용 프롬프트 구성"""
        prompt_parts = [
            "다음은 사용자가 발송한 이메일입니다. 내용을 간략하게 요약해주세요.\n\n",
            f"📧 제목: {email_data['subject']}\n",
            f"📥 수신자: {email_data['to']}\n"
        ]
        
        if email_data['cc']:
            prompt_parts.append(f"📋 참조: {email_data['cc']}\n")
        
        if email_data['attachments']:
            attachments_info = ", ".join([att['filename'] for att in email_data['attachments']])
            prompt_parts.append(f"📎 첨부파일: {attachments_info}\n")
        
        prompt_parts.extend([
            "\n" + "="*50 + "\n",
            "📝 본문 내용:\n",
            email_data['body_clean'],
            "\n" + "="*50 + "\n\n",
            "위 발송 이메일의 주요 내용을 다음과 같이 요약해주세요:\n",
            "1. 핵심 주제\n",
            "2. 주요 내용 (2-3줄)\n",
            "3. 요청사항 또는 전달사항 (있는 경우)\n\n",
            "간결하고 명확하게 작성해주세요."
        ])
        
        return "".join(prompt_parts)
    
    def process_outlook_emails(self, outlook_folder_path=None, date_filter=None):
        """
        Outlook 폴더의 모든 EML 파일을 하나씩 처리하여 요약 생성
        
        Args:
            outlook_folder_path (str): Outlook 폴더 경로 (사용하지 않음, 호환성 위해 유지)
            date_filter (str, optional): 날짜 필터 (YYYY-MM-DD 형식)
            
        Returns:
            list: 처리된 이메일 요약 배열
        """
        processed_summaries = []
        
        try:
            print(f"📂 Outlook 이메일 처리 시작: {OUTLOOK_FOLDER_PATH}")
            
            # EML 파일 찾기
            eml_files = self.find_eml_files()
            
            if not eml_files:
                print("⚠️ 처리할 EML 파일이 없습니다.")
                return processed_summaries
            
            print(f"📧 총 {len(eml_files)}개의 EML 파일을 순차적으로 처리합니다.")
            
            for index, eml_file in enumerate(eml_files, 1):
                try:
                    print(f"\n[{index}/{len(eml_files)}] 처리 중: {os.path.basename(eml_file)}")
                    
                    # 1. EML 파일 파싱
                    email_data = self.parse_eml_file(eml_file)
                    
                    # 2. 날짜 필터 적용 (옵션)
                    if date_filter and email_data['date']:
                        email_date = email_data['date'][:10]  # YYYY-MM-DD 부분만
                        if email_date < date_filter:
                            print(f"⏭️ 날짜 필터로 제외: {email_data['subject'][:30]}...")
                            continue
                    
                    # 3. 이메일 요약 생성 (하나씩 LLM 요청)
                    if email_data['body_clean'].strip():
                        print(f"🤖 LLM 요약 요청 중...")
                        summary = self.summarize_email(email_data)
                        
                        # 요약 결과를 배열에 추가 (발신자 제외, 간소화된 필드)
                        summary_item = {
                            'subject': email_data['subject'],
                            'to': email_data['to'],
                            'ai_summary': summary
                        }
                        processed_summaries.append(summary_item)
                        print(f"✅ 요약 완료 및 배열에 추가")
                    else:
                        print(f"⚠️ 본문이 비어있어 요약 생략")
                        summary_item = {
                            'subject': email_data['subject'],
                            'to': email_data['to'],
                            'ai_summary': "본문이 비어있거나 읽을 수 없습니다."
                        }
                        processed_summaries.append(summary_item)
                    
                except Exception as e:
                    print(f"❌ EML 파일 처리 오류 ({os.path.basename(eml_file)}): {e}")
                    # 오류가 있어도 다른 파일 계속 처리
                    error_item = {
                        'subject': "파싱 오류",
                        'to': "알 수 없음",
                        'ai_summary': f"처리 중 오류 발생: {str(e)}"
                    }
                    processed_summaries.append(error_item)
                    continue
            
            print(f"\n🎉 모든 이메일 처리 완료!")
            print(f"   - 총 처리된 파일: {len(processed_summaries)}개")
            print(f"   - 성공적으로 요약된 이메일: {len([s for s in processed_summaries if not s['ai_summary'].startswith('처리 중 오류')])}개")
            
            return processed_summaries
            
        except Exception as e:
            error_msg = f"이메일 처리 중 전체 오류: {e}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
    
    def save_email_summaries(self, processed_summaries, output_file="email_summaries.json"):
        """
        처리된 이메일 요약 배열을 JSON 파일로 저장
        
        Args:
            processed_summaries (list): 처리된 이메일 요약 배열
            output_file (str): 출력 파일명
            
        Returns:
            str: 저장된 파일 경로
        """
        try:
            # log 폴더 생성
            log_dir = "./log"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                print(f"📁 로그 폴더 생성: {log_dir}")
            
            # 파일 경로를 log 폴더로 설정
            output_path = os.path.join(log_dir, output_file)
            
            # JSON 파일로 저장 (이미 요약된 형태이므로 그대로 저장)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(processed_summaries, f, ensure_ascii=False, indent=2)
            
            print(f"💾 이메일 요약 저장 완료: {output_path}")
            print(f"   - 저장된 요약 개수: {len(processed_summaries)}개")
            return os.path.abspath(output_path)
            
        except Exception as e:
            raise Exception(f"이메일 요약 저장 중 오류: {e}")


def create_email_processor(llm_processor=None):
    """
    설정 파일에서 EmailProcessor 인스턴스 생성
    
    Args:
        llm_processor (LLMProcessor, optional): 외부 LLMProcessor 인스턴스
        
    Returns:
        EmailProcessor: 초기화된 EmailProcessor 인스턴스
    """
    try:
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        return EmailProcessor(config, llm_processor)
        
    except Exception as e:
        raise Exception(f"EmailProcessor 생성 중 오류 발생: {e}")


# 사용 예제
if __name__ == "__main__":
    # 예제 사용법
    try:
        # 설정 파일에서 EmailProcessor 생성
        processor = create_email_processor()
        
        # 최근 7일간의 이메일만 처리 (옵션)
        from datetime import datetime, timedelta
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        # 이메일 처리 (하나씩 순차적으로 LLM 요약 요청)
        print("📧 이메일 처리를 시작합니다...")
        summaries = processor.process_outlook_emails(date_filter=week_ago)
        
        if summaries:
            print(f"✅ 처리 성공! {len(summaries)}개 이메일 요약 완료")
            
            # 결과 저장
            output_file = processor.save_email_summaries(summaries)
            print(f"📄 저장 완료: {output_file}")
            
            # 요약 미리보기
            print(f"\n📋 요약 미리보기:")
            for i, summary in enumerate(summaries[:3], 1):  # 처음 3개만 미리보기
                print(f"\n[{i}] {summary['subject'][:50]}...")
                print(f"    수신자: {summary['to'][:50]}...")
                print(f"    요약: {summary['ai_summary'][:100]}...")
        else:
            print("⚠️ 처리할 이메일이 없습니다.")
            
    except Exception as e:
        print(f"❌ 오류: {e}")
