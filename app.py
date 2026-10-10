import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import openpyxl
import os



# Chargement des donnees FAOSTAT
def charger_donnees_faostat(chemin):
    wb = openpyxl.load_workbook(chemin)
    ws = wb.active
    donnees = {"senegal": {}, "mali": {}, "niger": {}}
    for row in ws.iter_rows(min_row=2, values_only=True):
        annee, senegal, mali, niger = row
        if annee is not None:
            donnees["senegal"][int(annee)] = senegal
            donnees["mali"][int(annee)]    = mali
            donnees["niger"][int(annee)]   = niger
    return donnees



# Fonction d'appariement
def appariement(M, F, a, k=1000):
    if M + k == 0:
        return 0.0
    return a * F * M / (M + k)



# Systeme d'equations differentielles
def systeme(t, u, params):
    M, F, Fp, JM, JF = u

    f_val = appariement(M, F, params["a"])

    dM  = params["gm"] * JM  - (params["uM"] + params["tM"] + params["sM"]) * M
    dF  = params["gf"] * JF  - f_val - (params["uF"] + params["sF"] + params["tF"]) * F + params["d"] * Fp
    dFp = f_val               - (params["d"] + params["uFp"]) * Fp
    dJM = params["lm"] * Fp  - (params["gm"] + params["um"]) * JM
    dJF = params["lf"] * Fp  - (params["gf"] + params["uf"]) * JF

    return np.array([dM, dF, dFp, dJM, dJF])



# Runge-Kutta ordre 4
def rk4(f, t0, u0, h, T_final, params):
    t = float(t0)
    u = np.array(u0, dtype="float64")
    T = [t]
    U = [u.copy()]

    while t < T_final:
        k1 = f(t,       u,               params)
        k2 = f(t + h/2, u + (h/2) * k1, params)
        k3 = f(t + h/2, u + (h/2) * k2, params)
        k4 = f(t + h,   u + h      * k3, params)
        u  = u + (h / 6) * (k1 + 2*k2 + 2*k3 + k4)
        t  = t + h
        T.append(t)
        U.append(u.copy())

    return np.array(T), np.array(U)

# Calcul des metriques RMSE et MAPE
def calculer_metriques(annees_r, pop_r, T_annees, pop_sim, debut, fin):
    yr, ys = [], []
    for annee, reel in zip(annees_r, pop_r):
        if debut <= annee <= fin:
            idx = np.argmin(np.abs(T_annees - annee))
            yr.append(reel)
            ys.append(pop_sim[idx])
    if not yr:
        return None, None
    yr = np.array(yr, dtype=float)
    ys = np.array(ys, dtype=float)
    rmse = np.sqrt(np.mean((ys - yr) ** 2))
    mape = np.mean(np.abs((ys - yr) / yr)) * 100
    return rmse, mape



# Constantes
PROPORTIONS_DEFAUT = {
    "senegal": {"M": 0.06,  "F": 0.27,  "Fp": 0.18,  "JM": 0.15,  "JF": 0.34},
    "mali":    {"M": 0.156, "F": 0.222, "Fp": 0.144, "JM": 0.224, "JF": 0.254},
    "niger":   {"M": 0.122, "F": 0.227, "Fp": 0.15,  "JM": 0.256, "JF": 0.245},
}

COULEURS_PAYS = {
    "senegal": "#27ae60",
    "mali":    "#e74c3c",
    "niger":   "#2980b9",
}

NOMS_PAYS = {
    "senegal": "Senegal",
    "mali":    "Mali",
    "niger":   "Niger",
}

COMPARTIMENTS = {
    "Population totale":            None,
    "Males matures (M)":            0,
    "Femelles non gestantes (F)":   1,
    "Femelles gestantes (Fp)":      2,
    "Jeunes males (JM)":            3,
    "Jeunes femelles (JF)":         4,
}

BG = "#f0f0f0"



