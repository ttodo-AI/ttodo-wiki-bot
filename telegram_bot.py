import os, re, time
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from notion_client import Client

load_dotenv(r"C:\ttodo_wiki\config.txt")

TOKEN   = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = str(os.environ["TELEGRAM_CHAT_ID"])
DB_ID   = os.environ["NOTION_DB_ID"]
notion  = Client(auth=os.environ["NOTION_API_KEY"])

URL_RE = re.compile(r'https?://\S+')

def tg(method, **kwargs):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/{method}",
        json=kwargs, timeout=10
    )

def reply(chat_id, text):
    tg("sendMessage", chat_id=chat_id, text=text)

def get_updates(offset):
    r = requests.get(
        f"https://api.telegram.org/bot{TOKEN}/getUpdates",
        params={"timeout": 30, "offset": offset},
        timeout=35
    )
    return r.json().get("result", [])

def create_page(content, source_url=None):
    title = content.split('\n')[0][:50] or "텔레그램 메모"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    props = {
        "Title": {"title": [{"text": {"content": title}}]},
        "Date":  {"date": {"start": today}}
    }
    if source_url:
        props["Source URL"] = {"url": source_url}

    notion.pages.create(
        parent={"database_id": DB_ID},
        properties=props,
        children=[{
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": content}}]}
        }]
    )

def handle(text, chat_id):
    if chat_id != CHAT_ID:
        reply(chat_id, "❌ 권한 없음")
        return

    if text.startswith("/start"):
        reply(chat_id, (
            "✅ ttodo_wiki 봇\n"
            "메모를 그냥 보내세요.\n\n"
            "- URL 포함 → 출처 자동 등록\n"
            "- i: 접두사 → Idea 타입 강제\n"
            "- 나머지는 AI가 분류"
        ))
        return

    urls = URL_RE.findall(text)
    source_url = urls[-1] if urls else None

    try:
        create_page(text, source_url)
        msg = "✅ 노션 저장 완료"
        if source_url:
            msg += "\n🔗 출처 링크 등록됨"
        reply(chat_id, msg)
    except Exception as e:
        reply(chat_id, f"❌ 저장 실패\n{e}")

def main():
    print("🤖 텔레그램 봇 시작")
    offset = 0
    while True:
        try:
            updates = get_updates(offset)
            for u in updates:
                offset = u["update_id"] + 1
                msg  = u.get("message", {})
                text = msg.get("text", "")
                cid  = str(msg.get("chat", {}).get("id", ""))
                if text and cid:
                    handle(text, cid)
        except KeyboardInterrupt:
            print("봇 종료")
            break
        except requests.exceptions.ConnectionError:
            time.sleep(2)
        except Exception as e:
            print(f"오류: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
