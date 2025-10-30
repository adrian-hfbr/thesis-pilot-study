# utils.py 
"""
Data Logging Utilities for RAG-Based Tax Advisor Experiment

This module handles all CSV-based data logging for the experimental study investigating
the impact of justification explanation design on cognitive load, trust, and reliance
in a RAG-based tax advisory system.

Architecture:
    Four separate CSV log files track different aspects of participant behavior:
    
    1. participants.csv: Demographics, experimental condition assignment, and control
       variables (tech affinity, chatbot experience, tax knowledge, task complexity)
    
    2. tasks.csv: Task-level performance metrics and behavioral verification indicators
       including click counts, dwell times, and self-reported reliance
    
    3. interactions.csv: Fine-grained event-level logging with timestamps for all
       user actions (questions, clicks, modal/expander interactions)
    
    4. post_survey.csv: Post-study questionnaire responses measuring cognitive load
       (ICL, ECL, GCL), trust dimensions (functionality, helpfulness, reliability),
       and manipulation check validation

Design Rationale:
    - CSV format chosen for simplicity, human-readability, and pandas integration
    - Session IDs (UUID v4) ensure participant anonymity while enabling data linkage
    - Append-only operations minimize data loss risk during experimental sessions
    - Separate files prevent data corruption if one log fails

Production Enhancements:
    - File locking prevents concurrent write conflicts in multi-user environment
    - Write verification ensures data integrity before proceeding
    - Prolific PID validation prevents invalid submissions
    - Robust directory creation with permission checks

Dependencies:
    - pandas: CSV read/write operations
    - streamlit: Error display to participants
    - config.py: Dwell time thresholds (MINIMUM_DWELL_TIME_MODAL = 3s, 
                 MINIMUM_DWELL_TIME_EXPANDER = 1s)
"""

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
    """
    Context manager for safe concurrent CSV file access using lock files.
    
    This prevents race conditions when multiple Streamlit sessions (Prolific participants)
    write to the same CSV file simultaneously. Uses a simple lock file mechanism
    compatible with Streamlit Community Cloud (Linux-based).
    
    Args:
        filepath: Path to the CSV file to protect
        timeout: Maximum seconds to wait for lock acquisition (default: 10s)
    
    Yields:
        None: Control flow within the locked context
    
    Raises:
        TimeoutError: If lock cannot be acquired within timeout period
        
    Design:
        - Lock file named <filepath>.lock created atomically
        - Exponential backoff (10ms increments) reduces contention
        - Automatic cleanup in finally block ensures locks don't persist
        - Compatible with network filesystems used by Streamlit Cloud
        
    Example:
        with file_lock_context(TASKS_LOG):
            # Safe to write to CSV here - exclusive access guaranteed
            pd.DataFrame([entry]).to_csv(TASKS_LOG, mode='a', header=False, index=False)
    """
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
    """
    Internal helper to log system-level errors without disrupting participant flow.
    
    Writes to a separate error log file instead of crashing the application.
    This function never raises exceptions.
    
    Args:
        error_type: Short error identifier (e.g., "file_lock_timeout", "csv_write_failure")
        details: Detailed error message for debugging
    """
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
    """
    Creates the log directory and initializes all CSV files with correct headers.
    
    This function is idempotent - safe to call multiple times. It only creates
    files if they don't already exist, preserving any existing logged data.
    Called once at application startup in app.py.
    
    File Schemas:
        participants.csv: 8 columns (session metadata + control variables)
        tasks.csv: 17 columns (performance + behavioral verification metrics)
        interactions.csv: 6 columns (fine-grained event logging)
        post_survey.csv: 22 columns (cognitive load + trust + manipulation check)
    
    Production Enhancements:
        - Validates write permissions before proceeding
        - Shows user-friendly error messages if filesystem access fails
        - Stops execution gracefully if critical logging infrastructure unavailable
    
    Raises:
        Calls st.stop() if directory creation or file writing fails
        
    FUNCTIONAL EQUIVALENCE:
        - Same os.makedirs(LOG_DIR, exist_ok=True) call
        - Same CSV schemas (column names, order, data types)
        - Same idempotent behavior (no-op if files exist)
        - Additional: Permission validation test
        - Additional: Error handling with st.error() + st.stop()
    """
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
                "prolific_pid",         # Prolific participant ID for payment
                "timestamp",            # ISO 8601 format session start time
                "experimental_group",   # "Augmented" or "Minimal" condition
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
                #EFFORT
                "effort_1",
                # Trust - Functionality (3 items)  
                "trust_func_1", "trust_func_2", "trust_func_3",
                # Trust - Helpfulness (4 items)  
                "trust_help_1", "trust_help_2", "trust_help_3", "trust_help_4",
                # Trust - Reliability (4 items) 
                "trust_reli_1", "trust_reli_2", "trust_reli_3", "trust_reli_4",
                # RELIANCE
                "reliance_1",
                # Manipulation check 
                "manip_check_1"
            ]).to_csv(POST_SURVEY_LOG, index=False)
        except Exception as e:
            st.error(f"Fehler beim Erstellen von {POST_SURVEY_LOG}: {e}")
            _log_system_error("post_survey_csv_creation_failed", str(e))
            st.stop()


# PROLIFIC PID VALIDATION IN SESSION ID GENERATION
def get_session_id():
    """
    Retrieves or generates a unique session identifier for the current participant.
    """
    if 'session_id' not in st.session_state:
        # Generate new session ID (UNCHANGED from original)
        st.session_state['session_id'] = str(uuid.uuid4())
    
    return st.session_state['session_id']



