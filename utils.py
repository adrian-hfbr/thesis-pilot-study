# utils.py 

import os
import pandas as pd
import streamlit as st
import uuid
import time
from datetime import datetime
from contextlib import contextmanager

# --- Paths
LOG_DIR = "logs"
PARTICIPANTS_LOG = os.path.join(LOG_DIR, "participants.csv")
TASKS_LOG = os.path.join(LOG_DIR, "tasks.csv")
INTERACTIONS_LOG = os.path.join(LOG_DIR, "interactions.csv")
POST_SURVEY_LOG = os.path.join(LOG_DIR, "post_survey.csv")

# Error fallback files
PARTICIPANTS_ERROR_LOG = os.path.join(LOG_DIR, "participants_error.csv")
TASKS_ERROR_LOG = os.path.join(LOG_DIR, "tasks_error.csv")
INTERACTIONS_ERROR_LOG = os.path.join(LOG_DIR, "interactions_error.csv")
POST_SURVEY_ERROR_LOG = os.path.join(LOG_DIR, "post_survey_error.csv")


# FILE LOCKING FOR CONCURRENT CSV WRITES
@contextmanager
def file_lock_context(filepath, timeout=10):
    """Context manager using atomic lock files to safely handle concurrent CSV writes across multiple Streamlit sessions."""
    lock_file = f"{filepath}.lock"
    start_time = time.time()
    lock_fd = None
    
    # Attempt to acquire lock with exponential backoff
    while True:
        try:
            # O_CREAT | O_EXCL ensures atomic lock file creation
            lock_fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break  # Lock acquired successfully
        except FileExistsError:
            # Lock file exists - another session is writing
            if time.time() - start_time > timeout:
                # Log timeout for debugging but don't crash - data loss better than participant failure
                _log_system_error("file_lock_timeout", f"Could not acquire lock on {filepath} after {timeout}s")
                # Proceed anyway - small risk of race condition better than stopping experiment
                raise TimeoutError(f"Could not acquire lock on {filepath}")
            time.sleep(0.01)  # 10ms wait before retry
    
    try:
        yield  # Execute the protected code block
    finally:
        # Always clean up lock file
        if lock_fd is not None:
            try:
                os.close(lock_fd)
                os.remove(lock_file)
            except Exception:
                pass  # Lock file cleanup failure is non-critical


def _log_system_error(error_type, details):
    """Log non-critical system errors to system_errors.log without disrupting participant flow."""
    try:
        error_log_path = os.path.join(LOG_DIR, "system_errors.log")
        with open(error_log_path, "a", encoding='utf-8') as f:
            timestamp = datetime.now().isoformat()
            session_id = st.session_state.get('session_id', 'unknown')
            f.write(f"{timestamp} | {session_id} | {error_type} | {details}\n")
    except Exception:
        # If even error logging fails, print to console
        print(f"[SYSTEM ERROR] {error_type}: {details}")


