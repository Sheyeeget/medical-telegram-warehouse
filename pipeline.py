import os
import sys
import subprocess
from dagster import graph, op, job, get_dagster_logger

project_root = os.path.dirname(os.path.abspath(__file__))

@op
def scrape_telegram_data():
    """Run the Telegram scraper."""
    logger = get_dagster_logger()
    logger.info("Starting Telegram scraper...")
    
    result = subprocess.run(
        [sys.executable, "src/scraper.py"],
        capture_output=True,
        text=True,
        cwd=project_root
    )
    
    if result.returncode != 0:
        logger.error(f"Scraper failed: {result.stderr}")
        raise Exception("Scraper failed")
    
    logger.info("Scraper completed")
    return "scrape_done"

@op
def load_raw_to_postgres(scrape_result):
    """Load raw JSON data to PostgreSQL."""
    logger = get_dagster_logger()
    logger.info(f"Loading data... (scrape: {scrape_result})")
    
    result = subprocess.run(
        [sys.executable, "src/load_raw_to_postgres.py"],
        capture_output=True,
        text=True,
        cwd=project_root
    )
    
    if result.returncode != 0:
        logger.error(f"Load failed: {result.stderr}")
        raise Exception("Load failed")
    
    logger.info("Data loaded")
    return "load_done"

@op
def run_dbt_transformations(load_result):
    """Run dbt models."""
    logger = get_dagster_logger()
    logger.info(f"Running dbt... (load: {load_result})")
    
    dbt_dir = os.path.join(project_root, "medical_warehouse")
    result = subprocess.run(
        ["dbt", "run"],
        capture_output=True,
        text=True,
        cwd=dbt_dir
    )
    
    if result.returncode != 0:
        logger.error(f"dbt failed: {result.stderr}")
        raise Exception("dbt failed")
    
    logger.info("dbt completed")
    return "dbt_done"

@op
def run_yolo_enrichment(dbt_result):
    """Run YOLO object detection."""
    logger = get_dagster_logger()
    logger.info(f"Running YOLO... (dbt: {dbt_result})")
    
    result = subprocess.run(
        [sys.executable, "src/yolo_load.py"],
        capture_output=True,
        text=True,
        cwd=project_root
    )
    
    if result.returncode != 0:
        logger.error(f"YOLO failed: {result.stderr}")
        raise Exception("YOLO failed")
    
    logger.info("YOLO completed")
    return "yolo_done"

@graph
def medical_telegram_graph():
    """Define the pipeline graph with dependencies."""
    scrape = scrape_telegram_data()
    load = load_raw_to_postgres(scrape)
    dbt = run_dbt_transformations(load)
    yolo = run_yolo_enrichment(dbt)
    return yolo

# Create a job from the graph
medical_telegram_pipeline = medical_telegram_graph.to_job()
