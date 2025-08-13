# --- 1. Импорт необходимых библиотек ---
# Это как "инструменты", которые мы берём для работы.

# BeautifulSoup — инструмент для парсинга HTML. Мы используем его, чтобы "читать" HTML-код страницы.
from bs4 import BeautifulSoup
# vaderSentiment — библиотека для анализа тональности (позитив/негатив).
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
# googletrans — инструмент для перевода текста. VADER лучше всего работает с английским.
from googletrans import Translator
# nltk — библиотека для работы с естественным языком. Нужна для словаря VADER.
import nltk
# time — позволяет делать паузы в коде. Нужна, чтобы не нагружать сервисы.
import time
# Selenium — основной инструмент для автоматизации браузера. Позволяет управлять Chrome.
from selenium import webdriver
# By — нужен, чтобы Selenium мог искать элементы по разным критериям (CSS-селектор, ID и т.д.).
from selenium.webdriver.common.by import By
# НОВЫЙ ИНСТРУМЕНТ: Библиотека для работы с табличными данными (как Excel)
import pandas as pd 
# НОВЫЙ ИНСТРУМЕНТ: Библиотека для создания графиков и визуализации данных
import matplotlib.pyplot as plt 

# --- 2. Настройка VADER и NLTK ---
# Этот блок можно закомментировать, если словарь уже скачан
# try:
#     nltk.data.find('sentiment/vader_lexicon.zip')
# except nltk.downloader.DownloadError:
#     nltk.download('vader_lexicon')

# Создаём "анализатор" для оценки текста
analyzer = SentimentIntensityAnalyzer()
# Создаём "переводчик"
translator = Translator()

# --- 3. Настройка и сбор данных с помощью Selenium ---
# URL-адрес страницы, которую мы будем парсить
url = 'https://www.wildberries.ru/catalog/337703147/feedbacks?imtId=320962769&size=503798039'

# Создаём объект, который будет хранить настройки для нашего браузера Chrome
options = webdriver.ChromeOptions()
# settings.add_argument('--headless')
# settings.add_argument('--disable-gpu')
# Эти строки закомментированы. Если их раскомментировать, браузер будет работать в скрытом режиме.

reviews = [] # Список для хранения собранных отзывов

try:
    # Запускаем браузер Chrome, используя наши настройки (сейчас они пустые).
    # driver — это переменная, которая теперь представляет окно браузера, которым мы управляем.
    driver = webdriver.Chrome(options=options)
    # Командуем браузеру открыть нужную страницу
    driver.get(url)

    # --- Умный механизм бесконечной прокрутки ---
    last_review_count = 0
    scroll_attempts = 0
    max_scroll_attempts = 10 # Максимальное количество попыток прокрутки без новых отзывов

    while True:
        # Прокручиваем страницу до самого низа
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Делаем паузу, чтобы дать сайту время подгрузить новый контент
        time.sleep(2)
        
        # Получаем полный HTML-код и считаем количество найденных отзывов
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        current_reviews = soup.select('p.feedback__text span.feedback__text--item')
        current_review_count = len(current_reviews)
        
        # Проверяем, появились ли новые отзывы
        if current_review_count > last_review_count:
            print(f"Найдено {current_review_count} отзывов. Продолжаем прокрутку...")
            last_review_count = current_review_count
            scroll_attempts = 0 # Сбрасываем счётчик, потому что отзывы нашлись
        else:
            scroll_attempts += 1
            print(f"Новые отзывы не найдены. Попытка {scroll_attempts} из {max_scroll_attempts}...")
            
        # Если после нескольких попыток не появилось новых отзывов, выходим из цикла
        if scroll_attempts >= max_scroll_attempts:
            print("Все отзывы загружены.")
            reviews = [element.get_text(strip=True) for element in current_reviews if element.get_text(strip=True)]
            break

except Exception as e:
    print(f"Произошла ошибка: {e}")
    print("Не удалось загрузить страницу или найти отзывы.")

finally:
    # Обязательно закрываем браузер, чтобы не расходовать ресурсы компьютера.
    driver.quit()

