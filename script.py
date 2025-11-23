#!/usr/bin/env python3
"""
leetcode_daily.py

Fetch today's LeetCode daily problem and post to a Telegram chat.
Ready for cloud deployment:
 - Uses environment variables for secrets
 - Avoids reliance on local state file persistence
 - Dependencies listed in requirements.txt
"""

import os
import sys
import time
import logging
from typing import Optional, Dict, Any
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

# --- TELEGRAM CREDENTIALS (from environment variables) ---
TELEGRAM_BOT_TOKEN = "8282381882:AAH-IJLyk0OOHIZhS7ph-3S9-3kgQZZoBBw"
TELEGRAM_CHAT_ID = 85585557529285752928

# Basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def clean_html(html: str) -> str:
    """Convert HTML to plain text and limit length."""
    soup = BeautifulSoup(html or "", "html.parser")
    text = soup.get_text(" ", strip=True)
    return text[:700] + "..." if len(text) > 700 else text


def send_telegram(text: str) -> requests.Response:
    """Send message via Telegram Bot API."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID.")

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    j = resp.json()
    if not j.get("ok", False):
        logging.error("Telegram API error: %s", j)
    else:
        logging.info("Telegram message sent successfully (message_id=%s).", j.get("result", {}).get("message_id"))
    return resp


def fetch_daily(session: Optional[requests.Session] = None) -> Dict[str, Any]:
    """Fetch today's LeetCode daily challenge."""
    session = session or requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; leetcode-daily-bot/1.0)"})

    # Initial GET to obtain cookies / csrftoken
    init = session.get("https://leetcode.com", timeout=REQUEST_TIMEOUT)
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

    raise RuntimeError("Failed to fetch LeetCode daily challenge.")


def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID.")
        sys.exit(1)

    logging.info("Fetching today's LeetCode challenge...")
    today = fetch_daily()

    snippet = clean_html(today.get("content", ""))
    message = (
        f"🔥 <b>LeetCode Daily Challenge</b> ({today.get('date')})\n\n"
        f"📘 <b>{today.get('title')}</b>\n"
        f"🏷️ Difficulty: <code>{today.get('difficulty')}</code>\n\n"
        f"🔗 <a href='{today.get('link')}'>Solve Problem</a>\n\n"
        f"<i>{snippet}</i>"
    )

    logging.info("Sending to Telegram...")
    send_telegram(message)


if __name__ == "__main__":
    main()
