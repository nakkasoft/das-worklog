# DAS WorkLog 애플리케이션 빌드 및 배포 가이드

## 📦 EXE 파일 빌드하기

### 1. 빌드 전 준비사항

#### 필수 요구사항
- Python 3.8 이상
- PyQt5
- PyInstaller
- 모든 종속성 패키지

#### 필수 파일 확인
다음 파일들이 프로젝트 디렉토리에 있는지 확인하세요:
```
📁 das-worklog/
├── worklog.py                    # 메인 애플리케이션
├── worklog.ui                    # UI 파일
├── settings.ui                   # 설정 UI 파일
├── Loading.gif                   # 로딩 애니메이션
├── worklog_extractor.py          # 데이터 수집 모듈
├── llm_processor.py              # LLM 처리 모듈
├── email_processor.py            # 이메일 처리 모듈
├── jira_uploader.py              # Jira 업로드 모듈
├── user_config.json              # 설정 파일
├── weekly_report_template.md     # 주간 보고서 템플릿
├── worklog.spec                  # PyInstaller 설정
├── build_exe.bat                 # Windows 빌드 스크립트
└── build_exe.sh                  # Linux/Mac 빌드 스크립트
```

### 2. 빌드 실행

#### Windows에서 빌드
```cmd
# 관리자 권한으로 명령 프롬프트 실행
cd d:\mysource\python\das-worklog
build_exe.bat
```

#### Linux/Mac에서 빌드
```bash
cd /path/to/das-worklog
chmod +x build_exe.sh
./build_exe.sh
```

#### 수동 빌드 (고급)
```bash
# 의존성 설치
pip install pyinstaller

# 빌드 실행
pyinstaller worklog.spec
```

### 3. 빌드 결과

빌드가 성공하면 다음과 같은 구조가 생성됩니다:

### 빌드된 dist 폴더 구조

빌드 스크립트(`build_exe.bat`)를 실행하면 다음과 같은 구조로 자동 생성됩니다:

```
📁 dist/
├── DAS_WorkLog.exe              # 실행 파일 (Windows)
├── user_config_template.json    # 설정 템플릿 (참고용)
├── templates/                   # 템플릿 폴더 (사용자 수정 가능)
│   ├── weekly_report_template.md
│   └── (기타 템플릿 파일들)
├── outlook/                     # 이메일 작업 폴더 (빈 폴더)
└── USER_GUIDE.md                # 사용자 가이드
```

**주요 특징:**
- **자동 파일 복사**: 빌드 시점에 필요한 모든 파일이 자동으로 dist 폴더에 복사됩니다
- **설정 파일 생성**: `user_config_template.json`이 `user_config.json`으로 복사되어 exe에 포함됩니다
- **원클릭 배포**: dist 폴더 전체를 복사하면 즉시 사용 가능합니다

## 🚀 배포하기

### 1. 배포 패키지 준비 (자동화됨)

빌드 스크립트가 자동으로 다음 작업을 수행합니다:

```
📁 DAS_WorkLog_배포패키지/ (= dist 폴더)
├── DAS_WorkLog.exe              # 실행 파일
├── user_config_template.json    # 설정 템플릿 (참고용)
├── templates/                   # 템플릿 폴더 (사용자가 수정 가능)
│   ├── weekly_report_template.md
│   └── (기타 템플릿 파일들)
├── outlook/                     # 이메일 작업 폴더 (빈 폴더)
└── USER_GUIDE.md                # 사용자 가이드 문서
```

### 2. 대상 컴퓨터에서 설정

#### 2.1 파일 복사
**dist 폴더 전체를 대상 컴퓨터에 복사**하면 됩니다. 모든 필요한 파일이 이미 포함되어 있습니다.

#### 2.2 설정 파일 구성
빌드 시점에 이미 `user_config.json`이 생성되어 exe에 포함되어 있습니다.
**추가 작업 불필요** - 바로 다음 단계로 진행하세요.

#### 2.3 API 키 설정
exe와 같은 디렉토리에 있는 `user_config.json` 파일을 열어 실제 값으로 교체:

**참고:** `user_config_template.json` 파일이 참고용으로 제공됩니다.

