from datetime import datetime
import config
import streamlit as st
from utils import log_interaction

def update_last_action_time():
    """Updates timestamps and calculates answer reading time.
    Calculate answer reading time ONLY for FIRST action after answer
    """
    now = datetime.now()
    
    if (st.session_state.last_answer_time is not None and 
        not st.session_state.answer_reading_recorded):
        
        reading_time = (now - st.session_state.last_answer_time).total_seconds()
        st.session_state.answer_reading_times.append(reading_time)
        st.session_state.answer_reading_recorded = True
    
    st.session_state.last_action_time = now


def finalize_open_quotes():
    """Auto-close all open quotes and log their dwell times - ONCE only."""
    now = datetime.now()
    keys_to_delete = []
    
    for key in list(st.session_state.keys()):
        if key.startswith("quote_visible_") and st.session_state[key]:
            quote_index = key.replace("quote_visible_", "")
            timestamp_key = f"quote_timestamp_{quote_index}"
            
            if timestamp_key in st.session_state:
                dwell_time = (now - st.session_state[timestamp_key]).total_seconds()
                
                if dwell_time >= config.MINIMUM_DWELL_TIME_EXPANDER:
                    st.session_state.cumulative_expander_dwell += dwell_time
                    st.session_state.expander_clicks_verification += 1
                    
                    if not st.session_state.get('first_verification_occurred', False):
                        st.session_state.first_verification_occurred = True
                        st.session_state.prompts_before_first_verification = st.session_state.question_count
                    
                    log_interaction(
                        session_id=st.session_state.session_id,
                        task_number=st.session_state.task_number,
                        event_type="quote_closed_auto",
                        details=f"quote_{quote_index}|auto_closed",
                        dwell_time=dwell_time
                    )
                else:
                    log_interaction(
                        session_id=st.session_state.session_id,
                        task_number=st.session_state.task_number,
                        event_type="quote_closed_brief_auto",
                        details=f"quote_{quote_index}|below_threshold",
                        dwell_time=dwell_time
                    )
                
                keys_to_delete.append(timestamp_key)
                keys_to_delete.append(key)
    
    for key in keys_to_delete:
        if key in st.session_state:
            del st.session_state[key]

def track_quote_toggle(quote_key, is_opening, task_number, legal_ref, url):
    visible_key = f"quote_visible_{quote_key}"
    timestamp_key = f"quote_timestamp_{quote_key}"
    
    if is_opening:
        st.session_state[visible_key] = True
        st.session_state[timestamp_key] = datetime.now()
        st.session_state.expander_clicks_total += 1
        st.session_state.last_expander_click_time = datetime.now()
        
        if not st.session_state.first_click_happened and st.session_state.last_answer_time:
            if st.session_state.first_click_latency is None:
                st.session_state.first_click_latency = (datetime.now() - st.session_state.last_answer_time).total_seconds()
            st.session_state.first_click_happened = True
        
        if st.session_state.followup_count > 0:
            st.session_state.clicks_after_followups += 1
        
        log_interaction(
            session_id=st.session_state.session_id,
            task_number=task_number,
            event_type="quote_opened",
            details=f"{legal_ref}|url={url}"
        )
    else:
        if timestamp_key in st.session_state:
            dwell_time = (datetime.now() - st.session_state[timestamp_key]).total_seconds()
            
            if dwell_time >= config.MINIMUM_DWELL_TIME_EXPANDER:
                st.session_state.cumulative_expander_dwell += dwell_time
                st.session_state.expander_clicks_verification += 1
                
                if not st.session_state.get('first_verification_occurred', False):
                    st.session_state.first_verification_occurred = True
                    st.session_state.prompts_before_first_verification = st.session_state.question_count
                
                log_interaction(
                    session_id=st.session_state.session_id,
                    task_number=task_number,
                    event_type="quote_closed",
                    details=f"quote_{quote_key}",
                    dwell_time=dwell_time
                )
            else:
                log_interaction(
                    session_id=st.session_state.session_id,
                    task_number=task_number,
                    event_type="quote_closed_brief",
                    details=f"quote_{quote_key}|below_threshold",
                    dwell_time=dwell_time
                )
            
            del st.session_state[timestamp_key]
        
        st.session_state[visible_key] = False

def finalize_modal_tracking(doc):
    if st.session_state.modal_opened_time:
        dwell_time = (datetime.now() - st.session_state.modal_opened_time).total_seconds()
        legal_ref_clean = doc.metadata.get("legal_reference", "Unknown")
        group = st.session_state.get("group", "Minimal")
        event_type = "modal_augmented" if group == "Augmented" else "modal_minimal"
        
        if dwell_time >= config.MINIMUM_DWELL_TIME_MODAL:
            st.session_state.cumulative_modal_dwell += dwell_time
            st.session_state.modal_clicks_verification += 1
            
            if not st.session_state.get('first_verification_occurred', False):
                st.session_state.first_verification_occurred = True
                st.session_state.prompts_before_first_verification = st.session_state.question_count
            
            log_interaction(
                session_id=st.session_state.session_id,
                task_number=st.session_state.task_number,
                event_type=event_type,
                details=f"{legal_ref_clean}",
                dwell_time=dwell_time
            )
        else:
            log_interaction(
                session_id=st.session_state.session_id,
                task_number=st.session_state.task_number,
                event_type=f"{event_type}_brief",
                details=f"{legal_ref_clean}|below_threshold",
                dwell_time=dwell_time
            )
        
        update_last_action_time()
        st.session_state.modal_doc = None
        st.session_state.modal_opened_time = None



def track_modal_button_click():
    """
    Tracks when the modal button is clicked, handling first click timing
    and clicks after follow-ups.
    """
    st.session_state.modal_clicks_total += 1
    
    if st.session_state.last_expander_click_time is not None:
        st.session_state.expander_then_modal_escalations += 1
        # Reset to avoid double-counting on subsequent modal clicks
        st.session_state.last_expander_click_time = None


    # Track first click timing
    if not st.session_state.first_click_happened and st.session_state.last_answer_time:
        if st.session_state.first_click_latency is None:
            st.session_state.first_click_latency = (
                datetime.now() - st.session_state.last_answer_time
            ).total_seconds()
            st.session_state.first_click_happened = True
    
    # Track clicks after follow-ups
    if st.session_state.followup_count > 0:
        st.session_state.clicks_after_followups += 1


def calculate_final_metrics():
    """
    Calculates final behavioral metrics for task completion.
    
    Returns:
        dict: Dictionary with mean_answer_reading and answer_finalization_time
    """
    # Calculate mean answer reading time
    mean_answer_reading = 0
    if st.session_state.answer_reading_times:
        mean_answer_reading = (
            sum(st.session_state.answer_reading_times) /
            len(st.session_state.answer_reading_times)
        )
    
    # Calculate answer finalization time (MC window to submission)
    answer_finalization_time = 0
    if st.session_state.answer_finalization_start_time:
        answer_finalization_time = (
            datetime.now() - st.session_state.answer_finalization_start_time
        ).total_seconds()
    
    return {
        'mean_answer_reading': mean_answer_reading,
        'answer_finalization_time': answer_finalization_time
    }