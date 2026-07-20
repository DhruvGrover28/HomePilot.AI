1. Start backend server and confirm health endpoint returns status ok.
2. Upload sample_bank_statement.csv to POST /api/expenses/upload.
3. Verify response includes upload_id, categorized transactions, and anomalies_count.
4. Confirm at least one anomaly appears (duplicate or unusually large).
5. Open SQLite file and verify inserted rows in transactions table.
