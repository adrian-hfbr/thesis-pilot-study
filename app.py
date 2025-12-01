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
    format_legal_text
)
from behavioral_tracking import (
    update_last_action_time,
    finalize_open_quotes,
    finalize_modal_tracking,
    calculate_final_metrics,
    finalize_modal_if_open
)

from task_renderer import (
    render_task_header,
    render_message_list,
    handle_user_input
)

from utils import (
    get_session_id,
    initialize_log_files,
    log_participant_info,
    log_task_data,
    log_interaction,
    log_post_survey,
    check_all_tasks_correct
)

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
        st.session_state.group = "Augmented" # random.choice(['Augmented', 'Minimal'])
        
    if 'experiment_start_time' not in st.session_state:
        st.session_state.experiment_start_time = datetime.now()
        st.session_state.session_id = get_session_id()

        # URL EXTRACTION - Always initialize these
        if "prolific_pid" not in st.session_state:
            try:
                st.session_state.prolific_pid = st.query_params.get("PROLIFIC_PID", "")
            except Exception:
                st.session_state.prolific_pid = ""
        
        if "prolific_session_id" not in st.session_state:
            prolific_session_id = st.query_params.get("SESSION_ID", "")
            st.session_state.prolific_session_id = prolific_session_id if prolific_session_id else get_session_id()
        
        if "study_id" not in st.session_state:
            try:
                st.session_state.study_id = st.query_params.get("STUDY_ID", "")
            except Exception:
                st.session_state.study_id = ""

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

        st.session_state.postsurvey_page1_responses = {}  # Manipulation Check
        st.session_state.postsurvey_page2_responses = {}  # Cognitive Load
        st.session_state.postsurvey_page3_responses = {}  # Trust
        st.session_state.current_postsurvey_page = 1

        # Step completion tracking - ADD THIS SECTION
        st.session_state.consent_completed = False
        st.session_state.instructions_completed = False
        st.session_state.pre_study_completed = False
        st.session_state.task_1_completed = False
        st.session_state.task_2_completed = False
        st.session_state.task_3_completed = False
        st.session_state.task_4_completed = False
        st.session_state.postsurvey_page1_completed = False
        st.session_state.postsurvey_page2_completed = False
        st.session_state.postsurvey_page3_completed = False


        # Initialize task-scoped histories
        for task_num in range(1, 5):  # You have 4 tasks
            if f"task_{task_num}_history" not in st.session_state:
                st.session_state[f"task_{task_num}_history"] = []

initialize_session_state()

def create_postsurvey_page1():
    """Construct post-study survey page 1 dictionary with manipulation check questions."""
    return {
        'title': 'Fragebogen nach der Studie - Teil 1 von 3',
        'manipulation_check': content.POST_STUDY_SURVEY['manipulation_check']
    }

def create_postsurvey_page2():
    """Construct post-study survey page 2 dictionary with cognitive load items (ICL, ECL, GCL) and attention checks."""
    return {
        'title': 'Fragebogen nach der Studie - Teil 2 von 3',
        'icl_items': content.POST_STUDY_SURVEY['icl_items'],
        'ecl_items': content.POST_STUDY_SURVEY['ecl_items'],
        'attention_check': content.POST_STUDY_SURVEY.get('attention_check', {}),
        'gcl_items': content.POST_STUDY_SURVEY['gcl_items']
    }

def create_postsurvey_page3():
    """Construct post-study survey page 3 dictionary with trust and system reliability items."""
    return {
        'title': 'Fragebogen nach der Studie - Teil 3 von 3',
        'trust_items': content.POST_STUDY_SURVEY['trust_items'],
    }