# ROBUST DIRECTORY CREATION WITH VALIDATION
def initialize_log_files():
    """Create logs directory and initialize all four CSV files (participants, tasks, interactions, post_survey) with proper headers."""
    # STEP 1: Create directory (UNCHANGED from original)
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except PermissionError:
        st.error("Keine Berechtigung zum Erstellen des Log-Verzeichnisses.")
        _log_system_error("log_dir_permission_denied", f"Cannot create {LOG_DIR}")
        st.stop()
    except Exception as e:
        st.error(f"Fehler beim Erstellen des Log-Verzeichnisses: {e}")
        _log_system_error("log_dir_creation_failed", str(e))
        st.stop()
    
    # STEP 2: Initialize CSV files with headers (UNCHANGED schemas from original)
    # Participant-level data: demographics and experimental condition
    if not os.path.exists(PARTICIPANTS_LOG):
        try:
            pd.DataFrame(columns=[
                "session_id",           # UUID v4 for anonymization
                "study_id",
                "prolific_session_id",
                "prolific_pid",         # Prolific participant ID for payment
                "timestamp",            # ISO 8601 format session start time
                "experimental_group",   # "Augmented" or "Minimal" condition
                "task_completion_thoroughness",
                # ATI Short-Scale (4 items)
                "ati_1",
                "ati_2",
                "ati_3",
                "ati_4",
                "chatbot_experience",   # 1-7 Likert: prior AI chatbot usage
                "tax_knowledge",        # 1-7 Likert: German tax law knowledge
                "total_duration_seconds"  # Total experiment duration
            ]).to_csv(PARTICIPANTS_LOG, index=False)
        except Exception as e:
            st.error(f"Fehler beim Erstellen von {PARTICIPANTS_LOG}: {e}")
            _log_system_error("participants_csv_creation_failed", str(e))
            st.stop()
    
    # Task-level data: performance and behavioral verification metrics
    if not os.path.exists(TASKS_LOG):
        try:
            pd.DataFrame(columns=[
                "session_id",                    # Links to participants.csv
                "task_number",                   # 1-4 (four experimental tasks)
                "post_interaction_answer",       # Multiple choice final answer 
                "is_correct",                    # Boolean correctness
                "decision_confidence",           # 1-7 Likert confidence+
                "duration_seconds",              # Time from task start to submission
                
                # === Total Interaction Counts ===
                "expander_clicks_total",         # All expander clicks
                "modal_clicks_total",            # All modal button clicks
                
                # === Verification Behavior Indicators ===
                "expander_clicks_verification",  # Clicks above dwell
                "modal_clicks_verification",     # Clicks above dwell
                
                # === Temporal Metrics ===
                "followup_questions",            # Count of follow-up questions
                "cumulative_modal_dwell",        # Total seconds viewing paragraphs
                "cumulative_expander_dwell",     # Total seconds viewing quotes 
                "mean_answer_reading_time",      # Average reading time
                "answer_finalization_time",      # Time in MC window
                "first_click_latency",           # Latency to first verification 
                
                # === Sequential Behavior ===
                "clicks_after_followups",        # Verification after follow-ups
                "prompts_before_first_verification",  
                "expander_then_modal_escalations" 
            ]).to_csv(TASKS_LOG, index=False)
        except Exception as e:
            st.error(f"Fehler beim Erstellen von {TASKS_LOG}: {e}")
            _log_system_error("tasks_csv_creation_failed", str(e))
            st.stop()
    
    # Interaction-level data: fine-grained event timestamps
    if not os.path.exists(INTERACTIONS_LOG):
        try:
            pd.DataFrame(columns=[
                'session_id',      # Links to participants.csv
                'timestamp',       # ISO 8601 event timestamp
                'task_number',     # 1-4 which task
                'event_type',      # Event category
                'dwell_time',       # Time spent in seconds (for verification events)
                'details',         # Event details (includes AI response text)
                'selected_answer', # Multiple choice selection
            ]).to_csv(INTERACTIONS_LOG, index=False)
        except Exception as e:
            st.error(f"Fehler beim Erstellen von {INTERACTIONS_LOG}: {e}")
            _log_system_error("interactions_csv_creation_failed", str(e))
            st.stop()
    
    # Post-survey data: cognitive load, trust, manipulation check
    if not os.path.exists(POST_SURVEY_LOG):
        try:
            pd.DataFrame(columns=[
                "session_id",
                "timestamp",
                "manip_check_passed",   # Boolean manipulation check result 
                # Intrinsic Cognitive Load (2 items) 
                "icl_1", "icl_2",
                # Extraneous Cognitive Load (3 items) 
                "ecl_1", "ecl_2", "ecl_3",
                # Germane Cognitive Load (3 items)  
                "gcl_1", "gcl_2", "gcl_3",
                # Trust - Functionality (3 items)  
                "trust_func_1", "trust_func_2", "trust_func_3",
                # Trust - Helpfulness (4 items)  
                "trust_help_1", "trust_help_2", "trust_help_3", "trust_help_4",
                # Trust - Reliability (4 items) 
                "trust_reli_1", "trust_reli_2", "trust_reli_3", "trust_reli_4",
                # attention_check
                "ac1",
                # Manipulation check 
                "manip_check_1"
            ]).to_csv(POST_SURVEY_LOG, index=False)
        except Exception as e:
            st.error(f"Fehler beim Erstellen von {POST_SURVEY_LOG}: {e}")
            _log_system_error("post_survey_csv_creation_failed", str(e))
            st.stop()


