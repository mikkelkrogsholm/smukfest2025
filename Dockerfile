# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt requirements.txt

# Install any needed packages specified in requirements.txt
# We use --no-cache-dir to keep the image size down
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt


# Copy the rest of the application code into the container at /app
# COPY ./app /app/app # Comment out for dev volume mount
# COPY ./scripts /app/scripts # Comment out for dev volume mount

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variables (optional, can also be passed during run)
# ENV NAME=World

# Run uvicorn when the container launches
# Use 0.0.0.0 to bind to all network interfaces within the container
# The --reload flag is typically NOT used in production images, 
# but can be useful during development if you mount your code as a volume.
# For a production image, remove --reload.
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 
# If you need reload during development with volume mounts, use this instead:
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"] 