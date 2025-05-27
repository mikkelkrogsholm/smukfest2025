# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# --- START Locale Configuration ---
# Install locales package
RUN apt-get update && apt-get install -y --no-install-recommends locales

# Uncomment/add the da_DK.UTF-8 locale to /etc/locale.gen
RUN sed -i '/^# da_DK.UTF-8/s/^# //' /etc/locale.gen && \
    locale-gen

# Set locale environment variables
ENV LANG da_DK.UTF-8  
ENV LANGUAGE da_DK:da
ENV LC_ALL da_DK.UTF-8  
# --- END Locale Configuration ---

# Copy the requirements file into the container at /app
COPY requirements.txt requirements.txt

# Install any needed packages specified in requirements.txt
# We use --no-cache-dir to keep the image size down
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt


# Copy the rest of the application code into the container at /app
# COPY ./app /app/       # Commented out - Rely on volume mounts for dev/setup
# COPY ./scripts /app/scripts/ # Commented out - Rely on volume mounts for dev/setup

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variables (optional, can also be passed during run)
# ENV NAME=World

# Start command with hot-reloading for development
# Note: The host 0.0.0.0 makes it accessible from outside the container
# Use --reload-dir to specify which directories to watch (avoids reload on script changes)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "app",  "--proxy-headers", "--forwarded-allow-ips=*"]
# For production, you might remove --reload and use multiple workers:
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"] 