import re
import requests
import time
import hashlib
from datetime import datetime
from bs4 import BeautifulSoup
from pathlib import Path

# === Настройки ===
URL = "https://www.zoe.com.ua"
CHECK_INTERVAL = 60 * 5  # проверка каждые 5 минут
TOKEN = "YOUR_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
STATE_FILE = Path("YOUR_FILE_PATH")  # путь к файлу состояния

# === Регулярка для строк вида "5.2: не вимикається" или "1.1: 19:00 - 20:30"
pattern = re.compile(r"(\d+\.\d+:\s*[^\n\r]+)")

def fetch_data():
    """Загружает страницу и вытягивает строки расписания."""
    response = requests.get(URL, timeout=20, verify=False)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text(separator="\n")
    matches = pattern.findall(text)
    return "\n".join(matches)

def escape_md(text: str) -> str:
    """Экранирует спецсимволы MarkdownV2."""
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!\\])', r'\\\1', text)

def make_table(data: str) -> str:
    """Форматирует данные в таблицу MarkdownV2."""
    lines = data.splitlines()
    rows = []
    for line in lines:
        m = re.match(r"(\d+\.\d+):\s*(.+)", line)
        if not m:
            continue
        line_num = m.group(1)
        content = m.group(2)
        if "не вимикається" in content:
            rows.append(f"{line_num:4} │ не вимикається")
        else:
            times = re.findall(r"(\d{2}:\d{2})", content)
            if len(times) == 2:
                rows.append(f"{line_num:4} │ {times[0]:7} │ {times[1]:7}")
            else:
                rows.append(f"{line_num:4} │ {content}")

    header = "Лінія │ З       │ До\n──────┼─────────┼─────────"
    table = "\n".join([header] + rows)
    """return f"```\n{table}\n```"""
    return f"```\n{table}```\n"

def get_hash(text):
    """Создаёт хэш строки для проверки изменений."""
    return hashlib.sha256(text.encode()).hexdigest()

def load_last_hash():
    """Загружает хэш из файла."""
    if STATE_FILE.exists():
        return STATE_FILE.read_text().strip()
    return None

def save_last_hash(hash_value):
    """Сохраняет хэш в файл."""
    STATE_FILE.write_text(hash_value)

def send_telegram(data):
    """Отправляет сообщение в Telegram."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    table = make_table(data)
    text = f"*⚡ Нове оновлення розкладу:* \n{table}"

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": f"{text}",
                "parse_mode": "MarkdownV2"
            }
        )
        if not resp.ok:
            print("Ошибка отправки:", resp.text)
    except Exception as e:
        print("Ошибка при отправке в Telegram:", e)

def main():
    last_hash = load_last_hash()
    print(f"Последний сохранённый хэш: {last_hash}")

    while True:
        time.sleep(CHECK_INTERVAL)

        try:
            data = fetch_data()
            if not data:
                print("Данные не найдены, скип.")
                continue

            current_hash = get_hash(data)

            if last_hash != current_hash:
                print("Изменения обнаружены — отправляем обновление...")
                send_telegram(data)
                save_last_hash(current_hash)
                last_hash = current_hash
            else:
                print("Изменений нет.")

        except Exception as e:
            print(f"Ошибка: {e}")

if __name__ == "__main__":
    main()
