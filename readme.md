# DAS Worklog Extractor

업무 활동 추출 및 요약 도구 - Jira, Confluence, Gerrit에서 개인 활동을 수집하여 AI로 요약해주는 PyQt5 기반 GUI 애플리케이션

## 🚀 주요 기능

- **다중 플랫폼 데이터 수집**: Jira, Confluence, Gerrit(NA/EU/AS) 에서 최근 1일간의 개인 활동 자동 수집
- **AI 기반 요약**: Azure OpenAI GPT를 활용한 업무 활동 지능형 요약
- **GUI 인터페이스**: 사용자 친화적인 PyQt5 기반 데스크톱 애플리케이션
- **통합 타임라인**: 모든 플랫폼의 활동을 시간순으로 정렬한 통합 뷰
- **CSV 내보내기**: 수집된 데이터를 CSV 형식으로 저장

## 📋 요구사항

### 시스템 요구사항
- Python 3.7+
- Windows/macOS/Linux

### 필요한 패키지
```
openai>=1.0.0
PyQt5
requests
```

## 🛠️ 설치 방법

1. **저장소 클론**
```bash
git clone https://github.com/nakkasoft/das-worklog.git
cd das-worklog
```

2. **의존성 설치**
```bash
pip install -r requirements.txt
```

3. **설정 파일 구성**
`user_config.json` 파일을 수정하여 개인 API 토큰들을 설정:

```json
{
  "username": "your_sso_username",
  "azure_openai_endpoint": "https://your-endpoint.openai.azure.com/",
  "azure_openai_api_key": "your_azure_openai_api_key",
  "azure_openai_api_version": "2024-05-01-preview",
  "azure_openai_chat_deployment": "gpt-4",
  "jira_token": "your_jira_token",
  "confluence_token": "your_confluence_token",
  "gerrit_token_na": "your_gerrit_na_token",
  "gerrit_token_eu": "your_gerrit_eu_token",
  "gerrit_token_as": "your_gerrit_as_token"
}
```

## 🚦 사용 방법

### GUI 애플리케이션 실행
```bash
python worklog.py
```

### 명령행 스크립트 실행
```bash
python worklog_extractor.py
```

## 📂 프로젝트 구조

```
das-worklog/
├── worklog.py              # 메인 GUI 애플리케이션
├── worklog_extractor.py    # 데이터 수집 엔진
├── worklog.ui              # PyQt5 UI 디자인 파일
├── user_config.json        # 사용자 설정 파일
├── requirements.txt        # 의존성 목록
├── readme.md              # 프로젝트 문서
└── worklog_result.md      # AI 요약 결과 (생성됨)
```

## 🔧 주요 구성요소

### 1. worklog.py
- PyQt5 기반 메인 GUI 애플리케이션
- Azure OpenAI와의 연동
- 사용자 설정 관리
- 데이터 수집 및 AI 요약 프로세스 조율

### 2. worklog_extractor.py
- Jira, Confluence, Gerrit API 연동
- 개인 활동 데이터 수집 및 가공
- CSV 파일 생성
- 통합 활동 타임라인 생성

### 3. user_config.json
- API 토큰 및 엔드포인트 설정
- 사용자 개인화 설정

## 📊 수집 데이터 유형

### Jira
- 이슈 생성/업데이트
- 코멘트 작성
- 워크로그 기록
- 상태 변경

### Confluence
- 페이지 생성/편집
- 공간별 활동
- 최근 수정 내역

### Gerrit (NA/EU/AS)
- 코드 리뷰 생성
- 리뷰 댓글
- 코드 댓글
- 승인/거부 활동

## 🤖 AI 요약 기능

- **Azure OpenAI GPT** 모델 사용
- 수집된 활동 데이터를 자연어로 요약
- 업무 성과 및 주요 활동 하이라이트
- 프로젝트별, 시간대별 활동 분석

## ⚙️ 설정 가이드

### API 토큰 획득 방법

1. **Jira Token**: Atlassian 계정 설정에서 API 토큰 생성
2. **Confluence Token**: Confluence 개인 설정에서 API 키 생성  
3. **Gerrit Token**: 각 Gerrit 서버의 사용자 설정에서 HTTP 패스워드 생성
4. **Azure OpenAI**: Azure Portal에서 OpenAI 리소스 생성 후 키 획득

### 기본 URL 설정
```python
JIRA_BASE = "http://jira.lge.com/issue"
CONFLUENCE_BASE = "http://collab.lge.com/main"
GERRIT_URLS = {
    "NA": "http://vgit.lge.com/na",
    "EU": "http://vgit.lge.com/eu", 
    "AS": "http://vgit.lge.com/as"
}
```

## 🐛 문제 해결

### 자주 발생하는 문제

1. **설정 파일 오류**: `user_config.json` 파일 형식 확인
2. **API 토큰 만료**: 각 플랫폼에서 토큰 재생성
3. **네트워크 연결**: VPN 또는 회사 네트워크 설정 확인
4. **Qt 라이브러리 오류**: PyQt5 재설치

### 로그 확인
애플리케이션 실행 시 콘솔에 출력되는 로그를 통해 문제점 파악

## 📄 라이선스

이 프로젝트는 개인 및 기업 내부용으로 개발되었습니다.

## 👥 기여

버그 리포트나 기능 제안은 GitHub Issues를 통해 제출해주세요.

## 📝 변경 로그

### v1.0.0 (2024-09)
- 초기 릴리스
- Jira, Confluence, Gerrit 통합 지원
- Azure OpenAI 기반 AI 요약
- PyQt5 GUI 인터페이스

---

**개발자**: nakkasoft  
**저장소**: https://github.com/nakkasoft/das-worklog