Start pods running: `docker compose up -d`
Shut down pods: `docker compose down`

Live logs of API: `docker logs -f post-secret-archive-flask-app-1`

Querying the database: `docker exec -it post-secret-archive-postgres-1 psql -U mvp_user -d image_text_mvp`
    \l list databases
    \c to connect to database
    \dt to list the tables
    SELECT * FROM table_name; to query a table