# -*- mode: python ; coding: utf-8 -*-

import os
import sys

# 현재 디렉토리 설정
current_dir = os.path.dirname(os.path.abspath('worklog.py'))

block_cipher = None

# 데이터 파일들 수집 (templates 폴더는 외부에서 읽도록 제외)
datas = [
    ('worklog.ui', '.'),  # UI 파일
    ('settings.ui', '.'),  # 설정 UI 파일
    ('Loading.gif', '.'),  # 로딩 애니메이션
]

# 선택적으로 포함할 파일들 (존재하는 경우에만)
optional_files = [
    'BUILD_DEPLOY_GUIDE.md',
    'requirements.txt',
    'user_config_template.json'
]

for file in optional_files:
    if os.path.exists(file):
        datas.append((file, '.'))

# 히든 임포트 설정
hiddenimports = [
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtWidgets',
    'PyQt5.QtGui',
    'requests',
    'openai',
    'json',
    'datetime',
    'email',
    'email.mime',
    'email.mime.text',
    'email.mime.multipart',
    'smtplib',
    'imaplib',
    'ssl',
    'base64',
    'quopri',
    'html2text',
    'chardet',
    'worklog_extractor',
    'llm_processor',
    'email_processor',
    'jira_uploader'
]

a = Analysis(
    ['worklog.py'],
    pathex=[current_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DAS_WorkLog',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI 앱이므로 콘솔 창 숨김
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 아이콘 파일이 있다면 경로 지정
)
