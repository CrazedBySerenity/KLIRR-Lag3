# to open/create a new html file in the write mode
import os
import uuid

# katalogen där detta Python-script ligger
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# repository-mappen 
OUTPUT_DIR = os.path.join(BASE_DIR, "repository")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# variabler
file_name = f"{uuid.uuid4()}.html" #skapar unikt htmlfilnamn
file_path = os.path.join(OUTPUT_DIR, file_name) #filens directory

# Öppnar fil att skapas
with open(file_path, "w", encoding="utf-8") as f:

    # Genererad html template, med angivet datum
    html_template = """<html>
<head>
<title>
ID : (NAME)
</title>
</head>
<body>

<h2>Namn: (NAME) </h2><h4> Datum: (DATE) </h4>

<h3>Personnummer:</h3>
<p>(PRNR)</p>

<h3> Adress: (ADDRESS) </h3>
<h3> Postnr: (POSTNR) </h3>

<h4>Områdes ID:</h4>
<p>(ZONKOD)</p>

</body>
</html>
"""
    # skriv html-koden till filen
    f.write(html_template)
