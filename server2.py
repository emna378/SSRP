from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "sspr_secret_key"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

clients_data = []
alerts = []

CPU_ALERT = 1
RAM_ALERT = 1
PORTS_ALERT = 10

# -------------------------
# Login
# -------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            flash("Nom d'utilisateur ou mot de passe incorrect", "danger")
            return render_template("login.html")
    return render_template("login.html")

# -------------------------
# Dashboard
# -------------------------
@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    # Clients uniques par IP (dernier envoi)
    unique_clients = {}
    for client in clients_data:
        unique_clients[client["ip"]] = client
    # Ajouter info alerte
    for client in unique_clients.values():
        client["alert"] = (
            client["cpu_percent"] > CPU_ALERT or
            client["ram_percent"] > RAM_ALERT or
            client["open_ports_count"] > PORTS_ALERT or
            client.get("brute_force") or
            client.get("flood") or
            client.get("scan")
        )
    return render_template("dashboard.html", clients=list(unique_clients.values()))

# -------------------------
# Détails client
# -------------------------
@app.route("/client/<ip>")
def client_detail(ip):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    history = [c for c in clients_data if c["ip"] == ip]
    latest = history[-1] if history else None

    alert = False
    if latest:
        alert = (
            latest["cpu_percent"] > CPU_ALERT or
            latest["ram_percent"] > RAM_ALERT or
            latest["open_ports_count"] > PORTS_ALERT or
            latest.get("brute_force") or
            latest.get("flood") or
            latest.get("scan")
        )

    return render_template("client_detail.html", latest=latest, alert=alert, ip=ip, history=history)

# -------------------------
# Endpoint agent
# -------------------------
@app.route("/agent/report", methods=["POST"])
def receive_data():
    data = request.get_json()
    if data:
        data["ip"] = request.remote_addr
        clients_data.append(data)

        # Générer alerte
        if (
            data["cpu_percent"] > CPU_ALERT or
            data["ram_percent"] > RAM_ALERT or
            data["open_ports_count"] > PORTS_ALERT or
            data.get("brute_force") or
            data.get("flood") or
            data.get("scan")
        ):
            alert_data = {
                "ip": data["ip"],
                "hostname": data["hostname"],
                "timestamp": data["timestamp"],
                "type": "brute_force" if data.get("brute_force") else
                        "flood" if data.get("flood") else
                        "scan" if data.get("scan") else "cpu_ram",
                "details": data
            }
            alerts.append(alert_data)

        print(f"[+] Données reçues : {data['hostname']} à {data['timestamp']} depuis {data['ip']}")
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "error", "message": "Aucune donnée reçue"}), 400


def add_alert(ip, hostname, alert_type, pid=None):
    global alerts
    # Vérifier si l’alerte existe déjà (IP + type)
    for alert in alerts:
        if alert["ip"] == ip and alert["type"] == alert_type:
            # Mise à jour du timestamp seulement
            alert["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return

    # Sinon créer nouvelle alerte
    alerts.append({
        "ip": ip,
        "hostname": hostname,
        "type": alert_type,
        "pid": pid,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

# -------------------------
# Endpoint alerts
# -------------------------
@app.route("/alerts")
def list_alerts():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("alerts.html", alerts=alerts)

# -------------------------
# Bloquer IP
# -------------------------
@app.route("/block/<ip>")
def block_ip(ip):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    import os
    os.system(f"sudo iptables -A INPUT -s {ip} -j DROP")
    flash(f"IP {ip} bloquée.", "success")
    return redirect(url_for("dashboard"))



@app.route("/kill/<ip>/<int:pid>")
def kill_process(ip, pid):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    # ⚠️ Simulation (sécurité)
    # En réel → commande envoyée à l’agent
    print(f"[ADMIN] Kill process {pid} on {ip}")

    flash(f"Process {pid} arrêté sur {ip}", "success")
    return redirect(url_for("list_alerts"))

# -------------------------
# Logout
# -------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

