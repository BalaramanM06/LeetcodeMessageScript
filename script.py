#!/usr/bin/env python3
"""
leetcode_daily.py

Fetch today's LeetCode daily problem and post to one or more Telegram chats.

This version:
 - Escapes unsafe HTML so Telegram accepts the message
 - Sends the message to multiple recipients (either hardcoded below or from the
   TELEGRAM_RECIPIENTS env var).
 - If TELEGRAM_RECIPIENTS is set, it overrides the hardcoded list.

RECIPIENT formats:
 - Env var TELEGRAM_RECIPIENTS (optional): comma-separated entries of
   BOT_TOKEN:CHAT_ID
   Example:
     TELEGRAM_RECIPIENTS="828238...:8555752928,828601...:6398158417"
 - If env var not set, this script will fallback to the hardcoded RECIPIENTS list.
"""
import os
import sys
import time
import logging
import html
from typing import Optional, Dict, Any, List, Tuple
import requests
from bs4 import BeautifulSoup

# --- Config ---
GRAPHQL_URL = "https://leetcode.com/graphql"
QUERY = """
query {
  activeDailyCodingChallengeQuestion {
    date
    link
    question {
      title
      titleSlug
      difficulty
      content
      frontendQuestionId : questionFrontendId
    }
  }
}
"""

RETRY_ATTEMPTS = 2
RETRY_DELAY = 2  # seconds
REQUEST_TIMEOUT = 10  # seconds

# ---------------------------
# RECIPIENTS: override using the TELEGRAM_RECIPIENTS env var (recommended)
# Format for env var: BOT_TOKEN:CHAT_ID,BOT_TOKEN2:CHAT_ID2
#
# If env var not provided, the script falls back to the hardcoded list below.
# NOTE: Hardcoding tokens in files is insecure. Use secrets instead.
# ---------------------------

# HARD-CODED FALLBACK (as you provided). Insecure if committed to a repo.
RECIPIENTS_FALLBACK: List[Tuple[str, str]] = [
    ("8282381882:AAH-IJLyk0OOHIZhS7ph-3S9-3kgQZZoBBw", "8555752928"),
    ("8286012641:AAGdzxUT9facwORw3HSJBy9fH4SbKbZlGok", "6398158417"),
]

def load_recipients_from_env() -> List[Tuple[str, str]]:
    """Parse TELEGRAM_RECIPIENTS env var into a list of (token, chat_id)."""
    raw = os.environ.get("TELEGRAM_RECIPIENTS", "").strip()
    if not raw:
        return []
    pairs = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        # split only on the last colon in case token contains colons (it doesn't normally)
        if ":" not in part:
            logging.warning("Skipping invalid recipient entry (no colon found): %s", part)
            continue
        token, chat = part.split(":", 1)
        token = token.strip()
        chat = chat.strip()
        if token and chat:
            pairs.append((token, chat))
        else:
            logging.warning("Skipping invalid recipient entry (empty token/chat): %s", part)
    return pairs

# Final recipients (env overrides fallback)
RECIPIENTS = load_recipients_from_env() or RECIPIENTS_FALLBACK

# Basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

if RECIPIENTS == RECIPIENTS_FALLBACK:
    logging.warning("Using hardcoded TELEGRAM tokens/chat IDs from RECIPIENTS_FALLBACK. "
                    "This is insecure for public repos. Prefer TELEGRAM_RECIPIENTS env var or GitHub secrets.")

def clean_html(html_content: str) -> str:
    """Convert HTML to plain text, escape unsafe chars, and limit length."""
    soup = BeautifulSoup(html_content or "", "html.parser")
    text = soup.get_text(" ", strip=True)
    text = html.escape(text)  # escape <, >, & so Telegram won't misinterpret
    return text[:700] + "..." if len(text) > 700 else text

def send_telegram_single(bot_token: str, chat_id: str, text: str) -> Dict[str, Any]:
    """Send message via Telegram Bot API for a single bot/chat pair. Returns JSON response."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",  # safe because we escape snippet
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        j = resp.json()
    except Exception as e:
        logging.exception("Failed to send Telegram message to chat_id=%s (bot_token first 8 chars=%s): %s",
                          chat_id, bot_token[:8] if bot_token else "?", e)
        return {"ok": False, "error": str(e)}
    return j

def fetch_daily(session: Optional[requests.Session] = None) -> Dict[str, Any]:
    """Fetch today's LeetCode daily challenge."""
    session = session or requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; leetcode-daily-bot/1.0)"})

    # Initial GET to obtain cookies / csrftoken
    try:
        _ = session.get("https://leetcode.com", timeout=REQUEST_TIMEOUT)
    except Exception as e:
        logging.warning("Initial GET to leetcode.com failed: %s", e)

    csrftoken = session.cookies.get("csrftoken", "")
    headers = {
        "Referer": "https://leetcode.com",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "x-csrftoken": csrftoken,
    }

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            resp = session.post(
                GRAPHQL_URL,
                json={"query": QUERY},
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            j = resp.json()
        except Exception as e:
            logging.warning("GraphQL attempt %d failed: %s", attempt, e)
            time.sleep(RETRY_DELAY)
            continue

        if "data" in j and j["data"].get("activeDailyCodingChallengeQuestion"):
            data = j["data"]["activeDailyCodingChallengeQuestion"]
            q = data["question"]
            return {
                "id": str(q.get("frontendQuestionId", "")),
                "title": q.get("title", ""),
                "difficulty": q.get("difficulty", ""),
                "content": q.get("content", ""),
                "link": "https://leetcode.com" + data.get("link", ""),
                "date": data.get("date", ""),
            }

    raise RuntimeError("Failed to fetch LeetCode daily challenge after retries.")

def build_message(today: Dict[str, Any]) -> str:
    snippet = clean_html(today.get("content", ""))
    msg = (
        f"🔥 <b>LeetCode Daily Challenge</b> ({today.get('date')})\n\n"
        f"📘 <b>{html.escape(today.get('title', ''))}</b>\n"
        f"🏷️ Difficulty: <code>{html.escape(today.get('difficulty', ''))}</code>\n\n"
        f"🔗 <a href='{today.get('link')}'>Solve Problem</a>\n\n"
        f"<i>{snippet}</i>"
    )
    return msg

def main():
    if not RECIPIENTS:
        logging.error("No TELEGRAM recipients configured. Set TELEGRAM_RECIPIENTS env var or update RECIPIENTS_FALLBACK.")
        sys.exit(1)

    logging.info("Fetching today's LeetCode challenge...")
    today = fetch_daily()

    message = build_message(today)

    errors = []
    for bot_token, chat_id in RECIPIENTS:
        logging.info("Sending to chat_id=%s (bot token starts with %s)", chat_id, bot_token[:8] if bot_token else "?")
        result = send_telegram_single(bot_token, chat_id, message)
        if not result.get("ok"):
            errors.append({"bot_token_head": bot_token[:8], "chat_id": chat_id, "response": result})
            logging.error("Telegram API error for chat_id=%s: %s", chat_id, result)
        else:
            logging.info("Message sent to chat_id=%s (message_id=%s).", chat_id, result.get("result", {}).get("message_id"))

    if errors:
        logging.error("Some sends failed. See logs above for details.")
        sys.exit(2)
    logging.info("All messages sent successfully.")
    sys.exit(0)

if __name__ == "__main__":
    main()
