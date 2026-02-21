"""
╔══════════════════════════════════════════════════════╗
║   FINANCEFLOW v3  —  Controlador Financeiro Premium  ║
║   pip install customtkinter matplotlib pillow        ║
╚══════════════════════════════════════════════════════╝
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import sqlite3, csv, os
from datetime import datetime

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG      = "#080B14"
SB      = "#0C0F1E"
CARD    = "#111527"
CARD2   = "#171C30"
BORDER  = "#1F2540"
ACCENT  = "#7C6EFA"
A2      = "#F472B6"
GREEN   = "#10D9A0"
RED     = "#F4546A"
YELLOW  = "#FBBF24"
BLUE    = "#38BDF8"
TEXT    = "#E2E8F0"
TEXT2   = "#7C87A0"
TEXT3   = "#3D4460"
WHITE   = "#FFFFFF"

MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
CATS_D = ["🍔 Alimentação","🏠 Moradia","🚗 Transporte","💊 Saúde","🎓 Educação",
          "👗 Vestuário","🎮 Lazer","💳 Dívidas","💡 Contas","📱 Assinaturas",
          "🐾 Pets","🎁 Presentes","✈️ Viagens","📦 Compras","🔧 Manutenção",
          "💰 Investimentos","🏋️ Academia","💈 Beleza","🍕 Delivery","Outros"]
CATS_R = ["💼 Salário","🏢 Freelance","📈 Investimentos","🏠 Aluguel",
          "🎁 Presente","💸 Reembolso","💰 Bônus","🛒 Venda","Outros"]

def M(v, m="R$"):
    s = f"{abs(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
    return f"{m} {s}"

def _mix(c1, c2="#ffffff", t=0.18):
    def h(c): c=c.lstrip("#"); return tuple(int(c[i:i+2],16) for i in (0,2,4))
    r1,g1,b1=h(c1); r2,g2,b2=h(c2)
    return "#{:02x}{:02x}{:02x}".format(int(r1+(r2-r1)*t),int(g1+(g2-g1)*t),int(b1+(b2-b1)*t))

class DB:
    def __init__(self):
        self.path = os.path.join(os.path.expanduser("~"), "financeflow3.db")
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS tx(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT, desc TEXT, valor REAL,
            cat TEXT, data TEXT, conta TEXT DEFAULT 'Principal',
            obs TEXT, rec INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS contas(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE, tipo TEXT DEFAULT 'Corrente',
            saldo_ini REAL DEFAULT 0, cor TEXT DEFAULT '#7C6EFA', ativo INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS metas(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT, alvo REAL, atual REAL DEFAULT 0,
            prazo TEXT, cor TEXT DEFAULT '#10D9A0', ativo INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS orc(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cat TEXT, limite REAL, mes INTEGER, ano INTEGER);
        CREATE TABLE IF NOT EXISTS div(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT, total REAL, pago REAL DEFAULT 0,
            juros REAL DEFAULT 0, parcelas INTEGER DEFAULT 1,
            parc_atual INTEGER DEFAULT 0, venc TEXT, credor TEXT, ativo INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS cfg(chave TEXT PRIMARY KEY, valor TEXT);
        INSERT OR IGNORE INTO contas VALUES(1,'Principal','Corrente',0,'#7C6EFA',1);
        INSERT OR IGNORE INTO contas VALUES(2,'Poupança','Poupança',0,'#10D9A0',1);
        INSERT OR IGNORE INTO contas VALUES(3,'Carteira','Espécie',0,'#FBBF24',1);
        INSERT OR IGNORE INTO cfg VALUES('nome','Usuário');
        INSERT OR IGNORE INTO cfg VALUES('moeda','R$');
        """)
        self.conn.commit()

    def q(self, sql, p=()):   return self.conn.execute(sql,p).fetchall()
    def run(self, sql, p=()):
        c=self.conn.execute(sql,p); self.conn.commit(); return c.lastrowid
    def cfg(self, k, v=None):
        if v is not None: self.run("INSERT OR REPLACE INTO cfg VALUES(?,?)",(k,v))
        else:
            r=self.q("SELECT valor FROM cfg WHERE chave=?",(k,))
            return r[0][0] if r else ""

    def add_tx(self,tipo,desc,valor,cat,data,conta,obs="",rec=0):
        return self.run("INSERT INTO tx(tipo,desc,valor,cat,data,conta,obs,rec) VALUES(?,?,?,?,?,?,?,?)",
                        (tipo,desc,valor,cat,data,conta,obs,rec))
    def get_tx(self,filtro="",mes=None,ano=None,tipo=None,limit=500):
        sql="SELECT * FROM tx WHERE 1=1"; p=[]
        if filtro: sql+=" AND (desc LIKE ? OR cat LIKE ?)"; p+=[f"%{filtro}%"]*2
        if mes:    sql+=" AND strftime('%m',data)=?"; p.append(f"{mes:02d}")
        if ano:    sql+=" AND strftime('%Y',data)=?"; p.append(str(ano))
        if tipo:   sql+=" AND tipo=?"; p.append(tipo)
        sql+=" ORDER BY data DESC,id DESC LIMIT ?"; p.append(limit)
        return self.q(sql,p)
    def del_tx(self,i): self.run("DELETE FROM tx WHERE id=?",(i,))
    def resumo(self,mes,ano):
        r=self.q("""SELECT SUM(CASE WHEN tipo='receita' THEN valor ELSE 0 END) r,
            SUM(CASE WHEN tipo='despesa' THEN valor ELSE 0 END) d FROM tx
            WHERE strftime('%m',data)=? AND strftime('%Y',data)=?""",
            (f"{mes:02d}",str(ano)))[0]
        rc=r[0] or 0; de=r[1] or 0; return rc,de,rc-de
    def por_cat(self,tipo,mes=None,ano=None):
        sql="SELECT cat,SUM(valor) t FROM tx WHERE tipo=?"; p=[tipo]
        if mes: sql+=" AND strftime('%m',data)=?"; p.append(f"{mes:02d}")
        if ano: sql+=" AND strftime('%Y',data)=?"; p.append(str(ano))
        return self.q(sql+" GROUP BY cat ORDER BY t DESC",p)
    def evolucao(self,ano):
        rows=self.q("""SELECT strftime('%m',data) m,tipo,SUM(valor) t
            FROM tx WHERE strftime('%Y',data)=? GROUP BY m,tipo""",(str(ano),))
        r=[0]*12; d=[0]*12
        for row in rows:
            i=int(row["m"])-1
            if row["tipo"]=="receita": r[i]=row["t"]
            else: d[i]=row["t"]
        return r,d
    def saldo_contas(self):
        return self.q("""SELECT c.nome,c.tipo,c.saldo_ini,c.cor,
            COALESCE(SUM(CASE WHEN t.tipo='receita' THEN t.valor
                             WHEN t.tipo='despesa' THEN -t.valor ELSE 0 END),0) mov
            FROM contas c LEFT JOIN tx t ON t.conta=c.nome
            WHERE c.ativo=1 GROUP BY c.nome""")
    def add_meta(self,nome,alvo,prazo,cor):
        return self.run("INSERT INTO metas(nome,alvo,prazo,cor) VALUES(?,?,?,?)",(nome,alvo,prazo,cor))
    def get_metas(self): return self.q("SELECT * FROM metas WHERE ativo=1 ORDER BY id DESC")
    def dep_meta(self,i,v): self.run("UPDATE metas SET atual=atual+? WHERE id=?",(v,i))
    def del_meta(self,i): self.run("UPDATE metas SET ativo=0 WHERE id=?",(i,))
    def set_orc(self,cat,lim,mes,ano):
        self.run("DELETE FROM orc WHERE cat=? AND mes=? AND ano=?",(cat,mes,ano))
        self.run("INSERT INTO orc(cat,limite,mes,ano) VALUES(?,?,?,?)",(cat,lim,mes,ano))
    def get_orc(self,mes,ano): return self.q("SELECT * FROM orc WHERE mes=? AND ano=?",(mes,ano))
    def add_div(self,nome,total,juros,parc,venc,cred):
        return self.run("INSERT INTO div(nome,total,juros,parcelas,venc,credor) VALUES(?,?,?,?,?,?)",
                        (nome,total,juros,parc,venc,cred))
    def get_div(self): return self.q("SELECT * FROM div WHERE ativo=1 ORDER BY venc")
    def pagar(self,i,v): self.run("UPDATE div SET pago=pago+?,parc_atual=parc_atual+1 WHERE id=?",(v,i))
    def del_div(self,i): self.run("UPDATE div SET ativo=0 WHERE id=?",(i,))


