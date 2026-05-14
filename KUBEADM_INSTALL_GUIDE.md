# kubeadm Installation Guide for Ubuntu 24.04 - Step by Step

Follow these commands exactly on your Ubuntu instance. Copy-paste each section in order.

## Step 1: Update System

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

## Step 2: Install Docker

```bash
sudo apt-get install -y docker.io

# Add your user to docker group
sudo usermod -aG docker $USER

# Verify Docker installation
docker --version
```

Note: You may need to log out and log back in for docker group changes to take effect. Or run:
```bash
newgrp docker
```

## Step 3: Disable Swap (Required for Kubernetes)

```bash
sudo swapoff -a

# Permanently disable swap
sudo sed -i '/ swap / s/^/#/' /etc/fstab

# Verify swap is off
free -h
```

## Step 4: Configure Kernel Parameters

```bash
cat <<EOF | sudo tee /etc/modules-load.d/containerd.conf
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter

cat <<EOF | sudo tee /etc/sysctl.d/99-kubernetes-cri.conf
net.bridge.bridge-nf-call-iptables  = 1
net.ipv4.ip_forward                 = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF

sudo sysctl --system
```

## Step 5: Install kubeadm, kubelet, kubectl

```bash
sudo apt-get update

# Add Kubernetes GPG key
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

# Add Kubernetes repository
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list

# Install kubeadm, kubelet, kubectl
sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl

# Prevent auto-updates of these packages
sudo apt-mark hold kubelet kubeadm kubectl
```

## Step 6: Initialize Kubernetes Cluster

```bash
sudo kubeadm init --pod-network-cidr=10.244.0.0/16
```

**IMPORTANT:** Save the output! You'll see a `kubeadm join` command at the end. Save it if you need to add more nodes later.

## Step 7: Configure kubectl Access

```bash
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

Verify it works:
```bash
kubectl cluster-info
kubectl get nodes
```

## Step 8: Install Network Plugin (Flannel)

```bash
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml
```

Wait for Flannel pods to be ready:
```bash
kubectl get pods -n kube-flannel -w
```

Press `Ctrl+C` once all pods show "Running".

## Step 9: Verify Cluster

```bash
# Check all nodes are ready
kubectl get nodes

# Check system pods
kubectl get pods -n kube-system
```

Expected output: Node should show **STATUS: Ready**

---

## Step 10: Load Your Docker Image

From your project directory on the server:

```bash
cd /path/to/jkmilkbooth

# Build the Docker image
docker build -t milkbooth:latest .
```

## Step 11: Deploy Your Application

Copy your `k8s/` folder to the server, then:

```bash
# Update credentials in the secret first (IMPORTANT!)
# Edit k8s/secret.yaml and change:
#   - SECRET_KEY: use a strong random key
#   - DATABASE_URL: use strong password
#   - POSTGRES_PASSWORD: use strong password

nano k8s/secret.yaml  # Edit the credentials

# Deploy resources in order
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/app-deployment.yaml
kubectl apply -f k8s/app-service.yaml
```

## Step 12: Verify Deployment

```bash
# Check all pods
kubectl get pods

# Check services
kubectl get svc

# Check logs
kubectl logs -l app=milkbooth
kubectl logs -l app=milkbooth-postgres
```

Expected: All pods should show **STATUS: Running**

## Step 13: Access Your Application

```bash
kubectl port-forward svc/milkbooth 8080:80
```

Then visit: `http://<your-instance-ip>:8080`

Or if accessing from same machine: `http://localhost:8080`

---

## Troubleshooting

### Check pod status
```bash
kubectl describe pod <pod-name>
```

### View pod logs
```bash
kubectl logs <pod-name>
kubectl logs <pod-name> -f  # Follow logs
```

### If database connection fails
```bash
kubectl exec -it <postgres-pod-name> -- psql -U milkuser -d milkbooth
```

### View cluster events
```bash
kubectl get events --sort-by='.lastTimestamp'
```

### Remove everything and start fresh
```bash
kubectl delete -f k8s/
```

---

## Resource Limits (For Your Small VM)

Edit `k8s/app-deployment.yaml` and add under `containers:` → after `env:`:

```yaml
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

Edit `k8s/postgres-deployment.yaml` similarly:

```yaml
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

This prevents pods from consuming all available memory on your 1.9GB instance.

---

## Done! 🎉

Your Milk Booth app is now running on Kubernetes. It will auto-restart if pods crash, and persist data in PostgreSQL.