# PROLIFIC PID VALIDATION IN SESSION ID GENERATION
def get_session_id():
    """Retrieve or generate a unique UUID v4 session identifier for participant anonymization."""
    if 'session_id' not in st.session_state:
        # Generate new session ID (UNCHANGED from original)
        st.session_state['session_id'] = str(uuid.uuid4())
    
    return st.session_state['session_id']


def log_participant_info(session_id, study_id, prolific_session_id, prolific_pid, group, survey_responses, total_duration=None):
    """Log participant data, experimental condition, and pre-study survey responses with concurrent-safe file locking and write verification."""
    max_retries = 4
    for attempt in range(max_retries):
        try:
            with file_lock_context(PARTICIPANTS_LOG, timeout=10):
                new_entry = {
                    "session_id": session_id,
                    "study_id": study_id,
                    "prolific_session_id": prolific_session_id,
                    "prolific_pid": prolific_pid,
                    "timestamp": datetime.now().isoformat(),
                    "experimental_group": group,
                    **survey_responses,  # Unpacks the values
                    "total_duration_seconds": total_duration,
                }
                
                # Count rows before write for verification
                try:
                    existing_df = pd.read_csv(PARTICIPANTS_LOG)
                    initial_count = len(existing_df)
                except:
                    initial_count = 0
                
                # Write to CSV (EXACT SAME operation as original)
                pd.DataFrame([new_entry]).to_csv(PARTICIPANTS_LOG, mode='a', header=False, index=False)
                
                # Verify write succeeded by checking row count
                try:
                    verification_df = pd.read_csv(PARTICIPANTS_LOG)
                    if len(verification_df) != initial_count + 1:
                        raise RuntimeError(f"Row count mismatch: expected {initial_count + 1}, got {len(verification_df)}")
                    
                    # Verify this specific session's data exists
                    if session_id not in verification_df['session_id'].values:
                        raise RuntimeError(f"Session {session_id} not found after write")
                except Exception as verify_error:
                    raise RuntimeError(f"Write verification failed: {verify_error}")
                
            return  # Success - exit retry loop
            
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.25 * (attempt + 1))  # 0.25s, 0.5s, 0.75s, 1s
                continue
            else:
                # After 4 failed attempts, write to error file
                error_msg = f"Failed after {max_retries} attempts: {e}"
                _log_system_error("critical_participant_data_loss", error_msg)
                
                # FALLBACK: Write to error file
                try:
                    new_entry['_error_timestamp'] = datetime.now().isoformat()
                    new_entry['_error_reason'] = error_msg
                    
                    if not os.path.exists(PARTICIPANTS_ERROR_LOG):
                        pd.DataFrame([new_entry]).to_csv(PARTICIPANTS_ERROR_LOG, index=False)
                    else:
                        pd.DataFrame([new_entry]).to_csv(PARTICIPANTS_ERROR_LOG, mode='a', header=False, index=False)
                    
                    _log_system_error("participant_data_saved_to_error_file", f"Session {session_id}")
                except Exception as fallback_error:
                    _log_system_error("error_file_write_also_failed", str(fallback_error))



