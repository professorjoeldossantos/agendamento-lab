import os
from flask import Flask, render_template_string, request, redirect, jsonify
import psycopg2
from urllib.parse import urlparse
from datetime import datetime

app = Flask(__name__)


EQUIPAMENTOS = {
    "Notebook": 10,
    "Tablet": 10,
    "Caixa de Som": 5
}

def get_connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise Exception("DATABASE_URL não configurada.")
        
    url = urlparse(database_url)
    return psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS agendamentos (
            id SERIAL PRIMARY KEY,
            professor TEXT,
            materia TEXT,
            equipamento TEXT,
            quantidade INTEGER,
            periodo TEXT,
            aula INTEGER,
            atividade TEXT,
            data DATE
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


@app.route("/", methods=["GET", "POST"])
def index():
    erro = None

    if request.method == "POST":
        professor = request.form["professor"]
        materia = request.form["materia"]
        equipamento = request.form["equipamento"]
        quantidade = int(request.form["quantidade"])
        periodo = request.form["periodo"]
        aula = int(request.form["aula"])
        atividade = request.form["atividade"]
        data = request.form["data"]

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT COALESCE(SUM(quantidade),0)
            FROM agendamentos
            WHERE equipamento=%s AND periodo=%s AND aula=%s AND data=%s
        """, (equipamento, periodo, aula, data))

        total = cur.fetchone()[0]

        if total + quantidade > EQUIPAMENTOS[equipamento]:
            erro = "Equipamentos insuficientes para este horário."
        else:
            cur.execute("""
                INSERT INTO agendamentos
                (professor, materia, equipamento, quantidade, periodo, aula, atividade, data)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (professor, materia, equipamento, quantidade, periodo, aula, atividade, data))
            conn.commit()
            cur.close()
            conn.close()
            return redirect("/")

        cur.close()
        conn.close()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM agendamentos ORDER BY data, periodo, aula")
    agendamentos = cur.fetchall()
    cur.close()
    conn.close()

    return render_template_string(TEMPLATE, agendamentos=agendamentos, erro=erro)

@app.route("/delete/<int:id>")
def delete(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM agendamentos WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/")

@app.route("/events")
def events():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, professor, equipamento, periodo, aula, data FROM agendamentos")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    eventos = []
    for r in rows:
        eventos.append({
            "id": r[0],
            "title": f"{r[1]} - {r[2]} ({r[3]} Aula {r[4]})",
            "start": r[5].strftime("%Y-%m-%d")
        })

    return jsonify(eventos)

TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agendamento Laboratório</title>

<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.10/main.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.10/main.min.js"></script>

</head>

<body class="bg-light">

<div class="container mt-4">

<div class="card shadow p-4 mb-4">
<h3 class="text-center">📚 Agendamento de Equipamentos</h3>

{% if erro %}
<div class="alert alert-danger">{{erro}}</div>
{% endif %}

<form method="POST" class="row g-3">

<div class="col-md-4">
<label>Data</label>
<input type="date" name="data" class="form-control" required>
</div>

<div class="col-md-4">
<label>Professor</label>
<input name="professor" class="form-control" required>
</div>

<div class="col-md-4">
<label>Matéria</label>
<input name="materia" class="form-control" required>
</div>

<div class="col-md-3">
<label>Equipamento</label>
<select name="equipamento" class="form-select">
<option>Notebook</option>
<option>Tablet</option>
<option>Caixa de Som</option>
</select>
</div>

<div class="col-md-2">
<label>Qtd</label>
<input type="number" name="quantidade" min="1" class="form-control" required>
</div>

<div class="col-md-3">
<label>Período</label>
<select name="periodo" class="form-select">
<option>Manhã</option>
<option>Tarde</option>
<option>Noite</option>
</select>
</div>

<div class="col-md-2">
<label>Aula</label>
<input type="number" name="aula" min="1" max="6" class="form-control" required>
</div>

<div class="col-md-12">
<label>Atividade</label>
<input name="atividade" class="form-control" required>
</div>

<div class="col-12 text-center">
<button class="btn btn-primary btn-lg">Agendar</button>
</div>

</form>
</div>

<div class="card shadow p-4 mb-4">
<h4>📅 Calendário</h4>
<div id="calendar"></div>
</div>

<div class="card shadow p-4">
<h4>📋 Lista de Agendamentos</h4>
<table class="table table-striped">
<tr>
<th>Data</th>
<th>Professor</th>
<th>Equipamento</th>
<th>Qtd</th>
<th>Período</th>
<th>Aula</th>
<th>Ação</th>
</tr>
{% for ag in agendamentos %}
<tr>
<td>{{ag[8]}}</td>
<td>{{ag[1]}}</td>
<td>{{ag[3]}}</td>
<td>{{ag[4]}}</td>
<td>{{ag[5]}}</td>
<td>{{ag[6]}}</td>
<td>
<a href="/delete/{{ag[0]}}" class="btn btn-danger btn-sm"
onclick="return confirm('Deseja excluir este agendamento?')">
Excluir
</a>
</td>
</tr>
{% endfor %}
</table>
</div>

</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
var calendarEl = document.getElementById('calendar');
var calendar = new FullCalendar.Calendar(calendarEl, {
initialView: 'dayGridMonth',
locale: 'pt-br',
events: '/events'
});
calendar.render();
});
</script>

</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
