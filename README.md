# Milk Booth Management System

A comprehensive milk collection and sales management system for dairy businesses.

## Features
- 📊 **Dashboard**: Real-time statistics and overview
- 🥛 **Milk Collection**: Record collections from suppliers
- ⚡ **Quick Add**: Fast collection entry
- 💰 **Sales Management**: Record sales to customers
- 👥 **Supplier & Customer Management**
- 📅 **Daily & Monthly Reports**
- 📈 **Financial Reports**
- 📁 **CSV Export**


## Quick Start

```bash
# 1. Clone repository
git clone <repository-url>
cd milkbooth_server

# 2. Set up virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initialize database
python3 -c "from app import app, db, create_default_admin; with app.app_context(): db.create_all(); create_default_admin()"

# 5. Run application
python3 app.py
```

## Kubernetes Deployment

The application is now containerized and can be deployed to Kubernetes.

1. Build the Docker image:

```bash
docker build -t milkbooth:latest .
```

2. Apply the Kubernetes resources from the `k8s/` folder:

```bash
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/app-deployment.yaml
kubectl apply -f k8s/app-service.yaml
```

3. Expose or port-forward the service:

```bash
kubectl port-forward svc/milkbooth 8080:80
```

Then open `http://localhost:8080` in your browser.

### Notes

- The app reads `DATABASE_URL` from `k8s/secret.yaml`.
- The folder now contains separate resource files for secrets, PostgreSQL PVC, PostgreSQL deployment, PostgreSQL service, app deployment, and app service.
- Update `k8s/secret.yaml` to replace `SECRET_KEY` and database credentials before production.