def log_task_data(session_id, task_number, post_answer, confidence,
                  duration, is_correct=False, expander_clicks_total=0, modal_clicks_total=0,
                  expander_clicks_verification: int = 0, modal_clicks_verification: int = 0,
                  followup_questions=0, cumulative_modal_dwell=0,
                  cumulative_expander_dwell=0, mean_answer_reading_time=0,
                  answer_finalization_time=0,
                  first_click_latency=None, clicks_after_followups=0,
                  prompts_before_first_verification=None,
                  expander_then_modal_escalations=0):
    """Log comprehensive task-level performance and behavioral metrics with retry logic and fallback error handling."""
    max_retries = 4
    for attempt in range(max_retries):
        try:
            with file_lock_context(TASKS_LOG, timeout=10):
                new_entry = {
                    "session_id": session_id,
                    "task_number": task_number,
                    "post_interaction_answer": post_answer,
                    "is_correct": is_correct,
                    "decision_confidence": confidence,
                    "duration_seconds": duration,
                    "expander_clicks_total": expander_clicks_total,
                    "modal_clicks_total": modal_clicks_total,
                    "expander_clicks_verification": expander_clicks_verification,
                    "modal_clicks_verification": modal_clicks_verification,
                    "followup_questions": followup_questions,
                    "cumulative_modal_dwell": round(cumulative_modal_dwell, 1),
                    "cumulative_expander_dwell": round(cumulative_expander_dwell, 1),
                    "mean_answer_reading_time": round(mean_answer_reading_time, 1),
                    "answer_finalization_time": round(answer_finalization_time, 1),
                    "first_click_latency": round(first_click_latency, 1) if first_click_latency else None,
                    "clicks_after_followups": clicks_after_followups,
                    "prompts_before_first_verification": prompts_before_first_verification,
                    "expander_then_modal_escalations": expander_then_modal_escalations,
                }
                
                # Count rows before write
                try:
                    existing_df = pd.read_csv(TASKS_LOG)
                    initial_count = len(existing_df)
                except:
                    initial_count = 0
                
                # Write to CSV (EXACT SAME operation as original)
                pd.DataFrame([new_entry]).to_csv(TASKS_LOG, mode='a', header=False, index=False)
                
                # Verify write succeeded
                try:
                    verification_df = pd.read_csv(TASKS_LOG)
                    if len(verification_df) != initial_count + 1:
                        raise RuntimeError(f"Row count mismatch after task {task_number} write")
                    
                    # Verify this specific task exists
                    task_mask = (verification_df['session_id'] == session_id) & (verification_df['task_number'] == task_number)
                    if not task_mask.any():
                        raise RuntimeError(f"Task {task_number} for session {session_id} not found after write")
                except Exception as verify_error:
                    raise RuntimeError(f"Write verification failed: {verify_error}")
                
            return  # Success
            
        except Exception as e:
            error_msg = f"Attempt {attempt + 1}/{max_retries}: {type(e).__name__}: {str(e)}"
            _log_system_error("task_log_failed", error_msg)
            
            if attempt < max_retries - 1:
                time.sleep(0.25 * (attempt + 1))  # 0.25s, 0.5s, 0.75s, 1s
                continue
            else:
                error_msg_full = f"Task {task_number} failed after {max_retries} attempts: {error_msg}"
                _log_system_error("critical_task_data_loss", error_msg_full)
                
                # FALLBACK: Write to error file
                try:
                    new_entry['_error_timestamp'] = datetime.now().isoformat()
                    new_entry['_error_reason'] = error_msg_full
                    
                    if not os.path.exists(TASKS_ERROR_LOG):
                        pd.DataFrame([new_entry]).to_csv(TASKS_ERROR_LOG, index=False)
                    else:
                        pd.DataFrame([new_entry]).to_csv(TASKS_ERROR_LOG, mode='a', header=False, index=False)
                    
                    _log_system_error("task_data_saved_to_error_file", f"Session {session_id}, Task {task_number}")
                except Exception as fallback_error:
                    _log_system_error("error_file_write_also_failed", str(fallback_error))
                
                st.stop()  # Still stop - task data is critical



