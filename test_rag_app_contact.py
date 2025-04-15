#!/usr/bin/env python3
"""
PDN Analysis RAG Application

This script implements a Retrieval-Augmented Generation (RAG) application
for Personal Development Navigator (PDN) analysis.
"""

import os
import time
from typing import Dict, List, Optional, Any
import re

# LangChain imports
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Load OpenAI API key from environment variable
# You need to set this before running: export OPENAI_API_KEY=your_key_here
os.environ.setdefault("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))


class PdnAnalysisRAG:
    """RAG system for PDN (Personal Development Navigator) analysis."""
    
    def __init__(self, knowledge_path: str = "rag/pdn_knowledge.txt"):
        """Initialize the RAG system with PDN knowledge base."""
        print("\n[INIT] Initializing PDN Analysis RAG system...")
        self.pdn_knowledge_path = knowledge_path
        
        self.setup_vector_store()
        self.setup_llm()
        self.setup_pdn_chain()
        print("[INIT] PDN Analysis RAG system initialization complete")
    
    def load_and_chunk_pdn_knowledge(self) -> List[Document]:
        """Loads PDN knowledge from file and splits it into documents."""
        print(f"[DATA] Loading PDN knowledge from: {self.pdn_knowledge_path}")
        try:
            with open(self.pdn_knowledge_path, 'r', encoding='utf-8') as f:
                pdn_text = f.read()
            print(f"[DATA] Loaded {len(pdn_text)} characters from PDN knowledge file.")

            # Using LangChain splitter for more sophisticated chunking
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,  # Adjust chunk size as needed
                chunk_overlap=100,  # Adjust overlap as needed
                separators=["\n\n", "\n", "## ", "# ", ". ", " ", ""]  # Prioritize meaningful breaks
            )
            chunks = text_splitter.split_text(pdn_text)

            print(f"[DATA] Split PDN knowledge into {len(chunks)} chunks.")

            documents = []
            for i, chunk in enumerate(chunks):
                # Add simple metadata
                metadata = {"source": "PDN Knowledge Base", "chunk_id": i}
                documents.append(Document(page_content=chunk, metadata=metadata))

            print(f"[DATA] Created {len(documents)} documents for vector store.")
            return documents
        except FileNotFoundError:
            print(f"[ERROR] PDN knowledge file not found at: {self.pdn_knowledge_path}")
            return []
        except Exception as e:
            print(f"[ERROR] Failed to load or chunk PDN knowledge: {e}")
            return []

    def setup_vector_store(self):
        """Set up the vector store for PDN knowledge retrieval."""
        print("[STEP 1] Setting up vector store for PDN knowledge...")

        # Load and chunk PDN data
        print("[STEP 1.1] Loading and chunking PDN documents...")
        pdn_documents = self.load_and_chunk_pdn_knowledge()

        if not pdn_documents:
            print("[ERROR] No PDN documents loaded. Cannot set up vector store. Exiting.")
            exit()  # Or raise an exception

        # Create vector store with embeddings
        print("[STEP 1.2] Initializing OpenAI embeddings...")
        embeddings = OpenAIEmbeddings()

        print("[STEP 1.3] Creating FAISS vector store from PDN documents...")
        vector_store_start_time = time.time()
        self.vector_store = FAISS.from_documents(pdn_documents, embeddings)
        vector_store_duration = time.time() - vector_store_start_time
        print(f"[STEP 1.3] FAISS vector store created in {vector_store_duration:.3f} seconds")

        # Set up retriever with increased k for richer context
        print("[STEP 1.4] Setting up retriever with k=4...")
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 4})

        print("[STEP 1] Vector store setup complete")

    def setup_llm(self):
        """Set up the LLM for PDN analysis."""
        print("[STEP 2] Setting up LLM (gpt-4) for PDN Analysis...")
        self.llm = ChatOpenAI(model="gpt-4", temperature=0.3)  # Lower temperature for more focused output
        print("[STEP 2] LLM setup complete")

    def format_docs(self, docs: List[Document]) -> str:
        """Helper function to format retrieved documents into a single string."""
        return "\n\n".join(f"--- Document {i+1} ---\n{doc.page_content}" for i, doc in enumerate(docs))

    def setup_pdn_chain(self):
        """Set up the RAG chain for performing PDN analysis."""
        print("[STEP 3] Setting up RAG chain for PDN Analysis...")

        # Create the new prompt template for PDN analysis
        print("[STEP 3.1] Creating prompt template for PDN analysis...")
        # Read prompt template from file
        with open("prompts/pdn_diagnostic.txt", "r") as f:
            template = f.read()

        self.prompt = ChatPromptTemplate.from_template(template)
        print("[STEP 3.1] PDN analysis prompt template created")

        # Create the RAG chain using LCEL
        print("[STEP 3.2] Building PDN analysis RAG chain...")
        self.rag_chain = (
            {
                "context": self.retriever | RunnableLambda(self.format_docs),  # Use retriever and format docs
                "tester_answer": RunnablePassthrough()  # Pass the input directly
            }
            | self.prompt
            | self.llm
            | StrOutputParser()
        )
        print("[STEP 3] PDN analysis RAG chain setup complete")

    def analyze_pdn(self, tester_answer: str) -> str:
        """Analyzes the tester's answer using the PDN RAG chain."""
        print(f"\n[ANALYZE] Starting PDN analysis for the provided text...")
        analysis_start_time = time.time()

        try:
            # Invoke the RAG chain with the tester's answer
            # The chain internally handles retrieval based on this input
            report = self.rag_chain.invoke(tester_answer)

            analysis_duration = time.time() - analysis_start_time
            print(f"[ANALYZE] PDN analysis completed in {analysis_duration:.3f} seconds")
            return report

        except Exception as e:
            print(f"[ERROR] Error during PDN analysis: {str(e)}")
            analysis_duration = time.time() - analysis_start_time
            print(f"[ANALYZE] Analysis failed after {analysis_duration:.3f} seconds")
            return f"Error during analysis: {e}\n\nPlease ensure your OpenAI API key is valid and the PDN knowledge file is accessible."

    def generate_report(self, tester_answer: str) -> Dict:
        """Generates a PDN analysis report for the given text."""
        print(f"\n[PROCESS] Generating PDN report...")
        process_start_time = time.time()
        result: Dict[str, Any] = {"report": None, "timing": {}}  # Initialize result dict

        # Perform analysis
        report_text = self.analyze_pdn(tester_answer)
        analysis_duration = time.time() - process_start_time  # Calculate total time

        result["report"] = report_text
        result["timing"]["analysis_time"] = analysis_duration

        print(f"[PROCESS] Report generation complete in {analysis_duration:.3f} seconds")
        return result


