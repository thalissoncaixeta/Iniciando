import json
import os
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from tkcalendar import Calendar, DateEntry
except ImportError as exc:
    raise SystemExit("Instale a biblioteca 'tkcalendar' antes de executar: pip3 install tkcalendar") from exc

ARQUIVO_CONFIGURACAO = Path(__file__).with_name("configuracoes_calendario.json")
ARQUIVO_AGENDA = Path(__file__).with_name("agenda_aulas.json")

class CategoriaAula(Enum):
    TEORICA = "Teórica"
    LUDICA = "Lúdica"
    PRATICA = "Prática"
    AVALIACAO = "Avaliação"
    REVISAO = "Revisão"
    PASSEIO_CULTURA = "Passeio e Cultura"
    OUTRA = "Outra"

class TipoEvento(Enum):
    FERIADO = "Feriado"
    RECESSO = "Recesso"
    SABADO_LETIVO = "Sábado Letivo"

@dataclass
class Aula:
    data: str
    turma: str
    disciplina: str
    categoria: str
    nome_local: str = ""
    endereco_local: str = ""
    email_local: str = ""
    telefone_local: str = ""
    observacoes: str = ""
    autorizacao_pais: bool = False

@dataclass
class EventoEspecial:
    data: str
    nome: str
    tipo: str

class PlanejadorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Planejador de Aulas - Dashboard do Professor")
        self.geometry("1200x750")
        self.minsize(1000, 650)
        
        self._aplicar_tema_moderno()
        
        # Estado do Aplicativo
        self.aulas_registradas = self._carregar_agenda()
        self.config_dados = self._carregar_configuracoes()
        
        self.eventos_especiais = self.config_dados.get("eventos", [])
        self.turmas_cadastradas = self.config_dados.get("turmas", ["6º Ano A", "7º Ano A", "8º Ano A", "9º Ano A"])
        self.disciplinas_cadastradas = self.config_dados.get("disciplinas", ["Inglês", "Artes"])
        
        self.aula_em_edicao = None
        
        self._criar_interface()
        self._marcar_calendario()

    def _aplicar_tema_moderno(self):
        self.configure(bg="#f4f6f9")
        style = ttk.Style(self)
        style.theme_use('clam')
        
        # Cores Flat Modernas
        COR_BG = "#f4f6f9"
        COR_PRIMARIA = "#005b9f"
        COR_SECUNDARIA = "#ffffff"
        COR_TEXTO = "#333333"
        
        style.configure(".", background=COR_BG, foreground=COR_TEXTO, font=("Segoe UI", 10))
        style.configure("TNotebook", background=COR_BG, borderwidth=0)
        style.configure("TNotebook.Tab", padding=[20, 10], font=("Segoe UI", 10, "bold"), background="#e0e0e0")
        style.map("TNotebook.Tab", background=[("selected", COR_PRIMARIA)], foreground=[("selected", "white")])
        
        style.configure("TFrame", background=COR_BG)
        style.configure("Card.TFrame", background=COR_SECUNDARIA, relief="flat")
        
        style.configure("TLabelframe", background=COR_SECUNDARIA, font=("Segoe UI", 11, "bold"), borderwidth=1)
        style.configure("TLabelframe.Label", background=COR_SECUNDARIA, foreground=COR_PRIMARIA)
        
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6, background="#e0e0e0", borderwidth=0)
        style.map("TButton", background=[("active", "#d5d5d5")])
        
        style.configure("Primary.TButton", background=COR_PRIMARIA, foreground="white")
        style.map("Primary.TButton", background=[("active", "#00467a")])
        
        style.configure("Danger.TButton", background="#dc3545", foreground="white")
        style.map("Danger.TButton", background=[("active", "#c82333")])

    def _criar_interface(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=15)
        
        self.aba_agenda = ttk.Frame(self.notebook)
        self.aba_editor = ttk.Frame(self.notebook)
        self.aba_grade = ttk.Frame(self.notebook)
        self.aba_config = ttk.Frame(self.notebook)
        
        self.notebook.add(self.aba_agenda, text="📅 Agenda Geral")
        self.notebook.add(self.aba_editor, text="📝 Editor de Aula")
        self.notebook.add(self.aba_grade, text="⚡ Gerador de Grade")
        self.notebook.add(self.aba_config, text="⚙️ Configurações")
        
        self._construir_aba_agenda()
        self._construir_aba_editor()
        self._construir_aba_grade()
        self._construir_aba_config()

    # ================= ABA 1: AGENDA GERAL =================
    def _construir_aba_agenda(self):
        pane = ttk.PanedWindow(self.aba_agenda, orient=tk.HORIZONTAL)
        pane.pack(fill="both", expand=True, pady=10)
        
        # Coluna Esquerda: Calendário + Resumo do Dia
        frame_cal = ttk.Frame(pane, style="Card.TFrame", padding=15)
        pane.add(frame_cal, weight=1)
        
        ttk.Label(frame_cal, text="Selecione uma data:", font=("Segoe UI", 12, "bold"), background="#ffffff").pack(anchor="w", pady=(0,10))
        
        # CORREÇÃO: fonte passada como tupla ("Segoe UI", 10)
        self.cal = Calendar(frame_cal, selectmode="day", date_pattern="yyyy-mm-dd", font=("Segoe UI", 10), 
                            background="white", foreground="black", bordercolor="#e0e0e0",
                            headersbackground="#005b9f", headersforeground="white", 
                            selectbackground="#005b9f", selectforeground="white",
                            normalbackground="white", weekendbackground="#f8f9fa")
        self.cal.pack(fill="both", expand=True)
        self.cal.bind("<<CalendarSelected>>", self._ao_selecionar_data_calendario)
        
        # Painel de Resumo do Dia Selecionado
        self.frame_resumo_dia = ttk.LabelFrame(frame_cal, text="Resumo do Dia Selecionado", padding=10)
        self.frame_resumo_dia.pack(fill="x", pady=15)
        self.lbl_resumo_dia = ttk.Label(self.frame_resumo_dia, text="Selecione um dia...", font=("Segoe UI", 10), background="#ffffff", wraplength=300)
        self.lbl_resumo_dia.pack(anchor="w")
        
        # Legenda do Calendário
        frame_legenda = ttk.Frame(frame_cal, style="Card.TFrame")
        frame_legenda.pack(fill="x", pady=5)
        ttk.Label(frame_legenda, text="🔴 Feriado/Recesso  🟢 Sáb. Letivo  🔵 Aula  🟠 Passeio", font=("Segoe UI", 9), background="#ffffff").pack()

        # Coluna Direita: Lista de Aulas
        frame_lista = ttk.Frame(pane, style="Card.TFrame", padding=15)
        pane.add(frame_lista, weight=2)
        
        ttk.Label(frame_lista, text="Aulas Registradas", font=("Segoe UI", 12, "bold"), background="#ffffff").pack(anchor="w", pady=(0,10))
        
        self.lista_aulas = tk.Listbox(frame_lista, font=("Consolas", 11), selectbackground="#005b9f", relief="flat", highlightthickness=1, highlightcolor="#005b9f")
        self.lista_aulas.pack(fill="both", expand=True, side="left")
        
        scroll = ttk.Scrollbar(frame_lista, orient="vertical", command=self.lista_aulas.yview)
        scroll.pack(side="right", fill="y")
        self.lista_aulas.config(yscrollcommand=scroll.set)
        
        frame_botoes = ttk.Frame(self.aba_agenda)
        frame_botoes.pack(fill="x", pady=10)
        
        ttk.Button(frame_botoes, text="➕ Nova Aula", style="Primary.TButton", command=self._nova_aula_pelo_calendario).pack(side="left", padx=5)
        ttk.Button(frame_botoes, text="✏️ Editar Selecionada", command=self._editar_aula_selecionada).pack(side="left", padx=5)
        ttk.Button(frame_botoes, text="🗑️ Excluir", style="Danger.TButton", command=self._excluir_aula).pack(side="left", padx=5)
        ttk.Button(frame_botoes, text="📄 Exportar Relatório PDF", command=self._exportar_pdf).pack(side="right", padx=5)
        
        self._atualizar_lista()

    # ================= ABA 2: EDITOR DE AULA =================
    def _construir_aba_editor(self):
        form_frame = ttk.LabelFrame(self.aba_editor, text="Detalhes do Planejamento", padding=25)
        form_frame.pack(fill="both", expand=True, padx=40, pady=20)
        
        self.campos = {}
        
        ttk.Label(form_frame, text="Data da Aula:", background="#ffffff").grid(row=0, column=0, sticky="w", pady=10)
        # CORREÇÃO: fonte passada como tupla
        self.campos['data'] = DateEntry(form_frame, width=15, background='#005b9f', foreground='white', borderwidth=0, date_pattern="yyyy-mm-dd", font=("Segoe UI", 10))
        self.campos['data'].grid(row=0, column=1, sticky="w", padx=10)
        
        ttk.Label(form_frame, text="Turma:", background="#ffffff").grid(row=1, column=0, sticky="w", pady=10)
        self.campos['turma'] = ttk.Combobox(form_frame, values=self.turmas_cadastradas, width=25, font=("Segoe UI", 10))
        self.campos['turma'].grid(row=1, column=1, sticky="w", padx=10)

        ttk.Label(form_frame, text="Disciplina:", background="#ffffff").grid(row=1, column=2, sticky="w", pady=10, padx=(30,0))
        self.campos['disciplina'] = ttk.Combobox(form_frame, values=self.disciplinas_cadastradas, width=25, font=("Segoe UI", 10))
        self.campos['disciplina'].grid(row=1, column=3, sticky="w", padx=10)

        ttk.Label(form_frame, text="Categoria:", background="#ffffff").grid(row=2, column=0, sticky="w", pady=10)
        self.campos['categoria'] = ttk.Combobox(form_frame, values=[c.value for c in CategoriaAula], state="readonly", width=40, font=("Segoe UI", 10))
        self.campos['categoria'].set(CategoriaAula.TEORICA.value)
        self.campos['categoria'].grid(row=2, column=1, columnspan=3, sticky="w", padx=10)
        self.campos['categoria'].bind("<<ComboboxSelected>>", self._toggle_campos_passeio)

        # Campos Passeio Cultural (Dinâmico)
        self.frame_passeio = ttk.Frame(form_frame, style="Card.TFrame")
        self.frame_passeio.grid(row=3, column=0, columnspan=4, sticky="ew", pady=10)
        self.frame_passeio.grid_remove()

        ttk.Label(self.frame_passeio, text="Local do Passeio:", background="#ffffff").grid(row=0, column=0, sticky="w")
        self.campos['nome_local'] = ttk.Entry(self.frame_passeio, width=25, font=("Segoe UI", 10))
        self.campos['nome_local'].grid(row=0, column=1, padx=10)
        
        ttk.Label(self.frame_passeio, text="Endereço:", background="#ffffff").grid(row=0, column=2, sticky="w", padx=(20,0))
        self.campos['endereco_local'] = ttk.Entry(self.frame_passeio, width=35, font=("Segoe UI", 10))
        self.campos['endereco_local'].grid(row=0, column=3, padx=10)
        
        self.campos['autorizacao_pais'] = tk.BooleanVar()
        ttk.Checkbutton(self.frame_passeio, text="Exige Autorização dos Pais/Responsáveis", variable=self.campos['autorizacao_pais'], style="TCheckbutton").grid(row=1, column=0, columnspan=4, sticky="w", pady=15)

        ttk.Label(form_frame, text="Conteúdo / Obs:", background="#ffffff").grid(row=4, column=0, sticky="nw", pady=10)
        self.obs_text = tk.Text(form_frame, height=8, width=70, font=("Segoe UI", 10), relief="solid", borderwidth=1)
        self.obs_text.grid(row=4, column=1, columnspan=3, sticky="w", padx=10)

        btn_frame = ttk.Frame(self.aba_editor)
        btn_frame.pack(fill="x", padx=40, pady=10)
        
        ttk.Button(btn_frame, text="💾 Salvar Planejamento", style="Primary.TButton", command=self._salvar_aula).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="🧹 Limpar Formulário", command=self._limpar_form).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="❌ Voltar", command=self._cancelar_edicao).pack(side="left", padx=5)

    # ================= ABA 3: GERADOR DE GRADE =================
    def _construir_aba_grade(self):
        container = ttk.Frame(self.aba_grade, style="Card.TFrame", padding=30)
        container.pack(fill="both", expand=True, padx=40, pady=20)
        
        ttk.Label(container, text="⚡ Automação de Planejamento", font=("Segoe UI", 16, "bold"), background="#ffffff", foreground="#005b9f").pack(anchor="w", pady=(0, 5))
        ttk.Label(container, text="Selecione a turma e os dias da semana. O sistema irá agendar as aulas para os próximos 60 dias,\nignorando automaticamente os feriados e recessos que você cadastrou nas configurações.", background="#ffffff", foreground="#555555").pack(anchor="w", pady=(0, 25))

        form = ttk.Frame(container, style="Card.TFrame")
        form.pack(fill="x")
        
        ttk.Label(form, text="Turma Alvo:", background="#ffffff").grid(row=0, column=0, sticky="w", pady=10)
        self.combo_turma_grade = ttk.Combobox(form, values=self.turmas_cadastradas, width=30, font=("Segoe UI", 10))
        self.combo_turma_grade.grid(row=0, column=1, sticky="w", padx=15, pady=10)
        
        ttk.Label(form, text="Disciplina:", background="#ffffff").grid(row=1, column=0, sticky="w", pady=10)
        self.combo_disc_grade = ttk.Combobox(form, values=self.disciplinas_cadastradas, width=30, font=("Segoe UI", 10))
        self.combo_disc_grade.grid(row=1, column=1, sticky="w", padx=15, pady=10)
        
        dias_frame = ttk.LabelFrame(container, text="Dias da Semana", padding=15)
        dias_frame.pack(fill="x", pady=25)
        
        self.vars_dias_grade = []
        nomes_dias = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira"]
        for i, nome in enumerate(nomes_dias):
            var = tk.BooleanVar()
            self.vars_dias_grade.append((i, var))
            ttk.Checkbutton(dias_frame, text=nome, variable=var).pack(side="left", padx=20)

        ttk.Button(container, text="🚀 Gerar Grade Automática", style="Primary.TButton", command=self._executar_gerador).pack(pady=20)

    # ================= ABA 4: CONFIGURAÇÕES E EVENTOS =================
    def _construir_aba_config(self):
        pane = ttk.PanedWindow(self.aba_config, orient=tk.HORIZONTAL)
        pane.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Esquerda: Gestor de Datas Especiais (Novo Feriados)
        frame_esq = ttk.LabelFrame(pane, text="Gestão de Datas Especiais", padding=15)
        pane.add(frame_esq, weight=3)
        
        form_evento = ttk.Frame(frame_esq, style="Card.TFrame")
        form_evento.pack(fill="x", pady=(0, 15))
        
        ttk.Label(form_evento, text="Data:", background="#ffffff").grid(row=0, column=0, sticky="w", padx=5)
        self.ev_data = DateEntry(form_evento, width=12, background='#005b9f', foreground='white', date_pattern="yyyy-mm-dd", font=("Segoe UI", 10))
        self.ev_data.grid(row=0, column=1, padx=5)
        
        ttk.Label(form_evento, text="Nome:", background="#ffffff").grid(row=0, column=2, sticky="w", padx=(10,5))
        self.ev_nome = ttk.Entry(form_evento, width=20, font=("Segoe UI", 10))
        self.ev_nome.grid(row=0, column=3, padx=5)
        
        ttk.Label(form_evento, text="Tipo:", background="#ffffff").grid(row=0, column=4, sticky="w", padx=(10,5))
        self.ev_tipo = ttk.Combobox(form_evento, values=[t.value for t in TipoEvento], state="readonly", width=12, font=("Segoe UI", 10))
        self.ev_tipo.set(TipoEvento.FERIADO.value)
        self.ev_tipo.grid(row=0, column=5, padx=5)
        
        ttk.Button(form_evento, text="Adicionar", style="Primary.TButton", command=self._adicionar_evento).grid(row=0, column=6, padx=(15,5))
        
        # Tabela (Treeview) de Eventos
        colunas = ("Data", "Nome do Evento", "Tipo")
        self.tree_eventos = ttk.Treeview(frame_esq, columns=colunas, show="headings", height=10)
        self.tree_eventos.heading("Data", text="Data")
        self.tree_eventos.heading("Nome do Evento", text="Nome do Evento")
        self.tree_eventos.heading("Tipo", text="Tipo")
        self.tree_eventos.column("Data", width=90, anchor="center")
        self.tree_eventos.column("Nome do Evento", width=200)
        self.tree_eventos.column("Tipo", width=100, anchor="center")
        self.tree_eventos.pack(fill="both", expand=True)
        
        ttk.Button(frame_esq, text="🗑️ Remover Selecionado", style="Danger.TButton", command=self._remover_evento).pack(anchor="e", pady=10)
        
        # Direita: Turmas e Disciplinas
        frame_dir = ttk.Frame(pane)
        pane.add(frame_dir, weight=1)
        
        frame_t = ttk.LabelFrame(frame_dir, text="Turmas Cadastradas", padding=10)
        frame_t.pack(fill="both", expand=True, pady=(0,5))
        self.text_turmas = tk.Text(frame_t, height=8, width=20, font=("Consolas", 10))
        self.text_turmas.pack(fill="both", expand=True)
        ttk.Label(frame_t, text="* Uma por linha", font=("Segoe UI", 8), background="#ffffff").pack(anchor="w")
        
        frame_d = ttk.LabelFrame(frame_dir, text="Disciplinas Cadastradas", padding=10)
        frame_d.pack(fill="both", expand=True, pady=5)
        self.text_disciplinas = tk.Text(frame_d, height=8, width=20, font=("Consolas", 10))
        self.text_disciplinas.pack(fill="both", expand=True)
        
        ttk.Button(frame_dir, text="💾 Salvar Configurações", style="Primary.TButton", command=self._salvar_configuracoes).pack(fill="x", pady=10)
        
        self._preencher_configuracoes_ui()

    # ================= INTERAÇÕES DE EVENTOS (NOVO) =================
    def _adicionar_evento(self):
        data = self.ev_data.get()
        nome = self.ev_nome.get().strip()
        tipo = self.ev_tipo.get()
        
        if not nome:
            messagebox.showwarning("Aviso", "Digite o nome do evento.")
            return
            
        # Evitar duplicatas na mesma data
        self.eventos_especiais = [e for e in self.eventos_especiais if e["data"] != data]
        self.eventos_especiais.append({"data": data, "nome": nome, "tipo": tipo})
        
        self._salvar_configuracoes(silencioso=True)
        self.ev_nome.delete(0, tk.END)

    def _remover_evento(self):
        selecionado = self.tree_eventos.selection()
        if not selecionado: return
        
        item = self.tree_eventos.item(selecionado[0])
        data_remover = item['values'][0]
        
        self.eventos_especiais = [e for e in self.eventos_especiais if e["data"] != data_remover]
        self._salvar_configuracoes(silencioso=True)

    def _preencher_configuracoes_ui(self):
        # Treeview de Eventos
        for i in self.tree_eventos.get_children():
            self.tree_eventos.delete(i)
            
        # Ordenar eventos por data
        self.eventos_especiais.sort(key=lambda x: x["data"])
        for ev in self.eventos_especiais:
            self.tree_eventos.insert("", tk.END, values=(ev["data"], ev["nome"], ev["tipo"]))
            
        self.text_turmas.delete("1.0", tk.END)
        self.text_turmas.insert(tk.END, "\n".join(self.turmas_cadastradas))
        self.text_disciplinas.delete("1.0", tk.END)
        self.text_disciplinas.insert(tk.END, "\n".join(self.disciplinas_cadastradas))

    # ================= LÓGICA DO CALENDÁRIO VISUAL =================
    def _marcar_calendario(self):
        self.cal.calevent_remove("all")
        
        # Definindo as cores das Tags
        self.cal.tag_config("feriado", background="#dc3545", foreground="white") # Vermelho
        self.cal.tag_config("sabado_letivo", background="#28a745", foreground="white") # Verde
        self.cal.tag_config("aula_normal", background="#005b9f", foreground="white") # Azul
        self.cal.tag_config("passeio", background="#fd7e14", foreground="white") # Laranja
        
        # 1. Marca Eventos (Feriados, Recessos)
        for ev in self.eventos_especiais:
            data_obj = date.fromisoformat(ev["data"])
            if ev["tipo"] in [TipoEvento.FERIADO.value, TipoEvento.RECESSO.value]:
                self.cal.calevent_create(data_obj, ev["nome"], tags="feriado")
            elif ev["tipo"] == TipoEvento.SABADO_LETIVO.value:
                self.cal.calevent_create(data_obj, ev["nome"], tags="sabado_letivo")
                
        # 2. Marca Aulas Registradas
        # Mapeia quais dias tem passeio e quais tem aula normal
        dias_aulas = {}
        for aula in self.aulas_registradas:
            if aula.data not in dias_aulas:
                dias_aulas[aula.data] = "aula_normal"
            if aula.categoria == CategoriaAula.PASSEIO_CULTURA.value:
                dias_aulas[aula.data] = "passeio" # Sobrescreve para Laranja se houver passeio no dia
                
        for data_str, tag in dias_aulas.items():
            # Não sobrescreve feriados com tag de aula
            if not any(e["data"] == data_str for e in self.eventos_especiais if e["tipo"] != TipoEvento.SABADO_LETIVO.value):
                data_obj = date.fromisoformat(data_str)
                self.cal.calevent_create(data_obj, "Aula", tags=tag)
                
        # Força a atualização do resumo visual
        self._ao_selecionar_data_calendario(None)

    def _ao_selecionar_data_calendario(self, event):
        data_str = self.cal.get_date()
        try:
            data_obj = datetime.strptime(data_str, "%Y-%m-%d").date()
        except:
            return
            
        self.campos['data'].set_date(data_obj)
        
        # Construir o Resumo do Dia
        resumo = []
        
        # Verifica eventos especiais
        eventos_dia = [e for e in self.eventos_especiais if e["data"] == data_str]
        for e in eventos_dia:
            if e["tipo"] == TipoEvento.FERIADO.value:
                resumo.append(f"🔴 Feriado: {e['nome']}")
            elif e["tipo"] == TipoEvento.RECESSO.value:
                resumo.append(f"🔴 Recesso: {e['nome']}")
            elif e["tipo"] == TipoEvento.SABADO_LETIVO.value:
                resumo.append(f"🟢 Sábado Letivo: {e['nome']}")
                
        # Verifica Aulas
        aulas_dia = [a for a in self.aulas_registradas if a.data == data_str]
        for a in aulas_dia:
            icone = "🟠" if a.categoria == CategoriaAula.PASSEIO_CULTURA.value else "🔵"
            resumo.append(f"{icone} {a.turma} - {a.disciplina} ({a.categoria})")
            
        if not resumo:
            self.lbl_resumo_dia.config(text="Nenhum evento ou aula para este dia.", foreground="#555555")
        else:
            self.lbl_resumo_dia.config(text="\n".join(resumo), foreground="#000000")

    # ================= MÉTODOS DE SALVAMENTO E ESTADO =================
    def _salvar_configuracoes(self, silencioso=False):
        turmas_novas = [t.strip() for t in self.text_turmas.get("1.0", tk.END).splitlines() if t.strip()]
        disc_novas = [d.strip() for d in self.text_disciplinas.get("1.0", tk.END).splitlines() if d.strip()]
        
        self.turmas_cadastradas = turmas_novas
        self.disciplinas_cadastradas = disc_novas
        
        dados = {
            "eventos": self.eventos_especiais,
            "turmas": self.turmas_cadastradas,
            "disciplinas": self.disciplinas_cadastradas
        }
        with ARQUIVO_CONFIGURACAO.open("w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
            
        self._preencher_configuracoes_ui()
        self._marcar_calendario()
        
        self.campos['turma'].config(values=self.turmas_cadastradas)
        self.combo_turma_grade.config(values=self.turmas_cadastradas)
        self.campos['disciplina'].config(values=self.disciplinas_cadastradas)
        self.combo_disc_grade.config(values=self.disciplinas_cadastradas)
        
        if not silencioso:
            messagebox.showinfo("Sucesso", "Configurações atualizadas e salvas!")

    def _carregar_configuracoes(self) -> dict:
        if not ARQUIVO_CONFIGURACAO.exists(): return {}
        try:
            with ARQUIVO_CONFIGURACAO.open("r", encoding="utf-8") as f:
                dados = json.load(f)
                # Script de Migração
                if "feriados" in dados and isinstance(dados["feriados"], dict):
                    eventos_migrados = []
                    for data, nome in dados["feriados"].items():
                        eventos_migrados.append({"data": data, "nome": nome, "tipo": "Feriado"})
                    dados["eventos"] = eventos_migrados
                    del dados["feriados"]
                elif dados and not any(k in dados for k in ["eventos", "turmas", "disciplinas"]):
                    eventos_migrados = [{"data": d, "nome": n, "tipo": "Feriado"} for d, n in dados.items()]
                    return {"eventos": eventos_migrados}
                return dados
        except: return {}

    def _toggle_campos_passeio(self, event=None):
        if self.campos['categoria'].get() == CategoriaAula.PASSEIO_CULTURA.value:
            self.frame_passeio.grid()
        else:
            self.frame_passeio.grid_remove()

    def _nova_aula_pelo_calendario(self):
        self._cancelar_edicao()
        self._ao_selecionar_data_calendario(None)
        self.notebook.select(self.aba_editor)

    def _editar_aula_selecionada(self):
        if not self.lista_aulas.curselection():
            messagebox.showwarning("Aviso", "Selecione uma aula na lista primeiro.")
            return
            
        idx = self.lista_aulas.curselection()[0]
        self.aula_em_edicao = self.aulas_registradas[idx]
        
        data_obj = datetime.strptime(self.aula_em_edicao.data, "%Y-%m-%d").date()
        self.campos['data'].set_date(data_obj)
        self.campos['turma'].set(self.aula_em_edicao.turma)
        self.campos['disciplina'].set(self.aula_em_edicao.disciplina)
        self.campos['categoria'].set(self.aula_em_edicao.categoria)
        self.campos['nome_local'].delete(0, tk.END)
        self.campos['nome_local'].insert(0, self.aula_em_edicao.nome_local)
        self.campos['endereco_local'].delete(0, tk.END)
        self.campos['endereco_local'].insert(0, self.aula_em_edicao.endereco_local)
        self.campos['autorizacao_pais'].set(self.aula_em_edicao.autorizacao_pais)
        
        self.obs_text.delete("1.0", tk.END)
        self.obs_text.insert("1.0", self.aula_em_edicao.observacoes)
        
        self._toggle_campos_passeio()
        self.notebook.select(self.aba_editor)

    def _cancelar_edicao(self):
        self._limpar_form()
        self.notebook.select(self.aba_agenda)

    def _salvar_aula(self):
        nova_aula = Aula(
            data=self.campos['data'].get(),
            turma=self.campos['turma'].get().strip(),
            disciplina=self.campos['disciplina'].get().strip(),
            categoria=self.campos['categoria'].get(),
            nome_local=self.campos.get('nome_local').get() if self.campos.get('nome_local') else "",
            endereco_local=self.campos.get('endereco_local').get() if self.campos.get('endereco_local') else "",
            observacoes=self.obs_text.get("1.0", tk.END).strip(),
            autorizacao_pais=self.campos['autorizacao_pais'].get()
        )
        
        if not nova_aula.turma or not nova_aula.disciplina:
            messagebox.showerror("Erro", "Turma e Disciplina são obrigatórios.")
            return

        if self.aula_em_edicao:
            idx = self.aulas_registradas.index(self.aula_em_edicao)
            self.aulas_registradas[idx] = nova_aula
            self.aula_em_edicao = None
        else:
            self.aulas_registradas.append(nova_aula)
            
        self._salvar_agenda()
        self._atualizar_lista()
        self._marcar_calendario() 
        self._limpar_form()
        messagebox.showinfo("Sucesso", "Planejamento salvo com sucesso!")
        self.notebook.select(self.aba_agenda)

    def _excluir_aula(self):
        if not self.lista_aulas.curselection():
            messagebox.showwarning("Aviso", "Selecione uma aula na lista primeiro.")
            return
        
        idx = self.lista_aulas.curselection()[0]
        aula = self.aulas_registradas[idx]
        
        if messagebox.askyesno("Confirmar", f"Deseja excluir a aula de {aula.disciplina} da turma {aula.turma}?"):
            self.aulas_registradas.remove(aula)
            self._salvar_agenda()
            self._atualizar_lista()
            self._marcar_calendario()
            self._limpar_form()

    def _limpar_form(self):
        self.aula_em_edicao = None
        self.campos['data'].set_date(date.today())
        self.campos['turma'].set('')
        self.campos['disciplina'].set('')
        self.campos['categoria'].set(CategoriaAula.TEORICA.value)
        self.campos['nome_local'].delete(0, tk.END)
        self.campos['endereco_local'].delete(0, tk.END)
        self.campos['autorizacao_pais'].set(False)
        self.obs_text.delete("1.0", tk.END)
        self._toggle_campos_passeio()

    def _atualizar_lista(self):
        self.lista_aulas.delete(0, tk.END)
        self.aulas_registradas.sort(key=lambda x: x.data)
        
        for aula in self.aulas_registradas:
            data_br = datetime.strptime(aula.data, "%Y-%m-%d").strftime("%d/%m/%Y")
            linha = f"[{data_br}] {aula.turma} | {aula.disciplina} | {aula.categoria}"
            self.lista_aulas.insert(tk.END, linha)

    def _executar_gerador(self):
        turma = self.combo_turma_grade.get().strip()
        disc = self.combo_disc_grade.get().strip()
        dias_selecionados = [i for i, var in self.vars_dias_grade if var.get()]
        
        if not turma or not disc or not dias_selecionados:
            messagebox.showerror("Erro", "Preencha Turma, Disciplina e selecione ao menos um dia.")
            return
            
        data_atual = date.today()
        aulas_geradas = 0
        
        dias_bloqueados = [e["data"] for e in self.eventos_especiais if e["tipo"] in [TipoEvento.FERIADO.value, TipoEvento.RECESSO.value]]
        
        for i in range(60):
            data_alvo = data_atual + timedelta(days=i)
            data_str = data_alvo.strftime("%Y-%m-%d")
            
            if data_alvo.weekday() in dias_selecionados and data_str not in dias_bloqueados:
                existe = any(a.data == data_str and a.turma == turma and a.disciplina == disc for a in self.aulas_registradas)
                if not existe:
                    nova_aula = Aula(
                        data=data_str, turma=turma, disciplina=disc,
                        categoria=CategoriaAula.TEORICA.value, observacoes="Aula gerada automaticamente."
                    )
                    self.aulas_registradas.append(nova_aula)
                    aulas_geradas += 1
        
        if aulas_geradas > 0:
            self._salvar_agenda()
            self._atualizar_lista()
            self._marcar_calendario()
            messagebox.showinfo("Sucesso", f"{aulas_geradas} aulas agendadas com sucesso!")
            self.notebook.select(self.aba_agenda)
        else:
            messagebox.showinfo("Aviso", "Nenhuma aula nova gerada (já existiam ou coincidiram com feriados).")

    def _exportar_pdf(self):
        if not self.lista_aulas.curselection():
            messagebox.showwarning("Aviso", "Selecione uma aula na lista primeiro.")
            return
            
        idx = self.lista_aulas.curselection()[0]
        aula = self.aulas_registradas[idx]
            
        caminho = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Arquivo PDF", "*.pdf"), ("Arquivo de texto", "*.txt")],
            title="Salvar Relatório de Aula"
        )
        if not caminho: return

        data_br = datetime.strptime(aula.data, "%Y-%m-%d").strftime("%d/%m/%Y")
        texto_relatorio = (
            f"Relatório de Planejamento de Aula - {data_br}\n"
            f"Turma: {aula.turma} | Disciplina: {aula.disciplina}\n"
            f"Categoria: {aula.categoria}\n\n"
        )
        if aula.categoria == CategoriaAula.PASSEIO_CULTURA.value:
            texto_relatorio += (
                f"Local da Atividade: {aula.nome_local}\n"
                f"Endereço: {aula.endereco_local}\n"
                f"Autorização dos pais exigida: {'Sim' if aula.autorizacao_pais else 'Não'}\n\n"
            )
        texto_relatorio += f"Conteúdo e Observações:\n{aula.observacoes}\n"

        try:
            from reportlab.pdfgen import canvas
            pdf = canvas.Canvas(caminho)
            pdf.setTitle(f"Aula - {aula.data}")
            pdf.setFont("Helvetica-Bold", 14)
            y = 800
            for linha in texto_relatorio.splitlines():
                pdf.drawString(50, y, linha[:100])
                y -= 20
            pdf.save()
            messagebox.showinfo("Sucesso", "Relatório PDF gerado com sucesso!")
        except ImportError:
            caminho_txt = os.path.splitext(caminho)[0] + ".txt"
            with open(caminho_txt, "w", encoding="utf-8") as f:
                f.write(texto_relatorio)
            messagebox.showinfo("Sucesso", f"Biblioteca reportlab não instalada. Salvo como TXT em:\n{caminho_txt}")

    def _salvar_agenda(self):
        with ARQUIVO_AGENDA.open("w", encoding="utf-8") as f:
            json.dump([asdict(a) for a in self.aulas_registradas], f, ensure_ascii=False, indent=2)

    def _carregar_agenda(self) -> list[Aula]:
        if not ARQUIVO_AGENDA.exists(): return []
        try:
            with ARQUIVO_AGENDA.open("r", encoding="utf-8") as f:
                return [Aula(**item) for item in json.load(f)]
        except: return []

if __name__ == "__main__":
    app = PlanejadorApp()
    app.mainloop()