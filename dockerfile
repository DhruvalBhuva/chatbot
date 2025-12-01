# Use a lean official Python image as the base
FROM python:3.11-slim

# Set environment variables to prevent Python from writing .pyc files 
# and ensure output is sent immediately (good for logs)
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PATH="/root/.local/bin:${PATH}"

# Set the working directory   the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker's build cache.
# If requirements.txt doesn't change, this layer won't be rebuilt.
COPY requirements.txt /app/

# Install dependencies. Use --no-cache-dir for a smaller image.
# We also install aiosqlite dependencies (needed for the AsyncSqliteSaver)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire application source code
# Note: Copying the whole directory structure from the root of your project
COPY backend /app/backend
COPY frontend /app/frontend

# Create the data directory for the SQLite database
# The database file (chatbot.db) will be created inside this directory by the app
RUN mkdir -p database

# Expose the default port for Streamlit applications
EXPOSE 8501

# The command to run the application when the container starts.
# We explicitly set the host to 0.0.0.0 so it's accessible externally in Docker.
CMD ["streamlit", "run", "frontend/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]