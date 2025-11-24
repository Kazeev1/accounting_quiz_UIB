import streamlit as st
import docx
from docx.shared import RGBColor
import random


# ---------------------------
# Функция для чтения DOCX
# ---------------------------
def parse_quiz_file(uploaded_file):
    doc = docx.Document(uploaded_file)
    questions = []
    current_q = None
    RED_HEX = "FF0000"

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # Новый вопрос начинается с "№"
        if text.startswith("№"):
            if current_q:
                questions.append(current_q)
            current_q = {"question": text, "options": [], "correct_text": None}

        elif current_q:
            is_correct = False

            for run in para.runs:
                if (
                    run.font.color
                    and run.font.color.rgb
                    and str(run.font.color.rgb) == RED_HEX
                ):
                    is_correct = True
                    break

            current_q["options"].append(text)
            if is_correct:
                current_q["correct_text"] = text

    if current_q:
        questions.append(current_q)

    # Оставляем только валидные вопросы
    valid = [q for q in questions if q["correct_text"]]

    return valid


# ---------------------------
# Streamlit UI
# ---------------------------
st.title("📘 Accounting Quiz — DOCX Tester")
st.write("Загружай DOCX с вопросами, выбирай количество вопросов и проходи тест!")

# Загрузка файла
uploaded = st.file_uploader("Загрузите docx файл с тестом", type=["docx"])

if uploaded:
    # Загружаем базу вопросов в кеш
    if "all_questions" not in st.session_state:
        st.session_state.all_questions = parse_quiz_file(uploaded)
        st.session_state.current_batch = None
        st.session_state.user_answers = {}
        st.session_state.step = "menu"

    all_questions = st.session_state.all_questions

    st.success(f"Загружено вопросов: {len(all_questions)}")

    # ---------------------------------------
    # Выбор количества вопросов и генерация теста
    # ---------------------------------------
    if st.session_state.step == "menu":
        st.subheader("Создать новый тест")
        num = st.number_input(
            "Сколько вопросов взять?", min_value=1, max_value=len(all_questions), value=len(all_questions)
        )

        if st.button("Сформировать тест"):
            st.session_state.current_batch = random.sample(all_questions, num)
            st.session_state.user_answers = {}
            st.session_state.step = "quiz"

    # ---------------------------------------
    # Основной тест
    # ---------------------------------------
    if st.session_state.step == "quiz":
        batch = st.session_state.current_batch
        total = len(batch)

        st.subheader(f"Тест из {total} вопросов")

        for i, q in enumerate(batch):
            st.write(f"### ❓ {q['question']}")

            options = q["options"].copy()
            random.shuffle(options)

            # Уникальный ключ для радиокнопок
            key = f"q_{i}"

            st.radio(
                "Выберите ответ:",
                options,
                key=key,
                index=None,
            )

            st.write("---")

        if st.button("Завершить тест"):
            st.session_state.step = "results"

    # ---------------------------------------
    # Результаты
    # ---------------------------------------
    if st.session_state.step == "results":
        st.subheader("📊 Результаты")

        batch = st.session_state.current_batch
        score = 0

        for i, q in enumerate(batch):
            user_answer = st.session_state.get(f"q_{i}", None)

            st.write(f"### ❓ {q['question']}")

            if user_answer == q["correct_text"]:
                st.success(f"✔ Правильно: {user_answer}")
                score += 1
            else:
                st.error(f"✘ Неправильно: {user_answer}")
                st.info(f"Правильный ответ: **{q['correct_text']}**")

            st.write("---")

        st.write(f"## Итог: {score} из {len(batch)} ({score/len(batch)*100:.1f}%)")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔁 Повторить этот тест"):
                st.session_state.step = "quiz"

        with col2:
            if st.button("🆕 Новый тест"):
                st.session_state.step = "menu"

        with col3:
            if st.button("🔚 Выйти"):
                st.session_state.all_questions = None
                st.session_state.step = "menu"
                st.experimental_rerun()
