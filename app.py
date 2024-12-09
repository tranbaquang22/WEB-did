from flask import Flask, render_template, request, jsonify
import requests
import random
import string

app = Flask(__name__)

ACA_PY_ADMIN_URL = "http://192.168.1.81:8021"  # Địa chỉ API của ACA-Py
HEADERS = {"Content-Type": "application/json"}

# Trang chính (Dashboard)
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

# Tạo DID mới và đăng ký lên Ledger
@app.route('/create-and-register-did', methods=['POST'])
def create_and_register_did():
    try:
        # Tạo seed ngẫu nhiên
        seed = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        create_payload = {"method": "sov", "seed": seed}
        
        # Tạo DID
        create_response = requests.post(
            f"{ACA_PY_ADMIN_URL}/wallet/did/create", headers=HEADERS, json=create_payload
        )
        
        if create_response.status_code != 200:
            return jsonify({
                "message": "Failed to create DID",
                "details": create_response.json()
            }), create_response.status_code
        
        did_data = create_response.json().get("result", {})
        did = did_data.get("did")
        verkey = did_data.get("verkey")
        
        if not did or not verkey:
            return jsonify({
                "message": "DID created but incomplete",
                "details": did_data
            }), 500
        
        # Đăng ký DID lên Ledger
        register_payload = {"did": did, "verkey": verkey, "alias": f"DID-{did[:6]}", "role": None}
        register_response = requests.post(
            f"{ACA_PY_ADMIN_URL}/ledger/register-nym", headers=HEADERS, json=register_payload
        )
        
        if register_response.status_code == 200:
            return jsonify({"message": "DID created and registered successfully", "did_info": did_data}), 200
        else:
            return jsonify({
                "message": "DID created but failed to register",
                "did_info": did_data,
                "error_details": register_response.json()
            }), register_response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Hiển thị danh sách DID đã tạo từ ví ACA-Py
@app.route('/list-dids', methods=['GET'])
def list_dids():
    try:
        # Gửi yêu cầu tới ACA-Py để lấy danh sách DID
        response = requests.get(f"{ACA_PY_ADMIN_URL}/wallet/did", headers=HEADERS)
        
        if response.status_code == 200:
            dids = response.json().get("results", [])
            return render_template('list_dids.html', dids=dids)
        else:
            return render_template('list_dids.html', dids=[], error="Không thể lấy danh sách DID.")
    except Exception as e:
        return render_template('list_dids.html', dids=[], error=str(e))

# Xác thực DID
@app.route('/verify-did/<did>', methods=['GET'])
def verify_did(did):
    try:
        # Kiểm tra DID trong ví ACA-Py
        wallet_response = requests.get(f"{ACA_PY_ADMIN_URL}/wallet/did", headers=HEADERS)
        if wallet_response.status_code == 200:
            wallet_dids = wallet_response.json().get("results", [])
            for d in wallet_dids:
                if d["did"] == did:
                    return jsonify({
                        "did": did,
                        "status": "wallet_found",
                        "details": d
                    }), 200

        # Nếu không tìm thấy trong ví, kiểm tra trên Ledger
        ledger_response = requests.get(f"{ACA_PY_ADMIN_URL}/ledger/get-nym?did={did}", headers=HEADERS)
        if ledger_response.status_code == 200:
            return jsonify({
                "did": did,
                "status": "ledger_found",
                "details": ledger_response.json()
            }), 200
        else:
            return jsonify({"message": "DID not found in wallet or ledger"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Giao diện tạo DID
@app.route('/create-did-page')
def create_did_page():
    return render_template('create_did.html')

# Giao diện xác thực DID
@app.route('/verify-did-page')
def verify_did_page():
    return render_template('verify_did.html')

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
