# Shell Scripts for Kubernetes Setup

This folder contains automated shell scripts to set up Kubernetes and deploy your Milk Booth application.

## Files

1. **install-kubernetes.sh** — Installs kubeadm, kubectl, kubelet, and initializes the cluster
2. **deploy-app.sh** — Builds Docker image and deploys the app to Kubernetes

## Quick Start

### Step 1: Copy scripts to your Ubuntu server

```bash
scp install-kubernetes.sh ubuntu@<your-ip>:/tmp/
scp deploy-app.sh ubuntu@<your-ip>:/tmp/
scp -r k8s/ ubuntu@<your-ip>:/tmp/jkmilkbooth/
```

Or clone the entire repository:
```bash
git clone <repo-url> /tmp/jkmilkbooth
cd /tmp/jkmilkbooth
```

### Step 2: Run Kubernetes Installation

```bash
sudo bash install-kubernetes.sh
```

This script will:
- ✓ Update system
- ✓ Install Docker
- ✓ Install kubeadm, kubelet, kubectl
- ✓ Initialize Kubernetes cluster
- ✓ Install Flannel network plugin
- ✓ Wait for cluster to be ready

**Time:** ~10-15 minutes

### Step 3: Verify Kubernetes is Working

```bash
kubectl get nodes
kubectl get pods -n kube-system
```

You should see the node in "Ready" state and system pods running.

### Step 4: Deploy Your Application

First, update credentials in `k8s/secret.yaml`:

```bash
nano k8s/secret.yaml
```

Change:
- `SECRET_KEY` — Replace with a strong random string
- `DATABASE_URL` — Change password from `milkpass` to something secure
- `POSTGRES_PASSWORD` — Change password from `milkpass` to something secure

Then run:
```bash
bash deploy-app.sh
```

This script will:
- ✓ Build Docker image
- ✓ Deploy PostgreSQL
- ✓ Deploy application
- ✓ Wait for all pods to be ready
- ✓ Show deployment status

**Time:** ~5 minutes

### Step 5: Access Your Application

```bash
kubectl port-forward svc/milkbooth 8080:80
```

Open in browser: `http://localhost:8080`

Default credentials:
- Username: `admin`
- Password: `admin123`

---

## Detailed Usage

### Run Installation Script

```bash
chmod +x install-kubernetes.sh
sudo ./install-kubernetes.sh
```

**What it does:**
1. Updates Ubuntu packages
2. Installs Docker
3. Disables swap (required by Kubernetes)
4. Configures kernel modules
5. Installs kubeadm, kubelet, kubectl v1.30
6. Initializes single-node cluster
7. Installs Flannel CNI plugin
8. Waits for cluster readiness

**Expected output:**
```
✓ System updated
✓ Docker installed
✓ Kubernetes tools installed
✓ Cluster initialized
✓ Flannel installed
✓ Cluster is ready!

Cluster Status:
NAME                STATUS   ROLES           VERSION
ip-172-31-2-61      Ready    control-plane   v1.30.x
```

### Run Deployment Script

```bash
chmod +x deploy-app.sh
./deploy-app.sh
```

**Before running:**
1. Edit `k8s/secret.yaml` with strong credentials
2. Ensure `k8s/` folder contains all YAML files

**What it does:**
1. Builds Docker image: `milkbooth:latest`
2. Deploys PostgreSQL database
3. Deploys Milk Booth application
4. Waits for all pods to be ready
5. Shows deployment status

**Expected output:**
```
Step 1: Building Docker image...
✓ Docker image built successfully

Step 2: Reviewing k8s/secret.yaml...
⚠️  IMPORTANT: Update the following...

Step 3: Deploying Kubernetes resources...
✓ Deployment completed

Pod Status: 3/3 running
✓ All pods are running!

Access Your Application:
  kubectl port-forward svc/milkbooth 8080:80
  Then open: http://localhost:8080
```

---

## Troubleshooting

### Script fails with "permission denied"

Make scripts executable:
```bash
chmod +x install-kubernetes.sh deploy-app.sh
```

### "kubectl not found" error

Run installation script first:
```bash
sudo bash install-kubernetes.sh
```

### Pods not starting

Check pod status:
```bash
kubectl get pods
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

### Database connection failed

Check PostgreSQL pod:
```bash
kubectl logs -l app=milkbooth-postgres
```

Verify database is running:
```bash
kubectl exec -it <postgres-pod-name> -- psql -U milkuser -d milkbooth
```

### Port-forward not working

Ensure service is created:
```bash
kubectl get svc
```

Then retry:
```bash
kubectl port-forward svc/milkbooth 8080:80
```

---

## Manual Deployment (Without Scripts)

If you prefer to run commands manually, follow the `KUBEADM_INSTALL_GUIDE.md` file step-by-step.

---

## Security Notes

⚠️ **Before production use:**

1. **Update credentials in `k8s/secret.yaml`**
   - Use strong, random values
   - Don't use default passwords

2. **Use a reverse proxy (Nginx/HAProxy)**
   - Don't expose directly to internet
   - Implement SSL/TLS

3. **Enable persistent backups**
   - Backup PostgreSQL data regularly
   - Store backups securely

4. **Monitor cluster health**
   ```bash
   kubectl get nodes
   kubectl top nodes
   kubectl top pods
   ```

---

## Cleanup

To remove all deployments:

```bash
kubectl delete -f k8s/
```

To remove entire cluster (WARNING: deletes everything):

```bash
sudo kubeadm reset -f
```

---

## Support

For detailed instructions, see:
- `KUBEADM_INSTALL_GUIDE.md` — Step-by-step manual installation
- `KUBERNETES_INSTALL.md` — Options and detailed info
- `README.md` — General deployment info
