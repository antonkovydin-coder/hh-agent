import os
import re
import time
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any

# ============================================================
# 1. ЗАГРУЗКА КЛЮЧЕЙ ИЗ .ENV (если файл есть)
# ============================================================
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# ============================================================
# 2. ТВОИ КЛЮЧИ И НАСТРОЙКИ
# ============================================================
CLIENT_ID = os.getenv("CLIENT_ID", "ВАШ_CLIENT_ID_ОТ_HH")  # Замените или положите в .env
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "ВАШ_CLIENT_SECRET_ОТ_HH")  # Замените или положите в .env
USER_AGENT = "AndreyPM/1.0 (andreikovydin@yandex.ru)"  # Укажи свой email

# --- Твоё резюме (эталон для сравнения) ---
try:
    with open("resume.txt", "r", encoding="utf-8") as f:
        MY_RESUME = f.read()
except:
    MY_RESUME = """
    Ковыдин Андрей, 36 лет, Москва.
    Senior Project Manager / Delivery Manager (Digital / Banking / IT).
    Опыт 5+ лет в Т-Банке и Совкомбанке.
    Управление портфелем цифровых инициатив, координация 12+ кросс-функциональных команд.
    Навыки: Agile, Scrum, Kanban, Jira, управление бэклогом, фасилитация, риск-менеджмент.
    Результаты: рост конверсии на 30%, запуск 100+ A/B-тестов.
    """

# ============================================================
# 3. КЛАСС ДЛЯ РАБОТЫ С HEADHUNTER API
# ============================================================
class HHAuth:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expires = None
    
    def get_access_token(self):
        """Получает или обновляет токен доступа через OAuth"""
        if self.access_token and self.token_expires > datetime.now():
            return self.access_token
        
        # Получаем код авторизации (требует ручного входа в браузере)
        auth_url = (
            f"https://hh.ru/oauth/authorize?response_type=code"
            f"&client_id={self.client_id}&redirect_uri=https://dev.hh.ru"
        )
        print("🔑 Перейдите по ссылке и скопируйте код из URL после ?code=")
        print(auth_url)
        code = input("Введите код: ").strip()
        
        # Обмениваем код на токен
        token_url = "https://hh.ru/oauth/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": "https://dev.hh.ru"
        }
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.token_expires = datetime.now() + timedelta(seconds=token_data["expires_in"])
            print(f"✅ Токен получен. Действителен до {self.token_expires}")
            return self.access_token
        else:
            print(f"❌ Ошибка получения токена: {response.text}")
            return None

# --- Класс для поиска вакансий ---
class HHAgent:
    def __init__(self, auth):
        self.auth = auth
        self.base_url = "https://api.hh.ru/vacancies"
    
    def search_vacancies(self, text, area=1, period=3, per_page=100):
        """Ищет вакансии по запросу"""
        token = self.auth.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "AndreyPM/1.0 (andreikovydin@yandex.ru)"
        }
        params = {
            "text": text,
            "area": area,  # 1 = Москва
            "search_period": period,  # за последние 3 дня
            "per_page": per_page,
            "page": 0
        }
        
        all_vacancies = []
        while True:
            response = requests.get(self.base_url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                all_vacancies.extend(data.get("items", []))
                if data.get("pages") <= params["page"] + 1:
                    break
                params["page"] += 1
                time.sleep(0.5)
            else:
                print(f"⚠️ Ошибка: {response.status_code} {response.text}")
                break
        return all_vacancies

# ============================================================
# 4. СРАВНЕНИЕ С РЕЗЮМЕ (УПРОЩЁННАЯ ВЕРСИЯ)
# ============================================================
def simple_match(vacancy, resume_text):
    """Простое сравнение по ключевым словам и навыкам"""
    # Извлекаем текст вакансии
    title = vacancy.get("name", "").lower()
    description = vacancy.get("description", "").lower()
    key_skills = " ".join([s["name"].lower() for s in vacancy.get("key_skills", [])])
    vacancy_text = f"{title} {description} {key_skills}"
    
    # Ключевые слова из твоего резюме
    keywords = ["project manager", "руководитель проектов", "проджект-менеджер", "delivery manager"]
    skills = ["agile", "scrum", "kanban", "jira", "управление бэклогом", "фасилитация"]
    
    # Считаем количество совпадений
    matches = 0
    for kw in keywords:
        if kw in vacancy_text or kw in title:
            matches += 10
    for sk in skills:
        if sk in vacancy_text:
            matches += 5
    
    # Если в вакансии есть "банк" или "финансы" — плюс 5%
    if "банк" in vacancy_text or "финанс" in vacancy_text:
        matches += 5
    
    # Ограничиваем максимум 100%
    return min(matches, 100)

# ============================================================
# 5. ОСНОВНАЯ ФУНКЦИЯ
# ============================================================
def main():
    # Инициализация
    auth = HHAuth(CLIENT_ID, CLIENT_SECRET)
    agent = HHAgent(auth)
    
    print("🧠 Запускаю поиск вакансий...")
    
    # Поиск по трём запросам
    queries = [
        "Руководитель проектов",
        "Project Manager",
        "Менеджер проектов"
    ]
    
    all_vacancies = []
    for query in queries:
        print(f"🔍 Ищу: {query}")
        vacancies = agent.search_vacancies(query, period=7)  # За 7 дней
        all_vacancies.extend(vacancies)
        time.sleep(1)
    
    # Убираем дубли по ID
    seen = set()
    unique_vacancies = []
    for v in all_vacancies:
        if v["id"] not in seen:
            seen.add(v["id"])
            unique_vacancies.append(v)
    
    print(f"📊 Найдено {len(unique_vacancies)} уникальных вакансий")
    
    # Сравниваем с резюме
    matched = []
    for v in unique_vacancies:
        match = simple_match(v, MY_RESUME)
        if match >= 75:
            matched.append({
                "title": v.get("name"),
                "company": v.get("employer", {}).get("name"),
                "link": v.get("alternate_url"),
                "match": match
            })
        time.sleep(0.2)
    
    # Сортируем и выводим
    matched.sort(key=lambda x: x["match"], reverse=True)
    
    if matched:
        print(f"\n🎯 Найдено {len(matched)} вакансий с совпадением ≥ 75%:\n")
        for item in matched:
            print(f"• {item['match']}% — {item['title']}")
            print(f"  {item['company']}")
            print(f"  {item['link']}")
            print("-" * 50)
    else:
        print("\n⚠️ Подходящих вакансий с совпадением ≥ 75% не найдено.")

if __name__ == "__main__":
    main()
