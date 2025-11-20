import streamlit as st
import config
import re

def format_legal_text(text):
    """Highlight German legal text: paragraphs (§), subsections ((1)), and numbered items (1.) with colored styling."""
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
    """Render 7-point Likert scale with hidden labels until user interacts, showing response label post-selection."""
    # Initialize session state
    interaction_key = f"{key}_interacted"
    
    if interaction_key not in st.session_state:
        st.session_state[interaction_key] = False
    
    st.markdown(f'<span style="font-size: 1.1em">{question}</span>', unsafe_allow_html=True)
    
    # CSS FOR DOTS - ALWAYS SHOW (GLOBAL, NOT SCOPED TO KEY)
    st.markdown(f"""
    <style>
    /* Show red dots - ALWAYS VISIBLE */
    div[data-testid="stSlider"] > div > div > div::before {{
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
    }}
    </style>
    """, unsafe_allow_html=True)
    
    # CSS FOR THUMB VISIBILITY - CONDITIONAL
    if st.session_state[interaction_key]:
        st.markdown(f"""
        <style>
        /* Make thumb visible after interaction */
        div[data-testid="stSlider"] [role="slider"] {{
            opacity: 1 !important;
        }}
        </style>
        """, unsafe_allow_html=True)
    else:
        # Before interaction: only fade the thumb, NOT the track
        st.markdown(f"""
        <style>
        /* Make only the thumb subtle before interaction */
        div[data-testid="stSlider"] [role="slider"] {{
            opacity: 0.15 !important;
            cursor: pointer;
        }}
        </style>
        """, unsafe_allow_html=True)
    
    # Callback function
    def mark_interacted():
        if not st.session_state[interaction_key]:
            st.session_state[interaction_key] = True
    
    # Render slider
    result = st.select_slider(
        label="Rating",
        label_visibility="hidden",
        options=[1, 2, 3, 4, 5, 6, 7],
        value=1,
        format_func=lambda x: "",
        key=key,
        on_change=mark_interacted
    )
    
    st.markdown(
        f"""<div style="display: flex; justify-content: space-between; margin-top: -10px; font-size: 0.875em; color: #6c757d;">
        <span>1 = stimme überhaupt nicht zu</span>
        <span>7 = stimme voll und ganz zu</span>
        </div>""",
        unsafe_allow_html=True
    )
    
    if st.session_state[interaction_key]:
        st.markdown(
            f"""
            <div style="display: flex; justify-content: center; margin-bottom: 12px; font-size: 0.9em; color: #dc3545; font-weight: 600;">
            {config.LIKERT_LABELS_7[result]}
            </div>
            """,
            unsafe_allow_html=True
        )
    
    st.markdown("---")
    st.markdown('<div style="margin-bottom: 6px;"></div>', unsafe_allow_html=True)
    
    return result


def likert_select_conf(question: str, key: str, default: int = 4) -> int:
    """Render 7-point confidence Likert scale (very unsure to very sure) with conditional label reveal."""
    
    # Initialize session state
    interaction_key = f"{key}_interacted"
    
    if interaction_key not in st.session_state:
        st.session_state[interaction_key] = False
    
    st.markdown(f'<span style="font-size: 1.1em">{question}</span>', unsafe_allow_html=True)
    
    # CSS FOR DOTS - ALWAYS SHOW (GLOBAL, NOT SCOPED TO KEY)
    st.markdown(f"""
    <style>
    /* Show red dots - ALWAYS VISIBLE */
    div[data-testid="stSlider"] > div > div > div::before {{
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
    }}
    </style>
    """, unsafe_allow_html=True)
    
    # CSS FOR THUMB VISIBILITY - CONDITIONAL
    if st.session_state[interaction_key]:
        st.markdown(f"""
        <style>
        /* Make thumb visible after interaction */
        div[data-testid="stSlider"] [role="slider"] {{
            opacity: 1 !important;
        }}
        </style>
        """, unsafe_allow_html=True)
    else:
        # Before interaction: only fade the thumb, NOT the track
        st.markdown(f"""
        <style>
        /* Make only the thumb subtle before interaction */
        div[data-testid="stSlider"] [role="slider"] {{
            opacity: 0.15 !important;
            cursor: pointer;
        }}
        </style>
        """, unsafe_allow_html=True)
    
    # Callback function
    def mark_interacted():
        if not st.session_state[interaction_key]:
            st.session_state[interaction_key] = True
    
    # Render slider
    result = st.select_slider(
        label="Rating",
        label_visibility="hidden",
        options=[1, 2, 3, 4, 5, 6, 7],
        value=1,
        format_func=lambda x: "",
        key=key,
        on_change=mark_interacted
    )
    
    st.markdown(
        f"""<div style="display: flex; justify-content: space-between; margin-top: -10px; font-size: 0.875em; color: #6c757d;">
        <span>1 = sehr unsicher</span>
        <span>7 = sehr sicher</span>
        </div>""",
        unsafe_allow_html=True
    )
    
    if st.session_state[interaction_key]:
        st.markdown(
            f"""
            <div style="display: flex; justify-content: center; margin-bottom: 12px; font-size: 0.9em; color: #dc3545; font-weight: 600;">
            {config.LIKERT_LABELS_CONF[result]}
            </div>
            """,
            unsafe_allow_html=True
        )
    
    st.markdown("---")
    st.markdown('<div style="margin-bottom: 6px;"></div>', unsafe_allow_html=True)
    
    return result
