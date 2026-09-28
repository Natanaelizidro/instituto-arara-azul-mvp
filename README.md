from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from pathlib import Path

app = Flask(__name__)

app.config["SECRET_KEY"] = "chave-mvp-arara-azul"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database/arara_azul.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)


class Atividade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="Pendente")
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect(url_for("login"))

        return func(*args, **kwargs)

    return wrapper


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and check_password_hash(usuario.senha_hash, senha):
            session["usuario_id"] = usuario.id
            session["usuario_nome"] = usuario.nome
            return redirect(url_for("atividades"))

        flash("E-mail ou senha inválidos.", "erro")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/atividades")
@login_required
def atividades():
    lista = Atividade.query.filter_by(
        usuario_id=session["usuario_id"]
    ).order_by(Atividade.id.desc()).all()

    return render_template("atividades.html", atividades=lista)


@app.route("/atividades/nova", methods=["GET", "POST"])
@login_required
def nova_atividade():
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        descricao = request.form.get("descricao", "").strip()

        if not titulo or not descricao:
            flash("Preencha todos os campos.", "erro")
            return render_template("nova_atividade.html")

        atividade = Atividade(
            titulo=titulo,
            descricao=descricao,
            status="Pendente",
            usuario_id=session["usuario_id"]
        )

        db.session.add(atividade)
        db.session.commit()

        flash("Atividade cadastrada com sucesso.", "sucesso")
        return redirect(url_for("atividades"))

    return render_template("nova_atividade.html")


@app.route("/atividades/<int:id>/status", methods=["POST"])
@login_required
def alterar_status(id):
    atividade = Atividade.query.filter_by(
        id=id,
        usuario_id=session["usuario_id"]
    ).first_or_404()

    novo_status = request.form.get("status")

    if novo_status in ["Pendente", "Em andamento", "Concluída"]:
        atividade.status = novo_status
        db.session.commit()
        flash("Status atualizado.", "sucesso")

    return redirect(url_for("atividades"))


@app.route("/atividades/<int:id>/excluir", methods=["POST"])
@login_required
def excluir_atividade(id):
    atividade = Atividade.query.filter_by(
        id=id,
        usuario_id=session["usuario_id"]
    ).first_or_404()

    db.session.delete(atividade)
    db.session.commit()

    flash("Atividade excluída.", "sucesso")
    return redirect(url_for("atividades"))


def criar_dados_iniciais():
    if Usuario.query.count() == 0:
        usuario = Usuario(
            nome="Voluntário Demo",
            email="voluntario@exemplo.com",
            senha_hash=generate_password_hash("12345678")
        )

        db.session.add(usuario)
        db.session.commit()


with app.app_context():
    Path("database").mkdir(exist_ok=True)
    db.create_all()
    criar_dados_iniciais()


if __name__ == "__main__":
    app.run(debug=True)
