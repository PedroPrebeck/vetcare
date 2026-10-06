"""API JSON com validação, SQL parametrizado e transações."""

import sqlite3
from datetime import date
from clock import today
from flask import Blueprint, current_app, jsonify, request
from db import get_db
from validation import (
    ValidationError,
    text,
    integer,
    choice,
    weight,
    money,
    day,
    moment,
)

api = Blueprint("api", __name__, url_prefix="/api")
MASTERS = {"tutors", "pets", "veterinarians", "services"}
QUERY = """SELECT a.*,p.name AS pet_name,p.species,p.breed,t.name AS tutor_name,
 t.phone AS tutor_phone,v.name AS veterinarian_name,s.name AS service_name,r.id AS record_id
 FROM appointment_balances a JOIN pets p ON p.id=a.pet_id JOIN tutors t ON t.id=p.tutor_id
 JOIN veterinarians v ON v.id=a.veterinarian_id JOIN services s ON s.id=a.service_id
 LEFT JOIN medical_records r ON r.appointment_id=a.id"""


def rows(sql, args=()):
    return [dict(r) for r in get_db().execute(sql, args).fetchall()]


def payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Envie um objeto JSON válido.")
    return data


def exists(table, identifier, active=False):
    if table not in MASTERS | {"appointments"}:
        raise ValidationError("Cadastro inválido.")
    row = (
        get_db().execute(f"SELECT * FROM {table} WHERE id=?", (identifier,)).fetchone()
    )
    if row is None:
        raise ValidationError("Registro não encontrado.")
    if active and not row["active"]:
        raise ValidationError("Selecione um cadastro ativo.")
    return row


@api.errorhandler(ValidationError)
def validation_error(error):
    return jsonify(error=str(error)), 400


@api.errorhandler(sqlite3.IntegrityError)
def integrity_error(error):
    message = str(error)
    if message.startswith("UNIQUE constraint"):
        message = "Já existe um registro com esse nome, CRMV ou consulta vinculada."
    elif message.startswith("FOREIGN KEY"):
        message = "O registro está vinculado a outros dados."
    elif message.startswith(("CHECK", "NOT NULL")):
        message = "Verifique os campos e os limites permitidos."
    return jsonify(error=message), 409


@api.errorhandler(sqlite3.OperationalError)
def database_error(error):
    current_app.logger.error("Falha SQLite: %s", error)
    return (
        jsonify(
            error="Banco indisponível. Confira a inicialização ou tente novamente."
        ),
        503,
    )


@api.get("/bootstrap")
def bootstrap():
    current_day = today().isoformat()
    db = get_db()
    dashboard = dict(
        today=current_day,
        appointments_today=db.execute(
            "SELECT COUNT(*) FROM appointments WHERE substr(starts_at,1,10)=? AND status<>'Cancelado'",
            (current_day,),
        ).fetchone()[0],
        patients=db.execute("SELECT COUNT(*) FROM pets WHERE active=1").fetchone()[0],
        revenue_month_cents=db.execute(
            "SELECT COALESCE(SUM(amount_cents),0) FROM payments WHERE substr(paid_at,1,7)=?",
            (current_day[:7],),
        ).fetchone()[0],
        outstanding_cents=db.execute(
            "SELECT COALESCE(SUM(balance_cents),0) FROM appointment_balances WHERE status='Concluído'"
        ).fetchone()[0],
    )
    return jsonify(
        dashboard=dashboard,
        tutors=rows("SELECT * FROM tutors ORDER BY active DESC,name"),
        pets=rows(
            "SELECT p.*,t.name AS tutor_name FROM pets p JOIN tutors t ON t.id=p.tutor_id ORDER BY p.active DESC,p.name"
        ),
        veterinarians=rows("SELECT * FROM veterinarians ORDER BY active DESC,name"),
        services=rows("SELECT * FROM services ORDER BY active DESC,name"),
        appointments=rows(QUERY + " ORDER BY a.starts_at,a.id"),
        payments=rows(
            """SELECT x.*,p.name AS pet_name,t.name AS tutor_name FROM payments x
        JOIN appointments a ON a.id=x.appointment_id JOIN pets p ON p.id=a.pet_id JOIN tutors t ON t.id=p.tutor_id ORDER BY x.paid_at DESC,x.id DESC"""
        ),
    )


