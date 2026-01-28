import re
import requests
import time
import hashlib
from datetime import datetime
from bs4 import BeautifulSoup
from pathlib import Path

# === Настройки ===
URL = "https://www.zoe.com.ua/outage"
CHECK_INTERVAL = 60 * 5  # проверка каждые 5 минут
TOKEN = "YOUR_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
STATE_FILE = Path("YOUR_FILE_PATH")  # путь к файлу состояния

# === Регулярка для строк вида "5.2: не вимикається" или "1.1: 19:00 - 20:30"
LINE_RE = re.compile(r"\d+\.\d+:\s*.+", re.UNICODE)

def fetch_latest_article():
    r = requests.get(URL, timeout=20, verify=False)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    article = soup.find("article")
    if not article:
        raise RuntimeError("Не найден <article>")

    article_id = article.get("id")           # post-386182
    title = article.find("h2").get_text(strip=True)
    content = article.find("div", class_="content")

    return article_id, title, content

def load_last_article_id():
    if STATE_FILE.exists():
        return STATE_FILE.read_text().strip()
    return None

def save_last_article_id(article_id):
    STATE_FILE.write_text(article_id)

def extract_lines(content_div):
    text = content_div.get_text("\n")
    lines = []

    for line in text.splitlines():
        line = line.strip()
        if LINE_RE.match(line):
            lines.append(line)

    return lines

def make_table(lines):
    rows = []
    rows.append("Лінія | Відключення")
    rows.append("------+---------------------------------------------")

    for line in lines:
        line_id, rest = line.split(":", 1)
        rows.append(f"{line_id:5} | {rest.strip()}")

    return "\n".join(rows)

def send_telegram(title, table):
    text = (
        f"<b>⚡ {title}</b>\n"
        f"<pre>{table}</pre>"
    )

    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }
    )

    if not r.ok:
        print("Ошибка Telegram:", r.text)

def main():
    while True:
        time.sleep(CHECK_INTERVAL)

        last_id = load_last_article_id()

        article_id, title, content = fetch_latest_article()

        if article_id == last_id:
            print("Новая запись не обнаружена")
            continue

        lines = extract_lines(content)
        if not lines:
            print("Нет строк отключений")
            continue

        table = make_table(lines)

        send_telegram(title, table)

        save_last_article_id(article_id)
        print("Отправлено и сохранено:", article_id)

if __name__ == "__main__":
    main()
