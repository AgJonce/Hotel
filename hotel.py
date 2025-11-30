import os
import sqlite3
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
from st_aggrid import AgGrid, GridOptionsBuilder
import io
import base64
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import urllib.parse

conn = sqlite3.connect("hotel.db", check_same_thread=False)
cursor = conn.cursor()

# Tabela de produtos em estoque
cursor.execute("""
CREATE TABLE IF NOT EXISTS estoque (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    categoria TEXT,
    unidade TEXT,
    quantidade INTEGER DEFAULT 0,
    valor_unitario REAL DEFAULT 0,
    status TEXT,
    observacao TEXT,
    estoque_minimo INTEGER DEFAULT 0,
    estoque_maximo INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS movimentacoes_estoque (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER,
    tipo TEXT,
    quantidade INTEGER,
    data TEXT,
    hora TEXT,
    valor_total REAL,
    observacao TEXT,
    FOREIGN KEY(produto_id) REFERENCES estoque(id)
)
""")
conn.commit()

cursor.execute('''
CREATE TABLE IF NOT EXISTS arrumacoes_itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    arrumacao_id INTEGER,
    produto_id INTEGER,
    quantidade INTEGER,
    valor_unitario REAL,
    valor_total REAL,
    data TEXT,
    hora TEXT,
    FOREIGN KEY(arrumacao_id) REFERENCES arrumacoes(id),
    FOREIGN KEY(produto_id) REFERENCES estoque(id)
)
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        usuario TEXT UNIQUE,
        senha TEXT,
        funcao TEXT
    );
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS hospedes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    cpf TEXT,
    data_nascimento TEXT,
    documento TEXT,
    endereco TEXT,
    telefone TEXT,
    cidade TEXT,
    placa TEXT,
    rg TEXT
)
''')

# Criar tabela de produtos
cursor.execute('''
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    preco REAL,
    quantidade INTEGER
)
''')

# Criar tabela de funcionários
cursor.execute('''
CREATE TABLE IF NOT EXISTS funcionarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    funcao TEXT,
    status TEXT
)
''')

# Criar tabela de arrumações
cursor.execute('''
CREATE TABLE IF NOT EXISTS arrumacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    funcao TEXT,
    quarto TEXT,
    status TEXT,
    data TEXT,
    hora TEXT,
    diferenca_tempo TEXT,
    tempo_previsto TEXT,
    observacao TEXT,
    tempo_gasto TEXT
)
''')

# Criar tabela de reservas
cursor.execute("""
CREATE TABLE IF NOT EXISTS reservas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    cpf TEXT,
    data_entrada TEXT,
    data_saida TEXT,
    valor TEXT,
    quarto TEXT,
    status TEXT DEFAULT 'Ativa',
    motivo_cancelamento TEXT
)
""")

# Criar tabela de quartos
cursor.execute('''
CREATE TABLE IF NOT EXISTS quartos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quarto TEXT,
    status TEXT
)
''')

# Tabela de produtos em estoque
cursor.execute("""
CREATE TABLE IF NOT EXISTS estoquelj (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    categoria TEXT,
    unidade TEXT,
    quantidade INTEGER DEFAULT 0,
    valor_unitario REAL DEFAULT 0,
    status TEXT,
    observacao TEXT,
    codigo_barras TEXT,
    estoque_minimo INTEGER DEFAULT 0,
    estoque_maximo INTEGER DEFAULT 0
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS comunicados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mensagem TEXT,
    destinatario TEXT,
    data TEXT,
    hora TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS movimentacoes_estoquelj (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER,
    tipo TEXT,
    cliente TEXT,
    quarto TEXT,
    quantidade INTEGER,
    data TEXT,
    hora TEXT,
    valor_total REAL,
    observacao TEXT,
    FOREIGN KEY(produto_id) REFERENCES estoque(id)
)
""")

# Criar tabela de produtos
cursor.execute('''
CREATE TABLE IF NOT EXISTS produtoslj (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    preco REAL,
    quantidade INTEGER
)
''')
# Popula os quartos se estiver vazio
cursor.execute("SELECT COUNT(*) FROM quartos")
if cursor.fetchone()[0] == 0:
    for andar in range(8):
        for numero in range(10):
            quarto = f"{andar+1}-{numero+1}"
            cursor.execute("INSERT INTO quartos (quarto, status) VALUES (?, ?)", (quarto, "Livre"))
    conn.commit()

conn.commit()

def main():
    st.set_page_config(page_title="Sistema de Hotelaria", page_icon="🏨", layout="wide")
    st.title("🏨 Sistema de Hotelaria")
    st.markdown("---")

    if "usuario_logado" not in st.session_state:
        st.warning("Faça login para acessar o sistema.")
        login()
        return

    funcao = st.session_state.get("funcao_usuario", "")
    st.sidebar.success(f"👤 Usuário: {st.session_state['usuario_logado']}")
    st.sidebar.info(f"🔐 Função: {funcao}")

    # Menus por função
    if funcao == "Administrador":
        menu = [
            "Reservas 🛎️",
            "Recepção 🔔",
            "Governança 🧹",
            "Dashboard 📊",
            "👨‍🔧 Cadastro de Funcionário",
            "Contabilidade 💰",
            "Lojinha 🛍️",
            "➕ Cadastrar Usuário"
        ]
    elif funcao == "Recepcionista":
        menu = ["Reservas 🛎️", "Recepção 🔔"]
    elif funcao == "Financeiro":
        menu = ["Contabilidade 💰"]
    elif funcao == "Estoquista":
        menu = ["Governança 🧹", "Lojinha 🛍️"]
    elif funcao == "Governança":
        menu = ["Governança 🧹"]
    else:
        st.error("❌ Função não reconhecida. Contate o administrador.")
        return

    escolha = st.sidebar.selectbox("📋 Menu", menu + ["🔓 Logout"])

    # Mapeamento de funcionalidades
    if escolha == "Dashboard 📊":
        dashboard()
    elif escolha == "👨‍🔧 Cadastro de Funcionário":
        cadastrar_funcionario()
    elif escolha == "Contabilidade 💰":
        opcao = st.sidebar.radio("🧰 Contas - Módulos:", [
            "🧹 Contabilidade",
            "📦 Financeiro",
        ])
        if opcao == "🧹 Contabilidade":
            modulo_contabil()
        elif opcao == "📦 Financeiro":
            modulo_financeiro()
    elif escolha == "➕ Cadastrar Usuário":
        cadastrar_usuario()

    elif escolha == "Governança 🧹":
        opcao = st.sidebar.radio("🧰 Governança - Módulos:", [
            "🧹 Arrumação",
            "📦 Cadastrar Produto",
            "📥 Entrada de Produto",
            "📤 Saída de Produto",
            "🏷️ Almoxarifado",
            "📝 Cadastro de Hospedes ",
            "🛏️ Quartos "
        ])
        if opcao == "🧹 Arrumação":
            arrumacao()
        elif opcao == "📦 Cadastrar Produto":
            cadastrar_produtoam()
        elif opcao == "📥 Entrada de Produto":
            entrada_produtoam()
        elif opcao == "📤 Saída de Produto":
            saida_produtoam()
        elif opcao == "🏷️ Almoxarifado":
            modulo_almoxarifado()
        elif opcao == "📝 Cadastro de Hospedes ":
            cadastrar_hospede()
        elif opcao == "🛏️ Quartos ":
            mostrar_ocupacao_quartos()

    elif escolha == "Recepção 🔔":
        opcao = st.sidebar.radio("🧰 Recepção - Módulos:", [
            "Cadastrar Produto",
            "Entrada de Produto",
            "Saída de Produto",
            "Almoxarifado",
            "Check in ",
            "Consulta Reservas",
            "Menssagens ",
            "Estadia "
        ])
        if opcao == "Cadastrar Produto":
            cadastrar_produto()
        elif opcao == "Entrada de Produto":
            entrada_produto()
        elif opcao == "Saída de Produto":
            saida_produto()
        elif opcao == "Almoxarifado":
            modulo_almoxarifado()
        elif opcao == "Check in ":
            gerenciar_ocupacoes()
        elif opcao == "Consulta Reservas":
            consultar_reserva()
        elif opcao == "Menssagens ":
            mensagens()
        elif opcao == "Estadia ":
            emitir_estadia()

    elif escolha == "Reservas 🛎️":
        opcao = st.sidebar.radio("🧰 Reservas - Módulos:", [
            "📝 Agendar Estadia",
            "📖 Histórico de Estadia",
            "🧾 Detalhes de Reservas",
            "🔁 Reagendar Estadia",
            "❌ Cancelar Reserva",
            "📝 Cadastro de Hospedes ",
            "🛏️ Quartos "
        ])
        if opcao == "📝 Agendar Estadia":
            agendar_estadia()
        elif opcao == "📖 Histórico de Estadia":
            historico_estadias()
        elif opcao == "🧾 Detalhes de Reservas":
            detalhes_reservas()
        elif opcao == "🔁 Reagendar Estadia":
            reagendar_estadia()
        elif opcao == "❌ Cancelar Reserva":
            cancelar_reserva()
        elif opcao == "📝 Cadastro de Hospedes ":
            cadastrar_hospede()
        elif opcao == "🛏️ Quartos ":
            mostrar_ocupacao_quartos()

    elif escolha == "🔓 Logout":
        st.session_state.clear()
        st.rerun()