def master_fields(table, data):
    if table == "tutors":
        email = text(data, "email", "E-mail", maximum=150) or None
        if email and (
            "@" not in email or "." not in email.split("@")[-1] or " " in email
        ):
            raise ValidationError("E-mail inválido.")
        return dict(
            name=text(data, "name", "Nome", 2, 100),
            phone=text(data, "phone", "Telefone", 8, 25),
            email=email,
            address=text(data, "address", "Endereço", maximum=250),
        )
    if table == "pets":
        tutor_id = integer(data, "tutor_id", "Tutor")
        exists("tutors", tutor_id, True)
        birth = data.get("birth_date") or None
        if birth:
            day(birth, "Nascimento", False)
        return dict(
            tutor_id=tutor_id,
            name=text(data, "name", "Nome", 1, 80),
            species=choice(data, "species", ["Cão", "Gato", "Ave", "Outro"], "Espécie"),
            breed=text(data, "breed", "Raça", maximum=80),
            sex=choice(data, "sex", ["Macho", "Fêmea", "Não informado"], "Sexo"),
            birth_date=birth,
            weight_kg=weight(data),
            notes=text(data, "notes", "Observações"),
        )
    if table == "veterinarians":
        return dict(
            name=text(data, "name", "Nome", 2, 100),
            crmv=text(data, "crmv", "CRMV", 3, 30),
            specialty=text(data, "specialty", "Especialidade", 2, 100),
            phone=text(data, "phone", "Telefone", maximum=25),
        )
    return dict(
        name=text(data, "name", "Serviço", 2, 100),
        price_cents=money(data, "price", True),
        duration_minutes=integer(data, "duration_minutes", "Duração", 10, 240),
    )


@api.post("/<table>")
def create_master(table):
    if table not in MASTERS:
        return jsonify(error="Recurso não encontrado."), 404
    fields = master_fields(table, payload())
    db = get_db()
    with db:
        cursor = db.execute(
            f"INSERT INTO {table} ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})",
            tuple(fields.values()),
        )
    return jsonify(id=cursor.lastrowid), 201


@api.patch("/<table>/<int:identifier>")
def edit_master(table, identifier):
    if table not in MASTERS:
        return jsonify(error="Recurso não encontrado."), 404
    old = exists(table, identifier)
    data = payload()
    db = get_db()
    if set(data) == {"active"}:
        fields = {"active": integer(data, "active", "Situação", 0, 1)}
        if not fields["active"]:
            if (
                table == "tutors"
                and db.execute(
                    "SELECT 1 FROM pets WHERE tutor_id=? AND active=1", (identifier,)
                ).fetchone()
            ):
                raise ValidationError(
                    "Arquive os animais deste tutor antes de arquivar o tutor."
                )
            if table in {"pets", "veterinarians", "services"}:
                fk = {
                    "pets": "pet_id",
                    "veterinarians": "veterinarian_id",
                    "services": "service_id",
                }[table]
                if db.execute(
                    f"SELECT 1 FROM appointments WHERE {fk}=? AND status IN ('Agendado','Confirmado')",
                    (identifier,),
                ).fetchone():
                    raise ValidationError(
                        "Há consultas abertas vinculadas. Conclua ou cancele antes de arquivar."
                    )
        elif table == "pets":
            exists("tutors", old["tutor_id"], True)
    else:
        fields = master_fields(table, data)
        if (
            table == "pets"
            and fields["tutor_id"] != old["tutor_id"]
            and db.execute(
                "SELECT 1 FROM appointments WHERE pet_id=?", (identifier,)
            ).fetchone()
        ):
            raise ValidationError(
                "Animal com histórico não pode trocar de tutor neste projeto."
            )
    with db:
        db.execute(
            f"UPDATE {table} SET {','.join(k+'=?' for k in fields)} WHERE id=?",
            (*fields.values(), identifier),
        )
    return jsonify(ok=True)


