# 🚀 Oracle Cloud Always Free 24/7 Deployment Guide

To deploy the **Antigravity AI Brain Trading Model** to your **Oracle Cloud VM (Ubuntu / Ampere A1)** so that your laptop can be turned off 24/7, run this single command on your Oracle VM terminal:

```bash
git clone https://github.com/USRJ78/universal-market-app.git && cd universal-market-app/analysis && chmod +x deploy_oracle_cloud.sh && ./deploy_oracle_cloud.sh
```

---

### 📑 What This Deployment Does Automatically:
1. **Installs System Dependencies**: Python 3.12, Rust Toolchain (`cargo`), Nginx Web Server.
2. **Compiles Pure Rust Engines**: Builds LLVM release binaries for sub-microsecond HFT math solvers.
3. **Creates 24/7 Systemd Background Service**: `antigravity_ai_agent.service` auto-starts on boot and restarts automatically in 5 seconds if interrupted.
4. **Zero-Downtime Guarantee**: Your trading models, live Delta Testnet orders, and self-learning engines run 24/7 continuously on Oracle Cloud servers.
