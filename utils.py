from datetime import datetime, timedelta

def gerar_slots_massagem(hora_inicio_str, hora_fim_str, tem_almoco=False, inicio_almoco_str=None, fim_almoco_str=None):
    """
    Gera uma lista de horários de 20 minutos ignorando o período de almoço se houver.
    
    Formatos esperados para as horas: 'HH:MM' (ex: '09:00', '16:00')
    """
    formato_hora = "%H:%M"
    duracao_slot = timedelta(minutes=20)
    
    # Converter strings para objetos datetime
    atual = datetime.strptime(hora_inicio_str, formato_hora)
    fim_dia = datetime.strptime(hora_fim_str, formato_hora)
    
    if tem_almoco and inicio_almoco_str and fim_almoco_str:
        inicio_almoco = datetime.strptime(inicio_almoco_str, formato_hora)
        fim_almoco = datetime.strptime(fim_almoco_str, formato_hora)
    else:
        inicio_almoco = None
        fim_almoco = None

    slots = []

    # Loop para criar as "caixas" de 20 minutos
    while atual + duracao_slot <= fim_dia:
        proximo = atual + duracao_slot
        
        # Verificar se o horário atual cai dentro do intervalo de almoço
        no_almoco = False
        if tem_almoco:
            # Se o início do slot for entre o inicio e o fim do almoço
            if inicio_almoco <= atual < fim_almoco:
                no_almoco = True

        if not no_almoco:
            # Adiciona o slot formatado ex: "09:00 - 09:20"
            slots.append({
                "inicio": atual.strftime(formato_hora),
                "fim": proximo.strftime(formato_hora)
            })
            atual = proximo
        else:
            # Se estiver no almoço, pula direto para o fim do almoço
            atual = fim_almoco

    return slots

# ==========================================
# TESTANDO A LÓGICA (Exemplo prático)
# ==========================================

# Exemplo: Das 09:00 às 16:00, com almoço das 12:00 às 13:00
horarios_disponiveis = gerar_slots_massagem(
    hora_inicio_str="09:00",
    hora_fim_str="16:00",
    tem_almoco=True,
    inicio_almoco_str="12:00",
    fim_almoco_str="13:00"
)

# Exibindo o resultado
for slot in horarios_disponiveis:
    print(f"Slot disponível: {slot['inicio']} às {slot['fim']}")