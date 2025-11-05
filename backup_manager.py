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

@st.cache_resource
def get_s3_client():
    """Initialize and return AWS S3 client and bucket name; gracefully fallback to None on credential/connectivity errors."""
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
        from botocore.config import Config
        
        # Get credentials from Streamlit secrets
        access_key = st.secrets["AWS_ACCESS_KEY_ID"]
        secret_key = st.secrets["AWS_SECRET_ACCESS_KEY"]
        bucket_name = st.secrets["S3_BUCKET_NAME"]
        region = st.secrets.get("AWS_REGION", "eu-central-1")
        
        s3_config = Config(
        connect_timeout=10,           # 10 seconds to establish connection
        read_timeout=30,              # 30 seconds for read operations
        retries={'max_attempts': 2}   # Retry failed uploads twice
        )

        # Create S3 client (no token refresh needed - keys never expire)
        s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=s3_config
        )
        
        # Test connection with a simple operation
        s3_client.head_bucket(Bucket=bucket_name)
        
        return s3_client, bucket_name
        
    except ImportError:
        st.warning("boto3 nicht installiert. Daten sind lokal gespeichert.")
        return None, None
    except KeyError as e:
        st.warning(f"AWS-Konfiguration fehlt in secrets: {e}. Daten sind lokal gespeichert.")
        return None, None
    except NoCredentialsError:
        st.warning("AWS-Zugangsdaten ungültig. Daten sind lokal gespeichert.")
        return None, None
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            st.error(f"S3-Bucket nicht gefunden. Daten sind lokal gespeichert.")
        else:
            st.warning(f"S3-Verbindung fehlgeschlagen: {e}. Daten sind lokal gespeichert.")
        return None, None
    except Exception as e:
        st.warning(f"Unerwarteter Fehler: {e}. Daten sind lokal gespeichert.")
        return None, None

def backup_participant_data(session_id):
    """Back up participant's session data to S3 by filtering and uploading relevant CSV rows after study completion."""
    s3_client, bucket_name = get_s3_client()
    if not s3_client:
        return False

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_count = 0

    # All four regular CSV files + error fallback files
    csv_files = [
        'participants.csv',
        'tasks.csv',
        'interactions.csv',
        'post_survey.csv',
        'participants_error.csv',     
        'tasks_error.csv',        
        'interactions_error.csv',   
        'post_survey_error.csv',     
        'system_errors.log'
    ]

    for csv_file in csv_files:
        try:
            filepath = os.path.join('logs', csv_file)
            
            if not os.path.exists(filepath):
                continue  # Skip if doesn't exist
            
            # For error files and system_errors.log, backup the entire file
            if csv_file.endswith('_error.csv') or csv_file == 'system_errors.log':
                s3_key = f"participants/{session_id}/{timestamp}_{csv_file}"
                s3_client.upload_file(
                    filepath,
                    bucket_name,
                    s3_key,
                    ExtraArgs={'ContentType': 'text/plain' if csv_file.endswith('.log') else 'text/csv'}
                )
            else:
                # For regular CSVs, filter for this participant only
                df = pd.read_csv(filepath)
                participant_df = df[df['session_id'] == session_id]
                
                if len(participant_df) == 0:
                    continue
                
                s3_key = f"participants/{session_id}/{timestamp}_{csv_file}"
                csv_buffer = BytesIO()
                participant_df.to_csv(csv_buffer, index=False)
                csv_buffer.seek(0)
                
                try:
                    s3_client.upload_fileobj(
                        csv_buffer,
                        bucket_name,
                        s3_key,
                        ExtraArgs={'ContentType': 'text/csv'}
                    )
                except Exception as e:
                    if 'Timeout' in str(e):
                        st.error(f"S3 upload timeout for {csv_file}. Data saved locally.")
                    continue
            
            backup_count += 1
            
        except Exception as e:
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
