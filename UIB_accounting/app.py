import streamlit as st
import docx
import random
import os
from docx.shared import RGBColor

# --- КОНФИГУРАЦИЯ СТРАНИЦЫ ---
st.set_page_config(
    page_title="Бухучет: Тест", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ФУНКЦИЯ ПАРСИНГА (С КЭШИРОВАНИЕМ) ---

# Декоратор st.cache_data позволяет Streamlit не перечитывать и не парсить
# тяжелый docx файл при каждом действии пользователя, что ускоряет работу.
@st.cache_data
def parse_quiz_file(filename):
    """
    Читает docx файл, ищет вопросы (начинаются с №) и ответы (красным цветом).
    """
    if not os.path.exists(filename):
        # В Streamlit, если файл не найден, мы просто возвращаем пустой список.
        return []

    try:
        doc = docx.Document(filename)
    except Exception as e:
        st.error(f"Не удалось открыть файл: {e}")
        return []

    questions = []
    current_q = None
    RED_HEX = 'FF0000' 

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        if text.startswith("№"):
            if current_q and current_q["correct_text"]: # Добавляем только если есть ответ
                questions.append(current_q)
            current_q = {
                "question": text,
                "options": [],
                "correct_text": None,
                "id": random.getrandbits(16) # Уникальный ID для ключей Streamlit
            }
        
        elif current_q:
            is_correct = False
            for run in para.runs:
                # Проверка на красный цвет
                if run.font.color and run.font.color.rgb and str(run.font.color.rgb) == RED_HEX:
                    is_correct = True
                    break
            
            current_q["options"].append(text)
            if is_correct:
                current_q["correct_text"] = text

    if current_q and current_q["correct_text"]:
        questions.append(current_q)

    return questions

# --- УПРАВЛЕНИЕ ТЕСТОМ (ЛОГИКА) ---

def initialize_session_state():
    """Инициализация состояния при первом запуске или сбросе."""
    if 'quiz_started' not in st.session_state:
        st.session_state.quiz_started = False
    if 'current_batch' not in st.session_state:
        st.session_state.current_batch = []
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0
    if 'score' not in st.session_state:
        st.session_state.score = 0
    if 'show_feedback' not in st.session_state:
        st.session_state.show_feedback = False
    if 'last_correct' not in st.session_state:
        st.session_state.last_correct = None

def start_new_test(all_questions, num):
    """Начинает новый тест, формируя новый случайный набор вопросов."""
    st.session_state.current_batch = random.sample(all_questions, num)
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.quiz_started = True
    st.session_state.show_feedback = False
    st.session_state.last_correct = None

def check_answer(selected_option):
    """Проверяет ответ и готовит следующее состояние."""
    q = st.session_state.current_batch[st.session_state.current_index]
    
    if selected_option == q["correct_text"]:
        st.session_state.score += 1
        st.session_state.last_correct = True
        st.toast("✅ Правильно!", icon="🎉")
    else:
        st.session_state.last_correct = False
        st.toast(f"❌ Неверно! Ответ: {q['correct_text']}", icon="❌")
        
    st.session_state.show_feedback = True

def next_question():
    """Переход к следующему вопросу."""
    st.session_state.current_index += 1
    st.session_state.show_feedback = False
    st.session_state.last_correct = None

# --- ИНТЕРФЕЙС ПРИЛОЖЕНИЯ ---

def display_quiz_config(all_questions):
    """Экран выбора количества вопросов."""
    st.markdown("### 📝 Настройка теста по Бухучету")
    st.info(f"В базе найдено вопросов: **{len(all_questions)}**")
    
    # Поле ввода для количества вопросов
    num_questions = st.number_input(
        "Сколько вопросов включить в тест?", 
        min_value=1, 
        max_value=len(all_questions), 
        value=min(10, len(all_questions)),
        step=1
    )
    
    if st.button("Начать тест", use_container_width=True, type="primary"):
        start_new_test(all_questions, num_questions)
        # st.rerun() не нужен, так как Streamlit перерисовывается после нажатия кнопки

def display_quiz_flow():
    """Экран прохождения теста."""
    questions = st.session_state.current_batch
    idx = st.session_state.current_index
    n = len(questions)

    # Завершение теста
    if idx >= n:
        display_results()
        return

    q = questions[idx]
    
    st.markdown(f"**Вопрос {idx + 1} из {n}** | Счет: {st.session_state.score}/{idx}")
    st.progress(idx / n)
    
    st.markdown(f"#### {q['question']}")
    st.divider()

    # Перемешиваем варианты ответов (если еще не перемешивали для этого вопроса)
    if f"shuffled_opts_{q['id']}" not in st.session_state:
        opts = q["options"].copy()
        random.shuffle(opts)
        st.session_state[f"shuffled_opts_{q['id']}]"] = opts
    
    options = st.session_state[f"shuffled_opts_{q['id']}]"]

    # Кнопки вариантов ответов
    for opt in options:
        
        # Если фидбек показан, выделяем правильный ответ зеленым
        is_correct_option = (opt == q["correct_text"])
        
        button_type = "secondary"
        if st.session_state.show_feedback:
            if is_correct_option:
                button_type = "primary" # Зеленый для правильного
            elif opt == st.session_state.selected_option and not is_correct_option:
                button_type = "danger" # Красный для неправильно выбранного
                
        # Кнопки неактивны после выбора
        disabled = st.session_state.show_feedback
        
        st.button(
            opt, 
            key=f"opt_{q['id']}_{opt}", 
            on_click=check_answer_wrapper, 
            args=(opt, q["correct_text"]),
            use_container_width=True,
            disabled=disabled,
            type=button_type
        )
        
    # Кнопка "Далее" появляется только после ответа
    if st.session_state.show_feedback:
        st.button(
            "👉 Следующий вопрос", 
            on_click=next_question, 
            use_container_width=True
        )

def check_answer_wrapper(selected_option, correct_answer):
    """Обёртка для проверки ответа и сохранения выбранной опции."""
    st.session_state.selected_option = selected_option
    check_answer(selected_option)


def display_results():
    """Экран результатов теста."""
    n = len(st.session_state.current_batch)
    score = st.session_state.score
    percent = (score / n) * 100 if n > 0 else 0
    
    st.markdown("---")
    st.header("🎉 Тест завершен!")
    
    if percent == 100:
        st.balloons()
        st.success("## ИДЕАЛЬНО! Браво!")
    elif percent >= 75:
        st.info("## Отличный результат!")
    else:
        st.warning("## Есть над чем поработать. Повторите!")
        
    st.metric(label="Финальный счет", value=f"{score} из {n}", delta=f"{percent:.1f}%")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Повторить этот же тест (сбрасывает индекс, сохраняет вопросы)
        if st.button("🔄 Повторить ЭТОТ ЖЕ тест", use_container_width=True):
            st.session_state.current_index = 0
            st.session_state.score = 0
            st.session_state.show_feedback = False
            st.rerun()

    with col2:
        # Новый тест (возвращает на экран настройки)
        if st.button("🆕 Сформировать НОВЫЙ тест", use_container_width=True, type="secondary"):
            st.session_state.quiz_started = False
            st.rerun()

# --- ОСНОВНАЯ ФУНКЦИЯ ЗАПУСКА ---
def main():
    initialize_session_state()
    file_name = "бух учет сессия.docx"
    
    # Загрузка базы вопросов
    all_questions = parse_quiz_file(file_name)
    
    if not all_questions:
        st.error(f"Не удалось загрузить вопросы из файла: '{file_name}'.")
        st.write("Убедитесь, что:")
        st.markdown("- Файл `.docx` находится в той же папке, что и `app.py`.")
        st.markdown("- Ответы выделены **стандартным красным цветом** (RGB: FF0000).")
        return

    # Отображение нужного экрана
    if not st.session_state.quiz_started:
        display_quiz_config(all_questions)
    else:
        display_quiz_flow()

if __name__ == '__main__':
    main()
