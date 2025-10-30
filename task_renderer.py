"""
task_renderer.py

This module contains all rendering logic for the chat/task interface.
Extracted from app.py to improve modularity and maintainability.

Functions handle:
- Task header rendering
- Message list display
- Augmented condition quote buttons
- Minimal condition modal buttons
- User input handling
"""

import streamlit as st
import re
from datetime import datetime
from behavioral_tracking import (
    update_last_action_time,
    finalize_open_quotes,
    track_quote_toggle,
    track_modal_button_click
)
from utils import log_interaction


def render_task_header(task):
    """
    Renders the task header with scenario, question, and instructions.
    
    Args:
        task: Task dictionary from content.TASKS containing name, scenario, question
    """
    with st.container(border=True):
        # CSS to prevent text selection in this container
        st.markdown("""
            <style>
            .element-container {
                -webkit-user-select: none;
                -moz-user-select: none;
                -ms-user-select: none;
                user-select: none;
            }
            </style>
        """, unsafe_allow_html=True)
        
        st.subheader(task["name"])
        st.markdown(task["scenario"])
        st.markdown(f"**Ihre Aufgabe:** {task['question']}")
        
        # Info-Box should remain selectable
        st.markdown("""
            <style>
            div[data-testid="stAlert"] {
                -webkit-user-select: text !important;
                -moz-user-select: text !important;
                -ms-user-select: text !important;
                user-select: text !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        st.info("Nutzen Sie nun den KI-Assistenten, um die korrekte Antwort zu finden.")


def render_augmented_buttons(doc, legal_ref, url, message_index, task_number, quote, show_source_modal_callback):
    """
    Renders quote expander and modal button for Augmented condition.
    
    Args:
        doc: Document object with metadata
        legal_ref: Legal reference string
        url: Source URL
        message_index: Index of the message in the message list (used for unique keys)
        task_number: Current task number
        quote: Quote text to display
        show_source_modal_callback: Callback function to open modal
    """
    quote_visible_key = f"quote_visible_{message_index}"
    
    # Initialize visibility state
    if quote_visible_key not in st.session_state:
        st.session_state[quote_visible_key] = False
    
    # Toggle button
    button_label = "Zitat ausblenden ▲" if st.session_state[quote_visible_key] else "Zitat anzeigen ▼"
    
    button_key = f"btn_quote_{message_index}"
    if st.button(button_label, key=button_key, use_container_width=True):
        # Calculate opening/closing BEFORE toggling
        is_opening = not st.session_state[quote_visible_key]
        
        st.session_state[quote_visible_key] = not st.session_state[quote_visible_key]
        
        # ALWAYS track the toggle (NO GUARD - expanders need both open and close tracked)
        track_quote_toggle(
            quote_key=message_index,
            is_opening=is_opening,
            task_number=task_number,
            legal_ref=legal_ref,
            url=url
        )
        update_last_action_time()
        
        st.rerun()


    
    # Display quote if visible
    if st.session_state[quote_visible_key]:
        st.markdown(f"""
            <div style="background-color: #e8f4f8; border-left: 4px solid #1f77b4; padding: 15px; margin: 10px 0; border-radius: 5px;">
                <em>{quote}</em>
            </div>
        """, unsafe_allow_html=True)
    
    # Modal button
    modal_button_key = f"btn_modal_aug_{message_index}"
    if st.button("Gesetzestext anzeigen", key=modal_button_key, use_container_width=True):
        finalize_open_quotes()
        track_modal_button_click()
        update_last_action_time()
        # Debounce: only track if this button hasn't been processed
        if modal_button_key not in st.session_state.button_clicks_processed:
            st.session_state.button_clicks_processed.add(modal_button_key)
            
            log_interaction(
                session_id=st.session_state.session_id,
                task_number=task_number,
                event_type="modal_augmented",
                details=f"{legal_ref}|url={url}"
            )
        
        st.session_state.modal_doc = doc
        show_source_modal_callback()


def render_minimal_buttons(doc, legal_ref, url, message_index, task_number, show_source_modal_callback):
    """
    Renders modal button for Minimal condition (no quote expander).
    
    Args:
        doc: Document object with metadata
        legal_ref: Legal reference string
        url: Source URL
        message_index: Index of the message in the message list (used for unique keys)
        task_number: Current task number
        show_source_modal_callback: Callback function to open modal
    """
    modal_button_key = f"btn_modal_min_{message_index}"
    if st.button("Gesetzestext anzeigen", key=modal_button_key, use_container_width=True):
        finalize_open_quotes()
        track_modal_button_click()
        update_last_action_time()
        if modal_button_key not in st.session_state.button_clicks_processed:
            st.session_state.button_clicks_processed.add(modal_button_key)
            
            log_interaction(
                session_id=st.session_state.session_id,
                task_number=task_number,
                event_type="modal_minimal",
                details=f"{legal_ref}|url={url}"
            )
        st.session_state.modal_doc = doc
        show_source_modal_callback()


def render_message_list(messages, task_number, show_source_modal_callback):
    """
    Renders all messages in the chat, including buttons for the last assistant message.
    
    Args:
        messages: List of message dictionaries with 'role', 'content', 'context', etc.
        task_number: Current task number
        show_source_modal_callback: Callback function to open modal
    """
    if 'button_clicks_processed' not in st.session_state:
        st.session_state.button_clicks_processed = set()

    for i, message in enumerate(messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            if message["role"] == "assistant" and message.get("context"):
                # Skip if no answer or no context
                if message.get("no_answer") or len(message.get("context", [])) == 0:
                    continue
                
                # Check if this is the LAST assistant message
                is_last_assistant = (i == len(messages) - 1)
                
                # ONLY render buttons/expanders for the last assistant message
                if is_last_assistant:
                    st.markdown("---")
                    
                    doc = message["context"][0]
                    legal_ref = message.get("legal_reference", "Unbekannte Quelle")
                    url = doc.metadata.get("url", "")
                    
                    if st.session_state.group == "Augmented":
                        quote = message.get("quote", "Kein Zitat verfügbar.")
                        render_augmented_buttons(
                            doc=doc,
                            legal_ref=legal_ref,
                            url=url,
                            message_index=i,
                            task_number=task_number,
                            quote=quote,
                            show_source_modal_callback=show_source_modal_callback
                        )
                    else:  # Minimal condition
                        render_minimal_buttons(
                            doc=doc,
                            legal_ref=legal_ref,
                            url=url,
                            message_index=i,
                            task_number=task_number,
                            show_source_modal_callback=show_source_modal_callback
                        )


def _validate_user_input(user_query):
    """
    Validates and sanitizes user input before RAG processing.
    
    NEW FUNCTION - Added for input validation (Fix #2: Chat Input Validation)
    
    Args:
        user_query: Raw user input string
        
    Returns:
        tuple: (is_valid: bool, sanitized_query: str, error_message: str)
    """
    # Sanitize: strip whitespace
    sanitized = user_query.strip()
    
    # Check 1: Empty input
    if len(sanitized) == 0:
        return False, "", "Bitte geben Sie eine Frage ein."
    
    # Check 2: Minimum length
    if len(sanitized) < 3:
        return False, "", "Ihre Frage ist zu kurz. Bitte geben Sie mindestens 3 Zeichen ein."
    
    # Check 3: Maximum length
    if len(sanitized) > 500:
        return False, "", "Ihre Frage ist zu lang. Bitte kürzen Sie sie auf maximal 500 Zeichen."
    
    # All checks passed
    return True, sanitized, ""


def handle_user_input(user_input, task_number, history_key, pipeline):
    """
    Handles user input: logs interaction, calls RAG pipeline, updates state.
    
    MODIFIED: Added input validation (Fix #2: Chat Input Validation)
    
    Args:
        user_input: User's query string
        task_number: Current task number
        history_key: Session state key for chat history (e.g., "task_1_history")
        pipeline: RAG pipeline instance for generating responses
    """

    is_valid, sanitized_query, error_message = _validate_user_input(user_input)
    
    if not is_valid:
        # Show error message to user and stop processing
        st.warning(error_message)
        return
        
    finalize_open_quotes()
    
    update_last_action_time()
    
    # Determine event type (initial vs follow-up)
    event_type = "initial_question" if st.session_state.question_count == 0 else "followup_question"
    
    log_interaction(
        session_id=st.session_state.session_id,
        task_number=task_number,
        event_type=event_type,
        details=sanitized_query, 
    )
    
    st.session_state.question_count += 1
    
    # Track follow-ups separately (excluding initial)
    if event_type == "followup_question":
        st.session_state.followup_count += 1
    
    st.session_state.messages.append({"role": "user", "content": sanitized_query})
    
    with st.spinner("Antwort wird generiert..."):
        response_dict = pipeline.get_response(
            sanitized_query,  # Use sanitized version
            st.session_state.group,
            chat_history=st.session_state[history_key]
        )
    
    # Handle no-answer case
    if response_dict.get("no_answer", False):
        assistant_message = {
            "role": "assistant",
            "content": response_dict["answer"],
            "context": [],
            "legal_reference": None
        }
    else:
        assistant_message = {
            "role": "assistant",
            "content": response_dict["answer"],
            "context": response_dict.get("context", []),
            "quote": response_dict.get("quote"),
            "legal_reference": response_dict.get("legal_reference")
        }
    
    st.session_state.messages.append(assistant_message)
    
    st.session_state.last_answer_time = datetime.now()
    st.session_state.answer_reading_recorded = False
    
    log_interaction(
        session_id=st.session_state.session_id,
        task_number=task_number,
        event_type="ai_response",
        details=response_dict["answer"]
    )

    st.session_state[history_key].append({
        "query": sanitized_query,
        "answer": response_dict["answer"]
    })
