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
    doc = docx.Documen
