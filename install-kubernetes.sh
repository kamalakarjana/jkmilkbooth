#!/bin/bash

# Kubernetes Setup Script for Ubuntu 24.04
# This script automates the installation of kubeadm, kubelet, and kubectl

set -e  # Exit on any error

echo "=========================================="
echo "Kubernetes (kubeadm) Installation Script"
echo "=========================================="
echo ""

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root or with sudo"
   exit 1
fi

# Step 1: Update System
echo "Step 1: Updating system..."
apt-get update
apt-get upgrade -y
echo "✓ System updated"
echo ""

# Step 2: Install Docker
echo "Step 2: Installing Docker..."
apt-get install -y docker.io
echo "✓ Docker installed"
echo ""

# Step 3: Add user to docker group
echo "Step 3: Adding user to docker group..."
SUDO_USER=${SUDO_USER:-ubuntu}
usermod -aG docker $SUDO_USER
echo "✓ User added to docker group"
echo ""

# Step 4: Disable Swap
echo "Step 4: Disabling swap..."
swapoff -a
sed -i '/ swap / s/^/#/' /etc/fstab
echo "✓ Swap disabled"
echo ""

# Step 5: Configure Kernel Parameters
echo "Step 5: Configuring kernel parameters..."

cat <<EOF > /etc/modules-load.d/containerd.conf
overlay
br_netfilter
EOF

modprobe overlay
modprobe br_netfilter

cat <<EOF > /etc/sysctl.d/99-kubernetes-cri.conf
net.bridge.bridge-nf-call-iptables  = 1
net.ipv4.ip_forward                 = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF

sysctl --system > /dev/null 2>&1
echo "✓ Kernel parameters configured"
echo ""

# Step 6: Install Kubernetes Tools
echo "Step 6: Installing kubeadm, kubelet, kubectl..."

apt-get update

# Add GPG key
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

# Add repository
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' > /etc/apt/sources.list.d/kubernetes.list

apt-get update
apt-get install -y kubelet kubeadm kubectl
apt-mark hold kubelet kubeadm kubectl

echo "✓ Kubernetes tools installed"
echo ""

# Step 7: Initialize Cluster
echo "Step 7: Initializing Kubernetes cluster..."
kubeadm init --pod-network-cidr=10.244.0.0/16 > /tmp/kubeadm-init.log 2>&1

if [ $? -eq 0 ]; then
    echo "✓ Cluster initialized"
    echo ""
    echo "=========================================="
    echo "IMPORTANT: Save this join command if adding nodes:"
    echo "=========================================="
    grep -A 2 "kubeadm join" /tmp/kubeadm-init.log || true
    echo ""
else
    echo "✗ Cluster initialization failed"
    cat /tmp/kubeadm-init.log
    exit 1
fi

# Step 8: Configure kubectl
echo "Step 8: Configuring kubectl..."
mkdir -p /home/$SUDO_USER/.kube
cp -i /etc/kubernetes/admin.conf /home/$SUDO_USER/.kube/config
chown $SUDO_USER:$SUDO_USER /home/$SUDO_USER/.kube/config
echo "✓ kubectl configured"
echo ""

# Step 9: Install Flannel
echo "Step 9: Installing Flannel network plugin..."
sudo -u $SUDO_USER kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml > /dev/null 2>&1
echo "✓ Flannel installed"
echo ""

# Step 10: Wait for nodes to be ready
echo "Step 10: Waiting for cluster to be ready..."
echo "This may take 2-3 minutes..."
for i in {1..60}; do
    if sudo -u $SUDO_USER kubectl get nodes 2>/dev/null | grep -q "Ready"; then
        echo "✓ Cluster is ready!"
        break
    fi
    echo -n "."
    sleep 5
done
echo ""
echo ""

# Final Status
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Cluster Status:"
sudo -u $SUDO_USER kubectl get nodes
echo ""
echo "System Pods:"
sudo -u $SUDO_USER kubectl get pods -n kube-system
echo ""
echo "Next Steps:"
echo "1. Deploy your application:"
echo "   cd /path/to/jkmilkbooth"
echo "   kubectl apply -f k8s/secret.yaml"
echo "   kubectl apply -f k8s/postgres-pvc.yaml"
echo "   kubectl apply -f k8s/postgres-deployment.yaml"
echo "   kubectl apply -f k8s/postgres-service.yaml"
echo "   kubectl apply -f k8s/app-deployment.yaml"
echo "   kubectl apply -f k8s/app-service.yaml"
echo ""
echo "2. Access your application:"
echo "   kubectl port-forward svc/milkbooth 8080:80"
echo ""
echo "3. Open browser: http://localhost:8080"
echo ""
echo "=========================================="
