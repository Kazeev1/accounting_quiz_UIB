# app.py
import streamlit as st
import docx
from docx.shared import RGBColor
import random
import io
import hashlib

# -----------------------------
# Утилиты для парсинга DOCX
# -----------------------------
@st.cache_data
def parse_quiz_bytes_cached(docx_bytes: bytes):
    """
    Парсер, возвращает список вопросов в формате:
    [ {"question": str, "options": [str,...], "correct_text": str}, ... ]
    Поддерживает:
      - правильный вариант, выделенный RGB цветом ( FF0000 )
      - или вариант, начинающийся с '*' (звёздочка) как запасной метод
    """
    return _parse_quiz_bytes(docx_bytes)

def _parse_quiz_bytes(docx_bytes: bytes):
    """
    Нефункциональная часть парсера вынесена отдельно (без кеша), чтобы было проще тестировать.
    """
    doc = docx.Document(io.BytesIO(docx_bytes))
    questions = []
    current_q = None
    RED_HEX = "FF0000"

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # Начало нового вопроса (строка начинается с "№")
        if text.startswith("№"):
            if current_q:
                questions.append(current_q)
            current_q = {"question": text, "options": [], "correct_text": None}
            continue

        # Если ещё не наткнулись на вопрос — пропускаем
        if current_q is None:
            continue

        # Обработка варианта ответа — проверяем на "красный" run или на звёздочку в начале
        is_correct = False

        # 1) Проверяем, есть ли в параграфе явная звёздочка в начале (последняя надежда)
        if text.startswith("*"):
            # убираем знак * из текста при сохранении
            clean = text.lstrip("*").strip()
            current_q["options"].append(clean)
            current_q["correct_text"] = clean
            continue

        # 2) Проверяем runs на RGB цвет (надёжный метод)
        for run in para.runs:
            try:
                color = getattr(run.font, "color", None)
                if color is None:
                    continue
                rgb = getattr(color, "rgb", None)
                if rgb is not None and str(rgb).upper() == RED_HEX:
                    is_correct = True
                    break
            except Exception:
                # Иногда у run.font.color может быть неожиданный тип — просто игнорируем
                pass

        # Добавляем вариант (без изменений текста)
        current_q["options"].append(text)
        if is_correct:
            current_q["correct_text"] = text

    # добавляем последний вопрос
    if current_q:
        questions.append(current_q)

    # Оставляем только вопросы с найденным корректным ответом
    valid = [q for q in questions if q.get("correct_text") is not None]

    return valid

