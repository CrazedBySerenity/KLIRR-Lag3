from flask import Flask, request, send_from_directory, jsonify
import uuid
import os

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

</body>
</html>
"""

# Directory to store the generated PWA files
PWA_DIR = "pwa_files"

# Ensure the directory exists
os.makedirs(PWA_DIR, exist_ok=True)


@app.route("/generate", methods=["POST"])
def generate_pwa():
    # Get data from JSON payload
    data = request.get_json()
    # or you can get form data: request.form

    # Assign default values if any field is missing
    name = data.get("NAME", "Unknown")
    date = data.get("DATE", "Unknown")
    prnr = data.get("PRNR", "Unknown")
    address = data.get("ADDRESS", "Unknown")
    postnr = data.get("POSTNR", "Unknown")
    zonkod = data.get("ZONKOD", "Unknown")

    # Generate a UUID
    pwa_id = str(uuid.uuid4())

    # Fill the template
    html_content = html_template.format(
        NAME=name, DATE=date, PRNR=prnr, ADDRESS=address, POSTNR=postnr, ZONKOD=zonkod
    )

    # Save to file
    filename = f"{pwa_id}.html"
    filepath = os.path.join(PWA_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Return UUID to the client
    return jsonify({"uuid": pwa_id})


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


if __name__ == "__main__":
    app.run(debug=True)
