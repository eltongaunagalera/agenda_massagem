from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    matricula = db.Column(db.String(20), unique=True, nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    agendamentos = db.relationship('Agendamento', backref='usuario', lazy=True)

class Agendamento(db.Model):
    __tablename__ = 'agendamentos'
    
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10), nullable=False)        # Formato: "YYYY-MM-DD"
    horario_inicio = db.Column(db.String(5), nullable=False) # Formato: "HH:MM"
    horario_fim = db.Column(db.String(5), nullable=False)    # Formato: "HH:MM"
    status = db.Column(db.String(20), default='ativa')       # 'ativa' ou 'finalizada'
    
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)