1. Start backend and frontend and confirm the health endpoint returns status ok.
2. Confirm an empty database returns empty dashboard arrays and zero open tasks.
3. Click "Seed simulated demo" and verify electricity/water charts, five appliances and simulated labels.
4. Upload a valid readings CSV to `POST /api/readings/import` and verify the imported count.
5. Upload a malformed readings CSV and verify HTTP 422 with row numbers and no partial inserts.
6. Exercise create/update/delete for readings, appliances, inventory, shopping-list items and tasks.