# Application principale
class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Evolution du betail - Afrique de l'Ouest")
        self.geometry("1280x800")
        self.resizable(True, True)

        chemin = os.path.join(os.path.dirname(__file__), "donnees_FAOSTAT.xlsx")
        self.donnees = charger_donnees_faostat(chemin)

        self._construire_interface()

    # Construction de l'interface
    def _construire_interface(self):
        # Panneau gauche : grid avec 3 lignes (scroll | separateur | boutons)
        panneau_gauche = tk.Frame(self, width=375, bg=BG)
        panneau_gauche.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=6)
        panneau_gauche.pack_propagate(False)
        panneau_gauche.grid_rowconfigure(0, weight=1)
        panneau_gauche.grid_rowconfigure(1, weight=0)
        panneau_gauche.grid_rowconfigure(2, weight=0)
        panneau_gauche.grid_columnconfigure(0, weight=1)

        # Ligne 0 : zone scrollable
        cadre_scroll = tk.Frame(panneau_gauche, bg=BG)
        cadre_scroll.grid(row=0, column=0, sticky="nsew")

        canvas_scroll = tk.Canvas(cadre_scroll, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(cadre_scroll, orient="vertical", command=canvas_scroll.yview)
        self.frame_scroll = tk.Frame(canvas_scroll, bg=BG)

        self.frame_scroll.bind(
            "<Configure>",
            lambda e: canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all"))
        )

        canvas_scroll.create_window((0, 0), window=self.frame_scroll, anchor="nw")
        canvas_scroll.configure(yscrollcommand=scrollbar.set)
        canvas_scroll.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Ligne 1 : separateur
        tk.Frame(panneau_gauche, bg="#bbbbbb", height=2).grid(row=1, column=0, sticky="ew")

        # Ligne 2 : boutons toujours visibles
        cadre_boutons = tk.Frame(panneau_gauche, bg=BG)
        cadre_boutons.grid(row=2, column=0, sticky="ew", padx=8, pady=8)

        tk.Button(
            cadre_boutons, text="Par defaut", command=self.inserer_defaut,
            bg="#2980b9", fg="white", font=("Arial", 9, "bold"), width=10
        ).pack(side=tk.LEFT, padx=3)

        tk.Button(
            cadre_boutons, text="Nettoyer", command=self.nettoyer_champs,
            bg="#c0392b", fg="white", font=("Arial", 9, "bold"), width=10
        ).pack(side=tk.LEFT, padx=3)

        tk.Button(
            cadre_boutons, text="Simuler", command=self.lancer_simulation,
            bg="#27ae60", fg="white", font=("Arial", 9, "bold"), width=10
        ).pack(side=tk.LEFT, padx=3)

        # Panneau droit : graphique
        panneau_droit = tk.Frame(self, bg="white")
        panneau_droit.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=6, pady=6)

        self._section_pays(self.frame_scroll)
        self._section_parametres(self.frame_scroll)
        self._section_proportions(self.frame_scroll)
        self._section_options(self.frame_scroll)
        self._section_graphique(panneau_droit)

    # Section pays
    def _section_pays(self, parent):
        cadre = tk.LabelFrame(parent, text="Pays", bg=BG, font=("Arial", 9, "bold"))
        cadre.pack(fill=tk.X, padx=8, pady=(8, 4))

        self.var_pays = {}
        for pays in ["senegal", "mali", "niger"]:
            var = tk.BooleanVar(value=True)
            self.var_pays[pays] = var
            tk.Checkbutton(
                cadre, text=NOMS_PAYS[pays], variable=var,
                bg=BG, font=("Arial", 9),
                command=self._simuler_si_pret
            ).pack(side=tk.LEFT, padx=10, pady=4)

    # Section parametres
    def _section_parametres(self, parent):
        cadre = tk.LabelFrame(parent, text="Parametres (valeurs annuelles)", bg=BG, font=("Arial", 9, "bold"))
        cadre.pack(fill=tk.X, padx=8, pady=4)

        self.champs_params = {}
        etiquettes = [
            ("gm",  "Taux maturation males"),
            ("uM",  "Mortalite males matures"),
            ("tM",  "Prelevement males matures"),
            ("tF",  "Prelevement femelles matures"),
            ("gf",  "Taux maturation femelles"),
            ("uF",  "Mortalite femelles matures"),
            ("sM",  "Taux abattage males"),
            ("sF",  "Taux abattage femelles"),
            ("d",   "Taux de mise bas"),
            ("uFp", "Mortalite femelles gestantes"),
            ("lm",  "Taux naissance males"),
            ("um",  "Mortalite jeunes males"),
            ("lf",  "Taux naissance femelles"),
            ("uf",  "Mortalite jeunes femelles"),
            ("a",   "Taux appariement fertile"),
        ]

        for cle, libelle in etiquettes:
            ligne = tk.Frame(cadre, bg=BG)
            ligne.pack(fill=tk.X, padx=4, pady=1)
            tk.Label(ligne, text=libelle, bg=BG, font=("Arial", 8), width=26, anchor="w").pack(side=tk.LEFT)
            champ = tk.Entry(ligne, width=9, font=("Arial", 8))
            champ.pack(side=tk.RIGHT)
            champ.bind("<Return>", lambda e: self._simuler_si_pret())
            self.champs_params[cle] = champ

    # Section proportions initiales
    def _section_proportions(self, parent):
        cadre = tk.LabelFrame(parent, text="Proportions initiales (%)", bg=BG, font=("Arial", 9, "bold"))
        cadre.pack(fill=tk.X, padx=8, pady=4)

        for col, texte in enumerate(["", "M", "F", "Fp", "JM", "JF"]):
            tk.Label(cadre, text=texte, bg=BG, font=("Arial", 8, "bold"), width=6).grid(
                row=0, column=col, padx=2, pady=2
            )

        self.champs_prop = {}
        for i, pays in enumerate(["senegal", "mali", "niger"]):
            tk.Label(cadre, text=NOMS_PAYS[pays], bg=BG, font=("Arial", 8), anchor="w").grid(
                row=i+1, column=0, sticky="w", padx=4
            )
            self.champs_prop[pays] = {}
            for j, comp in enumerate(["M", "F", "Fp", "JM", "JF"]):
                champ = tk.Entry(cadre, width=6, font=("Arial", 8))
                champ.grid(row=i+1, column=j+1, padx=2, pady=2)
                champ.bind("<Return>", lambda e: self._simuler_si_pret())
                self.champs_prop[pays][comp] = champ

    # Section options de visualisation
    def _section_options(self, parent):
        cadre = tk.LabelFrame(parent, text="Visualisation", bg=BG, font=("Arial", 9, "bold"))
        cadre.pack(fill=tk.X, padx=8, pady=4)

        # Compartiment a afficher
        ligne1 = tk.Frame(cadre, bg=BG)
        ligne1.pack(fill=tk.X, padx=4, pady=3)
        tk.Label(ligne1, text="Afficher :", bg=BG, font=("Arial", 8), width=10, anchor="w").pack(side=tk.LEFT)
        self.var_graphe = tk.StringVar(value="Population totale")
        menu = ttk.Combobox(
            ligne1, textvariable=self.var_graphe,
            values=list(COMPARTIMENTS.keys()),
            state="readonly", width=24, font=("Arial", 8)
        )
        menu.pack(side=tk.LEFT, padx=4)
        menu.bind("<<ComboboxSelected>>", lambda e: self._simuler_si_pret())

        # Filtre annees
        ligne2 = tk.Frame(cadre, bg=BG)
        ligne2.pack(fill=tk.X, padx=4, pady=3)
        tk.Label(ligne2, text="Annees :", bg=BG, font=("Arial", 8), width=10, anchor="w").pack(side=tk.LEFT)
        self.champ_annee_debut = tk.Entry(ligne2, width=6, font=("Arial", 8))
        self.champ_annee_debut.insert(0, "2000")
        self.champ_annee_debut.pack(side=tk.LEFT, padx=2)
        tk.Label(ligne2, text="a", bg=BG, font=("Arial", 8)).pack(side=tk.LEFT)
        self.champ_annee_fin = tk.Entry(ligne2, width=6, font=("Arial", 8))
        self.champ_annee_fin.insert(0, "2024")
        self.champ_annee_fin.pack(side=tk.LEFT, padx=2)
        self.champ_annee_debut.bind("<Return>", lambda e: self._simuler_si_pret())
        self.champ_annee_fin.bind("<Return>",   lambda e: self._simuler_si_pret())

        # Checkbox analyse long terme
        self.var_variation_sf = tk.BooleanVar(value=False)
        tk.Checkbutton(
            cadre, text="Analyse long terme : variation sF",
            variable=self.var_variation_sf, bg=BG, font=("Arial", 8),
            command=self._basculer_mode_sf
        ).pack(anchor="w", padx=4, pady=3)

        # Bloc slider (masque au demarrage)
        self.cadre_slider = tk.Frame(cadre, bg=BG)

        tk.Label(
            self.cadre_slider,
            text="Courbe variable — sF personnalise :",
            bg=BG, font=("Arial", 8, "bold")
        ).pack(anchor="w", padx=4, pady=(4, 0))

        ligne_sf = tk.Frame(self.cadre_slider, bg=BG)
        ligne_sf.pack(fill=tk.X, padx=4)

        self.label_sf_val = tk.Label(
            ligne_sf, text="sF = 0.020", bg=BG, font=("Arial", 9, "bold"),
            fg="#8e44ad", width=10, anchor="w"
        )
        self.label_sf_val.pack(side=tk.LEFT)

        self.slider_sf = tk.Scale(
            ligne_sf,
            from_=0, to=400,
            orient=tk.HORIZONTAL,
            resolution=1,
            showvalue=False,
            bg=BG,
            highlightthickness=0,
            command=self._slider_sf_change
        )
        self.slider_sf.set(20)
        self.slider_sf.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 8))

        # Legende des 3 courbes
        tk.Label(
            self.cadre_slider,
            text="Courbe 1 : sF = 0 (aucun abattage femelles)\n"
                 "Courbe 2 : donnees reelles FAOSTAT\n"
                 "Courbe 3 : sF variable (slider ci-dessus)",
            bg=BG, font=("Arial", 7), fg="#555555", justify=tk.LEFT
        ).pack(anchor="w", padx=8, pady=(2, 6))

        self.cadre_slider.pack_forget()

        # Pas de temps
        ligne3 = tk.Frame(cadre, bg=BG)
        ligne3.pack(fill=tk.X, padx=4, pady=3)
        tk.Label(ligne3, text="Pas h (jours) :", bg=BG, font=("Arial", 8), width=14, anchor="w").pack(side=tk.LEFT)
        self.champ_h = tk.Entry(ligne3, width=6, font=("Arial", 8))
        self.champ_h.insert(0, "1")
        self.champ_h.pack(side=tk.LEFT)

    # Zone graphique
    def _section_graphique(self, parent):
        barre_haut = tk.Frame(parent, bg="white")
        barre_haut.pack(fill=tk.X, padx=4, pady=(4, 0))

        tk.Button(
            barre_haut, text="Sauvegarder PNG", command=self.sauvegarder_image,
            bg="#8e44ad", fg="white", font=("Arial", 9, "bold")
        ).pack(side=tk.RIGHT, padx=4)

        self.figure = plt.Figure(figsize=(9, 5.5), dpi=96)
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.label_metriques = tk.Label(
            parent, text="", bg="white",
            font=("Arial", 9), fg="#2c3e50", anchor="center"
        )
        self.label_metriques.pack(fill=tk.X, padx=4, pady=4)

    # Basculer l'affichage du slider
    def _basculer_mode_sf(self):
        if self.var_variation_sf.get():
            self.cadre_slider.pack(fill=tk.X, padx=4, pady=2)
        else:
            self.cadre_slider.pack_forget()
        self._simuler_si_pret()

    # Callback slider sF
    def _slider_sf_change(self, valeur):
        sf_val = int(valeur) / 1000.0
        self.label_sf_val.config(text=f"sF = {sf_val:.3f}")
        self._simuler_si_pret()

    # Dictionnaire des jeux de parametres par defaut (un par pays)
    PRESETS_DEFAUT = {
        "senegal": {
            "label": "Senegal",
            "params": {
                "gm": 0.33,  "uM": 0.0501, "tM": 0.0053, "tF": 0.0,
                "gf": 0.33,  "uF": 0.082,  "sM": 0.1,    "sF": 0.02,
                "d":  0.53,  "uFp": 0.1,   "lm": 0.265,  "um": 0.125,
                "lf": 0.265, "uf": 0.1183, "a":  0.61,
            },
        },
        "mali": {
            "label": "Mali",
            "params": {
                "gm": 0.30,  "uM": 0.0501, "tM": 0.0053, "tF": 0.0,
                "gf": 0.34,  "uF": 0.082,  "sM": 0.05,   "sF": 0.01,
                "d":  0.48,  "uFp": 0.1,   "lm": 0.32,   "um": 0.125,
                "lf": 0.32,  "uf": 0.1183, "a":  0.85,
            },
        },
        "niger": {
            "label": "Niger",
            "params": {
                "gm": 0.33,  "uM": 0.0501, "tM": 0.0053, "tF": 0.0,
                "gf": 0.44,  "uF": 0.082,  "sM": 0.07,   "sF": 0.005,
                "d":  0.58,  "uFp": 0.1,   "lm": 0.38,   "um": 0.125,
                "lf": 0.38,  "uf": 0.1183, "a":  0.80,
            },
        },
    }

    # Fenetre de selection du jeu de parametres par defaut
    def inserer_defaut(self):
        fenetre = tk.Toplevel(self)
        fenetre.title("Choisir un jeu de parametres par defaut")
        fenetre.resizable(False, False)
        fenetre.grab_set()

        # Centrer la fenetre par rapport a la fenetre principale
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()  - 620) // 2
        y = self.winfo_y() + (self.winfo_height() - 340) // 2
        fenetre.geometry(f"620x340+{x}+{y}")
        fenetre.configure(bg=BG)

        tk.Label(
            fenetre,
            text="Selectionner un jeu de parametres calibres",
            bg=BG, font=("Arial", 10, "bold")
        ).pack(pady=(12, 6))

        tk.Label(
            fenetre,
            text="Chaque slot correspond au jeu de parametres qui ajuste le mieux la courbe du pays indique.",
            bg=BG, font=("Arial", 8), fg="#555555"
        ).pack(pady=(0, 10))

        # Cadre des 3 slots cote a cote
        cadre_slots = tk.Frame(fenetre, bg=BG)
        cadre_slots.pack(fill=tk.X, padx=14, pady=4)

        infos_slots = [
            ("senegal", "#27ae60", "MAPE ≈ 3.8 %"),
            ("mali",    "#e74c3c", "MAPE ≈ 2.0 %"),
            ("niger",   "#2980b9", "MAPE ≈ 2.8 %"),
        ]

        for col, (pays, couleur, mape_info) in enumerate(infos_slots):
            preset  = self.PRESETS_DEFAUT[pays]
            p       = preset["params"]

            slot = tk.Frame(cadre_slots, bg="white", relief=tk.RIDGE, bd=1)
            slot.grid(row=0, column=col, padx=6, sticky="nsew")
            cadre_slots.grid_columnconfigure(col, weight=1)

            # En-tete colore
            entete = tk.Frame(slot, bg=couleur)
            entete.pack(fill=tk.X)
            tk.Label(
                entete,
                text=f"Slot {col+1} — {preset['label']}",
                bg=couleur, fg="white", font=("Arial", 9, "bold")
            ).pack(pady=4)

            # Parametres affiches (les plus discriminants)
            corps = tk.Frame(slot, bg="white")
            corps.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

            lignes_affichees = [
                ("gm",  "Matur. M"),
                ("gf",  "Matur. F"),
                ("d",   "Mise bas"),
                ("sM",  "Abattage M"),
                ("sF",  "Abattage F"),
                ("lm",  "Naiss. M"),
                ("lf",  "Naiss. F"),
                ("a",   "Appariement"),
            ]
            for cle, libelle in lignes_affichees:
                ligne = tk.Frame(corps, bg="white")
                ligne.pack(fill=tk.X, pady=1)
                tk.Label(ligne, text=f"{libelle} :", bg="white",
                         font=("Arial", 7), width=11, anchor="w").pack(side=tk.LEFT)
                tk.Label(ligne, text=f"{p[cle]:.4f}", bg="white",
                         font=("Arial", 7, "bold"), fg=couleur).pack(side=tk.LEFT)

            # Indication MAPE
            tk.Label(slot, text=mape_info, bg="white",
                     font=("Arial", 7, "italic"), fg="#888888").pack(pady=(2, 4))

            # Bouton Appliquer
            tk.Button(
                slot,
                text="Appliquer",
                command=lambda pays=pays, fen=fenetre: self._appliquer_preset(pays, fen),
                bg=couleur, fg="white", font=("Arial", 8, "bold"), width=10
            ).pack(pady=(0, 8))

        # Bouton Annuler
        tk.Button(
            fenetre, text="Annuler", command=fenetre.destroy,
            bg="#7f8c8d", fg="white", font=("Arial", 9), width=10
        ).pack(pady=10)

    # Application du preset selectionne dans la fenetre
    def _appliquer_preset(self, pays, fenetre):
        valeurs = self.PRESETS_DEFAUT[pays]["params"]

        for cle, val in valeurs.items():
            self.champs_params[cle].delete(0, tk.END)
            self.champs_params[cle].insert(0, str(val))

        for p in ["senegal", "mali", "niger"]:
            for comp in ["M", "F", "Fp", "JM", "JF"]:
                self.champs_prop[p][comp].delete(0, tk.END)
                self.champs_prop[p][comp].insert(0, f"{PROPORTIONS_DEFAUT[p][comp]*100:.1f}")

        if fenetre is not None:
            fenetre.destroy()
        self._simuler_si_pret()

    # Nettoyer
    def nettoyer_champs(self):
        for champ in self.champs_params.values():
            champ.delete(0, tk.END)
        for pays in self.champs_prop.values():
            for champ in pays.values():
                champ.delete(0, tk.END)
        self.label_metriques.config(text="")
        self.figure.clear()
        self.canvas.draw()

    # Lecture des entrees
    def lire_parametres(self):
        params = {}
        try:
            for cle in self.champs_params:
                params[cle] = float(self.champs_params[cle].get()) / 365
        except ValueError:
            messagebox.showerror("Erreur", "Tous les parametres doivent etre des nombres.")
            return None
        return params

    def lire_proportions(self, pays):
        proportions = {}
        try:
            total = 0.0
            for comp in ["M", "F", "Fp", "JM", "JF"]:
                val = float(self.champs_prop[pays][comp].get()) / 100
                proportions[comp] = val
                total += val
            if abs(total - 1.0) > 0.05:
                messagebox.showwarning(
                    "Proportions",
                    f"Les proportions pour {NOMS_PAYS[pays]} totalisent {total*100:.1f}% (attendu 100%)."
                )
        except ValueError:
            messagebox.showerror("Erreur", f"Proportions invalides pour {NOMS_PAYS[pays]}.")
            return None
        return proportions

    def lire_filtre_annees(self):
        try:
            debut = int(self.champ_annee_debut.get())
            fin   = int(self.champ_annee_fin.get())
            if debut > fin:
                raise ValueError
            return debut, fin
        except ValueError:
            messagebox.showerror("Erreur", "Les annees doivent etre des entiers valides (debut <= fin).")
            return None, None

    # Simulation automatique si les champs sont remplis
    def _simuler_si_pret(self):
        for champ in self.champs_params.values():
            if champ.get().strip() == "":
                return
        self.lancer_simulation()

    # Lancement de la simulation
    def lancer_simulation(self):
        pays_selectionnes = [p for p, v in self.var_pays.items() if v.get()]
        if not pays_selectionnes:
            return

        params = self.lire_parametres()
        if params is None:
            return

        try:
            h = float(self.champ_h.get())
        except ValueError:
            return

        annee_debut, annee_fin = self.lire_filtre_annees()
        if annee_debut is None:
            return

        self.figure.clear()
        self.label_metriques.config(text="")

        if self.var_variation_sf.get():
            self._tracer_analyse_sf(pays_selectionnes, params, h, annee_debut, annee_fin)
        else:
            self._tracer_simulation(pays_selectionnes, params, h, annee_debut, annee_fin)

        self.canvas.draw()

    # Graphe principal : simule vs reel
    def _tracer_simulation(self, pays_selectionnes, params, h, annee_debut, annee_fin):
        ax            = self.figure.add_subplot(1, 1, 1)
        idx_comp      = COMPARTIMENTS[self.var_graphe.get()]
        textes_metric = []

        for pays in pays_selectionnes:
            proportions = self.lire_proportions(pays)
            if proportions is None:
                return

            annees_toutes = sorted(self.donnees[pays].keys())
            pop_initiale  = self.donnees[pays][annees_toutes[0]]
            u0 = [proportions[c] * pop_initiale for c in ["M", "F", "Fp", "JM", "JF"]]

            T, U     = rk4(systeme, annees_toutes[0] * 365, u0, h, annees_toutes[-1] * 365, params)
            T_annees = T / 365

            masque   = (T_annees >= annee_debut) & (T_annees <= annee_fin)
            T_f      = T_annees[masque]
            U_f      = U[masque]

            val_sim       = U_f.sum(axis=1)        if idx_comp is None else U_f[:, idx_comp]
            val_sim_toutes = U.sum(axis=1)          if idx_comp is None else U[:, idx_comp]

            couleur = COULEURS_PAYS[pays]
            ax.plot(T_f, val_sim, color=couleur, linewidth=2, label=f"{NOMS_PAYS[pays]} - simule")

            if idx_comp is None:
                annees_r = [a for a in annees_toutes if annee_debut <= a <= annee_fin]
                pop_r    = [self.donnees[pays][a] for a in annees_r]
                ax.plot(annees_r, pop_r, "o--", color=couleur, linewidth=1.2,
                        markersize=5, alpha=0.55, label=f"{NOMS_PAYS[pays]} - reel FAOSTAT")

                annees_r_all = sorted(self.donnees[pays].keys())
                pop_r_all    = [self.donnees[pays][a] for a in annees_r_all]
                rmse, mape   = calculer_metriques(annees_r_all, pop_r_all, T_annees, val_sim_toutes, annee_debut, annee_fin)
                if rmse is not None:
                    textes_metric.append(f"{NOMS_PAYS[pays]} : RMSE = {rmse/1e3:.1f}k  |  MAPE = {mape:.2f}%")

        ax.set_title(f"{self.var_graphe.get()} — {annee_debut} a {annee_fin}", fontsize=11, fontweight="bold")
        ax.set_xlabel("Annee")
        ax.set_ylabel("Effectif")
        ax.legend(fontsize=8)
        ax.grid(True, linestyle="--", alpha=0.4)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x/1e6:.2f}M"))
        self.figure.tight_layout()

        if textes_metric:
            self.label_metriques.config(text="     ".join(textes_metric))

    # Analyse long terme : 3 courbes avec slider sF
    def _tracer_analyse_sf(self, pays_selectionnes, params, h, annee_debut, annee_fin):
        ax   = self.figure.add_subplot(1, 1, 1)
        pays = pays_selectionnes[0]

        proportions = self.lire_proportions(pays)
        if proportions is None:
            return

        annees_toutes = sorted(self.donnees[pays].keys())
        pop_initiale  = self.donnees[pays][annees_toutes[0]]
        u0 = [proportions[c] * pop_initiale for c in ["M", "F", "Fp", "JM", "JF"]]

        t0 = annees_toutes[0] * 365
        tf = annee_fin        * 365

        # Courbe 1 : sF = 0
        p_sf0       = dict(params)
        p_sf0["sF"] = 0.0
        T1, U1      = rk4(systeme, t0, u0, h, tf, p_sf0)
        T1_a        = T1 / 365
        masque1     = (T1_a >= annee_debut) & (T1_a <= annee_fin)
        ax.plot(T1_a[masque1], U1[masque1].sum(axis=1),
                color="#2ecc71", linewidth=2.5, label="sF = 0 (aucun abattage femelles)")

        # Courbe 2 : donnees reelles FAOSTAT
        annees_r = [a for a in annees_toutes if annee_debut <= a <= annee_fin]
        pop_r    = [self.donnees[pays][a] for a in annees_r]
        ax.plot(annees_r, pop_r, "o--", color="#2c3e50", linewidth=2,
                markersize=6, label="Donnees reelles FAOSTAT")

        # Courbe 3 : sF variable via slider
        sf_val      = int(self.slider_sf.get()) / 1000.0
        p_sf_var    = dict(params)
        p_sf_var["sF"] = sf_val / 365
        T3, U3      = rk4(systeme, t0, u0, h, tf, p_sf_var)
        T3_a        = T3 / 365
        masque3     = (T3_a >= annee_debut) & (T3_a <= annee_fin)
        ax.plot(T3_a[masque3], U3[masque3].sum(axis=1),
                color="#8e44ad", linewidth=2.5, linestyle="--",
                label=f"sF = {sf_val:.3f} (variable)")

        ax.set_title(
            f"Analyse sF — {NOMS_PAYS[pays]} — {annee_debut} a {annee_fin}",
            fontsize=11, fontweight="bold"
        )
        ax.set_xlabel("Annee")
        ax.set_ylabel("Population bovine totale")
        ax.legend(fontsize=9)
        ax.grid(True, linestyle="--", alpha=0.4)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x/1e6:.2f}M"))
        self.figure.tight_layout()

        # Metriques entre courbe variable et reel
        if annees_r:
            rmse, mape = calculer_metriques(
                annees_r, pop_r, T3_a, U3[masque3].sum(axis=1), annee_debut, annee_fin
            )
            # recalcul sur toute la plage pour les metriques
            annees_reel_all = sorted(self.donnees[pays].keys())
            pop_reel_all    = [self.donnees[pays][a] for a in annees_reel_all]
            rmse, mape = calculer_metriques(annees_reel_all, pop_reel_all, T3_a,
                                            U3.sum(axis=1), annee_debut, annee_fin)
            if rmse is not None:
                self.label_metriques.config(
                    text=f"{NOMS_PAYS[pays]} (sF={sf_val:.3f}) : RMSE = {rmse/1e3:.1f}k  |  MAPE = {mape:.2f}%"
                )

    # Sauvegarde PNG
    def sauvegarder_image(self):
        chemin = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("Tous les fichiers", "*.*")],
            title="Enregistrer le graphe",
            initialfile="betail_graphe.png"
        )
        if chemin:
            self.figure.savefig(chemin, dpi=150, bbox_inches="tight")
            messagebox.showinfo("Sauvegarde", f"Image enregistree :\n{chemin}")



# Point d'entree
if __name__ == "__main__":
    app = Application()
    # Chargement automatique du preset Senegal au demarrage
    app._appliquer_preset("senegal", None)
    app.mainloop()