class Card(ctk.CTkFrame):
    def __init__(self, p, accent=None, **kw):
        super().__init__(p, fg_color=CARD, corner_radius=14,
                         border_width=1, border_color=BORDER, **kw)
        if accent:
            ctk.CTkFrame(self, fg_color=accent, height=3,
                         corner_radius=0).pack(fill="x")

class MiniCard(ctk.CTkFrame):
    def __init__(self, p, icon, title, value, sub, color, **kw):
        super().__init__(p, fg_color=CARD, corner_radius=14,
                         border_width=1, border_color=BORDER, **kw)
        ctk.CTkFrame(self, fg_color=color, height=3, corner_radius=0).pack(fill="x")
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12,0))
        ctk.CTkLabel(top, text=icon, font=("Segoe UI",18)).pack(side="left")
        ctk.CTkLabel(top, text=title, font=("Segoe UI",11), text_color=TEXT2).pack(side="left", padx=8)
        self.val = ctk.CTkLabel(self, text=value, font=("Segoe UI",22,"bold"), text_color=WHITE)
        self.val.pack(anchor="w", padx=16, pady=(4,0))
        ctk.CTkLabel(self, text=sub, font=("Segoe UI",10), text_color=color).pack(anchor="w", padx=16, pady=(2,12))

class PBar(ctk.CTkFrame):
    def __init__(self, p, pct, color=ACCENT, h=8, **kw):
        super().__init__(p, fg_color=CARD2, corner_radius=4, height=h, **kw)
        pct=min(max(pct,0),1)
        if pct>0:
            ctk.CTkFrame(self, fg_color=color, corner_radius=4, height=h).place(
                relx=0, rely=0, relwidth=pct, relheight=1)

class Btn(ctk.CTkButton):
    def __init__(self, p, text, cmd, color=ACCENT, w=None, h=34, **kw):
        kw2=dict(fg_color=color, hover_color=_mix(color,"#ffffff",0.2),
                 font=("Segoe UI",12,"bold"), corner_radius=8,
                 border_width=0, height=h, text_color=WHITE)
        if w: kw2["width"]=w
        super().__init__(p, text=text, command=cmd, **kw2, **kw)

class Div(ctk.CTkFrame):
    def __init__(self, p, **kw):
        super().__init__(p, fg_color=BORDER, height=1, **kw)

def lbl(p, text, size=11, bold=False, color=None, **kw):
    return ctk.CTkLabel(p, text=text, font=("Segoe UI", size, "bold" if bold else "normal"),
                        text_color=color or TEXT2, **kw)

def ent(p, var, placeholder="", w=None, **kw):
    kwargs = dict(textvariable=var, fg_color=CARD2, border_color=BORDER, border_width=1,
                  font=("Segoe UI",12), corner_radius=8, text_color=TEXT,
                  placeholder_text=placeholder, placeholder_text_color=TEXT3)
    if w: kwargs["width"]=w
    return ctk.CTkEntry(p, **kwargs, **kw)

def cmb(p, values, var, **kw):
    return ctk.CTkComboBox(p, values=values, variable=var, state="readonly",
                           fg_color=CARD2, border_color=BORDER, button_color=ACCENT,
                           dropdown_fg_color=CARD2, font=("Segoe UI",12),
                           dropdown_font=("Segoe UI",12), **kw)