def appointment_fields(data):
    pet_id = integer(data, "pet_id", "Paciente")
    pet = exists("pets", pet_id, True)
    exists("tutors", pet["tutor_id"], True)
    vet = integer(data, "veterinarian_id", "Veterinário")
    exists("veterinarians", vet, True)
    service_id = integer(data, "service_id", "Serviço")
    service = exists("services", service_id, True)
    return dict(
        pet_id=pet_id,
        veterinarian_id=vet,
        service_id=service_id,
        starts_at=moment(data.get("starts_at")),
        duration_minutes=service["duration_minutes"],
        fee_cents=service["price_cents"],
        notes=text(data, "notes", "Observações"),
    )


@api.post("/appointments")
def create_appointment():
    fields = appointment_fields(payload())
    db = get_db()
    with db:
        cursor = db.execute(
            f"INSERT INTO appointments ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})",
            tuple(fields.values()),
        )
    return jsonify(id=cursor.lastrowid), 201


@api.patch("/appointments/<int:identifier>")
def edit_appointment(identifier):
    old = exists("appointments", identifier)
    if old["status"] in ("Concluído", "Cancelado"):
        raise ValidationError(
            "Consultas concluídas ou canceladas preservam o histórico."
        )
    data = payload()
    if set(data) == {"status"}:
        fields = {
            "status": choice(data, "status", ["Confirmado", "Cancelado"], "Status")
        }
    else:
        fields = appointment_fields(data)
        if fields["service_id"] == old["service_id"]:
            fields.update(
                fee_cents=old["fee_cents"], duration_minutes=old["duration_minutes"]
            )
    db = get_db()
    with db:
        db.execute(
            f"UPDATE appointments SET {','.join(k+'=?' for k in fields)} WHERE id=?",
            (*fields.values(), identifier),
        )
    return jsonify(ok=True)


@api.get("/pets/<int:identifier>/history")
def patient_history(identifier):
    exists("pets", identifier)
    return jsonify(
        appointments=rows(
            QUERY + " WHERE a.pet_id=? ORDER BY a.starts_at DESC", (identifier,)
        ),
        records=rows(
            """SELECT r.*,a.starts_at,v.name AS veterinarian_name,s.name AS service_name FROM medical_records r
        JOIN appointments a ON a.id=r.appointment_id JOIN veterinarians v ON v.id=a.veterinarian_id
        JOIN services s ON s.id=a.service_id WHERE a.pet_id=? ORDER BY a.starts_at DESC""",
            (identifier,),
        ),
    )


@api.post("/appointments/<int:identifier>/record")
def finish_appointment(identifier):
    old = exists("appointments", identifier)
    if old["status"] not in ("Agendado", "Confirmado"):
        raise ValidationError("Esta consulta não está aberta.")
    if old["starts_at"][:10] > today().isoformat():
        raise ValidationError("Consulta futura não pode ser concluída.")
    data = payload()
    fields = dict(
        appointment_id=identifier,
        complaint=text(data, "complaint", "Queixa", 2),
        diagnosis=text(data, "diagnosis", "Avaliação", 2),
        treatment=text(data, "treatment", "Conduta"),
        weight_kg=weight(data),
    )
    db = get_db()
    # Conclusão e prontuário são uma única transação. Qualquer falha desfaz ambos.
    with db:
        db.execute("BEGIN IMMEDIATE")
        cursor = db.execute(
            "UPDATE appointments SET status='Concluído' WHERE id=? AND status IN ('Agendado','Confirmado')",
            (identifier,),
        )
        if cursor.rowcount != 1:
            raise ValidationError("Consulta já foi alterada. Recarregue a página.")
        db.execute(
            f"INSERT INTO medical_records ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})",
            tuple(fields.values()),
        )
        if fields["weight_kg"] is not None:
            db.execute(
                "UPDATE pets SET weight_kg=? WHERE id=?",
                (fields["weight_kg"], old["pet_id"]),
            )
    return jsonify(ok=True), 201


@api.post("/payments")
def receive_payment():
    data = payload()
    identifier = integer(data, "appointment_id", "Consulta")
    exists("appointments", identifier)
    amount = money(data)
    method = choice(data, "method", ["Pix", "Dinheiro", "Cartão"], "Forma de pagamento")
    paid_at = day(data.get("paid_at"), "Pagamento", False)
    db = get_db()
    with db:
        cursor = db.execute(
            "INSERT INTO payments(appointment_id,amount_cents,method,paid_at) VALUES (?,?,?,?)",
            (identifier, amount, method, paid_at),
        )
    return jsonify(id=cursor.lastrowid), 201
