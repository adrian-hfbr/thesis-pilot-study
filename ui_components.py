import streamlit as st
import config
import re

def format_legal_text(text):
    """Format German legal text with proper highlighting"""
    # Highlight paragraph headers like "§35a EStG"
    # Highlight paragraph headers like "§35a EStG" 
    # Highlight paragraph headers like "§35a" (WITHOUT following text)
    text = re.sub(r'(§\s*\d+[a-z]?)\b',
                r'<strong style="color: #2c5aa0; font-size: 17px;">\1</strong>',
                text)

    # Highlight subsection numbers like "(1)", "(2)", etc.
    text = re.sub(r'^(\(\d+\))', 
                  r'<strong style="color: #c7254e; margin-right: 10px;">\1</strong>', 
                  text, flags=re.MULTILINE)
    
    # Highlight numbered items like "1.", "2.", etc.
    text = re.sub(r'^(\d+\.)\s', 
                  r'<span style="color: #4a5568; font-weight: 600; margin-left: 20px;">\1</span> ', 
                  text, flags=re.MULTILINE)
    
    # Preserve line breaks
    text = text.replace('\n', '<br>')
    
    return text

def likert_select(question: str, key: str, default: int = 4) -> int:
    st.markdown(f'<span style="font-size: 1.1em">{question}</span>', unsafe_allow_html=True)
    
    st.markdown("""
    <style>
    /* Füge Punkte auf der Slider-Linie hinzu */
    div[data-testid="stSlider"] > div > div > div {
        position: relative;
    }
    
    div[data-testid="stSlider"] > div > div > div::before {
        content: '';
        position: absolute;
        width: 100%;
        height: 12px;
        top: 50%;
        transform: translateY(-50%);
        background-image: 
            radial-gradient(circle, #dc3545 4px, transparent 4px),
            radial-gradient(circle, #dc3545 4px, transparent 4px),
            radial-gradient(circle, #dc3545 4px, transparent 4px),
            radial-gradient(circle, #dc3545 4px, transparent 4px),
            radial-gradient(circle, #dc3545 4px, transparent 4px),
            radial-gradient(circle, #dc3545 4px, transparent 4px),
            radial-gradient(circle, #dc3545 4px, transparent 4px);
        background-size: 12px 12px;
        background-position: 
            0% center,
            16.66% center,
            33.33% center,
            50% center,
            66.66% center,
            83.33% center,
            100% center;
        background-repeat: no-repeat;
        pointer-events: none;
        z-index: 1;
    }
    </style>
    """, unsafe_allow_html=True)
    
    result = st.select_slider(
        label="Rating",
        label_visibility="hidden",
        options=[1, 2, 3, 4, 5, 6, 7],
        value=default,
        format_func=lambda x: config.LIKERT_LABELS_7[x],
        key=key
    )
    
    st.markdown(
        f"""<div style="display: flex; justify-content: space-between; margin-top: -10px; font-size: 0.875em; color: #6c757d;">
        <span>1 = stimme überhaupt nicht zu</span>
        <span>7 = stimme voll und ganz zu</span>
        </div>""",
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.markdown('<div style="margin-bottom: 6px;"></div>', unsafe_allow_html=True)
    
    return result


def likert_select_conf(question: str, key: str, default: int = 4) -> int:
    """
    Likert scale selector specifically for confidence measurements.
    Uses LIKERT_LABELS_CONF from config instead of the standard agreement scale.
    """
    st.markdown(f'<span style="font-size: 1.1em">{question}</span>', unsafe_allow_html=True)
    
    # CSS for visible scale points
    st.markdown("""
    <style>
    /* Add points on the slider line */
    div[data-testid="stSlider"] > div > div > div {
        position: relative;
    }
    
    div[data-testid="stSlider"] > div > div > div::before {
        content: '';
        position: absolute;
        width: 100%;
        height: 12px;
        top: 50%;
        transform: translateY(-50%);
        background-image: 
            radial-gradient(circle, #dc3545 4px, transparent 4px),
            radial-gradient(circle, #dc3545 4px, transparent 4px),
            radial-gradient(circle, #dc3545 4px, transparent 4px),
            radial-gradient(circle, #dc3545 4px, transparent 4px),
            radial-gradient(circle, #dc3545 4px, transparent 4px),
            radial-gradient(circle, #dc3545 4px, transparent 4px),
            radial-gradient(circle, #dc3545 4px, transparent 4px);
        background-size: 12px 12px;
        background-position: 
            0% center,
            16.66% center,
            33.33% center,
            50% center,
            66.66% center,
            83.33% center,
            100% center;
        background-repeat: no-repeat;
        pointer-events: none;
        z-index: 1;
    }
    </style>
    """, unsafe_allow_html=True)
    
    result = st.select_slider(
        label="Rating",
        label_visibility="hidden",
        options=[1, 2, 3, 4, 5, 6, 7],
        value=default,
        format_func=lambda x: config.LIKERT_LABELS_CONF[x],
        key=key
    )
    
    st.markdown(
        f"""<div style="display: flex; justify-content: space-between; margin-top: -10px; font-size: 0.875em; color: #6c757d;">
        <span>1 = sehr unsicher</span>
        <span>7 = sehr sicher</span>
        </div>""",
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.markdown('<div style="margin-bottom: 6px;"></div>', unsafe_allow_html=True)
    
    return result

def likert_select_6(question: str, key: str, default: int = 4) -> int:
    """6-point Likert scale selector for ATI items."""
    st.markdown(f'<span style="font-size: 1.1em">{question}</span>', unsafe_allow_html=True)
    
    # CSS targeting only this specific slider using the key
    st.markdown(f"""
    <style>
    /* Target only 6-point sliders using their unique key */
    .st-key-{key} div[data-testid="stSlider"] > div > div > div::before {{
        content: '';
        position: absolute;
        width: 100%;
        height: 12px;
        top: 50%;
        transform: translateY(-50%);
        background-image: 
            radial-gradient(circle, #dc3545 4px, transparent 4px),
            radial-gradient(circle, #dc3545 4px, transparent 4px),
            radial-gradient(circle, #dc3545 4px, transparent 4px),
            radial-gradient(circle, #dc3545 4px, transparent 4px),
            radial-gradient(circle, #dc3545 4px, transparent 4px),
            radial-gradient(circle, #dc3545 4px, transparent 4px);
        background-size: 12px 12px;
        background-position: 
            0% center,
            20% center,
            40% center,
            60% center,
            80% center,
            100% center;
        background-repeat: no-repeat;
        pointer-events: none;
        z-index: 1;
    }}
    </style>
    """, unsafe_allow_html=True)
    
    result = st.select_slider(
        label="Rating",
        label_visibility="hidden",
        options=[1, 2, 3, 4, 5, 6],
        value=default,
        format_func=lambda x: config.LIKERT_LABELS_6[x],
        key=key
    )
    
    st.markdown(
        f"""<div style="display: flex; justify-content: space-between; margin-top: -10px; font-size: 0.875em; color: #6c757d;">
        <span>1 = stimmt gar nicht</span>
        <span>6 = stimmt völlig</span>
        </div>""",
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.markdown('<div style="margin-bottom: 6px;"></div>', unsafe_allow_html=True)
    
    return result
