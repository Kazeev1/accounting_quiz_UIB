import streamlit as st
import docx
import random


# ------------------------------------------------
# Парсер DOCX
# ------------------------------------------------
def parse_quiz_file(uploaded_file):
    doc = docx.Document(uploaded_file)
    questions = []
    current_q = None
    RED_HEX = 'FF0000'

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        if text.startswith("№"):
            if current_q:
                questions.append(current_q)
            current_q = {"question": text, "options": [], "correct_text": None}

        else:
            if current_q:
                is_correct = False
                for run in para.runs:
                    if run.font.color and run.font.color.rgb and str(run.font.color.rgb) == RED_HEX:
                        is_correct = True
                        break

                current_q["options"].append(text)
                if is_correct:
                    current_q["correct_text"] = text

    if current_q:
        questions.append(current_q)

    return [q for q in questions if q["correct_text"]]


# ------------------------------------------------
# UI
# ------------------------------------------------
st.title("📘 Accounting Quiz — Быстрый режим тестирования")
st.write("Загружайте DOCX и проходите тест. Ответ показывается сразу!")

uploaded = st.file_uploader("Загрузите файл .docx", type=["docx"])

if uploaded:

    # Загружаем вопросы один раз
    if "questions" not in st.session_state:
        st.session_state.questions = parse_quiz_file(uploaded)
        st.session_state.current_batch = []
        st.session_state.index = 0
        st.session_state.show_answer = False
        st.session_state.selected_option = None
        st.session_state.running = False

    questions = st.session_state.questions

    st.success(f"Загружено вопросов: {len(questions)}")

    # ---------------------------------------------
    # Меню выбора количества вопросов
    # ---------------------------------------------
    if not st.session_state.running:

        st.subheader("Настройки теста")

        count = st.slider(
            "Сколько вопросов использовать?",
            1,
            len(questions),
            len(questions),
            step=1
        )

        if st.button("Начать тест"):
            st.session_state.current_batch = random.sample(questions, count)
            st.session_state.index = 0
            st.session_state.running = True
            st.session_state.show_answer = False
            st.session_state.selected_option = None
            st.experimental_rerun()

    # ---------------------------------------------
    # Основной тест — по одному вопросу
    # ---------------------------------------------
    if st.session_state.running:

        batch = st.session_state.current_batch
        idx = st.session_state.index
        q = batch[idx]

        st.markdown(f"### Вопрос {idx+1}/{len(batch)}")
        st.write(q["question"])
        st.write("---")

        # Перемешиваем варианты на каждый question
        options = q["options"].copy()
        random.shuffle(options)

        # Если пользователь еще не выбрал ответ
        if not st.session_state.show_answer:

            choice = st.radio(
                "Выберите ответ:",
                options,
                key=f"q{idx}"
            )

            st.session_state.selected_option = choice

            if st.button("Проверить ответ"):
                st.session_state.show_answer = True
                st.experimental_rerun()

        # Если ответ проверён → показываем результат
        else:
            user = st.session_state.selected_option
            correct = q["correct_text"]

            if user == correct:
                st.success(f"✔ Правильно! \n\n**{user}**")
            else:
                st.error(f"✘ Неправильно. Ваш ответ: **{user}**")
                st.info(f"Правильный ответ: **{correct}**")

            st.write("---")

            # Кнопка "Следующий вопрос" или "Завершить"
            if idx < len(batch) - 1:
                if st.button("Следующий вопрос ➜"):
                    st.session_state.index += 1
                    st.session_state.show_answer = False
                    st.session_state.selected_option = None
                    st.experimental_rerun()
            else:
                if st.button("Завершить тест"):
                    st.session_state.running = False
                    st.session_state.show_answer = False
                    st.success("Тест завершён!")
                    st.experimental_rerun()