# --- Modal for Source Verification ---
@st.dialog("Quelle", width="large")
def show_source_modal():
    """Display full source document text in a modal dialog with dwell time tracking."""
    
    # 1. Mapping
    task_map = {
        1: ("estg_6.txt", "EStG § 6"),
        2: ("estg_35a.txt", "EStG § 35a"),
        3: ("estg_20.txt", "EStG § 20"),
        4: ("estg_9.txt", "EStG § 9")
    }
    
    current_task = st.session_state.get("task_number")
    doc = st.session_state.get("modal_doc")

    # 2. Determine Content: Hardcoded (Priority) vs. Dynamic (Fallback)
    if current_task in task_map:
        filename, legal_ref = task_map[current_task]
        full_text = full_documents.get(filename, "Fehler: Dokument nicht geladen.")
    else:
        # Dynamic Path: Fallback to RAG result (Original Logic)
        if not doc:
            st.warning("Keine Quelle zum Anzeigen ausgewählt.")
            if st.button("Schließen"):
                st.session_state.modal_doc = None
                if 'button_clicks_processed' in st.session_state:
                    st.session_state.button_clicks_processed = {
                        k for k in st.session_state.button_clicks_processed 
                        if not k.startswith('btn_modal_')
                    }
                st.rerun()
            return

        # Extract info from RAG doc
        legal_ref = doc.metadata.get('legal_reference_full', doc.metadata.get('legal_reference', 'Unbekannte Quelle'))
        full_text = doc.page_content 
        # Try to load from disk if metadata has source_file, else use page_content
        source_file = doc.metadata.get('source_file', '')
        if source_file:
            try:
                filepath = os.path.join("data", source_file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    full_text = f.read()
            except Exception:
                pass # Keep page_content as fallback

    # 3. Track Open Time
    if st.session_state.modal_opened_time is None:
        st.session_state.modal_opened_time = datetime.now()
    
    # 4. Render UI
    st.info(f"Hier sehen Sie den vollständigen Paragraphen ({legal_ref}). **Schließen Sie das Fenster bitte ausschließlich über den 'Schließen'-Button.**")

    formatted_text = format_legal_text(full_text)

    st.markdown(
        f"""
        <div style="height: 55vh; overflow-y: auto; 
                    border: 2px solid #e2e8f0; 
                    padding: 20px; 
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
        # Pass 'doc' to tracking if it exists, otherwise None (tracking handles timestamps regardless)
        finalize_modal_tracking(doc)
        update_last_action_time()
        st.rerun()

# --- Screen Rendering Functions ---
def render_consent():
    """Display informed consent form and advance to instructions upon agreement."""
    st.header("Einverständniserklärung")
    st.markdown(content.CONSENT_TEXT)
    
    if st.button("Ich stimme zu und möchte fortfahren"):
        st.session_state.consent_completed = True
        st.session_state.current_step = "instructions"
        st.rerun()


def render_instructions_and_comprehension():
    """Display condition-specific instructions with screenshots and validate comprehension via quiz questions."""
    group = st.session_state.group  # "Augmented" or "Minimal"
    st.header("Anleitung")
    
    # Display instructions with integrated images based on condition
    if group == "Minimal":
        st.markdown(content.INSTRUCTIONS_BY_CONDITION["Minimal"])
        st.image("assets/mehr_kontext.png", 
                caption="Button 'Gesetzestext anzeigen' für den vollständigen Paragraphen",
                use_container_width=True)
        st.markdown(content.INSTRUCTIONS_BY_CONDITION["Minimal_continuation"])
        st.image(content.INSTRUCTIONS_BY_CONDITION["minimal_paragraph_image_path"],
             caption=content.INSTRUCTIONS_BY_CONDITION["minimal_paragraph_caption"],
             use_container_width=True)
        st.markdown(content.INSTRUCTIONS_BY_CONDITION["Minimal_end"])
    
    elif group == "Augmented":
        st.markdown(content.INSTRUCTIONS_BY_CONDITION["Augmented"])
        st.image("assets/zitat_anzeigen.png", 
                caption="'Zitat anzeigen'-Button für sofortigen Zugriff auf das Zitat",
                use_container_width=True)
        st.markdown(content.INSTRUCTIONS_BY_CONDITION["Augmented_continuation1"])
        st.image("assets/zitat_ausblenden.png", 
                caption="Geöffneter 'Zitat anzeigen'-Button für sofortigen Zugriff auf das Zitat",
                use_container_width=True)
        st.markdown(content.INSTRUCTIONS_BY_CONDITION["Augmented_continuation2"])
        st.image("assets/mehr_kontext.png", 
                caption="Button 'Gesetzestext anzeigen' für den vollständigen Paragraphen",
                use_container_width=True)
        st.markdown(content.INSTRUCTIONS_BY_CONDITION["Augmented_continuation3"])
        st.image(content.INSTRUCTIONS_BY_CONDITION["augmented_paragraph_image_path"],
            caption=content.INSTRUCTIONS_BY_CONDITION["augmented_paragraph_caption"],
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
                st.session_state.instructions_completed = True
                st.session_state.current_step = "pre_study_survey"
                st.rerun()
            else:
                st.error("Mindestens eine Antwort ist nicht korrekt. Bitte prüfen Sie die Anweisungen und beantworten Sie alle Fragen richtig, um fortzufahren.")



def render_survey(surveydict, next_step):
    """Render survey pages (Likert scales, manipulation checks, cognitive load, trust) with interaction tracking and validation."""
    st.header(surveydict["title"])
    responses = {}

    current_page = 1
    if "manipulation_check" in surveydict:
        current_page = 1  # Seite 1: Nur Manipulation Check
    elif "icl_items" in surveydict or "ecl_items" in surveydict:
        current_page = 2  # Seite 2: Cognitive Load
    elif "trust_items" in surveydict:
        current_page = 3  # Seite 3: Trust + attention_check

    # Track total items and interacted items
    total_items = 0
    interacted_items = 0

    # Generic single-scale "items" (used by PRE_STUDY_SURVEY)
    if "items" in surveydict:
        for key, question in surveydict["items"].items():
            total_items += 1
            responses[key] = likert_select(question, key, default=4)
            if st.session_state.get(f"{key}_interacted", False):
                interacted_items += 1

    if "manipulation_check" in surveydict:
        st.subheader("Bewertung des KI-Assistenten")

        image_mapping = {
        0: "mehr_kontext.png",      # First option
        1: "zitat_anzeigen.png",    # Second option
        2: "beide_buttons.png"      # Third option
        }

        for idx, (key, mc) in enumerate(surveydict["manipulation_check"].items()):
            question = mc.get("question", "")
            options = mc.get("options", [])

            st.markdown(f"**{question}**", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            for opt_idx, opt_text in enumerate(options, start=1):
                item_key = f"{key}_opt{opt_idx}"
                
                image_file = image_mapping.get(opt_idx - 1)
                if image_file:
                    try:
                        st.image(f"assets/{image_file}", use_container_width=True)
                    except Exception as e:
                        st.warning(f"Image {image_file} not found in assets folder")

                total_items += 1
                # Wert holen
                val = likert_select(
                    question=opt_text,
                    key=item_key,
                    default=4
                )
                
                # Speichern
                responses[item_key] = val
                
                if st.session_state.get(f"{item_key}_interacted", False):
                    interacted_items += 1

                st.markdown("<br>", unsafe_allow_html=True)

    
    # Intrinsic Cognitive Load
    if "icl_items" in surveydict:
        st.subheader("Inhaltliche Anforderungen")
        for key, question in surveydict["icl_items"].items():
            total_items += 1
            responses[key] = likert_select(question, key, default=4)
            if st.session_state.get(f"{key}_interacted", False):
                interacted_items += 1
    
    # Extraneous Cognitive Load
    if "ecl_items" in surveydict:
        st.subheader("Bewertung der Interaktion")
        for key, question in surveydict["ecl_items"].items():
            total_items += 1
            responses[key] = likert_select(question, key, default=4)
            if st.session_state.get(f"{key}_interacted", False):
                interacted_items += 1
        for key, question in surveydict["attention_check"].items():  # attention_check
            total_items += 1
            responses[key] = likert_select(question, key, default=4)
            if st.session_state.get(f"{key}_interacted", False):
                interacted_items += 1
    
    # Germane Cognitive Load
    if "gcl_items" in surveydict:
        st.subheader("Lernbezogene Verarbeitung")
        for key, question in surveydict["gcl_items"].items():
            total_items += 1
            responses[key] = likert_select(question, key, default=4)
            if st.session_state.get(f"{key}_interacted", False):
                interacted_items += 1
    
    # Trust (functionality, helpfulness, reliability)
    if "trust_items" in surveydict:
        st.subheader("Bewertung des Systems")
        for key, question in surveydict["trust_items"].items():
            total_items += 1
            responses[key] = likert_select(question, key, default=4)
            if st.session_state.get(f"{key}_interacted", False):
                interacted_items += 1
    
    # Check if all items were interacted with
    all_interacted = (interacted_items == total_items) and total_items > 0
    
    # Show red warning text if not all items are completed
    if not all_interacted:
        st.markdown(
            '<p style="color: #dc3545; font-weight: 600; margin-top: 10px; margin-bottom: 10px;">'
            'Bitte vervollständigen Sie den Fragebogen, um fortzufahren.</p>',
            unsafe_allow_html=True
        )
    
    if st.button("Weiter", disabled=not all_interacted):        
        # Pre-study survey logging
        if surveydict["title"] == content.PRE_STUDY_SURVEY["title"]:
            log_participant_info(
                session_id=st.session_state.session_id,
                study_id=st.session_state.study_id,
                prolific_session_id=st.session_state.prolific_session_id,
                prolific_pid=st.session_state.prolific_pid,
                group=st.session_state.group,
                survey_responses=responses,
                total_duration=None  # Not finished yet
            )
            st.session_state.current_step = next_step
            st.session_state.pre_study_completed = True  # ADD THIS
            st.rerun()
        
        # Post-study survey - UNTERSCHIEDLICH je nach Seite
        elif surveydict["title"].startswith("Fragebogen nach der Studie"):
            # ===== SEITE 1 & 2: NUR speichern, dann weiterleiten =====
            if current_page == 1:
                st.session_state.postsurvey_page1_responses = responses
                st.session_state.postsurvey_page1_completed = True
                st.session_state.current_step = next_step
                st.rerun()
                return
            
            elif current_page == 2:
                st.session_state.postsurvey_page2_responses = responses
                st.session_state.postsurvey_page2_completed = True
                st.session_state.current_step = next_step
                st.rerun()
                return
            
            # ===== SEITE 3: Responses speichern + zusammenführen + LOGGING =====
            elif current_page == 3:
                st.session_state.postsurvey_page3_responses = responses
                st.session_state.postsurvey_page3_completed = True
                
                # Zusammenführen aller 3 Seiten
                combined_responses = {}
                combined_responses.update(st.session_state.postsurvey_page1_responses or {})
                combined_responses.update(st.session_state.postsurvey_page2_responses or {})
                combined_responses.update(st.session_state.postsurvey_page3_responses or {})
                
                # Calculate experiment duration
                if hasattr(st.session_state, 'experiment_start_time') and st.session_state.experiment_start_time:
                    st.session_state.total_experiment_duration = (
                        datetime.now() - st.session_state.experiment_start_time
                    ).total_seconds()
                
                # Validate manipulation check JETZT
                manip_check_passed = None
                if "manipulation_check" in st.session_state.postsurvey_page1_responses or combined_responses:
                    manip_check_passed = True
                    user_group = st.session_state.group
                    
                    # Manipulation Check Validation aus content.POST_STUDY_SURVEY
                    manip_check_def = content.POST_STUDY_SURVEY["manipulation_check"]
                    for key, mc in manip_check_def.items():
                        user_answer = combined_responses.get(key)
                        correct_idx = mc.get("correct_index_augmented" if user_group == "Augmented" 
                                           else "correct_index_minimal")
                        
                        if user_answer and correct_idx is not None:
                            user_answer_idx = mc["options"].index(user_answer)
                            if user_answer_idx != correct_idx:
                                manip_check_passed = False
                                break
                
                log_post_survey(
                    session_id=st.session_state.session_id,
                    survey_responses=combined_responses,
                    manip_check_correct=manip_check_passed,
                    total_duration=st.session_state.total_experiment_duration
                )
                
                # Backup
                from backup_manager import backup_participant_data
                prolific_pid = st.session_state.get('prolific_pid', 'UNKNOWN')
                backup_participant_data(st.session_state.session_id)
                
                st.session_state.current_step = next_step  # → debriefing
                st.rerun()



def render_chat():
    """Render main task interface with AI assistant chat, quote/modal buttons, and interaction logging."""

    # Validate task hasn't been completed already
    if st.session_state.get(f'task_{st.session_state.task_number}_completed', False):
        st.warning("Diese Aufgabe wurde bereits abgeschlossen.")
        if st.session_state.task_number < 4:
            st.session_state.task_number += 1
            st.rerun()
        else:
            st.session_state.current_step = 'poststudysurvey_page1'
            st.rerun()
        return

    if "modal_was_open" not in st.session_state:
        st.session_state.modal_was_open = False
    
    if st.session_state.modal_was_open and not st.session_state.get("modal_doc"):
        # Modal was open but is now closed without explicit button click
        finalize_modal_if_open()
        log_interaction(
            session_id=st.session_state.session_id,
            task_number=st.session_state.task_number,
            event_type="modal_closed_incorrect",
            details="Modal closed via ESC or outside click"
        )
        st.session_state.modal_was_open = False
        st.session_state.modal_opened_time = None
    
    # Track current modal state
    if st.session_state.get("modal_doc"):
        st.session_state.modal_was_open = True
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
            finalize_modal_if_open()
            update_last_action_time()
            st.session_state.answer_finalization_start_time = datetime.now()
            st.session_state.current_step = "task_post"
            st.rerun()


def render_task_post():
    """Render answer selection screen for multiple choice task with confidence rating and behavioral metrics logging."""
    task = content.TASKS[st.session_state.task_number]
    
    st.markdown(f"""
    <p style='font-size: 18px; font-weight: 500; margin-bottom: 14px;'> {task['question']} </p>
    """, unsafe_allow_html=True)

    post_answer = st.radio(
        "",
        options=task['options'],
        key=f"post_task_{st.session_state.task_number}",
        index=None
    )
        
    if st.button("**Antwort final einloggen.**", type="secondary", use_container_width=False):
        if post_answer is None:
            st.error("Bitte wählen Sie eine Antwort aus, bevor Sie fortfahren.")
            return
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
    
    if st.session_state.get("answer_logged", False) == True:
        st.divider()
        st.markdown("**Bitte stimmen Sie ab:**")

        confidence = likert_select_conf(
            "Ich bin mir sicher bei meiner Antwort.",
            key=f"conf_{st.session_state.task_number}",
            default=4
        )
        # Track interaction status
        total_items = 2  # Multiple choice + confidence
        interacted_items = 0
        
        # Check if multiple choice was answered
        if post_answer is not None:
            interacted_items += 1
        
        # Check if confidence was interacted with
        conf_key = f"conf_{st.session_state.task_number}"
        if st.session_state.get(f"{conf_key}_interacted", False):
            interacted_items += 1
        
        # Check if all items were interacted with
        all_interacted = (interacted_items == total_items)
        
        
        # Show red warning text if not all items are completed
        if not all_interacted:
            st.markdown(
                '<p style="color: #dc3545; font-weight: 600; margin-top: 10px; margin-bottom: 10px;">'
                'Bitte vervollständigen Sie den Fragebogen, um fortzufahren.</p>',
                unsafe_allow_html=True
            )

        # Get task content for correct answer
        task_content = content.TASKS[st.session_state.task_number]

        # Convert selected answer to letter (A/B/C)
        selected_index = task_content['options'].index(post_answer)
        selected_letter = ['A', 'B', 'C'][selected_index]

        # Calculate if answer is correct
        correct_answer_index = task_content['correct_answer']
        is_correct = (selected_index == correct_answer_index)

        
        if st.button("Weiter", disabled=not all_interacted):
            if post_answer is None:
                st.error("Bitte wählen Sie eine Antwort aus, bevor Sie fortfahren.")
                return
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

            if st.session_state.task_number == 1:
                st.session_state.task_1_completed = True
            elif st.session_state.task_number == 2:
                st.session_state.task_2_completed = True
            elif st.session_state.task_number == 3:
                st.session_state.task_3_completed = True
            elif st.session_state.task_number == 4:
                st.session_state.task_4_completed = True
            
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
                st.session_state.first_verification_occurred = False
                st.session_state.expander_then_modal_escalations = 0
                st.session_state.last_expander_click_time = None

                for key in list(st.session_state.keys()):
                    if key.startswith("quote_visible_") or key.startswith("quote_timestamp_"):
                        del st.session_state[key]

                st.session_state.current_step = 'task_chat'
            else:
                st.session_state.current_step = 'poststudysurvey_page1'
            
            st.rerun()
        
    if 'answer_logged' not in st.session_state:
        st.session_state.answer_logged = False

def render_debriefing():
    """Display debriefing message and Prolific completion link for study closure."""
    st.header("Vielen Dank für Ihre Teilnahme!")
    try:
        st.balloons()
    except Exception:
        pass
    
    st.markdown(content.DEBRIEFING)
    
    st.markdown("---")
    
    # Prolific completion button
    st.markdown("### Studie abschließen")
    st.info("**Wichtig:** Klicken Sie auf den Button unten, um Ihre Teilnahme auf Prolific zu bestätigen und Ihre Vergütung zu erhalten.")
    
    # Check if all tasks were answered correctly
    all_correct = check_all_tasks_correct(st.session_state.session_id)
    
    # Set completion code based on performance
    if all_correct:
        PROLIFICCOMPLETIONCODE = 'C1E98YYT' # all correct
    else:
        PROLIFICCOMPLETIONCODE = 'C9PXAZPH' # at least 1 wrong
    
    completion_url = f"https://app.prolific.com/submissions/complete?cc={PROLIFICCOMPLETIONCODE}"
    
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
    
    st.caption("Nach dem Klick werden Sie zu Prolific weitergeleitet. Im Anschluss können Sie das Fenster schließen.")



# --- Main Application Logic ---
# --- Main Application Logic with Validation ---
st.title("KI-Steuerassistent")

step = st.session_state.current_step

# COMPREHENSIVE VALIDATION SYSTEM
def validate_and_redirect():
    """Validates workflow progression and redirects if necessary."""
    
    progression = {
        'instructions': 'consent',
        'pre_study_survey': 'instructions',
        'task_chat': 'pre_study_survey',
        'task_post': 'task_chat',
        'poststudysurvey_page1': ['task_1', 'task_2', 'task_3', 'task_4'],
        'poststudysurvey_page2': 'poststudysurvey_page1',
        'poststudysurvey_page3': 'poststudysurvey_page2',
        'debriefing': 'poststudysurvey_page3'
    }
    
    current = st.session_state.current_step
    
    # Skip validation for consent (first step)
    if current == 'consent':
        return False
    
    # Check instructions requires consent
    if current == 'instructions':
        if not st.session_state.get('consent_completed', False):
            st.warning("Bitte stimmen Sie zuerst der Einverständniserklärung zu.")
            st.session_state.current_step = 'consent'
            return True
    
    # Check pre-study survey requires instructions
    if current == 'pre_study_survey':
        if not st.session_state.get('instructions_completed', False):
            st.warning("Bitte schließen Sie zuerst die Anleitung ab.")
            st.session_state.current_step = 'instructions'
            return True
    
    # Check task_chat requires pre-study
    if current == 'task_chat':
        if not st.session_state.get('pre_study_completed', False):
            st.warning("Bitte schließen Sie zuerst den Vorfragebogen ab.")
            st.session_state.current_step = 'pre_study_survey'
            return True
        
        # Also check previous tasks are completed
        task_num = st.session_state.task_number
        if task_num > 1 and not st.session_state.get(f'task_{task_num-1}_completed', False):
            st.warning(f"Bitte schließen Sie zuerst Aufgabe {task_num-1} ab.")
            st.session_state.task_number = task_num - 1
            st.session_state.current_step = 'task_chat'
            return True
    
    # Check task_post requires that task was started
    if current == 'task_post':
        if len(st.session_state.messages) == 0:
            st.warning("Sie müssen zuerst Fragen an den Assistenten stellen.")
            st.session_state.current_step = 'task_chat'
            return True
    
    # Check post-survey page 1 requires all tasks completed
    if current == 'poststudysurvey_page1':
        for i in range(1, 5):
            if not st.session_state.get(f'task_{i}_completed', False):
                st.warning(f"Bitte schließen Sie zuerst alle Aufgaben ab. Aufgabe {i} fehlt noch.")
                st.session_state.task_number = i
                st.session_state.current_step = 'task_chat'
                return True
    
    # Check post-survey page 2 requires page 1
    if current == 'poststudysurvey_page2':
        if not st.session_state.get('postsurvey_page1_completed', False):
            st.warning("Bitte füllen Sie zuerst Seite 1 des Nachfragebogens aus.")
            st.session_state.current_step = 'poststudysurvey_page1'
            return True
    
    # Check post-survey page 3 requires pages 1 and 2
    if current == 'poststudysurvey_page3':
        if not st.session_state.get('postsurvey_page1_completed', False) or \
           not st.session_state.get('postsurvey_page2_completed', False):
            st.warning("Bitte füllen Sie alle vorherigen Seiten des Nachfragebogens aus.")
            st.session_state.current_step = 'poststudysurvey_page1'
            return True
    
    # Check debriefing requires page 3
    if current == 'debriefing':
        if not st.session_state.get('postsurvey_page3_completed', False):
            st.warning("Bitte schließen Sie zuerst den Nachfragebogen ab.")
            st.session_state.current_step = 'poststudysurvey_page1'
            return True
    
    return False

# Run validation before rendering
if validate_and_redirect():
    st.rerun()

# Normal rendering after validation passes
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
elif step == "poststudysurvey_page1":
    render_survey(create_postsurvey_page1(), next_step="poststudysurvey_page2")
elif step == "poststudysurvey_page2":
    render_survey(create_postsurvey_page2(), next_step="poststudysurvey_page3")
elif step == "poststudysurvey_page3":
    render_survey(create_postsurvey_page3(), next_step="debriefing")
elif step == "debriefing":
    render_debriefing()

