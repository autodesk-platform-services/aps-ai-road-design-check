# Dokku Deployment Guide (Docker)

This guide explains how to deploy the APS Road Design Check application to Dokku using Docker.

## Prerequisites

- Dokku instance (v0.28+) with Docker support
- Git repository access
- Required API credentials (APS and OpenAI)

## Deployment Files

- **`Dockerfile`**: Defines the container with Python 3.12
- **`Procfile`**: Tells Dokku how to run the application
- **`.dockerignore`**: Excludes unnecessary files from the Docker image
- **`pyproject.toml`**: Contains all Python dependencies

## Deployment Steps

### 1. Create the Dokku App

SSH into your Dokku server or use remote commands:

```bash
ssh dokku@10.57.230.158 apps:create aps-alignment-check
```

Or if you already created it, skip this step.

### 2. Configure Environment Variables

Set the required environment variables:

```bash
ssh dokku@10.57.230.158 config:set aps-alignment-check \
  APS_CLIENT_ID="your_client_id" \
  APS_CLIENT_SECRET="your_client_secret" \
  APS_CALLBACK_URL="http://your-domain/oauth/callback" \
  OPENAI_API_KEY="your_openai_api_key" \
  SECRET_KEY="$(openssl rand -hex 32)"
```

### 3. Deploy from Git

Dokku will automatically detect the `Dockerfile` and use it instead of buildpacks:

```bash
git add Dockerfile .dockerignore Procfile pyproject.toml
git commit -m "Add Docker deployment configuration"
git push dokku main:master
```

That's it! Dokku will:
1. Detect the Dockerfile
2. Build a Docker image with Python 3.12
3. Install all dependencies from pyproject.toml
4. Run the application using gunicorn

### 4. Check Application Status

```bash
# View logs
ssh dokku@10.57.230.158 logs aps-alignment-check -t

# Check if app is running
ssh dokku@10.57.230.158 ps:report aps-alignment-check

# Restart if needed
ssh dokku@10.57.230.158 ps:restart aps-alignment-check
```

## How the Docker Deployment Works

1. **Base Image**: Uses official `python:3.12-slim` image
2. **Dependencies**: Installs from `pyproject.toml` using pip
3. **Application**: Copies all application code
4. **Runtime**: Runs gunicorn with 4 workers on the port specified by Dokku

## Docker-Specific Configuration

### Adjust Worker Count

Edit the `Dockerfile` CMD line to change workers:

```dockerfile
CMD gunicorn app:app --bind 0.0.0.0:${PORT:-5000} --workers 2 --timeout 120
```

Formula: `(2 x CPU cores) + 1`

### Configure Domain (Optional)

```bash
ssh dokku@10.57.230.158 domains:add aps-alignment-check your-domain.com
```

### Enable SSL (Recommended)

```bash
ssh dokku@10.57.230.158 letsencrypt:enable aps-alignment-check
```

### Persistent Storage (Optional)

If you need persistent uploads:

```bash
ssh dokku@10.57.230.158 storage:ensure-directory aps-alignment-check
ssh dokku@10.57.230.158 storage:mount aps-alignment-check /var/lib/dokku/data/storage/aps-alignment-check:/app/uploads
```

## Troubleshooting

### View Build Logs

```bash
ssh dokku@10.57.230.158 logs aps-alignment-check
```

### Rebuild Application

```bash
ssh dokku@10.57.230.158 ps:rebuild aps-alignment-check
```

### Check Docker Image

```bash
ssh dokku@10.57.230.158 run aps-alignment-check python --version
```

Should output: `Python 3.12.x`

### Access Container Shell

```bash
ssh dokku@10.57.230.158 enter aps-alignment-check
```

### Environment Variables

```bash
# List all environment variables
ssh dokku@10.57.230.158 config:show aps-alignment-check

# Remove a variable
ssh dokku@10.57.230.158 config:unset aps-alignment-check VARIABLE_NAME
```

## Advantages of Docker Deployment

✅ **Full Control**: Specify exact Python version (3.12)  
✅ **Consistency**: Same environment in development and production  
✅ **Reproducibility**: Build is deterministic and repeatable  
✅ **No Buildpack Issues**: Direct control over the entire stack  
✅ **Better Caching**: Docker layers cache dependencies efficiently  

## Local Testing

Test the Docker build locally before deploying:

```bash
# Build the image
docker build -t aps-road-design-check .

# Run locally
docker run -p 5000:5000 \
  -e APS_CLIENT_ID="your_client_id" \
  -e APS_CLIENT_SECRET="your_client_secret" \
  -e APS_CALLBACK_URL="http://localhost:5000/oauth/callback" \
  -e OPENAI_API_KEY="your_openai_key" \
  -e SECRET_KEY="dev-secret-key" \
  aps-road-design-check
```

Visit `http://localhost:5000` to test.

## Production Considerations

1. ✅ **Python 3.12**: Now properly installed via Docker
2. ✅ **Environment Variables**: Set via Dokku config (never commit .env)
3. ✅ **SSL/HTTPS**: Use Let's Encrypt in production
4. ✅ **Logging**: Gunicorn logs to stdout/stderr for Dokku
5. ✅ **Health Checks**: Set up proper health monitoring

## Additional Resources

- [Dokku Dockerfile Deployment](https://dokku.com/docs/deployment/builders/dockerfiles/)
- [Official Python Docker Images](https://hub.docker.com/_/python)
- [Gunicorn Configuration](https://docs.gunicorn.org/en/stable/settings.html)

