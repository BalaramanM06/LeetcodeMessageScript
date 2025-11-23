# 📘 LeetCode Daily Challenge → Telegram Bot

This repository automatically fetches the **LeetCode Daily Coding Challenge** and posts a formatted message to a **Telegram chat**.  
It is designed to run automatically using **GitHub Actions**, **Azure Functions**, or any scheduler.

---

## 🚀 Features
- Fetches the daily challenge from LeetCode using GraphQL.
- Cleans and sanitizes HTML so Telegram accepts the message.
- Sends a formatted message with title, difficulty, link, and description snippet.
- Uses environment variables for secrets.
- Includes a GitHub Actions workflow for scheduled runs.

---


## 📂 Project Structure
```
.
├── Leetcode_daily.py # Main script.
├── requirements.txt # Python dependencies.
└── .github/
  └── workflows/
    └── run.yml # GitHub Actions workflow

```

---

## ⚙️ Requirements
- Python **3.8+**
- Dependencies:
  - `requests`
  - `beautifulsoup4`

Install dependencies:
```bash
pip install -r requirements.txt
```

## 🔧 Local Testing

### 1️⃣ Clone the repository
```bash
git clone https://github.com/your-username/LeetcodeMessageScript.git
cd LeetcodeMessageScript
```

## 2️ Install dependencies
```bash
pip install -r requirements.txt
```
