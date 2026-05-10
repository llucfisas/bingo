# 🎲 Bingo de festa

Web per fer un bingo amb amics durant una nit de festa. Una única partida activa a la vegada; quan acabeu, l'admin la reinicia per la pròxima.

## Com funciona

- **Fase 1** · Cadascú rep un "objectiu" (una altra persona del grup, a l'atzar) i li omple un cartró 3×3 amb 9 prediccions de coses que farà durant la nit.
- **Fase 2** · L'admin avança la partida i els cartrons es redistribueixen: a cada jugador li toca el cartró d'algú altre, sobre algú altre (ni el creador ni l'objectiu). Es marquen les caselles durant la nit.
- **Victòria** · El primer en fer línia s'anuncia (i la partida continua). El primer en omplir el cartró sencer, guanya i s'acaba la partida.

## Variables d'entorn

A Render hauràs de configurar **3 variables** (te les demanarà al deploy):

| Variable | Què és |
|---|---|
| `ADMIN_PASSWORD` | Contrasenya per ser admin. Només tu la sabràs. |
| `JOIN_PASSWORD` | Contrasenya per entrar al joc. La passes als amics perquè es puguin registrar. |
| `DATABASE_URL` | Connection string de Neon (vegeu sota). Si la deixes buida fa servir SQLite, però es perdrà a cada deploy. |

`SECRET_KEY` es genera sola.

---

## 🚀 Desplegament a Render + Neon (pas a pas)

### Pas 1 · Crear la base de dades persistent a Neon

[Neon](https://neon.tech) és Postgres gratuït, sense caducitat, perfecte per aquesta app.

1. Vés a [neon.tech](https://neon.tech) i fes Sign Up (amb GitHub va bé).
2. Crea un projecte nou (el nom és el que vulguis, regió Europa per latència).
3. Al dashboard del projecte, Connection Details, copia la **connection string** sencera. Té forma de:
   ```
   postgresql://username:password@ep-xxx-xxx.eu-central-1.aws.neon.tech/neondb?sslmode=require
   ```
4. Guarda-la, la faràs servir al pas 3.

### Pas 2 · Posar el codi a GitHub

```bash
cd bingo-festa
git init
git add .
git commit -m "Initial commit: bingo de festa"
```

Crea un repo nou a [github.com/new](https://github.com/new) (privat va bé) i:

```bash
git remote add origin https://github.com/EL_TEU_USUARI/bingo-festa.git
git branch -M main
git push -u origin main
```

### Pas 3 · Desplegar a Render

1. Vés a [dashboard.render.com](https://dashboard.render.com) → fes login amb GitHub.
2. Clica **New → Blueprint**.
3. Tria el teu repo `bingo-festa`. Render detectarà el `render.yaml`.
4. Et demanarà els 3 valors d'entorn:
   - `ADMIN_PASSWORD` · una contrasenya forta que recordis
   - `JOIN_PASSWORD` · una de més senzilla per passar als amics
   - `DATABASE_URL` · la connection string de Neon del pas 1
5. Clica **Apply** i espera 3-5 minuts.
6. Et donarà una URL `https://bingo-festa-XXXX.onrender.com`. Aquesta és la teva web.

### Avís sobre el pla gratuït de Render

El servei web **s'adorm després de 15 minuts d'inactivitat**. El primer cop que algú entri després d'una estona, trigarà ~30 segons a despertar-se. Per una nit de festa això no és problema — fes una primera visita 1 min abans que comenci.

Les dades són persistents perquè estan a Neon, no a Render.

---

## 🎮 Com s'utilitza

### Si ets l'admin

1. Comparteix la URL de la web amb els amics i la `JOIN_PASSWORD`.
2. Tu també et registres normal: nom, contrasenya teva, `JOIN_PASSWORD`. Desplega "Soc l'admin" i posa-hi `ADMIN_PASSWORD`.
3. Al panell d'admin, quan ja hi siguin tots (mínim 3), clica **Engegar Fase 1**.
4. Quan tothom hagi enviat el cartró (ho veuràs al panell), clica **Passar a Fase 2**.
5. Durant la nit pots tancar la partida manualment, o esperar a que algú ompli el cartró.
6. Després de la festa, des del panell pots **Reiniciar tot** per deixar la web a punt per a la pròxima.

### Si ets jugador

1. Entra a la URL → "Apuntar-me".
2. Posa el teu nom, una contrasenya teva (per tornar a entrar si surts) i la `JOIN_PASSWORD` que t'ha passat l'admin.
3. Quan engegui la fase 1, et dirà a qui has d'observar i podràs omplir el cartró.
4. Quan engegui la fase 2, veuràs el cartró que t'ha tocat — toca les caselles per marcar-les.

---

## 🛠️ Provar-ho en local

```bash
python -m venv .venv
source .venv/bin/activate          # Linux/Mac
# .venv\Scripts\activate           # Windows
pip install -r requirements.txt
export ADMIN_PASSWORD=admin123
export JOIN_PASSWORD=festa
export SECRET_KEY=qualsevolcosa
python app.py
```

Obre http://localhost:5000. En local fa servir SQLite (`bingo.db`).

---

## 📁 Estructura

```
bingo-festa/
├── app.py              # Lògica, rutes, autenticació
├── models.py           # Models de BD (Game, User, BingoCard)
├── requirements.txt    # Dependències Python
├── render.yaml         # Configuració de Render
├── templates/          # Plantilles Jinja
└── static/style.css    # Estils
```
