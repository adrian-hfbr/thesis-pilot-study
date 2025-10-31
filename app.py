import streamlit as st
import config
import content
import nest_asyncio
import warnings
import random
import os
import pandas as pd
from datetime import datetime
from rag_pipeline import RAGPipeline as _RAG
from ui_components import (
    likert_select,
    likert_select_conf,
    likert_select_6,
    format_legal_text
)
from behavioral_tracking import (
    update_last_action_time,
    finalize_open_quotes,
    finalize_modal_tracking,
    calculate_final_metrics
)

from task_renderer import (
    render_task_header,
    render_message_list,
    handle_user_input
)

from utils import get_session_id, initialize_log_files, log_participant_info, log_task_data, log_interaction, log_post_survey


# --- Application Setup ---
warnings.filterwarnings("ignore", category=UserWarning, message=".*verbose.*")
nest_asyncio.apply()
st.set_page_config(
    page_title="KI-Steuerassistent", 
    page_icon="💼", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

initialize_log_files()

@st.cache_resource
def load_rag_pipeline():
    """Initializes and caches the RAG pipeline."""
    return _RAG(config)


@st.cache_resource
def load_full_documents():
    """
    Loads the full text of source documents into memory for the modal view.
    This is crucial for the minimal condition to ensure the full document is shown.
    """
    docs = {}
    source_file_map = {
        'estg_6.txt': 'estg_6.txt',
        'estg_9.txt': 'estg_9.txt',
        'estg_20.txt': 'estg_20.txt',
        'estg_35a.txt': 'estg_35a.txt',
    }
    
    loaded_content = {}
    for disk_filename in set(source_file_map.values()):
        try:
            with open(os.path.join('data', disk_filename), 'r', encoding='utf-8') as f:
                loaded_content[disk_filename] = f.read()
        except FileNotFoundError:
            st.error(f"Source file not found: {disk_filename}. Please ensure it is in the 'data' directory.")
            loaded_content[disk_filename] = f"Error: Source file '{disk_filename}' could not be loaded."

    for rag_source_name, disk_filename in source_file_map.items():
        docs[rag_source_name] = loaded_content.get(disk_filename, "Error: Content not loaded.")

    return docs

pipeline = load_rag_pipeline()
full_documents = load_full_documents()

# --- Session State Initialization ---
def initialize_session_state():
    """Sets up the session state for a new participant. This runs only once per session."""
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 'consent'
        st.session_state.task_number = 1
        st.session_state.group = random.choice(['Augmented', 'Minimal'])
        
    if 'experiment_start_time' not in st.session_state:
        st.session_state.experiment_start_time = datetime.now()
        st.session_state.session_id = get_session_id()
        
        prolific_pid = ""
        try:
            prolific_pid = st.query_params.get("PROLIFIC_PID", "")
        except Exception:
            pass
        st.session_state.prolific_pid = prolific_pid
        
        st.session_state.messages = []
        st.session_state.responses = {}
        st.session_state.task_start_time = None
        st.session_state.question_count = 0
        
        # Existing counters
        st.session_state.expander_clicks_total = 0
        st.session_state.modal_clicks_total = 0
        st.session_state.followup_count = 0
        st.session_state.modal_opened_time = None
        st.session_state.modal_doc = None
        st.session_state.expanded_quotes = set()
        
        # Enhanced time tracking variables
        st.session_state.last_answer_time = None
        st.session_state.last_action_time = None
        st.session_state.answer_reading_times = []
        st.session_state.answer_reading_recorded = False
        st.session_state.answer_finalization_start_time = None
        
        # Cumulative dwell time counters
        st.session_state.cumulative_modal_dwell = 0
        st.session_state.cumulative_expander_dwell = 0
        
        # Sequential behavior tracking
        st.session_state.first_click_happened = False
        st.session_state.first_click_latency = None
        st.session_state.clicks_after_followups = 0
        
        # Expander tracking for dwell time calculation
        st.session_state.expander_open_times = {}  # Dict: {key: datetime}
        st.session_state.last_expander_key = None

        st.session_state.expander_clicks_verification = 0  # Only clicks >= threshold
        st.session_state.modal_clicks_verification = 0     # Only clicks >= threshold

        st.session_state.prompts_before_first_verification = None
        st.session_state.expander_then_modal_escalations = 0
        st.session_state.last_expander_click_time = None

        # Initialize task-scoped histories
        for task_num in range(1, 5):  # You have 4 tasks
            if f"task_{task_num}_history" not in st.session_state:
                st.session_state[f"task_{task_num}_history"] = []

initialize_session_state()

# --- Modal for Source Verification ---
@st.dialog("Quelle", width="large")
def show_source_modal():
    doc = st.session_state.get("modal_doc")
    if not doc:
        st.warning("Keine Quelle zum Anzeigen ausgewählt.")
        if st.button("Schließen"):
            st.session_state.modal_doc = None
            # NEW: Clear all modal button guards so they can be clicked again
            if 'button_clicks_processed' in st.session_state:
                keys_to_remove = [k for k in st.session_state.button_clicks_processed 
                                if k.startswith('btn_modal_')]
                for key in keys_to_remove:
                    st.session_state.button_clicks_processed.discard(key)
            st.rerun()
        return
    
    # Track modal open time when first opened
    if st.session_state.modal_opened_time is None:
        st.session_state.modal_opened_time = datetime.now()
    
    legal_ref = doc.metadata.get('legal_reference_full', doc.metadata.get('legal_reference', 'Unbekannte Quelle'))
    
    st.info(f"Hier sehen Sie den vollständigen Paragraphen ({legal_ref}). Sie müssen die relevante Passage selbst finden.")
    
    full_text = doc.page_content
    source_file = doc.metadata.get('source_file', '')
    
    if source_file:
        try:
            filepath = os.path.join("data", source_file)
            with open(filepath, 'r', encoding='utf-8') as f:
                full_text = f.read()
        except Exception as e:
            full_text = doc.page_content  # Fallback
    else:
        full_text = doc.page_content

    formatted_text = format_legal_text(full_text)

    st.markdown(
        f"""
        <div style="height: 600px; overflow-y: auto; 
                    border: 2px solid #e2e8f0; 
                    padding: 30px; 
                    border-radius: 10px; 
                    background: linear-gradient(to bottom, #ffffff, #f8f9fa);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <div style="font-family: 'Palatino', 'Georgia', serif; 
                        font-size: 16px; 
                        line-height: 1.9; 
                        color: #1a202c;">
                {formatted_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    


    if st.button("**Schließen**", use_container_width=True):
        finalize_modal_tracking(doc)
        update_last_action_time()
        st.rerun()

# --- Screen Rendering Functions ---
def render_consent():
    st.header("Einverständniserklärung")
    st.markdown(content.CONSENT_TEXT)
    
    if st.button("Ich stimme zu und möchte fortfahren"):
        st.session_state.current_step = "instructions"
        st.rerun()


def render_instructions_and_comprehension():
    group = st.session_state.group  # "Augmented" or "Minimal"
    st.header("Anleitung")
    
    # Display instructions with integrated images based on condition
    if group == "Minimal":
        st.markdown(content.INSTRUCTIONS_BY_CONDITION["Minimal"])
        st.image("assets/mehr_kontext.png", 
                caption="Button 'Gesetzestext anzeigen' für den vollständigen Paragraphen",
                use_container_width=True)
        st.markdown(content.INSTRUCTIONS_BY_CONDITION["Minimal_continuation"])
        st.image("assets/schliessen.png", 
                caption="Fenster mit vollständigem Paragraphen und 'Schließen'-Button",
                use_container_width=True)
        st.markdown(content.INSTRUCTIONS_BY_CONDITION["Minimal_end"])
    
    elif group == "Augmented":
        st.markdown(content.INSTRUCTIONS_BY_CONDITION["Augmented"])
        st.image("assets/zitat_anzeigen.png", 
                caption="'Zitat anzeigen'-Button für sofortigen Zugriff auf das Zitat",
                use_container_width=True)
        st.markdown(content.INSTRUCTIONS_BY_CONDITION["Augmented_continuation1"])
        st.image("assets/zitat_ausblenden.png", 
                caption="Geöffnetes Zitat mit 'Zitat ausblenden'-Option",
                use_container_width=True)
        st.markdown(content.INSTRUCTIONS_BY_CONDITION["Augmented_continuation2"])
        st.image("assets/mehr_kontext.png", 
                caption="Button 'Gesetzestext anzeigen' für den vollständigen Paragraphen",
                use_container_width=True)
        st.markdown(content.INSTRUCTIONS_BY_CONDITION["Augmented_continuation3"])
        st.image("assets/schliessen.png", 
                use_container_width=True)
        st.markdown(content.INSTRUCTIONS_BY_CONDITION["Augmented_end"])
    
    st.divider()
    st.subheader("Verständnisfragen")
    
    if "comp_answers" not in st.session_state:
        st.session_state.comp_answers = {}
    
    questions = content.COMPREHENSION_BY_CONDITION["Augmented"] if group == "Augmented" else content.COMPREHENSION_BY_CONDITION["Minimal"]
    all_correct = True
    
    for idx, q in enumerate(questions, start=1):
        st.markdown(f"**Frage {idx}:** {q['question']}")
        choice = st.radio(
            "Bitte wählen:",
            q["options"],
            key=f"comp_q_{idx}",
            index=None,
        )
        st.session_state.comp_answers[idx] = choice
        
        if choice is None:
            all_correct = False
        else:
            if q["options"].index(choice) != q["correct_index"]:
                all_correct = False
        st.markdown("")
    
    cols = st.columns([1, 1])
    with cols[0]:
        if st.button("Weiter"):
            if all_correct:
                st.session_state.current_step = "pre_study_survey"
                st.rerun()
            else:
                st.error("Mindestens eine Antwort ist nicht korrekt. Bitte prüfen Sie die Anweisungen und beantworten Sie alle Fragen richtig, um fortzufahren.")



def render_survey(surveydict, next_step):
    st.header(surveydict["title"])
    responses = {}
    ati_items = surveydict.get("ati_items", [])

    # Generic single-scale "items" (used by PRE_STUDY_SURVEY)
    if "items" in surveydict:
        for key, question in surveydict["items"].items():
            # Use 6-point scale for ATI items, 7-point for others
            if key in ati_items:
                responses[key] = likert_select_6(question, key, default=4)
            else:
                responses[key] = likert_select(question, key, default=4)

    
    # Manipulation check (multiple choice)
    if "manipulation_check" in surveydict:
        st.subheader("Bewertung des KI-Assistenten")
        for key, mc in surveydict["manipulation_check"].items():
            question = mc.get("question", "")
            options = mc.get("options", [])
            # Render question as subheader for consistency with other survey items
            st.markdown(f"**{question}**")
            
            responses[key] = st.radio(
                label=question,
                options=options,
                index=None,
                key=key,
                label_visibility="collapsed"
            )
        st.divider()
    
    # Intrinsic Cognitive Load
    if "icl_items" in surveydict:
        st.subheader("Inhaltliche Anforderungen")
        for key, question in surveydict["icl_items"].items():
            responses[key] = likert_select(question, key, default=4)
    
    # Extraneous Cognitive Load
    if "ecl_items" in surveydict:
        st.subheader("Bewertung der Interaktion")
        for key, question in surveydict["ecl_items"].items():
            responses[key] = likert_select(question, key, default=4)
    
    # Germane Cognitive Load
    if "gcl_items" in surveydict:
        st.subheader("Lernbezogene Verarbeitung")
        for key, question in surveydict["gcl_items"].items():
            responses[key] = likert_select(question, key, default=4)

    # Render EFFORT items
    #if "effort_items" in surveydict:
    #    st.subheader("Anstrengung bei der Aufgabenbearbeitung")
    #    for key, question in surveydict["effort_items"].items():
    #        responses[key] = likert_select(question, key, default=4)

    # Render RELIANCE items
    #if "reliance_items" in surveydict:
    #    st.subheader("Bereitschaft zu akzeptieren")
    #    for key, question in surveydict["reliance_items"].items():
    #        responses[key] = likert_select(question, key, default=4)
    
    # Trust (functionality, helpfulness, reliability)
    if "trust_items" in surveydict:
        st.subheader("Bewertung des Systems")
        for key, question in surveydict["trust_items"].items():
            responses[key] = likert_select(question, key, default=4)
    
    if st.button("Absenden"):
        # Validation: Check if manipulation check questions are answered
        if "manipulation_check" in surveydict:
            all_manip_answered = True
            for key in surveydict["manipulation_check"].keys():
                if responses.get(key) is None:
                    all_manip_answered = False
                    break
            
            if not all_manip_answered:
                st.error("Bitte beantworten Sie die Fragen, bevor Sie fortfahren.")
                return
        # Pre-study survey logging
        if surveydict["title"] == content.PRE_STUDY_SURVEY["title"]:
            log_participant_info(
                session_id=st.session_state.session_id,
                prolific_pid=st.session_state.prolific_pid,
                group=st.session_state.group,
                survey_responses=responses,
                total_duration=None  # Not finished yet
            )
            st.session_state.current_step = next_step
            st.rerun()
        
        # Post-study survey logging
        elif surveydict["title"] == content.POST_STUDY_SURVEY["title"]:
            # Calculate and STORE duration
            if hasattr(st.session_state, 'experiment_start_time') and st.session_state.experiment_start_time:
                st.session_state.total_experiment_duration = (datetime.now() - st.session_state.experiment_start_time).total_seconds()
            
            # Check manipulation check correctness based on participant's condition
            manip_check_passed = None
            if "manipulation_check" in surveydict:
                manip_check_passed = True
                user_group = st.session_state.group  # "Augmented" or "Minimal"
                
                for key, mc in surveydict["manipulation_check"].items():
                    user_answer = responses.get(key)
                    
                    # Get the correct index for this participant's condition
                    if user_group == "Augmented":
                        correct_idx = mc.get("correct_index_augmented")
                    else:  # Minimal
                        correct_idx = mc.get("correct_index_minimal")
                    
                    if user_answer and correct_idx is not None:
                        # Check if user's answer matches the condition-specific correct index
                        user_answer_idx = mc["options"].index(user_answer)
                        if user_answer_idx != correct_idx:
                            manip_check_passed = False
                            break
            
            log_post_survey(
                session_id=st.session_state.session_id,
                survey_responses=responses,
                manip_check_correct=manip_check_passed
            )

            if hasattr(st.session_state, 'total_experiment_duration') and 'duration_logged' not in st.session_state:
                df = pd.read_csv('logs/participants.csv')
                df.loc[df['session_id'] == st.session_state.session_id, 'total_duration_seconds'] = st.session_state.total_experiment_duration
                df.to_csv('logs/participants.csv', index=False)
                st.session_state.duration_logged = True

            # ===== NEW: BACKUP TO S3 =====
            from backup_manager import backup_participant_data
            
            # Get Prolific ID
            prolific_pid = st.session_state.get('prolific_pid', 'UNKNOWN')
            
            # Backup this participant's data to S3
            backup_success = backup_participant_data(st.session_state.session_id, prolific_pid)

            st.session_state.current_step = next_step
            st.rerun()


def render_chat():
    """
    Main chat/task interface rendering function.
    Now uses extracted task_renderer functions for better modularity.
    """
    # Initialize task state on first render
    if st.session_state.task_start_time is None:
        st.session_state.task_start_time = datetime.now()
        st.session_state.question_count = 0
        st.session_state.expander_clicks_total = 0
        st.session_state.modal_clicks_total = 0
        st.session_state.followup_count = 0
        st.session_state.expanded_quotes = set()
        st.session_state.current_history_key = f"task_{st.session_state.task_number}_history"
    
        # Log the task start event for verification
        log_interaction(
            session_id=st.session_state.session_id,
            task_number=st.session_state.task_number,
            event_type="task_started",
            details=f"Task {st.session_state.task_number} presentation started"
        )

    task_number = st.session_state.task_number
    task = content.TASKS[task_number]
    history_key = st.session_state.current_history_key

    # Render task header
    st.header(f"Aufgabe {task_number}")
    render_task_header(task)

    # Render all messages with buttons
    render_message_list(
        messages=st.session_state.messages,
        task_number=task_number,
        show_source_modal_callback=show_source_modal
    )

    # Chat input box
    user_input = st.chat_input("Formulieren Sie Ihre Anfrage an den KI-Assistenten...")
    
    if user_input:
        handle_user_input(
            user_input=user_input,
            task_number=task_number,
            history_key=history_key,
            pipeline=pipeline
        )
        st.rerun()

    # Task completion button
    st.divider()
    
    if len(st.session_state.messages) > 0:
        if st.button("Ich möchte die Frage beantworten.", type="primary"):
            finalize_open_quotes()
            update_last_action_time()
            st.session_state.answer_finalization_start_time = datetime.now()
            st.session_state.current_step = "task_post"
            st.rerun()


def render_task_post():
    task = content.TASKS[st.session_state.task_number]
    
    st.markdown(f"""
    <p style='font-size: 18px; font-weight: 500; margin-bottom: 14px;'> {task['question']} </p>
    """, unsafe_allow_html=True)

    post_answer = st.radio(
        "",
        options=task['options'],
        key=f"post_task_{st.session_state.task_number}"
    )
        
    if st.button("**Antwort final einloggen.**", type="secondary", use_container_width=False):
        if not st.session_state.answer_logged:
            st.session_state.answer_finalization_start_time = datetime.now()
            st.session_state.answer_logged = True
            log_interaction(
                session_id=st.session_state.session_id,
                task_number=st.session_state.task_number,
                event_type="answer_finalized",
                details=f"Participant finalized answer at {datetime.now().isoformat()}"
            )
            st.success("Antwort wurde eingeloggt!")
        else:
            st.info("Antwort wurde bereits eingeloggt.")
    
    st.divider()
    st.markdown("**Bitte stimmen Sie ab:**")

    confidence = likert_select_conf(
        "Ich bin mir sicher bei meiner Antwort.",
        key=f"conf_{st.session_state.task_number}",
        default=4
    )

    if 'answer_logged' not in st.session_state:
        st.session_state.answer_logged = False

    # Get task content for correct answer
    task_content = content.TASKS[st.session_state.task_number]

    # Convert selected answer to letter (A/B/C/D)
    selected_index = task_content['options'].index(post_answer)
    selected_letter = ['A', 'B', 'C'][selected_index]

    # Calculate if answer is correct
    correct_answer_index = task_content['correct_answer']
    is_correct = (selected_index == correct_answer_index)

    
    if st.button("Absenden und fortfahren"):
        st.session_state.answer_logged = False
        finalize_open_quotes()
        
        end_time = datetime.now()
        
        if st.session_state.task_start_time:
            duration = (end_time - st.session_state.task_start_time).total_seconds()
        else:
            duration = -1
            log_interaction(
                session_id=st.session_state.session_id,
                task_number=st.session_state.task_number,
                event_type="error",
                details="Task start time was None - duration could not be calculated"
            )
        
        # Calculate final metrics using behavioral_tracking module
        metrics = calculate_final_metrics()
        mean_answer_reading = metrics['mean_answer_reading']
        
        # Determine expander_clicks value based on condition
        expander_clicks_value = (st.session_state.expander_clicks_total 
                                if st.session_state.group == "Augmented" else None)
        
        log_task_data(
            session_id=st.session_state.session_id,
            task_number=st.session_state.task_number,
            post_answer=selected_letter,
            is_correct=is_correct,
            confidence=confidence,
            duration=round(duration, 1) if duration >= 0 else duration,
            expander_clicks_total=expander_clicks_value,
            modal_clicks_total=st.session_state.modal_clicks_total,
            expander_clicks_verification=st.session_state.expander_clicks_verification,
            modal_clicks_verification=st.session_state.modal_clicks_verification,
            followup_questions=st.session_state.followup_count,
            cumulative_modal_dwell=st.session_state.cumulative_modal_dwell,
            cumulative_expander_dwell=st.session_state.cumulative_expander_dwell,
            mean_answer_reading_time=mean_answer_reading,
            answer_finalization_time=metrics['answer_finalization_time'],
            first_click_latency=st.session_state.first_click_latency,
            clicks_after_followups=st.session_state.clicks_after_followups,
            prompts_before_first_verification=st.session_state.prompts_before_first_verification,
            expander_then_modal_escalations=st.session_state.expander_then_modal_escalations,
        )
        
        log_interaction(
            session_id=st.session_state.session_id,
            task_number=st.session_state.task_number,
            event_type="task_completed",
            details=f"Duration: {duration:.2f}s, Answer submitted: {post_answer}",
            selected_answer=selected_letter
        )
        
        # Reset for next task or proceed to post-survey
        if st.session_state.task_number < len(content.TASKS):
            st.session_state.task_number += 1
            # Reset all task-specific variables
            st.session_state.messages = []
            st.session_state.responses = {}
            st.session_state.task_start_time = None
            st.session_state.question_count = 0
            st.session_state.button_clicks_processed = set()
            st.session_state.expander_clicks_total = 0
            st.session_state.modal_clicks_total = 0
            st.session_state.followup_count = 0
            st.session_state.modal_opened_time = None
            st.session_state.answer_finalization_start_time = None
            
            # Reset enhanced tracking variables
            st.session_state.last_answer_time = None
            st.session_state.last_action_time = None
            st.session_state.answer_reading_times = []
            st.session_state.cumulative_modal_dwell = 0
            st.session_state.cumulative_expander_dwell = 0
            st.session_state.first_click_happened = False
            st.session_state.first_click_latency = None
            st.session_state.clicks_after_followups = 0
            st.session_state.expander_clicks_verification = 0
            st.session_state.modal_clicks_verification = 0            
            st.session_state.prompts_before_first_verification = None
            st.session_state.expander_then_modal_escalations = 0
            st.session_state.last_expander_click_time = None

            for key in list(st.session_state.keys()):
                if key.startswith("quote_visible_") or key.startswith("quote_timestamp_"):
                    del st.session_state[key]

            st.session_state.current_step = 'task_chat'
        else:
            st.session_state.current_step = 'post_study_survey'
        
        st.rerun()

def render_debriefing():
    st.header("Vielen Dank für Ihre Teilnahme!")
    try:
        st.balloons()
    except Exception:
        pass
    
    st.markdown(content.DEBRIEFING)
    
    # Add some spacing
    st.markdown("---")
    
    # Prolific completion button
    st.markdown("### Studie abschließen")
    st.info("**Wichtig:** Klicken Sie auf den Button unten, um Ihre Teilnahme auf Prolific zu bestätigen und Ihre Vergütung zu erhalten.")
    
    # Get Prolific completion URL
    PROLIFIC_COMPLETION_CODE = "XYZXYZXYZ"
    completion_url = f"https://app.prolific.com/submissions/complete?cc={PROLIFIC_COMPLETION_CODE}"
    
    # Create a clickable button-style link
    st.markdown(
        f"""
        <a href="{completion_url}" target="_blank">
            <button style="
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 15px 32px;
                text-align: center;
                text-decoration: none;
                display: inline-block;
                font-size: 18px;
                margin: 4px 2px;
                cursor: pointer;
                border-radius: 8px;
                font-weight: bold;
            ">
                Zurück zu Prolific
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )
    
    st.caption("Nach dem Klick werden Sie zu Prolific weitergeleitet. Sie können dieses Fenster dann schließen.")



# --- Main Application Logic ---
st.title("KI-Steuerassistent")

step = st.session_state.current_step

if step == "consent":
    render_consent()
elif step == "instructions":
    render_instructions_and_comprehension()
elif step == "pre_study_survey":
    render_survey(content.PRE_STUDY_SURVEY, next_step="task_chat")
elif step == "task_chat":
    render_chat()
elif step == "task_post":
    render_task_post()
elif step == "post_study_survey":
    render_survey(content.POST_STUDY_SURVEY, next_step="debriefing")
elif step == "debriefing":
    render_debriefing()