```json
{
  "username": "actual_username",
  "azure_openai_api_key": "actual_azure_key",
  "jira_token": "actual_jira_token",
  "confluence_token": "actual_confluence_token",
  "gerrit_token_na": "actual_gerrit_na_token",
  "gerrit_token_eu": "actual_gerrit_eu_token",
  "gerrit_token_as": "actual_gerrit_as_token"
}
```

### 3. 실행
```bash
# Windows
DAS_WorkLog.exe

# Linux/Mac
./DAS_WorkLog
```

## ⚠️ 문제 해결

### 빌드 오류 해결

#### 1. 모듈 누락 오류
```
ModuleNotFoundError: No module named 'xxx'
```
**해결방법:**
```bash
pip install 누락된_모듈명
```

#### 2. UI 파일 누락
```
FileNotFoundError: worklog.ui
```
**해결방법:**
- `worklog.ui` 파일이 프로젝트 디렉토리에 있는지 확인
- Qt Designer로 다시 생성

#### 3. PyInstaller 오류
```bash
# PyInstaller 재설치
pip uninstall pyinstaller
pip install pyinstaller
```

### 실행 오류 해결

#### 1. 설정 파일 오류
```
설정 파일을 찾을 수 없습니다
```
**해결방법:**
- `user_config.json` 파일이 실행 파일과 같은 폴더에 있는지 확인
- 파일 권한 확인

#### 2. API 인증 오류
```
Jira 데이터 수집 오류
```
**해결방법:**
- API 토큰이 올바른지 확인
- 네트워크 연결 확인
- VPN/방화벽 설정 확인

#### 3. 권한 오류
```bash
# Windows: 관리자 권한으로 실행
# Linux/Mac: 실행 권한 부여
chmod +x DAS_WorkLog
```

## 🔧 고급 설정

### 파일 처리 방식

#### exe 내부에 포함되는 파일들 (읽기 전용)
- `worklog.ui`, `settings.ui` (UI 파일들)
- `Loading.gif` (로딩 애니메이션)
- 기타 정적 리소스들

#### exe 외부에서 읽는 파일들 (사용자 편집 가능)
- `user_config.json` (설정 파일 - 사용자가 편집 필요)
- `templates/` 폴더 (템플릿 파일들 - 사용자가 수정 가능)
- 생성되는 로그 파일들
- 생성되는 보고서 파일들

**장점:**
- UI 파일들은 사용자가 실수로 삭제할 수 없음
- 설정 파일과 템플릿은 사용자가 언제든 편집 가능
- 개발/배포 환경에서 동일하게 작동

### 아이콘 추가
```python
# worklog.spec 파일에서
exe = EXE(
    ...
    icon='icon.ico',  # 아이콘 파일 경로
    ...
)
```

### 콘솔 창 표시/숨김
```python
# worklog.spec 파일에서
exe = EXE(
    ...
    console=True,   # 콘솔 표시
    console=False,  # 콘솔 숨김 (GUI 앱)
    ...
)
```

### 파일 압축 최적화
```python
# worklog.spec 파일에서
exe = EXE(
    ...
    upx=True,       # UPX 압축 사용
    strip=False,    # 디버그 정보 유지
    ...
)
```

## 📋 체크리스트

### 빌드 전 체크리스트
- [ ] Python 환경 설정 완료
- [ ] 모든 종속성 패키지 설치
- [ ] 필수 파일들 존재 확인
- [ ] UI 파일들 정상 작동 확인
- [ ] 설정 파일 템플릿 준비

### 배포 전 체크리스트
- [ ] EXE 파일 정상 빌드 확인
- [ ] 테스트 환경에서 실행 확인
- [ ] 설정 파일 템플릿 포함
- [ ] 사용자 가이드 문서 포함
- [ ] 모든 템플릿 파일 포함

### 사용자 설치 체크리스트
- [ ] 배포 패키지 다운로드
- [ ] 파일 압축 해제
- [ ] user_config.json 설정
- [ ] API 키 입력
- [ ] 첫 실행 테스트

## 📞 지원

문제가 발생하면 다음 정보와 함께 문의하세요:
- 운영체제 정보
- Python 버전
- 오류 메시지 전체
- 실행 환경 (네트워크, VPN 등)

## 📝 업데이트 방법

새 버전 배포 시:
1. 기존 실행 파일 백업
2. 새 EXE 파일로 교체
3. user_config.json 설정 유지
4. 새로운 템플릿 파일 확인