class Modal(ctk.CTkToplevel):
    def __init__(self, parent, title, w=460, h=500, accent=ACCENT):
        super().__init__(parent)
        self.title(title); self.geometry(f"{w}x{h}")
        self.configure(fg_color=BG); self.grab_set(); self.resizable(False,False)
        hdr = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, height=52)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        ctk.CTkFrame(hdr, fg_color=accent, width=4, corner_radius=0).pack(side="left", fill="y")
        ctk.CTkLabel(hdr, text=title, font=("Segoe UI",14,"bold"), text_color=WHITE).pack(side="left", padx=16)
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                           scrollbar_button_color=BORDER,
                                           scrollbar_button_hover_color=ACCENT)
        self.body.pack(fill="both", expand=True, padx=20, pady=12)
        self.body.grid_columnconfigure(0, weight=1)
        self._r = 0

    def add(self, label_txt, var=None, combo=False, values=None, default=None, placeholder=""):
        lbl(self.body, label_txt, 10, color=TEXT3).grid(row=self._r, column=0, sticky="w", pady=(6,1))
        self._r+=1
        if combo:
            var = var or ctk.StringVar(value=default or (values[0] if values else ""))
            cmb(self.body, values or [], var).grid(row=self._r, column=0, sticky="ew")
        else:
            var = var or ctk.StringVar(value=default or "")
            ent(self.body, var, placeholder).grid(row=self._r, column=0, sticky="ew")
        self._r+=1
        return var

    def footer(self, cancel, ok, ok_lbl="✓ Salvar", ok_col=ACCENT):
        f = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, height=56)
        f.pack(fill="x", side="bottom"); f.pack_propagate(False)
        Btn(f,"Cancelar",cancel,CARD2,h=34).pack(side="left", padx=16, pady=11)
        Btn(f, ok_lbl, ok, ok_col, h=34).pack(side="right", padx=16, pady=11)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.db    = DB()
        self.moeda = self.db.cfg("moeda") or "R$"
        self.nome  = self.db.cfg("nome")  or "Usuário"
        self.mes   = datetime.now().month
        self.ano   = datetime.now().year
        self._page = ""

        self.title("FinanceFlow"); self.geometry("1300x820")
        self.minsize(1100, 700); self.configure(fg_color=BG)
        self._build(); self._nav("dashboard")

    def _build(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self._sidebar()
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)
        self._topbar(main)
        self.body = ctk.CTkFrame(main, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0,18))
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)

    def _sidebar(self):
        sb = ctk.CTkFrame(self, fg_color=SB, width=210, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsew"); sb.pack_propagate(False)

        logo = ctk.CTkFrame(sb, fg_color="transparent", height=56)
        logo.pack(fill="x", padx=14, pady=(18,10)); logo.pack_propagate(False)
        dot = ctk.CTkFrame(logo, fg_color=ACCENT, width=32, height=32, corner_radius=8)
        dot.pack(side="left", pady=12)
        ctk.CTkLabel(dot, text="₣", font=("Segoe UI",15,"bold"), text_color=WHITE).place(relx=.5,rely=.5,anchor="center")
        ctk.CTkLabel(logo, text=" FinanceFlow", font=("Segoe UI",14,"bold"), text_color=WHITE).pack(side="left")

        Div(sb).pack(fill="x", padx=12, pady=(0,8))

        navs = [
            ("dashboard",  "📊", "Dashboard"),
            ("transacoes", "💸", "Transações"),
            ("graficos",   "📈", "Gráficos"),
            ("metas",      "🎯", "Metas"),
            ("dividas",    "💳", "Dívidas"),
            ("orcamento",  "📋", "Orçamento"),
            ("contas",     "🏦", "Contas"),
            ("relatorio",  "📄", "Relatório"),
            ("config",     "⚙️",  "Config"),
        ]
        self._nb = {}
        for pg, ico, name in navs:
            f = ctk.CTkFrame(sb, fg_color="transparent", height=38, cursor="hand2", corner_radius=8)
            f.pack(fill="x", padx=8, pady=1); f.pack_propagate(False)
            ind = ctk.CTkFrame(f, fg_color="transparent", width=3, corner_radius=2)
            ind.pack(side="left", fill="y", padx=(4,0))
            ico_l = ctk.CTkLabel(f, text=ico, font=("Segoe UI",14), width=28, text_color=TEXT3)
            ico_l.pack(side="left", padx=(6,4))
            name_l = ctk.CTkLabel(f, text=name, font=("Segoe UI",12), text_color=TEXT3, anchor="w")
            name_l.pack(side="left", fill="x", expand=True)
            self._nb[pg] = (f, ind, ico_l, name_l)
            for w in [f, ico_l, name_l]:
                w.bind("<Button-1>", lambda e,p=pg: self._nav(p))
                w.bind("<Enter>",    lambda e,f_=f,p_=pg: f_.configure(fg_color=CARD2) if self._page!=p_ else None)
                w.bind("<Leave>",    lambda e,f_=f,p_=pg: f_.configure(fg_color=CARD if self._page==p_ else "transparent"))

        ctk.CTkFrame(sb, fg_color="transparent").pack(fill="both", expand=True)
        Div(sb).pack(fill="x", padx=12, pady=4)

        uf = ctk.CTkFrame(sb, fg_color=CARD2, corner_radius=10, height=44)
        uf.pack(fill="x", padx=10, pady=(0,14)); uf.pack_propagate(False)
        av = ctk.CTkFrame(uf, fg_color=A2, width=28, height=28, corner_radius=14)
        av.pack(side="left", padx=(10,8), pady=8)
        ctk.CTkLabel(av, text=self.nome[0].upper(), font=("Segoe UI",11,"bold"), text_color=WHITE).place(relx=.5,rely=.5,anchor="center")
        self._user_lbl = ctk.CTkLabel(uf, text=self.nome, font=("Segoe UI",11), text_color=TEXT)
        self._user_lbl.pack(side="left")

    def _highlight_nav(self, page):
        for pg,(f,ind,ico_l,name_l) in self._nb.items():
            on = pg==page
            f.configure(fg_color=CARD if on else "transparent")
            ind.configure(fg_color=ACCENT if on else "transparent")
            ico_l.configure(text_color=ACCENT if on else TEXT3)
            name_l.configure(text_color=WHITE if on else TEXT3,
                             font=("Segoe UI",12,"bold") if on else ("Segoe UI",12))

    def _topbar(self, parent):
        tb = ctk.CTkFrame(parent, fg_color="transparent", height=58)
        tb.grid(row=0, column=0, sticky="ew", padx=18, pady=(14,6))
        tb.pack_propagate(False); tb.grid_columnconfigure(1, weight=1)

        self._title_lbl = ctk.CTkLabel(tb, text="", font=("Segoe UI",20,"bold"), text_color=WHITE)
        self._title_lbl.grid(row=0, column=0, sticky="w")

        nav = ctk.CTkFrame(tb, fg_color=CARD, corner_radius=10, height=36)
        nav.grid(row=0, column=2, sticky="e")
        # FIXED: use text= and command= as keyword arguments
        ctk.CTkButton(nav, text="◀", command=lambda:self._chg(-1),
                      fg_color="transparent", hover_color=CARD2,
                      font=("Segoe UI",12), width=28, height=28).pack(side="left",padx=4,pady=4)
        self._mlbl = ctk.CTkLabel(nav, text="",font=("Segoe UI",12,"bold"),text_color=TEXT,width=108)
        self._mlbl.pack(side="left")
        ctk.CTkButton(nav, text="▶", command=lambda:self._chg(1),
                      fg_color="transparent", hover_color=CARD2,
                      font=("Segoe UI",12), width=28, height=28).pack(side="left",padx=4,pady=4)
        self._upd_m()

        self._clk = ctk.CTkLabel(tb, text="",font=("Segoe UI",10),text_color=TEXT3)
        self._clk.grid(row=0, column=3, padx=12)
        self._tick()

    def _tick(self):
        self._clk.configure(text=datetime.now().strftime("%d/%m/%Y  %H:%M:%S"))
        self.after(1000, self._tick)
    def _chg(self,d):
        m=self.mes+d
        if m>12: m=1; self.ano+=1
        if m<1:  m=12; self.ano-=1
        self.mes=m; self._upd_m(); self._nav(self._page)
    def _upd_m(self):
        self._mlbl.configure(text=f"  {MESES[self.mes-1]} {self.ano}  ")
    def _nav(self, page):
        self._page=page
        titles={"dashboard":"Dashboard","transacoes":"Transações","graficos":"Gráficos",
                "metas":"Metas","dividas":"Dívidas","orcamento":"Orçamento",
                "contas":"Contas","relatorio":"Relatório","config":"Configurações"}
        self._title_lbl.configure(text=titles.get(page,""))
        self._highlight_nav(page)
        for w in self.body.winfo_children(): w.destroy()
        getattr(self,f"_p_{page}")()

    def _p_dashboard(self):
        p=self.body
        p.grid_columnconfigure((0,1,2,3),weight=1)
        p.grid_rowconfigure((1,2),weight=1)

        rec,des,sal=self.db.resumo(self.mes,self.ano)
        eco=sal/rec*100 if rec else 0

        for i,(ico,ttl,val,sub,clr) in enumerate([
            ("💰","Receitas",  M(rec,self.moeda),"Entradas do mês",GREEN),
            ("💸","Despesas",  M(des,self.moeda),"Saídas do mês",  RED),
            ("📊","Saldo",     M(sal,self.moeda),"Resultado",      ACCENT if sal>=0 else RED),
            ("📈","Economia",  f"{eco:.1f}%",    "Taxa de poupança",YELLOW),
        ]):
            MiniCard(p,ico,ttl,val,sub,clr).grid(row=0,column=i,padx=5,pady=(0,5),sticky="nsew",ipady=2)

        if HAS_MPL:
            ef=Card(p,ACCENT); ef.grid(row=1,column=0,columnspan=2,padx=5,pady=5,sticky="nsew")
            lbl(ef,"📈  Evolução Mensal",13,True,WHITE).pack(anchor="w",padx=16,pady=(12,6))
            Div(ef).pack(fill="x",padx=16,pady=(0,4))
            self._evo_chart(ef)

            df=Card(p,A2); df.grid(row=1,column=2,columnspan=2,padx=5,pady=5,sticky="nsew")
            lbl(df,"🍩  Despesas por Categoria",13,True,WHITE).pack(anchor="w",padx=16,pady=(12,6))
            Div(df).pack(fill="x",padx=16,pady=(0,4))
            self._donut_chart(df)

        tf=Card(p); tf.grid(row=2,column=0,columnspan=2,padx=5,pady=5,sticky="nsew")
        lbl(tf,"🕐  Últimas Transações",13,True,WHITE).pack(anchor="w",padx=16,pady=(12,6))
        Div(tf).pack(fill="x",padx=16,pady=(0,6))
        txs=self.db.get_tx(mes=self.mes,ano=self.ano,limit=5)
        if not txs: lbl(tf,"Nenhuma transação neste mês").pack(pady=16)
        for t in txs:
            c=GREEN if t["tipo"]=="receita" else RED
            s="+" if t["tipo"]=="receita" else "-"
            r=ctk.CTkFrame(tf,fg_color="transparent"); r.pack(fill="x",padx=16,pady=4)
            ctk.CTkFrame(r,fg_color=c,width=3,height=28,corner_radius=2).pack(side="left",padx=(0,10))
            ctk.CTkLabel(r,text=t["desc"],font=("Segoe UI",11),text_color=TEXT,anchor="w").pack(side="left")
            ctk.CTkLabel(r,text=t["data"],font=("Segoe UI",9),text_color=TEXT3).pack(side="left",padx=6)
            ctk.CTkLabel(r,text=f"{s}{M(t['valor'],self.moeda)}",
                         font=("Segoe UI",11,"bold"),text_color=c).pack(side="right")

        af=Card(p); af.grid(row=2,column=2,columnspan=2,padx=5,pady=5,sticky="nsew")
        lbl(af,"🏦  Saldo das Contas",13,True,WHITE).pack(anchor="w",padx=16,pady=(12,6))
        Div(af).pack(fill="x",padx=16,pady=(0,6))
        for c in self.db.saldo_contas():
            sl=(c["saldo_ini"] or 0)+(c["mov"] or 0)
            r=ctk.CTkFrame(af,fg_color="transparent"); r.pack(fill="x",padx=16,pady=5)
            ctk.CTkFrame(r,fg_color=c["cor"] or ACCENT,width=8,height=8,corner_radius=4).pack(side="left",padx=(0,8))
            ctk.CTkLabel(r,text=c["nome"],font=("Segoe UI",11),text_color=TEXT).pack(side="left")
            ctk.CTkLabel(r,text=M(sl,self.moeda),font=("Segoe UI",11,"bold"),
                         text_color=GREEN if sl>=0 else RED).pack(side="right")

    def _evo_chart(self, parent):
        rec,des=self.db.evolucao(self.ano)
        fig=Figure(figsize=(5.4,2.5),facecolor=CARD); ax=fig.add_subplot(111,facecolor=CARD)
        x=list(range(12)); w=0.34
        ax.bar([i-w/2 for i in x],rec,w,color=GREEN,alpha=0.85,label="Receitas",zorder=3)
        ax.bar([i+w/2 for i in x],des,w,color=RED,  alpha=0.85,label="Despesas",zorder=3)
        ax.set_xticks(x); ax.set_xticklabels(MESES,fontsize=7.5,color=TEXT2)
        ax.tick_params(colors=TEXT2,labelsize=7.5)
        ax.grid(axis="y",color=BORDER,lw=0.5,zorder=0)
        for s in ax.spines.values(): s.set_color(BORDER)
        ax.legend(fontsize=7.5,facecolor=CARD2,edgecolor=BORDER,labelcolor=TEXT2)
        fig.tight_layout(pad=0.9)
        cv=FigureCanvasTkAgg(fig,parent); cv.draw()
        cv.get_tk_widget().configure(bg=CARD,highlightthickness=0)
        cv.get_tk_widget().pack(fill="both",expand=True,padx=12,pady=(0,10))

    def _donut_chart(self, parent):
        cats=self.db.por_cat("despesa",self.mes,self.ano)
        if not cats: lbl(parent,"Sem dados").pack(pady=20); return
        lbls=[r["cat"] for r in cats[:7]]; vals=[r["t"] for r in cats[:7]]
        clrs=[ACCENT,A2,GREEN,YELLOW,BLUE,"#FF8C42","#A8DADC"][:len(lbls)]
        fig=Figure(figsize=(4.2,2.5),facecolor=CARD); ax=fig.add_subplot(111,facecolor=CARD)
        ws,_,ats=ax.pie(vals,labels=None,colors=clrs,autopct="%1.0f%%",
            startangle=90,pctdistance=0.76,wedgeprops=dict(width=0.52))
        for a in ats: a.set_color(WHITE); a.set_fontsize(7.5)
        ax.legend(ws,[l[:14] for l in lbls],loc="lower right",
                  fontsize=7,facecolor=CARD2,edgecolor=BORDER,labelcolor=TEXT2)
        fig.tight_layout(pad=0.2)
        cv=FigureCanvasTkAgg(fig,parent); cv.draw()
        cv.get_tk_widget().configure(bg=CARD,highlightthickness=0)
        cv.get_tk_widget().pack(fill="both",expand=True,padx=12,pady=(0,10))

    def _p_transacoes(self):
        p=self.body; p.grid_columnconfigure(0,weight=1); p.grid_rowconfigure(1,weight=1)

        tb=ctk.CTkFrame(p,fg_color="transparent"); tb.grid(row=0,column=0,sticky="ew",pady=(0,10))
        Btn(tb,"+ Receita",lambda:self._modal_tx("receita"),GREEN,w=110).pack(side="left",padx=(0,6))
        Btn(tb,"+ Despesa",lambda:self._modal_tx("despesa"),RED,  w=110).pack(side="left",padx=(0,14))
        self._sv=ctk.StringVar(); self._sv.trace("w",lambda*a:self._rtx())
        ent(tb,self._sv,"🔍  Buscar...",w=220).pack(side="left")
        self._tv=ctk.StringVar(value="todos")
        for v,t in [("todos","Todos"),("receita","Receitas"),("despesa","Despesas")]:
            ctk.CTkRadioButton(tb,text=t,variable=self._tv,value=v,command=self._rtx,
                               fg_color=ACCENT,border_color=BORDER,font=("Segoe UI",11),
                               text_color=TEXT2).pack(side="left",padx=8)
        Btn(tb,"📤 CSV",self._exp_csv,CARD2,w=90).pack(side="right",padx=4)
        Btn(tb,"📥 CSV",self._imp_csv,CARD2,w=90).pack(side="right",padx=4)

        outer=Card(p); outer.grid(row=1,column=0,sticky="nsew")
        outer.grid_rowconfigure(1,weight=1); outer.grid_columnconfigure(0,weight=1)

        hdr=ctk.CTkFrame(outer,fg_color=CARD2,corner_radius=0,height=34)
        hdr.grid(row=0,column=0,sticky="ew")
        cols=[("Data",88),("Descrição",210),("Categoria",160),("Conta",100),("Tipo",84),("Valor",118),("",44)]
        for i,(c,w) in enumerate(cols):
            ctk.CTkLabel(hdr,text=c,font=("Segoe UI",10),text_color=TEXT3,anchor="w",width=w).grid(
                row=0,column=i,padx=8,pady=6,sticky="w")
        hdr.grid_columnconfigure(1,weight=1)

        self._tsf=ctk.CTkScrollableFrame(outer,fg_color="transparent",
                                          scrollbar_button_color=BORDER,
                                          scrollbar_button_hover_color=ACCENT)
        self._tsf.grid(row=1,column=0,sticky="nsew",padx=2,pady=2)
        self._tsf.grid_columnconfigure(1,weight=1)
        self._cols=cols; self._rtx()

    def _rtx(self):
        for w in self._tsf.winfo_children(): w.destroy()
        fi=self._sv.get() if hasattr(self,"_sv") else ""
        ti=self._tv.get() if hasattr(self,"_tv") else "todos"
        txs=self.db.get_tx(filtro=fi,mes=self.mes,ano=self.ano,tipo=None if ti=="todos" else ti)
        if not txs: lbl(self._tsf,"Nenhuma transação encontrada").pack(pady=24); return
        for i,t in enumerate(txs):
            bg=CARD if i%2==0 else CARD2
            c=GREEN if t["tipo"]=="receita" else RED
            s="+" if t["tipo"]=="receita" else "-"
            row=ctk.CTkFrame(self._tsf,fg_color=bg,corner_radius=6); row.pack(fill="x",pady=1)
            vals=[t["data"],t["desc"],t["cat"] or "-",t["conta"] or "-",
                  t["tipo"].capitalize(),f"{s}{M(t['valor'],self.moeda)}"]
            for j,(v,(_,w)) in enumerate(zip(vals,self._cols)):
                fc=c if j==5 else (WHITE if j==1 else TEXT2)
                fn=("Segoe UI",11,"bold") if j==5 else ("Segoe UI",11)
                ctk.CTkLabel(row,text=v,font=fn,text_color=fc,anchor="w",width=w).grid(
                    row=0,column=j,padx=8,pady=5,sticky="w")
            ctk.CTkButton(row, text="✕", width=26, height=22, fg_color="transparent",
                          hover_color=RED, text_color=TEXT3, font=("Segoe UI",10),
                          command=lambda tid=t["id"]:self._dtx(tid)).grid(row=0,column=6,padx=4)
            row.grid_columnconfigure(1,weight=1)

    def _dtx(self,tid):
        if messagebox.askyesno("Confirmar","Excluir esta transação?"):
            self.db.del_tx(tid); self._rtx()

    def _modal_tx(self, tipo):
        clr=GREEN if tipo=="receita" else RED
        ttl=f"💰  Nova Receita" if tipo=="receita" else "💸  Nova Despesa"
        m=Modal(self,ttl,460,500,clr)
        desc =m.add("Descrição *")
        valor=m.add("Valor (R$) *")
        data =m.add("Data *",default=datetime.now().strftime("%Y-%m-%d"))
        cats =CATS_R if tipo=="receita" else CATS_D
        cat  =m.add("Categoria",combo=True,values=cats,default=cats[0])
        cnts =[c["nome"] for c in self.db.q("SELECT nome FROM contas WHERE ativo=1")]
        conta=m.add("Conta",combo=True,values=cnts,default=cnts[0] if cnts else "Principal")
        obs  =m.add("Observação (opcional)")
        rv   =ctk.BooleanVar()
        ctk.CTkCheckBox(m.body,text="Recorrente (mensal)",variable=rv,fg_color=ACCENT,
                        border_color=BORDER,font=("Segoe UI",11),text_color=TEXT2).grid(
            row=m._r,column=0,sticky="w",pady=8)
        def ok():
            d_=desc.get().strip(); v_=valor.get().strip().replace(",",".")
            dt_=data.get().strip()
            if not d_ or not v_ or not dt_:
                messagebox.showwarning("Atenção","Preencha os campos obrigatórios.",parent=m); return
            try: vf=float(v_); datetime.strptime(dt_,"%Y-%m-%d")
            except: messagebox.showerror("Erro","Valor ou data inválidos.",parent=m); return
            self.db.add_tx(tipo,d_,vf,cat.get(),dt_,conta.get(),obs.get(),int(rv.get()))
            m.destroy()
            if self._page in("transacoes","dashboard"): self._nav(self._page)
        m.footer(m.destroy,ok,"✓ Salvar",clr)

    def _p_graficos(self):
        if not HAS_MPL:
            lbl(self.body,"Instale matplotlib: pip install matplotlib").pack(pady=40); return
        p=self.body; p.grid_columnconfigure((0,1),weight=1); p.grid_rowconfigure((0,1),weight=1)
        rec,des=self.db.evolucao(self.ano)

        def make(row,col,title):
            f=Card(p); f.grid(row=row,column=col,padx=5,pady=5,sticky="nsew")
            lbl(f,title,12,True,WHITE).pack(anchor="w",padx=16,pady=(12,6))
            Div(f).pack(fill="x",padx=16,pady=(0,4))
            return f

        f1=make(0,0,"📊  Receitas vs Despesas")
        fig1=Figure(figsize=(5,2.6),facecolor=CARD); ax1=fig1.add_subplot(111,facecolor=CARD)
        x=list(range(12))
        ax1.fill_between(x,rec,alpha=0.2,color=GREEN); ax1.fill_between(x,des,alpha=0.2,color=RED)
        ax1.plot(x,rec,GREEN,lw=2,label="Receitas",marker="o",ms=3,zorder=3)
        ax1.plot(x,des,RED,  lw=2,label="Despesas",marker="o",ms=3,zorder=3)
        ax1.set_xticks(x); ax1.set_xticklabels(MESES,fontsize=7.5,color=TEXT2)
        ax1.tick_params(colors=TEXT2,labelsize=7.5); ax1.grid(color=BORDER,lw=0.5,zorder=0)
        for s in ax1.spines.values(): s.set_color(BORDER)
        ax1.legend(fontsize=7.5,facecolor=CARD2,edgecolor=BORDER,labelcolor=TEXT2)
        fig1.tight_layout(pad=0.9)
        cv1=FigureCanvasTkAgg(fig1,f1); cv1.draw()
        cv1.get_tk_widget().configure(bg=CARD,highlightthickness=0)
        cv1.get_tk_widget().pack(fill="both",expand=True,padx=12,pady=(0,10))

        f2=make(0,1,f"🍩  Categorias — {MESES[self.mes-1]}")
        cats=self.db.por_cat("despesa",self.mes,self.ano)
        if cats:
            clrs=[ACCENT,A2,GREEN,YELLOW,BLUE,"#FF8C42","#A8DADC","#06D6A0"]
            fig2=Figure(figsize=(4,2.6),facecolor=CARD); ax2=fig2.add_subplot(111,facecolor=CARD)
            ws,_,ats=ax2.pie([r["t"] for r in cats[:8]],labels=None,
                colors=clrs[:len(cats[:8])],autopct="%1.0f%%",startangle=90,
                pctdistance=0.76,wedgeprops=dict(width=0.5))
            for a in ats: a.set_color(WHITE); a.set_fontsize(7.5)
            ax2.legend(ws,[r["cat"][:13] for r in cats[:8]],loc="lower right",
                       fontsize=7,facecolor=CARD2,edgecolor=BORDER,labelcolor=TEXT2)
            fig2.tight_layout(pad=0.2)
            cv2=FigureCanvasTkAgg(fig2,f2); cv2.draw()
            cv2.get_tk_widget().configure(bg=CARD,highlightthickness=0)
            cv2.get_tk_widget().pack(fill="both",expand=True,padx=12,pady=(0,10))
        else: lbl(f2,"Sem dados neste mês").pack(pady=24)

        f3=make(1,0,"💹  Saldo Acumulado no Ano")
        ac=[]; s=0
        for r,d in zip(rec,des): s+=r-d; ac.append(s)
        fig3=Figure(figsize=(5,2.4),facecolor=CARD); ax3=fig3.add_subplot(111,facecolor=CARD)
        ax3.bar(x,ac,color=[GREEN if v>=0 else RED for v in ac],alpha=0.85,zorder=3)
        ax3.axhline(0,color=BORDER,lw=1)
        ax3.set_xticks(x); ax3.set_xticklabels(MESES,fontsize=7.5,color=TEXT2)
        ax3.tick_params(colors=TEXT2,labelsize=7.5)
        ax3.grid(axis="y",color=BORDER,lw=0.5,zorder=0)
        for s2 in ax3.spines.values(): s2.set_color(BORDER)
        fig3.tight_layout(pad=0.9)
        cv3=FigureCanvasTkAgg(fig3,f3); cv3.draw()
        cv3.get_tk_widget().configure(bg=CARD,highlightthickness=0)
        cv3.get_tk_widget().pack(fill="both",expand=True,padx=12,pady=(0,10))

        f4=make(1,1,f"💰  Receitas — {MESES[self.mes-1]}")
        cats_r=self.db.por_cat("receita",self.mes,self.ano)
        if cats_r:
            fig4=Figure(figsize=(4,2.4),facecolor=CARD); ax4=fig4.add_subplot(111,facecolor=CARD)
            lbls=[r["cat"][:16] for r in cats_r[:6]]; vals=[r["t"] for r in cats_r[:6]]
            bars=ax4.barh(lbls,vals,color=GREEN,alpha=0.82)
            mx=max(vals) if vals else 1
            for b,v in zip(bars,vals):
                ax4.text(b.get_width()+mx*0.01,b.get_y()+b.get_height()/2,
                         M(v,self.moeda),va="center",fontsize=7.5,color=TEXT2)
            ax4.invert_yaxis(); ax4.tick_params(colors=TEXT2,labelsize=7.5)
            for s2 in ax4.spines.values(): s2.set_color(BORDER)
            fig4.tight_layout(pad=0.9)
            cv4=FigureCanvasTkAgg(fig4,f4); cv4.draw()
            cv4.get_tk_widget().configure(bg=CARD,highlightthickness=0)
            cv4.get_tk_widget().pack(fill="both",expand=True,padx=12,pady=(0,10))
        else: lbl(f4,"Sem dados neste mês").pack(pady=24)

    def _p_metas(self):
        p=self.body; p.grid_columnconfigure(0,weight=1); p.grid_rowconfigure(1,weight=1)
        tb=ctk.CTkFrame(p,fg_color="transparent"); tb.grid(row=0,column=0,sticky="ew",pady=(0,10))
        Btn(tb,"+ Nova Meta",self._m_meta,w=140).pack(side="left")

        sf=ctk.CTkScrollableFrame(p,fg_color="transparent",
                                   scrollbar_button_color=BORDER,
                                   scrollbar_button_hover_color=ACCENT)
        sf.grid(row=1,column=0,sticky="nsew"); sf.grid_columnconfigure((0,1,2),weight=1)
        metas=self.db.get_metas()
        if not metas: lbl(sf,"Nenhuma meta. Crie sua primeira! 🎯").pack(pady=40); return

        for i,m in enumerate(metas):
            pct=min(m["atual"]/m["alvo"],1) if m["alvo"] else 0
            cor=m["cor"] or ACCENT
            c=Card(sf); c.grid(row=i//3,column=i%3,padx=7,pady=7,sticky="nsew")
            ctk.CTkFrame(c,fg_color=cor,height=3,corner_radius=0).pack(fill="x")
            ctk.CTkLabel(c,text=m["nome"],font=("Segoe UI",13,"bold"),text_color=WHITE).pack(anchor="w",padx=14,pady=(10,2))
            if m["prazo"]: lbl(c,f"📅 {m['prazo']}",10).pack(anchor="w",padx=14)
            PBar(c,pct,cor,h=8).pack(fill="x",padx=14,pady=6)
            vf=ctk.CTkFrame(c,fg_color="transparent"); vf.pack(fill="x",padx=14)
            lbl(vf,M(m["atual"],self.moeda),11,color=TEXT).pack(side="left")
            lbl(vf,f"/ {M(m['alvo'],self.moeda)}",10,color=TEXT3).pack(side="left",padx=4)
            ctk.CTkLabel(vf,text=f"{pct*100:.0f}%",font=("Segoe UI",12,"bold"),text_color=cor).pack(side="right")
            bf=ctk.CTkFrame(c,fg_color="transparent"); bf.pack(fill="x",padx=14,pady=(8,12))
            Btn(bf,"💰 Depositar",lambda mid=m["id"]:self._m_dep(mid),ACCENT,w=108,h=30).pack(side="left")
            Btn(bf,"✕",lambda mid=m["id"]:(self.db.del_meta(mid),self._p_metas()),CARD2,w=34,h=30).pack(side="right")

    def _m_meta(self):
        m=Modal(self,"🎯  Nova Meta",420,400)
        nome=m.add("Nome da Meta *"); alvo=m.add("Valor Alvo (R$) *"); prazo=m.add("Prazo (AAAA-MM-DD)")
        lbl(m.body,"Cor",10,color=TEXT3).grid(row=m._r,column=0,sticky="w",pady=(6,3)); m._r+=1
        cv=ctk.StringVar(value=ACCENT)
        cf=ctk.CTkFrame(m.body,fg_color="transparent"); cf.grid(row=m._r,column=0,sticky="w"); m._r+=1
        for c in [ACCENT,GREEN,YELLOW,RED,BLUE,A2]:
            ctk.CTkButton(cf, text="", fg_color=c, width=26, height=26, corner_radius=13,
                          command=lambda c_=c:cv.set(c_)).pack(side="left",padx=3)
        def ok():
            if not nome.get().strip() or not alvo.get().strip():
                messagebox.showwarning("Atenção","Preencha nome e valor.",parent=m); return
            try: af=float(alvo.get().replace(",","."))
            except: messagebox.showerror("Erro","Valor inválido.",parent=m); return
            self.db.add_meta(nome.get().strip(),af,prazo.get(),cv.get()); m.destroy(); self._p_metas()
        m.footer(m.destroy,ok)

    def _m_dep(self,mid):
        m=Modal(self,"💰  Depositar na Meta",320,200); m.geometry("320x210")
        val=m.add("Valor (R$)")
        def ok():
            try: self.db.dep_meta(mid,float(val.get().replace(",","."))); m.destroy(); self._p_metas()
            except: messagebox.showerror("Erro","Valor inválido.",parent=m)
        m.footer(m.destroy,ok,"✓ Depositar",GREEN)

    def _p_dividas(self):
        p=self.body; p.grid_columnconfigure(0,weight=1); p.grid_rowconfigure(1,weight=1)
        tb=ctk.CTkFrame(p,fg_color="transparent"); tb.grid(row=0,column=0,sticky="ew",pady=(0,8))
        Btn(tb,"+ Nova Dívida",self._m_div,RED,w=140).pack(side="left")
        divs=self.db.get_div()
        if divs:
            total=sum(d["total"]-d["pago"] for d in divs)
            ban=ctk.CTkFrame(p,fg_color=_mix(RED,BG,0.15),corner_radius=12,height=52)
            ban.grid(row=0,column=0,sticky="ew",pady=(0,8)); ban.grid_propagate(False)
            ctk.CTkLabel(ban,text=f"  💳  Dívida total: {M(total,self.moeda)}",
                         font=("Segoe UI",14,"bold"),text_color=RED).pack(side="left",padx=16)
        sf=ctk.CTkScrollableFrame(p,fg_color="transparent",
                                   scrollbar_button_color=BORDER,
                                   scrollbar_button_hover_color=ACCENT)
        sf.grid(row=1,column=0,sticky="nsew"); sf.grid_columnconfigure(0,weight=1)
        if not divs: lbl(sf,"Nenhuma dívida. Ótimo! 🎉").pack(pady=40); return
        for d in divs:
            rest=d["total"]-d["pago"]; pct=d["pago"]/d["total"] if d["total"] else 0
            c=Card(sf); c.pack(fill="x",pady=5)
            ctk.CTkFrame(c,fg_color=RED,height=3,corner_radius=0).pack(fill="x")
            h=ctk.CTkFrame(c,fg_color="transparent"); h.pack(fill="x",padx=16,pady=(10,4))
            ctk.CTkLabel(h,text=d["nome"],font=("Segoe UI",13,"bold"),text_color=WHITE).pack(side="left")
            if d["credor"]: lbl(h,f" → {d['credor']}",10).pack(side="left")
            ctk.CTkLabel(h,text=M(rest,self.moeda),font=("Segoe UI",13,"bold"),text_color=RED).pack(side="right")
            inf=ctk.CTkFrame(c,fg_color="transparent"); inf.pack(fill="x",padx=16)
            for t in [f"Total: {M(d['total'],self.moeda)}",f"Pago: {M(d['pago'],self.moeda)}",
                      f"Juros: {d['juros']}%",f"Parcelas: {d['parc_atual']}/{d['parcelas']}"]:
                lbl(inf,t,10).pack(side="left",padx=(0,14))
            PBar(c,pct,GREEN,h=8).pack(fill="x",padx=16,pady=6)
            ctk.CTkLabel(c,text=f"{pct*100:.0f}% pago",font=("Segoe UI",10),text_color=GREEN).pack(anchor="w",padx=16)
            bf=ctk.CTkFrame(c,fg_color="transparent"); bf.pack(fill="x",padx=16,pady=(6,12))
            pv=d["total"]/max(d["parcelas"],1)
            Btn(bf,"💳 Pagar Parcela",lambda did=d["id"],v=pv:self._pagar(did,v),ACCENT,w=140,h=30).pack(side="left")
            Btn(bf,"✕ Excluir",lambda did=d["id"]:(self.db.del_div(did),self._p_dividas()),CARD2,w=100,h=30).pack(side="right")

    def _m_div(self):
        m=Modal(self,"💳  Nova Dívida",440,480,RED)
        nome=m.add("Nome *"); total=m.add("Valor Total *")
        taxa=m.add("Taxa de Juros (% a.m.)",default="0"); parc=m.add("Parcelas",default="1")
        venc=m.add("Vencimento (AAAA-MM-DD)"); cred=m.add("Credor")
        def ok():
            if not nome.get().strip() or not total.get().strip():
                messagebox.showwarning("Atenção","Preencha nome e valor.",parent=m); return
            try: t_=float(total.get().replace(",",".")); tx_=float(taxa.get() or 0); p_=int(parc.get() or 1)
            except: messagebox.showerror("Erro","Valores inválidos.",parent=m); return
            self.db.add_div(nome.get().strip(),t_,tx_,p_,venc.get(),cred.get())
            m.destroy(); self._p_dividas()
        m.footer(m.destroy,ok,"✓ Cadastrar",RED)

    def _pagar(self,did,pv):
        m=Modal(self,"💳  Pagar Parcela",320,200); m.geometry("320x210")
        val=m.add("Valor",default=f"{pv:.2f}")
        def ok():
            try: self.db.pagar(did,float(val.get().replace(",","."))); m.destroy(); self._p_dividas()
            except: messagebox.showerror("Erro","Valor inválido.",parent=m)
        m.footer(m.destroy,ok,"✓ Pagar",GREEN)

    def _p_orcamento(self):
        p=self.body; p.grid_columnconfigure(0,weight=1); p.grid_rowconfigure(1,weight=1)
        tb=ctk.CTkFrame(p,fg_color="transparent"); tb.grid(row=0,column=0,sticky="ew",pady=(0,10))
        Btn(tb,"+ Definir Limite",self._m_orc,w=150).pack(side="left")
        lbl(tb,f"  {MESES[self.mes-1]} {self.ano}",11).pack(side="left",padx=8)
        sf=ctk.CTkScrollableFrame(p,fg_color="transparent",
                                   scrollbar_button_color=BORDER,
                                   scrollbar_button_hover_color=ACCENT)
        sf.grid(row=1,column=0,sticky="nsew"); sf.grid_columnconfigure((0,1),weight=1)
        orcs=self.db.get_orc(self.mes,self.ano)
        gastos={r["cat"]:r["t"] for r in self.db.por_cat("despesa",self.mes,self.ano)}
        if not orcs: lbl(sf,"Nenhum limite definido para este mês.").pack(pady=30); return
        for i,o in enumerate(orcs):
            g=gastos.get(o["cat"],0); pct=g/o["limite"] if o["limite"] else 0
            cor=GREEN if pct<0.7 else (YELLOW if pct<1 else RED)
            c=Card(sf); c.grid(row=i//2,column=i%2,padx=7,pady=7,sticky="nsew")
            ctk.CTkFrame(c,fg_color=cor,height=3,corner_radius=0).pack(fill="x")
            h=ctk.CTkFrame(c,fg_color="transparent"); h.pack(fill="x",padx=14,pady=(10,4))
            ctk.CTkLabel(h,text=o["cat"],font=("Segoe UI",12,"bold"),text_color=WHITE).pack(side="left")
            ctk.CTkLabel(h,text=f"{pct*100:.0f}%",font=("Segoe UI",12,"bold"),text_color=cor).pack(side="right")
            PBar(c,pct,cor,h=10).pack(fill="x",padx=14,pady=6)
            vf=ctk.CTkFrame(c,fg_color="transparent"); vf.pack(fill="x",padx=14,pady=(0,10))
            lbl(vf,f"Gasto: {M(g,self.moeda)}",10,color=TEXT2).pack(side="left")
            lbl(vf,f"Limite: {M(o['limite'],self.moeda)}",10,color=TEXT3).pack(side="right")
            if pct>=1:
                ctk.CTkLabel(c,text=f"⚠️ Excedido em {M(g-o['limite'],self.moeda)}",
                             font=("Segoe UI",10),text_color=RED).pack(anchor="w",padx=14,pady=(0,8))

    def _m_orc(self):
        m=Modal(self,"📋  Definir Limite",370,260); m.geometry("370x260")
        cat=m.add("Categoria",combo=True,values=CATS_D,default=CATS_D[0])
        lim=m.add("Limite (R$)")
        def ok():
            if not lim.get().strip(): messagebox.showwarning("Atenção","Informe o limite.",parent=m); return
            try: lf=float(lim.get().replace(",",".")); self.db.set_orc(cat.get(),lf,self.mes,self.ano); m.destroy(); self._p_orcamento()
            except: messagebox.showerror("Erro","Valor inválido.",parent=m)
        m.footer(m.destroy,ok)

    def _p_contas(self):
        p=self.body; p.grid_columnconfigure(0,weight=1); p.grid_rowconfigure(1,weight=1)
        contas=self.db.saldo_contas()
        total=sum((c["saldo_ini"] or 0)+(c["mov"] or 0) for c in contas)
        ban=ctk.CTkFrame(p,fg_color=ACCENT,corner_radius=14,height=72)
        ban.grid(row=0,column=0,sticky="ew",pady=(0,10)); ban.grid_propagate(False)
        ctk.CTkLabel(ban,text="💰  Patrimônio Total",font=("Segoe UI",11),text_color=WHITE).place(x=20,y=10)
        ctk.CTkLabel(ban,text=M(total,self.moeda),font=("Segoe UI",22,"bold"),text_color=WHITE).place(x=20,y=30)
        sf=ctk.CTkScrollableFrame(p,fg_color="transparent",
                                   scrollbar_button_color=BORDER,
                                   scrollbar_button_hover_color=ACCENT)
        sf.grid(row=1,column=0,sticky="nsew"); sf.grid_columnconfigure((0,1,2),weight=1)
        ICO={"Corrente":"🏦","Poupança":"💰","Investimento":"📈","Espécie":"💵","Cartão":"💳"}
        for i,c in enumerate(contas):
            sl=(c["saldo_ini"] or 0)+(c["mov"] or 0); cor=c["cor"] or ACCENT
            cd=Card(sf); cd.grid(row=i//3,column=i%3,padx=7,pady=7,sticky="nsew")
            ctk.CTkFrame(cd,fg_color=cor,height=3,corner_radius=0).pack(fill="x")
            ctk.CTkLabel(cd,text=f"{ICO.get(c['tipo'],'🏦')}  {c['nome']}",
                         font=("Segoe UI",13,"bold"),text_color=WHITE).pack(anchor="w",padx=14,pady=(12,2))
            lbl(cd,c["tipo"],10).pack(anchor="w",padx=14)
            ctk.CTkLabel(cd,text=M(sl,self.moeda),font=("Segoe UI",18,"bold"),
                         text_color=GREEN if sl>=0 else RED).pack(anchor="w",padx=14,pady=(6,2))
            lbl(cd,f"Inicial: {M(c['saldo_ini'] or 0,self.moeda)}",9,color=TEXT3).pack(anchor="w",padx=14,pady=(0,12))
        Btn(sf,"+ Nova Conta",self._m_conta,w=140).grid(row=len(contas)//3+1,column=0,padx=7,pady=10,sticky="w")

    def _m_conta(self):
        m=Modal(self,"🏦  Nova Conta",370,360); m.geometry("370x360")
        nome=m.add("Nome *")
        tipo=m.add("Tipo",combo=True,values=["Corrente","Poupança","Investimento","Espécie","Cartão"])
        saldo=m.add("Saldo Inicial",default="0")
        lbl(m.body,"Cor",10,color=TEXT3).grid(row=m._r,column=0,sticky="w",pady=(6,3)); m._r+=1
        cv=ctk.StringVar(value=ACCENT)
        cf=ctk.CTkFrame(m.body,fg_color="transparent"); cf.grid(row=m._r,column=0,sticky="w"); m._r+=1
        for c in [ACCENT,GREEN,YELLOW,RED,BLUE,A2]:
            ctk.CTkButton(cf, text="", fg_color=c, width=26, height=26, corner_radius=13,
                          command=lambda c_=c:cv.set(c_)).pack(side="left",padx=3)
        def ok():
            n=nome.get().strip()
            if not n: messagebox.showwarning("Atenção","Informe o nome.",parent=m); return
            try: sf_=float(saldo.get().replace(",","."))
            except: sf_=0
            self.db.run("INSERT OR IGNORE INTO contas(nome,tipo,saldo_ini,cor) VALUES(?,?,?,?)",(n,tipo.get(),sf_,cv.get()))
            m.destroy(); self._p_contas()
        m.footer(m.destroy,ok)

    def _p_relatorio(self):
        p=self.body; p.grid_columnconfigure(0,weight=1); p.grid_rowconfigure(1,weight=1)
        tb=ctk.CTkFrame(p,fg_color="transparent"); tb.grid(row=0,column=0,sticky="ew",pady=(0,10))
        Btn(tb,"📤 Exportar CSV",self._exp_csv,w=150).pack(side="left",padx=(0,8))
        Btn(tb,"📋 Salvar TXT",self._exp_txt,CARD2,w=130).pack(side="left")
        outer=Card(p); outer.grid(row=1,column=0,sticky="nsew")
        outer.grid_rowconfigure(0,weight=1); outer.grid_columnconfigure(0,weight=1)
        txt=tk.Text(outer,bg=CARD,fg=TEXT,font=("Consolas",11),relief="flat",
                    bd=0,padx=20,pady=16,insertbackground=TEXT,wrap="none")
        vsb=ctk.CTkScrollbar(outer,command=txt.yview)
        txt.configure(yscrollcommand=vsb.set)
        txt.grid(row=0,column=0,sticky="nsew"); vsb.grid(row=0,column=1,sticky="ns")
        rec,des,sal=self.db.resumo(self.mes,self.ano)
        cats_d=self.db.por_cat("despesa",self.mes,self.ano)
        cats_r=self.db.por_cat("receita",self.mes,self.ano)
        metas=self.db.get_metas()
        L=["═"*62,f"  FINANCEFLOW  —  RELATÓRIO  {MESES[self.mes-1]} {self.ano}",
           f"  Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", "═"*62,"",
           "  RESUMO","  "+"─"*38,
           f"  💰 Receitas :  {M(rec,self.moeda):>20}",
           f"  💸 Despesas :  {M(des,self.moeda):>20}",
           f"  📊 Saldo    :  {M(sal,self.moeda):>20}",
           f"  📈 Economia :  {(sal/rec*100 if rec else 0):>19.1f}%","",
           "  DESPESAS","  "+"─"*38]
        for r in cats_d:
            pct=r["t"]/des*100 if des else 0
            L.append(f"  {r['cat']:<22} {M(r['t'],self.moeda):>12}  {'█'*int(pct/5)}{'░'*(20-int(pct/5))} {pct:.1f}%")
        L+=["","  RECEITAS","  "+"─"*38]
        for r in cats_r:
            pct=r["t"]/rec*100 if rec else 0
            L.append(f"  {r['cat']:<22} {M(r['t'],self.moeda):>12}  {pct:.1f}%")
        L+=["","  METAS","  "+"─"*38]
        for mt in metas:
            pct=mt["atual"]/mt["alvo"]*100 if mt["alvo"] else 0
            L.append(f"  {mt['nome']:<22}  {pct:5.0f}%  {'█'*int(pct/5)}{'░'*(20-int(pct/5))}")
        L+=["","═"*62]
        self._reltxt="\n".join(L)
        txt.insert("1.0",self._reltxt)
        txt.tag_configure("h",foreground=ACCENT); txt.tag_configure("g",foreground=GREEN)
        txt.tag_configure("r",foreground=RED);    txt.tag_configure("y",foreground=YELLOW)
        for i,line in enumerate(L):
            n=str(i+1)
            if "═" in line: txt.tag_add("h",f"{n}.0",f"{n}.end")
            if "Receita" in line: txt.tag_add("g",f"{n}.0",f"{n}.end")
            if "Despesa" in line: txt.tag_add("r",f"{n}.0",f"{n}.end")
            if "Saldo" in line:   txt.tag_add("y",f"{n}.0",f"{n}.end")
        txt.configure(state="disabled")

    def _exp_csv(self):
        path=filedialog.asksaveasfilename(defaultextension=".csv",filetypes=[("CSV","*.csv")],
                                          initialfile=f"financeflow_{self.mes:02d}_{self.ano}.csv")
        if not path: return
        txs=self.db.get_tx(mes=self.mes,ano=self.ano)
        with open(path,"w",newline="",encoding="utf-8-sig") as f:
            w=csv.writer(f,delimiter=";")
            w.writerow(["ID","Tipo","Descrição","Valor","Categoria","Data","Conta"])
            for t in txs: w.writerow([t["id"],t["tipo"],t["desc"],t["valor"],t["cat"],t["data"],t["conta"]])
        messagebox.showinfo("Sucesso",f"Exportado:\n{path}")

    def _exp_txt(self):
        path=filedialog.asksaveasfilename(defaultextension=".txt",filetypes=[("Texto","*.txt")],
                                          initialfile=f"relatorio_{self.mes:02d}_{self.ano}.txt")
        if not path: return
        if not hasattr(self,"_reltxt"): self._p_relatorio()
        try:
            with open(path,"w",encoding="utf-8") as f: f.write(self._reltxt)
            messagebox.showinfo("Sucesso",f"Salvo:\n{path}")
        except Exception as e: messagebox.showerror("Erro",str(e))

    def _imp_csv(self):
        path=filedialog.askopenfilename(filetypes=[("CSV","*.csv")])
        if not path: return
        n=0
        try:
            with open(path,encoding="utf-8-sig") as f:
                for r in csv.DictReader(f,delimiter=";"):
                    self.db.add_tx(r.get("Tipo","despesa"),r.get("Descrição",""),
                        float(r.get("Valor",0)),r.get("Categoria",""),
                        r.get("Data",datetime.now().strftime("%Y-%m-%d")),
                        r.get("Conta","Principal")); n+=1
            messagebox.showinfo("Importado",f"{n} transações importadas!")
            self._rtx()
        except Exception as e: messagebox.showerror("Erro",f"Falha: {e}")

    def _p_config(self):
        p=self.body; p.grid_columnconfigure(0,weight=1)

        c1=Card(p,ACCENT); c1.grid(row=0,column=0,sticky="ew",pady=(0,10))
        ctk.CTkLabel(c1,text="⚙️  Preferências",font=("Segoe UI",14,"bold"),text_color=WHITE).pack(anchor="w",padx=18,pady=(14,6))
        Div(c1).pack(fill="x",padx=18)
        frm=ctk.CTkFrame(c1,fg_color="transparent"); frm.pack(fill="x",padx=18,pady=10)
        frm.grid_columnconfigure(1,weight=1)
        nv=ctk.StringVar(value=self.db.cfg("nome"))
        mv=ctk.StringVar(value=self.db.cfg("moeda"))
        for i,(t,v) in enumerate([("👤  Seu nome",nv),("💱  Símbolo moeda",mv)]):
            ctk.CTkLabel(frm,text=t,font=("Segoe UI",11),text_color=TEXT2).grid(row=i,column=0,pady=8,sticky="w",padx=(0,20))
            ent(frm,v,w=180).grid(row=i,column=1,sticky="w",pady=8)
        def save():
            self.db.cfg("nome",nv.get()); self.db.cfg("moeda",mv.get())
            self.moeda=mv.get(); self.nome=nv.get()
            self._user_lbl.configure(text=self.nome); messagebox.showinfo("Salvo","Configurações atualizadas!")
        Btn(c1,"✓ Salvar",save,w=160).pack(anchor="w",padx=18,pady=(4,16))

        c2=Card(p); c2.grid(row=1,column=0,sticky="ew",pady=(0,10))
        ctk.CTkLabel(c2,text="ℹ️  Informações",font=("Segoe UI",13,"bold"),text_color=WHITE).pack(anchor="w",padx=18,pady=(14,6))
        Div(c2).pack(fill="x",padx=18)
        inf=ctk.CTkFrame(c2,fg_color="transparent"); inf.pack(fill="x",padx=18,pady=10)
        inf.grid_columnconfigure(1,weight=1)
        rows=[("📁 Banco",self.db.path),
              ("💸 Transações",str(self.db.q("SELECT COUNT(*) n FROM tx")[0][0])),
              ("🎯 Metas ativas",str(self.db.q("SELECT COUNT(*) n FROM metas WHERE ativo=1")[0][0])),
              ("💳 Dívidas ativas",str(self.db.q("SELECT COUNT(*) n FROM div WHERE ativo=1")[0][0]))]
        for i,(k,v) in enumerate(rows):
            lbl(inf,k,10,color=TEXT3).grid(row=i,column=0,pady=5,sticky="w")
            lbl(inf,v,10,color=TEXT).grid(row=i,column=1,padx=16,sticky="w")

        c3=Card(p); c3.configure(border_color=RED); c3.grid(row=2,column=0,sticky="ew")
        ctk.CTkLabel(c3,text="⚠️  Zona de Perigo",font=("Segoe UI",13,"bold"),text_color=RED).pack(anchor="w",padx=18,pady=(14,4))
        lbl(c3,"Ações irreversíveis.",10).pack(anchor="w",padx=18)
        def clear():
            if messagebox.askyesno("ATENÇÃO","Apagar TODAS as transações?"):
                self.db.run("DELETE FROM tx"); messagebox.showinfo("Feito","Removido.")
        Btn(c3,"🗑  Limpar Transações",clear,RED,w=200).pack(anchor="w",padx=18,pady=(8,16))


if __name__=="__main__":
    if not HAS_MPL: print("⚠️  Instale matplotlib: pip install matplotlib")
    App().mainloop()