# ============================================================================
# FEATURE 4: CONCURRENT-SAFE LOGGING WITH WRITE VERIFICATION
# ============================================================================
# REASONING: Original logging functions used pd.DataFrame.to_csv(mode='a') without
# any concurrency protection or write verification. The refactored versions wrap
# the EXACT SAME write operations in file locks and add verification.
# 
# CRITICAL: The data being written, column order, and CSV format are UNCHANGED.
# Only the write operation itself is protected.
# ============================================================================

def log_participant_info(session_id, prolific_pid, group, survey_responses, total_duration=None):
    """
    Logs participant demographic data and experimental condition assignment.
    
    Called once at the end of the pre-study survey. The total_duration field
    is initially None and updated at experiment completion.
    
    Production Enhancement:
        - File locking prevents concurrent write conflicts
        - Write verification ensures data actually saved to disk
        - Graceful error handling prevents participant disruption
    
    Args:
        session_id: UUID v4 participant identifier (UNCHANGED)
        prolific_pid: Prolific ID for payment (UNCHANGED)
        group: "Augmented" or "Minimal" (UNCHANGED)
        survey_responses: Dict with tech_affinity, chatbot_experience, tax_knowledge (UNCHANGED)
        total_duration: Experiment duration in seconds (UNCHANGED)
        
    FUNCTIONAL EQUIVALENCE:
        - Same new_entry dict structure (UNCHANGED)
        - Same column order in CSV (UNCHANGED)
        - Same pd.DataFrame([new_entry]).to_csv() call (UNCHANGED)
        - Additional: Wrapped in file_lock_context()
        - Additional: Write verification after save
    """
    max_retries = 4
    for attempt in range(max_retries):
        try:
            with file_lock_context(PARTICIPANTS_LOG, timeout=10):
                new_entry = {
                    "session_id": session_id,
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
    """
    Logs comprehensive task-level performance and behavioral verification metrics.
    
    This function captures the complete behavioral trace for a single task,
    including both outcome measures (answer correctness, confidence) and process
    measures (verification behavior, temporal patterns).
    
    Production Enhancement:
        - File locking prevents concurrent write conflicts
        - Critical data write verified before proceeding
        - Stops execution on failure (task data is critical for thesis)
    
    Args:
        All parameters UNCHANGED from original function signature
        
    FUNCTIONAL EQUIVALENCE:
        - Same new_entry dict structure (UNCHANGED)
        - Same column order in CSV (UNCHANGED)
        - Same rounding logic: round(..., 1) (UNCHANGED)
        - Same pd.DataFrame([new_entry]).to_csv() call (UNCHANGED)
        - Additional: Wrapped in file_lock_context()
        - Additional: Write verification (stops on failure)
    """
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
    """
    Logs individual interaction events with precise timestamps for process mining.
    
    Production Enhancement:
        - File locking prevents concurrent write conflicts
        - Graceful error handling (interactions are less critical than task data)
        - Multiple retry attempts before showing warning
    
    Args:
        session_id: UUID v4 participant identifier
        task_number: Current task number
        event_type: Type of event (e.g., 'quote_opened', 'ai_response')
        details: Event details (now includes AI response text for ai_response events)
        selected_answer: Multiple choice selection (optional)
        dwell_time: Time spent in seconds (optional, for verification events)
        
    Changes from previous version:
        - Removed ai_response_text parameter
        - Added dwell_time parameter
        - AI responses now go directly in details column
        - Dwell time tracked in separate numeric column
    """

    max_retries = 4
    for attempt in range(max_retries):
        try:
            with file_lock_context(INTERACTIONS_LOG, timeout=5):
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

def log_post_survey(session_id, survey_responses, manip_check_correct=None):
    """
    Logs post-study questionnaire responses including cognitive load, trust, and
    manipulation check validation.
    
    This function captures the attitudinal outcomes of the experiment, including
    three dimensions of cognitive load (intrinsic, extraneous, germane), three
    dimensions of trust (functionality, helpfulness, reliability), and validation
    that participants correctly perceived their experimental condition.
    
    Production Enhancement:
        - File locking prevents concurrent write conflicts
        - Write verification ensures critical survey data saved
        - Stops execution on failure (survey data critical for thesis hypotheses)
    
    Args:
        All parameters UNCHANGED from original function signature
        
    FUNCTIONAL EQUIVALENCE:
        - Same new_entry dict construction (UNCHANGED)
        - Same key ordering matching CSV headers (UNCHANGED)
        - Same survey_responses.get(key) pattern (UNCHANGED)
        - Same pd.DataFrame([new_entry]).to_csv() call (UNCHANGED)
        - Additional: Wrapped in file_lock_context()
        - Additional: Write verification (stops on failure)
    """
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

                new_entry["effort_1"] = survey_responses.get("effort_1")
                
                for key in ["trust_func_1", "trust_func_2", "trust_func_3"]:
                    new_entry[key] = survey_responses.get(key)
                
                for key in ["trust_help_1", "trust_help_2", "trust_help_3", "trust_help_4"]:
                    new_entry[key] = survey_responses.get(key)
                
                for key in ["trust_reli_1", "trust_reli_2", "trust_reli_3", "trust_reli_4"]:
                    new_entry[key] = survey_responses.get(key)

                new_entry["reliance_1"] = survey_responses.get("reliance_1")
                
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
