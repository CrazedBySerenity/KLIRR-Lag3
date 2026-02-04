from flask import Flask, request, send_from_directory, jsonify
import uuid
import os
from base64 import b64decode, b64encode

from Cryptodome.Cipher import AES
from Cryptodome.Hash import SHA256
from Cryptodome.Random import get_random_bytes
from Cryptodome.Util.Padding import pad, unpad

app = Flask(__name__)

html_template = """<html>
<head>
<title>
ID : {NAME}
</title>
</head>
<body>

<h2>Namn: {NAME} </h2><h4> Datum: {DATE} </h4>

<h3>Personnummer:</h3>
<p>{PRNR}</p>

<h3> Adress: {ADDRESS} </h3>
<h3> Postnr: {POSTNR} </h3>

<h4>Områdes ID:</h4>
<p>{ZONKOD}</p>

<p>{ENCRYPTED_DATA}</p>

</body>
</html>
"""

# Directory to store the generated PWA files
PWA_DIR = "pwa_files"

os.makedirs(PWA_DIR, exist_ok=True)

with open("secret.b64", "r") as f:
    b64_content = f.read()

SECRET_BYTES = b64decode(b64_content)


def encrypt(data: bytes, secret: bytes):
    """
    encrypt the data, returning the encrypted data with the IV (16 bytes) prepended to it
    """
    key = SHA256.new(secret).digest()
    iv = get_random_bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(data, AES.block_size)
    ciphertext = cipher.encrypt(padded_data)
    return iv + ciphertext


def decrypt(encrypted_data: bytes, secret: bytes) -> bytes:
    """
    Decrypts data encrypted with AES-CBC, with the iv pretended to the data
    """
    key = SHA256.new(secret).digest()
    iv = encrypted_data[:16]
    ciphertext = encrypted_data[16:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_plaintext = cipher.decrypt(ciphertext)
    plaintext = unpad(padded_plaintext, AES.block_size)
    return plaintext


@app.route("/generate", methods=["POST"])
def generate_pwa():
    # Get data from JSON payload
    data = request.get_json()

    # Assign default values if any field is missing
    name = data.get("NAME", "Unknown")
    date = data.get("DATE", "Unknown")
    prnr = data.get("PRNR", "Unknown")
    address = data.get("ADDRESS", "Unknown")
    postnr = data.get("POSTNR", "Unknown")
    zonkod = data.get("ZONKOD", "Unknown")

    encrypted_data = encrypt(request.data, SECRET_BYTES)

    pwa_id = str(uuid.uuid4())

    print(encrypted_data)
    html_content = html_template.format(
        NAME=name,
        DATE=date,
        PRNR=prnr,
        ADDRESS=address,
        POSTNR=postnr,
        ZONKOD=zonkod,
        ENCRYPTED_DATA=b64encode(encrypted_data).decode("ascii"),
    )

    # Save to file
    filename = f"{pwa_id}.html"
    filepath = os.path.join(PWA_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Return UUID to the client
    return jsonify({"link": f"{request.host_url}pwa/{pwa_id}"})


@app.route("/pwa/<uuid>", methods=["GET"])
def get_pwa(uuid):
    filename = f"{uuid}.html"
    filepath = os.path.join(PWA_DIR, filename)
    if os.path.exists(filepath):
        # Send the file if it exists
        return send_from_directory(PWA_DIR, filename, as_attachment=False)
    else:
        # Return 404 if not found
        return jsonify({"error": "PWA file not found"}), 404

@app.route("/decrypt", methods=["POST"])
def decrypt_data():
    content = request.get_json()
    if not content or 'data' not in content:
        return jsonify({'error': 'Missing data field'}), 400


    binary_data = b64decode(content['data'])

    print(binary_data)

    plaintext = decrypt(binary_data, SECRET_BYTES)
    return jsonify({'data': plaintext.decode()})


if __name__ == "__main__":
    app.run(debug=True)