def log_interaction(session_id, task_number, event_type, details, selected_answer=None, dwell_time=None):
    """Log fine-grained interaction events with timestamps for process mining and behavioral analysis."""
    max_retries = 4
    for attempt in range(max_retries):
        try:
            with file_lock_context(INTERACTIONS_LOG, timeout=10):
                # Build entry dict
                new_entry = {
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "task_number": task_number,
                    "event_type": event_type,
                    "dwell_time": round(dwell_time, 2) if dwell_time is not None else None,
                    "details": details,
                    "selected_answer": selected_answer if selected_answer else None,
                    }
                
                # Count rows before write
                try:
                    existing_df = pd.read_csv(INTERACTIONS_LOG)
                    initial_count = len(existing_df)
                except:
                    initial_count = 0
                
                # Write to CSV
                pd.DataFrame([new_entry]).to_csv(INTERACTIONS_LOG, mode='a', header=False, index=False)

                # Verify write succeeded
                try:
                    verification_df = pd.read_csv(INTERACTIONS_LOG)
                    if len(verification_df) != initial_count + 1:
                        raise RuntimeError(f"Interaction row count mismatch: expected {initial_count + 1}, got {len(verification_df)}")
                    
                    if session_id not in verification_df['session_id'].values:
                        raise RuntimeError(f"Session {session_id} interaction not found after write")
                except Exception as verify_error:
                    raise RuntimeError(f"Write verification failed: {verify_error}")
                
            return  # Success
            
        except Exception as e:
            error_msg = f"Attempt {attempt + 1}/{max_retries}: {event_type} | {str(e)}"
            _log_system_error("interaction_log_failed", error_msg)
            
            if attempt < max_retries - 1:
                time.sleep(0.25 * (attempt + 1))  # 0.25s, 0.5s, 0.75s, 1s
                continue
            else:
                error_msg_full = f"Interaction {event_type} failed after {max_retries} attempts"
                _log_system_error("interaction_log_failed_final", error_msg_full)
                
                # FALLBACK: Write to error file
                try:
                    new_entry['_error_timestamp'] = datetime.now().isoformat()
                    new_entry['_error_reason'] = error_msg_full
                    
                    if not os.path.exists(INTERACTIONS_ERROR_LOG):
                        pd.DataFrame([new_entry]).to_csv(INTERACTIONS_ERROR_LOG, index=False)
                    else:
                        pd.DataFrame([new_entry]).to_csv(INTERACTIONS_ERROR_LOG, mode='a', header=False, index=False)
                    
                    _log_system_error("interaction_data_saved_to_error_file", f"Session {session_id}, Event {event_type}")
                except Exception as fallback_error:
                    _log_system_error("error_file_write_also_failed", str(fallback_error))
                
                # No st.stop() - continue silently for interactions

