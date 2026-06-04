from flask import Flask, request, jsonify
from flask_cors import CORS
from dgsp_agent import DGSPAgent
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
CORS(app)

# Inicializa el agente una sola vez al arrancar el servidor
# None = escanea automáticamente la carpeta ./documents
# Usamos un session_id fijo para persistencia entre peticiones web
agent = DGSPAgent(documents_path=None, session_id="web_session")

@app.route("/api/chat", methods=["POST"])
def chat():
    # Inicialización explícita de variables para evitar persistencia entre peticiones
    user_message = ""
    response = ""

    data = request.get_json()
    user_message = data.get("message", "").strip()

    # DIAGNÓSTICO HIPÓTESIS 1: Formato del mensaje entrante
    print(f"\n[DEBUG API] Input recibido del frontend: {user_message}")
    print(f"[DEBUG API] Tipo de dato: {type(user_message)}")
    print(f"[DEBUG API] Data completa recibida: {data}")

    if not user_message:
        return jsonify({"response": "Mensaje vacío."}), 400

    try:
        # PRUEBA DE AISLAMIENTO: Forzar ejecución limpia sin historial
        # Pasar use_history=False para ignorar memoria intermedia
        print(f"[DEBUG EXECUTE] Invocando agente con input: '{user_message}'")
        response = agent.ask(user_message, use_history=False)
        print(f"[DEBUG EXECUTE] Respuesta del agente: '{response[:100]}...'")  # Primeros 100 chars
        return jsonify({"response": response})
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"response": "Error interno del servidor."}), 500

@app.route("/api/reset", methods=["POST"])
def reset():
    try:
        agent.memory.delete_session("web_session")
        agent.memory.create_session("web_session")
        return jsonify({"ok": True})
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"ok": False}), 500

if __name__ == "__main__":
    app.run(port=3000, debug=False)