def main():
    """Main function to run the PDN Analysis RAG application."""
    # Print welcome message
    print("\n===== PDN Analysis RAG Application =====")
    print("This app performs a preliminary PDN analysis based on your text input,")
    print("using a PDN knowledge base and RAG.")

    # Check if OPENAI_API_KEY is set
    if not os.getenv("OPENAI_API_KEY"):
        print("\nError: OPENAI_API_KEY environment variable is not set.")
        print("Please set it using: export OPENAI_API_KEY='your_key_here'")
        return

    # Ensure rag directory exists
    if not os.path.exists("rag"):
        print("\nError: 'rag' directory not found. Please create it and place 'pdn_knowledge.txt' inside.")
        return
    if not os.path.exists("rag/pdn_knowledge.txt"):
        print("\nError: 'rag/pdn_knowledge.txt' file not found. Please create this file with the PDN knowledge.")
        return

    # Initialize the RAG system
    print("\n[MAIN] Starting PDN RAG system initialization...")
    init_start_time = time.time()
    rag_system = PdnAnalysisRAG()  # Uses default knowledge path
    init_duration = time.time() - init_start_time
    print(f"[MAIN] PDN RAG system ready! (Initialization took {init_duration:.3f} seconds)\n")

    # Enter main loop
    while True:
        try:
            # Get user input
            print("\n" + "-" * 50)
            # Use input() for potentially long text, consider alternatives for very long inputs
            print("Enter text for PDN analysis (type 'q' to quit). You can paste multiple lines. Press Enter twice when done:")

            lines = []
            while True:
                line = input()
                if line:
                    lines.append(line)
                else:
                    break  # Exit loop on empty line (double enter)
            query = "\n".join(lines).strip()

            # Check if user wants to quit
            if query.lower() in ['q', 'quit', 'exit']:
                print("\n[MAIN] Shutting down the PDN Analysis Application")
                print("Thank you!")
                break

            if not query:
                print("[MAIN] No input received. Please enter some text or 'q'.")
                continue

            # Process the query
            print(f"[MAIN] Starting PDN analysis for the provided text...")
            start_time = time.time()
            result = rag_system.generate_report(query)  

            # Display results
            print("\n" + "=" * 10 + " PDN Analysis Report " + "=" * 10)
            if result["report"]:
                print(result["report"])
            else:
                print("[RESULT] Failed to generate report.")

            # Print processing time
            processing_time = time.time() - start_time  # Use overall time
            timing = result.get("timing", {})
            print("\n" + "-" * 50)
            print(f"[STATS] Timing Information:")
            print(f"  Analysis time: {timing.get('analysis_time', 0):.3f} seconds")
            print(f"  Total request time: {processing_time:.3f} seconds")
            print("-" * 50)

        except KeyboardInterrupt:
            print("\n[MAIN] Program interrupted. Exiting...")
            break
        except Exception as e:
            import traceback
            print(f"\n[ERROR] An unexpected error occurred: {str(e)}")
            print("Traceback:")
            traceback.print_exc()


if __name__ == "__main__":
    # Remember to create the rag directory and the pdn_knowledge.txt file
    # Example: mkdir rag && touch rag/pdn_knowledge.txt
    # Then paste the PDN content into rag/pdn_knowledge.txt
    main() 