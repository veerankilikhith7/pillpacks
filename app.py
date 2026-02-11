from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    message = """
    hey Gnanu,i believe in destiny from the day i saw you.
    mana eddharam same 5th cls lo join ayyam,inter dhaka adhe clg telidu baley vintha kadhaa kanisam chudala
    same centre malli 2years ayina teliduuu,ippudu same clg nenu ninnu 1-2 lo chusa appudu nuv telidu malli malli
    gaa nuv svs lo chadivavu ani telisindhi nenu shock nuv lunch box kosam kindhaki vasthavu anaganey nenu roju vache
    vadini ayina chudala maybe destiny antte adhe emoo..Gnanu i truly love you from the bottom of my heart.
    Will You Marry Me Gnanu! I don't know nitho vunte bagindidhi nuv navvithe bagundidhi overall nitho vunte chalu ane
    feeling vundidhi i hope your reply will be in a positive way.
    """
    return render_template("index.html", message=message)

@app.route("/yes")
def yes():
    return render_template("yes.html")

if __name__ == "__main__":
    app.run(debug=True)
