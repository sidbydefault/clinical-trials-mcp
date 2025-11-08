"""
Example setup script for loading demo data into the database and vector store.

This script demonstrates how to:
1. Initialize the database with schema
2. Load patient and condition data from Parquet files
3. Load clinical trial data
4. Generate and store vector embeddings
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
from database import DatabaseManager
from vectorstore import VectorStoreManager
from config import get_settings


def main():
    """Run the example setup."""
    settings = get_settings()

    print("🏥 Clinical Trials MCP - Setup Example")
    print("=" * 50)

    # Initialize managers
    print("\n1. Initializing database...")
    db_manager = DatabaseManager(settings.database_url)
    db_manager.create_tables()
    print("✓ Database initialized")

    print("\n2. Initializing vector store...")
    vector_manager = VectorStoreManager(
        persist_directory=settings.vector_store_path,
        embedding_model=settings.embedding_model
    )
    print("✓ Vector store initialized")

    # Load sample data
    examples_dir = Path(__file__).parent / "sample_data"

    if not examples_dir.exists():
        print(f"\n⚠ Sample data directory not found: {examples_dir}")
        print("Please ensure sample data files are present:")
        print("  - patients_demo.parquet")
        print("  - conditions_demo.parquet")
        print("  - trials_demo.parquet")
        return

    # Load patients
    print("\n3. Loading patient data...")
    patients_file = examples_dir / "patients_demo.parquet"
    if patients_file.exists():
        patients_df = pd.read_parquet(patients_file)
        db_manager.load_patients(patients_df)
        print(f"✓ Loaded {len(patients_df)} patients")
    else:
        print(f"⚠ Patients file not found: {patients_file}")

    # Load conditions
    print("\n4. Loading condition data...")
    conditions_file = examples_dir / "conditions_demo.parquet"
    if conditions_file.exists():
        conditions_df = pd.read_parquet(conditions_file)
        db_manager.load_conditions(conditions_df)
        print(f"✓ Loaded {len(conditions_df)} conditions")
    else:
        print(f"⚠ Conditions file not found: {conditions_file}")

    # Load clinical trials
    print("\n5. Loading clinical trials data...")
    trials_file = examples_dir / "trials_demo.parquet"
    if trials_file.exists():
        trials_df = pd.read_parquet(trials_file)
        db_manager.load_trials(trials_df)
        print(f"✓ Loaded {len(trials_df)} clinical trials")

        # Generate embeddings
        print("\n6. Generating trial embeddings...")
        vector_manager.index_trials(trials_df)
        print("✓ Embeddings generated and stored")
    else:
        print(f"⚠ Trials file not found: {trials_file}")

    print("\n" + "=" * 50)
    print("✓ Setup complete!")
    print(f"\nDatabase: {settings.database_url}")
    print(f"Vector store: {settings.vector_store_path}")
    print("\nRun the server with: make run")


if __name__ == "__main__":
    main()
