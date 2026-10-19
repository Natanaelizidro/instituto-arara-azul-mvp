from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from pathlib import Path
import os

# =====================================
# INSTITUTO ARARA AZUL - MVP
# =====================================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "chave-mvp-arara-azul"
)

# Banco SQLite dentro da pasta instance
pasta_banco = Path(app.instance_path) / "database"
pasta_banco.mkdir(parents=True, exist_ok=True)

arquivo_banco = pasta_banco / "arara_azul.db"

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + arquivo_banco.as_posix()
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# =====================================
# MODELO DE USUÁRIO
# =====================================

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)


# =====================================
# MODELO DE ATIVIDADE
# =====================================

class Atividade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text, nullable=False)

    status = db.Column(
        db.String(30),
        nullable=False,
        default="Pendente"
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id"),
        nullable=False
    )


# =====================================
# PROTEÇÃO DAS PÁGINAS
# =====================================

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect(url_for("login"))

        return func(*args, **kwargs)

    return wrapper


# =====================================
# LOGIN
# =====================================

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and check_password_hash(
            usuario.senha_hash, senha
        ):
            session.clear()
            session["usuario_id"] = usuario.id
            session["usuario_nome"] = usuario.nome

            return redirect(url_for("atividades"))

        flash("E-mail ou senha inválidos.", "erro")

    return render_template("login.html")


# =====================================
# CADASTRO DE USUÁRIOS
# =====================================

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        confirmar_senha = request.form.get(
            "confirmar_senha", ""
        )

        if not nome or not email or not senha or not confirmar_senha:
            flash("Preencha todos os campos.", "erro")
            return render_template("cadastro.html")

        if len(senha) < 8:
            flash(
                "A senha deve ter pelo menos 8 caracteres.",
                "erro"
            )
            return render_template("cadastro.html")

        if senha != confirmar_senha:
            flash("As senhas não são iguais.", "erro")
            return render_template("cadastro.html")

        usuario_existente = Usuario.query.filter_by(
            email=email
        ).first()

        if usuario_existente:
            flash("Este e-mail já está cadastrado.", "erro")
            return render_template("cadastro.html")

        novo_usuario = Usuario(
            nome=nome,
            email=email,
            senha_hash=generate_password_hash(senha)
        )

        try:
            db.session.add(novo_usuario)
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception("Erro ao cadastrar usuário")
            flash(
                "Não foi possível concluir o cadastro. Tente novamente.",
                "erro"
            )
            return render_template("cadastro.html")

        flash(
            "Cadastro realizado com sucesso! Faça seu login.",
            "sucesso"
        )
        return redirect(url_for("login"))

    return render_template("cadastro.html")


# =====================================
# SAIR DO SISTEMA
# =====================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# =====================================
# LISTAR ATIVIDADES
# =====================================

@app.route("/atividades")
@login_required
def atividades():

    lista = Atividade.query.filter_by(
        usuario_id=session["usuario_id"]
    ).order_by(
        Atividade.id.desc()
    ).all()

    return render_template(
        "atividades.html",
        atividades=lista
    )


# =====================================
# CADASTRAR NOVA ATIVIDADE
# =====================================

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


# =====================================
# ALTERAR STATUS DA ATIVIDADE
# =====================================

@app.route(
    "/atividades/<int:id>/status",
    methods=["POST"]
)
@login_required
def alterar_status(id):

    atividade = Atividade.query.filter_by(
        id=id,
        usuario_id=session["usuario_id"]
    ).first_or_404()

    novo_status = request.form.get("status")

    status_validos = [
        "Pendente",
        "Em andamento",
        "Concluída"
    ]

    if novo_status in status_validos:
        atividade.status = novo_status
        db.session.commit()
        flash("Status atualizado.", "sucesso")
    else:
        flash("Status inválido.", "erro")

    return redirect(url_for("atividades"))


# =====================================
# EXCLUIR ATIVIDADE
# =====================================

@app.route(
    "/atividades/<int:id>/excluir",
    methods=["POST"]
)
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


# =====================================
# INICIALIZAR BANCO DE DADOS
# =====================================

with app.app_context():
    db.create_all()

    # Conta de demonstração para testes.
    # Só é criada se ainda não existir nenhum usuário.
    if Usuario.query.count() == 0:
        usuario_demo = Usuario(
            nome="Voluntário Demo",
            email="voluntario@exemplo.com",
            senha_hash=generate_password_hash("12345678")
        )

        db.session.add(usuario_demo)
        db.session.commit()


# =====================================
# EXECUTAR A APLICAÇÃO
# =====================================

if __name__ == "__main__":
    app.run(debug=True)

