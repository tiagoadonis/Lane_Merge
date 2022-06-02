from flask import Flask, render_template
import time

app = Flask(__name__, static_url_path='/static')

@app.route("/")
def home():
    coordinates_obu1 = [[40.640571, -8.663110], [40.640517, -8.663169], [40.640489, -8.663201], 
                       [40.640455, -8.663244], [40.640375, -8.663347]]

    coordinates_obu2 = [[40.640615, -8.662906], [40.640461, -8.663109], [40.640395, -8.663191], 
                        [40.640323, -8.663289], [40.640160, -8.663497]]

    return render_template("index.html", obu1_speed = "300", coordinates_obu1 = coordinates_obu1, 
                           coordinates_obu2 = coordinates_obu2)

if __name__ == "__main__":
    app.run(debug=True)