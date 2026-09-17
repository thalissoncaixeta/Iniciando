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

class PlanejadorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Planejador de Aulas - Ensino Fundamental II")
        self.geometry("1150x700")
        self.minsize(950, 600)
        
        # Tema e Estilo
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TNotebook.Tab', padding=[15, 5], font=('Helvetica', 10, 'bold'))
        style.configure('TButton', font=('Helvetica', 10))
        
        # Carregamento de Estado e Configurações Dinâmicas
        self.aulas_registradas = self._carregar_agenda()
        self.config_dados = self._carregar_configuracoes()
        
        self.feriados_cadastrados = self.config_dados.get("feriados", {})
        self.turmas_cadastradas = self.config_dados.get("turmas", ["6º Ano A", "7º Ano A", "8º Ano A", "9º Ano A"])
        self.disciplinas_cadastradas = self.config_dados.get("disciplinas", ["Inglês", "Artes"])
        
        self.aula_em_edicao = None
        
        self._criar_interface()

    def _criar_interface(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.aba_agenda = ttk.Frame(self.notebook, padding=10)
        self.aba_editor = ttk.Frame(self.notebook, padding=10)
        self.aba_grade = ttk.Frame(self.notebook, padding=10)
        self.aba_config = ttk.Frame(self.notebook, padding=10)
        
        self.notebook.add(self.aba_agenda, text="📅 Agenda Geral")
        self.notebook.add(self.aba_editor, text="📝 Editor de Aula")
        self.notebook.add(self.aba_grade, text="⚡ Gerador de Grade")
        self.notebook.add(self.aba_config, text="⚙️ Configurações")
        
        self._construir_aba_agenda()
        self._construir_aba_editor()
        self._construir_aba_grade()
        self._construir_aba_config()
        
        self._marcar_calendario()

    # ================= ABA 1: AGENDA GERAL =================
    def _construir_aba_agenda(self):
        pane = ttk.PanedWindow(self.aba_agenda, orient=tk.HORIZONTAL)
        pane.pack(fill="both", expand=True)
        
        frame_cal = ttk.Frame(pane)
        pane.add(frame_cal, weight=1)
        
        ttk.Label(frame_cal, text="Selecione uma data:", font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(0,5))
        self.cal = Calendar(frame_cal, selectmode="day", date_pattern="yyyy-mm-dd", font="Helvetica 10")
        self.cal.pack(fill="both", expand=True)
        self.cal.bind("<<CalendarSelected>>", self._ao_selecionar_data_calendario)
        
        frame_lista = ttk.Frame(pane)
        pane.add(frame_lista, weight=2)
        
        ttk.Label(frame_lista, text="Aulas Registradas:", font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(0,5))
        
        self.lista_aulas = tk.Listbox(frame_lista, font=("Consolas", 11), selectbackground="#4a6984")
        self.lista_aulas.pack(fill="both", expand=True, side="left")
        
        scroll = ttk.Scrollbar(frame_lista, orient="vertical", command=self.lista_aulas.yview)
        scroll.pack(side="right", fill="y")
        self.lista_aulas.config(yscrollcommand=scroll.set)
        
        frame_botoes = ttk.Frame(self.aba_agenda)
        frame_botoes.pack(fill="x", pady=10)
        
        ttk.Button(frame_botoes, text="➕ Nova Aula nesta Data", command=self._nova_aula_pelo_calendario).pack(side="left", padx=5)
        ttk.Button(frame_botoes, text="✏️ Editar Selecionada", command=self._editar_aula_selecionada).pack(side="left", padx=5)
        ttk.Button(frame_botoes, text="🗑️ Excluir", command=self._excluir_aula).pack(side="left", padx=5)
        ttk.Button(frame_botoes, text="📄 Exportar PDF", command=self._exportar_pdf).pack(side="right", padx=5)
        
        self._atualizar_lista()

    # ================= ABA 2: EDITOR DE AULA =================
    def _construir_aba_editor(self):
        form_frame = ttk.LabelFrame(self.aba_editor, text="Detalhes do Planejamento", padding=20)
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.campos = {}
        
        ttk.Label(form_frame, text="Data:").grid(row=0, column=0, sticky="w", pady=10)
        self.campos['data'] = DateEntry(form_frame, width=15, background='darkblue', foreground='white', borderwidth=2, date_pattern="yyyy-mm-dd")
        self.campos['data'].grid(row=0, column=1, sticky="w", padx=5)
        
        ttk.Label(form_frame, text="Turma:").grid(row=1, column=0, sticky="w", pady=10)
        self.campos['turma'] = ttk.Combobox(form_frame, values=self.turmas_cadastradas, width=25)
        self.campos['turma'].grid(row=1, column=1, sticky="w", padx=5)

        ttk.Label(form_frame, text="Disciplina:").grid(row=1, column=2, sticky="w", pady=10, padx=(20,0))
        self.campos['disciplina'] = ttk.Combobox(form_frame, values=self.disciplinas_cadastradas, width=25)
        self.campos['disciplina'].grid(row=1, column=3, sticky="w", padx=5)

        ttk.Label(form_frame, text="Categoria:").grid(row=2, column=0, sticky="w", pady=10)
        self.campos['categoria'] = ttk.Combobox(form_frame, values=[c.value for c in CategoriaAula], state="readonly", width=40)
        self.campos['categoria'].set(CategoriaAula.TEORICA.value)
        self.campos['categoria'].grid(row=2, column=1, columnspan=3, sticky="w", padx=5)
        self.campos['categoria'].bind("<<ComboboxSelected>>", self._toggle_campos_passeio)

        self.frame_passeio = ttk.Frame(form_frame)
        self.frame_passeio.grid(row=3, column=0, columnspan=4, sticky="ew", pady=5)
        self.frame_passeio.grid_remove()

        ttk.Label(self.frame_passeio, text="Local:").grid(row=0, column=0, sticky="w")
        self.campos['nome_local'] = ttk.Entry(self.frame_passeio, width=22)
        self.campos['nome_local'].grid(row=0, column=1, padx=5)
        
        ttk.Label(self.frame_passeio, text="Endereço:").grid(row=0, column=2, sticky="w", padx=(10,0))
        self.campos['endereco_local'] = ttk.Entry(self.frame_passeio, width=30)
        self.campos['endereco_local'].grid(row=0, column=3, padx=5)
        
        self.campos['autorizacao_pais'] = tk.BooleanVar()
        ttk.Checkbutton(self.frame_passeio, text="Exige Autorização dos Pais", variable=self.campos['autorizacao_pais']).grid(row=1, column=0, columnspan=4, sticky="w", pady=10)

        ttk.Label(form_frame, text="Conteúdo / Obs:").grid(row=4, column=0, sticky="nw", pady=10)
        self.obs_text = tk.Text(form_frame, height=8, width=65, font=("Helvetica", 10))
        self.obs_text.grid(row=4, column=1, columnspan=3, sticky="w", padx=5)

        btn_frame = ttk.Frame(self.aba_editor)
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        ttk.Button(btn_frame, text="💾 Salvar Aula", command=self._salvar_aula).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="🧹 Limpar Formulário", command=self._limpar_form).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="❌ Cancelar Edição", command=self._cancelar_edicao).pack(side="left", padx=5)

    # ================= ABA 3: GERADOR DE GRADE =================
    def _construir_aba_grade(self):
        container = ttk.Frame(self.aba_grade, padding=20)
        container.pack(fill="both", expand=True)
        
        ttk.Label(container, text="Automação de Planejamento", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 15))
        ttk.Label(container, text="Configure a repetição semanal. O sistema irá ignorar os feriados cadastrados automaticamente.", foreground="gray").pack(anchor="w", pady=(0, 20))

        form = ttk.Frame(container)
        form.pack(fill="x")
        
        ttk.Label(form, text="Turma:").grid(row=0, column=0, sticky="w", pady=5)
        self.combo_turma_grade = ttk.Combobox(form, values=self.turmas_cadastradas, width=25)
        self.combo_turma_grade.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        
        ttk.Label(form, text="Disciplina:").grid(row=1, column=0, sticky="w", pady=5)
        self.combo_disc_grade = ttk.Combobox(form, values=self.disciplinas_cadastradas, width=25)
        self.combo_disc_grade.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        dias_frame = ttk.LabelFrame(container, text="Dias da Semana da Aula", padding=10)
        dias_frame.pack(fill="x", pady=20)
        
        self.vars_dias_grade = []
        nomes_dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
        for i, nome in enumerate(nomes_dias):
            var = tk.BooleanVar()
            self.vars_dias_grade.append((i, var))
            ttk.Checkbutton(dias_frame, text=nome, variable=var).pack(side="left", padx=15)

        ttk.Button(container, text="⚡ Gerar Grade para os Próximos 60 Dias", command=self._executar_gerador).pack(pady=30)

    # ================= ABA 4: CONFIGURAÇÕES DINÂMICAS =================
    def _construir_aba_config(self):
        container = ttk.Frame(self.aba_config, padding=20)
        container.pack(fill="both", expand=True)
        
        ttk.Label(container, text="Painel de Configurações do Professor", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 15))
        
        # Grid para 3 colunas
        grid_frame = ttk.Frame(container)
        grid_frame.pack(fill="both", expand=True, pady=10)
        
        # Coluna 1: Feriados
        frame_f = ttk.LabelFrame(grid_frame, text="Feriados (YYYY-MM-DD; Nome)", padding=10)
        frame_f.grid(row=0, column=0, sticky="nsew", padx=5)
        self.text_feriados = tk.Text(frame_f, height=12, width=30, font=("Consolas", 10))
        self.text_feriados.pack(fill="both", expand=True)
        
        # Coluna 2: Turmas
        frame_t = ttk.LabelFrame(grid_frame, text="Turmas (Uma por linha)", padding=10)
        frame_t.grid(row=0, column=1, sticky="nsew", padx=5)
        self.text_turmas = tk.Text(frame_t, height=12, width=30, font=("Consolas", 10))
        self.text_turmas.pack(fill="both", expand=True)
        
        # Coluna 3: Disciplinas
        frame_d = ttk.LabelFrame(grid_frame, text="Disciplinas (Uma por linha)", padding=10)
        frame_d.grid(row=0, column=2, sticky="nsew", padx=5)
        self.text_disciplinas = tk.Text(frame_d, height=12, width=30, font=("Consolas", 10))
        self.text_disciplinas.pack(fill="both", expand=True)
        
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.columnconfigure(2, weight=1)
        
        self._preencher_textos_config()
        
        ttk.Button(container, text="💾 Salvar Todas as Configurações", command=self._salvar_configuracoes).pack(pady=15)

    # ================= INTERAÇÕES E LÓGICA =================

    def _preencher_textos_config(self):
        self.text_feriados.delete("1.0", tk.END)
        for data, nome in sorted(self.feriados_cadastrados.items()):
            self.text_feriados.insert(tk.END, f"{data}; {nome}\n")
            
        self.text_turmas.delete("1.0", tk.END)
        self.text_turmas.insert(tk.END, "\n".join(self.turmas_cadastradas))
        
        self.text_disciplinas.delete("1.0", tk.END)
        self.text_disciplinas.insert(tk.END, "\n".join(self.disciplinas_cadastradas))

    def _salvar_configuracoes(self):
        # 1. Processar Feriados
        texto_f = self.text_feriados.get("1.0", tk.END).splitlines()
        feriados_novos = {}
        for linha in texto_f:
            if ";" in linha:
                d, n = [p.strip() for p in linha.split(";", 1)]
                try:
                    datetime.strptime(d, "%Y-%m-%d")
                    feriados_novos[d] = n
                except ValueError: continue
                
        # 2. Processar Turmas e Disciplinas (Ignora linhas em branco)
        turmas_novas = [t.strip() for t in self.text_turmas.get("1.0", tk.END).splitlines() if t.strip()]
        disc_novas = [d.strip() for d in self.text_disciplinas.get("1.0", tk.END).splitlines() if d.strip()]
        
        # 3. Atualizar estado interno
        self.feriados_cadastrados = feriados_novos
        self.turmas_cadastradas = turmas_novas
        self.disciplinas_cadastradas = disc_novas
        
        # 4. Salvar no JSON
        dados = {
            "feriados": feriados_novos,
            "turmas": turmas_novas,
            "disciplinas": disc_novas
        }
        with ARQUIVO_CONFIGURACAO.open("w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
            
        # 5. Atualizar a UI Dinamicamente
        self._marcar_calendario()
        self.campos['turma'].config(values=self.turmas_cadastradas)
        self.combo_turma_grade.config(values=self.turmas_cadastradas)
        self.campos['disciplina'].config(values=self.disciplinas_cadastradas)
        self.combo_disc_grade.config(values=self.disciplinas_cadastradas)
        
        messagebox.showinfo("Sucesso", "Configurações, turmas e disciplinas salvas e atualizadas!")

    def _carregar_configuracoes(self) -> dict:
        if not ARQUIVO_CONFIGURACAO.exists(): return {}
        try:
            with ARQUIVO_CONFIGURACAO.open("r", encoding="utf-8") as f:
                dados = json.load(f)
                # Migração: Se o arquivo antigo tinha apenas feriados soltos no dict
                if dados and not any(k in dados for k in ["feriados", "turmas", "disciplinas"]):
                    return {"feriados": dados}
                return dados
        except: return {}

    # (Os métodos restantes permanecem idênticos ao código anterior)
    def _toggle_campos_passeio(self, event=None):
        if self.campos['categoria'].get() == CategoriaAula.PASSEIO_CULTURA.value:
            self.frame_passeio.grid()
        else:
            self.frame_passeio.grid_remove()

    def _ao_selecionar_data_calendario(self, event):
        data_str = self.cal.get_date()
        data_obj = datetime.strptime(data_str, "%Y-%m-%d").date()
        self.campos['data'].set_date(data_obj)

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
        self._limpar_form()
        messagebox.showinfo("Sucesso", "Aula salva na agenda!")
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
        
        for i in range(60):
            data_alvo = data_atual + timedelta(days=i)
            data_str = data_alvo.strftime("%Y-%m-%d")
            
            if data_alvo.weekday() in dias_selecionados and data_str not in self.feriados_cadastrados:
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
            messagebox.showinfo("Sucesso", f"{aulas_geradas} aulas agendadas com sucesso!")
            self.notebook.select(self.aba_agenda)
        else:
            messagebox.showinfo("Aviso", "Nenhuma aula nova gerada (já existiam ou coincidiram com feriados).")

    def _marcar_calendario(self):
        self.cal.calevent_remove("all")
        self.cal.tag_config("feriado", background="#f8d7da", foreground="#842029")
        for data_iso, nome in self.feriados_cadastrados.items():
            data_obj = date.fromisoformat(data_iso)
            self.cal.calevent_create(data_obj, nome, tags="feriado")

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

        texto_relatorio = (
            f"Relatório de Aula - {aula.data}\n"
            f"Turma: {aula.turma} | Disciplina: {aula.disciplina}\n"
            f"Categoria: {aula.categoria}\n\n"
        )
        if aula.categoria == CategoriaAula.PASSEIO_CULTURA.value:
            texto_relatorio += (
                f"Local: {aula.nome_local}\n"
                f"Endereço: {aula.endereco_local}\n"
                f"Autorização dos pais exigida: {'Sim' if aula.autorizacao_pais else 'Não'}\n\n"
            )
        texto_relatorio += f"Observações / Conteúdo:\n{aula.observacoes}\n"

        try:
            from reportlab.pdfgen import canvas
            pdf = canvas.Canvas(caminho)
            pdf.setTitle(f"Aula - {aula.data}")
            pdf.setFont("Helvetica-Bold", 14)
            y = 800
            for linha in texto_relatorio.splitlines():
                pdf.drawString(50, y, linha[:110])
                y -= 20
            pdf.save()
            messagebox.showinfo("Sucesso", "PDF gerado com sucesso!")
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