import json
import os
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from tkcalendar import Calendar
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
        self.geometry("1280x850")
        self.minsize(1100, 750)
        
        # Estado do Aplicativo
        self.aulas_registradas = self._carregar_agenda()
        self.feriados_cadastrados = self._carregar_feriados()
        self.aula_em_edicao = None
        
        # Dados de Domínio (Pode ser alterado conforme a grade real sair)
        self.turmas_padrao = ["6º Ano A", "7º Ano A", "8º Ano A", "9º Ano A"]
        self.disciplinas_padrao = ["Inglês", "Artes"]
        
        self._criar_interface()

    def _criar_interface(self):
        # Frame Principal - Dividido em Esquerda (Calendário/Config) e Direita (Formulário/Lista)
        pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        pane.pack(fill="both", expand=True, padx=10, pady=10)
        
        frame_esq = ttk.Frame(pane)
        frame_dir = ttk.Frame(pane)
        pane.add(frame_esq, weight=1)
        pane.add(frame_dir, weight=3)

        # ================= ESQUERDA: Calendário e Feriados =================
        ttk.Label(frame_esq, text="Calendário", font=("Helvetica", 12, "bold")).pack(pady=(0, 5))
        self.cal = Calendar(frame_esq, selectmode="day", date_pattern="yyyy-mm-dd")
        self.cal.pack(fill="x", pady=5)
        self.cal.bind("<<CalendarSelected>>", self._on_data_selecionada)

        config_frame = ttk.LabelFrame(frame_esq, text="Feriados (YYYY-MM-DD; Nome)", padding=5)
        config_frame.pack(fill="both", expand=True, pady=10)
        self.text_feriados = tk.Text(config_frame, height=10, width=30)
        self.text_feriados.pack(fill="both", expand=True, pady=5)
        self._atualizar_texto_feriados()
        ttk.Button(config_frame, text="Salvar Feriados", command=self._salvar_feriados).pack(fill="x")

        # ================= DIREITA: Formulário e Ações =================
        form_frame = ttk.LabelFrame(frame_dir, text="Detalhes da Aula", padding=10)
        form_frame.pack(fill="x", pady=(0, 10))

        self.campos = {}
        
        # Linha 1
        ttk.Label(form_frame, text="Turma:").grid(row=0, column=0, sticky="w", pady=5)
        self.campos['turma'] = ttk.Combobox(form_frame, values=self.turmas_padrao)
        self.campos['turma'].grid(row=0, column=1, sticky="ew", padx=5)

        ttk.Label(form_frame, text="Disciplina:").grid(row=0, column=2, sticky="w", pady=5)
        self.campos['disciplina'] = ttk.Combobox(form_frame, values=self.disciplinas_padrao)
        self.campos['disciplina'].grid(row=0, column=3, sticky="ew", padx=5)

        # Linha 2
        ttk.Label(form_frame, text="Categoria:").grid(row=1, column=0, sticky="w", pady=5)
        self.campos['categoria'] = ttk.Combobox(form_frame, values=[c.value for c in CategoriaAula], state="readonly")
        self.campos['categoria'].set(CategoriaAula.TEORICA.value)
        self.campos['categoria'].grid(row=1, column=1, sticky="ew", padx=5)
        self.campos['categoria'].bind("<<ComboboxSelected>>", self._toggle_campos_passeio)

        # Campos Específicos Passeio Cultural (Ocultos por padrão)
        self.frame_passeio = ttk.Frame(form_frame)
        self.frame_passeio.grid(row=2, column=0, columnspan=4, sticky="ew", pady=5)
        self.frame_passeio.grid_remove() # Esconde inicialmente

        ttk.Label(self.frame_passeio, text="Local:").grid(row=0, column=0, sticky="w")
        self.campos['nome_local'] = ttk.Entry(self.frame_passeio, width=25)
        self.campos['nome_local'].grid(row=0, column=1, padx=5)
        
        ttk.Label(self.frame_passeio, text="Endereço:").grid(row=0, column=2, sticky="w")
        self.campos['endereco_local'] = ttk.Entry(self.frame_passeio, width=25)
        self.campos['endereco_local'].grid(row=0, column=3, padx=5)
        
        self.campos['autorizacao_pais'] = tk.BooleanVar()
        ttk.Checkbutton(self.frame_passeio, text="Exige Autorização", variable=self.campos['autorizacao_pais']).grid(row=1, column=0, columnspan=2, sticky="w", pady=5)

        # Observações (Sempre visível)
        ttk.Label(form_frame, text="Conteúdo / Obs:").grid(row=3, column=0, sticky="nw", pady=5)
        self.obs_text = tk.Text(form_frame, height=4, width=50)
        self.obs_text.grid(row=3, column=1, columnspan=3, sticky="ew", padx=5)

        form_frame.columnconfigure(1, weight=1)
        form_frame.columnconfigure(3, weight=1)

        # BOTOÕES DE AÇÃO
        btn_frame = ttk.Frame(frame_dir)
        btn_frame.pack(fill="x", pady=5)
        
        ttk.Button(btn_frame, text="Salvar Aula", command=self._salvar_aula).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Limpar", command=self._limpar_form).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Excluir Selecionada", command=self._excluir_aula).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Exportar Relatório PDF", command=self._exportar_pdf).pack(side="left", padx=5)
        
        # Botão Mágico
        btn_gerar = ttk.Button(btn_frame, text="⚡ Gerar Grade Automática", command=self._abrir_gerador_grade)
        btn_gerar.pack(side="right", padx=5)

        # LISTA DE AULAS
        lista_frame = ttk.LabelFrame(frame_dir, text="Planejamento Registrado", padding=10)
        lista_frame.pack(fill="both", expand=True)
        
        self.lista_aulas = tk.Listbox(lista_frame, font=("Consolas", 10))
        self.lista_aulas.pack(fill="both", expand=True, side="left")
        
        scroll = ttk.Scrollbar(lista_frame, orient="vertical", command=self.lista_aulas.yview)
        scroll.pack(side="right", fill="y")
        self.lista_aulas.config(yscrollcommand=scroll.set)
        self.lista_aulas.bind("<<ListboxSelect>>", self._on_lista_selecionada)
        
        self._atualizar_lista()
        self._marcar_calendario()

    # ================= REGRAS DE NEGÓCIO E MÉTODOS =================
    
    def _toggle_campos_passeio(self, event=None):
        if self.campos['categoria'].get() == CategoriaAula.PASSEIO_CULTURA.value:
            self.frame_passeio.grid()
        else:
            self.frame_passeio.grid_remove()

    def _salvar_aula(self):
        data_str = self.cal.get_date() # Retorna YYYY-MM-DD devido ao date_pattern
        
        nova_aula = Aula(
            data=data_str,
            turma=self.campos['turma'].get(),
            disciplina=self.campos['disciplina'].get(),
            categoria=self.campos['categoria'].get(),
            nome_local=self.campos.get('nome_local').get() if self.campos.get('nome_local') else "",
            endereco_local=self.campos.get('endereco_local').get() if self.campos.get('endereco_local') else "",
            observacoes=self.obs_text.get("1.0", tk.END).strip(),
            autorizacao_pais=self.campos['autorizacao_pais'].get()
        )
        
        if self.aula_em_edicao:
            idx = self.aulas_registradas.index(self.aula_em_edicao)
            self.aulas_registradas[idx] = nova_aula
            self.aula_em_edicao = None
        else:
            self.aulas_registradas.append(nova_aula)
            
        self._salvar_agenda()
        self._atualizar_lista()
        self._limpar_form()
        messagebox.showinfo("Sucesso", "Aula registrada na agenda!")

    def _excluir_aula(self):
        if not self.aula_em_edicao:
            messagebox.showwarning("Aviso", "Selecione uma aula na lista primeiro.")
            return
        
        if messagebox.askyesno("Confirmar", "Deseja excluir esta aula?"):
            self.aulas_registradas.remove(self.aula_em_edicao)
            self._salvar_agenda()
            self._atualizar_lista()
            self._limpar_form()

    def _atualizar_lista(self):
        self.lista_aulas.delete(0, tk.END)
        self.aulas_registradas.sort(key=lambda x: x.data)
        
        for idx, aula in enumerate(self.aulas_registradas):
            data_br = datetime.strptime(aula.data, "%Y-%m-%d").strftime("%d/%m/%Y")
            linha = f"[{data_br}] {aula.turma} - {aula.disciplina} | {aula.categoria}"
            self.lista_aulas.insert(tk.END, linha)

    def _on_lista_selecionada(self, event):
        if not self.lista_aulas.curselection(): return
        idx = self.lista_aulas.curselection()[0]
        self.aula_em_edicao = self.aulas_registradas[idx]
        
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
        
        data_obj = datetime.strptime(self.aula_em_edicao.data, "%Y-%m-%d").date()
        self.cal.selection_set(data_obj)
        self._toggle_campos_passeio()

    def _on_data_selecionada(self, event):
        self._limpar_form() # Preparar para nova inserção na nova data

    def _limpar_form(self):
        self.aula_em_edicao = None
        self.campos['turma'].set('')
        self.campos['disciplina'].set('')
        self.campos['categoria'].set(CategoriaAula.TEORICA.value)
        self.campos['nome_local'].delete(0, tk.END)
        self.campos['endereco_local'].delete(0, tk.END)
        self.campos['autorizacao_pais'].set(False)
        self.obs_text.delete("1.0", tk.END)
        self._toggle_campos_passeio()
        self.lista_aulas.selection_clear(0, tk.END)

    # ================= FERIADOS E CALENDÁRIO =================
    
    def _carregar_feriados(self) -> dict:
        if not ARQUIVO_CONFIGURACAO.exists(): return {}
        try:
            with ARQUIVO_CONFIGURACAO.open("r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}

    def _atualizar_texto_feriados(self):
        self.text_feriados.delete("1.0", tk.END)
        for data, nome in sorted(self.feriados_cadastrados.items()):
            self.text_feriados.insert(tk.END, f"{data}; {nome}\n")

    def _salvar_feriados(self):
        texto = self.text_feriados.get("1.0", tk.END).splitlines()
        self.feriados_cadastrados.clear()
        
        for linha in texto:
            if ";" in linha:
                data_txt, nome = [p.strip() for p in linha.split(";", 1)]
                try:
                    datetime.strptime(data_txt, "%Y-%m-%d") # Valida
                    self.feriados_cadastrados[data_txt] = nome
                except ValueError: continue
                
        with ARQUIVO_CONFIGURACAO.open("w", encoding="utf-8") as f:
            json.dump(self.feriados_cadastrados, f, ensure_ascii=False, indent=2)
            
        self._marcar_calendario()
        messagebox.showinfo("Salvo", "Feriados atualizados!")

    def _marcar_calendario(self):
        self.cal.calevent_remove("all")
        self.cal.tag_config("feriado", background="#f8d7da", foreground="#842029")
        
        for data_iso, nome in self.feriados_cadastrados.items():
            data_obj = date.fromisoformat(data_iso)
            self.cal.calevent_create(data_obj, nome, tags="feriado")

    # ================= GERADOR DE GRADE (O ELEMENTO SURPRESA) =================
    
    def _abrir_gerador_grade(self):
        top = tk.Toplevel(self)
        top.title("Gerar Grade de Aulas")
        top.geometry("400x350")
        
        ttk.Label(top, text="Turma:").pack(pady=2)
        combo_turma = ttk.Combobox(top, values=self.turmas_padrao)
        combo_turma.pack()
        
        ttk.Label(top, text="Disciplina:").pack(pady=2)
        combo_disc = ttk.Combobox(top, values=self.disciplinas_padrao)
        combo_disc.pack()
        
        # Frame de Dias da Semana
        dias_frame = ttk.LabelFrame(top, text="Dias da Semana", padding=5)
        dias_frame.pack(fill="x", padx=20, pady=10)
        
        vars_dias = []
        nomes_dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
        for i, nome in enumerate(nomes_dias):
            var = tk.BooleanVar()
            vars_dias.append((i, var)) # 0=Segunda, 4=Sexta (padrão Python)
            ttk.Checkbutton(dias_frame, text=nome, variable=var).pack(anchor="w")

        def executar_geracao():
            turma = combo_turma.get()
            disc = combo_disc.get()
            dias_selecionados = [i for i, var in vars_dias if var.get()]
            
            if not turma or not disc or not dias_selecionados:
                messagebox.showerror("Erro", "Preencha Turma, Disciplina e pelo menos um dia da semana.")
                return
                
            # Exemplo: Gerar para os próximos 60 dias (pode ser adaptado para pegar input de data fim)
            data_atual = date.today()
            aulas_geradas = 0
            
            for i in range(60):
                data_alvo = data_atual + timedelta(days=i)
                data_str = data_alvo.strftime("%Y-%m-%d")
                
                # Se for o dia da semana selecionado E não for feriado cadastrado
                if data_alvo.weekday() in dias_selecionados and data_str not in self.feriados_cadastrados:
                    # Verifica se já não tem essa mesma aula nesse dia
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
                messagebox.showinfo("Sucesso", f"{aulas_geradas} aulas geradas com sucesso, ignorando feriados!")
                top.destroy()
            else:
                messagebox.showinfo("Aviso", "Nenhuma aula nova gerada (já existiam ou só caíram em feriados).")

        ttk.Button(top, text="Gerar Planejamento", command=executar_geracao).pack(pady=15)

    # ================= EXPORTAÇÃO E PERSISTÊNCIA =================
    
    def _exportar_pdf(self):
        if not self.aula_em_edicao:
            messagebox.showwarning("Aviso", "Selecione uma aula na lista para exportar.")
            return
            
        caminho = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Arquivo PDF", "*.pdf"), ("Arquivo de texto", "*.txt")],
            title="Salvar Relatório de Aula"
        )
        if not caminho: return

        texto_relatorio = (
            f"Relatório de Aula - {self.aula_em_edicao.data}\n"
            f"Turma: {self.aula_em_edicao.turma} | Disciplina: {self.aula_em_edicao.disciplina}\n"
            f"Categoria: {self.aula_em_edicao.categoria}\n\n"
        )
        if self.aula_em_edicao.categoria == CategoriaAula.PASSEIO_CULTURA.value:
            texto_relatorio += (
                f"Local: {self.aula_em_edicao.nome_local}\n"
                f"Endereço: {self.aula_em_edicao.endereco_local}\n"
                f"Autorização dos pais exigida: {'Sim' if self.aula_em_edicao.autorizacao_pais else 'Não'}\n\n"
            )
        texto_relatorio += f"Observações / Conteúdo:\n{self.aula_em_edicao.observacoes}\n"

        try:
            from reportlab.pdfgen import canvas
            pdf = canvas.Canvas(caminho)
            pdf.setTitle(f"Aula - {self.aula_em_edicao.data}")
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