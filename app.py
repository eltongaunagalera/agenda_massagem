from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, Usuario, Agendamento
from utils import gerar_slots_massagem

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave-secreta-para-sessoes'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///banco.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


# =======================================================
# ROTAS DE AUTENTICAÇÃO E CONTA
# =======================================================

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form.get('nome')
        matricula = request.form.get('matricula', '').upper().strip()
        senha = request.form.get('senha')

        if Usuario.query.filter_by(matricula=matricula).first():
            flash('Matrícula já cadastrada no sistema!', 'danger')
            return redirect(url_for('cadastro'))

        senha_hash = generate_password_hash(senha)
        novo_usuario = Usuario(nome=nome, matricula=matricula, senha=senha_hash, is_admin=False)
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        flash('Cadastro realizado com sucesso! Faça login.', 'success')
        return redirect(url_for('login'))

    return render_template('cadastro.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        matricula = request.form.get('matricula', '').upper().strip()
        senha = request.form.get('senha')
        manter_logado = True if request.form.get('lembrar') else False

        usuario = Usuario.query.filter_by(matricula=matricula).first()

        if not usuario or not check_password_hash(usuario.senha, senha):
            flash('Matrícula ou senha incorretos.', 'danger')
            return redirect(url_for('login'))

        login_user(usuario, remember=manter_logado)
        
        if usuario.is_admin:
            return redirect(url_for('admin_painel'))
        return redirect(url_for('usuario_painel'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/alterar-senha', methods=['GET', 'POST'])
@login_required
def alterar_senha():
    if request.method == 'POST':
        senha_atual = request.form.get('senha_atual')
        nova_senha = request.form.get('nova_senha')
        confirmacao = request.form.get('confirmacao_senha')

        if not check_password_hash(current_user.senha, senha_atual):
            flash('A senha atual inserida está incorreta.', 'danger')
            return redirect(url_for('alterar_senha'))

        if nova_senha != confirmacao:
            flash('A nova senha e a confirmação não coincidem.', 'danger')
            return redirect(url_for('alterar_senha'))

        current_user.senha = generate_password_hash(nova_senha)
        db.session.commit()

        flash('Sua senha foi alterada com sucesso!', 'success')
        
        if current_user.is_admin:
            return redirect(url_for('admin_painel'))
        return redirect(url_for('usuario_painel'))

    return render_template('alterar_senha.html')


# =======================================================
# ROTAS DO FUNCIONÁRIO (PAINEL DE AGENDAMENTO)
# =======================================================

@app.route('/')
@login_required
def usuario_painel():
    if current_user.is_admin:
        return redirect(url_for('admin_painel'))

    agora = datetime.now()
    hoje_str = agora.strftime("%Y-%m-%d")
    hora_atual_str = agora.strftime("%H:%M")

    # Finaliza automaticamente listas ativas de dias anteriores
    listas_antigas = Agendamento.query.filter(Agendamento.data < hoje_str, Agendamento.status == 'ativa').all()
    for item in listas_antigas:
        item.status = 'finalizada'

    # Finaliza horários do dia atual se já passou do último slot
    listas_hoje = Agendamento.query.filter_by(data=hoje_str, status='ativa').all()
    if listas_hoje:
        ultimo_horario = max([h.horario_fim for h in listas_hoje])
        if hora_atual_str >= ultimo_horario:
            for item in listas_hoje:
                item.status = 'finalizada'

    db.session.commit()

    # Busca todas as datas ativas disponíveis
    datas_ativas = db.session.query(Agendamento.data).filter_by(status='ativa').group_by(Agendamento.data).order_by(Agendamento.data).all()
    datas_list = [d[0] for d in datas_ativas]

    data_selecionada = request.args.get('data')
    
    # Se não houver data selecionada na requisição, escolhe automaticamente a primeira data ativa
    if not data_selecionada and datas_list:
        data_selecionada = datas_list[0]

    horarios = []
    if data_selecionada:
        horarios = Agendamento.query.filter_by(data=data_selecionada, status='ativa').order_by(Agendamento.horario_inicio).all()

    return render_template('usuario.html', horarios=horarios, data_selecionada=data_selecionada, datas_ativas=datas_list)


@app.route('/reservar/<int:horario_id>', methods=['POST'])
@login_required
def reservar(horario_id):
    horario = Agendamento.query.get_or_404(horario_id)

    # 1. Verifica se a lista do dia está finalizada
    if horario.status == 'finalizada':
        flash('Esta lista já foi finalizada.', 'warning')
        return redirect(url_for('usuario_painel'))

    # 2. Verifica se o horário específico já foi reservado por outra pessoa
    if horario.usuario_id is not None:
        flash('Ops! Este horário acabou de ser reservado por outra pessoa.', 'warning')
        return redirect(url_for('usuario_painel', data=horario.data))

    # 3. Restrição: Verifica se o usuário já possui outro horário reservado na mesma data
    ja_reservou_hoje = Agendamento.query.filter_by(
        data=horario.data, 
        usuario_id=current_user.id
    ).first()

    if ja_reservou_hoje:
        flash(f'Você já tem um horário reservado para o dia {horario.data} ({ja_reservou_hoje.horario_inicio} às {ja_reservou_hoje.horario_fim}). Cada usuário só pode agendar 1 horário por dia.', 'danger')
        return redirect(url_for('usuario_painel', data=horario.data))

    # Realiza a reserva
    horario.usuario_id = current_user.id
    db.session.commit()
    
    flash('Horário reservado com sucesso!', 'success')
    return redirect(url_for('usuario_painel', data=horario.data))


@app.route('/cancelar/<int:horario_id>', methods=['POST'])
@login_required
def cancelar_reserva(horario_id):
    horario = Agendamento.query.get_or_404(horario_id)

    if horario.usuario_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para cancelar este horário.', 'danger')
        return redirect(url_for('usuario_painel', data=horario.data))

    horario.usuario_id = None
    db.session.commit()

    flash('Reserva cancelada com sucesso.', 'info')
    return redirect(url_for('usuario_painel', data=horario.data))


# =======================================================
# ROTAS DO ADMIN / MASSAGISTA
# =======================================================

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_painel():
    if not current_user.is_admin:
        flash('Acesso negado: área restrita.', 'danger')
        return redirect(url_for('usuario_painel'))

    if request.method == 'POST':
        data = request.form.get('data')
        hora_inicio = request.form.get('hora_inicio')
        hora_fim = request.form.get('hora_fim')
        tem_almoco = 'tem_almoco' in request.form
        inicio_almoco = request.form.get('inicio_almoco') if tem_almoco else None
        fim_almoco = request.form.get('fim_almoco') if tem_almoco else None

        slots = gerar_slots_massagem(hora_inicio, hora_fim, tem_almoco, inicio_almoco, fim_almoco)

        # Remove agendamentos pré-existentes na mesma data
        Agendamento.query.filter_by(data=data).delete()

        for slot in slots:
            novo_agendamento = Agendamento(
                data=data,
                horario_inicio=slot['inicio'],
                horario_fim=slot['fim'],
                status='ativa',
                usuario_id=None
            )
            db.session.add(novo_agendamento)
            
        db.session.commit()
        flash(f'Agenda criada/liberada para o dia {data} com sucesso!', 'success')
        return redirect(url_for('admin_painel', data=data))

    todas_datas = db.session.query(Agendamento.data).group_by(Agendamento.data).order_by(Agendamento.data.desc()).all()
    lista_datas = [d[0] for d in todas_datas]

    data_selecionada = request.args.get('data')
    if not data_selecionada and lista_datas:
        data_selecionada = lista_datas[0]

    horarios = []
    texto_whatsapp = ""
    status_lista = "ativa"

    if data_selecionada:
        horarios = Agendamento.query.filter_by(data=data_selecionada).order_by(Agendamento.horario_inicio).all()
        if horarios:
            status_lista = horarios[0].status

        linhas_texto = [f"💆‍♂️ *LISTA DE MASSAGEM - DIA {data_selecionada}* 💆‍♀️\n"]
        for h in horarios:
            nome_reserva = h.usuario.nome if h.usuario else "LIVRE"
            linhas_texto.append(f"⏰ {h.horario_inicio} às {h.horario_fim} - {nome_reserva}")
        texto_whatsapp = "\n".join(linhas_texto)

    return render_template('admin.html', horarios=horarios, data_selecionada=data_selecionada, datas=lista_datas, texto_whatsapp=texto_whatsapp, status_lista=status_lista)


@app.route('/admin/finalizar/<data>', methods=['POST'])
@login_required
def finalizar_lista(data):
    if not current_user.is_admin:
        return redirect(url_for('usuario_painel'))

    Agendamento.query.filter_by(data=data).update({'status': 'finalizada'})
    db.session.commit()

    flash(f'Lista do dia {data} finalizada e arquivada com sucesso!', 'info')
    return redirect(url_for('admin_painel', data=data))


@app.route('/admin/resetar-senha-usuario', methods=['POST'])
@login_required
def resetar_senha_usuario():
    if not current_user.is_admin:
        flash('Acesso negado: apenas a massagista pode realizar essa ação.', 'danger')
        return redirect(url_for('usuario_painel'))

    matricula = request.form.get('matricula', '').upper().strip()
    usuario = Usuario.query.filter_by(matricula=matricula).first()

    if not usuario:
        flash(f'Usuário com matrícula "{matricula}" não foi encontrado.', 'danger')
        return redirect(url_for('admin_painel'))

    usuario.senha = generate_password_hash('123456')
    db.session.commit()

    flash(f'Senha do usuário {usuario.nome} (Matrícula: {usuario.matricula}) redefinida com sucesso para: 123456', 'success')
    return redirect(url_for('admin_painel'))


@app.route('/admin/relatorio/<data>')
@login_required
def gerar_relatorio(data):
    if not current_user.is_admin:
        return redirect(url_for('usuario_painel'))

    horarios = Agendamento.query.filter_by(data=data).order_by(Agendamento.horario_inicio).all()
    return render_template('relatorio.html', horarios=horarios, data=data)


def inicializar_banco():
    with app.app_context():
        db.create_all()
        admin = Usuario.query.filter_by(matricula='ADMIN').first()
        if not admin:
            admin_senha = generate_password_hash('admin123')
            novo_admin = Usuario(nome='Massagista (Admin)', matricula='ADMIN', senha=admin_senha, is_admin=True)
            db.session.add(novo_admin)
            db.session.commit()
            print("Conta Admin recriada (Matrícula: ADMIN | Senha: admin123)")

if __name__ == '__main__':
    inicializar_banco()
    app.run(debug=True)