def login():
    st.subheader("🔐 Login no Sistema")

    with st.form("form_login"):
        usuario = st.text_input("👤 Usuário")
        senha = st.text_input("🔑 Senha", type="password")
        entrar = st.form_submit_button("Entrar")

    if entrar:
        if usuario and senha:
            cursor.execute("SELECT * FROM usuarios WHERE usuario = ? AND senha = ?", (usuario, senha))
            resultado = cursor.fetchone()
            if resultado:
                st.session_state["usuario_logado"] = usuario
                st.session_state["funcao_usuario"] = resultado[4]  # índice 4 = função
                st.success("✅ Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("🚫 Usuário ou senha inválidos.")
        else:
            st.warning("⚠️ Preencha todos os campos.")

    st.markdown("---")
    if st.button("➕ Criar Novo Usuário"):
        st.session_state["tela_cadastro_usuario"] = True
        st.rerun()

    # Exibe a tela de cadastro se ativada
    if st.session_state.get("tela_cadastro_usuario"):
        cadastrar_usuario()

def cadastrar_usuario():
    st.subheader("➕ Cadastrar Novo Usuário")

    with st.form("form_cadastro_usuario", clear_on_submit=True):
        nome = st.text_input("Nome Completo")
        usuario = st.text_input("Nome de Usuário")
        senha = st.text_input("Senha", type="password")
        funcao = st.selectbox("Função", [
            "Administrador",
            "Recepcionista",
            "Governança",
            "Limpeza",
            "Financeiro",
            "Estoquista"
        ])

        cadastrar = st.form_submit_button("Cadastrar")

        if cadastrar:
            if nome and usuario and senha and funcao:
                try:
                    cursor.execute("""
                        INSERT INTO usuarios (nome, usuario, senha, funcao)
                        VALUES (?, ?, ?, ?)
                    """, (nome, usuario, senha, funcao))
                    conn.commit()
                    st.success("✅ Usuário cadastrado com sucesso.")
                except sqlite3.IntegrityError:
                    st.error("🚫 Nome de usuário já existe.")
            else:
                st.warning("⚠️ Preencha todos os campos.")
def cadastrar_produtoam():
    st.title("📦 Cadastrar Produto")
    with st.form("form_cadastro_produto", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("📛 Nome do Produto")
            categoria = st.selectbox("📂 Categoria", [
                "🧽 Limpeza", "🧻 Higiene", "🖋️ Escritório", "🛏️ Cama", "🛁 Banho",
                "🧰 Manutenção", "🥣 Cozinha", "🍽️ Utensílios", "🧴 Cosméticos",
                "📱 Eletrônicos", "🪑 Mobiliário", "🚪 Portaria", "🌿 Jardinagem",
                "💡 Elétrica", "🚰 Hidráulica", "🔧 Ferramentas", "📦 Outros"
            ])
            unidade = st.selectbox("📏 Unidade", ["un", "kg", "L", "pacote", "cx"])
            estoque_minimo = st.number_input("📉 Estoque Mínimo", min_value=0)
        with col2:
            quantidade = st.number_input("📦 Quantidade Inicial", min_value=0)
            valor = st.number_input("💰 Valor Unitário (R$)", min_value=0.0, format="%.2f")
            estoque_maximo = st.number_input("📈 Estoque Máximo", min_value=0)
            status = st.selectbox("🔘 Status", ["✅ Ativo", "⛔ Inativo"])
        observacao = st.text_area("📝 Observações", height=80)

        if st.form_submit_button("✅ Cadastrar Produto"):
            if nome.strip() == "":
                st.warning("⚠️ Preencha o nome do produto.")
            else:
                cursor.execute("""
                INSERT INTO estoque (nome, categoria, unidade, quantidade, valor_unitario, status, observacao, estoque_minimo, estoque_maximo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (nome, categoria, unidade, quantidade, valor, status, observacao, estoque_minimo, estoque_maximo))
                conn.commit()
                st.success("✅ Produto cadastrado com sucesso!")

# -------------------- SAÍDA DE PRODUTO --------------------
def saida_produtoam():
    st.title("📤 Saída de Produto")

    categorias = [row[0] for row in cursor.execute("SELECT DISTINCT categoria FROM estoque").fetchall()]
    categoria_sel = st.selectbox("📂 Filtrar por Categoria", ["Selecionar Categoria..."] + categorias)

    if categoria_sel == "Selecionar Categoria...":
        st.info("👈 Por favor, selecione uma categoria para continuar.")
        return

    produtos = cursor.execute("SELECT id, nome FROM estoque WHERE categoria = ? AND quantidade > 0", (categoria_sel,)).fetchall()

    if not produtos:
        st.info("📭 Nenhum produto com estoque disponível nesta categoria.")
        return

    produto_dict = {nome: pid for pid, nome in produtos}
    nome_sel = st.selectbox("🛒 Produto", ["Selecionar Produto..."] + list(produto_dict.keys()))

    if nome_sel == "Selecionar Produto...":
        st.info("👈 Por favor, selecione um produto para registrar a saída.")
        return

    produto_id = produto_dict[nome_sel]

    dados = cursor.execute("""
        SELECT quantidade, valor_unitario, unidade, categoria, estoque_minimo
        FROM estoque WHERE id = ?
    """, (produto_id,)).fetchone()

    qtd, valor, unidade, categoria, min_estoque = dados

    st.markdown(f"""
    <div style='padding:10px; border:1px solid #DDD; border-radius:10px; background-color:#F9F9F9'>
        <b>📦 Quantidade disponível:</b> <span style='color:{'red' if qtd <= min_estoque else 'green'}'>{qtd} {unidade}</span><br>
        <b>📂 Categoria:</b> {categoria}<br>
        <b>💰 Valor Unitário:</b> R$ {valor:.2f}<br>
        {"⚠️ <b>Estoque abaixo do mínimo!</b>" if qtd <= min_estoque else ""}
    </div>
    """, unsafe_allow_html=True)

    with st.form("form_saida_produto", clear_on_submit=True):
        qtd_saida = st.number_input("🔻 Quantidade para saída", min_value=1, max_value=qtd)
        observacao = st.text_area("📝 Observação (opcional)")

        enviar = st.form_submit_button("📤 Registrar Saída")

        if enviar:
            nova_qtd = qtd - qtd_saida
            total = qtd_saida * valor
            data = datetime.now().strftime("%Y-%m-%d")
            hora = datetime.now().strftime("%H:%M:%S")

            try:
                # Atualiza estoque
                cursor.execute("UPDATE estoque SET quantidade = ? WHERE id = ?", (nova_qtd, produto_id))

                # Registra movimentação
                cursor.execute("""
                    INSERT INTO movimentacoes_estoque (produto_id, tipo, quantidade, data, hora, valor_total, observacao)
                    VALUES (?, 'Saída', ?, ?, ?, ?, ?)
                """, (produto_id, qtd_saida, data, hora, total, observacao))

                conn.commit()
                st.success(f"✅ Saída registrada com sucesso para o produto **{nome_sel}**!")
            except Exception as e:
                st.error(f"❌ Erro ao registrar saída: {e}")

# -------------------- ALMOXARIFADO --------------------
def modulo_almoxarifadoam():
    st.title("🏷️ Almoxarifado - Itens em Estoque")

    # 🔍 Filtros
    with st.expander("🔍 Filtros"):
        col1, col2 = st.columns(2)
        filtro_nome = col1.text_input("🔎 Buscar por nome:")
        categorias = ["Todas"] + [row[0] for row in cursor.execute("SELECT DISTINCT categoria FROM estoquelj").fetchall()]
        filtro_categoria = col2.selectbox("📂 Filtrar por Categoria", categorias)

    # 📦 Consulta com filtros
    query = """
        SELECT id, nome, categoria, unidade, quantidade, estoque_minimo,
               estoque_maximo, valor_unitario, status, observacao
        FROM estoquelj WHERE quantidade > 0
    """
    params = []

    if filtro_nome:
        query += " AND nome LIKE ?"
        params.append(f"%{filtro_nome}%")

    if filtro_categoria != "Todas":
        query += " AND categoria = ?"
        params.append(filtro_categoria)

    query += " ORDER BY nome ASC"
    produtos = cursor.execute(query, tuple(params)).fetchall()

    if not produtos:
        st.info("📭 Nenhum item encontrado com os filtros aplicados.")
        return

    # 🧾 Exibição de produtos em "cartões" visuais
    st.markdown("### 🗃️ Detalhamento por Produto")
    for prod in produtos:
        id_, nome, categoria, unidade, qtd, min_estoque, max_estoque, valor, status, obs = prod
        cor_status = "#2ecc71" if status == "✅ Ativo" else "#e74c3c"
        cor_fundo = "#f0fdf4" if qtd > min_estoque else "#fff0f0"
        cor_qtd = "#2e8b57" if qtd > min_estoque else "#e60000"
        icone_categoria = categoria.split()[0] if categoria else "📦" 
        
        st.markdown(f"""
        <div style="background-color:{cor_fundo}; padding:15px; border:1px solid #ccc; border-radius:10px; margin-bottom:15px;">
            <h4 style="margin-bottom:10px;">{icone_categoria} <strong>{nome}</strong></h4>
            <div style="line-height: 1.7;">
                <b>📂 Categoria:</b> {categoria} &nbsp;&nbsp;&nbsp;
                <b>📏 Unidade:</b> {unidade}<br>
                <b>🔢 Quantidade:</b> <span style="color:{cor_qtd}">{qtd}</span> &nbsp;&nbsp;&nbsp;
                <b>📊 Mín/Máx:</b> {min_estoque}/{max_estoque}<br>
                <b>💰 Valor Unitário:</b> R$ {valor:.2f} &nbsp;&nbsp;&nbsp;
                <b>🔘 Status:</b> <span style="color:{cor_status}">{status}</span><br>
                {"<b>📝 Observações:</b> " + obs if obs.strip() else ""}
                {"<div style='color:red; margin-top:8px;'><b>⚠️ Estoque abaixo do mínimo!</b></div>" if qtd <= min_estoque else ""}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 📊 Tabela Estilizada com Destaque
    st.markdown("### 📋 Visão Geral dos Itens em Tabela")

    df = pd.read_sql_query("""
        SELECT nome AS Produto, categoria AS Categoria, unidade AS Unidade,
            quantidade AS Quantidade, estoque_minimo AS 'Estoque Mínimo',
            estoque_maximo AS 'Estoque Máximo', valor_unitario AS 'Valor Unitário (R$)', status AS Status
        FROM estoque
        WHERE quantidade > 0
        ORDER BY nome ASC
    """, conn)

    def destacar_estoque_baixo(row):
        return ['background-color: #ffe6e6' if row['Quantidade'] <= row['Estoque Mínimo'] else '' for _ in row]

    st.dataframe(df.style.apply(destacar_estoque_baixo, axis=1), use_container_width=True)

    # ⚠️ Alerta para itens críticos
    df_critico = df[df["Quantidade"] <= df["Estoque Mínimo"]]
    if not df_critico.empty:
        st.markdown("### ⚠️ Itens com Estoque Crítico")
        st.dataframe(df_critico.style.apply(highlight, axis=1), use_container_width=True)


# Estilo extra (opcional): função para aplicar destaque amarelo
def highlight(row):
    return ['background-color: #fff3cd'] * len(row)

def entrada_produtoam():
    st.title("📥 Entrada de Produto")

    categorias = [row[0] for row in cursor.execute("SELECT DISTINCT categoria FROM estoque").fetchall()]
    categoria_sel = st.selectbox("📂 Filtrar por Categoria", ["Selecionar Categoria..."] + categorias)

    if categoria_sel == "Selecionar Categoria...":
        st.info("👈 Por favor, selecione uma categoria.")
        return

    produtos = cursor.execute("SELECT id, nome FROM estoque WHERE categoria = ?", (categoria_sel,)).fetchall()

    if not produtos:
        st.info("📭 Nenhum produto disponível nesta categoria.")
        return

    produto_dict = {nome: pid for pid, nome in produtos}
    nome_sel = st.selectbox("🛒 Produto", ["Selecionar Produto..."] + list(produto_dict.keys()))

    if nome_sel == "Selecionar Produto...":
        st.info("👈 Por favor, selecione um produto para entrada.")
        return

    produto_id = produto_dict[nome_sel]

    dados = cursor.execute("""
        SELECT quantidade, valor_unitario, unidade, categoria, estoque_minimo, estoque_maximo
        FROM estoque WHERE id = ?
    """, (produto_id,)).fetchone()

    qtd, valor_unitario, unidade, categoria, min_estoque, max_estoque = dados

    st.markdown(f"""
    <div style='padding:10px; border:1px solid #DDD; border-radius:10px; background-color:#F9F9F9'>
        <b>📦 Quantidade Atual:</b> <span style='color:green'>{qtd} {unidade}</span><br>
        <b>📂 Categoria:</b> {categoria}<br>
        <b>💰 Valor Unitário Atual:</b> R$ {valor_unitario:.2f}<br>
        <b>📊 Estoque Mín/Máx:</b> {min_estoque} / {max_estoque}
    </div>
    """, unsafe_allow_html=True)

    # 🔽 Formulário de entrada
    with st.form("form_entrada_produto", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            qtd_entrada = st.number_input("📥 Quantidade para entrada", min_value=1, step=1)
        with col2:
            novo_valor = st.number_input("💰 Novo valor unitário (opcional)", value=valor_unitario, step=0.01, format="%.2f")

        observacao = st.text_area("📝 Observação (opcional)")

        enviar = st.form_submit_button("✅ Registrar Entrada")

        if enviar:
            nova_qtd = qtd + qtd_entrada
            valor_total = qtd_entrada * novo_valor
            data = datetime.now().strftime("%Y-%m-%d")
            hora = datetime.now().strftime("%H:%M:%S")

            try:
                # Atualiza estoque
                cursor.execute("""
                    UPDATE estoque SET quantidade = ?, valor_unitario = ? WHERE id = ?
                """, (nova_qtd, novo_valor, produto_id))

                # Registra movimentação
                cursor.execute("""
                    INSERT INTO movimentacoes_estoque (produto_id, tipo, quantidade, data, hora, valor_total, observacao)
                    VALUES (?, 'Entrada', ?, ?, ?, ?, ?)
                """, (produto_id, qtd_entrada, data, hora, valor_total, observacao))

                conn.commit()
                st.success(f"✅ Entrada registrada com sucesso para o produto **{nome_sel}**!")
            except Exception as e:
                st.error(f"❌ Erro ao registrar entrada: {e}")
                
def cadastrar_funcionario():
    st.header("👨‍🔧 Cadastro de Funcionário")
    nome = st.text_input("Nome do Funcionário")
    funcao = st.selectbox("Função", ["Arrumação", "Limpeza", "Manutenção", "Recepção"])
    if st.button("Salvar"):
        conn = sqlite3.connect("hotel.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO funcionarios (nome, funcao) VALUES (?, ?)", (nome, funcao))
        conn.commit()
        st.success("Funcionário cadastrado com sucesso!")

def agendar_estadia():
    st.title("🔔 Check-in Rápido")

    with st.form("form_checkin_rapido", clear_on_submit=True):
        # Seleção de hóspede
        hospedes = cursor.execute("SELECT nome FROM hospedes").fetchall()
        nomes_hospedes = ["Selecione um hóspede..."] + [h[0] for h in hospedes]
        nome = st.selectbox("🧑 Nome do hóspede", nomes_hospedes)

        if nome != "Selecione um hóspede...":
            resultado = cursor.execute("SELECT cpf FROM hospedes WHERE nome = ?", (nome,)).fetchone()
            cpf = resultado[0] if resultado else ""
        else:
            cpf = ""

        st.text_input("🆔 CPF", value=cpf, disabled=True)

        # Seleção de quarto
        lista_quartos = [f"{i+1}-{j+1}" for i in range(8) for j in range(10)]
        quarto = st.selectbox("🛏️ Quarto", lista_quartos)

        # Datas
        data_entrada = st.date_input("📅 Data de Entrada", datetime.today())
        data_saida = st.date_input("📅 Data de Saída", datetime.today() + timedelta(days=1))

        # Calcula quantidade de dias
        dias = (data_saida - data_entrada).days
        if dias <= 0:
            dias = 1  # pelo menos 1 diária

        # Valor da diária
        valor_diaria = st.number_input("💵 Valor da diária", min_value=0.0, step=0.01)

        # Total calculado
        valor_total = dias * valor_diaria
        st.info(f"💰 Total da Reserva: R$ {valor_total:.2f} ({dias} diárias)")

        confirmar = st.form_submit_button("✅ Realizar Check-in")

        # Verifica status do quarto
        cursor.execute("SELECT status FROM quartos WHERE quarto = ?", (quarto,))
        resultado = cursor.fetchone()

        if resultado is None:
            st.error(f"❌ O quarto {quarto} não está cadastrado no sistema.")
            return

        status_quarto = resultado[0].strip().lower()
        if status_quarto in ["ocupado", "em uso", "em arrumação", "em limpeza", "bloqueado"]:
            st.warning(f"⚠️ O quarto {quarto} está atualmente com status: {status_quarto.capitalize()}.")
            return

        if confirmar:
            if not nome or not cpf or not quarto or valor_diaria <= 0:
                st.warning("⚠️ Preencha todos os campos obrigatórios.")
            else:
                # Registrar reserva
                cursor.execute("""
                    INSERT INTO reservas (nome, cpf, quarto, data_entrada, data_saida, valor, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (nome, cpf, quarto, data_entrada, data_saida, valor_total, "Ativa"))

                # Atualizar status do quarto
                cursor.execute("UPDATE quartos SET status = ? WHERE quarto = ?", ("Ocupado", quarto))

                conn.commit()
                st.success(f"✅ Reserva registrada para {nome} no quarto {quarto} ({dias} diárias, total R$ {valor_total:.2f}).")

def gerenciar_ocupacoes():
    st.title("🛎️ Gerenciar Check-in e Check-out")

    tipo = st.radio("📌 Selecione o tipo de operação:", ["✅ Check-in", "📤 Check-out"])

    if tipo == "✅ Check-in":
        st.subheader("🔑 Confirmar Check-in")

        reservas_checkin = pd.read_sql_query("""
            SELECT r.id, r.nome, r.cpf, r.quarto, r.data_entrada, r.data_saida, r.valor
            FROM reservas r
            JOIN quartos q ON r.quarto = q.quarto
            WHERE r.status = 'Ativa' AND LOWER(q.status) = 'ocupado'
        """, conn)

        if reservas_checkin.empty:
            st.info("📭 Nenhuma reserva aguardando check-in.")
            return

        nome = st.selectbox("👤 Selecione o hóspede", reservas_checkin["nome"].unique().tolist())
        dados = reservas_checkin[reservas_checkin["nome"] == nome].iloc[0]

        st.markdown(f"""
        - 🧾 **CPF:** `{dados['cpf']}`
        - 🛏️ **Quarto reservado:** `{dados['quarto']}`
        - 📅 **Entrada:** `{pd.to_datetime(dados['data_entrada']).strftime('%d/%m/%Y')}`
        - 📅 **Saída:** `{pd.to_datetime(dados['data_saida']).strftime('%d/%m/%Y')}`
        - 💵 **Valor:** R$ {float(dados['valor']):.2f}
        """)

        if st.button("✅ Confirmar Check-in"):
            cursor.execute("UPDATE reservas SET status = ? WHERE id = ?", ("Ativa", dados["id"]))
            cursor.execute("UPDATE quartos SET status = ? WHERE quarto = ?", ("Em Uso", dados["quarto"]))
            conn.commit()
            st.success(f"🏨 Check-in confirmado para {dados['nome']}. Quarto {dados['quarto']} agora está Em Uso.")
            st.rerun()

    else:
        st.subheader("📤 Confirmar Check-out")

        reservas_checkout = pd.read_sql_query("""
            SELECT r.id, r.nome, r.cpf, r.quarto, r.data_entrada, r.data_saida, r.valor, q.status as status_quarto
            FROM reservas r
            JOIN quartos q ON r.quarto = q.quarto
            WHERE r.status = 'Ativa' AND LOWER(q.status) = 'em uso'
        """, conn)

        if reservas_checkout.empty:
            st.info("📭 Nenhuma hospedagem com quarto em uso para check-out.")
            return

        nome = st.selectbox("👤 Selecione o hóspede", reservas_checkout["nome"].unique().tolist())
        dados = reservas_checkout[reservas_checkout["nome"] == nome].iloc[0]

        st.markdown(f"""
        - 🧾 **CPF:** `{dados['cpf']}`
        - 🛏️ **Quarto:** `{dados['quarto']}`
        - 📅 **Entrada:** `{pd.to_datetime(dados['data_entrada']).strftime('%d/%m/%Y')}`
        - 📅 **Saída:** `{pd.to_datetime(dados['data_saida']).strftime('%d/%m/%Y')}`
        - 💵 **Valor:** R$ {float(dados['valor']):.2f}
        """)

        if st.button("📤 Confirmar Check-out"):
        # Finaliza a reserva e libera o quarto
            cursor.execute("UPDATE reservas SET status = ? WHERE id = ?", ("Finalizada", dados["id"]))
            cursor.execute("UPDATE quartos SET status = ? WHERE quarto = ?", ("Livre", dados["quarto"]))
            conn.commit()
            st.success(f"✅ Check-out realizado com sucesso para {dados['nome']}! Quarto {dados['quarto']} agora está Livre.")
            st.rerun()

# Consultar Reserva
def consultar_reserva():
    st.title("🔍 Consultar Reserva")

    cpf = st.text_input("Digite o CPF do hóspede:").replace(".", "").replace("-", "").replace(" ", "").strip()

    if cpf:
        df = pd.read_sql_query("""
            SELECT nome, cpf, quarto, data_entrada, data_saida, status
            FROM reservas
            WHERE REPLACE(REPLACE(REPLACE(cpf, '.', ''), '-', ''), ' ', '') = ?
            ORDER BY data_entrada DESC
        """, conn, params=(cpf,))

        if df.empty:
            st.info("⚠️ Nenhuma reserva encontrada para este CPF.")
        else:
            # Formata datas
            df["data_entrada"] = pd.to_datetime(df["data_entrada"], errors="coerce").dt.strftime("%d/%m/%Y")
            df["data_saida"] = pd.to_datetime(df["data_saida"], errors="coerce").dt.strftime("%d/%m/%Y")

            # Renomeia colunas para exibição
            df.columns = ["Nome", "CPF", "Quarto", "Check-in", "Check-out", "Status"]

            # Configura o AgGrid
            gb = GridOptionsBuilder.from_dataframe(df)
            gb.configure_pagination()
            gb.configure_side_bar()
            gb.configure_default_column(groupable=True, value=True, editable=False, filter=True)
            grid_options = gb.build()

            AgGrid(df, gridOptions=grid_options, theme="streamlit", height=400, fit_columns_on_grid_load=True)
def agendar_estadia():
    st.title("🔔 Check-in Rápido")

    with st.form("form_checkin_rapido", clear_on_submit=True):
        # Seleção de hóspede
        hospedes = cursor.execute("SELECT nome FROM hospedes").fetchall()
        nomes_hospedes = ["Selecione um hóspede..."] + [h[0] for h in hospedes]
        nome = st.selectbox("🧑 Nome do hóspede", nomes_hospedes)

        if nome != "Selecione um hóspede...":
            resultado = cursor.execute("SELECT cpf FROM hospedes WHERE nome = ?", (nome,)).fetchone()
            cpf = resultado[0] if resultado else ""
        else:
            cpf = ""

        st.text_input("🆔 CPF", value=cpf, disabled=True)

        # Seleção de quarto
        lista_quartos = [f"{i+1}-{j+1}" for i in range(8) for j in range(10)]
        quarto = st.selectbox("🛏️ Quarto", lista_quartos)

        # Datas
        data_entrada = st.date_input("📅 Data de Entrada", datetime.today())
        data_saida = st.date_input("📅 Data de Saída", datetime.today() + timedelta(days=1))

        # Calcula quantidade de dias
        dias = (data_saida - data_entrada).days
        if dias <= 0:
            dias = 1  # pelo menos 1 diária

        # Valor da diária
        valor_diaria = st.number_input("💵 Valor da diária", min_value=0.0, step=0.01)

        # Total calculado
        valor_total = dias * valor_diaria
        st.info(f"💰 Total da Reserva: R$ {valor_total:.2f} ({dias} diárias)")

        confirmar = st.form_submit_button("✅ Realizar Check-in")

        # Verifica status do quarto
        cursor.execute("SELECT status FROM quartos WHERE quarto = ?", (quarto,))
        resultado = cursor.fetchone()

        if resultado is None:
            st.error(f"❌ O quarto {quarto} não está cadastrado no sistema.")
            return

        status_quarto = resultado[0].strip().lower()
        if status_quarto in ["ocupado", "em uso", "em arrumação", "em limpeza", "bloqueado"]:
            st.warning(f"⚠️ O quarto {quarto} está atualmente com status: {status_quarto.capitalize()}.")
            return

        if confirmar:
            if not nome or not cpf or not quarto or valor_diaria <= 0:
                st.warning("⚠️ Preencha todos os campos obrigatórios.")
            else:
                # Registrar reserva
                cursor.execute("""
                    INSERT INTO reservas (nome, cpf, quarto, data_entrada, data_saida, valor, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (nome, cpf, quarto, data_entrada, data_saida, valor_total, "Ativa"))

                # Atualizar status do quarto
                cursor.execute("UPDATE quartos SET status = ? WHERE quarto = ?", ("Ocupado", quarto))

                conn.commit()
                st.success(f"✅ Reserva registrada para {nome} no quarto {quarto} ({dias} diárias, total R$ {valor_total:.2f}).")

def historico_estadias():
    st.header("📖 Histórico de Estadia")
    st.markdown("### 🔍 Filtros de Pesquisa")

    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("🗓️ De:", datetime.now() - timedelta(days=30))
        nome_filtro = st.text_input("🧑 Filtrar por nome")
    with col2:
        data_fim = st.date_input("🗓️ Até:", datetime.now())
        cpf_filtro = st.text_input("🆔 Filtrar por CPF")

    query = """
        SELECT nome, cpf, quarto, data_entrada, data_saida, status, motivo_cancelamento
        FROM reservas
        WHERE date(data_entrada) BETWEEN ? AND ?
    """
    params = [str(data_inicio), str(data_fim)]

    if nome_filtro:
        query += " AND nome LIKE ?"
        params.append(f"%{nome_filtro}%")
    if cpf_filtro:
        query += " AND cpf LIKE ?"
        params.append(f"%{cpf_filtro}%")

    query += " ORDER BY data_entrada DESC"
    df = pd.read_sql_query(query, conn, params=params)

    st.markdown("---")

    if df.empty:
        st.warning("⚠️ Nenhuma estadia encontrada com os filtros aplicados.")
    else:
        st.success(f"✅ {len(df)} estadia(s) encontrada(s) entre {data_inicio.strftime('%d/%m/%Y')} e {data_fim.strftime('%d/%m/%Y')}.")

        st.markdown("### 📋 Visualização das Reservas")

        # Formatar datas
        df["data_entrada"] = pd.to_datetime(df["data_entrada"]).dt.strftime("%d/%m/%Y")
        df["data_saida"] = pd.to_datetime(df["data_saida"]).dt.strftime("%d/%m/%Y")

        # Reorganizar colunas e renomear
        df = df[["nome", "cpf", "quarto", "data_saida", "data_entrada", "status", "motivo_cancelamento"]]
        df.columns = ["Nome", "CPF", "Quarto", "Data Saída", "Data Entrada", "Status", "Motivo Cancelamento"]

        # AgGrid interativa
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_pagination()
        gb.configure_side_bar()
        gb.configure_default_column(groupable=True, value=True, editable=False)
        grid_options = gb.build()

        AgGrid(df, gridOptions=grid_options, theme="streamlit", height=450, fit_columns_on_grid_load=True)

        # Exportar CSV
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Baixar histórico em CSV",
            data=csv,
            file_name=f"historico_estadias_{data_inicio}_{data_fim}.csv",
            mime="text/csv"
        )

# 🔹 3. Consultar detalhes de reservas
def detalhes_reservas():
    st.header("🧾 Detalhes de Reservas")
    busca = st.text_input("🔍 Buscar por CPF ou número do quarto")

    if busca:
        df = pd.read_sql_query("""
            SELECT nome, cpf, quarto, data_entrada, data_saida
            FROM reservas
            WHERE cpf LIKE ? OR quarto LIKE ?
            ORDER BY data_entrada DESC
        """, conn, params=(f"%{busca}%", f"%{busca}%"))

        if df.empty:
            st.warning("Nenhuma reserva encontrada.")
        else:
            st.dataframe(df, use_container_width=True)
    else:
        st.info("Digite um CPF ou número do quarto para buscar.")

def reagendar_estadia():
    st.header("🔁 Reagendar Estadia")

    reservas = cursor.execute("""
        SELECT id, nome, quarto, data_entrada, data_saida, cpf
        FROM reservas
        WHERE status = 'Ativa'
    """).fetchall()

    if not reservas:
        st.info("❌ Nenhuma reserva ativa disponível para reagendamento.")
        return

    opcoes = [f"{r[1]} - Quarto {r[2]} (ID: {r[0]})" for r in reservas]
    selecao = st.selectbox("📋 Selecione uma reserva para reagendar", opcoes)

    if selecao:
        reserva_id = int(selecao.split("ID: ")[-1].replace(")", ""))
        dados = cursor.execute("""
            SELECT nome, cpf, quarto, data_entrada, data_saida 
            FROM reservas WHERE id = ?
        """, (reserva_id,)).fetchone()

        nome, cpf, quarto, antiga_entrada, antiga_saida = dados

        nova_entrada = st.date_input("📅 Novo Check-in", value=pd.to_datetime(antiga_entrada))
        nova_saida = st.date_input("📅 Novo Check-out", value=pd.to_datetime(antiga_saida))
        motivo = st.text_area("✏️ Motivo do Reagendamento", max_chars=300)

        if st.button("🔄 Confirmar Reagendamento"):
            if not motivo.strip():
                st.warning("⚠️ Por favor, informe o motivo do reagendamento.")
                return

            # Atualiza reserva antiga com status e motivo
            cursor.execute("""
                UPDATE reservas 
                SET status = ?, motivo_cancelamento = ?
                WHERE id = ?
            """, ("Reagendada", motivo, reserva_id))

            # Cria nova reserva como ativa
            cursor.execute("""
                INSERT INTO reservas (nome, cpf, data_entrada, data_saida, quarto, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nome, cpf, str(nova_entrada), str(nova_saida), quarto, "Ativa"))

            conn.commit()
            st.success(f"✅ Reserva reagendada com sucesso para {nome} no quarto {quarto} de {nova_entrada.strftime('%d/%m/%Y')} a {nova_saida.strftime('%d/%m/%Y')}.")

def cancelar_reserva():
    st.header("❌ Cancelar Reserva")

    reservas = cursor.execute("""
        SELECT id, nome, quarto, data_entrada, data_saida
        FROM reservas
        WHERE status = 'Ativa'
    """).fetchall()

    if not reservas:
        st.info("✅ Nenhuma reserva ativa disponível para cancelamento.")
        return

    opcoes = [f"{r[1]} - Quarto {r[2]} (ID: {r[0]})" for r in reservas]
    selecao = st.selectbox("📋 Selecione uma reserva para cancelar", opcoes)

    if selecao:
        reserva_id = int(selecao.split("ID: ")[-1].replace(")", ""))
        dados = cursor.execute("SELECT nome, quarto FROM reservas WHERE id = ?", (reserva_id,)).fetchone()
        nome, quarto = dados

        motivo = st.text_area("✏️ Motivo do Cancelamento", max_chars=300)

        if st.button("🚫 Confirmar Cancelamento"):
            if not motivo.strip():
                st.warning("⚠️ Por favor, informe o motivo do cancelamento.")
                return

            # Atualiza status da reserva para "Cancelada" e salva o motivo
            cursor.execute("""
                UPDATE reservas 
                SET status = ?, motivo_cancelamento = ?
                WHERE id = ?
            """, ("Cancelada", motivo, reserva_id))

            # Atualiza o status do quarto para "Livre"
            cursor.execute("""
                UPDATE quartos 
                SET status = 'Livre'
                WHERE quarto = ?
            """, (quarto,))

            conn.commit()
            st.success(f"❌ Reserva cancelada com sucesso. Quarto {quarto} está agora disponível.")
def mostrar_ocupacao_quartos():
    st.subheader("Ocupação dos Quartos")

    # Padronizar os status antes de exibir
    mapeamento_status = {
        "livre": "Livre",
        "ocupado": "Ocupado",
        "em arrumacao": "Em Arrumação",
        "em arrumação": "Em Arrumação",
        "em limpeza": "Em Limpeza",
        "bloqueado": "Bloqueado"
    }

    # Buscar todos os quartos com id e status
    cursor.execute("SELECT id, status FROM quartos")
    quartos = cursor.fetchall()

    # Atualiza status no banco para o padrão correto
    for quarto_id, status in quartos:
        status_formatado = status.strip().lower()
        novo_status = mapeamento_status.get(status_formatado)
        if novo_status and novo_status != status:
            cursor.execute("UPDATE quartos SET status = ? WHERE id = ?", (novo_status, quarto_id))
    conn.commit()

    # Buscar dados atualizados
    cursor.execute("SELECT quarto, status FROM quartos")
    dados = cursor.fetchall()

    if not dados:
        st.warning("Nenhum quarto cadastrado.")
        return

    # Criar DataFrame atualizado
    quartos_df = pd.DataFrame(dados, columns=["Quarto", "Status"])

    # Configurações de mapa
    andares = 8
    quartos_por_andar = 10

    # Mapeamento cores status
    status_dict = {
        "Livre": "green",
        "Ocupado": "red",
        "Em Arrumação": "yellow",
        "Em Limpeza": "orange",
        "Bloqueado": "gray"
    }

    fig = go.Figure()

    for _, row in quartos_df.iterrows():
        andar, numero_quarto = row["Quarto"].split("-")
        x = int(andar) - 1
        y = int(numero_quarto) - 1
        cor = status_dict.get(row["Status"], "blue")

        fig.add_trace(go.Scatter(
            x=[x],
            y=[y],
            mode='markers',
            marker=dict(size=40, color=cor, line=dict(width=2, color='black')),
            text=f"Quarto {row['Quarto']} - {row['Status']}",
            hoverinfo="text",
            name=row['Quarto']
        ))

    fig.update_layout(
        title="Mapa de Ocupação dos Quartos",
        xaxis=dict(
            tickmode='array',
            tickvals=list(range(andares)),
            ticktext=[f"Andar {i+1}" for i in range(andares)],
            title="Andares",
            autorange="reversed"
        ),
        yaxis=dict(
            tickmode='array',
            tickvals=list(range(quartos_por_andar)),
            ticktext=[f"Quarto {i+1}" for i in range(quartos_por_andar)],
            title="Quartos"
        ),
        showlegend=False,
        plot_bgcolor="white",
        height=600,
        width=900,
        hoverlabel=dict(bgcolor="white", font_size=13)
    )

    fig.update_traces(marker=dict(size=35))
    st.plotly_chart(fig)

    # Selecionar quarto e mostrar detalhes
    quarto_selecionado = st.selectbox("Selecione um Quarto para Detalhes", quartos_df["Quarto"].tolist())
    if quarto_selecionado:
        quarto_info = quartos_df[quartos_df["Quarto"] == quarto_selecionado].iloc[0]
        st.write(f"Detalhes do Quarto {quarto_selecionado}:")
        st.write(f"Status: {quarto_info['Status']}")

def atualizar_status_quarto(quarto):
    cursor.execute("UPDATE quartos SET status = ? WHERE quarto = ?", ("Ocupado", quarto))
    conn.commit()
def cadastrar_hospede():
    st.subheader("📝 Cadastro de Hóspede 🏨")

    with st.form(key="form_hospede", clear_on_submit=True):
        nome = st.text_input("🧑 Nome")
        data = st.date_input("📅 Data de Nascimento")
        documento = st.text_input("🆔 Documento")
        telefone = st.text_input("📞 Telefone")
        cpf = st.text_input("🆔 CPF")
        placa = st.text_input("🚗 Placa do Veículo")
        cadastrar = st.form_submit_button("✅ Cadastrar")

        if cadastrar:
            cursor.execute('''
                INSERT INTO hospedes (nome, documento, telefone, cpf, placa, data_nascimento)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (nome, documento, telefone, cpf, placa, data))
            conn.commit()
            st.success(f"🛎️ Hóspede {nome} cadastrado com sucesso ✅")


def historico_estadias():
    st.header("📖 Histórico de Estadia")
    st.markdown("### 🔍 Filtros de Pesquisa")

    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("🗓️ De:", datetime.now() - timedelta(days=30))
        nome_filtro = st.text_input("🧑 Filtrar por nome")
    with col2:
        data_fim = st.date_input("🗓️ Até:", datetime.now())
        cpf_filtro = st.text_input("🆔 Filtrar por CPF")

    query = """
        SELECT nome, cpf, quarto, data_entrada, data_saida, status, motivo_cancelamento
        FROM reservas
        WHERE date(data_entrada) BETWEEN ? AND ?
    """
    params = [str(data_inicio), str(data_fim)]

    if nome_filtro:
        query += " AND nome LIKE ?"
        params.append(f"%{nome_filtro}%")
    if cpf_filtro:
        query += " AND cpf LIKE ?"
        params.append(f"%{cpf_filtro}%")

    query += " ORDER BY data_entrada DESC"
    df = pd.read_sql_query(query, conn, params=params)

    st.markdown("---")

    if df.empty:
        st.warning("⚠️ Nenhuma estadia encontrada com os filtros aplicados.")
    else:
        st.success(f"✅ {len(df)} estadia(s) encontrada(s) entre {data_inicio.strftime('%d/%m/%Y')} e {data_fim.strftime('%d/%m/%Y')}.")

        st.markdown("### 📋 Visualização das Reservas")

        # Formatar datas
        df["data_entrada"] = pd.to_datetime(df["data_entrada"]).dt.strftime("%d/%m/%Y")
        df["data_saida"] = pd.to_datetime(df["data_saida"]).dt.strftime("%d/%m/%Y")

        # Reorganizar colunas e renomear
        df = df[["nome", "cpf", "quarto", "data_saida", "data_entrada", "status", "motivo_cancelamento"]]
        df.columns = ["Nome", "CPF", "Quarto", "Data Saída", "Data Entrada", "Status", "Motivo Cancelamento"]

        # AgGrid interativa
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_pagination()
        gb.configure_side_bar()
        gb.configure_default_column(groupable=True, value=True, editable=False)
        grid_options = gb.build()

        AgGrid(df, gridOptions=grid_options, theme="streamlit", height=450, fit_columns_on_grid_load=True)

        # Exportar CSV
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Baixar histórico em CSV",
            data=csv,
            file_name=f"historico_estadias_{data_inicio}_{data_fim}.csv",
            mime="text/csv"
        )

# 🔹 3. Consultar detalhes de reservas
def detalhes_reservas():
    st.header("🧾 Detalhes de Reservas")
    busca = st.text_input("🔍 Buscar por CPF ou número do quarto")

    if busca:
        df = pd.read_sql_query("""
            SELECT nome, cpf, quarto, data_entrada, data_saida
            FROM reservas
            WHERE cpf LIKE ? OR quarto LIKE ?
            ORDER BY data_entrada DESC
        """, conn, params=(f"%{busca}%", f"%{busca}%"))

        if df.empty:
            st.warning("Nenhuma reserva encontrada.")
        else:
            st.dataframe(df, use_container_width=True)
    else:
        st.info("Digite um CPF ou número do quarto para buscar.")

def reagendar_estadia():
    st.header("🔁 Reagendar Estadia")

    reservas = cursor.execute("""
        SELECT id, nome, quarto, data_entrada, data_saida, cpf
        FROM reservas
        WHERE status = 'Ativa'
    """).fetchall()

    if not reservas:
        st.info("❌ Nenhuma reserva ativa disponível para reagendamento.")
        return

    opcoes = [f"{r[1]} - Quarto {r[2]} (ID: {r[0]})" for r in reservas]
    selecao = st.selectbox("📋 Selecione uma reserva para reagendar", opcoes)

    if selecao:
        reserva_id = int(selecao.split("ID: ")[-1].replace(")", ""))
        dados = cursor.execute("""
            SELECT nome, cpf, quarto, data_entrada, data_saida 
            FROM reservas WHERE id = ?
        """, (reserva_id,)).fetchone()

        nome, cpf, quarto, antiga_entrada, antiga_saida = dados

        nova_entrada = st.date_input("📅 Novo Check-in", value=pd.to_datetime(antiga_entrada))
        nova_saida = st.date_input("📅 Novo Check-out", value=pd.to_datetime(antiga_saida))
        motivo = st.text_area("✏️ Motivo do Reagendamento", max_chars=300)

        if st.button("🔄 Confirmar Reagendamento"):
            if not motivo.strip():
                st.warning("⚠️ Por favor, informe o motivo do reagendamento.")
                return

            # Atualiza reserva antiga com status e motivo
            cursor.execute("""
                UPDATE reservas 
                SET status = ?, motivo_cancelamento = ?
                WHERE id = ?
            """, ("Reagendada", motivo, reserva_id))

            # Cria nova reserva como ativa
            cursor.execute("""
                INSERT INTO reservas (nome, cpf, data_entrada, data_saida, quarto, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nome, cpf, str(nova_entrada), str(nova_saida), quarto, "Ativa"))

            conn.commit()
            st.success(f"✅ Reserva reagendada com sucesso para {nome} no quarto {quarto} de {nova_entrada.strftime('%d/%m/%Y')} a {nova_saida.strftime('%d/%m/%Y')}.")

def cancelar_reserva():
    st.header("❌ Cancelar Reserva")

    reservas = cursor.execute("""
        SELECT id, nome, quarto, data_entrada, data_saida
        FROM reservas
        WHERE status = 'Ativa'
    """).fetchall()

    if not reservas:
        st.info("✅ Nenhuma reserva ativa disponível para cancelamento.")
        return

    opcoes = [f"{r[1]} - Quarto {r[2]} (ID: {r[0]})" for r in reservas]
    selecao = st.selectbox("📋 Selecione uma reserva para cancelar", opcoes)

    if selecao:
        reserva_id = int(selecao.split("ID: ")[-1].replace(")", ""))
        dados = cursor.execute("SELECT nome, quarto FROM reservas WHERE id = ?", (reserva_id,)).fetchone()
        nome, quarto = dados

        motivo = st.text_area("✏️ Motivo do Cancelamento", max_chars=300)

        if st.button("🚫 Confirmar Cancelamento"):
            if not motivo.strip():
                st.warning("⚠️ Por favor, informe o motivo do cancelamento.")
                return

            # Atualiza status da reserva para "Cancelada" e salva o motivo
            cursor.execute("""
                UPDATE reservas 
                SET status = ?, motivo_cancelamento = ?
                WHERE id = ?
            """, ("Cancelada", motivo, reserva_id))

            # Atualiza o status do quarto para "Livre"
            cursor.execute("""
                UPDATE quartos 
                SET status = 'Livre'
                WHERE quarto = ?
            """, (quarto,))

            conn.commit()
            st.success(f"❌ Reserva cancelada com sucesso. Quarto {quarto} está agora disponível.")

def arrumacao():
    st.header("🧹 Arrumação / Limpeza / Manutenção")

    col1, col2 = st.columns(2)

    if "acao_cliente" not in st.session_state:
        st.session_state.acao_cliente = "Nova tarefa"

    with col1:
        if st.button("➕ Nova tarefa"):
            st.session_state.acao_cliente = "Nova tarefa"

    with col2:
        if st.button("✅ Concluir tarefa", key="botao_concluir_topo"):
            st.session_state.acao_cliente = "Concluir tarefa"

    modo = st.session_state.acao_cliente
    st.markdown(f"### Modo selecionado: **{modo}**")

    if modo == "Nova tarefa":
        cursor.execute('''
            SELECT quarto FROM quartos 
            WHERE quarto NOT IN (
                SELECT quarto FROM arrumacoes WHERE status = 'Pendente'
            )
        ''')
        quartos_disponiveis = [row[0] for row in cursor.fetchall()]

        if not quartos_disponiveis:
            st.warning("Todos os quartos já possuem tarefas pendentes.")
            return

        funcionarios = cursor.execute("SELECT nome FROM funcionarios").fetchall()
        lista_funcionarios = ["Selecione um funcionário..."] + [f[0] for f in funcionarios]

        with st.form(key="form_arrumacao", clear_on_submit=True):
            nome = st.selectbox("👷 Funcionário", lista_funcionarios)
            funcao = st.selectbox("🔧 Função", ["Selecione um Serviço...", "Bloqueado", "Arrumação", "Limpeza", "Manutenção"])
            quarto = st.selectbox("🛏️ Quarto", ["Selecionar Quartos Disponíveis ..."] + quartos_disponiveis)
            tempo_previsto = st.text_input("⏳ Tempo previsto (ex: 00:45)")
            cadastrar = st.form_submit_button("🚀 Lançar tarefa")

            if cadastrar:
                if nome == "Selecione um funcionário...":
                    st.warning("Por favor, selecione um funcionário.")
                    return
                if funcao == "Selecione um Serviço...":
                    st.warning("Por favor, selecione uma função.")
                    return
                if quarto == "Selecionar Quartos Disponíveis ...":
                    st.warning("Por favor, selecione um quarto.")
                    return
                if not tempo_previsto:
                    st.warning("Informe o tempo previsto.")
                    return

                data = datetime.now().strftime("%Y-%m-%d")
                hora = datetime.now().strftime("%H:%M")

                cursor.execute("""
                    INSERT INTO arrumacoes (nome, funcao, quarto, status, data, hora, tempo_previsto)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (nome, funcao, quarto, "Pendente", data, hora, tempo_previsto))

                status_quarto_por_funcao = {
                    "Arrumação": "Em Arrumação",
                    "Limpeza": "Em Limpeza",
                    "Manutenção": "Em Manutenção",
                    "Bloqueado": "Bloqueado"
                }
                status_quarto = status_quarto_por_funcao.get(funcao, "Livre")

                cursor.execute("UPDATE quartos SET status = ? WHERE quarto = ?", (status_quarto, quarto))
                conn.commit()

                st.success(f"Tarefa de {funcao} lançada para o quarto {quarto} ⏳")

        return

    # ------------------------- CONCLUIR TAREFA -----------------------------------
    elif modo == "Concluir tarefa":

        cursor.execute("SELECT quarto, funcao FROM arrumacoes WHERE status = 'Pendente'")
        tarefas_pendentes = cursor.fetchall()
        if not tarefas_pendentes:
            st.info("Nenhuma tarefa pendente.")
            return

        tarefas_display = [f"{quarto} - {funcao}" for quarto, funcao in tarefas_pendentes]

    # --------------------- LISTA TEMPORÁRIA DE ITENS USADOS -------------------------
        if "itens_usados" not in st.session_state:
            st.session_state.itens_usados = []   # [{id, nome, qtd}]

        st.subheader("🧺 Itens usados na tarefa")
        if st.session_state.itens_usados:
            for item in st.session_state.itens_usados:
                st.write(f"• {item['nome']} — {item['qtd']} un.")
        else:
            st.info("Nenhum item registrado ainda.")

    # ---------------- FORM 1: ADICIONAR ITENS USADOS --------------------------------
        with st.form("form_saida_itens", clear_on_submit=True):

            tarefa_selecionada = st.selectbox("🧾 Selecione uma tarefa", tarefas_display)

        # Carregar categorias
        categorias = [row[0] for row in cursor.execute("SELECT DISTINCT categoria FROM estoque").fetchall()]
        categoria_sel = st.selectbox("📂 Categoria", ["Selecionar Categoria..."] + categorias)

        nome_sel = None
        produto_dict = {}

        if categoria_sel != "Selecionar Categoria...":
            produtos = cursor.execute(
                "SELECT id, nome, quantidade FROM estoque WHERE categoria = ? AND quantidade > 0",
                (categoria_sel,)
            ).fetchall()

            if produtos:
                produto_dict = {nome: (pid, qtd) for pid, nome, qtd in produtos}
                nome_sel = st.selectbox("🛒 Produto", ["Selecionar Produto..."] + list(produto_dict.keys()))
            else:
                st.warning("Nenhum produto disponível.")
                nome_sel = None

        qtd_saida = 0
        if nome_sel and nome_sel != "Selecionar Produto...":
            produto_id, estoque_atual = produto_dict[nome_sel]
            qtd_saida = st.number_input("🔻 Quantidade usada", min_value=1, max_value=estoque_atual, value=1)

        registrar_item = st.form_submit_button("📤 Registrar item usado")

        if registrar_item:
            if nome_sel and nome_sel != "Selecionar Produto...":
                st.session_state.itens_usados.append({
                    "id": produto_id,
                    "nome": nome_sel,
                    "qtd": qtd_saida
                })
                st.success(f"Item **{nome_sel}** registrado!")
            else:
                st.warning("Selecione um item válido.")

    # ---------------- FORM 2: CONCLUIR TAREFA ---------------------------------------
    with st.form("form_concluir_final", clear_on_submit=True):

        tempo_gasto = st.text_input("🕒 Tempo gasto (ex: 00:50)")
        observacao_final = st.text_area("📋 Observação (se necessário)")
        concluir = st.form_submit_button("✅ Concluir tarefa")

        if concluir:

            if not tempo_gasto:
                st.warning("Informe o tempo gasto.")
                return

            if not st.session_state.itens_usados:
                st.warning("Registre ao menos um item usado antes de concluir.")
                return

            # Identifica quarto e função
            quarto_sel, funcao_sel = tarefa_selecionada.split(" - ")

            # Verifica tempo previsto
            cursor.execute("""
                SELECT tempo_previsto FROM arrumacoes 
                WHERE quarto = ? AND funcao = ? AND status = 'Pendente'
            """, (quarto_sel, funcao_sel))
            resultado = cursor.fetchone()

            tempo_previsto = resultado[0]

            t_prev = sum(int(x) * 60 ** i for i, x in enumerate(reversed(tempo_previsto.split(":"))))
            t_gasto = sum(int(x) * 60 ** i for i, x in enumerate(reversed(tempo_gasto.split(":"))))

            if t_gasto > t_prev and not observacao_final.strip():
                st.warning("⚠️ Tempo maior que o previsto — necessária observação.")
                return
            # ------------------------------------------
# BAIXAR ESTOQUE E REGISTRAR USO DOS ITENS
# ------------------------------------------
    data_hoje = datetime.now().strftime("%Y-%m-%d")
    hora_agora = datetime.now().strftime("%H:%M:%S")

# Recupera o ID da arrumação concluída
    cursor.execute("""
        SELECT id FROM arrumacoes
        WHERE quarto = ? AND funcao = ? AND status = 'Pendente'
    """, (quarto_sel, funcao_sel))
    arrumacao_id = cursor.fetchone()[0]

    for item in st.session_state.itens_usados:
        produto_id = item["id"]
        quantidade_usada = item["qtd"]

    # Obter quantidade atual e valor unitário
        cursor.execute("""
            SELECT quantidade, valor_unitario
            FROM estoque
            WHERE id = ?
        """, (produto_id,))
        quantidade_atual, valor_unitario = cursor.fetchone()

    # Nova quantidade
        nova_qtd = quantidade_atual - quantidade_usada

    # Baixar estoque
        cursor.execute("""
            UPDATE estoque 
            SET quantidade = ?
            WHERE id = ?
        """, (nova_qtd, produto_id))

    # Registrar movimentação (SAÍDA)
        valor_total = quantidade_usada * valor_unitario
        cursor.execute("""
            INSERT INTO movimentacoes_estoque 
            (produto_id, tipo, quantidade, data, hora, valor_total, observacao)
            VALUES (?, 'Saída', ?, ?, ?, ?, ?)
        """, (
            produto_id,
            quantidade_usada,
            data_hoje,
            hora_agora,
            valor_total,
            f"Uso em arrumação do quarto {quarto_sel}"
        ))

    # Registrar item vinculado à arrumação
        cursor.execute("""
        INSERT INTO arrumacoes_itens
            (arrumacao_id, produto_id, quantidade, valor_unitario, valor_total, data, hora)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            arrumacao_id,
            produto_id,
            quantidade_usada,
            valor_unitario,
            valor_total,
            data_hoje,
            hora_agora
        ))

            # ---------------- BAIXAR ESTOQUE --------------------
        for item in st.session_state.itens_usados:
                cursor.execute("""
                    UPDATE estoque 
                    SET quantidade = quantidade - ?
                    WHERE id = ?
                """, (item["qtd"], item["id"]))

            # Limpa lista após salvar
        st.session_state.itens_usados = []

            # Atualiza tarefa
        cursor.execute("""
                UPDATE arrumacoes SET status = ?, tempo_gasto = ?, observacao = ?
                WHERE quarto = ? AND funcao = ? AND status = 'Pendente'
            """, ("Concluído", tempo_gasto, observacao_final, quarto_sel, funcao_sel))

            # Libera o quarto
        cursor.execute("UPDATE quartos SET status = 'Livre' WHERE quarto = ?", (quarto_sel,))
        conn.commit()

    df = pd.read_sql_query("""
        SELECT quarto, funcao, nome, status, data, hora, tempo_previsto, tempo_gasto, observacao 
        FROM arrumacoes 
        ORDER BY id DESC
    """, conn)

    if df.empty:
        st.info("Nenhum registro no histórico.")
    else:
        for _, row in df.iterrows():
            with st.expander(f"🏷️ {row['funcao']} - {row['quarto']}"):
                st.markdown(f"**Funcionário:** {row['nome']}")
                st.markdown(f"**Status:** {row['status']}")
                st.markdown(f"**Data:** {row['data']} {row['hora']}")
                st.markdown(f"**Tempo previsto:** {row['tempo_previsto']}")
                st.markdown(f"**Tempo gasto:** {row['tempo_gasto'] if row['tempo_gasto'] else 'Não informado'}")
                st.markdown(f"**Observação:** {row['observacao'] if row['observacao'] else 'Nenhuma'}")

def mensagens():
    st.title("📞 Comunicação Interna")

    # Inserir novo comunicado
    with st.form("form_comunicado", clear_on_submit=True):
        mensagem = st.text_area("📝 Escreva um comunicado para os hóspedes ou equipe:")
        destinatario = st.selectbox("👥 Destinatário", ["Todos", "Equipe", "Hóspedes"])
        numero_whatsapp = st.text_input(
            "📱 Número do WhatsApp (com DDD e código do país, ex: 5599999999999)",
            placeholder="Opcional"
        )
        enviar = st.form_submit_button("📤 Enviar comunicado")

        if enviar:
            if mensagem.strip() == "":
                st.warning("⚠️ A mensagem está vazia.")
            else:
                # Salva no banco de dados
                data_envio = datetime.now().strftime("%Y-%m-%d")
                hora_envio = datetime.now().strftime("%H:%M:%S")
                cursor.execute("""
                    INSERT INTO comunicados (mensagem, destinatario, data, hora)
                    VALUES (?, ?, ?, ?)
                """, (mensagem, destinatario, data_envio, hora_envio))
                conn.commit()

                # Alerta visual
                st.success(f"📨 Comunicado enviado para {destinatario}!")

                # Alerta interno simulado
                st.toast(f"📢 Novo comunicado para {destinatario}: {mensagem}")

                # Envio via WhatsApp se número informado
                if numero_whatsapp.strip() != "":
                    texto = urllib.parse.quote(mensagem)
                    link = f"https://wa.me/{numero_whatsapp}?text={texto}"
                    st.markdown(
                        f"💬 [Clique aqui para enviar a mensagem via WhatsApp]({link})",
                        unsafe_allow_html=True
                    )

    st.markdown("---")
    st.subheader("📋 Comunicados Enviados")

    # Exibir comunicados
    df = pd.read_sql_query(
        "SELECT id, mensagem, destinatario, data, hora FROM comunicados ORDER BY data DESC, hora DESC",
        conn
    )

    if df.empty:
        st.info("📭 Nenhum comunicado registrado.")
    else:
        df.columns = ["ID", "Mensagem", "Destinatário", "Data", "Hora"]
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_pagination()
        gb.configure_selection("single", use_checkbox=True)
        grid_options = gb.build()

        grid_response = AgGrid(df, gridOptions=grid_options, theme="streamlit", height=300)
        selected_rows = grid_response.get("selected_rows", [])

        if isinstance(selected_rows, list) and len(selected_rows) > 0:
            comunicado_id = selected_rows[0]["ID"]
            if st.button("🗑️ Excluir Comunicado Selecionado"):
                cursor.execute("DELETE FROM comunicados WHERE id = ?", (comunicado_id,))
                conn.commit()
                st.success("🗑️ Comunicado excluído com sucesso!")
                st.experimental_rerun()
                
def emitir_estadia():
    st.title("📁 Emissão de Comprovante de Estadia")
    cpf = st.text_input("Digite o CPF do hóspede para gerar comprovante:").replace(".", "").replace("-", "").strip()

    if cpf:
        df = pd.read_sql_query("""
            SELECT id, nome, REPLACE(REPLACE(REPLACE(cpf, '.', ''), '-', ''), ' ', '') as cpf,
                quarto, data_entrada, data_saida, valor
            FROM reservas
            WHERE REPLACE(REPLACE(REPLACE(cpf, '.', ''), '-', ''), ' ', '') = ?
            AND status = 'Ativa'
            ORDER BY data_entrada DESC
        """, conn, params=(cpf,))

        if df.empty:
            st.warning("⚠️ Nenhuma estadia encontrada para este CPF.")
            return

        df["data_entrada"] = pd.to_datetime(df["data_entrada"], errors="coerce")
        df["data_saida"] = pd.to_datetime(df["data_saida"], errors="coerce")
        df = df.dropna(subset=["data_entrada", "data_saida"])

        df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
        df["dias"] = (df["data_saida"] - df["data_entrada"]).dt.days.clip(lower=1)
        df["total_estadia"] = df["dias"] * df["valor"]

        opcoes = df.apply(
            lambda row: f"{row['nome']} - Quarto {row['quarto']} ({row['data_entrada'].strftime('%d/%m/%Y')} a {row['data_saida'].strftime('%d/%m/%Y')})",
            axis=1
        ).values.tolist()

        selecionado = st.selectbox("Selecione a estadia:", opcoes)

        if selecionado:
            index = opcoes.index(selecionado)
            reserva = df.iloc[index]

            nome = reserva["nome"]
            quarto = reserva["quarto"]
            entrada = reserva["data_entrada"]
            saida = reserva["data_saida"]
            valor_diaria = float(reserva["valor"])
            dias = reserva["dias"]
            valor_total = reserva["total_estadia"]
            hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
            codigo_autenticacao = f"HTL-{cpf[-4:]}-{entrada.strftime('%d%m')}{saida.strftime('%d%m')}"

            st.success("✅ Estadia selecionada!")

            st.markdown(f"""
            **Nome:** {nome}  
            **CPF:** {cpf}  
            **Quarto:** {quarto}  
            **Check-in:** {entrada.strftime('%d/%m/%Y')}  
            **Check-out:** {saida.strftime('%d/%m/%Y')}  
            **Duração:** {dias} {'dia' if dias == 1 else 'dias'}  
            **Valor da Diária:** R$ {valor_diaria:.2f}  
            **Valor Total:** R$ {valor_total:.2f}  
            **Código de Autenticação:** `{codigo_autenticacao}`  
            """)

            if st.button("📄 Gerar PDF do Comprovante"):
                qr_img = qrcode.make(f"https://meuhotel.com/comprovante/{codigo_autenticacao}")
                qr_buffer = io.BytesIO()
                qr_img.save(qr_buffer)
                qr_buffer.seek(0)

                buffer = io.BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=A4)
                styles = getSampleStyleSheet()

                conteudo = [
                    Paragraph("🏨 Hotel Pousada do Sol", styles['Title']),
                    Spacer(1, 12),
                    Paragraph("📑 COMPROVANTE DE ESTADIA", styles['Heading2']),
                    Spacer(1, 20),
                    Paragraph(f"<b>Nome do Hóspede:</b> {nome}", styles['Normal']),
                    Paragraph(f"<b>CPF:</b> {cpf}", styles['Normal']),
                    Paragraph(f"<b>Quarto:</b> {quarto}", styles['Normal']),
                    Paragraph(f"<b>Check-in:</b> {entrada.strftime('%d/%m/%Y')}", styles['Normal']),
                    Paragraph(f"<b>Check-out:</b> {saida.strftime('%d/%m/%Y')}", styles['Normal']),
                    Paragraph(f"<b>Duração:</b> {dias} {'dia' if dias == 1 else 'dias'}", styles['Normal']),
                    Paragraph(f"<b>Valor da Diária:</b> R$ {valor_diaria:.2f}", styles['Normal']),
                    Paragraph(f"<b>Valor Total:</b> R$ {valor_total:.2f}", styles['Normal']),
                    Paragraph(f"<b>Código de Autenticação:</b> {codigo_autenticacao}", styles['Normal']),
                    Spacer(1, 12),
                    Paragraph(f"📅 Emitido em: {hoje}", styles['Italic']),
                    Spacer(1, 20),
                    Paragraph("Este documento confirma a estadia conforme os dados acima. Emitido automaticamente pelo sistema de hotelaria.", styles['Normal']),
                    Spacer(1, 20),
                    Paragraph("___________________________", styles['Normal']),
                    Paragraph("Assinatura do Responsável", styles['Normal']),
                    Spacer(1, 20),
                    Image(qr_buffer, 1.5 * inch, 1.5 * inch),
                    Paragraph("🔍 Verificação online disponível via QR Code", styles['Italic'])
                ]

                doc.build(conteudo)
                buffer.seek(0)

                b64 = base64.b64encode(buffer.read()).decode()
                href = f'<a href="data:application/pdf;base64,{b64}" download="comprovante_estadia_{cpf}.pdf">📥 Clique aqui para baixar o comprovante em PDF</a>'
                st.markdown(href, unsafe_allow_html=True)

def cadastrar_produto():
    st.title("📦 Cadastrar Produto")

    with st.form("form_cadastro_produto", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("📛 Nome do Produto")
            codigo_barras = st.text_input("📎 Código de Barras").strip()
            categoria = st.selectbox("📂 Categoria", [
                "🧽 Limpeza", "🧻 Higiene", "🖋️ Escritório", "🛏️ Cama", "🛁 Banho",
                "🧰 Manutenção", "🥣 Cozinha", "🍽️ Utensílios", "🧴 Cosméticos",
                "📱 Eletrônicos", "🪑 Mobiliário", "🚪 Portaria", "🌿 Jardinagem",
                "💡 Elétrica", "🚰 Hidráulica", "🔧 Ferramentas", "📦 Outros"
            ])
            unidade = st.selectbox("📏 Unidade", ["un", "kg", "L", "pacote", "cx"])
            estoque_minimo = st.number_input("📉 Estoque Mínimo", min_value=0)
        with col2:
            quantidade = st.number_input("📦 Quantidade Inicial", min_value=0)
            valor = st.number_input("💰 Valor Unitário (R$)", min_value=0.0, format="%.2f")
            estoque_maximo = st.number_input("📈 Estoque Máximo", min_value=0)
            status = st.selectbox("🔘 Status", ["✅ Ativo", "⛔ Inativo"])
        observacao = st.text_area("📝 Observações", height=80)

        if st.form_submit_button("✅ Cadastrar Produto"):
            if not nome.strip():
                st.warning("⚠️ Preencha o nome do produto.")
            elif not codigo_barras:
                st.warning("⚠️ Preencha o código de barras.")
            else:
                # Verifica duplicidade de código de barras
                existente = cursor.execute("SELECT COUNT(*) FROM estoquelj WHERE codigo_barras = ?", (codigo_barras,)).fetchone()[0]
                if existente > 0:
                    st.error("❌ Este código de barras já está cadastrado para outro produto.")
                    return

                cursor.execute("""
                    INSERT INTO estoquelj (
                        nome, codigo_barras, categoria, unidade, quantidade, valor_unitario,
                        status, observacao, estoque_minimo, estoque_maximo
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    nome, codigo_barras, categoria, unidade, quantidade, valor,
                    status, observacao, estoque_minimo, estoque_maximo
                ))
                conn.commit()
                st.success("✅ Produto cadastrado com sucesso!")


# -------------------- SAÍDA DE PRODUTO --------------------
def saida_produto():
    st.title("🛍️ Venda de Produto / Saída de Estoque")

    st.markdown("🔍 **Busque pelo código de barras ou selecione manualmente o produto.**")

    codigo_barras = st.text_input("📷 Leitor de Código de Barras (digite ou escaneie):")

    produto_info = None

    if codigo_barras:
        produto_info = cursor.execute("""
            SELECT id, nome, quantidade, valor_unitario, unidade, categoria, estoque_minimo 
            FROM estoquelj WHERE codigo_barras = ?
        """, (codigo_barras.strip(),)).fetchone()

        if not produto_info:
            st.warning("⚠️ Produto com este código de barras não encontrado.")
            return

    if not produto_info:
        categorias = [row[0] for row in cursor.execute("SELECT DISTINCT categoria FROM estoquelj").fetchall()]
        categoria_sel = st.selectbox("📂 Filtrar por Categoria", ["Selecionar Categoria..."] + categorias)

        if categoria_sel == "Selecionar Categoria...":
            st.info("👈 Por favor, selecione uma categoria para continuar.")
            return

        produtos = cursor.execute("""
            SELECT id, nome FROM estoquelj 
            WHERE categoria = ? AND quantidade > 0
        """, (categoria_sel,)).fetchall()

        if not produtos:
            st.info("📭 Nenhum produto com estoque disponível nesta categoria.")
            return

        produto_dict = {nome: pid for pid, nome in produtos}
        nome_sel = st.selectbox("🛒 Produto", ["Selecionar Produto..."] + list(produto_dict.keys()))

        if nome_sel == "Selecionar Produto...":
            st.info("👈 Por favor, selecione um produto.")
            return

        produto_id = produto_dict[nome_sel]
        produto_info = cursor.execute("""
            SELECT id, nome, quantidade, valor_unitario, unidade, categoria, estoque_minimo 
            FROM estoquelj WHERE id = ?
        """, (produto_id,)).fetchone()

    # Desempacotar info
    pid, nome, qtd, valor, unidade, categoria, min_estoque = produto_info

    st.markdown(f"""
    <div style='padding:15px; border:1px solid #CCC; border-radius:10px; background-color:#FAFAFA'>
        <h4 style='margin-bottom:5px'>📦 Produto: {nome}</h4>
        <b>📂 Categoria:</b> {categoria}<br>
        <b>📦 Quantidade em estoque:</b> <span style='color:{'red' if qtd <= min_estoque else 'green'}'>{qtd} {unidade}</span><br>
        <b>💲 Valor Unitário:</b> R$ {valor:.2f}<br>
        {"<b style='color:red;'>⚠️ Estoque abaixo do mínimo!</b>" if qtd <= min_estoque else ""}
    </div>
    """, unsafe_allow_html=True)

    # 🔍 Buscar hóspedes com reservas ativas
    reservas_ativas = cursor.execute("""
        SELECT nome, quarto FROM reservas WHERE status = 'Ativa'
    """).fetchall()

    if not reservas_ativas:
        st.warning("⚠️ Nenhum hóspede com reserva ativa encontrado.")
        return

    hospede_dict = {f"{nome} - Quarto {quarto}": (nome, quarto) for nome, quarto in reservas_ativas}
    selecionado = st.selectbox("👤 Selecione o Hóspede (Reserva Ativa)", list(hospede_dict.keys()))
    nome_hospede, quarto = hospede_dict[selecionado]

    with st.form("form_venda_produto", clear_on_submit=True):
        qtd_saida = st.number_input("🔻 Quantidade a vender", min_value=1, max_value=qtd)
        observacao = st.text_area("📝 Observação (opcional)", height=80)
        registrar = st.form_submit_button("💰 Registrar Venda")

    if registrar:
        nova_qtd = qtd - qtd_saida
        total = qtd_saida * valor
        data = datetime.now().strftime("%Y-%m-%d")
        hora = datetime.now().strftime("%H:%M:%S")

        try:
            # Atualiza estoque
            cursor.execute("UPDATE estoquelj SET quantidade = ? WHERE id = ?", (nova_qtd, pid))

            # Registra movimentação
            cursor.execute("""
                INSERT INTO movimentacoes_estoquelj (
                    produto_id, tipo, quantidade, data, hora, valor_total, observacao, cliente, quarto
                ) VALUES (?, 'Venda', ?, ?, ?, ?, ?, ?, ?)
            """, (pid, qtd_saida, data, hora, total, observacao, nome_hospede, quarto))

            conn.commit()

            st.success(f"✅ Venda registrada com sucesso!\nProduto: **{nome}**, Hóspede: **{nome_hospede}**, Quarto: **{quarto}**, Total: R$ {total:.2f}")

        except Exception as e:
            st.error(f"❌ Erro ao registrar a venda: {e}")


# -------------------- ALMOXARIFADO --------------------
def modulo_almoxarifado():
    st.title("🏷️ Almoxarifado - Itens em Estoque")

    # 🔍 Filtros
    with st.expander("🔍 Filtros"):
        col1, col2 = st.columns(2)
        filtro_nome = col1.text_input("🔎 Buscar por nome:")
        categorias = ["Todas"] + [row[0] for row in cursor.execute("SELECT DISTINCT categoria FROM estoque").fetchall()]
        filtro_categoria = col2.selectbox("📂 Filtrar por Categoria", categorias)

    # 📦 Consulta com filtros
    query = """
        SELECT id, nome, categoria, unidade, quantidade, estoque_minimo,
            estoque_maximo, valor_unitario, status, observacao
        FROM estoque WHERE quantidade > 0
    """
    params = []

    if filtro_nome:
        query += " AND nome LIKE ?"
        params.append(f"%{filtro_nome}%")

    if filtro_categoria != "Todas":
        query += " AND categoria = ?"
        params.append(filtro_categoria)

    query += " ORDER BY nome ASC"
    produtos = cursor.execute(query, tuple(params)).fetchall()

    if not produtos:
        st.info("📭 Nenhum item encontrado com os filtros aplicados.")
        return

    # 🧾 Exibição de produtos em "cartões" visuais
    st.markdown("### 🗃️ Detalhamento por Produto")
    for prod in produtos:
        id_, nome, categoria, unidade, qtd, min_estoque, max_estoque, valor, status, obs = prod
        cor_status = "#2ecc71" if status == "✅ Ativo" else "#e74c3c"
        cor_fundo = "#f0fdf4" if qtd > min_estoque else "#fff0f0"
        cor_qtd = "#2e8b57" if qtd > min_estoque else "#e60000"
        icone_categoria = categoria.split()[0] if categoria else "📦" 
        
        st.markdown(f"""
        <div style="background-color:{cor_fundo}; padding:15px; border:1px solid #ccc; border-radius:10px; margin-bottom:15px;">
            <h4 style="margin-bottom:10px;">{icone_categoria} <strong>{nome}</strong></h4>
            <div style="line-height: 1.7;">
                <b>📂 Categoria:</b> {categoria} &nbsp;&nbsp;&nbsp;
                <b>📏 Unidade:</b> {unidade}<br>
                <b>🔢 Quantidade:</b> <span style="color:{cor_qtd}">{qtd}</span> &nbsp;&nbsp;&nbsp;
                <b>📊 Mín/Máx:</b> {min_estoque}/{max_estoque}<br>
                <b>💰 Valor Unitário:</b> R$ {valor:.2f} &nbsp;&nbsp;&nbsp;
                <b>🔘 Status:</b> <span style="color:{cor_status}">{status}</span><br>
                {"<b>📝 Observações:</b> " + obs if obs.strip() else ""}
                {"<div style='color:red; margin-top:8px;'><b>⚠️ Estoque abaixo do mínimo!</b></div>" if qtd <= min_estoque else ""}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 📊 Tabela Estilizada com Destaque
    st.markdown("### 📋 Visão Geral dos Itens em Tabela")

    df = pd.read_sql_query("""
        SELECT nome AS Produto, categoria AS Categoria, unidade AS Unidade,
            quantidade AS Quantidade, estoque_minimo AS 'Estoque Mínimo',
            estoque_maximo AS 'Estoque Máximo', valor_unitario AS 'Valor Unitário (R$)', status AS Status
        FROM estoque
        WHERE quantidade > 0
        ORDER BY nome ASC
    """, conn)

    def destacar_estoque_baixo(row):
        return ['background-color: #ffe6e6' if row['Quantidade'] <= row['Estoque Mínimo'] else '' for _ in row]

    st.dataframe(df.style.apply(destacar_estoque_baixo, axis=1), use_container_width=True)

    # ⚠️ Alerta para itens críticos
    df_critico = df[df["Quantidade"] <= df["Estoque Mínimo"]]
    if not df_critico.empty:
        st.markdown("### ⚠️ Itens com Estoque Crítico")
        st.dataframe(df_critico.style.apply(highlight, axis=1), use_container_width=True)


# Estilo extra (opcional): função para aplicar destaque amarelo
def highlight(row):
    return ['background-color: #fff3cd'] * len(row)

def entrada_produto():
    st.title("📥 Entrada de Produto")

    categorias = [row[0] for row in cursor.execute("SELECT DISTINCT categoria FROM estoquelj").fetchall()]
    categoria_sel = st.selectbox("📂 Filtrar por Categoria", ["Selecionar Categoria..."] + categorias)

    if categoria_sel == "Selecionar Categoria...":
        st.info("👈 Por favor, selecione uma categoria.")
        return

    produtos = cursor.execute("SELECT id, nome FROM estoquelj WHERE categoria = ?", (categoria_sel,)).fetchall()

    if not produtos:
        st.info("📭 Nenhum produto disponível nesta categoria.")
        return

    produto_dict = {nome: pid for pid, nome in produtos}
    nome_sel = st.selectbox("🛒 Produto", ["Selecionar Produto..."] + list(produto_dict.keys()))

    if nome_sel == "Selecionar Produto...":
        st.info("👈 Por favor, selecione um produto para entrada.")
        return

    produto_id = produto_dict[nome_sel]

    dados = cursor.execute("""
        SELECT quantidade, valor_unitario, unidade, categoria, estoque_minimo, estoque_maximo
        FROM estoquelj WHERE id = ?
    """, (produto_id,)).fetchone()

    qtd, valor_unitario, unidade, categoria, min_estoque, max_estoque = dados

    st.markdown(f"""
    <div style='padding:10px; border:1px solid #DDD; border-radius:10px; background-color:#F9F9F9'>
        <b>📦 Quantidade Atual:</b> <span style='color:green'>{qtd} {unidade}</span><br>
        <b>📂 Categoria:</b> {categoria}<br>
        <b>💰 Valor Unitário Atual:</b> R$ {valor_unitario:.2f}<br>
        <b>📊 Estoque Mín/Máx:</b> {min_estoque} / {max_estoque}
    </div>
    """, unsafe_allow_html=True)

    # 🔽 Formulário de entrada
    with st.form("form_entrada_produto", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            qtd_entrada = st.number_input("📥 Quantidade para entrada", min_value=1, step=1)
        with col2:
            novo_valor = st.number_input("💰 Novo valor unitário (opcional)", value=valor_unitario, step=0.01, format="%.2f")

        observacao = st.text_area("📝 Observação (opcional)")

        enviar = st.form_submit_button("✅ Registrar Entrada")

        if enviar:
            nova_qtd = qtd + qtd_entrada
            valor_total = qtd_entrada * novo_valor
            data = datetime.now().strftime("%Y-%m-%d")
            hora = datetime.now().strftime("%H:%M:%S")

            try:
                # Atualiza estoque
                cursor.execute("""
                    UPDATE estoque SET quantidade = ?, valor_unitario = ? WHERE id = ?
                """, (nova_qtd, novo_valor, produto_id))

                # Registra movimentação
                cursor.execute("""
                    INSERT INTO movimentacoes_estoque (produto_id, tipo, quantidade, data, hora, valor_total, observacao)
                    VALUES (?, 'Entrada', ?, ?, ?, ?, ?)
                """, (produto_id, qtd_entrada, data, hora, valor_total, observacao))

                conn.commit()
                st.success(f"✅ Entrada registrada com sucesso para o produto **{nome_sel}**!")
            except Exception as e:
                st.error(f"❌ Erro ao registrar entrada: {e}")

def modulo_contabil():
    st.title("📊 Módulo Contábil")

    # ---- Filtros ----
    st.subheader("🔎 Filtros de Período e CPF")
    
    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("📅 Data Início", value=None)
    with col2:
        data_fim = st.date_input("📅 Data Fim", value=None)

    # Carrega lista de CPFs
    cpfs = pd.read_sql_query("SELECT DISTINCT cpf FROM reservas", conn)["cpf"].dropna().tolist()
    cpf_sel = None

    if cpfs:
        cpf_sel = st.selectbox("👤 Selecione um CPF (opcional)", options=["Todos"] + cpfs)

    # Define filtro base
    filtro_data = ""
    params = []

    if data_inicio and data_fim:
        filtro_data = " AND data_entrada BETWEEN ? AND ? "
        params.extend([str(data_inicio), str(data_fim)])

    # Consulta reservas
    if cpf_sel and cpf_sel != "Todos":
        query_reservas = f"SELECT data_entrada, data_saida, valor FROM reservas WHERE cpf = ? {filtro_data}"
        params_cpf = [cpf_sel] + params
    else:
        query_reservas = f"SELECT data_entrada, data_saida, valor FROM reservas WHERE 1=1 {filtro_data}"
        params_cpf = params

    reservas = pd.read_sql_query(query_reservas, conn, params=params_cpf)
    reservas["valor"] = pd.to_numeric(reservas["valor"], errors="coerce")
    reservas["data_entrada"] = pd.to_datetime(reservas["data_entrada"], errors="coerce")
    reservas["data_saida"] = pd.to_datetime(reservas["data_saida"], errors="coerce")
    reservas = reservas.dropna(subset=["valor", "data_entrada", "data_saida"])
    reservas["dias"] = (reservas["data_saida"] - reservas["data_entrada"]).dt.days.clip(lower=1)
    reservas["total"] = reservas["valor"] * reservas["dias"]
    total_reserva = reservas["total"].sum()

    # Consulta vendas
    if cpf_sel and cpf_sel != "Todos":
        vendas = pd.read_sql_query("SELECT valor_total FROM movimentacoes_estoquelj WHERE tipo = 'Venda' AND cliente = ?", conn, params=(cpf_sel,))
    else:
        vendas = pd.read_sql_query("SELECT valor_total FROM movimentacoes_estoquelj WHERE tipo = 'Venda'", conn)

    vendas["valor_total"] = pd.to_numeric(vendas["valor_total"], errors="coerce")
    receita_vendas = vendas["valor_total"].sum() if not vendas.empty else 0.0

    st.info(f"💼 Total com Reservas: R$ {float(total_reserva):.2f}")
    st.info(f"🛍️ Total com Compras: R$ {float(receita_vendas):.2f}")
    st.success(f"💰 Total Geral: R$ {float(total_reserva + receita_vendas):.2f}")

    # ---- Demonstração de Resultados ----
# Filtro por período
    st.subheader("📅 Filtro por Período")
    col1, col2 = st.columns(2)
    with col1:
        data_inicial = st.date_input("Data Inicial")
    with col2:
        data_final = st.date_input("Data Final")

    if data_inicial and data_final:
        st.subheader("📈 DRE - Demonstração do Resultado do Exercício")

    # ✅ Reservas no período
        reservas = pd.read_sql_query("""
            SELECT data_entrada, data_saida, valor FROM reservas
            WHERE data_saida >= ? AND data_entrada <= ?
        """, conn, params=(data_inicial.strftime("%Y-%m-%d"), data_final.strftime("%Y-%m-%d")))

        reservas["valor"] = pd.to_numeric(reservas["valor"], errors="coerce")
        reservas["data_entrada"] = pd.to_datetime(reservas["data_entrada"], errors="coerce")
        reservas["data_saida"] = pd.to_datetime(reservas["data_saida"], errors="coerce")
        reservas = reservas.dropna(subset=["valor", "data_entrada", "data_saida"])
        reservas["dias"] = (reservas["data_saida"] - reservas["data_entrada"]).dt.days.clip(lower=1)
        reservas["total"] = reservas["valor"] * reservas["dias"]
        receita_reservas = reservas["total"].sum()

    # ✅ Vendas no período
        vendas = pd.read_sql_query("""
            SELECT valor_total FROM movimentacoes_estoquelj
            WHERE tipo = 'Venda' AND data BETWEEN ? AND ?
        """, conn, params=(data_inicial.strftime("%Y-%m-%d"), data_final.strftime("%Y-%m-%d")))
        vendas["valor_total"] = pd.to_numeric(vendas["valor_total"], errors="coerce")
        receita_vendas = vendas["valor_total"].sum() if not vendas.empty else 0.0

    # ✅ Compras (Entrada) no almoxarifado no período
        compras_am = pd.read_sql_query("""
            SELECT valor_total FROM movimentacoes_estoque
            WHERE tipo = 'Entrada' AND data BETWEEN ? AND ?
        """, conn, params=(data_inicial.strftime("%Y-%m-%d"), data_final.strftime("%Y-%m-%d")))
        compras_am["valor_total"] = pd.to_numeric(compras_am["valor_total"], errors="coerce")
        total_compras_am = compras_am["valor_total"].sum() if not compras_am.empty else 0.0

    # ✅ Custos com arrumação no período
        arrumacao = pd.read_sql_query("""
            SELECT valor_total FROM movimentacoes_estoquelj
            WHERE tipo = 'Saída' AND LOWER(observacao) LIKE '%arrumação%' AND data BETWEEN ? AND ?
        """, conn, params=(data_inicial.strftime("%Y-%m-%d"), data_final.strftime("%Y-%m-%d")))
        arrumacao["valor_total"] = pd.to_numeric(arrumacao["valor_total"], errors="coerce")
        custo_arrumacao = arrumacao["valor_total"].sum() if not arrumacao.empty else 0.0

    # ✅ Cálculo dos totais
        receita_total = receita_reservas + receita_vendas
        custo_total = total_compras_am + custo_arrumacao
        lucro_bruto = receita_total - custo_total

    # ✅ Exibição dos resultados
        st.markdown(f"""
        **Receita de Reservas:** R$ {receita_reservas:.2f}  
        **Receita com Vendas:** R$ {receita_vendas:.2f}  
        **🔹 Receita Total:** R$ {receita_total:.2f}  

        **(-) Compras para Almoxarifado:** R$ {total_compras_am:.2f}  
        **(-) Custos com Arrumação:** R$ {custo_arrumacao:.2f}  
        **💵 Lucro Bruto:** R$ {lucro_bruto:.2f}
        """)

        st.markdown("---")

        st.subheader("💸 Fluxo de Caixa (Simplificado)")
        st.metric("Entradas (Receita Total)", f"R$ {receita_total:.2f}")
        st.metric("Saídas (Compras + Arrumação)", f"R$ {custo_total:.2f}")
        st.metric("Saldo Operacional", f"R$ {lucro_bruto:.2f}")

        st.markdown("---")

        st.subheader("📊 Indicadores Financeiros")
        total_clientes = pd.read_sql_query("SELECT COUNT(DISTINCT cpf) AS total FROM reservas", conn).iloc[0]["total"]
        ticket_medio = receita_total / total_clientes if total_clientes else 0
        margem_lucro = (lucro_bruto / receita_total * 100) if receita_total else 0
        custo_pct = (custo_total / receita_total * 100) if receita_total else 0

        st.markdown(f"""
        - **🎯 Ticket Médio por Cliente:** R$ {ticket_medio:.2f}  
        - **📈 Margem de Lucro:** {margem_lucro:.2f}%  
        - **💰 Custo Total (% Receita):** {custo_pct:.2f}%
        """)

        st.markdown("---")

        st.subheader("🏆 Top 5 Produtos Mais Vendidos")
        top_vendas = pd.read_sql_query("""
            SELECT p.nome, SUM(m.quantidade) as total_qtd, SUM(m.valor_total) as total_valor
            FROM movimentacoes_estoquelj m
            JOIN estoquelj p ON p.id = m.produto_id
            WHERE m.tipo = 'Venda' AND m.data BETWEEN ? AND ?
            GROUP BY p.nome
            ORDER BY total_valor DESC
            LIMIT 5
        """, conn, params=(data_inicial.strftime("%Y-%m-%d"), data_final.strftime("%Y-%m-%d")))

        if not top_vendas.empty:
            st.table(top_vendas.rename(columns={
                "nome": "Produto",
                "total_qtd": "Quantidade Vendida",
                "total_valor": "Receita"
            }))
        else:
            st.info("📭 Sem vendas registradas no período.")

def modulo_financeiro():
    st.title("💼 Módulo Financeiro")

    # Receitas
    reservas = pd.read_sql_query("SELECT data_entrada, data_saida, valor FROM reservas", conn)
    reservas["valor"] = pd.to_numeric(reservas["valor"], errors="coerce")
    reservas["data_entrada"] = pd.to_datetime(reservas["data_entrada"], errors="coerce")
    reservas["data_saida"] = pd.to_datetime(reservas["data_saida"], errors="coerce")
    reservas = reservas.dropna(subset=["valor", "data_entrada", "data_saida"])
    reservas["dias"] = (reservas["data_saida"] - reservas["data_entrada"]).dt.days.clip(lower=1)
    reservas["total"] = reservas["valor"] * reservas["dias"]
    receita_reservas = reservas["total"].sum()

    vendas = pd.read_sql_query("""
        SELECT valor_total FROM movimentacoes_estoquelj 
        WHERE tipo = 'Venda'
    """, conn)
    vendas["valor_total"] = pd.to_numeric(vendas["valor_total"], errors="coerce")
    receita_vendas = vendas["valor_total"].sum() if not vendas.empty else 0.0

    # Despesas - Compras para Almoxarifado
    compras = pd.read_sql_query("""
        SELECT valor_total FROM movimentacoes_estoque 
        WHERE tipo = 'Entrada'
    """, conn)
    compras["valor_total"] = pd.to_numeric(compras["valor_total"], errors="coerce")
    custo_compras = compras["valor_total"].sum() if not compras.empty else 0.0

    # Despesas - Arrumação
    arrumacao = pd.read_sql_query("""
        SELECT valor_total FROM movimentacoes_estoquelj
        WHERE tipo = 'Saída' AND LOWER(observacao) LIKE '%arrumação%'
    """, conn)
    arrumacao["valor_total"] = pd.to_numeric(arrumacao["valor_total"], errors="coerce")
    custo_arrumacao = arrumacao["valor_total"].sum() if not arrumacao.empty else 0.0

    # Totais
    receita_total = receita_reservas + receita_vendas
    despesas_total = custo_compras + custo_arrumacao
    lucro = receita_total - despesas_total
    margem_lucro = (lucro / receita_total * 100) if receita_total else 0

    st.subheader("📊 Visão Geral Financeira")
    st.metric("💰 Receita com Reservas", f"R$ {receita_reservas:.2f}")
    st.metric("🛍️ Receita com Vendas", f"R$ {receita_vendas:.2f}")
    st.metric("🔹 Receita Total", f"R$ {receita_total:.2f}")

    st.markdown("---")
    st.subheader("💸 Despesas")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📦 Compras Almoxarifado", f"R$ {custo_compras:.2f}")
    with col2:
        st.metric("🧹 Custos com Arrumação", f"R$ {custo_arrumacao:.2f}")

    st.metric("💸 Despesas Totais", f"R$ {despesas_total:.2f}")

    st.markdown("---")
    st.subheader("📈 Resultado Final")
    st.metric("📊 Lucro Bruto", f"R$ {lucro:.2f}", delta=f"{margem_lucro:.2f}%")

    st.markdown("---")
    st.info(f"""
    ✅ **Resumo**  
    - Receita Total: R$ {receita_total:.2f}  
    - Despesas Totais: R$ {despesas_total:.2f}  
    - Lucro Bruto: R$ {lucro:.2f}  
    - Margem de Lucro: {margem_lucro:.2f}%
    """)

    # (Opcional) Gráfico de barras
    if st.checkbox("📊 Mostrar gráfico comparativo"):
        import plotly.express as px
        df_fin = pd.DataFrame({
            "Categoria": ["Receitas Reservas", "Receitas Vendas", "Compras", "Arrumação", "Lucro"],
            "Valor": [receita_reservas, receita_vendas, -custo_compras, -custo_arrumacao, lucro]
        })
        fig = px.bar(df_fin, x="Categoria", y="Valor", text="Valor", title="💹 Comparativo Financeiro")
        st.plotly_chart(fig)

def dashboard():
    st.header("📊 Dashboard")
    st.write("Gráficos e estatísticas virão em breve.")
    st.line_chart([10, 20, 15, 30, 50])

if __name__ == "__main__":
    main()
