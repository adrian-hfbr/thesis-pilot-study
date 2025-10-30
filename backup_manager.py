# backup_manager.py
"""
AWS S3 Backup System for Thesis Experiment
Per-participant backup after completion, local CSV for performance.
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime
from io import BytesIO

def get_s3_client():
    """
    Initialize AWS S3 client with access keys (simple, never expires).
    Cached to avoid recreating connection on every call.
    """
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
        
        # Get credentials from Streamlit secrets
        access_key = st.secrets["AWS_ACCESS_KEY_ID"]
        secret_key = st.secrets["AWS_SECRET_ACCESS_KEY"]
        bucket_name = st.secrets["S3_BUCKET_NAME"]
        region = st.secrets.get("AWS_REGION", "eu-central-1")
        
        # Create S3 client (no token refresh needed - keys never expire)
        s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        
        # Test connection with a simple operation
        s3_client.head_bucket(Bucket=bucket_name)
        
        return s3_client, bucket_name
        
    except ImportError:
        st.warning("⚠️ boto3 nicht installiert. Daten sind lokal gespeichert.")
        return None, None
    except KeyError as e:
        st.warning(f"⚠️ AWS-Konfiguration fehlt in secrets: {e}. Daten sind lokal gespeichert.")
        return None, None
    except NoCredentialsError:
        st.warning("⚠️ AWS-Zugangsdaten ungültig. Daten sind lokal gespeichert.")
        return None, None
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            st.error(f"⚠️ S3-Bucket nicht gefunden. Daten sind lokal gespeichert.")
        else:
            st.warning(f"⚠️ S3-Verbindung fehlgeschlagen: {e}. Daten sind lokal gespeichert.")
        return None, None
    except Exception as e:
        st.warning(f"⚠️ Unerwarteter Fehler: {e}. Daten sind lokal gespeichert.")
        return None, None

def backup_participant_data(session_id, prolific_pid):
    """
    Backup all CSV data for one participant to S3 immediately after completion.
    
    This function:
    1. Reads each CSV file
    2. Filters for current participant's data only
    3. Uploads their data to S3 as separate files
    4. Fails gracefully - data remains in local CSV if backup fails
    
    Args:
        session_id (str): Participant's unique session ID
        prolific_pid (str): Prolific participant ID for file naming
        
    Returns:
        bool: True if at least one file backed up successfully, False otherwise
    """
    s3_client, bucket_name = get_s3_client()
    if not s3_client:
        # S3 not configured or failed - data is still safe in local CSV
        return False
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_count = 0
    
    # All four CSV files to backup
    csv_files = [
        'participants.csv',
        'tasks.csv',
        'interactions.csv',
        'post_survey.csv'
    ]
    
    for csv_file in csv_files:
        try:
            filepath = os.path.join('logs', csv_file)
            
            # Check if file exists
            if not os.path.exists(filepath):
                continue
            
            # Read CSV and filter for this participant
            df = pd.read_csv(filepath)
            participant_df = df[df['session_id'] == session_id]
            
            # Skip if no data for this participant
            if len(participant_df) == 0:
                continue
            
            # Create S3 key (path) with organized structure
            s3_key = f"participants/{session_id}/{timestamp}_{csv_file}"
            
            # Convert DataFrame to CSV bytes
            csv_buffer = BytesIO()
            participant_df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            
            # Upload to S3
            s3_client.upload_fileobj(
                csv_buffer,
                bucket_name,
                s3_key,
                ExtraArgs={'ContentType': 'text/csv'}
            )
            
            backup_count += 1
            
        except Exception as e:
            # Log error but continue with other files
            print(f"Warning: Backup failed for {csv_file}: {e}")
            continue
    
    return backup_count > 0

def backup_all_csvs():
    """
    Backup complete CSV files (all participants) to S3.
    Used for manual full backups via admin panel.
    
    Returns:
        bool: True if all files backed up successfully, False otherwise
    """
    s3_client, bucket_name = get_s3_client()
    if not s3_client:
        return False
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    success_count = 0
    
    csv_files = [
        'participants.csv',
        'tasks.csv',
        'interactions.csv',
        'post_survey.csv'
    ]
    
    for csv_file in csv_files:
        try:
            filepath = os.path.join('logs', csv_file)
            
            # Check if file exists
            if not os.path.exists(filepath):
                continue
            
            # Create S3 key for full backup
            s3_key = f"full_backups/{timestamp}_{csv_file}"
            
            # Upload entire file
            s3_client.upload_file(
                filepath,
                bucket_name,
                s3_key,
                ExtraArgs={'ContentType': 'text/csv'}
            )
            
            success_count += 1
            
        except Exception as e:
            print(f"Warning: Full backup failed for {csv_file}: {e}")
            continue
    
    return success_count == len(csv_files)
