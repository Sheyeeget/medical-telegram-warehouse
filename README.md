# 🏥 Medical Telegram Data Warehouse

**Kara Solutions - Week 8 Challenge**

An end-to-end ELT pipeline that scrapes Ethiopian medical Telegram channels, transforms data using dbt (Star Schema), enriches images via YOLOv8, and serves insights via a FastAPI orchestrated by Dagster.

## 🏗️ Architecture
`Telegram API` → `Data Lake (JSON/Images)` → `PostgreSQL (Staging)` → `dbt (Marts)` → `FastAPI` 
                                                                          ↳ `YOLOv8 (Enrichment)`

## 🚀 Quick Start
1. Copy `.env.example` to `.env` and fill in your Telegram API credentials.
2. Run `docker-compose up -d` to spin up PostgreSQL.
3. Install Python deps: `pip install -r requirements.txt`
4. Run the scraper: `python src/scraper.py`
5. Run dbt: `cd medical_warehouse && dbt run`
6. Launch API: `uvicorn api.main:app --reload`

## 📂 Project Structure
(Insert the tree from the document here)

## ✅ Current Status
- [ ] Task 1: Scraping & Data Lake
- [ ] Task 2: dbt Modeling & Star Schema
- [ ] Task 3: YOLO Enrichment
- [ ] Task 4: Analytical API
- [ ] Task 5: Dagster Orchestration