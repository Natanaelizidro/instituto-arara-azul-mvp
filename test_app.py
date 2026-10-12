from app import app


def test_atividades_exige_login():
    app.config["TESTING"] = True
    cliente = app.test_client()

    resposta = cliente.get(
        "/atividades",
        follow_redirects=False
    )

    assert resposta.status_code in (302, 401)