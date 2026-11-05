FROM postgres:16-alpine

# Label metadata
LABEL maintainer="Vocara Engineering Team"
LABEL description="Vocara Production PostgreSQL Database with Persistent Storage"

# Copy custom database initialization scripts
COPY init.sql /docker-entrypoint-initdb.d/init.sql

# Expose default PostgreSQL port
EXPOSE 5432

# Declare volume mount point for persistent data storage
VOLUME ["/var/lib/postgresql/data"]