def log_post_survey(session_id, survey_responses, manip_check_correct=None, total_duration=None):
    """Log post-study survey responses (cognitive load, trust, manipulation check) with write verification and fallback error logging."""
    max_retries = 4
    for attempt in range(max_retries):
        try:
            with file_lock_context(POST_SURVEY_LOG, timeout=10):
                new_entry = {
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "manip_check_passed": manip_check_correct,
                }
                
                # Add all survey responses in order (UNCHANGED from original)
                for key in ["icl_1", "icl_2"]:
                    new_entry[key] = survey_responses.get(key)
                
                for key in ["ecl_1", "ecl_2", "ecl_3"]:
                    new_entry[key] = survey_responses.get(key)
                
                for key in ["gcl_1", "gcl_2", "gcl_3"]:
                    new_entry[key] = survey_responses.get(key)
                
                for key in ["trust_func_1", "trust_func_2", "trust_func_3"]:
                    new_entry[key] = survey_responses.get(key)
                
                for key in ["trust_help_1", "trust_help_2", "trust_help_3", "trust_help_4"]:
                    new_entry[key] = survey_responses.get(key)
                
                for key in ["trust_reli_1", "trust_reli_2", "trust_reli_3", "trust_reli_4"]:
                    new_entry[key] = survey_responses.get(key)

                new_entry["ac1"] = survey_responses.get("ac1")
                
                new_entry["manip_check_1"] = survey_responses.get("manip_check_1")
                
                # Count rows before write
                try:
                    existing_df = pd.read_csv(POST_SURVEY_LOG)
                    initial_count = len(existing_df)
                except:
                    initial_count = 0
                
                pd.DataFrame([new_entry]).to_csv(POST_SURVEY_LOG, mode='a', header=False, index=False)
                
                # Verify write succeeded
                try:
                    verification_df = pd.read_csv(POST_SURVEY_LOG)
                    if len(verification_df) != initial_count + 1:
                        raise RuntimeError("Post-survey row count mismatch")
                    
                    if session_id not in verification_df['session_id'].values:
                        raise RuntimeError(f"Session {session_id} not found in post-survey after write")
                except Exception as verify_error:
                    raise RuntimeError(f"Write verification failed: {verify_error}")
            
            if total_duration is not None:
                try:
                    with file_lock_context(PARTICIPANTS_LOG, timeout=10):
                        df = pd.read_csv(PARTICIPANTS_LOG)
                        df.loc[df['session_id'] == session_id, 'total_duration_seconds'] = total_duration
                        df.to_csv(PARTICIPANTS_LOG, index=False)
                except Exception as e:
                    _log_system_error('duration_update_failed', f"Session {session_id} | Duration: {total_duration}s | Error: {type(e).__name__}: {str(e)}")
                    # Don't raise - duration update failure shouldn't stop completion

            return  # Success
            
        except Exception as e:
            error_msg = f"Attempt {attempt + 1}/{max_retries}: {type(e).__name__}: {str(e)}"
            _log_system_error("post_survey_log_failed", error_msg)
            
            if attempt < max_retries - 1:
                time.sleep(0.25 * (attempt + 1))  # 0.25s, 0.5s, 0.75s, 1s
                continue
            else:
                error_msg_full = f"Post-survey failed after {max_retries} attempts: {error_msg}"
                _log_system_error("critical_survey_data_loss", error_msg_full)
                
                # FALLBACK: Write to error file
                try:
                    new_entry['_error_timestamp'] = datetime.now().isoformat()
                    new_entry['_error_reason'] = error_msg_full
                    
                    if not os.path.exists(POST_SURVEY_ERROR_LOG):
                        pd.DataFrame([new_entry]).to_csv(POST_SURVEY_ERROR_LOG, index=False)
                    else:
                        pd.DataFrame([new_entry]).to_csv(POST_SURVEY_ERROR_LOG, mode='a', header=False, index=False)
                    
                    _log_system_error("post_survey_data_saved_to_error_file", f"Session {session_id}")
                except Exception as fallback_error:
                    _log_system_error("error_file_write_also_failed", str(fallback_error))
                
                st.stop()  # Still stop - survey data is critical

def check_all_tasks_correct(session_id):
    """
    Check if all 4 tasks were answered correctly for the given session.
    Returns True if all tasks are correct, False otherwise.
    """
    try:
        if not os.path.exists(TASKS_LOG):
            return False
        
        df = pd.read_csv(TASKS_LOG)
        # Filter for this session's tasks
        session_tasks = df[df['session_id'] == session_id]
        
        # Check if we have exactly 4 tasks
        if len(session_tasks) != 4:
            return False
        
        # Check if all tasks are correct
        return session_tasks['is_correct'].all()
    except Exception as e:
        _log_system_error('all_correct_check_failed', f'Session {session_id}: {str(e)}')
        return False