# -----------------------------
# Вспомогательные функции
# -----------------------------
def bytes_hash(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()

def init_session_state():
    # Инициализация необходимых ключей
    defaults = {
        "questions_hash": None,
        "all_questions": None,
        "current_batch": None,
        "batch_option_orders": None,
        "index": 0,
        "show_answer": None,   # list bool per question
        "running": False,
        "user_answers": None,
        "selected_choice_keys": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# -----------------------------
# UI и логика приложения
# -----------------------------
def main():
    st.set_page_config(page_title="Accounting Quiz (Streamlit)", layout="centered")
    st.title("📘 Accounting Quiz — Streamlit")
    st.write("Загружай DOCX, выбирай количество вопросов и проходи тест. Правильный ответ показывается сразу.")

    init_session_state()

    uploaded = st.file_uploader("Загрузите .docx файл с вопросами (варианты: красный цвет или *метка):", type=["docx"])

    # Если пользователь перезагрузил файл — обнуляем кешированные данные для нового файла
    if uploaded is not None:
        file_bytes = uploaded.getvalue()
        this_hash = bytes_hash(file_bytes)
        if st.session_state.questions_hash != this_hash:
            # новый файл — парсим
            try:
                parsed = parse_quiz_bytes_cached(file_bytes)
            except Exception as e:
                st.error(f"Ошибка при чтении файла: {e}")
                parsed = []

            st.session_state.questions_hash = this_hash
            st.session_state.all_questions = parsed
            # Сбрасываем текущее тестирование
            st.session_state.current_batch = None
            st.session_state.batch_option_orders = None
            st.session_state.index = 0
            st.session_state.running = False
            st.session_state.show_answer = None
            st.session_state.user_answers = None
            st.session_state.selected_choice_keys = None

    # Если файл не загружен — подсказка
    if uploaded is None:
        st.info("Пожалуйста, загрузите .docx файл с тестом. Варианты ответов должны идти после строки с '№'.\n"
                "Правильный вариант помечается красным цветом (RGB FF0000). Альтернатива: поставьте '*' в начале строки варианта.")
        return

    all_q = st.session_state.all_questions or []
    st.success(f"Найдено вопросов с отмеченными правильными ответами: {len(all_q)}")

    if not all_q:
        st.warning("В этом файле не найдено вопросов с помеченными правильными ответами. Убедитесь, что правильные ответы выделены красным цветом (RGB FF0000) или поставьте '*' перед правильным вариантом.")
        return

    # ------- Меню: выбрать количество и начать -------
    if not st.session_state.running:
        st.subheader("Настройки теста")
        count = st.slider("Сколько вопросов взять?", min_value=1, max_value=len(all_q), value=min(10, len(all_q)))
        cols = st.columns([1,1,1])
        with cols[0]:
            if st.button("Начать тест"):
                # формируем batch и сопутствующие структуры
                st.session_state.current_batch = random.sample(all_q, count)
                # создаём порядок опций для каждого вопрос и инициализируем show_answer
                orders = []
                for q in st.session_state.current_batch:
                    opts = q["options"].copy()
                    random.shuffle(opts)
                    orders.append(opts)
                st.session_state.batch_option_orders = orders
                st.session_state.index = 0
                st.session_state.show_answer = [False] * count
                st.session_state.user_answers = [None] * count
                st.session_state.selected_choice_keys = [f"choice_{i}" for i in range(count)]
                st.session_state.running = True

        with cols[1]:
            if st.button("Взять все вопросы"):
                count = len(all_q)
                st.session_state.current_batch = random.sample(all_q, count)
                orders = []
                for q in st.session_state.current_batch:
                    opts = q["options"].copy()
                    random.shuffle(opts)
                    orders.append(opts)
                st.session_state.batch_option_orders = orders
                st.session_state.index = 0
                st.session_state.show_answer = [False] * count
                st.session_state.user_answers = [None] * count
                st.session_state.selected_choice_keys = [f"choice_{i}" for i in range(count)]
                st.session_state.running = True

        with cols[2]:
            st.write("")  # placeholder for layout harmony

    # ------- Сам тест: по одному вопросу -------
    if st.session_state.running:
        batch = st.session_state.current_batch
        orders = st.session_state.batch_option_orders
        idx = st.session_state.index
        total = len(batch)

        st.subheader(f"Вопрос {idx+1} из {total}")
        q = batch[idx]
        st.markdown(f"**{q['question']}**")
        st.write("---")

        # Опции для этого вопроса — фиксированные в orders[idx]
        options = orders[idx]

        # Callback для немедленной проверки выбора
        def _on_choice_change():
            # Текущий ключ формируется как f"choice_{idx}"
            key = f"choice_{idx}"
            try:
                val = st.session_state.get(key, None)
            except Exception:
                val = None
            # Сохраняем ответ и помечаем для показа
            st.session_state.user_answers[idx] = val
            st.session_state.show_answer[idx] = True

        # Радио-кнопка с callback (показываем варианты)
        choice_key = f"choice_{idx}"
        # инициализируем ключ, чтобы он существовал
        if choice_key not in st.session_state:
            st.session_state[choice_key] = None

        selected = st.radio("Выберите вариант:", options, key=choice_key, on_change=_on_choice_change)

        # Если ответ выбран и show_answer True — показываем результат
        if st.session_state.show_answer and st.session_state.show_answer[idx]:
            user = st.session_state.user_answers[idx]
            correct = q["correct_text"]

            if user == correct:
                st.success(f"✔ Правильно! — {user}")
            else:
                st.error(f"✘ Неправильно. Ваш ответ: {user}")
                st.info(f"Правильный ответ: **{correct}**")

        st.write("---")
        # Навигация
        nav_cols = st.columns([1,1,1,1])
        with nav_cols[0]:
            if st.button("◀ Предыд. вопрос") and idx > 0:
                st.session_state.index -= 1
        with nav_cols[1]:
            if st.button("Следующий ▶") and idx < total - 1:
                st.session_state.index += 1
        with nav_cols[2]:
            if st.button("Завершить тест"):
                st.session_state.running = False
        with nav_cols[3]:
            if st.button("Перейти к результатам"):
                # Пересчитываем очки и показываем экран результатов
                st.session_state.running = False
                st.session_state.show_results = True

    # ------- Экран результатов -------
    # Показываем результаты, если тест был завершён (или пользователь нажал "Перейти к результатам")
    if not st.session_state.running and st.session_state.current_batch:
        # Если переменная show_results не задана — считаем что пользователь хочет увидеть результаты
        show_results = st.session_state.get("show_results", True)
        if show_results:
            batch = st.session_state.current_batch
            orders = st.session_state.batch_option_orders
            st.subheader("Результаты теста")
            score = 0
            for i, q in enumerate(batch):
                user = st.session_state.user_answers[i]
                correct = q["correct_text"]
                st.markdown(f"**Вопрос {i+1}:** {q['question']}")
                if user == correct:
                    st.success(f"✔ {user}")
                    score += 1
                else:
                    st.error(f"✘ Ваш ответ: {user}")
                    st.info(f"Правильный: **{correct}**")
                st.write("---")

            st.write(f"## Итого: {score} из {len(batch)} ({(score/len(batch))*100:.1f}%)")

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("🔁 Пройти этот же тест заново"):
                    # Сброс ответов, но сохраняем batch и порядок
                    st.session_state.index = 0
                    st.session_state.show_answer = [False] * len(batch)
                    st.session_state.user_answers = [None] * len(batch)
                    # очищаем выбранные ключи в session_state чтобы radio снова пустой
                    for k in st.session_state.selected_choice_keys or []:
                        if k in st.session_state:
                            del st.session_state[k]
                    st.session_state.running = True
                    st.session_state.show_results = False

            with c2:
                if st.button("🆕 Новый тест"):
                    # Сброс всех тестовых данных, оставляем загруженный файл в памяти
                    st.session_state.current_batch = None
                    st.session_state.batch_option_orders = None
                    st.session_state.index = 0
                    st.session_state.show_answer = None
                    st.session_state.user_answers = None
                    st.session_state.selected_choice_keys = None
                    st.session_state.running = False
                    st.session_state.show_results = False

            with c3:
                if st.button("🔚 Выйти (сбросить)"):
                    # Полный сброс, включая загруженный файл
                    st.session_state.questions_hash = None
                    st.session_state.all_questions = None
                    st.session_state.current_batch = None
                    st.session_state.batch_option_orders = None
                    st.session_state.index = 0
                    st.session_state.show_answer = None
                    st.session_state.user_answers = None
                    st.session_state.selected_choice_keys = None
                    st.session_state.running = False
                    st.session_state.show_results = False
                    st.experimental_rerun()  # безопасно вызывать здесь для перезапуска интерфейса

if __name__ == "__main__":
    main()