# --- 4. Анализ тональности и вывод результатов ---
if reviews:
    print("\n--- Отзывы успешно собраны. Начинаем анализ тональности... ---")
    
    positive_count = 0
    negative_count = 0
    neutral_count = 0

    # Создадим список, чтобы хранить все результаты для pandas
    # Это список словарей, каждый словарь - это одна строка в таблице
    results = []

    # Проходимся по каждому собранному отзыву
    for i, review in enumerate(reviews):
        # 1. Попытка перевода с повторами
        translated_review = ""
        retries = 3  # Количество попыток перевода
        
        while retries > 0:
            try:
                translated_review = translator.translate(review, src='ru', dest='en').text
                break  # Если перевод удался, выходим из внутреннего цикла
            except Exception as e:
                print(f"Ошибка перевода отзыва {i+1}, осталось попыток: {retries-1}")
                time.sleep(3)  # Делаем паузу перед следующей попыткой
                retries -= 1
        
        # 2. Если перевод всё-таки не удался
        if not translated_review:
            print(f"Не удалось перевести отзыв {i+1} после нескольких попыток. Пропускаем...")
            neutral_count += 1
            sentiment = "Нейтральный (Ошибка перевода)"
            results.append({'Отзыв': review, 'Перевод': '', 'Тональность': sentiment, 'Оценка': 0})
            continue # Переходим к следующему отзыву
        
        # 3. Анализ тональности переведённого текста (тот же код)
        scores = analyzer.polarity_scores(translated_review)
        
        if scores['compound'] >= 0.05:
            sentiment = "Позитивный"
            positive_count += 1
        elif scores['compound'] <= -0.05:
            sentiment = "Негативный"
            negative_count += 1
        else:
            sentiment = "Нейтральный"
            neutral_count += 1
        
        results.append({
            'Отзыв': review,
            'Перевод': translated_review,
            'Тональность': sentiment,
            'Оценка': scores['compound']
        })    

    # --- Вывод финальной статистики ---
    total_reviews = len(reviews)
    print("--- Общая статистика ---")
    print(f"Всего проанализировано отзывов: {total_reviews}")
    print(f"Позитивные: {positive_count} ({positive_count/total_reviews:.2%})")
    print(f"Негативные: {negative_count} ({negative_count/total_reviews:.2%})")
    print(f"Нейтральные: {neutral_count} ({neutral_count/total_reviews:.2%})")

    # --- 5. Сохранение результатов в Excel и создание графика ---
    try:
        # Создаём DataFrame из нашего списка словарей.
        # DataFrame — это основная структура данных в pandas, похожая на таблицу.
        df = pd.DataFrame(results)
        
        # Сохраняем DataFrame в файл Excel.
        # 'анализ_отзывов_wildberries.xlsx' — это имя файла.
        # index=False говорит pandas не добавлять в файл столбец с индексами (1, 2, 3...).
        df.to_excel('анализ_отзывов_wildberries.xlsx', index=False)
        print("\n--- Результаты успешно сохранены в файл 'анализ_отзывов_wildberries.xlsx' ---")
        
        # --- Визуализация данных ---
        # Считаем количество отзывов по каждой тональности
        sentiment_counts = df['Тональность'].value_counts()
        
        # Создаём круговую диаграмму (pie chart)
        plt.figure(figsize=(8, 6)) # Задаём размер окна для графика
        
        # plt.pie() — функция для создания диаграммы
        # sentiment_counts.values — сами данные (количество позитивных/негативных)
        # labels=sentiment_counts.index — подписи для каждого сектора ('Позитивный', 'Негативный' и т.д.)
        # autopct='%1.1f%%' — формат для отображения процентов на графике
        plt.pie(sentiment_counts.values, labels=sentiment_counts.index, autopct='%1.1f%%', startangle=90)
        
        plt.title('Распределение тональности отзывов') # Заголовок графика
        plt.ylabel('') # Убираем подпись оси Y, так как в круговой диаграмме она не нужна
        plt.show() # Показываем график в отдельном окне
        
    except Exception as e:
        print(f"Ошибка при сохранении в Excel или создании графика: {e}")


else:
    print("Нечего анализировать, так как отзывы не были найдены.")

