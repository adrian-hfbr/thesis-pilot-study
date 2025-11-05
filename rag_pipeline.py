import os
import streamlit as st
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents.stuff import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import config
from utils import log_interaction
import re
import time
import content

try:
    from tenacity import (
        retry,
        wait_random_exponential,
        stop_after_attempt,
        retry_if_exception_type
    )
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    print("[WARNING] tenacity not installed - basic retry will be used")

# OpenAI error types for selective retry
try:
    from openai import RateLimitError, APIError, APIConnectionError, APITimeoutError
    OPENAI_ERRORS_AVAILABLE = True
except ImportError:
    # Fallback for older openai versions
    OPENAI_ERRORS_AVAILABLE = False
    print("[WARNING] openai error types not available - will catch generic exceptions")


"""
To encapsulate the logic for retrieving information and generating answers.
It will be designed to load the pre-built index and provide the necessary
data for both experimental conditions.

Production-grade error handling includes:
- API key validation before initialization
- Exponential backoff for OpenAI API calls
- FAISS index loading with retry logic
- Timeout protection for long-running retrieval
- Graceful degradation for quote extraction failures
- Comprehensive error logging for thesis analysis
"""


class RAGPipeline:
    def __init__(self, params):
        """
        Initialize RAG pipeline with validation and error handling.
        
        Args:
            params: Configuration object (config.py)
        
        Raises:
            Stops Streamlit execution if critical components fail to initialize.
        """
        self.config = params
        
        # STEP 1: Validate API key exists and has correct format
        try:
            self.openai_api_key = st.secrets["OPENAI_API_KEY"]
            
            # Validate key format (should start with 'sk-' and be reasonable length)
            if not self.openai_api_key or len(self.openai_api_key) < 20:
                raise ValueError("API key appears to be invalid (too short)")
            
            if not self.openai_api_key.startswith('sk-'):
                raise ValueError("API key does not start with 'sk-'")
                
        except KeyError:
            st.error("KONFIGURATIONSFEHLER: OpenAI API Key nicht in Streamlit Secrets gefunden.")
            self._log_critical_error("missing_openai_api_key", "API key not found in secrets")
            st.stop()
        except ValueError as e:
            st.error(f"KONFIGURATIONSFEHLER: {e}")
            self._log_critical_error("invalid_api_key_format", str(e))
            st.stop()
        except Exception as e:
            st.error(f"Fehler beim Laden der API-Konfiguration: {e}")
            self._log_critical_error("api_key_load_error", str(e))
            st.stop()
        
        # STEP 2: Initialize main LLM with validated key
        try:
            self.main_llm = ChatOpenAI(
                model=self.config.LLM_MODEL, 
                openai_api_key=self.openai_api_key, 
                temperature=0.0
            )
        except Exception as e:
            st.error(f"Fehler beim Initialisieren des Sprachmodells: {e}")
            self._log_critical_error("llm_initialization_failed", str(e))
            st.stop()
        
        # STEP 3: Load FAISS retriever with retry logic
        self.retriever = self._load_retriever()
        if not self.retriever:
            st.error("Wissensbasis konnte nicht geladen werden.")
            st.info(f"Session ID für Support: {st.session_state.get('session_id', 'unknown')}")
            st.stop()


    def _log_critical_error(self, error_type, details):
        """
        Log critical errors that prevent system initialization.
        
        Args:
            error_type: Short identifier for error category
            details: Detailed error message
        """
        try:
            with open("logs/critical_errors.log", "a", encoding='utf-8') as f:
                timestamp = datetime.now().isoformat()
                session_id = st.session_state.get('session_id', 'unknown')
                f.write(f"{timestamp} | {session_id} | {error_type} | {details}\n")
        except Exception:
            # If logging fails, at least print to console
            print(f"[CRITICAL ERROR] {error_type}: {details}")


    def _load_retriever(self):
        """
        Load FAISS vector store with exponential backoff retry logic.
        
        Returns:
            LangChain retriever object or None on failure
        """
        vectorstore_path = self.config.VECTORSTORE_PATH
        
        # Validate path exists before attempting load
        if not os.path.exists(vectorstore_path):
            st.error(f"FAISS Index nicht gefunden: {vectorstore_path}")
            st.info("Create_index.py ausführen!")
            self._log_critical_error("faiss_index_missing", f"Path: {vectorstore_path}")
            return None
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Initialize embeddings
                embeddings = OpenAIEmbeddings(
                    model=self.config.EMBEDDING_MODEL, 
                    openai_api_key=self.openai_api_key
                )
                
                # Load FAISS index
                vectorstore = FAISS.load_local(
                    vectorstore_path, 
                    embeddings, 
                    allow_dangerous_deserialization=True
                )
                
                # Create retriever
                retriever = vectorstore.as_retriever(
                    search_kwargs={"k": self.config.SEARCH_K}
                )
                
                print(f"[SUCCESS] FAISS index loaded successfully on attempt {attempt + 1}")
                return retriever
                
            except Exception as e:
                error_msg = f"Attempt {attempt + 1}/{max_retries}: {type(e).__name__}: {str(e)}"
                print(f"[ERROR] FAISS load failed - {error_msg}")
                
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2 ** attempt
                    print(f"[RETRY] Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    # Final failure - log extensively
                    st.error(f"FAISS-Index konnte nach {max_retries} Versuchen nicht geladen werden.")
                    st.error(f"Technische Details: {type(e).__name__}")
                    self._log_critical_error("faiss_load_failed", error_msg)
                    return None


    def _call_llm_with_retry(self, chain_or_llm, input_data):
        """
        Wrapper for LLM calls with exponential backoff retry logic.
        
        Handles transient errors like rate limits, API errors, and timeouts.
        Uses tenacity library if available, falls back to manual retry otherwise.
        
        Args:
            chain_or_llm: LangChain chain or LLM object to invoke
            input_data: Input dict or string for the chain/LLM
        
        Returns:
            Response from chain/LLM
        
        Raises:
            Exception: If all retry attempts fail
        """
        if TENACITY_AVAILABLE and OPENAI_ERRORS_AVAILABLE:
            # Use tenacity for sophisticated retry logic
            @retry(
                retry=retry_if_exception_type((
                    RateLimitError, 
                    APIError, 
                    APITimeoutError, 
                    APIConnectionError
                )),
                wait=wait_random_exponential(multiplier=1, max=60),
                stop=stop_after_attempt(5),
                reraise=True
            )
            def _invoke_with_tenacity():
                if hasattr(chain_or_llm, 'invoke'):
                    return chain_or_llm.invoke(input_data)
                else:
                    # For direct LLM calls (quote extraction)
                    return chain_or_llm(input_data)
            
            return _invoke_with_tenacity()
        
        else:
            # Fallback: Manual retry with exponential backoff
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    if hasattr(chain_or_llm, 'invoke'):
                        return chain_or_llm.invoke(input_data)
                    else:
                        return chain_or_llm(input_data)
                        
                except Exception as e:
                    error_type = type(e).__name__
                    
                    # Check if error is retryable
                    retryable_errors = ['RateLimitError', 'APIError', 'Timeout', 'APIConnectionError']
                    is_retryable = any(err in error_type for err in retryable_errors)
                    
                    if attempt < max_retries - 1 and is_retryable:
                        wait_time = min(2 ** attempt, 60)  # Cap at 60 seconds
                        print(f"[RETRY] {error_type} on attempt {attempt + 1}, waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise e

    def _is_no_answer_response(self, text):
        """
        Detektiert ob eine Antwort eine "No Answer"-Antwort ist.
        Verwendet für: Chat-History-Filterung & Response-Validierung
        
        Args:
            text: Zu prüfende Antwort (string)
        
        Returns:
            bool: True wenn No-Answer, False sonst
        """
        if not text:
            return True
        
        no_answer_keywords = [
            "keine informationen",
            "keine hinweise", 
            "enthalten keine",
            "bitte stellen sie erneut die frage",
            "kann diese frage nicht beantworten",
            "nicht ausreichend informationen",
            "gesetzestexte enthalten keine"
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in no_answer_keywords)


    def get_response(self, query, group=None, chat_history=None):
        """
        Generate response with optional conversation history.
        
        Production-grade error handling ensures graceful degradation on failures.
        All errors are logged for thesis analysis.
        
        Args:
            query: Current user question
            group: Experimental condition (Augmented/Minimal)
            chat_history: List of dicts with 'query' and 'answer' keys
        
        Returns:
            Dict with keys: answer, context, quote, legal_reference, no_answer, error
        """
        # STEP 1: Build contextualized query if history exists
        contextualized_query = query
        
        if chat_history and len(chat_history) > 0:
            no_answer_phrases = [
                "keine informationen",
                "enthalten keine",
                "bitte stellen sie",
            ]
            
            useful_history = [
                turn for turn in chat_history[-4:]
                if not any(keyword in turn['answer'].lower() for keyword in no_answer_phrases)
            ]
            
            # only contextualize, if history is useful
            if useful_history:
                history_text = "\n".join([
                    f"Vorherige Frage: {turn['query']}\nVorherige Antwort: {turn['answer']}"
                    for turn in useful_history
                ])
                
                contextualized_query = f"""Bisheriger Gesprächskontext für dieses Steuerszenario:
                {history_text}

                Aktuelle Frage: {query}

                Anweisungen: Falls die aktuelle Frage sich auf vorherige Antworten bezieht ("das", "dieser Betrag", "die Regelung", etc.), nutze den obigen Gesprächsverlauf, um die Frage zu verstehen."""
            else:
                contextualized_query = query
        else:
            contextualized_query = query

        # STEP 2: Create RAG chain
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", content.UNIVERSAL_PROMPT),
                ("human", "{input}")
            ])
            
            question_answer_chain = create_stuff_documents_chain(self.main_llm, prompt)
            rag_chain = create_retrieval_chain(self.retriever, question_answer_chain)
        except Exception as e:
            self._log_rag_error("chain_creation_failed", query, e)
            return self._create_error_response(
                "Die Anfrage konnte nicht verarbeitet werden. Bitte versuchen Sie es erneut.",
                recoverable=True
            )
        
        # STEP 3: Invoke RAG chain with timeout and retry logic
        try:
            # Wrap in timeout to prevent indefinite hangs
            def retrieve_and_generate():
                return self._call_llm_with_retry(rag_chain, {"input": contextualized_query})
            
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(retrieve_and_generate)
                rag_response = future.result(timeout=45)  # 45 second timeout
                
        except FutureTimeoutError:
            # Retrieval/generation took too long
            self._log_rag_error("timeout", query, FutureTimeoutError("45s timeout exceeded"))
            return self._create_error_response(
                "Die Verarbeitung hat zu lange gedauert. Bitte versuchen Sie eine kürzere Frage.",
                recoverable=True
            )
            
        except Exception as e:
            # All retries exhausted or non-retryable error
            self._log_rag_error("rag_invocation_failed", query, e)
            
            # Check if error is potentially recoverable
            error_type = type(e).__name__
            recoverable = error_type in ['RateLimitError', 'APIConnectionError', 'Timeout']
            
            if recoverable:
                message = f"Die KI ist momentan überlastet. Bitte versuchen Sie es in ein paar Sekunden erneut."
                # Log the rate limit/overload error
                if hasattr(st.session_state, 'session_id'):
                    log_interaction(
                        session_id=st.session_state.session_id,
                        task_number=st.session_state.get('task_number', -1),
                        event_type="api_overload_error",
                        details=f"Query: {query[:30]} | Error: {error_type}"
                    )
            else:
                message = "Ein technischer Fehler ist aufgetreten. Bitte formulieren Sie Ihre Frage anders."
            
            return self._create_error_response(message, recoverable=recoverable)


        # STEP 4: Extract answer and context
        answer = rag_response.get("answer", "")
        retrieved_docs = rag_response.get("context", [])


        # ════════════════════════════════════════════════════════════════
        # DEBUG OUTPUT
        print("\n" + "="*80)
        print(f"[DEBUG] Query: {query}")
        print(f"[DEBUG] Retrieved {len(retrieved_docs)} documents")

        for i, doc in enumerate(retrieved_docs):
            legal_ref = doc.metadata.get('legal_reference', 'N/A')
            print(f"\n[{i}] {legal_ref}")
            
            # First 200 characters
            preview = doc.page_content[:200].replace('\n', ' ')
            print(f"{preview}...")
            
            # Extract amounts in document
            amounts = re.findall(r'(\d+)\s*(?:€|Euro)', doc.page_content)
            if amounts:
                print(f"    Amounts: {list(set(amounts))}")

        print(f"\n[DEBUG] Generated Answer: {answer[:250]}...")


        # STEP 5: Check for "no answer" condition
        if "Bitte stellen Sie erneut die Frage" in answer:
            return {
                "answer": "Bitte stellen Sie erneut die Frage.",
                "context": [],
                "quote": None,
                "legal_reference": None,
                "no_answer": True
            }
        
        # STEP 6: Validate retrieved documents
        if not retrieved_docs:
            return {
                "answer": "Bitte stellen Sie erneut die Frage.",
                "context": [],
                "quote": None,
                "legal_reference": None,
                "no_answer": True
            }

        # STEP 7: Select most relevant document
        top_doc = self._smart_document_selection(answer, retrieved_docs)

        # STEP 8: Extract clean legal reference from metadata
        source_text = top_doc.page_content
        legal_ref = top_doc.metadata.get('legal_reference', 'Unbekannte Quelle')
        legal_ref_full = top_doc.metadata.get('legal_reference_full', legal_ref)
        
        # STEP 9: Fix any hallucinated citations in answer
        answer = self._fix_hallucinated_citation(answer, legal_ref, source_text)

        # STEP 10: Extract supporting quote (only for Augmented condition)
        supporting_quote = None
        
        if group == "Augmented":
            supporting_quote = self._extract_quote_with_error_handling(
                query, answer, source_text
            )
        
        # STEP 11: Return complete response
        return {
            "answer": answer,
            "context": [top_doc],  # Single document only
            "quote": supporting_quote,
            "legal_reference": legal_ref,  # "EStG §35a"
            "legal_reference_full": legal_ref_full,  # "EStG §35a Abs. 2"
            "no_answer": False,
            "error": False
        }


    def _extract_quote_with_error_handling(self, query, answer, source_text):
        """
        Extract supporting quote with 3-tier fallback hierarchy:
        Tier 1: LLM extraction
        Tier 2: Hardcoded fallback (Tasks 1-4 only)
        Tier 3: "Es passt kein Zitat zu Ihrer Anfrage ..."
        """
        # Get current task number from session state
        task_number = st.session_state.get('task_number', None)
        
        try:
            # TIER 1: LLM-based extraction
            quote_prompt = content.QUOTE_EXTRACTION_PROMPT.format(
                user_query=query,
                answer=answer,
                source_text=source_text
            )
            
            quote_response = self._call_llm_with_retry(self.main_llm, quote_prompt)
            extracted_quote = quote_response.content.strip()
            
            # Validate extraction
            failure_keywords = ["KEINE_EXTRAKTION", "kein direktes Zitat", "nicht gefunden", "Es wurde kein"]
            has_failure = any(kw.lower() in extracted_quote.lower() for kw in failure_keywords)
            
            if len(extracted_quote) >= 50 and not has_failure:
                print(f"[QUOTE] Tier 1 success: {len(extracted_quote)} chars")
                return extracted_quote

            print(f"[QUOTE] Tier 2 hardcoded for Task {task_number}")
            self._log_quote_extraction_error(query, task_number, "hardcoded")

            # ADD DEFENSIVE CHECK HERE:
            if task_number and task_number in content.FALLBACK_QUOTES:
                return content.FALLBACK_QUOTES[task_number]
            else:
                return "Es passt kein Zitat zu Ihrer Anfrage. Bitte versuchen Sie es mit spezifischeren Begriffen erneut."
            
        except Exception as e:
            print(f"[QUOTE ERROR] {type(e).__name__}: {e}")
            # Try hardcoded even on exception
            if task_number and task_number in content.FALLBACK_QUOTES:
                self._log_quote_extraction_error(query, task_number, f"exception_fallback_{type(e).__name__}")
                return content.FALLBACK_QUOTES[task_number]
            return "Es passt kein Zitat zu Ihrer Anfrage. Bitte versuchen Sie es mit spezifischeren Begriffen erneut."


    def _smart_document_selection(self, answer: str, retrieved_docs: list) -> dict:
        """
        Intelligente Dokumentenauswahl die Absatz/Paragraph-Verwechslungen erkennt.
        
        Löst das Problem: LLM schreibt "§9" wenn es §20 Abs. 9 meint.
        
        Args:
            answer: Generierte LLM-Antwort mit potentieller Zitation
            retrieved_docs: Liste der k=2 FAISS-abgerufenen Dokumente
        
        Returns:
            Document object - das wahrscheinlich genutzte Quelldokument
        """
        all_numbers_in_answer = re.findall(r'§\s*(\d+[a-z]?)', answer)
        
        if not all_numbers_in_answer:
            print("[DOC SELECTION] No citation found, using retrieved_docs[0]")
            return retrieved_docs[0]
        
        print(f"[DOC SELECTION] Found citations: {all_numbers_in_answer}")
        
        for number in all_numbers_in_answer:
            for doc in retrieved_docs:
                legal_ref = doc.metadata.get('legal_reference', '')
                
                if number in legal_ref:
                    print(f"[DOC SELECTION] ✓ Exact match: §{number} found in {legal_ref}")
                    return doc
                
                absatz_pattern = rf'\(({number})\)'
                absatz_match = re.search(absatz_pattern, doc.page_content)
                
                if absatz_match:
                    print(f"[DOC SELECTION] Found ({number}) as Absatz in {legal_ref}")
                    
                    answer_keywords = set(re.findall(r'\b\w{5,}\b', answer.lower()))
                    doc_keywords = set(re.findall(r'\b\w{5,}\b', doc.page_content.lower()))
                    
                    overlap = len(answer_keywords & doc_keywords)
                    overlap_ratio = overlap / len(answer_keywords) if answer_keywords else 0
                    
                    print(f"[DOC SELECTION] Keyword overlap: {overlap} words ({overlap_ratio:.2%})")
                    
                    if overlap >= 3 or overlap_ratio >= 0.2:
                        print(f"[DOC SELECTION] ✓ Absatz confusion detected: LLM meant §{legal_ref} Abs. {number}")
                        
                        self._log_rag_error(
                            "absatz_paragraph_confusion_fixed",
                            f"Query yielded citation §{number}, corrected to {legal_ref} Abs. {number}",
                            Exception(f"Overlap: {overlap} keywords")
                        )
                        
                        return doc
        
        print("[DOC SELECTION]No clear match found, defaulting to retrieved_docs[0]")
        self._log_rag_error(
            "unclear_document_selection",
            f"Citations {all_numbers_in_answer} did not match any doc clearly",
            Exception("Using fallback to first retrieved doc")
        )
        return retrieved_docs[0]


    def _log_rag_error(self, error_type, query, exception):
        """
        Log RAG pipeline errors for debugging and thesis analysis.
        
        Args:
            error_type: Category of error (e.g., 'timeout', 'api_error')
            query: User query that triggered error
            exception: Exception object
        """
        try:
            # Log to interactions CSV if session exists
            if hasattr(st.session_state, 'session_id'):
                log_interaction(
                    session_id=st.session_state.session_id,
                    task_number=st.session_state.get('task_number', -1),
                    event_type=f"rag_error_{error_type}",
                    details=f"Query: {query[:100]} | Error: {type(exception).__name__}: {str(exception)[:200]}"
                )
            
            # Also log to dedicated error file
            with open("logs/rag_errors.log", "a", encoding='utf-8') as f:
                timestamp = datetime.now().isoformat()
                session_id = st.session_state.get('session_id', 'unknown')
                task_num = st.session_state.get('task_number', -1)
                f.write(f"{timestamp} | {session_id} | Task {task_num} | {error_type}\n")
                f.write(f"  Query: {query}\n")
                f.write(f"  Exception: {type(exception).__name__}: {str(exception)}\n")
                f.write("="*80 + "\n")
        except Exception:
            # If logging fails, print to console
            print(f"[RAG ERROR] {error_type}: {type(exception).__name__}")


    def _create_error_response(self, message, recoverable=True):
        """
        Create standardized error response structure.
        
        Args:
            message: User-facing error message
            recoverable: Whether user should try again
        
        Returns:
            Dict matching standard response structure
        """
        return {
            "answer": message,
            "context": [],
            "quote": None,
            "legal_reference": None,
            "no_answer": True,
            "error": True,
            "recoverable": recoverable
        }


    def _fix_hallucinated_citation(self, answer_text, correct_legal_ref, source_document_text):
        """
        Post-processes LLM answer to fix citation errors while preserving correct Absatz references.
        
        Fixes:
            - Hallucinated paragraph numbers (§9 → §20 if metadata says §20)
            - Absatz/Paragraph confusion (§9 → §20 Abs. 9 when LLM meant Absatz 9) [TASK 3]
            - Nummer as Absatz confusion (§9 Abs. 5 → §9 Abs. 1 Nr. 5) [TASK 4]
        
        Preserves:
            - Correct Absatz references (§20 Abs. 9 remains §20 Abs. 9)
            - Citations without Absatz (§35a remains §35a)
        
        Args:
            answer_text: Generated answer with potential citation errors
            correct_legal_ref: Correct legal reference from document metadata
            source_document_text: Full source document for Absatz matching
        
        Returns:
            Corrected answer text
        """
        # STEP 1: Extract correct paragraph number from metadata
        correct_match = re.search(r'§(\d+[a-z]?)', correct_legal_ref)
        if not correct_match:
            return answer_text  # No paragraph in metadata, can't fix
        
        correct_para = correct_match.group(1)
        
        # STEP 2: Extract existing citation from answer
        citation_pattern = r'§\s*(\d+[a-z]?)(?:\s+Abs\.\s*(\d+))?(?:\s+Satz\s*\d+)?(?:\s+Nr\.\s*\d+)?(?:\s+EStG)?'
        match = re.search(citation_pattern, answer_text)
        
        if not match:
            return answer_text  # No citation found, nothing to fix
        
        original = match.group(0)
        cited_para = match.group(1)  # Paragraph number in citation
        cited_abs = match.group(2)   # Absatz number in citation (or None)
        
        # CASE 1: Paragraph number is wrong → Check if Absatz confusion
        if cited_para != correct_para:
            print(f"[Citation Fix] Wrong paragraph: cited §{cited_para}, should be §{correct_para}")
            
            # SCENARIO 1A: Absatz/Paragraph confusion (TASK 3)
            # LLM wrote "§9" but meant "§20 Abs. 9"
            absatz_pattern = rf'\(({cited_para})\)'
            is_absatz_in_doc = re.search(absatz_pattern, source_document_text)
            
            if is_absatz_in_doc:
                fixed = f'§{correct_para} Abs. {cited_para} EStG'
                fixed_answer = answer_text.replace(original, fixed, 1)
                
                print(f"[Citation Fix] ✓ Absatz-Confusion detected: '{original}' → '{fixed}'")
                
                self._log_rag_error(
                    "citation_fixed_absatz_confusion",
                    f"LLM wrote §{cited_para} but meant §{correct_para} Abs. {cited_para}",
                    Exception(f"Found ({cited_para}) in source document")
                )
                
                return fixed_answer
            
            else:

                print(f"[Citation Fix] Unclear case - §{cited_para} not found as paragraph or Absatz")
                print(f"[Citation Fix] Skipping correction to avoid false positive")
                
                self._log_rag_error(
                    "citation_unclear_no_fix_applied",
                    f"Cited §{cited_para} in §{correct_para} doc, but no Absatz match",
                    Exception("Original citation preserved to prevent incorrect 'correction'")
                )
                
                return answer_text
        
        # CASE 2: Paragraph correct, but Nummer as Absatz confusion
        if cited_para == correct_para and cited_abs:
            try:
                abs_num = int(cited_abs)
                
                if abs_num >= 5:
                    absatz_1_pattern = r'\(1\)\s+(.*?)(?=\n\(2\)|\Z)'
                    absatz_1_match = re.search(absatz_1_pattern, source_document_text, re.DOTALL)
                    
                    if absatz_1_match:
                        absatz_1_text = absatz_1_match.group(1)
                        nummer_pattern = rf'^\s*{cited_abs}\.\s+'
                        
                        if re.search(nummer_pattern, absatz_1_text, re.MULTILINE):
                            fixed = f'§{correct_para} Abs. 1 Nr. {cited_abs} EStG'
                            fixed_answer = answer_text.replace(original, fixed, 1)
                            
                            print(f"[Citation Fix] ✓ Nummer-as-Absatz detected: '{original}' → '{fixed}'")
                            
                            self._log_rag_error(
                                "citation_fixed_nummer_as_absatz",
                                f"LLM wrote §{correct_para} Abs. {cited_abs} but meant Abs. 1 Nr. {cited_abs}",
                                Exception(f"Found '{cited_abs}.' as numbered list item in Absatz 1")
                            )
                            
                            return fixed_answer
            
            except (ValueError, AttributeError):
                pass
        
        # CASE 3: Citation already correct → no changes
        print(f"[Citation Fix] Citation correct, no changes: '{original}'")
        return answer_text



    def _fallback_quote_extraction(self, source_text, answer):
        """
        Heuristic extraction when LLM fails.
        Priority: numbers > answer keywords > first sentence
        """
        sentences = re.split(r'(?<=[.!?])\s+', source_text)
        
        # Strategy 1: Find sentences with numbers
        for sentence in sentences:
            if re.search(r'\d+\s*(?:€|Euro|Prozent|\d{3,})', sentence):
                if len(sentence) > 50:
                    return sentence.strip()
        
        # Strategy 2: Find sentences with answer keywords
        answer_keywords = set(re.findall(r'\b\w{5,}\b', answer.lower()))
        scored = []
        for sentence in sentences:
            sent_keywords = set(re.findall(r'\b\w{5,}\b', sentence.lower()))
            overlap = len(answer_keywords & sent_keywords)
            if overlap > 0 and len(sentence) > 50:
                scored.append((overlap, sentence))
        
        if scored:
            scored.sort(reverse=True, key=lambda x: x[0])
            return scored[0][1].strip()
        
        # Strategy 3: First substantial sentence
        for sentence in sentences:
            if len(sentence) > 50:
                return sentence.strip()
        
        return ""


    def _log_quote_extraction_error(self, query, task_number, tier_used):
        """Log quote extraction fallback for thesis transparency."""
        try:
            if hasattr(st.session_state, 'session_id'):
                log_interaction(
                    session_id=st.session_state.session_id,
                    task_number=task_number or -1,
                    event_type=f"quote_fallback_{tier_used}",
                    details=f"Query: {query[:80]}"
                )
        except Exception:
            pass  # Silent fail if logging impossible
