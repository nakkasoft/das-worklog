import os
import sys
import csv
import time
import datetime as dt
import requests
from requests.auth import HTTPBasicAuth
import json

# UTF-8 인코딩 설정
import codecs
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 시스템별 기본 URL 설정
JIRA_BASE = "http://jira.lge.com/issue"
CONFLUENCE_BASE = "http://collab.lge.com/main"
GERRIT_URLS = {
    "NA": "http://vgit.lge.com/na",
    "EU": "http://vgit.lge.com/eu", 
    "AS": "http://vgit.lge.com/as"
}

# 시간 설정
NOW_UTC = dt.datetime.now(dt.UTC).replace(tzinfo=None)
SINCE = NOW_UTC - dt.timedelta(days=3)  # 3일로 설정하여 적절한 수의 티켓 분석

def iso_to_dt(s):
    """시간 문자열을 datetime 객체로 변환"""
    try:
        if s.endswith("Z"):
            return dt.datetime.fromisoformat(s.replace("Z","+00:00")).replace(tzinfo=None)
        if "+" in s and s[-5] in ["+", "-"] and s[-3] != ":":
            s = s[:-5] + s[-5:-2] + ":" + s[-2:]
        # Gerrit 시간 형식: "2025-09-18 02:47:20.000000000"
        if "." in s and len(s.split(".")[-1]) > 6:
            # 나노초를 마이크로초로 변환
            parts = s.split(".")
            microseconds = parts[1][:6]
            s = f"{parts[0]}.{microseconds}"
        return dt.datetime.fromisoformat(s).replace(tzinfo=None)
    except Exception as e:
        # Gerrit 시간 형식 처리
        try:
            return dt.datetime.strptime(s.split(".")[0], "%Y-%m-%d %H:%M:%S")
        except:
            return None

def extract_text_from_adf(adf_content):
    """
    Atlassian Document Format(ADF)에서 텍스트를 추출
    
    Args:
        adf_content (dict): ADF 형식의 콘텐츠
        
    Returns:
        str: 추출된 텍스트
    """
    if not adf_content or not isinstance(adf_content, dict):
        return ""
    
    def extract_text_recursive(node):
        """ADF 노드에서 재귀적으로 텍스트 추출"""
        text_parts = []
        
        if isinstance(node, dict):
            # 텍스트 노드인 경우
            if node.get("type") == "text":
                text_parts.append(node.get("text", ""))
            
            # 다른 노드 타입들 처리
            elif node.get("type") in ["paragraph", "heading", "bulletList", "orderedList", "listItem"]:
                if "content" in node:
                    for child in node["content"]:
                        text_parts.append(extract_text_recursive(child))
            
            # hardBreak는 줄바꿈으로 처리
            elif node.get("type") == "hardBreak":
                text_parts.append("\n")
                
        elif isinstance(node, list):
            for item in node:
                text_parts.append(extract_text_recursive(item))
        
        return " ".join(text_parts)
    
    try:
        # ADF의 최상위 content에서 텍스트 추출
        if "content" in adf_content:
            extracted = extract_text_recursive(adf_content["content"])
            return extracted.strip()
        else:
            return str(adf_content).strip()
    except Exception as e:
        # ADF 파싱 실패시 원본을 문자열로 반환
        return str(adf_content)[:500]  # 길이 제한

# =============================================================================
# JIRA 데이터 수집 함수
# =============================================================================

