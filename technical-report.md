# Technical Report

## 1. Questions Asked
This project focused on understanding character-building behavior in DnD profile data.

1. Which character roles are most popular?
2. Which races are most popular?
3. How common is multiclassing?
4. How many characters reach level 20?
5. Which stats are most often maximized?
6. Which stats are most often used as dump stats?
7. Does note length vary by class?
8. What is the most common subclass within each class?

## 2. Datasets Used
I used exported character profile data and loaded it into PostgreSQL for analysis.

1. Primary dataset:
Character-level data (race, level, stats, notes length, etc.)
2. Derived tables:
Character table, class table, and feats table
3. SQL reporting views:
Views for class/race popularity, multiclass count, level 20 count, stat trends, and subclass summaries

## 3. ETL Process
The ETL pipeline was implemented in Python and orchestrated with Airflow.

1. Extract:
Read source character data into pandas dataframes
2. Transform:
Removed unusable rows, cleaned inconsistent values, standardized fields, and prepared class/feat relationships
3. Load:
Inserted cleaned data into PostgreSQL tables in the characters schema
4. Reporting layer:
Created SQL views for dashboard-friendly metrics

## 4. Technologies Used
1. Python:
Data processing and ETL logic (pandas, psycopg, SQLAlchemy, Dynaconf)
2. PostgreSQL:
Storage, joins, aggregations, and analytics views
3. Airflow:
Pipeline orchestration (schema + views + ETL)
4. Dash/Plotly:
Interactive dashboard for presenting results

## 5. ML Used (Optional)
No machine learning was used in this project.

## 6. Conclusions
1. Character choices were concentrated around a smaller set of popular classes and races.
2. Most profiles did not reach level 20.
3. Multiclassing was present but not dominant across all classes.
4. Stat trends showed repeatable optimization patterns (maxed stats and dump stats).
5. Notes behavior varied by class, showing differences in how users document builds.

## 7. Limitations
1. This analysis is descriptive and does not prove cause.
2. Some classes/races have small sample sizes and can skew percentages.
3. Data quality depends on source profile completeness and consistency.
4. Results reflect this dataset snapshot, not all possible players.

## 8. Next Steps
1. Add time-based analysis to track changes in behavior over updates.
2. Add user segments (for example by level bands or build complexity).
3. Expand validation checks for edge cases and category standardization.
4. Add more dashboard drill-downs for class/race combinations.

## 9. Deliverables
1. PostgreSQL schema and ETL-loaded tables.
2. SQL view layer for reporting and dashboard consumption.
3. Airflow DAG for orchestrated schema, view creation, and ETL flow.
4. Dash dashboard for interactive exploration of results.

## 10. Final Summary
This project turns raw character profile data into a repeatable analytics workflow.
Using Python ETL, PostgreSQL, Airflow, and Dash, it produces clear reporting on profile-building behavior and supports future analysis with minimal rework.
