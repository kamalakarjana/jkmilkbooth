# Kubernetes Installation Guide for Ubuntu

This guide covers installing Kubernetes on Ubuntu 24.04 (AWS instance).

## Option 1: Using Minikube (Recommended for Development)

Minikube is a lightweight Kubernetes distribution ideal for local development and testing.

### Step 1: Install Docker

```bash
sudo apt-get update
sudo apt-get install -y docker.io
sudo usermod -aG docker $USER
newgrp docker
```

Verify Docker:
```bash
docker --version
```

### Step 2: Install Minikube

```bash
curl -LO https://github.com/kubernetes/minikube/releases/latest/download/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
minikube version
```

### Step 3: Install kubectl

```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
kubectl version --client
```

### Step 4: Start Minikube

```bash
minikube start
```

To use with your app's Docker image:
```bash
eval $(minikube docker-env)
docker build -t milkbooth:latest .
```

### Step 5: Deploy Application

```bash
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/app-deployment.yaml
kubectl apply -f k8s/app-service.yaml
```

### Step 6: Access Application

```bash
kubectl port-forward svc/milkbooth 8080:80
```

Then visit `http://localhost:8080`

---

## Option 2: Using kubeadm (Production-Like Setup)

For a more production-like single-node or multi-node cluster.

### Step 1: Install Docker

```bash
sudo apt-get update
sudo apt-get install -y docker.io
sudo usermod -aG docker $USER
newgrp docker
```

### Step 2: Install kubeadm, kubelet, and kubectl

```bash
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gpg

curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list

sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

### Step 3: Disable Swap

```bash
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab
```

### Step 4: Initialize Kubernetes Cluster

```bash
sudo kubeadm init --pod-network-cidr=10.244.0.0/16
```

### Step 5: Configure kubectl

```bash
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

### Step 6: Install Network Plugin (Flannel)

```bash
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml
```

Wait for all pods to be ready:
```bash
kubectl get pods -n kube-flannel
kubectl get nodes
```

### Step 7: Deploy Application

```bash
docker build -t milkbooth:latest .
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/app-deployment.yaml
kubectl apply -f k8s/app-service.yaml
```

### Step 8: Access Application

```bash
kubectl port-forward svc/milkbooth 8080:80
```

---

## Verify Deployment

```bash
# Check all pods
kubectl get pods

# Check services
kubectl get svc

# Check deployments
kubectl get deployments

# Check logs
kubectl logs -l app=milkbooth
kubectl logs -l app=milkbooth-postgres
```

## Troubleshooting

If pods are not running:
```bash
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

For database connection issues:
```bash
kubectl exec -it <postgres-pod-name> -- psql -U milkuser -d milkbooth
```

## Clean Up

To remove all resources:
```bash
kubectl delete -f k8s/
```

To stop Minikube:
```bash
minikube stop
```
