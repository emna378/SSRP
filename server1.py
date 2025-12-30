from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
import json

app = Flask(__name__)
app.secret_key = "sspr_secret_key"

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

# Stockage des données clients (liste complète)
clients_data = []

# Seuils d'alerte
CPU_ALERT = 70
RAM_ALERT = 80
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
# Dashboard clients uniques
# -------------------------
@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    
    # Supprimer les doublons par IP (dernier envoi)
    unique_clients = {}
    for client in clients_data:
        unique_clients[client["ip"]] = client

    return render_template("dashboard.html", clients=list(unique_clients.values()))

# -------------------------
# Détails d’un client
# -------------------------
@app.route("/client/<ip>")
def client_detail(ip):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    # Filtrer tous les envois pour ce client
    history = [c for c in clients_data if c["ip"] == ip]

    # Dernière donnée
    latest = history[-1] if history else None

    # Vérifier alertes
    alert = False
    if latest:
        if latest["cpu_percent"] > CPU_ALERT or latest["ram_percent"] > RAM_ALERT or latest["open_ports_count"] > PORTS_ALERT:
            alert = True

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
        print(f"[+] Données reçues : {data['hostname']} à {data['timestamp']} depuis {data['ip']}")
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "error", "message": "Aucune donnée reçue"}), 400

# -------------------------
# Logout
# -------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