def get_jira_issue_details(username, token, issue_key):
    """
    특정 Jira 이슈의 상세 정보와 댓글을 가져오기
    
    Args:
        username (str): Jira 사용자명
        token (str): Jira API 토큰
        issue_key (str): Jira 이슈 키 (예: CLUSTWORK-16153)
        
    Returns:
        dict: 이슈 상세 정보 (댓글 포함)
    """
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    try:
        # 이슈 기본 정보 가져오기
        url = f"{JIRA_BASE}/rest/api/2/issue/{issue_key}"
        params = {
            "expand": "changelog,comments,worklog,attachments"
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        issue_data = response.json()
        
        # 댓글 정보 추출
        comments = []
        if "comments" in issue_data.get("fields", {}):
            for comment in issue_data["fields"]["comments"]["comments"]:
                comment_info = {
                    "author": comment.get("author", {}).get("displayName", "Unknown"),
                    "created": comment.get("created", ""),
                    "updated": comment.get("updated", ""),
                    "body": comment.get("body", "")
                }
                # ADF 형태인 경우 텍스트 추출
                if isinstance(comment_info["body"], dict):
                    comment_info["body"] = extract_text_from_adf(comment_info["body"])
                comments.append(comment_info)
        
        # 워크로그 정보 추출
        worklogs = []
        if "worklog" in issue_data.get("fields", {}):
            for worklog in issue_data["fields"]["worklog"]["worklogs"]:
                worklog_info = {
                    "author": worklog.get("author", {}).get("displayName", "Unknown"),
                    "created": worklog.get("created", ""),
                    "updated": worklog.get("updated", ""),
                    "timeSpent": worklog.get("timeSpent", ""),
                    "comment": worklog.get("comment", "")
                }
                # ADF 형태인 경우 텍스트 추출
                if isinstance(worklog_info["comment"], dict):
                    worklog_info["comment"] = extract_text_from_adf(worklog_info["comment"])
                worklogs.append(worklog_info)
        
        # 첨부파일 정보 추출
        attachments = []
        if "attachment" in issue_data.get("fields", {}):
            for attachment in issue_data["fields"]["attachment"]:
                attachments.append({
                    "filename": attachment.get("filename", ""),
                    "author": attachment.get("author", {}).get("displayName", "Unknown"),
                    "created": attachment.get("created", ""),
                    "size": attachment.get("size", 0)
                })
        
        # 변경 이력 추출
        changelog = []
        if "changelog" in issue_data:
            for history in issue_data["changelog"]["histories"]:
                for item in history.get("items", []):
                    changelog.append({
                        "author": history.get("author", {}).get("displayName", "Unknown"),
                        "created": history.get("created", ""),
                        "field": item.get("field", ""),
                        "fieldtype": item.get("fieldtype", ""),
                        "from": item.get("fromString", ""),
                        "to": item.get("toString", "")
                    })
        
        # 통합 상세 정보 반환
        fields = issue_data.get("fields", {})
        
        # description 필드 안전 처리
        description = ""
        description_field = fields.get("description")
        if description_field:
            if isinstance(description_field, str):
                description = description_field
            elif isinstance(description_field, dict):
                description = extract_text_from_adf(description_field)
        
        detailed_issue = {
            "key": issue_data.get("key", ""),
            "summary": fields.get("summary", ""),
            "description": description,
            "status": fields.get("status", {}).get("name", "Unknown"),
            "assignee": fields.get("assignee", {}).get("displayName", "Unassigned") if fields.get("assignee") else "Unassigned",
            "reporter": fields.get("reporter", {}).get("displayName", "Unknown") if fields.get("reporter") else "Unknown",
            "priority": fields.get("priority", {}).get("name", "Unknown") if fields.get("priority") else "Unknown",
            "created": fields.get("created", ""),
            "updated": fields.get("updated", ""),
            "resolutiondate": fields.get("resolutiondate", ""),
            "comments": comments,
            "worklogs": worklogs,
            "attachments": attachments,
            "changelog": changelog,
            "url": f"{JIRA_BASE}/browse/{issue_data.get('key', '')}"
        }
        
        return detailed_issue
        
    except Exception as e:
        print(f"❌ Jira 이슈 상세 정보 가져오기 실패 ({issue_key}): {e}")
        return None

def collect_jira_data(username, token, excluded_issues=None):
    """
    Jira 데이터 수집
    
    Args:
        username (str): Jira 사용자명
        token (str): Jira API 토큰
        excluded_issues (list, optional): 분석에서 제외할 이슈 키 목록
        
    Returns:
        list: Jira 활동 데이터 리스트
    """
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    if excluded_issues is None:
        excluded_issues = []
    
    try:
        # 사용자 ID 가져오기
        r = requests.get(f"{JIRA_BASE}/rest/api/2/myself", headers=headers)
        r.raise_for_status()
        user_data = r.json()
        
        # 최근 3일간의 활동 검색 (적절한 범위로 조정)
        jql = "(updated >= -7d) AND (assignee = currentUser() OR reporter = currentUser() OR comment ~ currentUser() OR worklogAuthor = currentUser())"
        #jql = "Key = CLUSTWORK-16128"
        
        params = {
            "jql": jql,
            "fields": "key,summary,updated,status,assignee,reporter,created,description",
            "maxResults": 500
        }
        
        r = requests.get(f"{JIRA_BASE}/rest/api/2/search", headers=headers, params=params)
        r.raise_for_status()
        
        # JSON 응답 검증
        try:
            data = r.json()
        except json.JSONDecodeError:
            print(f"❌ Jira API 응답이 올바른 JSON 형식이 아닙니다: {r.text[:200]}")
            return []
        
        # 응답 구조 검증
        if not isinstance(data, dict):
            print(f"❌ Jira API 응답이 딕셔너리가 아닙니다: {type(data)}")
            return []
        
        # issues 필드 검증
        if "issues" not in data:
            print(f"❌ Jira API 응답에 'issues' 필드가 없습니다. 사용 가능한 키: {list(data.keys())}")
            return []
        
        issues = data.get("issues", [])
        
        # issues가 리스트인지 확인
        if not isinstance(issues, list):
            print(f"❌ 'issues' 필드가 리스트가 아닙니다: {type(issues)}")
            return []
        
        print(f"✅ Jira에서 {len(issues)}개의 이슈를 가져왔습니다.")
        
        activities = []
        excluded_count = 0
        
        for issue in issues:
            try:
                # 이슈 키 확인
                issue_key = issue.get("key", "")
                
                # 제외 대상 이슈인지 확인
                if issue_key in excluded_issues:
                    excluded_count += 1
                    fields = issue.get("fields", {})
                    summary = fields.get("summary", "")[:50]
                    print(f"⏭️ 분석 제외: {issue_key} - {summary}...")
                    continue
                
                # 기본 필드들 안전하게 가져오기
                fields = issue.get("fields", {})
                if not fields:
                    continue
                
                # 시간 필드 처리
                updated_str = fields.get("updated")
                created_str = fields.get("created")
                
                if not updated_str:
                    continue
                    
                updated_dt = iso_to_dt(updated_str)
                created_dt = iso_to_dt(created_str) if created_str else None
                
                if updated_dt and updated_dt >= SINCE:
                    print(f"🔍 {issue_key} 상세 정보 수집 중...")
                    
                    # 이슈 상세 정보 가져오기 (댓글, 워크로그 등 포함)
                    detailed_issue = get_jira_issue_details(username, token, issue_key)
                    
                    if detailed_issue:
                        # 상세 정보가 있는 경우 이를 활동 목록에 추가
                        activities.append({
                            "source": "jira",
                            "type": "detailed_issue",
                            "issue_key": detailed_issue["key"],
                            "summary": detailed_issue["summary"],
                            "description": detailed_issue["description"],
                            "status": detailed_issue["status"],
                            "assignee": detailed_issue["assignee"],
                            "reporter": detailed_issue["reporter"],
                            "priority": detailed_issue["priority"],
                            "created": detailed_issue["created"],
                            "updated": detailed_issue["updated"],
                            "resolutiondate": detailed_issue["resolutiondate"],
                            "comments": detailed_issue["comments"],
                            "worklogs": detailed_issue["worklogs"],
                            "attachments": detailed_issue["attachments"],
                            "changelog": detailed_issue["changelog"],
                            "url": detailed_issue["url"],
                            "comment_count": len(detailed_issue["comments"]),
                            "worklog_count": len(detailed_issue["worklogs"]),
                            "attachment_count": len(detailed_issue["attachments"])
                        })
                        
                        print(f"✅ {issue_key} 상세 정보 수집 완료 (댓글: {len(detailed_issue['comments'])}개, 워크로그: {len(detailed_issue['worklogs'])}개)")
                    else:
                        # 상세 정보 가져오기 실패한 경우 기본 정보만 추가
                        print(f"⚠️ {issue_key} 상세 정보 수집 실패, 기본 정보만 사용")
                        
                        # description 필드 안전하게 처리
                        description = ""
                        description_field = fields.get("description")
                        if description_field:
                            if isinstance(description_field, str):
                                description = description_field
                            elif isinstance(description_field, dict):
                                # ADF(Atlassian Document Format) 형식인 경우 텍스트 추출
                                description = extract_text_from_adf(description_field)
                        
                        # assignee 안전 처리
                        assignee_info = fields.get("assignee")
                        if assignee_info is None:
                            assignee_name = "Unassigned"
                        else:
                            assignee_name = assignee_info.get("displayName", "Unknown") if isinstance(assignee_info, dict) else "Unknown"
                        
                        # reporter 안전 처리
                        reporter_info = fields.get("reporter")
                        if reporter_info is None:
                            reporter_name = "Unknown"
                        else:
                            reporter_name = reporter_info.get("displayName", "Unknown") if isinstance(reporter_info, dict) else "Unknown"
                        
                        # status 필드 안전 처리
                        status_info = fields.get("status")
                        if status_info is None:
                            status_name = "Unknown"
                        else:
                            status_name = status_info.get("name", "Unknown") if isinstance(status_info, dict) else "Unknown"
                        
                        # summary 필드 안전 처리
                        summary = fields.get("summary", "No Summary")
                        
                        activities.append({
                            "source": "jira",
                            "type": "basic_issue",
                            "issue_key": issue_key,
                            "summary": summary,
                            "description": description,
                            "status": status_name,
                            "assignee": assignee_name,
                            "reporter": reporter_name,
                            "created": created_str or "Unknown",
                            "updated": updated_str,
                            "url": f"{JIRA_BASE}/browse/{issue_key}",
                            "comments": [],
                            "worklogs": [],
                            "attachments": [],
                            "changelog": [],
                            "comment_count": 0,
                            "worklog_count": 0,
                            "attachment_count": 0
                        })
                    
            except Exception as e:
                print(f"⚠️ 이슈 처리 중 오류 (키: {issue.get('key', 'Unknown')}): {e}")
                continue
        
        if excluded_count > 0:
            print(f"📊 Jira 분석 결과: {len(activities)}개 포함, {excluded_count}개 제외")
        
        return activities
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Jira 네트워크 요청 오류: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Jira JSON 디코딩 오류: {e}")
        return []
    except KeyError as e:
        print(f"❌ Jira 응답에서 필수 필드 누락: {e}")
        return []
    except Exception as e:
        print(f"❌ Jira 데이터 수집 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        return []

# =============================================================================
# CONFLUENCE 데이터 수집 함수
# =============================================================================

def collect_confluence_data(username, token):
    """
    Confluence 데이터 수집
    
    Args:
        username (str): Confluence 사용자명
        token (str): Confluence API 토큰
        
    Returns:
        list: Confluence 활동 데이터 리스트
    """
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    try:
        since_str = SINCE.strftime("%Y-%m-%d")
        params = {
            "cql": f"contributor = currentUser() AND lastModified >= '{since_str}'",
            "limit": 500
        }
        
        r = requests.get(f"{CONFLUENCE_BASE}/rest/api/content/search", headers=headers, params=params)
        r.raise_for_status()
        data = r.json()
        
        activities = []
        for page in data.get("results", []):
            activities.append({
                "source": "confluence",
                "type": "page_activity", 
                "page_id": page["id"],
                "title": page["title"],
                "space": page.get("space", {}).get("name", ""),
                "space_key": page.get("space", {}).get("key", ""),
                "last_modified": page.get("version", {}).get("when", ""),
                "url": f"{CONFLUENCE_BASE}/pages/viewpage.action?pageId={page['id']}"
            })
        
        return activities
        
    except Exception as e:
        print(f"❌ Confluence 데이터 수집 오류: {e}")
        return []

# =============================================================================
# GERRIT 데이터 수집 함수
# =============================================================================

def collect_gerrit_data(username, tokens):
    """
    Gerrit 데이터 수집 (모든 서버)
    
    Args:
        username (str): Gerrit 사용자명
        tokens (dict): 서버별 Gerrit 토큰 딕셔너리 {"NA": "token1", "EU": "token2", "AS": "token3"}
        
    Returns:
        tuple: (reviews, comments) - 리뷰 데이터와 댓글 데이터
    """
    all_reviews = []
    all_comments = []
    
    for server, token in tokens.items():
        if server not in GERRIT_URLS:
            continue
            
        try:
            reviews, comments = collect_gerrit_server_data(username, token, server)
            all_reviews.extend(reviews)
            all_comments.extend(comments)
        except Exception as e:
            print(f"❌ Gerrit {server} 서버 데이터 수집 오류: {e}")
    
    return all_reviews, all_comments

def collect_gerrit_server_data(username, token, server="NA"):
    """
    특정 Gerrit 서버에서 데이터 수집
    
    Args:
        username (str): Gerrit 사용자명
        token (str): Gerrit API 토큰
        server (str): 서버 이름 (NA, EU, AS)
        
    Returns:
        tuple: (reviews, comments) - 해당 서버의 리뷰 데이터와 댓글 데이터
    """
    auth = HTTPBasicAuth(username, token)
    base_url = GERRIT_URLS[server]
    
    all_reviews = []
    all_comments = []
    
    # 최근 1일간의 검색 쿼리들
    since_str = SINCE.strftime("%Y-%m-%d")
    queries = [
        f"owner:{username} after:{since_str}",  # 내가 작성한 리뷰
        f"reviewer:{username} after:{since_str}",  # 내가 리뷰한 것들
        f"commentby:{username} after:{since_str}"  # 내가 댓글 단 것들
    ]
    
    processed_changes = set()  # 중복 방지
    
    for query in queries:
        try:
            changes = search_gerrit_changes(auth, base_url, query, limit=500)
            
            for change in changes:
                change_id = change.get("id", "")
                if change_id in processed_changes:
                    continue
                processed_changes.add(change_id)
                
                change_number = change.get("_number", "")
                subject = change.get("subject", "")
                status = change.get("status", "")
                owner = change.get("owner", {})
                created = change.get("created", "")
                updated = change.get("updated", "")
                project = change.get("project", "")
                branch = change.get("branch", "")
                
                # 시간 필터링
                updated_dt = iso_to_dt(updated)
                if not updated_dt or updated_dt < SINCE:
                    continue
                
                # 내가 소유자인 경우 (내가 작성한 리뷰)
                owner_username = owner.get("username", owner.get("name", ""))
                if owner_username == username:
                    all_reviews.append({
                        "source": f"gerrit_{server.lower()}",
                        "type": "review_created",
                        "change_id": change_id,
                        "change_number": change_number,
                        "subject": subject,
                        "status": status,
                        "project": project,
                        "branch": branch,
                        "created": created,
                        "updated": updated,
                        "url": f"{base_url}/c/{change_number}"
                    })
                
                # 메시지 확인 (내 댓글)
                messages = change.get("messages", [])
                for message in messages:
                    author = message.get("author", {})
                    author_username = author.get("username", author.get("name", ""))
                    message_date = message.get("date", "")
                    
                    if author_username == username:
                        message_dt = iso_to_dt(message_date)
                        if message_dt and message_dt >= SINCE:
                            all_comments.append({
                                "source": f"gerrit_{server.lower()}",
                                "type": "review_comment",
                                "change_id": change_id,
                                "change_number": change_number,
                                "subject": subject,
                                "project": project,
                                "message": message.get("message", ""),
                                "created": message_date,
                                "url": f"{base_url}/c/{change_number}"
                            })
                
                # 상세 댓글 가져오기
                try:
                    detailed_comments = get_gerrit_comments(auth, base_url, change_id)
                    
                    for file_path, comments_list in detailed_comments.items():
                        for comment in comments_list:
                            author = comment.get("author", {})
                            author_username = author.get("username", author.get("name", ""))
                            comment_updated = comment.get("updated", "")
                            
                            if author_username == username:
                                comment_dt = iso_to_dt(comment_updated)
                                if comment_dt and comment_dt >= SINCE:
                                    all_comments.append({
                                        "source": f"gerrit_{server.lower()}",
                                        "type": "code_comment",
                                        "change_id": change_id,
                                        "change_number": change_number,
                                        "subject": subject,
                                        "project": project,
                                        "file_path": file_path,
                                        "line": comment.get("line", ""),
                                        "message": comment.get("message", ""),
                                        "created": comment_updated,
                                        "url": f"{base_url}/c/{change_number}"
                                    })
                except Exception as e:
                    print(f"    ⚠️ {change_id} 상세 댓글 오류: {e}")
                
                time.sleep(0.1)  # API 부하 방지
                
        except Exception as e:
            print(f"  ⚠️ 쿼리 '{query}' 오류: {e}")
    
    return all_reviews, all_comments

def gerrit_request(url, auth, params=None):
    """Gerrit API 요청"""
    try:
        response = requests.get(url, auth=auth, params=params, timeout=30)
        
        # Gerrit은 보안상 ")]}'" 접두사를 응답에 추가함
        text = response.text
        if text.startswith(")]}'\n"):
            text = text[5:]
        
        response.raise_for_status()
        
        # UTF-8 인코딩 확인
        if response.encoding:
            response.encoding = 'utf-8'
        
        return json.loads(text) if text.strip() else []
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Gerrit 요청 오류: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON 파싱 오류: {e}")
        return []

def search_gerrit_changes(auth, base_url, query, limit=1000):
    """Gerrit에서 변경사항 검색"""
    url = f"{base_url}/a/changes/"
    params = {
        "q": query,
        "o": ["DETAILED_ACCOUNTS", "DETAILED_LABELS", "MESSAGES", "CURRENT_REVISION"],
        "n": limit
    }
    
    print(f"  Gerrit 검색: {query}")
    return gerrit_request(url, auth, params)

def get_gerrit_comments(auth, base_url, change_id):
    """특정 변경사항의 댓글 가져오기"""
    url = f"{base_url}/a/changes/{change_id}/comments"
    return gerrit_request(url, auth)

# =============================================================================
# 데이터 가공 및 분석 함수
# =============================================================================

def process_activity_data(jira_data, confluence_data, gerrit_reviews, gerrit_comments):
    """
    수집된 데이터를 가공하여 통합 활동 타임라인 생성
    
    Args:
        jira_data (list): Jira 활동 데이터
        confluence_data (list): Confluence 활동 데이터
        gerrit_reviews (list): Gerrit 리뷰 데이터
        gerrit_comments (list): Gerrit 댓글 데이터
        
    Returns:
        list: 통합된 활동 타임라인 데이터
    """
    all_activities = []
    
    # Jira 활동 변환
    for activity in jira_data:
        # description이 길면 일부만 표시
        description_preview = activity.get("description", "")
        if len(description_preview) > 100:
            description_preview = description_preview[:100] + "..."
        
        all_activities.append({
            "timestamp": activity["updated"],
            "source": "JIRA",
            "type": "이슈 활동",
            "reference": activity["issue_key"],
            "description": f"[{activity['status']}] {activity['summary']}",
            "content": description_preview if description_preview else activity["url"],
            "full_description": activity.get("description", ""),  # 전체 설명 보관
            "raw_data": activity
        })
    
    # Confluence 활동 변환
    for activity in confluence_data:
        all_activities.append({
            "timestamp": activity.get("last_modified", dt.datetime.now().isoformat()),
            "source": "CONFLUENCE",
            "type": "페이지 활동",
            "reference": activity["page_id"],
            "description": f"{activity['space']}: {activity['title']}",
            "content": activity["url"],
            "raw_data": activity
        })
    
    # Gerrit 리뷰 변환
    for review in gerrit_reviews:
        all_activities.append({
            "timestamp": review["updated"],
            "source": review["source"].upper(),
            "type": "코드리뷰 생성",
            "reference": f"{review['project']}#{review['change_number']}",
            "description": f"[{review['status']}] {review['subject']}",
            "content": review["url"],
            "raw_data": review
        })
    
    # Gerrit 댓글 변환
    for comment in gerrit_comments:
        comment_type = "코드 댓글" if comment["type"] == "code_comment" else "리뷰 댓글"
        all_activities.append({
            "timestamp": comment["created"],
            "source": comment["source"].upper(),
            "type": comment_type,
            "reference": f"{comment['project']}#{comment['change_number']}",
            "description": f"{comment['subject']}",
            "content": comment["message"][:100] + "..." if len(comment["message"]) > 100 else comment["message"],
            "raw_data": comment
        })
    
    # 시간순 정렬
    all_activities.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return all_activities

def generate_activity_summary(activities):
    """
    활동 데이터 요약 생성
    
    Args:
        activities (list): 활동 데이터 리스트
        
    Returns:
        dict: 활동 요약 정보
    """
    summary = {
        "total_activities": len(activities),
        "by_source": {},
        "by_type": {},
        "date_range": {
            "start": None,
            "end": None
        }
    }
    
    dates = []
    for activity in activities:
        # 소스별 카운트
        source = activity["source"]
        summary["by_source"][source] = summary["by_source"].get(source, 0) + 1
        
        # 타입별 카운트
        activity_type = activity["type"]
        summary["by_type"][activity_type] = summary["by_type"].get(activity_type, 0) + 1
        
        # 날짜 수집
        try:
            date = iso_to_dt(activity["timestamp"])
            if date:
                dates.append(date)
        except:
            pass
    
    # 날짜 범위 설정
    if dates:
        dates.sort()
        summary["date_range"]["start"] = dates[0].strftime("%Y-%m-%d")
        summary["date_range"]["end"] = dates[-1].strftime("%Y-%m-%d")
    
    return summary

# =============================================================================
# 유틸리티 함수들
# =============================================================================

def write_csv(path, headers, rows):
    """CSV 파일 작성 (UTF-8 BOM 포함) - log 폴더에 저장"""
    # log 폴더 생성
    log_dir = "./log"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        print(f"📁 로그 폴더 생성: {log_dir}")
    
    # 파일 경로를 log 폴더로 설정
    log_path = os.path.join(log_dir, os.path.basename(path))
    
    with open(log_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow({h: r.get(h, "") for h in headers})
    print(f"✓ {log_path} 작성 완료 ({len(rows)}개 행)")

# =============================================================================
# 메인 실행 함수 (예제)
# =============================================================================

def main():
    """
    메인 실행 함수 - 실제 토큰과 사용자명으로 수정하여 사용
    """
    print("=== Jira & Confluence & Gerrit 통합 활동 추출기 ===")
    print(f"수집 기간: 최근 3일 ({SINCE.strftime('%Y-%m-%d')} 이후)")
    
    # 실제 사용자 정보 설정 (여기서 수정하여 사용)
    USERNAME = ""
    JIRA_TOKEN = ""
    CONFLUENCE_TOKEN = ""
    GERRIT_TOKENS = {
        "NA": "",
        "EU": "",
        "AS": ""
    }
    
    # user_config.json에서 제외할 이슈 목록 읽기
    excluded_issues = []
    try:
        with open("user_config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            master_jira = config.get("master_jira", "")
            if master_jira:
                # master_jira를 제외 목록에 추가
                excluded_issues.append(master_jira)
                print(f"📋 제외 대상 마스터 이슈: {master_jira}")
                
                # TODO: 나중에 Jira API를 통해 master_jira의 subtask들도 가져와서 제외 목록에 추가
                # (현재는 master_jira만 제외)
                
    except Exception as e:
        print(f"⚠️ user_config.json 읽기 실패: {e}")
    
    # 1. 각 시스템에서 데이터 수집
    print("\n=== 데이터 수집 ===")
    
    print("JIRA 데이터 수집 중...")
    jira_data = collect_jira_data(USERNAME, JIRA_TOKEN, excluded_issues)
    print(f"✓ Jira 활동: {len(jira_data)}개")
    
    print("Confluence 데이터 수집 중...")
    confluence_data = collect_confluence_data(USERNAME, CONFLUENCE_TOKEN)
    print(f"✓ Confluence 활동: {len(confluence_data)}개")
    
    print("Gerrit 데이터 수집 중...")
    gerrit_reviews, gerrit_comments = collect_gerrit_data(USERNAME, GERRIT_TOKENS)
    print(f"✓ Gerrit 리뷰: {len(gerrit_reviews)}개")
    print(f"✓ Gerrit 댓글: {len(gerrit_comments)}개")
    
    # 2. 데이터 가공
    print("\n=== 데이터 가공 ===")
    integrated_activities = process_activity_data(jira_data, confluence_data, gerrit_reviews, gerrit_comments)
    activity_summary = generate_activity_summary(integrated_activities)
    
    print(f"통합 활동: {activity_summary['total_activities']}개")
    print("소스별 활동:")
    for source, count in activity_summary['by_source'].items():
        print(f"  - {source}: {count}개")
    
    # 3. CSV 파일 출력
    print("\n=== 파일 출력 ===")
    
    # Gerrit 리뷰 CSV
    if gerrit_reviews:
        write_csv("gerrit_reviews.csv",
                  ["source", "type", "change_id", "change_number", "subject", "status", "project", "branch", "created", "updated", "url"],
                  gerrit_reviews)
    
    # Gerrit 댓글 CSV
    if gerrit_comments:
        write_csv("gerrit_comments.csv",
                  ["source", "type", "change_id", "change_number", "subject", "project", "file_path", "line", "message", "created", "url"],
                  gerrit_comments)
    
    # 통합 활동 타임라인 CSV
    write_csv("integrated_activity_timeline.csv",
              ["timestamp", "source", "type", "reference", "description", "content", "full_description"],
              integrated_activities)
    
    print(f"\n🎉 완료! 모든 데이터가 수집 및 가공되었습니다.")
    print(f"   - 통합 활동: {len(integrated_activities)}개")
    print(f"   - 기간: {activity_summary['date_range']['start']} ~ {activity_summary['date_range']['end']}")
    
    return {
        "jira_data": jira_data,
        "confluence_data": confluence_data,
        "gerrit_reviews": gerrit_reviews,
        "gerrit_comments": gerrit_comments,
        "integrated_activities": integrated_activities,
        "summary": activity_summary
    }

# 개별 함수 사용 예제
def example_usage():
    """
    개별 함수들을 사용하는 예제
    """
    # 사용자 정보
    username = "sangyeob.na"
    jira_token = "your_jira_token"
    confluence_token = "your_confluence_token"
    gerrit_tokens = {
        "NA": "your_na_token",
        "EU": "your_eu_token", 
        "AS": "your_as_token"
    }
    
    # 1. 개별 시스템에서 데이터 수집
    jira_activities = collect_jira_data(username, jira_token, excluded_issues=None)
    confluence_activities = collect_confluence_data(username, confluence_token)
    gerrit_reviews, gerrit_comments = collect_gerrit_data(username, gerrit_tokens)
    
    # 2. 데이터 가공
    integrated_data = process_activity_data(
        jira_activities, 
        confluence_activities, 
        gerrit_reviews, 
        gerrit_comments
    )
    
    # 3. 요약 정보 생성
    summary = generate_activity_summary(integrated_data)
    
    return {
        "raw_data": {
            "jira": jira_activities,
            "confluence": confluence_activities,
            "gerrit_reviews": gerrit_reviews,
            "gerrit_comments": gerrit_comments
        },
        "processed_data": integrated_data,
        "summary": summary
    }

if __name__ == "__main__":
    main()
